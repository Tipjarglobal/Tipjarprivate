from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import re
import json
import math
import hashlib
import base64
import logging
import asyncio
import unicodedata
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import jwt
import bcrypt
import secrets
import requests
import resend
from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends, UploadFile, File, Form, Header, Query
from fastapi.responses import Response
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, EmailStr

from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent
from forebet import scrape_forebet_today
from predictz import scrape_predictz, parse_pred_score
from models import (
    RegisterInput, VerifyInput, OriginInput, LoginInput, ProfileUpdate, TipSaveInput,
    RateInput, GiftInput, CheckoutInput, SubscribeInput, StatusInput, SmartIdeaInput,
    IdeaRateInput, VisitInput, PushSubIn,
)
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest,
)

# ------------------------------------------------------------------ config
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALGORITHM = "HS256"
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
STRIPE_API_KEY = os.environ.get('STRIPE_API_KEY')
AI_MODEL_PROVIDER = "gemini"
AI_MODEL = "gemini-3.1-pro-preview"
API_FOOTBALL_KEY = os.environ.get('API_FOOTBALL_KEY')
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
SETTLE_INTERVAL_SECONDS = 15 * 60

# ── Web Push (VAPID) ────────────────────────────────────────────────────────
from pywebpush import webpush, WebPushException
VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.environ.get("VAPID_SUBJECT", "mailto:admin@tipjarglobal.com")
SETTLE_BATCH_CAP = 50   # max tips processed per settlement run (Pro plan: 7500 req/day)
# Retry cap per tip. High enough that a match whose FT status is published late by
# API-Football (some leagues lag) still gets settled, and that games needing the
# date-scan fallback keep being retried until the 36h purge removes them anyway.
SETTLE_MAX_ATTEMPTS = 240
FINISHED_STATUSES = {"FT", "AET", "PEN"}

# ── Cheeky, TEMPORARY public subscriber boost (owner request). Adds a flat number to
# the PUBLICLY shown subscriber count for social proof. The real count is untouched in
# the DB and in the private /insights dashboard. Auto-expires after ~2 months. ──
SUBSCRIBER_DISPLAY_BOOST = 140
SUBSCRIBER_BOOST_UNTIL = "2026-09-09"  # after this date the boost is 0 automatically
# Same cheeky, TEMPORARY idea for the public member count on the homepage progress bar.
MEMBER_DISPLAY_BOOST = 400
MEMBER_BOOST_UNTIL = "2026-09-09"


def _member_boost() -> int:
    from datetime import date
    try:
        return MEMBER_DISPLAY_BOOST if date.today().isoformat() < MEMBER_BOOST_UNTIL else 0
    except Exception:
        return 0


def _sub_boost() -> int:
    from datetime import date
    try:
        return SUBSCRIBER_DISPLAY_BOOST if date.today().isoformat() < SUBSCRIBER_BOOST_UNTIL else 0
    except Exception:
        return 0
# statuses that mean the game is genuinely running right now
LIVE_STATUSES = {"1H", "2H", "HT", "ET", "BT", "P", "SUSP", "INT", "LIVE"}
# how long a live pick may stay open before it is force-settled no matter what the
# feed says (covers postponed/abandoned games and fixtures that never report FT)
LIVE_MAX_OPEN_HOURS = 3.5

APP_NAME = "tipjar"
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"

# Credit economy config
# 1 credit = €0.01 to buy. Withdrawals pay half: €5 per 1000 earned credits.
CREDIT_PACKAGES = {
    "starter": {"credits": 1000, "price": 10.0, "label": "Starter"},
    "pro": {"credits": 5000, "price": 50.0, "label": "Pro"},
    "whale": {"credits": 10000, "price": 100.0, "label": "Whale"},
}
CREDIT_CURRENCY = "eur"
GIFT_FEE = 0.10                 # platform keeps 10% of gifted credits
REFERRAL_REWARD = 100           # credits to referrer when invitee verifies email
REDEEM_THRESHOLD = 10000        # earned (received) credits needed to redeem
REDEEM_EUR_PER_1000 = 5.0       # withdrawals pay €5 per 1000 credits (10k => €50)
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'onboarding@resend.dev')
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("tipjar")

app = FastAPI(title="TipJar API")
api_router = APIRouter(prefix="/api")

# ------------------------------------------------------------------ storage
storage_key = None


def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_LLM_KEY}, timeout=30)
    resp.raise_for_status()
    storage_key = resp.json()["storage_key"]
    return storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str):
    key = init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ------------------------------------------------------------------ auth utils
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {"sub": user_id, "email": email,
               "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user.get("email"),
        "username": user.get("username"),
        "role": user.get("role", "user"),
        "timezone": user.get("timezone", "UTC"),
        "language": user.get("language", "en"),
        "credits": user.get("credits", 0),
        "received_credits": user.get("received_credits", 0),
        "streak": user.get("streak", 0),
        "apex_flame": user.get("apex_flame", False),
        "ratings_given": user.get("ratings_given", 0),
        "email_verified": user.get("email_verified", False),
        "referral_code": user.get("referral_code"),
        "created_at": user.get("created_at"),
    }


async def get_current_user(request: Request) -> dict:
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


@api_router.post("/admin/forebet/run")
async def admin_forebet_run(admin: dict = Depends(require_admin)):
    if not await ensure_chromium():
        return {"posted": 0, "reason": "chromium unavailable in this environment"}
    return await forebet_autopost()


@api_router.post("/admin/predictz/run")
async def admin_predictz_run(admin: dict = Depends(require_admin)):
    if not await ensure_chromium():
        return {"posted": 0, "reason": "chromium unavailable in this environment"}
    return await predictz_autopost()


@api_router.post("/admin/autotips/reset")
async def admin_autotips_reset(admin: dict = Depends(require_admin)):
    """Wipe all auto-posted HQ tips and regenerate them with current filters/odds."""
    deleted = (await db.tips.delete_many({"id": {"$regex": "^hqtip-"}})).deleted_count
    if not await ensure_chromium():
        return {"deleted": deleted, "posted_a": 0, "posted_b": 0, "reason": "chromium unavailable"}
    a = await forebet_autopost()
    b = await predictz_autopost()
    return {"deleted": deleted, "forebet": a, "predictz": b}


@api_router.post("/admin/smart/run")
async def admin_smart_run(admin: dict = Depends(require_admin)):
    return await smart_autopost()


@api_router.post("/admin/smart/reset")
async def admin_smart_reset(admin: dict = Depends(require_admin)):
    deleted = (await db.tips.delete_many({"source": "smart"})).deleted_count
    res = await smart_autopost()
    return {"deleted": deleted, **res}


@api_router.post("/smart/idea")
async def submit_smart_idea(
    text: str = Form(default=""),
    files: List[UploadFile] = File(default=[]),
    user: dict = Depends(get_current_user),
):
    text = (text or "").strip()
    uploads = [f for f in (files or []) if f is not None and getattr(f, "filename", None)][:3]
    images_b64 = []
    for f in uploads:
        rb = await f.read()
        images_b64.append(base64.b64encode(rb).decode("utf-8"))
    if len(text) < 6 and not images_b64:
        raise HTTPException(status_code=400, detail="Idee ist zu kurz — schreib etwas mehr oder lade ein Bild hoch.")
    if len(text) > 600:
        text = text[:600]
    now = datetime.now(timezone.utc)
    idea_id = str(uuid.uuid4())
    # Only image, no text → never create a public "Eingegangene Idee" feed card (it would
    # render blank). We still process the image into a pick below; the feed record is created
    # ONLY when there is real text to show.
    has_text = len(text) >= 6

    async def _drop_or_fail():
        if has_text:
            await db.smart_ideas.update_one({"id": idea_id}, {"$set": {"status": "not_actionable"}})

    if has_text:
        await db.smart_ideas.insert_one({
            "id": idea_id, "user_id": user["id"], "username": user.get("username", "anon"),
            "text": text, "images": len(images_b64), "status": "pending",
            "created_at": now.isoformat(), "tip_id": None,
        })

    data = await generate_smart_from_idea(text, images_b64)
    if not data:
        await _drop_or_fail()
        return {"ok": True, "created": False, "reason": "not_actionable"}

    home_in = (data.get("home_team") or "").strip()
    away_in = (data.get("away_team") or "").strip()
    market = (data.get("market") or "").strip()
    if not market or not home_in:
        await _drop_or_fail()
        return {"ok": True, "created": False, "reason": "not_actionable"}

    # Try to attach a real upcoming fixture for a precise kickoff (nice-to-have, NOT
    # required). If we find a near fixture (≤48h) the pick auto-settles; otherwise it
    # is posted as a REPORT/analysis (report=True → excluded from auto-settlement),
    # exactly like the curated WC analysis cards.
    kickoff, country, is_report = "", "", True
    tid = await resolve_team_id(home_in)
    fx = find_upcoming_fixture(tid, away_in) if tid else None
    if not fx and away_in:
        tid2 = await resolve_team_id(away_in)
        fx = find_upcoming_fixture(tid2, home_in) if tid2 else None
    if fx and fx.get("date_iso"):
        try:
            ko_dt = datetime.fromisoformat(fx["date_iso"].replace("Z", "+00:00"))
            hours_to_ko = (ko_dt - now).total_seconds() / 3600.0
            if -3 <= hours_to_ko <= 48:
                kickoff = ko_dt.strftime("%d/%m/%Y %H:%M")
                country = fx.get("country") or ""
                home_in = fx.get("home_name") or home_in
                away_in = fx.get("away_name") or away_in
                is_report = False
        except Exception:
            pass
    # fall back to a date/time the KI read off the screenshot (e.g. "09/07/2026 21:00")
    if not kickoff:
        kickoff = (data.get("match_time") or data.get("kickoff") or "").strip()

    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    tip_id = f"smart-idea-{idea_id[:8]}"
    try:
        rating = max(1.0, min(10.0, float(data.get("rating") or 7.0)))
    except Exception:
        rating = 7.0
    analysis = (data.get("analysis") or "").strip()
    analysis = f"{analysis} 💡 Community-Insider von @{user.get('username','anon')} — von der KI zu einem Smart-Pick verarbeitet."
    tip = {
        "id": tip_id, "user_id": (hq or user)["id"], "username": "TipJarHQ",
        "raw_text": "", "image_path": None,
        "home_team": home_in, "away_team": away_in,
        "match_time": kickoff, "country": country,
        "league": "TipJarHQ Smart Pick", "league_code": "",
        "market": market,
        "odds": str(data.get("odds") or "").strip(), "ai_rating": rating, "ai_analysis": analysis,
        "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
        "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
        "source": "smart", "smart_idea": True, "report": is_report,
        "idea_by": user.get("username", "anon"),
        "created_at": now.isoformat(),
    }
    await db.tips.insert_one(tip)
    await db.smart_ideas.update_one({"id": idea_id}, {"$set": {"status": "used", "tip_id": tip_id}})
    return {"ok": True, "created": True, "tip": {k: v for k, v in tip.items() if k != "_id"}}


@api_router.get("/admin/smart/ideas")
async def list_smart_ideas(admin: dict = Depends(require_admin)):
    docs = await db.smart_ideas.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return docs


@api_router.get("/smart/ideas/recent")
async def recent_smart_ideas(limit: int = 30):
    """Public feed of community Smart-Lab ideas that ACTUALLY became a Smart Pick
    (status='used'). Failed/non-actionable submissions ('KEIN TIPP', 'KEIN SPIEL
    GEFUNDEN') never appear — the feed only shows ideas that produced a real pick."""
    limit = max(1, min(limit, 60))
    docs = await db.smart_ideas.find(
        {"status": "used", "text": {"$nin": ["", None]}},
        {"_id": 0, "id": 1, "username": 1, "text": 1, "images": 1, "status": 1,
         "created_at": 1, "sum_stars": 1, "ratings_count": 1, "avg_rating": 1}
    ).sort("created_at", -1).to_list(limit)
    return [d for d in docs if (d.get("text") or "").strip()]


@api_router.post("/smart/ideas/{idea_id}/rate")
async def rate_smart_idea(idea_id: str, inp: IdeaRateInput, user: dict = Depends(get_current_user)):
    """Rate a community Smart-Lab idea on the Apex Scale (1–10 stars)."""
    idea = await db.smart_ideas.find_one({"id": idea_id})
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    now = datetime.now(timezone.utc)
    existing = await db.idea_ratings.find_one({"idea_id": idea_id, "user_id": user["id"]})
    if existing:
        delta = inp.stars - existing["stars"]
        await db.idea_ratings.update_one(
            {"_id": existing["_id"]}, {"$set": {"stars": inp.stars, "updated_at": now.isoformat()}})
        new_sum = idea.get("sum_stars", 0) + delta
        new_count = idea.get("ratings_count", 0)
    else:
        await db.idea_ratings.insert_one({
            "id": str(uuid.uuid4()), "idea_id": idea_id, "user_id": user["id"],
            "stars": inp.stars, "created_at": now.isoformat(),
        })
        new_sum = idea.get("sum_stars", 0) + inp.stars
        new_count = idea.get("ratings_count", 0) + 1
    avg = round(new_sum / new_count, 1) if new_count else 0
    await db.smart_ideas.update_one(
        {"id": idea_id},
        {"$set": {"sum_stars": new_sum, "ratings_count": new_count, "avg_rating": avg}})
    return {"ok": True, "idea_id": idea_id, "avg_rating": avg,
            "ratings_count": new_count, "your_stars": inp.stars}


@api_router.get("/smart/ideas/my-ratings")
async def my_idea_ratings(user: dict = Depends(get_current_user)):
    docs = await db.idea_ratings.find(
        {"user_id": user["id"]}, {"_id": 0, "idea_id": 1, "stars": 1}).to_list(500)
    return {d["idea_id"]: d["stars"] for d in docs}





@api_router.get("/system-slip")
async def system_slip():
    """Curated 'System-Schein der Woche': bundles the safest current HQ bankers
    into a ready-to-play system bet (bankers marked, combined odds, loss tolerance)."""
    docs = await db.tips.find(
        {"source": "hq-auto", "status": "pending", "is_parlay": {"$ne": True}}
    ).sort("ai_rating", -1).limit(150).to_list(150)
    picks, seen = [], set()
    for d in docs:
        if not _slip_eligible(d):
            continue
        key = _match_key(d.get("home_team"), d.get("away_team"))
        if key in seen:
            continue
        try:
            odds = float(str(d.get("odds") or "0").replace(",", "."))
        except Exception:
            odds = 0.0
        if odds < 1.01:
            continue
        seen.add(key)
        picks.append({
            "id": d["id"], "home_team": d.get("home_team"), "away_team": d.get("away_team"),
            "market": d.get("market"), "odds": round(odds, 2),
            "rating": d.get("ai_rating"), "match_time": d.get("match_time"),
        })
        if len(picks) >= 6:
            break
    banker_n = min(2, len(picks))
    total = 1.0
    for i, p in enumerate(picks):
        p["banker"] = i < banker_n
        total *= p["odds"]
    n = len(picks)
    if n >= 5:
        system_label = f"{n} Auswahlen · {n - 1}er-System · 1 Fehler erlaubt"
    elif n >= 3:
        system_label = f"{n} Auswahlen · Kombi"
    else:
        system_label = f"{n} Auswahlen"
    return {
        "selections": picks, "count": n, "banker_count": banker_n,
        "total_odds": round(total, 2), "system_label": system_label,
        "week": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
    }


@api_router.get("/systems")
async def systems():
    """Four curated system bets by risk profile, built from HQ match predictions:
    Lock Bet (safe goals), Value (odds >=1.50), Risk (double-chance + BTTS combos),
    Gamble (correct-score / draw longshots). Only bookmaker-available leagues."""
    return await build_systems()


@api_router.get("/tips/counts")
async def tips_counts():
    """Post counts per picks area — powers the homepage badges & area alerts.
    The AI badge reflects the next-24h picks (the default view) so it stays realistic."""
    await purge_expired_autotips()
    await purge_settled_tips()
    now = datetime.now(timezone.utc)
    # AI badge = every pending Single-Game pick (singles + bet-builder combos, all
    # days) so it matches the bundled red "new" count and the Banker/Value/Risk tabs.
    ai_docs = await db.tips.find(
        {"source": "hq-auto", "status": "pending"}, {"match_time": 1}).to_list(1000)
    ai = len(ai_docs)
    ai_total = ai
    members = await db.tips.count_documents({"source": {"$nin": ["hq-auto", "smart"]}, "status": "pending"})
    live = await db.tips.count_documents({"status": "live"})
    smart = await db.tips.count_documents({"source": "smart", "status": "pending"})
    settled = await db.tips.count_documents({"status": {"$in": ["won", "lost", "cashed_out"]}})
    won_n = await db.tips.count_documents({"status": "won"})
    lost_n = await db.tips.count_documents({"status": "lost"})
    cashed_n = await db.tips.count_documents({"status": "cashed_out"})
    bestwon_n = await db.tips.count_documents({
        "status": "won",
        "id": {"$not": {"$regex": "^seed-"}},
        "$or": [
            {"source": "smart"},
            {"source": "hq-system"},
            {"source": "hq-auto", "category": "risk"},
            {"source": {"$nin": ["hq-auto", "smart", "hq-live", "hq-system"]}},
        ],
    })
    won_normal_n = await db.tips.count_documents({
        "status": "won",
        "id": {"$not": {"$regex": "^seed-"}},
        "$or": [
            {"source": "hq-live"},
            {"source": "hq-auto", "category": {"$ne": "risk"}},
        ],
    })
    try:
        sysdata = await build_systems()
        systems_n = sum(1 for s in sysdata["systems"] if len(s["selections"]) >= 2)
    except Exception:
        systems_n = 0
    return {"ai": ai, "ai_total": ai_total, "members": members, "live": live,
            "systems": systems_n, "smart": smart, "settled": settled,
            "won": won_n, "lost": lost_n, "cashed": cashed_n, "bestwon": bestwon_n,
            "won_normal": won_normal_n}




def gen_referral_code() -> str:
    return uuid.uuid4().hex[:8]


async def send_verification_email(email: str, token: str, origin: str) -> dict:
    link = f"{(origin or '').rstrip('/')}/verify?token={token}"
    if not RESEND_API_KEY:
        logger.info(f"[DEV] Email not configured. Verification link for {email}: {link}")
        return {"sent": False, "link": link}
    html = f"""
    <div style="font-family:Arial,sans-serif;background:#09090b;padding:32px;color:#fff">
      <div style="max-width:480px;margin:auto;background:#18181b;border:1px solid #27272a;border-radius:16px;padding:32px">
        <h1 style="font-size:24px;margin:0 0 8px">Welcome to <span style="color:#E1FF00">TipJar</span> 🏆</h1>
        <p style="color:#a1a1aa;line-height:1.6">Confirm your email to activate your account and unlock referral rewards.</p>
        <a href="{link}" style="display:inline-block;margin-top:16px;background:#E1FF00;color:#09090b;font-weight:bold;text-decoration:none;padding:12px 24px;border-radius:999px">Verify my email</a>
        <p style="color:#71717a;font-size:12px;margin-top:20px">Or paste this link: {link}</p>
      </div>
    </div>"""
    try:
        await asyncio.to_thread(resend.Emails.send, {
            "from": SENDER_EMAIL, "to": [email],
            "subject": "Verify your TipJar email", "html": html,
        })
        return {"sent": True, "link": link}
    except Exception as e:
        logger.error(f"verification email failed: {e}")
        return {"sent": False, "link": link}


# ------------------------------------------------------------------ models
# (Pydantic request models moved to models.py — imported at the top of this file.)


# ------------------------------------------------------------------ AI
AI_SYSTEM = (
    "You are TipJar's expert football (soccer) betting analyst. You receive a screenshot of a "
    "bet slip — it may be a single bet, a bet-builder (one match, several selections), or a "
    "multi-match parlay/accumulator (several matches) — and/or the user's written tip. "
    "Read it precisely and return ONLY strict JSON, no markdown, with keys: "
    "is_parlay (true if more than one match OR more than one selection), "
    "legs (array with ONE object per MATCH, each: {\"match\": \"Home - Away\", "
    "\"league\": \"competition/league name, e.g. 'Allsvenskan', 'La Liga', 'UEFA Nations League'\", "
    "\"kickoff\": \"HH:MM or ''\", \"selections\": [\"exact market lines, e.g. 'Total Over 1.5', "
    "'Djurgaren Total Over 0.5', 'Fouls Over 21.5'\"], "
    "\"sel_odds\": [\"the decimal odd for EACH selection in the SAME order, e.g. '1.24'; use '' if a "
    "selection's odd is not shown\"]}), "
    "home_team, away_team, match_time, country, league, "
    "market (a short human summary of all selections), odds (total/combined odds as a string), "
    "stake (string, '' if unknown), "
    "potential_return (string): ALWAYS compute it as stake MULTIPLIED BY odds (stake x odds) and "
    "IGNORE any tax, fees or deductions shown on the slip; use '' only if stake or odds is unknown. "
    "match_time MUST contain the match DATE and kickoff TIME whenever they appear on the slip (e.g. '19/07/2026 21:00'). "
    "rating (1-10, quality/value of the bet), analysis (one short punchy sentence, max 160 chars). "
    "ALSO act as a content-moderator on BOTH the image and the written text and add two keys: "
    "safe (boolean) and flag_reason (short string). Set safe=false if the image or text contains ANY "
    "of: nudity or sexual/pornographic content, graphic violence or gore, hate speech, insults, "
    "harassment or profanity directed at people, or content that is clearly NOT a football bet slip/tip "
    "(spam, random selfies, unrelated pictures). Otherwise safe=true and flag_reason=''. "
    "Copy each selection line EXACTLY as it appears on the slip. If a field is unknown use an empty "
    "string. Never invent scores or results."
)


def _sanitize_legs(legs) -> list:
    out = []
    if isinstance(legs, list):
        for lg in legs:
            if isinstance(lg, dict):
                sels = lg.get("selections") or []
                sodds = lg.get("sel_odds") or []
                out.append({
                    "match": str(lg.get("match", "") or ""),
                    "league": str(lg.get("league", "") or ""),
                    "kickoff": str(lg.get("kickoff", "") or ""),
                    "selections": [str(s) for s in sels if s][:10],
                    "sel_odds": [str(o or "") for o in sodds][:10],
                })
    return out[:12]


async def analyze_tip(images_b64: Optional[List[str]], text: str) -> dict:
    fallback = {
        "home_team": "", "away_team": "", "match_time": "", "country": "",
        "league": "", "market": text.strip()[:60], "odds": "",
        "rating": 5.0, "analysis": "Auto-rating unavailable, rated neutral.",
        "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
        "safe": True, "flag_reason": "",
    }
    if not EMERGENT_LLM_KEY:
        return fallback
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"tip-{uuid.uuid4()}",
            system_message=AI_SYSTEM,
        ).with_model(AI_MODEL_PROVIDER, AI_MODEL)

        prompt = (
            f"User's written tip: {text or '(none)'}\n\n"
            "Analyse the attached bet slip screenshot (if any) together with the written tip. "
            "Extract the teams, kickoff, country, league, market and odds, then rate the bet 1-10. "
            "Respond with strict JSON only."
        )
        kwargs = {"text": prompt}
        if images_b64:
            kwargs["file_contents"] = [ImageContent(image_base64=b) for b in images_b64]
        resp = await chat.send_message(UserMessage(**kwargs))
        raw = resp if isinstance(resp, str) else str(resp)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:]
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end != -1:
            data = json.loads(raw[start:end + 1])
        else:
            return fallback
        rating = float(data.get("rating", 5) or 5)
        rating = max(1.0, min(10.0, rating))
        return {
            "home_team": str(data.get("home_team", "") or ""),
            "away_team": str(data.get("away_team", "") or ""),
            "match_time": str(data.get("match_time", "") or ""),
            "country": str(data.get("country", "") or ""),
            "league": str(data.get("league", "") or ""),
            "market": str(data.get("market", "") or "") or text.strip()[:60],
            "odds": str(data.get("odds", "") or ""),
            "stake": str(data.get("stake", "") or ""),
            "potential_return": compute_return(data.get("stake"), data.get("odds"), str(data.get("potential_return", "") or "")),
            "legs": _sanitize_legs(data.get("legs")),
            "is_parlay": bool(data.get("is_parlay", False)),
            "rating": round(rating, 1),
            "analysis": str(data.get("analysis", "") or "")[:200],
            "safe": bool(data.get("safe", True)),
            "flag_reason": str(data.get("flag_reason", "") or "")[:160],
        }
    except Exception as e:
        logger.error(f"AI analyze failed: {e}")
        return fallback


async def moderate_text(text: str) -> tuple[bool, str]:
    """Lightweight text moderation. Returns (safe, reason). Fails open on error."""
    text = (text or "").strip()
    if not text or not EMERGENT_LLM_KEY:
        return True, ""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"mod-{uuid.uuid4()}",
            system_message=(
                "You are a strict content moderator for a football betting-tips community. "
                "Return ONLY strict JSON {\"safe\": boolean, \"reason\": string}. "
                "Set safe=false if the text contains insults, hate speech, harassment, threats, "
                "sexual/pornographic content, or spam/links unrelated to a football tip. "
                "Normal football/betting talk is safe."
            ),
        ).with_model(AI_MODEL_PROVIDER, AI_MODEL)
        resp = await chat.send_message(UserMessage(text=f"Moderate this text:\n{text[:1500]}"))
        raw = (resp if isinstance(resp, str) else str(resp)).strip()
        s, e = raw.find("{"), raw.rfind("}")
        if s != -1 and e != -1:
            data = json.loads(raw[s:e + 1])
            return bool(data.get("safe", True)), str(data.get("reason", "") or "")[:160]
    except Exception as e:
        logger.error(f"text moderation failed: {e}")
    return True, ""


# ------------------------------------------------------------------ auth routes
@api_router.post("/auth/register")
async def register(inp: RegisterInput):
    email = inp.email.lower() if inp.email else None
    username = inp.username.strip()
    if email and await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": username}):
        raise HTTPException(status_code=400, detail="Username already taken")
    referred_by = None
    if inp.ref:
        ref_user = await db.users.find_one({"referral_code": inp.ref})
        if ref_user:
            referred_by = ref_user["id"]
    # No email => no verification needed, account is active immediately
    has_email = bool(email)
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": hash_password(inp.password),
        "username": username,
        "role": "user",
        "timezone": inp.timezone,
        "language": inp.language,
        "credits": 100,          # welcome credits
        "received_credits": 0,
        "streak": 0,
        "last_rated_date": None,
        "ratings_given": 0,
        "email_verified": not has_email,
        "referral_code": gen_referral_code(),
        "referred_by": referred_by,
        "referral_rewarded": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    token = create_access_token(user["id"], email or username)
    resp = {"token": token, "user": public_user(user)}
    if has_email:
        vtoken = secrets.token_urlsafe(24)
        await db.email_verification_tokens.insert_one({
            "token": vtoken, "user_id": user["id"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        })
        email_res = await send_verification_email(email, vtoken, inp.origin_url or "")
        resp["email_sent"] = email_res.get("sent", False)
        if not email_res.get("sent"):
            resp["verify_link"] = email_res.get("link")  # dev aid until Resend key is set
    else:
        # email-less account is active now -> grant referral reward immediately
        if referred_by:
            await db.users.update_one({"id": user["id"]}, {"$set": {"referral_rewarded": True}})
            await db.users.update_one({"id": referred_by}, {"$inc": {"credits": REFERRAL_REWARD}})
            await db.credit_transactions.insert_one({
                "id": str(uuid.uuid4()), "type": "referral", "to_user": referred_by,
                "from_user": user["id"], "from_username": user.get("username"),
                "amount": REFERRAL_REWARD, "created_at": datetime.now(timezone.utc).isoformat(),
            })
        resp["email_sent"] = False
    return resp


@api_router.post("/auth/verify-email")
async def verify_email(inp: VerifyInput):
    doc = await db.email_verification_tokens.find_one({"token": inp.token})
    if not doc:
        raise HTTPException(status_code=400, detail="Invalid or already-used verification link")
    try:
        expired = datetime.fromisoformat(doc["expires_at"]) < datetime.now(timezone.utc)
    except Exception:
        expired = False
    if expired:
        await db.email_verification_tokens.delete_one({"token": inp.token})
        raise HTTPException(status_code=400, detail="Verification link expired")
    user = await db.users.find_one({"id": doc["user_id"]})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    reward_granted = False
    if not user.get("email_verified"):
        await db.users.update_one({"id": user["id"]}, {"$set": {"email_verified": True}})
        if user.get("referred_by") and not user.get("referral_rewarded"):
            await db.users.update_one({"id": user["id"]}, {"$set": {"referral_rewarded": True}})
            await db.users.update_one({"id": user["referred_by"]}, {"$inc": {"credits": REFERRAL_REWARD}})
            await db.credit_transactions.insert_one({
                "id": str(uuid.uuid4()), "type": "referral", "to_user": user["referred_by"],
                "from_user": user["id"], "from_username": user.get("username"),
                "amount": REFERRAL_REWARD, "created_at": datetime.now(timezone.utc).isoformat(),
            })
            reward_granted = True
    await db.email_verification_tokens.delete_one({"token": inp.token})
    return {"verified": True, "referral_reward_granted": reward_granted}


@api_router.post("/auth/resend-verification")
async def resend_verification(inp: OriginInput, user: dict = Depends(get_current_user)):
    if user.get("email_verified"):
        return {"already_verified": True}
    vtoken = secrets.token_urlsafe(24)
    await db.email_verification_tokens.insert_one({
        "token": vtoken, "user_id": user["id"],
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    })
    res = await send_verification_email(user["email"], vtoken, inp.origin_url or "")
    out = {"email_sent": res.get("sent", False)}
    if not res.get("sent"):
        out["verify_link"] = res.get("link")
    return out


@api_router.post("/auth/login")
async def login(inp: LoginInput):
    ident = (inp.username or inp.email or "").strip()
    if not ident:
        raise HTTPException(status_code=400, detail="Username or email required")
    user = await db.users.find_one({"$or": [{"username": ident}, {"email": ident.lower()}]})
    if not user or not verify_password(inp.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(user["id"], user.get("email") or user["username"])
    return {"token": token, "user": public_user(user)}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    updates = {}
    if not user.get("referral_code"):
        updates["referral_code"] = gen_referral_code()
    if "email_verified" not in user:
        updates["email_verified"] = True  # grandfather pre-existing accounts
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        user.update(updates)
    return {"user": public_user(user)}


@api_router.put("/auth/profile")
async def update_profile(inp: ProfileUpdate, user: dict = Depends(get_current_user)):
    updates = {}
    if inp.username and inp.username != user.get("username"):
        if await db.users.find_one({"username": inp.username, "id": {"$ne": user["id"]}}):
            raise HTTPException(status_code=400, detail="Username already taken")
        updates["username"] = inp.username
    if inp.email is not None:
        new_email = inp.email.strip().lower()
        if new_email and new_email != (user.get("email") or "").lower():
            if "@" not in new_email or "." not in new_email:
                raise HTTPException(status_code=400, detail="Invalid email address")
            if await db.users.find_one({"email": new_email, "id": {"$ne": user["id"]}}):
                raise HTTPException(status_code=400, detail="Email already in use")
            updates["email"] = new_email
    if inp.timezone:
        updates["timezone"] = inp.timezone
    if inp.language:
        updates["language"] = inp.language
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
        if "username" in updates:
            await db.tips.update_many({"user_id": user["id"]}, {"$set": {"username": updates["username"]}})
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"user": public_user(fresh)}


# ------------------------------------------------------------------ tips
@api_router.post("/tips/analyze")
async def analyze(file: Optional[UploadFile] = File(default=None),
                  files: List[UploadFile] = File(default=[]),
                  text: str = Form(default=""),
                  user: dict = Depends(get_current_user)):
    # accept up to 4 screenshots (a bet slip split across multiple images)
    uploads = []
    if files:
        uploads.extend([f for f in files if f is not None and getattr(f, "filename", None)])
    if file is not None and getattr(file, "filename", None):
        uploads.append(file)
    uploads = uploads[:4]
    images_b64, raw_list = [], []
    for f in uploads:
        rb = await f.read()
        images_b64.append(base64.b64encode(rb).decode("utf-8"))
        raw_list.append((rb, f))
    # Moderate (images + text) FIRST — never store or publish unsafe content.
    detected = await analyze_tip(images_b64 or None, text)
    if not detected.get("safe", True):
        raise HTTPException(
            status_code=422,
            detail=(detected.get("flag_reason")
                    or "This content can't be posted (offensive or not a bet slip)."),
        )
    # Only now upload the images to storage.
    image_paths = []
    for rb, fm in raw_list:
        ext = (fm.filename.rsplit(".", 1)[-1] if fm.filename and "." in fm.filename else "png").lower()
        path = f"{APP_NAME}/tips/{user['id']}/{uuid.uuid4()}.{ext}"
        try:
            result = put_object(path, rb, fm.content_type or "image/png")
            image_paths.append(result["path"])
            await db.files.insert_one({
                "id": str(uuid.uuid4()), "storage_path": result["path"],
                "original_filename": fm.filename, "content_type": fm.content_type,
                "owner": user["id"], "is_deleted": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.error(f"upload failed: {e}")
    detected["image_path"] = image_paths[0] if image_paths else None
    detected["image_paths"] = image_paths
    return detected


def _parse_num(s):
    if s is None:
        return None
    s = re.sub(r"[^0-9.,]", "", str(s))
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".") if len(s.split(",")[-1]) <= 2 else s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _fmt_eur(v):
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def compute_return(stake, odds, fallback=""):
    """Winnings = stake x odds (taxes never applied). Falls back if not parseable."""
    s, o = _parse_num(stake), _parse_num(odds)
    if s and o and s > 0 and o > 0:
        return _fmt_eur(s * o)
    return fallback


LIVE_MATCH_MAX_MINUTES = 150  # a football match (incl. HT/stoppage) rarely runs past ~2.5h


def _kickoff_dt(mt: str):
    dt = _parse_kickoff(mt)
    if dt:
        return dt
    s = (mt or "").strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})", s)
    if m:
        y, mo, d, h, mi = map(int, m.groups())
        try:
            return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)
        except Exception:
            return None
    return None


def _looks_live_now(match_time: str, legs, now) -> bool:
    """A user-submitted slip counts as LIVE if its match kicked off within the
    last ~2.5h (or any leg of a parlay did) and hasn't obviously finished yet."""
    candidates = []
    ko = _kickoff_dt(match_time)
    if ko:
        candidates.append(ko)
    for lg in (legs or []):
        k = _kickoff_dt(lg.get("kickoff"))
        if k:
            candidates.append(k)
    for ko in candidates:
        mins = (now - ko).total_seconds() / 60.0
        if -5 <= mins <= LIVE_MATCH_MAX_MINUTES:
            return True
    return False



@api_router.post("/tips")
async def create_tip(inp: TipSaveInput, user: dict = Depends(get_current_user)):
    legs = _sanitize_legs(inp.legs)
    is_parlay = inp.is_parlay or (inp.legs is not None and len(inp.legs) > 1)
    # A self star-rating (1-10) is mandatory — no stars, no bet accepted.
    if not (1 <= (inp.self_rating or 0) <= 10):
        raise HTTPException(status_code=400, detail="Bitte vergib zuerst deine Sterne (1–10) für diesen Tipp — ohne Sterne wird die Wette nicht angenommen.")
    # Text moderation safety net (catches typed insults / bypassing the analyze step).
    mod_text = " ".join(str(x or "") for x in [inp.raw_text, inp.market, inp.ai_analysis,
                                               inp.home_team, inp.away_team]).strip()
    safe, reason = await moderate_text(mod_text)
    if not safe:
        raise HTTPException(status_code=422, detail=reason or "This tip contains content that isn't allowed.")
    match_time = (inp.match_time or "").strip()
    if not match_time:
        if is_parlay and legs:
            # Multibet: no single kickoff — take the first leg that carries a date/time.
            match_time = next((lg["kickoff"] for lg in legs if lg.get("kickoff")), "") or "Multibet"
        else:
            raise HTTPException(status_code=400, detail="Tip needs a match date & time — add the kickoff to publish.")
    dup = await db.tips.find_one({
        "user_id": user["id"],
        "home_team": inp.home_team,
        "away_team": inp.away_team,
        "market": inp.market,
        "odds": inp.odds,
        "match_time": match_time,
    })
    if dup:
        raise HTTPException(status_code=409, detail="You already posted this tip — duplicates aren't allowed.")
    # LIVE at post time: a bet counts as live only if its match is IN-PLAY when posted
    # (kickoff window OR — reliably, ignoring slip-timezone quirks — API-Football live list).
    now_dt = datetime.now(timezone.utc)
    is_live_post = _looks_live_now(match_time, legs, now_dt)
    if not is_live_post and API_FOOTBALL_KEY and inp.home_team and inp.away_team:
        try:
            live_fx = await asyncio.to_thread(_apifootball, "/fixtures", {"live": "all"})
            if live_fx and _find_live_fixture(live_fx, inp.home_team, inp.away_team):
                is_live_post = True
        except Exception:
            pass
    tip = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "username": user["username"],
        "raw_text": inp.raw_text,
        "image_path": inp.image_path,
        "image_paths": inp.image_paths or ([inp.image_path] if inp.image_path else []),
        "home_team": inp.home_team,
        "away_team": inp.away_team,
        "match_time": match_time,
        "country": inp.country,
        "league": inp.league,
        "market": inp.market,
        "odds": inp.odds,
        "ai_rating": inp.ai_rating,
        "ai_analysis": inp.ai_analysis,
        "legs": legs,
        "is_parlay": is_parlay,
        "stake": inp.stake,
        "potential_return": compute_return(inp.stake, inp.odds, inp.potential_return),
        "status": "live" if is_live_post else "pending",
        "sum_stars": inp.self_rating,
        "ratings_count": 1,
        "avg_rating": float(inp.self_rating),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tips.insert_one(tip)
    # record the owner's own rating so it counts and shows as "your rating"
    await db.tip_ratings.insert_one({
        "id": str(uuid.uuid4()), "tip_id": tip["id"], "user_id": user["id"],
        "stars": inp.self_rating, "created_at": tip["created_at"],
    })
    tip.pop("_id", None)
    return tip


def _clean_tip(t: dict) -> dict:
    t.pop("_id", None)
    return t


# Trusted-rater gating for instant 1-star purge
TRUSTED_MIN_TIPS = 3      # must have at least this many rated tips
TRUSTED_REPUTATION = 7.0  # average avg_rating (Apex 1-10) required to be "highly rated"


async def is_trusted_rater(user: dict) -> bool:
    if user.get("role") == "admin":
        return True
    res = await db.tips.aggregate([
        {"$match": {"user_id": user["id"], "ratings_count": {"$gt": 0}}},
        {"$group": {"_id": None, "avg": {"$avg": "$avg_rating"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    if not res:
        return False
    r = res[0]
    return r.get("n", 0) >= TRUSTED_MIN_TIPS and (r.get("avg") or 0) >= TRUSTED_REPUTATION


APEX_FLAME_STREAK = 30  # rating-streak days needed to unlock the cosmetic Apex-Flamme badge


async def _maybe_award_apex_flame(user_id: str, streak: int, now: datetime) -> bool:
    """Grant the cosmetic Apex-Flamme badge at a 30-day rating streak.
    Returns True only the first time it is granted."""
    if streak < APEX_FLAME_STREAK:
        return False
    res = await db.users.update_one(
        {"id": user_id, "apex_flame": {"$ne": True}},
        {"$set": {"apex_flame": True, "apex_flame_at": now.isoformat()}},
    )
    return res.modified_count > 0


async def _bump_rating_streak(user: dict, now: datetime) -> int:
    today = now.date().isoformat()
    streak = user.get("streak", 0)
    last = user.get("last_rated_date")
    if last != today:
        yesterday = (now.date() - timedelta(days=1)).isoformat()
        streak = streak + 1 if last == yesterday else 1
        await db.users.update_one({"id": user["id"]},
                                  {"$set": {"last_rated_date": today, "streak": streak},
                                   "$inc": {"ratings_given": 1}})
    else:
        await db.users.update_one({"id": user["id"]}, {"$inc": {"ratings_given": 1}})
    await _maybe_award_apex_flame(user["id"], streak, now)
    return streak


async def purge_demo_tips() -> int:
    """Delete tips (and their ratings) submitted by test-bot accounts (emails on the @t.com domain)."""
    testers = await db.users.find({"email": {"$regex": r"@t\.com$"}}, {"id": 1, "_id": 0}).to_list(1000)
    ids = [u["id"] for u in testers]
    if not ids:
        return 0
    tips = await db.tips.find({"user_id": {"$in": ids}}, {"id": 1, "_id": 0}).to_list(5000)
    tip_ids = [t["id"] for t in tips]
    if not tip_ids:
        return 0
    await db.tips.delete_many({"id": {"$in": tip_ids}})
    await db.tip_ratings.delete_many({"tip_id": {"$in": tip_ids}})
    logger.info(f"Purged {len(tip_ids)} demo/test tips")
    return len(tip_ids)


@api_router.get("/tips")
async def list_tips(status: Optional[str] = None, sort: str = "new",
                    source: Optional[str] = None, window: Optional[str] = None,
                    category: Optional[str] = None, limit: int = 50):
    q = {}
    if status:
        q["status"] = status
    # Every AI single lands in exactly one bucket. Banker/Risk are strict;
    # VALUE is the catch-all so no pick can ever fall through the cracks.
    if category == "banker":
        q["category"] = "banker"
    elif category == "risk":
        q["category"] = "risk"
    elif category == "value":
        q["category"] = {"$nin": ["banker", "risk"]}
    if source == "ai":
        q["source"] = "hq-auto"
    elif source == "smart":
        q["source"] = "smart"
    elif source == "members":
        q["source"] = {"$nin": ["hq-auto", "smart"]}
    elif source == "bestwon":
        # "Best Won" bucket (owner): all winning Smart + Risk-single + Community +
        # System picks — the special wins the owner wants to track (esp. systems).
        q["$or"] = [
            {"source": "smart"},
            {"source": "hq-system"},
            {"source": "hq-auto", "category": "risk"},
            {"source": {"$nin": ["hq-auto", "smart", "hq-live", "hq-system"]}},
        ]
        q["id"] = {"$not": {"$regex": "^seed-"}}
    elif source == "normalwon":
        # The plain green "Won" bucket: ordinary AI value/banker singles + live wins.
        # The "best" wins (smart/risk/community/system) live in the Cashed-Out bucket.
        q["$or"] = [
            {"source": "hq-live"},
            {"source": "hq-auto", "category": {"$ne": "risk"}},
        ]
        q["id"] = {"$not": {"$regex": "^seed-"}}
    limit = max(1, min(limit, 1000))
    fetch = 300 if window in ("24", "48", "48plus") else (200 if source == "ai" else limit)
    if sort == "top":
        cursor = db.tips.find(q, {"_id": 0}).sort([("avg_rating", -1), ("ratings_count", -1)]).limit(fetch)
    elif sort == "hype":
        cursor = db.tips.find(q, {"_id": 0}).sort("ai_rating", -1).limit(fetch)
    else:
        cursor = db.tips.find(q, {"_id": 0}).sort("created_at", -1).limit(fetch)
    tips = await cursor.to_list(fetch)
    if window in ("24", "48", "48plus") and status in (None, "pending"):
        now = datetime.now(timezone.utc)
        tips = [t for t in tips if _in_kickoff_window(t.get("match_time"), window, now)]
    # Single AI picks (top area) are ordered by KICKOFF time — next match first —
    # unless the user explicitly sorts by rating/hype.
    if source == "ai" and sort not in ("top", "hype"):
        far = datetime.max.replace(tzinfo=timezone.utc)
        tips.sort(key=lambda t: _kickoff_dt(t.get("match_time")) or far)
    return tips[:limit]


def _in_kickoff_window(match_time: str, window: str, now) -> bool:
    ko = _parse_kickoff(match_time)
    if not ko:
        return True  # no parseable time → always show, never hide a tip
    hours = (ko - now).total_seconds() / 3600
    if window == "24":
        return hours < 24
    if window == "48":
        return 24 <= hours < 48
    return hours >= 48  # "48plus"


@api_router.get("/tips/mine")
async def my_tips(user: dict = Depends(get_current_user)):
    tips = await db.tips.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return tips


@api_router.delete("/tips/{tip_id}")
async def delete_tip(tip_id: str, user: dict = Depends(get_current_user)):
    tip = await db.tips.find_one({"id": tip_id})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    if user.get("role") != "admin" and tip.get("user_id") != user["id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own tips.")
    await db.tips.delete_one({"id": tip_id})
    await db.tip_ratings.delete_many({"tip_id": tip_id})
    return {"deleted": True, "tip_id": tip_id}


@api_router.post("/tips/{tip_id}/rate")
async def rate_tip(tip_id: str, inp: RateInput, user: dict = Depends(get_current_user)):
    tip = await db.tips.find_one({"id": tip_id})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    now = datetime.now(timezone.utc)

    # A 1-star vote from a trusted rater (admin or highly-rated tipster) purges the tip instantly.
    if inp.stars == 1 and await is_trusted_rater(user):
        await db.tips.delete_one({"id": tip_id})
        await db.tip_ratings.delete_many({"tip_id": tip_id})
        streak = await _bump_rating_streak(user, now)
        return {"deleted": True, "tip_id": tip_id, "streak": streak}

    existing = await db.tip_ratings.find_one({"tip_id": tip_id, "user_id": user["id"]})
    if existing:
        delta = inp.stars - existing["stars"]
        await db.tip_ratings.update_one(
            {"_id": existing["_id"]}, {"$set": {"stars": inp.stars, "updated_at": now.isoformat()}})
        new_sum = tip.get("sum_stars", 0) + delta
        new_count = tip.get("ratings_count", 0)
    else:
        await db.tip_ratings.insert_one({
            "id": str(uuid.uuid4()), "tip_id": tip_id, "user_id": user["id"],
            "stars": inp.stars, "created_at": now.isoformat(),
        })
        new_sum = tip.get("sum_stars", 0) + inp.stars
        new_count = tip.get("ratings_count", 0) + 1
    avg = round(new_sum / new_count, 1) if new_count else 0
    await db.tips.update_one({"id": tip_id},
                             {"$set": {"sum_stars": new_sum, "ratings_count": new_count, "avg_rating": avg}})

    # streak: increment once per day the user rates
    today = now.date().isoformat()
    streak = user.get("streak", 0)
    last = user.get("last_rated_date")
    if last != today:
        yesterday = (now.date() - timedelta(days=1)).isoformat()
        streak = streak + 1 if last == yesterday else 1
        await db.users.update_one({"id": user["id"]},
                                  {"$set": {"last_rated_date": today, "streak": streak},
                                   "$inc": {"ratings_given": 1}})
    elif not existing:
        await db.users.update_one({"id": user["id"]}, {"$inc": {"ratings_given": 1}})

    flame_new = await _maybe_award_apex_flame(user["id"], streak, now)
    fresh = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    return {"tip": fresh, "streak": streak, "your_stars": inp.stars,
            "apex_flame": bool(streak >= APEX_FLAME_STREAK or user.get("apex_flame", False)),
            "apex_flame_new": flame_new}


@api_router.put("/tips/{tip_id}/status")
async def set_status(tip_id: str, inp: StatusInput, user: dict = Depends(get_current_user)):
    if inp.status not in ("won", "lost", "pending", "live", "cashed_out", "void"):
        raise HTTPException(status_code=400, detail="Invalid status")
    tip = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    is_admin = user.get("role") == "admin"
    is_owner = tip.get("user_id") == user["id"]
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="You can only settle your own slips.")
    upd = {"status": inp.status}
    if inp.status in ("won", "lost", "cashed_out"):
        upd["settled_at"] = datetime.now(timezone.utc).isoformat()
        upd["settled_by"] = "admin" if is_admin else "owner"
    await db.tips.update_one({"id": tip_id}, {"$set": upd})
    return await db.tips.find_one({"id": tip_id}, {"_id": 0})


# ------------------------------------------------------------------ leaderboard
@api_router.get("/leaderboard")
async def leaderboard():
    pipeline = [
        {"$group": {
            "_id": "$user_id",
            "username": {"$first": "$username"},
            "total": {"$sum": 1},
            "won": {"$sum": {"$cond": [{"$in": ["$status", ["won", "cashed_out"]]}, 1, 0]}},
            "avg_ai": {"$avg": "$ai_rating"},
        }},
        {"$sort": {"won": -1, "total": -1}},
        {"$limit": 10},
    ]
    rows = await db.tips.aggregate(pipeline).to_list(10)
    out = []
    for r in rows:
        total, won = r.get("total", 0), r.get("won", 0)
        out.append({
            "user_id": r["_id"], "username": r.get("username", "anon"),
            "total_tips": total, "won": won,
            "win_rate": round((won / total) * 100) if total else 0,
            "avg_ai_rating": round(r.get("avg_ai") or 0, 1),
        })
    return out


# ------------------------------------------------------------------ credits
@api_router.get("/credits/packages")
async def packages():
    return CREDIT_PACKAGES


@api_router.post("/credits/checkout")
async def credits_checkout(inp: CheckoutInput, request: Request, user: dict = Depends(get_current_user)):
    if inp.package_id not in CREDIT_PACKAGES:
        raise HTTPException(status_code=400, detail="Invalid package")
    pkg = CREDIT_PACKAGES[inp.package_id]
    host_url = str(request.base_url)
    webhook_url = f"{host_url}api/webhook/stripe"
    stripe = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)
    origin = inp.origin_url.rstrip("/")
    success_url = f"{origin}/credits/success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/?checkout=cancelled"
    metadata = {"user_id": user["id"], "package_id": inp.package_id, "credits": str(pkg["credits"])}
    req = CheckoutSessionRequest(amount=float(pkg["price"]), currency=CREDIT_CURRENCY,
                                 success_url=success_url, cancel_url=cancel_url, metadata=metadata)
    session: CheckoutSessionResponse = await stripe.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "package_id": inp.package_id,
        "credits": pkg["credits"],
        "amount": float(pkg["price"]),
        "currency": CREDIT_CURRENCY,
        "payment_status": "initiated",
        "status": "initiated",
        "credited": False,
        "metadata": metadata,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/credits/checkout/status/{session_id}")
async def checkout_status(session_id: str, request: Request, user: dict = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one({"session_id": session_id})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    host_url = str(request.base_url)
    stripe = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}api/webhook/stripe")
    status: CheckoutStatusResponse = await stripe.get_checkout_status(session_id)
    update = {"payment_status": status.payment_status, "status": status.status}
    await db.payment_transactions.update_one({"session_id": session_id}, {"$set": update})
    if status.payment_status == "paid" and not txn.get("credited"):
        await db.payment_transactions.update_one({"session_id": session_id}, {"$set": {"credited": True}})
        await db.users.update_one({"id": txn["user_id"]}, {"$inc": {"credits": txn["credits"]}})
        await db.credit_transactions.insert_one({
            "id": str(uuid.uuid4()), "type": "buy", "to_user": txn["user_id"],
            "amount": txn["credits"], "created_at": datetime.now(timezone.utc).isoformat(),
        })
    fresh = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"payment_status": status.payment_status, "status": status.status,
            "credited": status.payment_status == "paid", "user": public_user(fresh)}


@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature")
    host_url = str(request.base_url)
    stripe = StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=f"{host_url}api/webhook/stripe")
    try:
        event = await stripe.handle_webhook(body, sig)
    except Exception as e:
        logger.error(f"webhook error: {e}")
        raise HTTPException(status_code=400, detail="Invalid webhook")
    if event.payment_status == "paid":
        txn = await db.payment_transactions.find_one({"session_id": event.session_id})
        if txn and not txn.get("credited"):
            await db.payment_transactions.update_one(
                {"session_id": event.session_id},
                {"$set": {"credited": True, "payment_status": "paid", "status": "complete"}})
            await db.users.update_one({"id": txn["user_id"]}, {"$inc": {"credits": txn["credits"]}})
    return {"received": True}


@api_router.post("/credits/gift")
async def gift_credits(inp: GiftInput, user: dict = Depends(get_current_user)):
    if inp.to_username == user["username"]:
        raise HTTPException(status_code=400, detail="You cannot gift yourself")
    sender = await db.users.find_one({"id": user["id"]})
    if sender.get("credits", 0) < inp.amount:
        raise HTTPException(status_code=400, detail="Not enough credits")
    receiver = await db.users.find_one({"username": inp.to_username})
    if not receiver:
        raise HTTPException(status_code=404, detail="Recipient not found")
    fee = int(round(inp.amount * GIFT_FEE))
    received = inp.amount - fee
    await db.users.update_one({"id": sender["id"]}, {"$inc": {"credits": -inp.amount}})
    await db.users.update_one({"id": receiver["id"]},
                              {"$inc": {"credits": received, "received_credits": received}})
    await db.credit_transactions.insert_one({
        "id": str(uuid.uuid4()), "type": "gift", "from_user": sender["id"], "from_username": sender["username"],
        "to_user": receiver["id"], "to_username": receiver["username"], "amount": inp.amount,
        "received": received, "fee": fee, "created_at": datetime.now(timezone.utc).isoformat(),
    })
    fresh = await db.users.find_one({"id": sender["id"]}, {"_id": 0})
    return {"user": public_user(fresh), "received": received, "fee": fee}


@api_router.post("/credits/redeem")
async def redeem(user: dict = Depends(get_current_user)):
    fresh = await db.users.find_one({"id": user["id"]})
    rc = fresh.get("received_credits", 0)
    if rc < REDEEM_THRESHOLD:
        raise HTTPException(status_code=400,
                            detail=f"You need {REDEEM_THRESHOLD} received credits to redeem")
    payout = round((rc / 1000.0) * REDEEM_EUR_PER_1000, 2)
    await db.users.update_one({"id": user["id"]}, {"$set": {"received_credits": 0}})
    redemption = {
        "id": str(uuid.uuid4()), "user_id": user["id"], "username": fresh["username"],
        "credits": rc, "amount_eur": payout, "currency": "eur", "status": "requested",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.redemptions.insert_one(redemption)
    redemption.pop("_id", None)
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"redemption": redemption, "user": public_user(updated)}


@api_router.get("/credits/transactions")
async def credit_txns(user: dict = Depends(get_current_user)):
    txns = await db.credit_transactions.find(
        {"$or": [{"from_user": user["id"]}, {"to_user": user["id"]}]}, {"_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    return txns


# ------------------------------------------------------------------ earn credits: win claims
WIN_MIN_PLAYED_LEGS = 3          # a played-along slip must have >= 3 legs (TipJar systems can be 3-leg)
WIN_MIN_SYSTEM_MATCH = 3         # >= 3 legs must match a TipJar system (anti-fraud)
WIN_LIVE_MIN_LEGS = 4            # live streak: 4 in a row
WIN_LIVE_MIN_ODDS = 1.60         # each live leg must be > 1.60
WIN_POSTED_CREDITS = 20
WIN_LIVE_CREDITS = 20
WIN_CASHED_CREDITS = 20
WIN_MAX_CREDITS = 20             # cap per claim


async def extract_win_slip(image_b64: str) -> dict:
    """Gemini Vision: read a bookmaker bet-slip screenshot into structured JSON."""
    fallback = {"status": "unknown", "total_odds": 0, "stake": "", "winnings": "", "legs": []}
    if not EMERGENT_LLM_KEY or not image_b64:
        return fallback
    try:
        chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"win-{uuid.uuid4()}",
                       system_message=("You read betting bet-slip screenshots and output STRICT JSON only. "
                                       "Never invent legs that are not visible.")).with_model(AI_MODEL_PROVIDER, AI_MODEL)
        prompt = (
            "Read this bet-slip screenshot. Return STRICT JSON: "
            '{"status":"won|lost|open|cashed","total_odds":<number>,"stake":"","winnings":"",'
            '"legs":[{"home":"","away":"","league":"","date":"","time":"","market":"","odds":<number>,"result":"won|lost|open"}]}. '
            "status is the overall slip result. If the slip shows 'Cashed Out' / 'Cash Out' / 'Ausgezahlt' / "
            "'Auszahlung' anywhere (it means the bettor took an early payout), set status to 'cashed' and put "
            "the paid-out amount into 'winnings' (e.g. '41,61 €'). "
            "Extract every leg. If a value is missing use empty/0. "
            "For EACH leg also read: 'league' = the competition/league name if shown (e.g. 'Champions-League-Quali', 'Premier League'); "
            "'date' = the match date if shown (keep as printed, e.g. '07/07' or '07.07.'); "
            "'time' = the kickoff time if shown (e.g. '21:00'). Leave these empty if not visible on the slip. "
            "IMPORTANT market naming — always in GERMAN, always spell the word 'Über' or 'Unter': "
            "goals over/under => 'Über 2.5 Tore' / 'Unter 3.5 Tore'; "
            "TEAM total goals => include the team name, e.g. 'Víkingur Über 0.5 Tore', 'Marokko Unter 2.5 Tore'; "
            "player shots on target => '<Spieler> Über 0.5 Torschüsse' (e.g. 'Mbappé Über 0.5 Torschüsse'); "
            "HANDICAP: a leg shown as a team name followed only by a number (e.g. 'Sutjeska 3.5', "
            "\"Connah's Quay Nomads 2.5\") is a HANDICAP on that team — output it as "
            "'<Team> Handicap +X.5' (the team gets a +X.5 head-start; use '-X.5' if the favourite "
            "gives a start). A bare team+number is ALWAYS a handicap, never a goals line; only "
            "'Total OVER/UNDER x.5' is a goals line (=> 'Über/Unter x.5 Tore'). "
            "double chance => '1X' or 'X2'; both teams to score => 'Beide Teams treffen'. "
            "Keep 'home' and 'away' as the two teams of the match the leg belongs to."
        )
        resp = await chat.send_message(UserMessage(text=prompt, file_contents=[ImageContent(image_base64=image_b64)]))
        raw = (resp if isinstance(resp, str) else str(resp)).strip()
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1]
            if raw.lstrip().startswith("json"):
                raw = raw.lstrip()[4:]
        s, e = raw.find("{"), raw.rfind("}")
        if s == -1 or e == -1:
            return fallback
        data = json.loads(raw[s:e + 1])
        legs = []
        for lg in (data.get("legs") or [])[:20]:
            try:
                od = float(lg.get("odds") or 0)
            except Exception:
                od = 0.0
            legs.append({"home": str(lg.get("home", "") or ""), "away": str(lg.get("away", "") or ""),
                         "league": str(lg.get("league", "") or ""), "date": str(lg.get("date", "") or ""),
                         "time": str(lg.get("time", "") or ""),
                         "market": str(lg.get("market", "") or ""), "odds": od,
                         "result": str(lg.get("result", "") or "").lower()})
        try:
            total = float(data.get("total_odds") or 0)
        except Exception:
            total = 0.0
        return {"status": str(data.get("status", "") or "").lower(), "total_odds": round(total, 2),
                "stake": str(data.get("stake", "") or ""), "winnings": str(data.get("winnings", "") or ""),
                "legs": legs}
    except Exception as ex:
        logger.error(f"win slip extract failed: {ex}")
        return fallback


async def _system_match_keys() -> set:
    """Match keys of every TipJar pick a user could have played — PERSISTENT.
    Claims arrive AFTER matches finish, so we must include finished picks too:
    current systems + all posted tips (any status) + their parlay legs."""
    keys = set()
    try:
        data = await build_systems()
        for sysd in data.get("systems", []):
            for sel in sysd.get("selections", []):
                keys.add(_match_key(sel.get("home_team"), sel.get("away_team")))
    except Exception:
        pass
    tips = await db.tips.find({}, {"_id": 0, "home_team": 1, "away_team": 1, "legs": 1}).to_list(4000)
    for t in tips:
        if t.get("home_team") and t.get("away_team"):
            keys.add(_match_key(t["home_team"], t["away_team"]))
        for lg in (t.get("legs") or []):
            m = lg.get("match") or ""
            parts = re.split(r"\s[–—\-]\s", m, maxsplit=1)
            if len(parts) == 2:
                keys.add(_match_key(parts[0], parts[1]))
    return keys


def _fmt_selection(sel: str) -> str:
    """Mirror of the frontend formatSelection: clean bookmaker raw text into proper labels."""
    s = (sel or "").strip()
    if not s:
        return s
    m = re.match(r"^total\s+(?:over|über|ueber)\s+(\d+(?:[.,]\d+)?)", s, re.I)
    if m:
        return f"Über {m.group(1).replace(',', '.')} Tore"
    m = re.match(r"^total\s+(?:under|unter)\s+(\d+(?:[.,]\d+)?)", s, re.I)
    if m:
        return f"Unter {m.group(1).replace(',', '.')} Tore"
    if re.search(r"handicap|über|unter|\btore\b|torsch|chance|treffen|draw no bet|ergebnis|btts|\bover\b|\bunder\b", s, re.I):
        return s
    m = re.match(r"^(.+?)\s([+-]?\d+(?:[.,]\d+)?)$", s)
    if m:
        n = m.group(2).replace(",", ".")
        if not n.startswith(("+", "-")):
            n = "+" + n
        return f"{m.group(1).strip()} Handicap {n}"
    return s


def _to_float(v) -> float:
    try:
        return float(str(v or "0").replace(",", ".").replace("€", "").strip())
    except Exception:
        return 0.0


def _split_match(match: str):
    parts = re.split(r"\s[–-]\s|\svs\.?\s", match or "", maxsplit=1)
    home = parts[0].strip() if parts else (match or "")
    away = parts[1].strip() if len(parts) > 1 else ""
    return home, away


def _tip_to_render_legs(tip: dict) -> list:
    """Convert a stored member tip into _render_slip_image legs (one per selection)."""
    rlegs = []
    for lg in (tip.get("legs") or []):
        home, away = _split_match(lg.get("match") or "")
        sels = lg.get("selections") or []
        sodds = lg.get("sel_odds") or []
        for i, sel in enumerate(sels):
            od = _to_float(sodds[i]) if i < len(sodds) else 0.0
            rlegs.append({"home": home, "away": away, "market": _fmt_selection(sel),
                          "odds": od, "result": "open",
                          "league": lg.get("league", ""), "date": "", "time": lg.get("kickoff", "")})
    if not rlegs:
        rlegs.append({"home": tip.get("home_team", ""), "away": tip.get("away_team", ""),
                      "market": _fmt_selection(tip.get("market", "")), "odds": _to_float(tip.get("odds")),
                      "result": "open", "league": tip.get("league", ""), "date": "",
                      "time": tip.get("match_time", "")})
    return rlegs


def _render_slip_image(legs, total_odds, stake, winnings, username, ctype, live_info=None) -> bytes:
    """Render a standardised, TipJar-branded bet slip from the extracted data — so we
    NEVER show a random bookmaker screenshot, only our own elegant black-green TipJar
    slip. live_info={'minute':int,'score':'1:0'} shows a LIVE badge for in-play tips."""
    from PIL import Image, ImageDraw, ImageFont
    import io
    FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
    FR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    CREST = "/app/frontend/public/tipjar-crest.png"

    def font(path, sz):
        try:
            return ImageFont.truetype(path, sz)
        except Exception:
            return ImageFont.load_default()
    f_logo = font(FB, 92)
    f_tag = font(FR, 38)
    f_badge = font(FB, 56)
    f_match = font(FB, 72)
    f_sub = font(FR, 44)
    f_live = font(FB, 48)
    f_market = font(FR, 62)
    f_odds = font(FB, 64)
    f_big = font(FB, 96)
    f_label = font(FB, 62)
    f_lbl = font(FR, 46)
    f_user = font(FB, 54)
    f_win = font(FB, 58)
    _scratch = ImageDraw.Draw(Image.new("RGB", (4, 4)))

    def fit_font(txt, hi, lo, maxw):
        for sz in range(hi, lo - 1, -2):
            f = font(FB, sz)
            if _scratch.textlength(txt, font=f) <= maxw:
                return f, sz
        return font(FB, lo), lo
    W, pad, head_h, foot_h = 1080, 60, 212, 344
    won = ctype not in ("pending", "live_pending")
    has_live = bool(live_info)
    legs = legs[:10]
    # group legs by match so the same fixture is only titled ONCE
    groups, gidx = [], {}
    for l in legs:
        k = _match_key(l.get("home", ""), l.get("away", ""))
        if k not in gidx:
            gidx[k] = len(groups)
            groups.append({"home": l.get("home", "?"), "away": l.get("away", "?"),
                           "league": l.get("league", ""), "date": l.get("date", ""),
                           "time": l.get("time", ""), "mkts": []})
        groups[gidx[k]]["mkts"].append(l)

    def _subline(g):
        parts = [p for p in (g.get("league", ""), g.get("date", ""), g.get("time", "")) if p]
        return "   ·   ".join(parts)
    # Team names must be FULLY visible: shrink the title to fit on one line, and if
    # it still won't fit, wrap to two lines (home / vs away) — never truncate.
    _tmaxw = W - 2 * pad
    for g in groups:
        title = f"{g['home']}  vs  {g['away']}"
        tf, _ = fit_font(title, 72, 42, _tmaxw)
        if _scratch.textlength(title, font=tf) <= _tmaxw:
            g["tlines"] = [(title, tf, 72)]
        else:
            f1, s1 = fit_font(g["home"], 64, 34, _tmaxw)
            f2, s2 = fit_font(f"vs {g['away']}", 64, 34, _tmaxw)
            g["tlines"] = [(g["home"], f1, s1), (f"vs {g['away']}", f2, s2)]
        g["hdr_h"] = sum(sz + 16 for _, _, sz in g["tlines"])
    mrow_h, gap, sub_h, live_h = 76, 22, 46, 76
    H = head_h + (live_h if has_live else 0) + sum(
        g["hdr_h"] + (sub_h if _subline(g) else 0) + len(g["mkts"]) * mrow_h + gap
        for g in groups) + foot_h
    VOID, CARD, GREEN = (9, 9, 11), (22, 23, 27), (46, 204, 87)
    WHITE, GREY, LINE = (244, 244, 246), (156, 158, 164), (40, 42, 48)
    VOLT, LIVE_RED = (225, 255, 0), (240, 68, 60)
    ACCENT = GREEN if won else VOLT
    img = Image.new("RGB", (W, H), VOID)
    d = ImageDraw.Draw(img)

    # subtle TipJar crest watermark — capped so it never clips the canvas
    try:
        crest = Image.open(CREST).convert("RGBA")
        cw = int(W * 0.58)
        ch = int(cw * crest.height / crest.width)
        maxh = int(H * 0.46)
        if ch > maxh:
            ch = maxh
            cw = int(ch * crest.width / crest.height)
        crest = crest.resize((cw, ch))
        crest.putalpha(crest.split()[3].point(lambda a: int(a * 0.06)))
        img.paste(crest, ((W - cw) // 2, (H - ch) // 2), crest)
    except Exception:
        pass

    def trunc(txt, fnt, maxw):
        txt = txt or ""
        if d.textlength(txt, font=fnt) <= maxw:
            return txt
        while txt and d.textlength(txt + "…", font=fnt) > maxw:
            txt = txt[:-1]
        return txt + "…"

    def check(cx, cy, sz, col):
        d.line([(cx, cy), (cx + sz * 0.32, cy + sz * 0.42)], fill=col, width=7)
        d.line([(cx + sz * 0.32, cy + sz * 0.42), (cx + sz, cy - sz * 0.5)], fill=col, width=7)
    # header: TipJar logo (Tip white / Jar green) + tagline
    d.text((pad, 34), "Tip", font=f_logo, fill=WHITE)
    tw = d.textlength("Tip", font=f_logo)
    d.text((pad + tw, 34), "Jar", font=f_logo, fill=GREEN)
    d.text((pad + 4, 138), "Post it. Rate it. Cash it.", font=f_tag, fill=GREY)
    badge = "WON" if won else "OFFEN"
    bw = d.textlength(badge, font=f_badge)
    bx0 = W - pad - bw - (92 if won else 52)
    d.rounded_rectangle([bx0, 40, W - pad, 122], 20, fill=ACCENT)
    tx = bx0 + 26
    if won:
        check(bx0 + 24, 84, 24, VOID)
        tx = bx0 + 66
    d.text((tx, 58), badge, font=f_badge, fill=VOID)
    # area pill (which channel the slip comes from)
    area = {"pending": "COMMUNITY PICK", "live_pending": "LIVE PICK"}.get(ctype)
    if area:
        aw = d.textlength(area, font=f_tag)
        ax0 = W - pad - aw - 40
        d.rounded_rectangle([ax0, 134, W - pad, 186], 16, outline=ACCENT, width=3)
        d.text((ax0 + 20, 142), area, font=f_tag, fill=ACCENT)
    d.line([pad, head_h - 20, W - pad, head_h - 20], fill=LINE, width=3)
    # legs grouped by match
    y = head_h
    for g in groups:
        ty = y + 6
        for txt, tfont, tsz in g["tlines"]:
            d.text((pad, ty), txt, font=tfont, fill=WHITE)
            ty += tsz + 16
        y += g["hdr_h"]
        if has_live:
            mn, sc = live_info.get("minute"), live_info.get("score")
            lt = "LIVE"
            if mn:
                lt += f"  {mn}'"
            if sc:
                lt += f"   ·   {sc}"
            lw = d.textlength(lt, font=f_live)
            d.rounded_rectangle([pad, y - 6, pad + lw + 84, y + 62], 18, fill=LIVE_RED)
            d.ellipse([pad + 26, y + 18, pad + 50, y + 42], fill=WHITE)
            d.text((pad + 66, y + 4), lt, font=f_live, fill=WHITE)
            y += live_h
            has_live = False  # only under the first match
        sub = _subline(g)
        if sub:
            d.text((pad, y - 4), trunc(sub, f_sub, W - 2 * pad), font=f_sub, fill=GREY)
            y += sub_h
        for l in g["mkts"]:
            od = l.get("odds") or 0
            odt = f"{od:.2f}" if od else ("gewonnen" if won else "offen")
            ow = d.textlength(odt, font=f_odds)
            mkx = pad + 28
            d.text((mkx, y + 6), trunc(l.get("market", "") or "", f_market, W - pad - mkx - ow - 72), font=f_market, fill=(214, 216, 220))
            d.text((W - pad - ow, y + 2), odt, font=f_odds, fill=ACCENT)
            if won:
                check(W - pad - ow - 52, y + 30, 24, GREEN)
            y += mrow_h
        d.line([pad, y + 2, W - pad, y + 2], fill=LINE, width=2)
        y += gap
    # footer card
    fy = y + 20
    d.rounded_rectangle([pad, fy, W - pad, H - 34], 28, fill=CARD)
    label = {"played": "Mitgespielt", "posted": "Reingepostet", "live": "Live-Serie",
             "cashed": "Ausgezahlt",
             "live_pending": "Live-Pick", "pending": "Community-Tipp"}.get(ctype, "Gewonnen")
    d.text((pad + 40, fy + 30), label, font=f_label, fill=ACCENT)
    d.text((pad + 40, fy + 108), "Gesamtquote", font=f_lbl, fill=GREY)
    ot = f"{total_odds:.2f}" if total_odds else "—"
    otw = d.textlength(ot, font=f_big)
    d.rounded_rectangle([W - pad - otw - 76, fy + 26, W - pad - 40, fy + 140], 20, fill=ACCENT)
    d.text((W - pad - otw - 58, fy + 34), ot, font=f_big, fill=VOID)
    d.text((pad + 40, fy + 160), f"@{username}", font=f_user, fill=WHITE)
    if stake:
        stt = f"Einsatz: {stake}"
        d.text((W - pad - d.textlength(stt, font=f_lbl) - 40, fy + 166), stt, font=f_lbl, fill=GREY)
    if winnings:
        wt = (f"Ausgezahlt: {winnings}" if ctype == "cashed" else f"Gewinn: {winnings}") if won else f"Möglicher Gewinn: {winnings}"
        d.text((pad + 40, fy + 224), wt, font=f_win, fill=ACCENT)
    out = io.BytesIO()
    img.save(out, format="WEBP", quality=90)
    return out.getvalue()


@api_router.post("/wins/claim")
async def claim_win(file: Optional[UploadFile] = File(None),
                    files: Optional[List[UploadFile]] = File(None),
                    type: str = Form(...),
                    user: dict = Depends(get_current_user)):
    ctype = (type or "").strip().lower()
    if ctype not in ("played", "posted", "live", "cashed"):
        raise HTTPException(status_code=400, detail="Invalid claim type")
    # gather uploaded images (live can be up to 4 separate screenshots)
    imgs_raw = []
    for f in (files or []):
        if f:
            b = await f.read()
            if b:
                imgs_raw.append(b)
    if file:
        b = await file.read()
        if b:
            imgs_raw.append(b)
    if not imgs_raw:
        raise HTTPException(status_code=400, detail="No file uploaded")

    if ctype == "live":
        legs = []
        for b in imgs_raw:
            s = await extract_win_slip(base64.b64encode(b).decode("utf-8"))
            if s["status"] != "won":
                raise HTTPException(status_code=422, detail="Jeder Live-Schein muss GEWONNEN sein.")
            legs.extend(s["legs"])
        legs_n = len(legs)
        if legs_n < WIN_LIVE_MIN_LEGS:
            raise HTTPException(status_code=422, detail=f"Live-Serie braucht mind. {WIN_LIVE_MIN_LEGS} gewonnene Live-Wetten (lade z.B. 4 Bilder hoch).")
        if any((l["odds"] or 0) <= WIN_LIVE_MIN_ODDS for l in legs):
            raise HTTPException(status_code=422, detail=f"Jede Live-Auswahl muss Quote > {WIN_LIVE_MIN_ODDS} haben.")
        import math
        odds_list = [l["odds"] for l in legs if l["odds"]]
        total_odds = round(math.prod(odds_list), 2) if odds_list else 0.0
        stake, winnings = "", ""
        credits, matched = WIN_LIVE_CREDITS, legs_n
    elif ctype == "cashed":
        # Cashed-out slip: the bettor took an early payout. It's their own trophy,
        # so we DON'T require it to match a TipJar system — just that it was cashed out.
        raw = imgs_raw[0]
        slip = await extract_win_slip(base64.b64encode(raw).decode("utf-8"))
        if slip["status"] not in ("cashed", "won"):
            raise HTTPException(status_code=422,
                                detail="Kein ausgezahlter Schein erkannt. Lade einen 'Cashed Out'/'Ausgezahlt'-Schein hoch.")
        legs = slip["legs"]
        legs_n = len(legs)
        if legs_n < 2:
            raise HTTPException(status_code=422, detail="Kein gültiger Kombi-Schein erkannt.")
        matched = legs_n
        credits = WIN_CASHED_CREDITS
        total_odds, stake, winnings = slip["total_odds"], slip["stake"], slip["winnings"]
    else:
        raw = imgs_raw[0]
        slip = await extract_win_slip(base64.b64encode(raw).decode("utf-8"))
        if slip["status"] not in ("won", "cashed"):
            raise HTTPException(status_code=422, detail="Nur gewonnene oder ausgezahlte Scheine zählen.")
        legs = slip["legs"]
        legs_n = len(legs)
        if legs_n < 2:
            raise HTTPException(status_code=422, detail="Kein gültiger Kombi-Schein erkannt.")
        # A cashed-out slip counts as a win trophy — no TipJar-system match required.
        if slip["status"] == "cashed":
            ctype = "cashed"
            matched = legs_n
            credits = WIN_CASHED_CREDITS
            total_odds, stake, winnings = slip["total_odds"], slip["stake"], slip["winnings"]
        else:
            sys_keys = await _system_match_keys()
            matched = sum(1 for l in legs if _match_key(l["home"], l["away"]) in sys_keys)
            if matched < WIN_MIN_SYSTEM_MATCH:
                raise HTTPException(status_code=422,
                                    detail="Das zählt nicht als mitgespielt — der Schein passt zu keinem TipJar-System.")
            if ctype == "played":
                if legs_n < WIN_MIN_PLAYED_LEGS:
                    raise HTTPException(status_code=422, detail=f"Mitgespielter Schein braucht mind. {WIN_MIN_PLAYED_LEGS} Legs.")
                credits = min(WIN_MAX_CREDITS, WIN_MIN_PLAYED_LEGS + (legs_n - WIN_MIN_PLAYED_LEGS))
            else:  # posted
                credits = WIN_POSTED_CREDITS
            total_odds, stake, winnings = slip["total_odds"], slip["stake"], slip["winnings"]

    # anti-duplicate: the same set of legs can't be claimed twice
    sig = hashlib.md5(("|".join(sorted(f"{l['home']}-{l['away']}-{l['market']}" for l in legs))
                       + f"|{total_odds}").encode()).hexdigest()
    if await db.win_claims.find_one({"sig": sig}):
        raise HTTPException(status_code=409, detail="Dieser Schein wurde bereits eingereicht.")

    # store a STANDARDISED TipJar-branded slip (never the raw bookmaker screenshot)
    ext, store_ct = "webp", "image/webp"
    store_bytes = _render_slip_image(legs, total_odds, stake, winnings, user["username"], ctype)
    image_path = None
    try:
        result = put_object(f"{APP_NAME}/wins/{user['id']}/{uuid.uuid4()}.{ext}", store_bytes, store_ct)
        image_path = result["path"]
        await db.files.insert_one({
            "id": str(uuid.uuid4()), "storage_path": image_path,
            "original_filename": f"tipjar-slip.{ext}", "content_type": store_ct,
            "owner": user["id"], "is_deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as ex:
        logger.error(f"win image upload failed: {ex}")

    claim = {
        "id": str(uuid.uuid4()), "sig": sig, "user_id": user["id"], "username": user["username"],
        "type": ctype, "image_path": image_path, "legs": legs, "legs_count": legs_n,
        "matched_legs": matched, "total_odds": total_odds, "stake": stake,
        "winnings": winnings, "credits": credits, "status": "approved",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.win_claims.insert_one(claim)
    await db.users.update_one({"id": user["id"]}, {"$inc": {"received_credits": credits}})
    claim.pop("_id", None)
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"claim": claim, "credits_awarded": credits, "user": public_user(updated)}


@api_router.get("/wins/hall-of-fame")
async def hall_of_fame():
    docs = await db.win_claims.find(
        {"status": "approved"}, {"_id": 0, "sig": 0, "user_id": 0}
    ).sort("total_odds", -1).limit(24).to_list(24)
    # Cashed-out slips are trophies too — surface them in the Hall of Fame.
    cashed = await db.tips.find(
        {"status": "cashed_out"}, {"_id": 0}
    ).sort("settled_at", -1).limit(24).to_list(24)
    for tp in cashed:
        docs.append({
            "id": tp["id"], "type": "cashed", "username": tp.get("username", "anon"),
            "total_odds": _to_float(tp.get("odds")),
            "winnings": tp.get("winnings") or tp.get("potential_return") or "",
            "legs_count": len(tp.get("legs") or []) or 1,
            "image_path": tp.get("image_path"),
            "created_at": tp.get("settled_at") or tp.get("created_at"),
        })
    return docs


@api_router.get("/wins/mine")
async def my_wins(user: dict = Depends(get_current_user)):
    docs = await db.win_claims.find(
        {"user_id": user["id"]}, {"_id": 0, "sig": 0, "user_id": 0}
    ).sort("created_at", -1).limit(50).to_list(50)
    total = sum(d.get("credits", 0) for d in docs)
    return {"claims": docs, "total_credits": total, "count": len(docs)}



# ------------------------------------------------------------------ notifications (no signup)
@api_router.post("/notifications/subscribe")
async def subscribe(inp: SubscribeInput):
    await db.subscribers.update_one(
        {"anon_id": inp.anon_id},
        {"$set": {"anon_id": inp.anon_id, "updated_at": datetime.now(timezone.utc).isoformat()},
         "$setOnInsert": {"created_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True)
    count = await db.subscribers.count_documents({})
    return {"subscribed": True, "subscriber_count": count + _sub_boost()}


@api_router.post("/notifications/unsubscribe")
async def unsubscribe(inp: SubscribeInput):
    await db.subscribers.delete_one({"anon_id": inp.anon_id})
    count = await db.subscribers.count_documents({})
    return {"subscribed": False, "subscriber_count": count + _sub_boost()}


@api_router.get("/stats")
async def community_stats():
    members = await db.users.count_documents({"role": {"$ne": "admin"}})
    subs = await db.subscribers.count_documents({})
    tips = await db.tips.count_documents({})
    return {"members": members + _member_boost(), "goal": 1000, "subscribers": subs + _sub_boost(), "total_tips": tips}


@api_router.get("/notifications/stats")
async def notif_stats():
    count = await db.subscribers.count_documents({})
    total = await db.tips.count_documents({})
    return {"subscriber_count": count + _sub_boost(), "total_tips": total}


@api_router.post("/track/visit")
async def track_visit(inp: VisitInput):
    """Anonymous, cookieless visit ping (visitor_id is a random localStorage id).
    Deduped per visitor per day so we can report both hits and unique visitors."""
    vid = (inp.visitor_id or "").strip()[:64]
    if not vid:
        return {"ok": True}
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    await db.visits.update_one(
        {"visitor_id": vid, "day": day},
        {"$inc": {"hits": 1},
         "$set": {"last_ts": now.isoformat(), "path": (inp.path or "")[:120]},
         "$setOnInsert": {"first_ts": now.isoformat()}},
        upsert=True,
    )
    return {"ok": True}


@api_router.get("/admin/visits")
async def admin_visits(admin: dict = Depends(require_admin)):
    """Private analytics — admin only. Never exposed publicly."""
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    days = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
    daily = []
    for d in days:
        docs = await db.visits.find({"day": d}, {"_id": 0, "hits": 1}).to_list(100000)
        daily.append({"day": d, "unique": len(docs), "hits": sum(x.get("hits", 0) for x in docs)})
    total_unique = len(await db.visits.distinct("visitor_id"))
    all_docs = await db.visits.find({}, {"_id": 0, "hits": 1}).to_list(200000)
    total_hits = sum(x.get("hits", 0) for x in all_docs)
    today_row = next((x for x in daily if x["day"] == today), {"unique": 0, "hits": 0})
    week = daily[-7:]
    members = await db.users.count_documents({"role": {"$ne": "admin"}})
    subs = await db.subscribers.count_documents({})
    return {
        "total_unique": total_unique, "total_hits": total_hits,
        "today_unique": today_row["unique"], "today_hits": today_row["hits"],
        "week_unique": sum(x["unique"] for x in week), "week_hits": sum(x["hits"] for x in week),
        "daily": daily, "members": members, "subscribers": subs,
    }


@api_router.get("/admin/pending-tips")
async def admin_pending_tips(admin: dict = Depends(require_admin)):
    """All open tips (pending/live) grouped by source — for the admin pick-manager."""
    docs = await db.tips.find(
        {"status": {"$in": ["pending", "live"]}},
        {"_id": 0, "id": 1, "source": 1, "status": 1, "market": 1, "match": 1,
         "home_team": 1, "away_team": 1, "match_time": 1, "kickoff": 1, "odds": 1,
         "win_prob": 1, "ai_rating": 1, "is_parlay": 1, "combo_legs": 1,
         "report": 1, "settle_attempts": 1, "created_at": 1},
    ).sort("created_at", -1).to_list(500)

    def _label(t):
        m = t.get("match")
        if m:
            return m
        h, a = t.get("home_team"), t.get("away_team")
        return f"{h} — {a}" if (h or a) else (t.get("market") or "—")

    src_names = {
        "hq-auto": "KI-Picks", "hq-live": "Live-Picks", "smart": "Smart Picks",
    }
    items = []
    for t in docs:
        src = t.get("source") or "member"
        items.append({
            **t,
            "label": _label(t),
            "source_name": src_names.get(src, "Mitglieder-Tipps"),
        })
    return {"count": len(items), "items": items}


@api_router.get("/admin/settlement-monitor")
async def admin_settlement_monitor(admin: dict = Depends(require_admin)):
    """Owner monitoring: track settlement of System picks (source=hq-system) and
    first-half (HT) bet-builders so we can confirm they auto-resolve in production."""
    def _clean(t):
        legs = t.get("legs") or t.get("combo_legs") or []
        return {
            "id": t.get("id"), "status": t.get("status"),
            "market": t.get("market"), "league": t.get("league"),
            "odds": t.get("odds"), "settled_at": t.get("settled_at"),
            "match_time": t.get("match_time"),
            "legs": [{"match": l.get("match") or "", "sel": l.get("selections") or [l.get("market")],
                      "status": l.get("status")} for l in legs],
        }
    systems = await db.tips.find({"source": "hq-system"}).sort("created_at", -1).to_list(200)
    ht = await db.tips.find(
        {"source": {"$ne": "hq-system"},
         "$or": [{"market": {"$regex": "Halbzeit", "$options": "i"}},
                 {"combo_legs.market": {"$regex": "Halbzeit", "$options": "i"}}]}
    ).sort("created_at", -1).to_list(200)

    def _summary(rows):
        return {"total": len(rows),
                "pending": sum(1 for r in rows if r.get("status") in ("pending", "live")),
                "won": sum(1 for r in rows if r.get("status") == "won"),
                "lost": sum(1 for r in rows if r.get("status") == "lost"),
                "void": sum(1 for r in rows if r.get("status") == "void")}
    return {
        "systems": {"summary": _summary(systems), "items": [_clean(t) for t in systems]},
        "ht_combos": {"summary": _summary(ht), "items": [_clean(t) for t in ht]},
    }



# ------------------------------------------------------------------ Web Push (VAPID)
@api_router.get("/push/vapid-public-key")
async def push_vapid_key():
    return {"publicKey": VAPID_PUBLIC_KEY}


@api_router.post("/push/subscribe")
async def push_subscribe(sub: PushSubIn, request: Request):
    if not sub.endpoint or not sub.keys.get("p256dh") or not sub.keys.get("auth"):
        raise HTTPException(status_code=400, detail="Invalid subscription")
    user = None
    try:
        user = await get_current_user(request)
    except Exception:
        user = None
    now = datetime.now(timezone.utc).isoformat()
    await db.push_subscriptions.update_one(
        {"endpoint": sub.endpoint},
        {"$set": {"endpoint": sub.endpoint, "keys": sub.keys,
                  "user_id": (user or {}).get("id"), "updated_at": now},
         "$setOnInsert": {"created_at": now}},
        upsert=True)
    return {"ok": True, "count": await db.push_subscriptions.count_documents({})}


@api_router.post("/push/unsubscribe")
async def push_unsubscribe(sub: PushSubIn):
    await db.push_subscriptions.delete_one({"endpoint": sub.endpoint})
    return {"ok": True}


def _send_web_push(subscription: dict, payload: dict):
    webpush(
        subscription_info={"endpoint": subscription["endpoint"], "keys": subscription["keys"]},
        data=json.dumps(payload),
        vapid_private_key=VAPID_PRIVATE_KEY,
        vapid_claims={"sub": VAPID_SUBJECT},
        ttl=3600,
    )


async def notify_all_push(payload: dict):
    """Send a Web Push to every stored subscription; prune dead ones (404/410)."""
    if not VAPID_PRIVATE_KEY:
        return 0
    subs = await db.push_subscriptions.find({}, {"_id": 0}).to_list(20000)
    sent = 0
    for s in subs:
        try:
            await asyncio.to_thread(_send_web_push, s, payload)
            sent += 1
        except WebPushException as exc:
            code = getattr(getattr(exc, "response", None), "status_code", None)
            if code in (404, 410):
                await db.push_subscriptions.delete_one({"endpoint": s["endpoint"]})
        except Exception:
            pass
    return sent


def _push_payload_for_tip(tip: dict) -> dict:
    """Build a game/market-detailed push. Live picks get the blue LIVE styling.
    High-impact picks get a punchier title + a richer sound the foreground app
    plays: 10★ → coin+explosion ('explosion'), 9★ → coin+fire ('fire')."""
    home, away = tip.get("home_team") or "", tip.get("away_team") or ""
    match = f"{home} vs {away}" if away else (home or "TipJar")
    market = tip.get("market") or ""
    odds = tip.get("odds")
    detail = f"{match} — {market}" + (f" @ {odds}" if odds else "")
    # Stars mirror the frontend rule: round(win_prob*10), capped 1-10.
    try:
        stars = max(1, min(10, round(float(tip.get("win_prob") or 0) * 10)))
    except Exception:
        stars = 0
    sound = "explosion" if stars >= 10 else ("fire" if stars == 9 else "coin")
    is_live = tip.get("status") == "live" or tip.get("source") == "hq-live"
    pid = tip.get("id")
    src = tip.get("source")
    area = "live" if is_live else ("ai" if src == "hq-auto" else ("smart" if src == "smart" else "members"))
    if is_live:
        # Owner (2026-07-10): live in-play bets are never "impossible to lose" — cap at
        # 7★ and never fire the 9/10★ explosion sound.
        stars = min(stars, 7)
        return {"title": "🔵 LIVE-Pick", "body": detail, "url": f"/?pick={pid}&area=live",
                "kind": "live", "sound": "coin", "pick_id": pid,
                "icon": "/push-live.png", "badge": "/push-live.png", "tag": "tipjar-live"}
    cat = (tip.get("category") or "").lower()
    if src == "hq-auto":
        if cat == "banker" and stars >= 10:
            title = "💥 10-Sterne-Banker!"
        elif cat == "banker" and stars == 9:
            title = "🔥 9-Sterne-Banker!"
        else:
            label = {"banker": "Banker-Pick", "risk": "Risk-Pick"}.get(cat, "Value-Pick")
            title = f"⚽ Neuer {label}"
    elif src == "smart":
        title = "🧠 Neuer Smart-Pick"
    else:
        title = "👥 Neuer Community-Tipp"
    # Fixed tag ('tipjar-pick') so a burst of queued pushes COLLAPSES into one visible
    # notification (newest wins) instead of stacking → no endless-swipe. Deep-link via ?pick=.
    return {"title": title, "body": detail, "url": f"/?pick={pid}&area={area}", "kind": "tip",
            "sound": sound, "pick_id": pid,
            "icon": "/icon-192.png", "badge": "/icon-192.png", "tag": "tipjar-pick"}


def _digest_payload_for_tips(tips: list) -> dict:
    """One bundled push for a batch of fresh picks (no endless-swipe). Fixed tag so it
    replaces any previous digest. Opens the app; the in-app bell lists each pick."""
    n = len(tips)
    live_n = sum(1 for t in tips if t.get("status") == "live" or t.get("source") == "hq-live")
    def _short(t):
        h, a = t.get("home_team") or "", t.get("away_team") or ""
        return f"{h} vs {a}" if a else (t.get("market") or h or "Pick")
    names = [_short(t) for t in tips[:3]]
    body = " · ".join(names) + (f" +{n - 3} mehr" if n > 3 else "")
    title = f"⚡ {n} neue Picks" + (f" ({live_n}× 🔵 LIVE)" if live_n else "")
    return {"title": title, "body": body, "url": "/", "kind": "digest", "sound": "coin",
            "icon": "/icon-192.png", "badge": "/icon-192.png", "tag": "tipjar-pick"}


async def push_watch_loop():
    """Watch for freshly-created tips (any source) and fire a Web Push with the
    game + market details. Live picks use the blue LIVE popup. On first run we set
    the watermark to 'now' so the existing backlog is never pushed."""
    await asyncio.sleep(45)
    st = await db.push_state.find_one({"key": "last_push"})
    last = (st or {}).get("value") or datetime.now(timezone.utc).isoformat()
    if not st:
        await db.push_state.update_one({"key": "last_push"}, {"$set": {"value": last}}, upsert=True)
    while True:
        if not _is_leader():
            await asyncio.sleep(45)
            continue
        try:
            if VAPID_PRIVATE_KEY:
                fresh = await db.tips.find(
                    {"created_at": {"$gt": last}, "status": {"$in": ["pending", "live"]}},
                    {"_id": 0}).sort("created_at", 1).to_list(50)
                # One detailed push for a single pick (with deep-link); one bundled digest
                # for a batch — never a stack of individual notifications.
                if len(fresh) == 1:
                    await notify_all_push(_push_payload_for_tip(fresh[0]))
                elif len(fresh) > 1:
                    await notify_all_push(_digest_payload_for_tips(fresh))
                if fresh:
                    last = fresh[-1]["created_at"]
                    await db.push_state.update_one({"key": "last_push"},
                                                   {"$set": {"value": last}}, upsert=True)
        except Exception as e:
            logger.error(f"push_watch_loop error: {e}")
        await asyncio.sleep(45)


# ------------------------------------------------------------------ files
@api_router.get("/users/public/{username}")
async def public_profile(username: str):
    u = await db.users.find_one({"username": username})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    tips_count = await db.tips.count_documents({"user_id": u["id"]})
    wins_count = await db.win_claims.count_documents({"user_id": u["id"]})
    return {
        "username": u.get("username"),
        "created_at": u.get("created_at"),
        "received_credits": u.get("received_credits", 0),
        "streak": u.get("streak", 0),
        "apex_flame": u.get("apex_flame", False),
        "tips_count": tips_count,
        "wins_count": wins_count,
    }


@api_router.post("/tips/{tip_id}/share-image")
async def tip_share_image(tip_id: str):
    """Generate a TipJar-branded shareable slip image for a member pick, tagged with
    the channel it comes from (COMMUNITY PICK for pending, LIVE PICK for live)."""
    tip = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    if tip.get("source") in ("hq-auto", "smart"):
        raise HTTPException(status_code=400, detail="Only member tips can be shared")
    ctype = "live_pending" if tip.get("status") == "live" else "pending"
    live_info = None
    if tip.get("status") == "live" and API_FOOTBALL_KEY and tip.get("home_team") and tip.get("away_team"):
        try:
            lf = await asyncio.to_thread(_apifootball, "/fixtures", {"live": "all"})
            fx = _find_live_fixture(lf or [], tip["home_team"], tip["away_team"])
            if fx:
                g = fx.get("goals") or {}
                live_info = {"minute": ((fx.get("fixture") or {}).get("status") or {}).get("elapsed"),
                             "score": f"{g.get('home') or 0}:{g.get('away') or 0}"}
        except Exception:
            pass
    rlegs = _tip_to_render_legs(tip)
    img = _render_slip_image(rlegs, _to_float(tip.get("odds")), tip.get("stake", ""),
                             tip.get("potential_return", ""), tip.get("username", "TipJar"), ctype, live_info)
    try:
        result = put_object(f"{APP_NAME}/shares/{tip_id}.webp", img, "image/webp")
        path = result["path"]
        await db.files.insert_one({
            "id": str(uuid.uuid4()), "storage_path": path,
            "original_filename": "tipjar-share.webp", "content_type": "image/webp",
            "owner": tip.get("user_id"), "is_deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        await db.tips.update_one({"id": tip_id}, {"$set": {"share_image_path": path}})
    except Exception as ex:
        logger.error(f"share image upload failed: {ex}")
        raise HTTPException(status_code=500, detail="Image generation failed")
    return {"path": path}


@api_router.get("/files/{path:path}")
async def download_file(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    data, content_type = get_object(path)
    return Response(content=data, media_type=record.get("content_type") or content_type)


# ------------------------------------------------------------------ results engine (API-Football)
def _norm(s: str) -> str:
    # Strip diacritics (Rīgas→rigas, Žilina→zilina, Mönchengladbach→monchen...) so
    # API-Football team names match regardless of accents.
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return "".join(c for c in s.lower() if c.isalnum() or c.isspace()).strip()


def _teams_match(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    # space-insensitive containment ("st josephs" ⇄ "st joseph s fc")
    ca, cb = na.replace(" ", ""), nb.replace(" ", "")
    if ca and cb and (ca in cb or cb in ca):
        return True
    stop = {"fc", "cf", "sc", "ac", "club", "de", "the", "and"}
    ta = [w for w in na.split() if w not in stop and len(w) > 2]
    tb = [w for w in nb.split() if w not in stop and len(w) > 2]

    def _close(x, y):
        if x == y or x.startswith(y) or y.startswith(x):
            return True
        # tolerate a single transliteration diff of equal-length tokens (Yelimai/Yelimay)
        if len(x) >= 5 and len(x) == len(y):
            return sum(1 for i in range(len(x)) if x[i] != y[i]) <= 1
        return False

    for wa in ta:
        for wb in tb:
            if _close(wa, wb):
                return True
    return False


def _apifootball(path: str, params: dict):
    if not API_FOOTBALL_KEY:
        return None
    try:
        r = requests.get(f"{API_FOOTBALL_BASE}{path}", params=params,
                         headers={"x-apisports-key": API_FOOTBALL_KEY}, timeout=20)
        r.raise_for_status()
        return r.json().get("response", [])
    except Exception as e:
        logger.error(f"API-Football {path} failed: {e}")
        return None


async def resolve_team_id(name: str):
    if not name or len(name.strip()) < 3:
        return None
    key = _norm(name)
    cached = await db.team_cache.find_one({"key": key})
    if cached:
        return cached.get("team_id")
    resp = _apifootball("/teams", {"search": name.strip()})
    # fallbacks for name mismatches (hyphens, city suffixes)
    if not resp:
        simplified = re.sub(r"[-_]", " ", name).strip()
        if simplified.lower() != name.strip().lower():
            resp = _apifootball("/teams", {"search": simplified})
    if not resp:
        first = re.sub(r"[^A-Za-z0-9 ]", " ", name).split()
        if first and len(first[0]) >= 4:
            resp = _apifootball("/teams", {"search": first[0]})
    team_id = None
    if resp:
        for item in resp:
            if _teams_match(item.get("team", {}).get("name", ""), name):
                team_id = item["team"]["id"]
                break
        if team_id is None:
            team_id = resp[0].get("team", {}).get("id")
    await db.team_cache.update_one({"key": key}, {"$set": {"key": key, "team_id": team_id}}, upsert=True)
    return team_id


def _is_corner_market(market) -> bool:
    """A corner (Ecken) Over/Under market — graded from fixture statistics, not the score."""
    return "ecken" in (market or "").lower()


def _corner_total_for_fixture(fixture_id):
    """Total match corners (both teams) from API-Football fixture statistics.
    Returns an int, or None when stats are unavailable (caller must NOT settle)."""
    if not fixture_id:
        return None
    stats = _apifootball("/fixtures/statistics", {"fixture": fixture_id})
    if not stats:
        return None
    _sog, corners, _shots = _live_stat_totals(stats)
    return corners


PLAYER_LEG_KINDS = {"sot", "shots", "fouls_c", "fouls_d", "scorer", "card", "saves", "player"}


def _name_key(n: str) -> str:
    """Last-name key for fuzzy player matching (handles 'Kylian Mbappé' vs 'K. Mbappé')."""
    parts = [p for p in _norm(n).split() if len(p) >= 2]
    return parts[-1] if parts else ""


def _player_stats_for_fixture(fixture_id):
    """Per-player match stats from API-Football /fixtures/players. Returns
    (players_by_key, team_card_totals) or (None, None) if stats are unavailable
    (caller must NOT settle in that case)."""
    if not fixture_id:
        return None, None
    resp = _apifootball("/fixtures/players", {"fixture": fixture_id})
    if not resp:
        return None, None
    pmap, team_cards = {}, {}
    for block in resp:
        tname = (block.get("team") or {}).get("name", "")
        tcards = 0
        for pl in (block.get("players") or []):
            name = (pl.get("player") or {}).get("name") or ""
            st = ((pl.get("statistics") or [{}])[0]) or {}
            shots = st.get("shots") or {}
            goals = st.get("goals") or {}
            fouls = st.get("fouls") or {}
            cards = st.get("cards") or {}
            yc = cards.get("yellow") or 0
            rc = cards.get("red") or 0
            rec = {
                "shots_total": shots.get("total") or 0,
                "shots_on": shots.get("on") or 0,
                "goals": goals.get("total") or 0,
                "saves": goals.get("saves") or 0,
                "fouls_c": fouls.get("committed") or 0,
                "fouls_d": fouls.get("drawn") or 0,
                "cards": yc + rc,
                "team": tname,
            }
            tcards += yc + rc
            key = _name_key(name)
            if key:
                pmap[key] = rec
        if tname:
            team_cards[_norm(tname)] = tcards
    return pmap, team_cards


def _parse_player_market(market: str):
    """Infer (kind, need) from a German player-prop market string (fallback for legs
    without a structured kind/line, e.g. legacy 'Mbappé 1+ Torschüsse')."""
    m = (market or "").lower()
    need = None
    nm = re.search(r"(\d+)\s*\+", m)
    if nm:
        need = int(nm.group(1))
    else:
        om = re.search(r"über\s+(\d+)[.,]5", m)
        if om:
            need = int(om.group(1)) + 1
    if "torschütze" in m or "anytime" in m or ("trifft" in m and "beide" not in m):
        kind = "scorer"
    elif "aufs tor" in m or "torschüsse" in m or "torschusse" in m:
        kind = "sot"
    elif "schüsse" in m or "schusse" in m:
        kind = "shots"
    elif "gefoult" in m:
        kind = "fouls_d"
    elif "foul" in m:
        kind = "fouls_c"
    elif "karte" in m:
        kind = "card"
    elif "paraden" in m:
        kind = "saves"
    else:
        kind = None
    return kind, (need if need else 1)


def _grade_player_leg(leg, pmap, team_cards, fx):
    """Grade a single player-prop / team-card leg from finished-match player stats.
    Returns True (won), False (lost) or None (cannot grade → do NOT settle)."""
    market = leg.get("market") or ""
    m = market.lower()
    # Team-level markets first (no single player)
    if "beide teams" in m and "karte" in m:
        if not team_cards or len(team_cards) < 2:
            return None
        return all(v >= 1 for v in team_cards.values())
    if "qualifiziert" in m or "qualif" in m or "weiterkommen" in m:
        # Knockout progression proxy: the named team qualifies if it wins the tie/match
        # (winner flag accounts for extra time & penalties; goals as fallback).
        home_de = _norm(leg.get("home") or "")
        away_de = _norm(leg.get("away") or "")
        first_home = home_de.split()[0] if home_de else ""
        first_away = away_de.split()[0] if away_de else ""
        target_home = bool(first_home and first_home in m)
        target_away = bool(first_away and first_away in m)
        if target_home == target_away:
            return None  # ambiguous team reference
        hw, aw = fx.get("home_winner"), fx.get("away_winner")
        hg, ag = fx.get("home_goals") or 0, fx.get("away_goals") or 0
        if target_home:
            return hw if hw is not None else hg > ag
        return aw if aw is not None else ag > hg
    kind = (leg.get("kind") or "").lower()
    line = leg.get("line")
    if kind in ("", "player") or line is None:
        pk, need = _parse_player_market(market)
        kind = pk or kind
        need = need
    else:
        need = int(line) + 1
    if kind not in ("sot", "shots", "fouls_c", "fouls_d", "scorer", "card", "saves"):
        return None
    if not pmap:
        return None
    player = leg.get("player") or (market.split(" — ")[0] if " — " in market else "")
    if not player:
        # legacy: take the leading words before the first digit / stat keyword
        player = re.split(r"\d|über|torsch|schüss|schuss|foul|karte|paraden|trifft",
                          market, flags=re.IGNORECASE)[0].strip()
    key = _name_key(player)
    rec = pmap.get(key)
    if not rec:
        for k, v in pmap.items():
            if key and (key in k or k in key):
                rec = v
                break
    if not rec:
        return None  # player not found in fixture stats → don't guess
    if kind == "sot":
        return rec["shots_on"] >= need
    if kind == "shots":
        return rec["shots_total"] >= need
    if kind == "fouls_c":
        return rec["fouls_c"] >= need
    if kind == "fouls_d":
        return rec["fouls_d"] >= need
    if kind == "scorer":
        return rec["goals"] >= 1
    if kind == "card":
        return rec["cards"] >= 1
    if kind == "saves":
        return rec["saves"] >= need
    return None


def _grade_goal_leg(kind, market, team, fx):
    """Deterministically grade a single-match goal / half-time / corner leg from a
    finished fixture. Returns True (won), False (lost) or None (kind can't be graded
    → the caller must NOT settle, so a leg we don't understand never fakes a result)."""
    hg = fx.get("home_goals") or 0
    ag = fx.get("away_goals") or 0
    hth, hta = fx.get("ht_home"), fx.get("ht_away")
    ht_known = hth is not None and hta is not None
    hth, hta = hth or 0, hta or 0
    total = hg + ag
    ht_total = hth + hta
    sh_total = total - ht_total          # second-half goals
    m = (market or "").lower()
    k = (kind or "").lower()
    # Corner (Ecken) Over/Under — settled from fixture statistics (fx['corners']).
    if k in ("corner_o", "corner_u") or "ecken" in m:
        ctot = fx.get("corners")
        if ctot is None:
            return None                  # no corner stats → don't guess
        cm = re.search(r"(\d+)\.5", m)
        if not cm:
            return None
        line = int(cm.group(1))
        over = ("über" in m) or (k == "corner_o")
        return ctot >= line + 1 if over else ctot <= line
    # full-time total goals line, e.g. "Über 2.5 Tore" (not a half-time line)
    gm = re.search(r"über\s+(\d+)\.5", m)
    if gm and not team and "halbzeit" not in m and "hz" not in m:
        return total >= int(gm.group(1)) + 1
    if k == "team_o05" or ("über 0.5" in m and team):
        if _teams_match(fx.get("home_name", ""), team):
            return hg >= 1
        if _teams_match(fx.get("away_name", ""), team):
            return ag >= 1
        return hg >= 1 or ag >= 1
    if k == "btts" or "beide teams treffen" in m:
        return hg >= 1 and ag >= 1
    # full-time result / double chance (computed straight from the final score)
    if k == "res_1":
        return hg > ag
    if k == "res_2":
        return ag > hg
    if k == "res_x":
        return hg == ag
    if k == "dc_1x":
        return hg >= ag
    if k == "dc_x2":
        return ag >= hg
    if k == "dc_12":
        return hg != ag
    if k in ("ht_o05", "ht_o15", "ht_o25", "sh_o05", "o05_each", "ht_u25", "ht_u35", "ht1_win"):
        if not ht_known:
            return None                  # no half-time data → don't guess
        if k == "ht_o05":
            return ht_total >= 1
        if k == "ht_o15":
            return ht_total >= 2
        if k == "ht_o25":
            return ht_total >= 3
        if k == "sh_o05":
            return sh_total >= 1
        if k == "o05_each":
            return ht_total >= 1 and sh_total >= 1
        if k == "ht_u25":
            return ht_total <= 2
        if k == "ht_u35":
            return ht_total <= 3
        if k == "ht1_win":
            if _teams_match(fx.get("home_name", ""), team):
                return hth > hta
            if _teams_match(fx.get("away_name", ""), team):
                return hta > hth
            return None
    return None


def _datescan_fixture(home_name: str, away_name: str, dates: list, cache: dict = None):
    """Robust fallback: scan ALL fixtures on the kickoff date and match BOTH team
    names (either orientation). Independent of team-id/season resolution, which
    fails for many summer-qualifier leagues (diacritics, city suffixes). Returns a
    finished-fixture dict like find_finished_fixture, else None."""
    for date in dates:
        try:
            int(date[:4])
        except (ValueError, TypeError):
            continue
        if cache is not None and date in cache:
            fixtures = cache[date]
        else:
            fixtures = _apifootball("/fixtures", {"date": date}) or []
            if cache is not None:
                cache[date] = fixtures
        for fx in fixtures:
            th = fx.get("teams", {}).get("home", {}).get("name", "")
            ta = fx.get("teams", {}).get("away", {}).get("name", "")
            hit = (_teams_match(th, home_name) and _teams_match(ta, away_name)) or \
                  (_teams_match(th, away_name) and _teams_match(ta, home_name))
            if not hit:
                continue
            status = fx.get("fixture", {}).get("status", {}).get("short")
            if status in FINISHED_STATUSES:
                ht = fx.get("score", {}).get("halftime", {}) or {}
                return {
                    "home_name": th, "away_name": ta,
                    "fixture_id": fx.get("fixture", {}).get("id"),
                    "home_goals": fx.get("goals", {}).get("home"),
                    "away_goals": fx.get("goals", {}).get("away"),
                    "ht_home": ht.get("home"), "ht_away": ht.get("away"),
                    "home_winner": fx.get("teams", {}).get("home", {}).get("winner"),
                    "away_winner": fx.get("teams", {}).get("away", {}).get("winner"),
                    "status": status,
                }
    return None


def find_finished_fixture(team_id: int, opponent_name: str, dates: list):
    for date in dates:
        try:
            yr = int(date[:4])
        except (ValueError, TypeError):
            continue
        for season in (yr, yr - 1):  # July matches = new season(yr); Jan = prev season(yr-1)
            fixtures = _apifootball("/fixtures", {"team": team_id, "date": date, "season": season})
            if not fixtures:
                continue
            for fx in fixtures:
                th = fx.get("teams", {}).get("home", {}).get("name", "")
                ta = fx.get("teams", {}).get("away", {}).get("name", "")
                if _teams_match(th, opponent_name) or _teams_match(ta, opponent_name):
                    status = fx.get("fixture", {}).get("status", {}).get("short")
                    if status in FINISHED_STATUSES:
                        ht = fx.get("score", {}).get("halftime", {}) or {}
                        return {
                            "home_name": th, "away_name": ta,
                            "fixture_id": fx.get("fixture", {}).get("id"),
                            "home_goals": fx.get("goals", {}).get("home"),
                            "away_goals": fx.get("goals", {}).get("away"),
                            "ht_home": ht.get("home"), "ht_away": ht.get("away"),
                            "home_winner": fx.get("teams", {}).get("home", {}).get("winner"),
                            "away_winner": fx.get("teams", {}).get("away", {}).get("winner"),
                            "status": status,
                        }
            break  # this season had data for the date; no need to probe the other season
    return None


async def judge_market(market: str, home: str, away: str, hg, ag) -> str:
    """Use the LLM to decide won/lost/void for a bet market given the final score."""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"judge-{uuid.uuid4()}",
            system_message=(
                "You are a betting settlement engine. Given a football bet market and the final "
                "full-time score, decide the outcome. Reply with ONLY one lowercase word: "
                "'won', 'lost', or 'void'. No punctuation, no explanation."
            ),
        ).with_model(AI_MODEL_PROVIDER, AI_MODEL)
        prompt = (
            f"Match: {home} {hg} - {ag} {away} (final full-time score).\n"
            f"Bet market: {market}\n"
            "Did this bet win, lose, or void? Answer with one word only."
        )
        resp = await chat.send_message(UserMessage(text=prompt))
        out = (resp if isinstance(resp, str) else str(resp)).strip().lower()
        for word in ("void", "won", "lost"):
            if word in out:
                return word
        return "void"
    except Exception as e:
        logger.error(f"judge_market failed: {e}")
        return "void"


async def settle_pending_tips() -> dict:
    if not API_FOOTBALL_KEY:
        return {"ok": False, "reason": "API_FOOTBALL_KEY not configured", "checked": 0, "settled": 0}
    now = datetime.now(timezone.utc)
    raw = await db.tips.find(
        {"is_parlay": {"$ne": True}, "report": {"$ne": True},
         "home_team": {"$nin": ["", None]}, "away_team": {"$nin": ["", None]},
         "$or": [
             {"status": "pending"},
             {"status": "live", "source": {"$nin": ["hq-live", "hq-auto"]}},
         ]},
        {"_id": 0},
    ).sort("created_at", 1).to_list(300)
    # only spend API calls on matches that have actually finished (kickoff > 2h ago,
    # or any live-status tip whose match may now be over) and that we haven't already
    # failed to resolve several times (quota protection). find_finished_fixture only
    # returns FT games, so an in-play live tip is never settled prematurely.
    finished = []
    for t in raw:
        if t.get("settle_attempts", 0) >= SETTLE_MAX_ATTEMPTS:
            continue
        ko = _parse_kickoff(t.get("match_time"))
        if t.get("status") == "live":
            finished.append((ko or now, t))
        elif _finished_eligible(t.get("match_time"), ko, now):
            finished.append((ko, t))
    finished.sort(key=lambda x: x[0])  # oldest finished first
    checked, settled, details = 0, 0, []
    date_cache = {}
    for ko, tip in finished[:SETTLE_BATCH_CAP]:
        checked += 1
        dates = [ko.date().isoformat(),
                 (ko + timedelta(days=1)).date().isoformat(),
                 (ko - timedelta(days=1)).date().isoformat()]
        team_id = await resolve_team_id(tip["home_team"])
        opponent = tip["away_team"]
        if not team_id:
            team_id = await resolve_team_id(tip["away_team"])
            opponent = tip["home_team"]
        fx = find_finished_fixture(team_id, opponent, dates) if team_id else None
        if not fx:
            # Fallback: scan the date's fixtures and match both team names directly.
            fx = _datescan_fixture(tip["home_team"], tip["away_team"], dates, date_cache)
        if not fx:
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
            continue
        outcome_market = tip.get("market", "")
        if _is_corner_market(outcome_market):
            fx["corners"] = _corner_total_for_fixture(fx.get("fixture_id"))
            res = _grade_goal_leg("corner_o" if "über" in outcome_market.lower() else "corner_u",
                                  outcome_market, "", fx)
            if res is None:
                await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
                continue
            new_status = "won" if res else "lost"
        else:
            outcome = await judge_market(tip.get("market", ""), tip["home_team"], tip["away_team"],
                                         fx["home_goals"], fx["away_goals"])
            new_status = outcome if outcome in ("won", "lost") else "void"
        if new_status == "void":
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
            continue
        await db.tips.update_one({"id": tip["id"]}, {"$set": {
            "status": new_status,
            "final_home": fx["home_goals"], "final_away": fx["away_goals"],
            "settled_by": "auto", "settled_at": datetime.now(timezone.utc).isoformat(),
        }})
        settled += 1
        details.append({"tip": tip["id"], "match": f"{tip['home_team']} vs {tip['away_team']}",
                        "score": f"{fx['home_goals']}-{fx['away_goals']}", "result": new_status})
    return {"ok": True, "checked": checked, "settled": settled, "details": details}


async def settle_hq_combos() -> dict:
    """Settle TipJarHQ bet-builders: the 2-leg goal builders (source=hq-auto) AND the
    Smart Mega-Bet-Builders (source=smart) with player-prop legs. Every leg lives on the
    SAME match, so legs are graded deterministically from the final score / fixture &
    player statistics. Win → 'Best Won', loss → 'Lost'."""
    if not API_FOOTBALL_KEY:
        return {"ok": False, "settled": 0}
    now = datetime.now(timezone.utc)
    combos = await db.tips.find(
        {"source": {"$in": ["hq-auto", "smart"]}, "status": "pending", "is_parlay": True},
        {"_id": 0}).sort("created_at", 1).to_list(200)
    settled = 0
    for tip in combos:
        if tip.get("settle_attempts", 0) >= SETTLE_MAX_ATTEMPTS:
            continue
        ko = _parse_kickoff(tip.get("match_time"))
        if not _finished_eligible(tip.get("match_time"), ko, now):
            continue
        dates = [ko.date().isoformat(),
                 (ko + timedelta(days=1)).date().isoformat(),
                 (ko - timedelta(days=1)).date().isoformat()]
        home, away = tip["home_team"], tip["away_team"]
        team_id = await resolve_team_id(home)
        opponent = away
        if not team_id:
            team_id = await resolve_team_id(away)
            opponent = home
        fx = find_finished_fixture(team_id, opponent, dates) if team_id else None
        if not fx:
            fx = _datescan_fixture(home, away, dates)
        if not fx:
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
            continue
        hg, ag = fx["home_goals"] or 0, fx["away_goals"] or 0
        total_g = hg + ag
        combo_legs = tip.get("combo_legs") or tip.get("legs", [])
        if any(("corner" in (lg.get("kind", "") or "")) or ("ecken" in (lg.get("market", "") or "").lower())
               for lg in combo_legs):
            fx["corners"] = _corner_total_for_fixture(fx.get("fixture_id"))
        # Player-prop legs (shots / shots on target / fouls / cards / scorer / saves) —
        # fetch the finished match's per-player stats once so the whole Mega-Bet-Builder
        # can auto-settle (win → Best Won, lose → Lost).
        pmap, team_cards = None, None
        has_player = any(
            (lg.get("kind", "") or "").lower() in PLAYER_LEG_KINDS
            or _parse_player_market(lg.get("market", ""))[0] is not None
            or ("beide teams" in (lg.get("market", "") or "").lower())
            for lg in combo_legs)
        if has_player:
            pmap, team_cards = _player_stats_for_fixture(fx.get("fixture_id"))
            if not pmap:
                await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
                continue
        all_won, ok = True, True
        for lg in combo_legs:
            lg.setdefault("home", home)
            lg.setdefault("away", away)
            res = _grade_goal_leg(lg.get("kind"), lg.get("market"), lg.get("team"), fx)
            if res is None:
                res = _grade_player_leg(lg, pmap or {}, team_cards or {}, fx)
            if res is None:
                ok = False
                break
            if not res:
                all_won = False
        if not ok:
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
            continue
        await db.tips.update_one({"id": tip["id"]}, {"$set": {
            "status": "won" if all_won else "lost",
            "final_home": hg, "final_away": ag,
            "settled_by": "auto", "settled_at": datetime.now(timezone.utc).isoformat(),
        }})
        settled += 1
    return {"ok": True, "settled": settled}


PARLAY_JUDGE_CAP = 40   # max LLM settlement calls per multi-match run (quota guard)


async def purge_settled_tips() -> int:
    """Settled slips (won/lost) are auto-removed 24h after they were settled — the
    'Abgerechnet' area only ever shows the last day. Seed showcase tips are kept.
    WON System picks (source=hq-system) are ALSO kept forever so the owner can always
    see whether a system ever won ('Best Won' history)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    docs = await db.tips.find(
        {"status": {"$in": ["won", "lost", "void"]}, "id": {"$not": {"$regex": "^seed-"}}},
        {"_id": 0, "id": 1, "settled_at": 1, "created_at": 1, "source": 1, "status": 1}).to_list(5000)
    stale = [d["id"] for d in docs
             if (d.get("settled_at") or d.get("created_at") or "") < cutoff
             and not (d.get("source") == "hq-system" and d.get("status") == "won")]
    if not stale:
        return 0
    await db.tips.delete_many({"id": {"$in": stale}})
    await db.tip_ratings.delete_many({"tip_id": {"$in": stale}})
    logger.info(f"Purged {len(stale)} settled tips older than 24h")
    return len(stale)


def _grade_ht_selection(selection, ht_h, ht_a):
    """Grade a FIRST-HALF goals market from the half-time score.
    Returns 'won' / 'lost' / 'open' (HT market but no HT data yet) / None (not a HT market)."""
    s = (selection or "").lower()
    is_ht = any(k in s for k in (
        "1. halbzeit", "erste halbzeit", "1.halbzeit", "1. hz", "erste hz",
        "1. hälfte", "1.hälfte", "first half", "1st half", "ht ", " ht", "halftime"))
    if not is_ht:
        return None
    if ht_h is None or ht_a is None:
        return "open"
    total = (ht_h or 0) + (ht_a or 0)
    m = re.search(r"(\d)[.,]5", s)
    line = (int(m.group(1)) + 0.5) if m else 0.5
    if "unter" in s or "under" in s:
        return "won" if total < line else "lost"
    return "won" if total > line else "lost"



async def settle_multimatch_parlays() -> dict:
    """Settle multi-match parlays (member + AI system tips) leg-by-leg from the final
    scores. A parlay is LOST the moment any leg loses, and WON only when every leg is
    won. Each leg's status is written back so no leg stays 'open' once its match is
    over. Single-game HQ bet-builders (combo_legs) are handled by settle_hq_combos."""
    if not API_FOOTBALL_KEY:
        return {"ok": False, "settled": 0}
    now = datetime.now(timezone.utc)
    parlays = await db.tips.find(
        {"status": {"$in": ["pending", "live", "cashed_out"]}, "is_parlay": True,
         "combo_legs": {"$exists": False}, "legs.0": {"$exists": True}},
        {"_id": 0}).sort("created_at", 1).to_list(200)
    settled, judged = 0, 0
    for tip in parlays:
        is_cashed = tip.get("status") == "cashed_out"
        # cashed-out slips keep grading legs longer so every finished game shows its
        # real Won/Lost, but their overall "Ausgezahlt" status is never overwritten.
        if tip.get("settle_attempts", 0) >= (24 if is_cashed else 8):
            continue
        legs = tip.get("legs") or []
        changed = any_lost = False
        all_won = all_resolved = True
        for leg in legs:
            st = leg.get("status")
            if st == "won":
                continue
            if st == "lost":
                any_lost, all_won = True, False
                continue
            home, away = _split_match(leg.get("match") or "")
            ko = _kickoff_dt(leg.get("kickoff")) or _kickoff_dt(tip.get("match_time"))
            if not home or not away or not (ko and ko < now - timedelta(hours=2)):
                all_resolved, all_won = False, False
                continue
            if judged >= PARLAY_JUDGE_CAP:
                all_resolved, all_won = False, False
                continue
            dates = [ko.date().isoformat(),
                     (ko + timedelta(days=1)).date().isoformat(),
                     (ko - timedelta(days=1)).date().isoformat()]
            team_id = await resolve_team_id(home)
            opp = away
            if not team_id:
                team_id = await resolve_team_id(away)
                opp = home
            fx = find_finished_fixture(team_id, opp, dates) if team_id else None
            if not fx:
                all_resolved, all_won = False, False
                continue
            hg, ag = fx["home_goals"] or 0, fx["away_goals"] or 0
            leg_res = "won"
            leg_open = False
            for sel in (leg.get("selections") or []):
                sel_txt = _fmt_selection(sel)
                ht = _grade_ht_selection(sel_txt, fx.get("ht_home"), fx.get("ht_away"))
                if ht is not None:
                    # first-half market → graded deterministically from the HT score
                    if ht == "open":
                        leg_open = True
                        break
                    if ht == "lost":
                        leg_res = "lost"
                        break
                    continue
                judged += 1
                o = await judge_market(sel_txt, home, away, hg, ag)
                if o == "lost":
                    leg_res = "lost"
                    break
            if leg_open:
                all_resolved, all_won = False, False
                continue
            leg["status"] = "lost" if leg_res == "lost" else "won"
            leg["final"] = f"{hg}:{ag}"
            changed = True
            if leg["status"] == "lost":
                any_lost, all_won = True, False
        new_status = "lost" if any_lost else ("won" if (all_won and all_resolved) else None)
        upd = {}
        if changed:
            upd["legs"] = legs
        # never overwrite an "Ausgezahlt" slip — only its legs are auto-graded.
        if new_status and not is_cashed:
            upd.update({"status": new_status, "settled_by": "auto", "settled_at": now.isoformat()})
        if upd:
            await db.tips.update_one({"id": tip["id"]}, {"$set": upd})
        if new_status and not is_cashed:
            settled += 1
        elif not (all_resolved and is_cashed):
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
    return {"ok": True, "settled": settled, "judged": judged}


@api_router.post("/admin/settle-now")
async def settle_now(admin: dict = Depends(require_admin)):
    res = await settle_pending_tips()
    res["systems_snapshot"] = await snapshot_systems()
    res["combos"] = await settle_hq_combos()
    res["parlays"] = await settle_multimatch_parlays()
    try:
        res["live"] = await live_autopost()
    except Exception as e:
        res["live"] = {"error": str(e)}
    return res


@api_router.post("/admin/live-run")
async def admin_live_run(admin: dict = Depends(require_admin)):
    return await live_autopost()


@api_router.get("/admin/live-health")
async def admin_live_health(admin: dict = Depends(require_admin)):
    """Production diagnostic: tells us in ONE call why the Live channel is/ isn't
    posting on the deployed environment (env key, HQ account, API reachability,
    leader status, live tip count)."""
    out = {
        "api_football_key_set": bool(API_FOOTBALL_KEY),
        "api_football_base": API_FOOTBALL_BASE,
        "is_leader": _is_leader(),
        "vapid_key_set": bool(VAPID_PRIVATE_KEY),
    }
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    out["hq_account_exists"] = bool(hq)
    out["current_live_tips"] = await db.tips.count_documents({"source": "hq-live", "status": "live"})
    out["pending_prematch_tips"] = await db.tips.count_documents({"source": "hq-auto", "status": "pending"})
    # Probe API-Football directly (quota + reachability + auth).
    try:
        st = await asyncio.to_thread(
            lambda: requests.get(f"{API_FOOTBALL_BASE}/status",
                                 headers={"x-apisports-key": API_FOOTBALL_KEY}, timeout=15))
        sj = st.json()
        out["api_football_http"] = st.status_code
        out["api_football_errors"] = sj.get("errors")
        out["api_football_requests"] = sj.get("response", {}).get("requests")
        out["api_football_plan"] = (sj.get("response", {}) or {}).get("subscription", {}).get("plan")
    except Exception as e:
        out["api_football_probe_error"] = str(e)
    # Probe the live feed count without posting anything.
    try:
        feed = await asyncio.to_thread(
            lambda: requests.get(f"{API_FOOTBALL_BASE}/fixtures", params={"live": "all"},
                                 headers={"x-apisports-key": API_FOOTBALL_KEY}, timeout=20).json())
        out["live_fixtures_available_now"] = feed.get("results")
        out["live_feed_errors"] = feed.get("errors")
    except Exception as e:
        out["live_feed_probe_error"] = str(e)
    return out



async def settlement_loop():
    while True:
        await asyncio.sleep(SETTLE_INTERVAL_SECONDS)
        if not _is_leader():
            continue
        try:
            if API_FOOTBALL_KEY:
                snap = await snapshot_systems()
                result = await settle_pending_tips()
                combos = await settle_hq_combos()
                parlays = await settle_multimatch_parlays()
                purged = await purge_settled_tips()
                logger.info(f"Auto-settlement run: {result.get('settled')} settled / {result.get('checked')} checked; "
                            f"combos {combos.get('settled')}; parlays {parlays.get('settled')}; systems snap {snap}; purged24h {purged}")
        except Exception as e:
            logger.error(f"settlement_loop error: {e}")


@api_router.get("/")
async def root():
    return {"message": "TipJar API live"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


async def seed_showcase():
    """Idempotently seed the TipJarHQ showcase account and its two demo-free showcase tips."""
    hq_email = "hq@tipjar.com"
    hq_pw = os.environ.get("HQ_PASSWORD", "TipJarHQ2026!")
    hq = await db.users.find_one({"email": hq_email})
    if not hq:
        hq = {
            "id": str(uuid.uuid4()), "email": hq_email, "password_hash": hash_password(hq_pw),
            "username": "TipJarHQ", "role": "user", "timezone": "Europe/Berlin", "language": "de",
            "credits": 100, "received_credits": 0, "streak": 0, "last_rated_date": None,
            "ratings_given": 0, "email_verified": True,
            "referral_code": gen_referral_code(), "referred_by": None, "referral_rewarded": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(hq)
        logger.info("Seeded TipJarHQ account")

    now = datetime.now(timezone.utc).isoformat()

    # Purge the tutorial-seed tips (they belong in the How-to-post tutorial only, not the wall)
    for old_id in ["seed-tut-bad", "seed-tut-banker", "seed-tut-live"]:
        await db.tips.delete_one({"id": old_id})
        await db.tip_ratings.delete_many({"tip_id": old_id})

    # Authoritative: TipJarHQ owns the showcase seeds + all auto-posted picks
    # (hqtip-* singles/combos, hqlive-* live picks, smart-* smart bets). Only remove
    # OTHER TipJarHQ-authored junk, and NEVER delete a settled/live pick — settled KI
    # single picks must stay in the 'Abgerechnet' box (they leave via the 24h purge).
    allowed_ids = ["seed-swiss-colombia-multibet"]
    await db.tips.delete_many({
        "user_id": hq["id"],
        "id": {"$nin": allowed_ids, "$not": {"$regex": "^(hqtip-|hqlive-|smart-|hqcur-|hqsys-)"}},
        "status": {"$nin": ["won", "lost", "live"]},
    })

    # Owner (2026-07-14): the old lost WC showcase slips ("Portugal & Messi – Winner &
    # Top Scorer", the Häcken/Portugal-Spanien parlay) are stale demo content and must
    # NOT reappear. Delete them permanently (they used to be re-seeded every startup).
    for dead_id in ["seed-portugal-messi", "seed-hacken-parlay"]:
        await db.tips.delete_one({"id": dead_id})
        await db.tip_ratings.delete_many({"tip_id": dead_id})

    # Swiss-Colombia + Vikingur Reykjavik 3-leg multibet (posted by user as TipJarHQ, 10 stars)
    await db.tips.update_one(
        {"id": "seed-swiss-colombia-multibet"},
        {"$set": {
            "user_id": hq["id"], "username": "TipJarHQ", "image_path": None,
            "home_team": "", "away_team": "",
            "match_time": "07/07/2026 21:00 & 22:00", "country": "International",
            "league": "WM-Quali / Champions-League-Quali",
            "market": "",
            "odds": "1.86", "ai_rating": 10.0,
            "ai_analysis": "Volles Vertrauen. Víkingur Reykjavík: wichtiges CL-Qualifikationsspiel, müssen zuhause gewinnen — wir wollen nur, dass sie treffen (Over 0,5, Quote 1,17). Kolumbien soll sich qualifizieren: keine Tore nötig, einfach nicht in regulärer Zeit verlieren (X2). Luis Díaz ist in absoluter Topform → Über 0,5 Torschüsse aufs Tor (1,59). Sauber abgesicherter Kombi bei 1,86 — Apex 10/10.",
            "legs": [
                {"match": "Víkingur Reykjavík – Győr ETO", "league": "Champions-League-Quali", "kickoff": "07/07 21:00", "status": "won", "selections": ["Víkingur Reykjavík Über 0.5 Tore"], "sel_odds": ["1.17"]},
                {"match": "Schweiz – Kolumbien", "league": "WM-Quali", "kickoff": "07/07 22:00", "status": "won", "selections": ["Doppelte Chance X2 (Kolumbien)"], "sel_odds": ["1.53"]},
                {"match": "Schweiz – Kolumbien", "league": "WM-Quali", "kickoff": "07/07 22:00", "status": "won", "selections": ["Luis Díaz Über 0.5 Torschüsse"], "sel_odds": ["1.59"]},
            ],
            "is_parlay": True, "stake": "", "potential_return": "",
            "status": "won", "settled_by": "manual", "settled_at": now,
        },
         "$setOnInsert": {"raw_text": "", "sum_stars": 0,
                          "ratings_count": 0, "avg_rating": 0, "created_at": now}},
        upsert=True,
    )
    logger.info("Seeded/updated showcase tip: Swiss-Colombia multibet (settled: won)")

    # NOTE: The former 'seed-community-pending' showcase parlay was removed — it used
    # real UPCOMING fixtures (e.g. Ottawa, Criciúma) with fabricated results, which
    # wrongly showed as settled. Real settled slips now populate the Abgerechnet area.
    await db.tips.delete_one({"id": "seed-community-pending"})


# ---------------------------------------------------------------------------
# Forebet auto-tips: TipJarHQ reads forebet.com daily and auto-posts strong picks
# ---------------------------------------------------------------------------
FOREBET_MIN_PROB = 55      # DNB: only when the favoured side is at least this likely
FOREBET_MAX_PER_RUN = 20   # cap new tips per run to avoid flooding the wall

# Leagues TipJar must NEVER touch (amateur / not offered by bookmakers).
# Forebet league short-codes (lowercased): Us4 = USA USL League Two, Fi3 = Finland 3rd tier.
FOREBET_BLOCKED_CODES = {"us4", "fi3", "sl1", "cn3", "brc"}
# Predictz league-string substrings to block (predictz has no short-code).
PREDICTZ_BLOCKED_KW = ("usl league two", "league two usa", "kakkonen")


def _league_blocked_forebet(r: dict) -> bool:
    return (r.get("lcode") or "").strip().lower() in FOREBET_BLOCKED_CODES


def _league_blocked_predictz(league: str) -> bool:
    lg = (league or "").lower()
    return any(kw in lg for kw in PREDICTZ_BLOCKED_KW)


# Owner blacklist: teams/leagues to ALWAYS exclude from AI picks & systems
# (keyword match on home team, away team OR league name). Extend as the owner flags
# obscure/untrustworthy fixtures.
TEAM_LEAGUE_BLACKLIST = ("golden", "mogadishu", "kahibah", "blumenau", "brc",
                         "forge", "saint-laurent", "saint laurent",
                         "delaware", "eagle fc", "gumi", "sportstoto",
                         "prievidza", "inter bratislava")


def _team_or_league_blocked(home: str, away: str, league: str = "") -> bool:
    hay = f" {(home or '').lower()} {(away or '').lower()} {(league or '').lower()} "
    return any(kw in hay for kw in TEAM_LEAGUE_BLACKLIST)


# ---------------------------------------------------------------------------
# System-Schein whitelist: the weekly system bet must ONLY bundle matches that
# mainstream bookmakers actually offer. We use a strict WHITELIST (not blacklist).
#  - Forebet picks are matched by their league short-code (lcode), e.g. En1, UCL.
#  - Predictz picks are matched by keywords in their (readable) league name.
# Everything else (Somalia, USL League Two, women/youth, 3rd/4th tiers, obscure
# national leagues) is excluded from the slip.
# ---------------------------------------------------------------------------
FOREBET_SLIP_CODES = {
    # UEFA / FIFA competitions
    "ucl", "uel", "el", "ecl", "uecl", "wc", "ec", "euro", "nl", "unl",
    "wcq", "ecq", "cq", "cqu",
    # England / Germany / Spain / Italy / France (top 2 tiers)
    "en1", "en2", "ge1", "ge2", "sp1", "sp2", "it1", "it2", "fr1", "fr2",
    # Other major European top flights
    "ne1", "po1", "be1", "tu1", "sc1", "gr1", "au1", "sw1", "da1", "no1",
    "se1", "sv1", "fi1", "ru1", "ua1", "pl1", "cz1", "cr1", "sr1", "hr1", "ro1",
    # Americas
    "br1", "br2", "ar1", "us1", "ml1", "mls", "mx1", "co1", "cl1", "ec1",
    "pe1", "ur1",
    # Asia
    "jp1", "kr1", "ko1", "cn1", "sa1", "qa1", "ae1",
}

SLIP_LEAGUE_KEYWORDS = (
    "champions league", "europa league", "conference league", "europa conference",
    "uefa", "world cup", "nations league", "qualif", "copa america",
    "copa libertadores", "copa sudamericana",
    "premier league", "bundesliga", "la liga", "laliga", "serie a", "serie b",
    "ligue 1", "ligue 2", "eredivisie", "primeira liga", "liga portugal",
    "championship", "efl", "pro league", "super lig", "süper lig",
    "brazil serie a", "brazil serie b", "brasileiro série a", "brasileiro série b",
    "brasileirão", "brasileirao", "série a", "série b",
    "argentina", "liga mx", "liga profesional",
    "major league soccer", "mls", "primera division", "primera división",
    "ecuador serie", "bolivia primera", "colombia primera", "peru primera",
    "uruguay primera", "chile primera", "j1 league", "j league", "j.league",
    "k league", "k1 league", "saudi", "allsvenskan", "eliteserien",
    "superligaen", "danish superliga", "ekstraklasa", "super league",
    "united soccer league",
)

SLIP_BLOCK_KEYWORDS = (
    "league two", "women", "reserve", "futsal", "friendly", " ii", " u19",
    " u21", " u17", " u20", " u23",
    # Brazil — exclude ALL obscure divisions & state championships (owner: only the
    # national Série A / Série B / Brasileirão are bettable). ~20 regional leagues out.
    "serie c", "série c", "serie d", "série d", "serie a1", "série a1",
    "serie a2", "série a2", "serie a3", "série a3", "serie b1", "série b1",
    "serie b2", "série b2", "serie b3", "série b3",
    "paulista", "carioca", "mineiro", "gaucho", "gaúcho", "catarinense", "baiano",
    "paranaense", "cearense", "pernambucano", "goiano", "paraibano", "potiguar",
    "sergipano", "alagoano", "amazonense", "capixaba", "brasiliense",
    "matogrossense", "mato-grossense", "sul-matogrossense", "rondoniense",
    "acreano", "acriano", "tocantinense", "maranhense", "piauiense",
    "amapaense", "roraimense", "copa do nordeste", "copa verde", "copa paulista",
    "copa rio", "copa fares lopes", "copa gaucha", "copa gaúcha",
)


def _is_women_or_youth(name: str) -> bool:
    n = (name or "").lower().strip()
    if n.endswith(" w") or n.endswith("(w)"):
        return True
    return bool(re.search(r"\bu(?:17|18|19|20|21|23)\b", n))


def _slip_eligible(tip: dict) -> bool:
    """True only if this HQ tip is a bookmaker-available, top-competition match."""
    if _is_women_or_youth(tip.get("home_team")) or _is_women_or_youth(tip.get("away_team")):
        return False
    if _team_or_league_blocked(tip.get("home_team"), tip.get("away_team"), tip.get("league")):
        return False
    league = (tip.get("league") or "").lower()
    if any(b in f" {league} " for b in SLIP_BLOCK_KEYWORDS):
        return False
    tid = tip.get("id", "")
    if tid.startswith("hqtip-a"):  # forebet -> whitelist by league short-code
        return (tip.get("league_code") or "").strip().lower() in FOREBET_SLIP_CODES
    # predictz (hqtip-b) -> whitelist by readable league name
    return any(k in league for k in SLIP_LEAGUE_KEYWORDS)


# common club-name noise stripped when de-duplicating the same match across sources
_CLUB_NOISE = {"fc", "sc", "sd", "ca", "ac", "cd", "cf", "afc", "cfc", "club",
               "cds", "aa", "ec", "se", "if", "sk", "fk", "cs", "us", "ik",
               "bk", "ff", "kf", "nk", "hnk", "cd", "ud", "sv", "vfl", "vfb"}

# German↔English aliases so a bookmaker slip ("Switzerland/Colombia") matches a
# TipJar pick stored in German ("Schweiz/Kolumbien"). Token-level, normalised to English.
_TEAM_ALIASES = {
    "schweiz": "switzerland", "kolumbien": "colombia", "deutschland": "germany",
    "spanien": "spain", "frankreich": "france", "italien": "italy",
    "brasilien": "brazil", "argentinien": "argentina", "niederlande": "netherlands",
    "belgien": "belgium", "kroatien": "croatia", "serbien": "serbia",
    "polen": "poland", "tuerkei": "turkey", "turkei": "turkey", "oesterreich": "austria",
    "schweden": "sweden", "daenemark": "denmark", "danemark": "denmark",
    "norwegen": "norway", "griechenland": "greece", "ungarn": "hungary",
    "tschechien": "czechia", "englaende": "england", "vereinigte": "usa",
    "mexiko": "mexico", "japan": "japan", "suedkorea": "southkorea",
    "portugal": "portugal", "irland": "ireland", "schottland": "scotland",
    "wales": "wales", "island": "iceland", "gyor": "gyor",
}


def _fold(n: str) -> str:
    """Lower-case + strip accents to ASCII (Víkingur→vikingur, Győr→gyor)."""
    import unicodedata
    return unicodedata.normalize("NFKD", (n or "").lower()).encode("ascii", "ignore").decode()


def _team_core(n: str) -> str:
    """Normalised core token-string for a team (accent/noise/alias-folded)."""
    toks = [_TEAM_ALIASES.get(t, t)
            for t in re.sub(r"[^a-z0-9 ]", " ", _fold(n)).split()
            if t and t not in _CLUB_NOISE]
    return "".join(sorted(toks)) or _fold(n).replace(" ", "")


def _match_key(home: str, away: str) -> str:
    """Order-independent, prefix-insensitive, accent- & language-insensitive key
    so 'SD Aucas'=='Aucas' and 'Schweiz'=='Switzerland'=='Víkingur'→'vikingur'."""
    return f"{_team_core(home)}|{_team_core(away)}"


# ---------------------------------------------------------------------------
# Expiry: auto-tips whose kickoff has passed must drop off the wall & counts
# (no live results engine yet, so pending picks would otherwise pile up forever)
# ---------------------------------------------------------------------------
_MONTH_ABBR = {"jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4, "mai": 5,
               "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "oct": 10,
               "nov": 11, "dez": 12, "dec": 12}


def _parse_kickoff(mt: str):
    s = (mt or "").strip()
    if not s or "&" in s or "multibet" in s.lower():
        return None  # multibet / unknown → never auto-expire
    # ISO 8601 (e.g. "2026-07-08T22:00:00+00:00" / "...Z") — used by hq-live/smart tips
    try:
        iso = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return iso if iso.tzinfo else iso.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})\s+(\d{1,2}):(\d{2})", s)
    if m:
        d, mo, y, h, mi = map(int, m.groups())
        try:
            return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)
        except Exception:
            return None
    m = re.match(r"^(\d{1,2})\.\s*([A-Za-zäöü]+)\.?\s+(\d{4})", s)
    if m:
        mon = _MONTH_ABBR.get(m.group(2).lower()[:3])
        if mon:
            try:
                return datetime(int(m.group(3)), mon, int(m.group(1)), 23, 59, tzinfo=timezone.utc)
            except Exception:
                return None
    return None


def _kickoff_is_date_only(mt: str) -> bool:
    """A kickoff string with a DATE but NO time (e.g. '9. Jul 2026'). _parse_kickoff
    assigns these 23:59, which wrongly makes an evening UEFA game that's already over
    look 'not yet kicked off' → it never auto-settles until after midnight."""
    s = (mt or "").strip()
    return bool(s) and ":" not in s and _parse_kickoff(s) is not None


def _finished_eligible(mt: str, ko, now) -> bool:
    """Should we ATTEMPT to settle this pick now? find_finished_fixture only ever
    returns FT games, so attempting early is always safe (no premature settlement).
    - normal (time known): kickoff was > 2h ago
    - date-only: assume a typical evening kickoff (18:00 UTC) so we start trying from
      ~20:00 UTC on the match date (not the morning → no wasted retries), and settle
      the same evening the API reports FT instead of waiting past midnight."""
    if not ko:
        return False
    if _kickoff_is_date_only(mt):
        assumed = ko.replace(hour=18, minute=0, second=0, microsecond=0)
        return now >= assumed + timedelta(hours=2)
    return ko < now - timedelta(hours=2)



async def purge_expired_autotips() -> int:
    """Delete pending HQ auto-tips (and predictions) whose kickoff is well past.
    When the results engine (API-Football) is active we keep them longer so
    auto-settlement can mark them won/lost before any cleanup."""
    grace = timedelta(hours=36) if API_FOOTBALL_KEY else timedelta(hours=3)
    cutoff = datetime.now(timezone.utc) - grace
    docs = await db.tips.find(
        {"source": {"$in": ["hq-auto", "smart"]}, "status": "pending"}, {"id": 1, "match_time": 1}).to_list(1000)
    stale = [d["id"] for d in docs
             if (ko := _parse_kickoff(d.get("match_time"))) and ko < cutoff]
    if stale:
        await db.tips.delete_many({"id": {"$in": stale}})
    preds = await db.match_predictions.find({}, {"id": 1, "kickoff": 1}).to_list(1000)
    stale_p = [p["id"] for p in preds
               if (ko := _parse_kickoff(p.get("kickoff"))) and ko < cutoff]
    if stale_p:
        await db.match_predictions.delete_many({"id": {"$in": stale_p}})
    return len(stale)


async def _dedupe_hq_tips() -> int:
    """One pick per match across ALL pending HQ auto-tips (forebet + predictz).
    When a game surfaces twice (e.g. Über 0.5 AND Über 1.5, or the same fixture with
    a slightly different team spelling like 'Orange County SC' vs 'Orange County
    Blues'), keep the single HIGHEST-RISK pick (VALUE preferred, then highest odds)
    and delete the rest — owner rule: never show the same match twice, always take
    the bigger risk."""
    docs = await db.tips.find(
        {"source": "hq-auto", "status": "pending", "is_parlay": {"$ne": True}},
        {"_id": 0, "id": 1, "home_team": 1, "away_team": 1, "odds": 1,
         "pick_type": 1, "match_time": 1, "category": 1}
    ).to_list(4000)

    def _odd(d):
        try:
            return float(str(d.get("odds") or "0").replace(",", "."))
        except Exception:
            return 0.0
    survivors = {d["id"]: d for d in docs}
    to_delete: set = set()

    def dedup_by(keyfn):
        groups: dict = {}
        for d in survivors.values():
            if d["id"] in to_delete:
                continue
            k = keyfn(d)
            if not k:
                continue
            groups.setdefault(k, []).append(d)
        for arr in groups.values():
            if len(arr) < 2:
                continue
            # keep highest risk: VALUE first, then highest odds
            arr.sort(key=lambda d: (d.get("pick_type") == "value", _odd(d)), reverse=True)
            for d in arr[1:]:
                to_delete.add(d["id"])

    def _mt(d):
        return (d.get("match_time") or "").strip()

    def _cat(d):
        return d.get("category") or d.get("pick_type") or "value"

    # dedupe PER CATEGORY so Banker / Value / Risk each keep their own pick per match
    # 1) exact both-team key  2) same kickoff + same home  3) same kickoff + same away
    dedup_by(lambda d: f"{_match_key(d.get('home_team'), d.get('away_team'))}|{_cat(d)}")
    dedup_by(lambda d: f"{_mt(d)}|H|{_team_core(d.get('home_team'))}|{_cat(d)}" if _mt(d) and d.get("home_team") else None)
    dedup_by(lambda d: f"{_mt(d)}|A|{_team_core(d.get('away_team'))}|{_cat(d)}" if _mt(d) and d.get("away_team") else None)

    if to_delete:
        await db.tips.delete_many({"id": {"$in": list(to_delete)}})
        logger.info(f"Dedup: removed {len(to_delete)} duplicate HQ picks (one per match, highest risk kept)")
    return len(to_delete)


# ---------------------------------------------------------------------------
# Match-prediction store + multi-system builder (Lock Bet / Value / Risk / Gamble)
# ---------------------------------------------------------------------------
def _pred_whitelisted(p: dict) -> bool:
    if _is_women_or_youth(p.get("home")) or _is_women_or_youth(p.get("away")):
        return False
    league = (p.get("league") or "").lower()
    if any(b in f" {league} " for b in SLIP_BLOCK_KEYWORDS):
        return False
    if p.get("source") == "forebet":
        return (p.get("league_code") or "").strip().lower() in FOREBET_SLIP_CODES
    return any(k in league for k in SLIP_LEAGUE_KEYWORDS)


async def store_match_prediction(source, matchid, home, away, kickoff, ph, pa, fav,
                                 fav_prob, btts, over25, conf, league="",
                                 league_code="", country=""):
    if not home or not away:
        return
    total = (ph + pa) if (ph is not None and pa is not None) else None
    pid = f"mp-{source[0]}-{matchid}"
    doc = {
        "id": pid, "source": source, "home": home, "away": away,
        "league": league, "league_code": (league_code or "").strip().lower(),
        "country": country, "kickoff": kickoff or "",
        "ph": ph, "pa": pa, "total": total, "fav": fav, "fav_prob": fav_prob,
        "btts": bool(btts), "over25": bool(over25), "conf": conf, "status": "pending",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.match_predictions.update_one({"id": pid}, {"$set": doc}, upsert=True)


def _dc_odds(fav_prob):
    if fav_prob is None:
        return 1.30
    if fav_prob >= 65:
        return 1.15
    if fav_prob >= 55:
        return 1.22
    if fav_prob >= 45:
        return 1.30
    return 1.40


def _dnb_odds(fav_prob):
    if fav_prob is None:
        return 1.60
    if fav_prob >= 70:
        return 1.25
    if fav_prob >= 60:
        return 1.45
    if fav_prob >= 52:
        return 1.65
    return 1.85


def _cs_odds(ph, pa):
    m = {(1, 0): 6.5, (0, 1): 7.0, (1, 1): 5.8, (2, 1): 8.5, (1, 2): 9.5,
         (2, 0): 9.0, (0, 2): 11.0, (2, 2): 13.0, (3, 1): 17.0, (1, 3): 21.0,
         (3, 0): 15.0, (0, 3): 19.0, (3, 2): 26.0, (2, 3): 34.0}
    if (ph, pa) in m:
        return m[(ph, pa)]
    return 15.0 if (ph + pa) >= 4 else 8.0


def _fav_team(p):
    if p.get("fav") == "home":
        return p.get("home")
    if p.get("fav") == "away":
        return p.get("away")
    return None


def _sel(p, market, odds, rating):
    return {
        "id": f"{p['id']}-{re.sub(r'[^a-z0-9]', '', market.lower())[:10]}",
        "home_team": p.get("home"), "away_team": p.get("away"),
        "market": market, "odds": round(float(odds), 2), "rating": rating,
        "match_time": p.get("kickoff", ""), "banker": False,
        "league": p.get("league") or "",
    }


def _finalize_system(sels, bankers, key, title, subtitle, risk):
    total = 1.0
    for i, s in enumerate(sels):
        s["banker"] = i < bankers
        total *= s["odds"]
    n = len(sels)
    if key in ("lock", "value") and n >= 5:
        label = f"{n} Auswahlen · {n - 1}er-System · 1 Fehler erlaubt"
    elif n >= 3:
        label = f"{n} Auswahlen · Kombi"
    else:
        label = f"{n} Auswahlen"
    return {
        "key": key, "title": title, "subtitle": subtitle, "risk": risk,
        "selections": sels, "count": n,
        "banker_count": sum(1 for s in sels if s["banker"]),
        "total_odds": round(total, 2), "system_label": label,
        "week": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
    }


async def build_systems() -> dict:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    raw = await db.match_predictions.find(
        {"status": "pending", "updated_at": {"$gte": cutoff}}).to_list(500)
    preds = [p for p in raw if _pred_whitelisted(p)]
    _ko_cutoff = datetime.now(timezone.utc) - timedelta(hours=3)
    preds = [p for p in preds
             if not ((ko := _parse_kickoff(p.get("kickoff"))) and ko < _ko_cutoff)]

    # de-duplicate the same match across sources; merge complementary fields
    by_key = {}
    for p in preds:
        k = _match_key(p.get("home"), p.get("away"))
        if k not in by_key:
            by_key[k] = dict(p)
        else:
            cur = by_key[k]
            if cur.get("fav_prob") is None and p.get("fav_prob") is not None:
                cur["fav_prob"] = p["fav_prob"]
                cur["fav"] = p.get("fav")
            cur["btts"] = cur.get("btts") or p.get("btts")
            cur["over25"] = cur.get("over25") or p.get("over25")
            if cur.get("total") is None and p.get("total") is not None:
                cur["ph"], cur["pa"], cur["total"] = p.get("ph"), p.get("pa"), p.get("total")
            if not cur.get("kickoff") and p.get("kickoff"):
                cur["kickoff"] = p["kickoff"]
    preds = list(by_key.values())

    # real bookmaker odds (populated by the autopost loops) to replace heuristics
    odds_docs = await db.odds_cache.find({}, {"_id": 0, "key": 1, "odds": 1}).to_list(2000)
    odds_map = {d["key"]: d.get("odds", {}) for d in odds_docs}

    def _apply_real(sel):
        ro = _real_odd_for(sel["market"], odds_map.get(_match_key(sel["home_team"], sel["away_team"]), {}),
                           sel["home_team"], sel["away_team"])
        if ro:
            sel["odds"] = round(float(ro), 2)
        return sel

    goals_sorted = sorted(preds, key=lambda p: (p.get("total") or 0), reverse=True)
    fav_sorted = sorted(preds, key=lambda p: (p.get("fav_prob") or 0), reverse=True)

    def _dc_sel(p, mult=1.0, rating=8.5, suffix=""):
        team = _fav_team(p)
        if not team:
            return None
        dc = "1X" if p.get("fav") == "home" else "X2"
        od = round(_dc_odds(p.get("fav_prob")) * mult, 2)
        return _sel(p, f"{team} Doppelte Chance {dc}{suffix}", od, rating)

    # 1) SICHERHEITS-KOMBI — 4 short "1+ goal" legs, meant to WIN most weeks
    safe, used = [], set()
    for p in goals_sorted:
        t = p.get("total")
        if t is None or t < 2 or p["id"] in used:
            continue
        used.add(p["id"])
        safe.append(_sel(p, "Über 0.5 Tore", 1.08, 9.0 if t >= 3 else 8.5))
        if len(safe) >= 4:
            break

    # 2) BANKER-KOMBI — 5 strongest favourites as Double Chance (owner's winning style)
    bankers = []
    for p in fav_sorted:
        if (p.get("fav_prob") or 0) < 45:
            continue
        s = _dc_sel(p, 1.0, 8.5)
        if s:
            bankers.append(s)
        if len(bankers) >= 5:
            break

    # 3) VALUE-KOMBI — 4 goals-value legs (BTTS / Über 2.5), moderate total odds
    vals = []
    for p in fav_sorted:
        if p.get("btts"):
            mk, od, rt = "Beide Teams treffen (BTTS)", 1.70, 8.0
        elif p.get("over25") or (p.get("total") or 0) >= 4:
            mk, od, rt = "Über 2.5 Tore", 1.55, 8.0
        else:
            continue
        vals.append(_sel(p, mk, od, rt))
        if len(vals) >= 4:
            break

    # 4) RISK-KOMBI — double-chance + BTTS bet-builders, higher total odds
    risks = []
    for p in fav_sorted:
        team = _fav_team(p)
        if not team or not p.get("btts"):
            continue
        dc = "1X" if p["fav"] == "home" else "X2"
        od = round(_dc_odds(p.get("fav_prob")) * 1.70, 2)
        risks.append(_sel(p, f"{team} Doppelte Chance {dc} + Beide treffen", od, 6.5))
        if len(risks) >= 5:
            break

    # 5) JACKPOT — big-odds lottery: the 3 MOST-LIKELY correct scores (dream combo)
    cs_cands = []
    for p in preds:
        ph, pa = p.get("ph"), p.get("pa")
        if ph is None or pa is None:
            continue
        cs_cands.append((_cs_odds(ph, pa), p, ph, pa))
    cs_cands.sort(key=lambda x: x[0])  # most likely (lowest odds) first
    gambles = []
    for od, p, ph, pa in cs_cands:
        if p.get("fav") == "draw" and ph == pa:
            mk, rt = "Unentschieden (X)", 4.0
            od = 3.30
        else:
            mk, rt = f"Genaues Ergebnis {ph}:{pa}", 3.0
        gambles.append(_sel(p, mk, od, rt))
        if len(gambles) >= 3:
            break

    for s in safe:
        _apply_real(s)
    for s in bankers:
        _apply_real(s)
    for s in vals:
        _apply_real(s)

    # 6) SYSTEM DER STUNDE — flash combo ~1h before kickoff. Flexible full-match markets
    # (team win / double chance / over goals / BTTS) so it settles reliably. Total odds
    # MUST exceed 3.6. Owner: "sei sehr flexibel, kannst auch sichere Variante gehen".
    now_dt = datetime.now(timezone.utc)
    hour_lo, hour_hi = now_dt - timedelta(minutes=10), now_dt + timedelta(minutes=90)
    near = []
    for p in preds:
        ko = _parse_kickoff(p.get("kickoff"))
        if ko and hour_lo <= ko <= hour_hi:
            near.append((ko, p))
    near.sort(key=lambda x: x[0])
    def _combo_odd(p, legs):
        tot = 1.0
        for mk, base in legs:
            s = _apply_real(_sel(p, mk, base, 7.0))
            tot *= float(s.get("odds") or base)
        return round(tot, 2)

    combo_games, single_cands, used_h = [], [], set()
    for ko, p in near:
        if p["id"] in used_h:
            continue
        used_h.add(p["id"])
        team = _fav_team(p)
        fp = p.get("fav_prob") or 0
        total = p.get("total") or 0
        ph, pa = p.get("ph") or 0, p.get("pa") or 0
        # HOT high-scoring game → the full "Anderlecht" 3-leg combo as ONE selection.
        if total >= 4 and ph >= 1 and pa >= 1:
            legs3 = [("Über 1.5 Tore 1. Halbzeit", 2.60),
                     ("Beide Teams treffen", 1.80),
                     ("Über 2.5 Tore", 1.85)]
            sel = _sel(p, "Über 1.5 Tore 1. HZ + Beide treffen + Über 2.5 Tore",
                       _combo_odd(p, legs3), 6.5)
            sel["combo_markets"] = [m for m, _ in legs3]
            combo_games.append(sel)
            continue
        # otherwise a single flexible leg (first-half goals preferred)
        if total >= 3.2 or p.get("over25"):
            mk, od, rt = "Über 1.5 Tore 1. Halbzeit", 2.60, 6.5
        elif p.get("btts"):
            mk, od, rt = "Beide Teams treffen (BTTS)", 1.90, 7.0
        elif team and fp >= 55:
            mk, od, rt = f"{team} Sieg", round(max(1.65, min(2.6, 100.0 / fp)), 2), 7.0
        elif team:
            dc = "1X" if p.get("fav") == "home" else "X2"
            mk, od, rt = f"{team} Doppelte Chance {dc}", round(_dc_odds(fp) * 1.15, 2), 7.5
        else:
            mk, od, rt = "Über 0.5 Tore 1. Halbzeit", 1.45, 7.5
        single_cands.append(_apply_real(_sel(p, mk, od, rt)))

    def _prod(ls):
        r = 1.0
        for s in ls:
            r *= float(s.get("odds") or 1)
        return r

    hour = []
    if combo_games:
        # A single Anderlecht combo (~4-9 odds) already clears 3.6 → that's the system.
        # Add a 2nd combo for extra Wumms when available (max 2 to stay sane).
        hour = combo_games[:2]
    elif len(single_cands) >= 2:
        single_cands.sort(key=lambda s: float(s.get("odds") or 1), reverse=True)
        picked = []
        for s in single_cands:
            picked.append(s)
            if len(picked) >= 2 and _prod(picked) > 3.6:
                break
        if len(picked) >= 2 and _prod(picked) > 3.6:
            hour = picked

    systems = [
        _finalize_system(safe, len(safe), "lock", "Sicherheits-Kombi des Tages",
                         "4 Banker · mind. 1 Tor pro Spiel — auf Gewinnen gebaut", "safe"),
        _finalize_system(bankers, len(bankers), "value", "Banker-Kombi des Tages",
                         "5 stärkste Favoriten · Doppelte Chance · echte Quoten", "value"),
        _finalize_system(vals, 2, "smartvalue", "Value-Kombi des Tages",
                         "Tor-Value: BTTS & Über 2.5 · mittlere Quote", "value"),
        _finalize_system(risks, 0, "risk", "Risk-Kombi des Tages",
                         "Doppelte Chance + Beide treffen · höhere Quote", "risk"),
        _finalize_system(gambles, 0, "gamble", "Jackpot-Kombi des Tages",
                         "Zocker-Jagd auf die große Quote (70x+)", "gamble"),
    ]
    if hour:
        systems.insert(0, _finalize_system(
            hour, 0, "hour", "System der Stunde",
            "Το Σύστημα της Ώρας · startet ~1 Std. vor Anpfiff · Gesamtquote 3.6+", "value"))

    return {
        "week": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
        "systems": systems,
    }


async def snapshot_systems() -> int:
    """Persist today's system slips as tips (source=hq-system, is_parlay) so they get
    auto-settled leg-by-leg and any WINNING system surfaces in 'Best Won'. This is the
    only way to answer 'does a system ever win'. Frozen once per day via $setOnInsert."""
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return 0
    try:
        data = await build_systems()
    except Exception as e:
        logger.warning(f"snapshot_systems build failed: {e}")
        return 0
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    now = datetime.now(timezone.utc).isoformat()
    saved = 0
    for s in data.get("systems", []):
        sels = s.get("selections") or []
        # A single-game 3-leg combo (Anderlecht) counts as a full slip on its own.
        has_combo = any(sel.get("combo_markets") for sel in sels)
        if len(sels) < 2 and not has_combo:
            continue
        legs = [{
            "match": f"{sel.get('home_team')} \u2013 {sel.get('away_team')}",
            "league": sel.get("league") or "",
            "kickoff": sel.get("match_time") or "",
            "sel_odds": [f"{sel.get('odds')}"],
            "selections": sel.get("combo_markets") or [sel.get("market")],
            "status": "open",
        } for sel in sels]
        tip_id = f"hqsys-{s.get('key')}-{day}"
        if s.get("key") == "hour":
            # the hour-system changes through the day — one persisted tip per match set
            sig = hashlib.md5("|".join(sorted(l["match"] for l in legs)).encode()).hexdigest()[:8]
            tip_id = f"hqsys-hour-{sig}"
        await db.tips.update_one({"id": tip_id}, {
            "$setOnInsert": {
                "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ System",
                "raw_text": "", "image_path": None,
                "home_team": "", "away_team": "",
                "match_time": legs[0]["kickoff"] if legs else "",
                "country": "", "league": s.get("title") or "System-Schein",
                "league_code": "",
                "market": s.get("system_label") or f"{len(sels)}er-System",
                "odds": f"{s.get('total_odds')}",
                "ai_rating": 6.0, "win_prob": 0.0,
                "ai_analysis": f"{s.get('title')} \u2014 {s.get('subtitle')} (Gesamtquote {s.get('total_odds')}).",
                "legs": legs, "is_parlay": True,
                "stake": "", "potential_return": "",
                "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
                "status": "pending", "source": "hq-system",
                "system_key": s.get("key"), "created_at": now,
            },
        }, upsert=True)
        saved += 1
    return saved


# team-name -> "DD/MM/YYYY HH:MM" kickoff index, filled by forebet, used by predictz
FOREBET_TIME_INDEX: dict[str, str] = {}
# token-set match list so 'Kairat' matches 'Kairat Almaty', 'Torpedo' matches 'Torpedo Kutaisi'
FOREBET_MATCHES: dict[str, dict] = {}


def _sig_tokens(name: str) -> set:
    return {t for t in re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split()
            if t and t not in _CLUB_NOISE and len(t) >= 3}


def _forebet_time_for(home: str, away: str):
    """Find a forebet kickoff by token overlap (handles city-suffix name diffs)."""
    ph, pa = _sig_tokens(home), _sig_tokens(away)
    if not ph or not pa:
        return None
    for e in FOREBET_MATCHES.values():
        if (ph & e["ht"]) and (pa & e["at"]):
            return e["time"]
    return None


def _remember_forebet_match(home: str, away: str, ko: str):
    FOREBET_TIME_INDEX[f"{_norm_team(home)}|{_norm_team(away)}"] = ko
    FOREBET_MATCHES[_match_key(home, away)] = {
        "ht": _sig_tokens(home), "at": _sig_tokens(away), "time": ko}


# --- Self-healing chromium: deployed containers may not ship the browser binary.
# On first scrape we verify chromium launches; if not, install it at runtime. ---
_chromium_ready = False
_chromium_lock = asyncio.Lock()
SCRAPE_TIMEOUT = 90  # hard cap (s) per scrape so a stuck browser can't hang the task/shutdown
_BG_TASKS: list = []  # long-running background loops, cancelled on shutdown


# ── Single-leader election for background jobs ──────────────────────────────
# Production runs multiple replicas. Without this, EVERY replica runs the
# settlement/scraper/live loops in parallel → double the API-Football calls
# (quota exhaustion) and double settle_attempts (tips hit the retry cap far too
# early and get stuck "open"). A tiny Mongo-based lease makes exactly ONE replica
# the worker. It is FAIL-OPEN: if the lease can't be read/written we default to
# running, so background work never stops completely.
import socket as _socket
_INSTANCE_ID = f"{_socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"
_LEADER_TTL_SECONDS = 90
_IS_LEADER = {"val": True}  # fail-open default


async def _refresh_leadership():
    now = datetime.now(timezone.utc)
    now_s = now.isoformat()
    expiry_s = (now + timedelta(seconds=_LEADER_TTL_SECONDS)).isoformat()
    r = await db.system_locks.update_one(
        {"_id": "bg_leader", "$or": [{"holder": _INSTANCE_ID},
                                     {"expires_at": {"$lte": now_s}}]},
        {"$set": {"holder": _INSTANCE_ID, "expires_at": expiry_s}},
    )
    if r.matched_count == 0:
        try:
            await db.system_locks.insert_one(
                {"_id": "bg_leader", "holder": _INSTANCE_ID, "expires_at": expiry_s})
        except Exception:
            pass  # another replica created/holds it → we're a follower
    doc = await db.system_locks.find_one({"_id": "bg_leader"})
    _IS_LEADER["val"] = bool(doc and doc.get("holder") == _INSTANCE_ID)


async def _leadership_loop():
    while True:
        try:
            await _refresh_leadership()
        except Exception as e:
            _IS_LEADER["val"] = True  # fail-open: never freeze all work on a DB blip
            logger.error(f"leadership refresh error (fail-open): {e}")
        await asyncio.sleep(30)


def _is_leader() -> bool:
    return _IS_LEADER["val"]




async def _chromium_launchable() -> bool:
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
            await b.close()
        return True
    except Exception as e:
        logger.warning(f"Chromium not launchable yet: {str(e)[:200]}")
        return False


async def ensure_chromium() -> bool:
    global _chromium_ready
    if _chromium_ready:
        return True
    async with _chromium_lock:
        if _chromium_ready:
            return True
        import sys
        path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "/root/.cache/ms-playwright"
        try:
            os.makedirs(path, exist_ok=True)
            t = os.path.join(path, ".wtest"); open(t, "w").close(); os.remove(t)
        except Exception:
            path = "/tmp/pw-browsers"
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = path
            os.makedirs(path, exist_ok=True)
        if await _chromium_launchable():
            _chromium_ready = True
            return True
        logger.info(f"Chromium missing — installing into {path} (one-time, ~30s)...")
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "playwright", "install", "chromium",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": path})
            out, _ = await proc.communicate()
            logger.info(f"playwright install rc={proc.returncode}: {(out or b'')[-300:]}")
        except Exception as e:
            logger.error(f"Chromium install failed: {e}")
            return False
        _chromium_ready = await _chromium_launchable()
        if not _chromium_ready:
            logger.error("Chromium still unavailable after install (missing system libs?).")
        return _chromium_ready



def _norm_team(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def _forebet_rating(prob: int) -> float:
    if prob >= 75:
        return 9.0
    if prob >= 68:
        return 8.5
    if prob >= 62:
        return 8.0
    return 7.0


def _forebet_datetime(raw: Optional[str]) -> str:
    # Forebet uses US format "MM/DD/YYYY H:MM AM/PM" -> app display "DD/MM/YYYY HH:MM"
    if not raw:
        return datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    try:
        dt = datetime.strptime(raw.strip(), "%m/%d/%Y %I:%M %p")
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return raw.strip()


# --- Owner value rule (2026-07-08): only give bets we win ~80% of the time AND at
# odds > 1.60 (genuine value). No 50/50 markets. Markets that lose too often over
# time are auto-disabled (self-learning). ---
VALUE_MIN_ODDS = 1.60
WIN_PROB_MIN = 0.72          # value pick: ≥72% win chance (owner) — clearly no coin-flip
BANKER_WIN_PROB = 0.85       # separate safe "banker" category (low odds, ~85%+), for combos
MARKET_MIN_SAMPLE = 8        # min settled tips before a market family can be judged
MARKET_MIN_WINRATE = 0.55    # families below this observed win-rate get disabled


def _market_family(market: str) -> str:
    m = (market or "").lower().strip()
    if "handicap" in m:
        return "handicap"
    if "draw no bet" in m:
        return "dnb"
    if "doppelte chance" in m and "beide" not in m and "treffen" not in m:
        return "dc"
    if "über 2.5" in m and ("beide" in m or "btts" in m):
        return "o25_btts"
    if "beide teams treffen" in m or "btts" in m:
        return "btts"
    if "über 2.5" in m:
        return "o25"
    if "über 1.5" in m:
        return "o15"
    if "unter 3.5" in m:
        return "u35"
    if "unter 2.5" in m:
        return "u25"
    if "unter" in m and "tore" in m:
        return "under"
    if "über 0.5" in m:
        return "o05" if m.startswith("über") else "team_o05"
    if "genaues ergebnis" in m or "unentschieden" in m:
        return "gamble"
    return "other"


async def _banned_market_families() -> set:
    """Self-learning: disable market families that have lost too often historically."""
    docs = await db.tips.find(
        {"status": {"$in": ["won", "lost"]}, "source": {"$in": ["hq-auto", "hq-live"]}},
        {"_id": 0, "market": 1, "status": 1}).to_list(3000)
    agg: dict[str, list] = {}
    for d in docs:
        fam = _market_family(d.get("market"))
        cell = agg.setdefault(fam, [0, 0])  # [wins, total]
        cell[0] += 1 if d.get("status") == "won" else 0
        cell[1] += 1
    banned = set()
    for fam, (w, n) in agg.items():
        if n >= MARKET_MIN_SAMPLE and (w / n) < MARKET_MIN_WINRATE:
            banned.add(fam)
            logger.info(f"Market family disabled (self-learning): {fam} — {w}/{n} won")
    return banned



def _pois_line_odds(lam, line, over=True, margin=0.95):
    """Realistic bookmaker-style odds for an Over/Under goals line, derived from a
    Poisson model on the expected total goals `lam`. Returns (odd, win_prob)."""
    import math
    lam = max(0.2, float(lam or 0))
    kmax = int(line)                       # goals 0..kmax count as 'Under'
    p_under = sum(math.exp(-lam) * lam ** k / math.factorial(k) for k in range(kmax + 1))
    p = (1.0 - p_under) if over else p_under
    p = min(0.985, max(0.02, p))
    return round(max(1.01, (1.0 / p) * margin), 2), round(p, 3)


def _forebet_candidates(r: dict) -> list[dict]:
    """Return ALL viable market options for a match, each with an estimated win
    probability ('winprob'). forebet_autopost then applies REAL bookmaker odds and
    keeps only genuine VALUE picks (owner rule): winprob >= WIN_PROB_MIN (~80%) AND
    odd >= VALUE_MIN_ODDS (1.60). Coin-flip markets never pass and are not posted."""
    opts = []
    probs = r.get("probs") or []
    pred = (r.get("pred") or "").strip()
    home, away = r.get("home"), r.get("away")
    draw = probs[1] if len(probs) >= 2 else 0
    # Favourite markets: Double Chance (draw counts as win) + Draw No Bet
    if pred in ("1", "2") and len(probs) >= 3:
        if pred == "1":
            win, loss, team, dc = probs[0], probs[2], home, "1X"
        else:
            win, loss, team, dc = probs[2], probs[0], away, "X2"
        if win >= FOREBET_MIN_PROB:
            dc_wp = min(0.97, (win + draw) / 100.0)
            opts.append({"sfx": "-dc", "market": f"{team} Doppelte Chance {dc}",
                         "odds": f"{max(1.05, 1 / max(dc_wp, 0.01)):.2f}",
                         "rating": 8.5, "winprob": dc_wp})
            dnb_wp = win / max(win + loss, 1)
            opts.append({"sfx": "-dnb", "market": f"{team} (Draw No Bet)",
                         "odds": f"{max(1.05, 1 / max(dnb_wp, 0.01)):.2f}",
                         "rating": 8.5 if win >= 72 else 8.0 if win >= 63 else 7.5,
                         "winprob": dnb_wp})
        # Underdog handicap (owner: safer than Unter X.5 — it survives high-scoring
        # games as long as the weak side isn't thrashed). Offered for ANY favourite,
        # not just strong ones, since +3.5/+2.5 rarely lose. +3.5/+2.5 = bankers.
        und = away if pred == "1" else home
        opts.append({"sfx": "-hcp35", "market": f"{und} Handicap +3.5",
                     "odds": "1.15", "rating": 8.5, "winprob": 0.92})
        opts.append({"sfx": "-hcp25", "market": f"{und} Handicap +2.5",
                     "odds": "1.30", "rating": 8.0, "winprob": 0.87})
        opts.append({"sfx": "-hcp15", "market": f"{und} Handicap +1.5",
                     "odds": "1.55", "rating": 7.5, "winprob": 0.73})
    # Doppelte Chance 12 (Heim ODER Auswärts, kein Remis) — value when a draw is
    # unlikely; the real bookmaker odd decides if it passes the 1.60 value gate.
    if len(probs) >= 3:
        dc12_wp = min(0.97, (probs[0] + probs[2]) / 100.0)
        if dc12_wp >= 0.60:
            opts.append({"sfx": "-dc12", "market": "Doppelte Chance 12",
                         "odds": f"{max(1.05, 1 / max(dc12_wp, 0.01)):.2f}",
                         "rating": 8.0, "winprob": dc12_wp})
    # Goals markets derived from the predicted correct score.
    sc = parse_pred_score(r.get("score"))
    try:
        avg = float((r.get("avg") or "0").replace(",", "."))
    except Exception:
        avg = 0.0
    if sc:
        ph, pa = sc
        total = ph + pa
        # Favourite handicap -1.5 is produced ONLY by the RISK generator below
        # (single -1.5 handicap per match, realistic odds) — no duplicate here.
        # underdog team-to-score (owner idea) — passes the gate only if the book
        # prices it >= 1.60 while our winprob is high enough.
        # Owner (2026-07-10): FAVOURITE to score over 0.5 (safe — a clear favourite
        # almost always scores). The risky UNDERDOG-to-score single was removed after
        # France–Morocco (the weak side that can't create chances must never anchor a pick).
        if pred == "1" and ph >= 1:
            opts.append({"sfx": "-ftg", "market": f"{home} Über 0.5 Tore",
                         "odds": "1.22", "rating": 8.5, "winprob": 0.88})
        elif pred == "2" and pa >= 1:
            opts.append({"sfx": "-ftg", "market": f"{away} Über 0.5 Tore",
                         "odds": "1.22", "rating": 8.5, "winprob": 0.88})
        # DYNAMIC single-game bet-builder (owner: "as many legs from one game as you
        # want — just win, but NEVER add a redundant leg"). Both teams to score already
        # guarantees at least 2 goals, so 'Über 1.5 Tore' is IMPLIED and must never be
        # added on top. We only stack goal-lines that are NOT implied (Über 2.5+) and
        # only with a 1-goal safety buffer under the predicted total. If nothing extra
        # qualifies we simply keep the classic 'both teams to score'.
        if sc and pred in ("1", "2") and ph >= 1 and pa >= 1 and total >= 3:
            # Owner (2026-07-10): the risky "Beide Teams treffen" builder is replaced by a
            # FAVOURITE-anchored combo that never needs the underdog to score:
            #   {Favourite} Über 0.5 Tore  +  Über 1.5 Tore gesamt  (+ Über 0.5 Tore 2. HZ)
            # Games like France–Morocco (weak side kept scoreless) now still win. Every
            # leg settles deterministically via _grade_goal_leg.
            fav_team = home if pred == "1" else away
            clegs = [
                {"market": f"{fav_team} Über 0.5 Tore", "base_odd": 1.22,
                 "kind": "team_o05", "team": fav_team},
                {"market": "Über 1.5 Tore", "base_odd": 1.30, "kind": "o15"},
            ]
            if total >= 4:
                clegs.append({"market": "Über 0.5 Tore 2. Halbzeit",
                              "base_odd": 1.40, "kind": "sh_o05"})
            n = len(clegs)
            others = " + ".join(l["market"] for l in clegs[1:])
            cmarket = f"{fav_team} Über 0.5 Tore + {others} ({n}er-Bet-Builder)"
            wp = 0.72 if n == 2 else 0.60
            opts.append({
                "sfx": "-favbb", "combo": True, "rating": 7.5, "winprob": wp,
                "market": cmarket, "legs": clegs,
            })
        # ── Extra sensible single-game builders (owner-requested variety). Every leg is
        # deterministically settleable via _grade_goal_leg, so nothing can get stuck. ──
        fav_side = pred if pred in ("1", "2") else None
        # (a) Favourite Über 0.5 Tore + Doppelte Chance (both backed by the strong side —
        # replaces the old BTTS+DC builder; the underdog is never required to score).
        if sc and total >= 2 and fav_side:
            fav_team = home if fav_side == "1" else away
            dc_kind, dc_lbl = ("dc_1x", "1X") if fav_side == "1" else ("dc_x2", "X2")
            opts.append({
                "sfx": "-favdc", "combo": True, "rating": 7.5, "winprob": 0.70,
                "market": f"{fav_team} Über 0.5 Tore + Doppelte Chance {dc_lbl} (Bet-Builder)",
                "legs": [
                    {"market": f"{fav_team} Über 0.5 Tore", "base_odd": 1.22,
                     "kind": "team_o05", "team": fav_team},
                    {"market": f"Doppelte Chance {dc_lbl}", "base_odd": 1.28, "kind": dc_kind},
                ],
            })
        # (a2) HOT high-scoring "Anderlecht-style" builder (owner 2026-07-11): for open,
        # goal-heavy games → Über 1.5 Tore 1. Halbzeit + Beide Teams treffen + Über 2.5 Tore.
        # Higher odds/risk; every leg settles deterministically (ht_o15 / btts / o25).
        if sc and total >= 4 and ph >= 1 and pa >= 1:
            opts.append({
                "sfx": "-hot", "combo": True, "hot": True, "rating": 7.0, "winprob": 0.40,
                "market": "Über 1.5 Tore 1. Halbzeit + Beide Teams treffen + Über 2.5 Tore (3er-Bet-Builder)",
                "legs": [
                    {"market": "Über 1.5 Tore 1. Halbzeit", "base_odd": 2.60, "kind": "ht_o15"},
                    {"market": "Beide Teams treffen", "base_odd": 1.80, "kind": "btts"},
                    {"market": "Über 2.5 Tore", "base_odd": 1.85, "kind": "o25"},
                ],
            })
        # (b) Über 2.5 Tore + Doppelte Chance 12 (high-scoring game, draw unlikely)
        if sc and total >= 4 and len(probs) >= 3 and (probs[0] + probs[2]) >= 60:
            opts.append({
                "sfx": "-o25dc", "combo": True, "rating": 7.5, "winprob": 0.48,
                "market": "Über 2.5 Tore + Doppelte Chance 12 (Bet-Builder)",
                "legs": [
                    {"market": "Über 2.5 Tore", "base_odd": 1.85, "kind": "o25"},
                    {"market": "Doppelte Chance 12", "base_odd": 1.35, "kind": "dc_12"},
                ],
            })
        # (c) Über 0.5 Tore je Halbzeit (both halves see a goal) — needs an open game
        if sc and total >= 3 and ph >= 1 and pa >= 1:
            opts.append({
                "sfx": "-o05each", "combo": True, "rating": 7.5, "winprob": 0.52,
                "market": "Über 0.5 Tore in jeder Halbzeit (Bet-Builder)",
                "legs": [
                    {"market": "Über 0.5 Tore 1. Halbzeit", "base_odd": 1.55, "kind": "ht_o05"},
                    {"market": "Über 0.5 Tore 2. Halbzeit", "base_odd": 1.40, "kind": "sh_o05"},
                ],
            })
        # ── Goal-line markets with REALISTIC, match-specific odds (owner fed real
        # bookmaker samples). Odds are derived from a Poisson model on the expected
        # total goals (lam), so 'Über 2.5' in a 1.5-goal game and a 3.5-goal game get
        # very different, believable prices instead of a fixed fantasy number. ──
        lam = avg if (avg and avg > 0) else float(total)
        # Over lines
        for line, sfx, rt in ((0.5, "-g", 8.5), (1.5, "-o15", 8.0), (2.5, "-o25", 7.5)):
            od, p = _pois_line_odds(lam, line, over=True)
            opts.append({"sfx": sfx, "market": f"Über {line} Tore", "odds": f"{od:.2f}",
                         "rating": rt, "winprob": p})
        # Under lines
        for line, sfx, rt in ((2.5, "-u25", 8.0), (3.5, "-u35", 8.5)):
            od, p = _pois_line_odds(lam, line, over=False)
            opts.append({"sfx": sfx, "market": f"Unter {line} Tore", "odds": f"{od:.2f}",
                         "rating": rt, "winprob": p})
        # ── Corner (Ecken) markets. Corners have no dedicated data feed, so we estimate
        # an expected total-corners rate from the goal expectation (open, attacking games
        # produce more corners) and price Over/Under lines with the same Poisson model.
        # These settle deterministically from API-Football fixture statistics. ──
        corner_lam = max(7.0, min(14.0, 6.5 + 1.4 * lam))
        for line, sfx, rt in ((7.5, "-co75", 8.0), (8.5, "-co85", 7.5)):
            od, p = _pois_line_odds(corner_lam, line, over=True)
            opts.append({"sfx": sfx, "market": f"Über {line} Ecken", "odds": f"{od:.2f}",
                         "rating": rt, "winprob": p})
        for line, sfx, rt in ((11.5, "-cu115", 8.0), (10.5, "-cu105", 7.5)):
            od, p = _pois_line_odds(corner_lam, line, over=False)
            opts.append({"sfx": sfx, "market": f"Unter {line} Ecken", "odds": f"{od:.2f}",
                         "rating": rt, "winprob": p})
        # Corner bet-builder: goals + corners from ONE match (owner request).
        if total >= 3:
            opts.append({
                "sfx": "-cornerbb", "combo": True, "rating": 7.5, "winprob": 0.55,
                "market": "Über 1.5 Tore + Über 8.5 Ecken (Bet-Builder)",
                "legs": [
                    {"market": "Über 1.5 Tore", "base_odd": 1.28, "kind": "o15"},
                    {"market": "Über 8.5 Ecken", "base_odd": 1.55, "kind": "corner_o"},
                ],
            })
        # RISK: favourite -1.5 handicap (win by 2+). Odds/probability scale with the
        # predicted winning margin. High-odds ones land in the "Risk" filter.
        if pred in ("1", "2"):
            fav = home if pred == "1" else away
            margin = abs(ph - pa)
            if margin >= 3:
                h_od, h_wp = 1.65, 0.60
            elif margin == 2:
                h_od, h_wp = 1.95, 0.50
            elif margin == 1:
                h_od, h_wp = 2.60, 0.38
            else:
                h_od, h_wp = None, None
            if h_od:
                opts.append({"sfx": "-hcap15", "market": f"{fav} -1.5 (Handicap)",
                             "odds": f"{h_od:.2f}", "rating": 6.5, "winprob": h_wp})
    return opts


# Owner curated-mode (2026-07-09): the Single-Picks feed is a hand-curated list
# (exact bookmaker legs & odds). While True, the Forebet/Predictz auto-scrapers do
# NOT post or overwrite single picks. Set to False to resume full automation.
# Owner curated-mode toggle. When True the Forebet/Predictz auto-scrapers do NOT
# post single picks at all. When False they post, but ONLY for tomorrow onward —
# today's Single-Picks stay hand-curated (see _AUTOPOST_MIN_KO usage below).
AUTOPOST_PAUSED = False
FOREBET_TOMORROW_URL = "https://www.forebet.com/en/football-tips-and-predictions-for-tomorrow"


async def forebet_autopost() -> dict:
    """Scrape forebet, publish DNB + safe goals bankers (with kickoff time) as TipJarHQ."""
    if AUTOPOST_PAUSED:
        return {"posted": 0, "reason": "autopost paused (curated mode)"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    # Only auto-post from the start of TOMORROW (UTC) — today stays curated.
    _now = datetime.now(timezone.utc)
    _AUTOPOST_MIN_KO = (_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        rows_today = await asyncio.wait_for(scrape_forebet_today(60), timeout=SCRAPE_TIMEOUT)
    except Exception as e:
        logger.error(f"Forebet today scrape failed: {e}")
        rows_today = []
    try:
        rows_tomorrow = await asyncio.wait_for(
            scrape_forebet_today(60, url=FOREBET_TOMORROW_URL), timeout=SCRAPE_TIMEOUT)
    except Exception as e:
        logger.warning(f"Forebet tomorrow scrape failed: {e}")
        rows_tomorrow = []
    rows = rows_today + rows_tomorrow
    if not rows:
        return {"posted": 0, "reason": "scrape empty"}

    banned = await _banned_market_families()
    candidates = []
    for r in rows:
        if _league_blocked_forebet(r):
            continue
        kickoff = _forebet_datetime(r.get("datetime"))
        # remember kickoff time for predictz to reuse
        if r.get("home") and r.get("away"):
            _remember_forebet_match(r["home"], r["away"], kickoff)
        # store the full match prediction (feeds the multi-system builder)
        try:
            sc = parse_pred_score(r.get("score"))
            ph, pa = sc if sc else (None, None)
            probs = r.get("probs") or []
            pred = (r.get("pred") or "").strip()
            if pred == "1":
                fav, fav_prob = "home", (probs[0] if len(probs) >= 1 else None)
            elif pred == "2":
                fav, fav_prob = "away", (probs[2] if len(probs) >= 3 else None)
            else:
                fav, fav_prob = "draw", (probs[1] if len(probs) >= 2 else None)
            btts = bool(ph and pa and ph >= 1 and pa >= 1)
            over25 = bool(ph is not None and pa is not None and (ph + pa) >= 3)
            await store_match_prediction(
                "forebet", r.get("matchid") or f"{r['home']}-{r['away']}",
                r.get("home"), r.get("away"), kickoff, ph, pa, fav, fav_prob,
                btts, over25, None, league_code=r.get("lcode"), country=r.get("cc"))
        except Exception as e:
            logger.warning(f"forebet prediction store failed: {e}")
        home, away = r.get("home"), r.get("away")
        if not home or not away:
            continue
        # Owner: today's Single-Picks are hand-curated → the auto-scraper only creates
        # picks from tomorrow onward. (Predictions for today are still stored above so
        # the System-Slip keeps working.)
        _ko = _parse_kickoff(kickoff)
        if _ko and _ko < _AUTOPOST_MIN_KO:
            continue
        if _is_women_or_youth(home) or _is_women_or_youth(away):
            continue  # owner: only recognised, bettable men's competitions
        if _team_or_league_blocked(home, away, r.get("league") or r.get("lcode")):
            continue  # owner blacklist (teams/leagues)
        # owner: only give picks from recognised, bookmaker-available leagues (same
        # whitelist as the system slips) — no Somalia/obscure lower divisions.
        if (r.get("lcode") or "").strip().lower() not in FOREBET_SLIP_CODES:
            continue
        # VALUE + BANKER gate (owner): apply real bookmaker odds; keep VALUE picks
        # (≥72% win AND odd≥1.60) or, as a separate safe category, BANKER picks (≥85%
        # win, any odd — great for combos). Drop self-learning-disabled families.
        try:
            odds_map = await ensure_match_odds(home, away, kickoff)
        except Exception:
            odds_map = {}
        value_opts, banker_opts, risk_opts, combo_opts = [], [], [], []
        for o in _forebet_candidates(r):
            if o.get("combo"):
                legs, prod = [], 1.0
                for lg in o["legs"]:
                    ro = _real_odd_for(lg["market"], odds_map, home, away)
                    od = round(float(ro) if ro else float(lg["base_odd"]), 2)
                    prod *= od
                    legs.append({"home": home, "away": away, "market": lg["market"],
                                 "odds": od, "kind": lg["kind"], "team": lg.get("team", "")})
                # Bet-Builder combos are the owner's favourite "nice" tips (goals each
                # half, favourite scores + DC, Über 2.5 + DC12 …). They live in VALUE
                # within 1.40–3.0. The HOT high-scoring builder allows bigger odds and
                # lands in the RISK filter (but stays a settleable combo).
                if o.get("hot"):
                    if 3.0 <= prod <= 15.0:
                        o2 = dict(o)
                        o2["_odd"], o2["_legs"] = round(prod, 2), legs
                        o2["_ptype"], o2["_real"] = "combo", True
                        risk_opts.append(o2)
                elif 1.40 <= prod <= 3.0:
                    o2 = dict(o)
                    o2["_odd"], o2["_legs"] = round(prod, 2), legs
                    o2["_ptype"], o2["_real"] = "combo", True
                    value_opts.append(o2)
                continue
            if _market_family(o["market"]) in banned:
                continue
            ro = _real_odd_for(o["market"], odds_map, home, away)
            final_odd = float(ro) if ro else float(o["odds"])
            o2 = dict(o)
            o2["_odd"], o2["_real"], o2["_legs"] = round(final_odd, 2), bool(ro), []
            ml = o["market"].lower()
            # Categorise every single pick into Banker / Value / Risk (owner rule):
            #  • RISK  = ONLY favourite -1.5 handicaps (must win by 2+).
            #  • VALUE = the sweet-spot 1.40–2.50 tips (goals lines, unders, DC12, team goals).
            #  • BANKER = very safe low-odds picks (ideal for combos / systems).
            if "-1.5" in ml and "handicap" in ml:
                o2["_ptype"] = "risk"
                risk_opts.append(o2)
            elif round(o["winprob"] * 10) >= 9:
                # Owner rule: EVERY 9- or 10-star single pick (≈86 %+ win chance) is a
                # Banker, regardless of odds — the safest picks always live in Banker.
                o2["_ptype"] = "banker"
                banker_opts.append(o2)
            elif 1.40 <= final_odd <= 2.60 and o["winprob"] >= 0.62:
                o2["_ptype"] = "value"
                value_opts.append(o2)
            elif o["winprob"] >= BANKER_WIN_PROB and final_odd >= 1.03:
                o2["_ptype"] = "banker"
                banker_opts.append(o2)
            # else: DROP it (owner 2026-07-10: fewer picks, but only ones we actually win.
            # A single with <62% win chance is a coin-flip and is no longer posted.)
        # Post the best pick of EACH available category for this match so all three
        # filters (Banker / Value / Risk) stay populated.
        cat_best = []
        if banker_opts:
            cat_best.append(("banker", max(banker_opts, key=lambda o: (o["winprob"], o["_odd"]))))
        if value_opts:
            cat_best.append(("value", max(value_opts, key=lambda o: (o["_ptype"] == "combo", o["winprob"], o["_odd"]))))
        if risk_opts:
            cat_best.append(("risk", max(risk_opts, key=lambda o: o["_odd"])))
        if not cat_best:
            continue
        for cat, best in cat_best:
            b = dict(best)
            b["_category"] = cat
            candidates.append((best["winprob"], r, b, kickoff))
    # order: value first, then risk, then bankers; within each by confidence/odds
    _catrank = {"value": 3, "combo": 3, "risk": 2, "banker": 1}
    candidates.sort(key=lambda x: (_catrank.get(x[2].get("_ptype"), 0), x[0], x[2]["_odd"]), reverse=True)
    ordered = candidates

    posted = 0
    now = datetime.now(timezone.utc).isoformat()
    for winprob, r, c, kickoff in ordered:
        if posted >= FOREBET_MAX_PER_RUN:
            break
        matchid = r.get("matchid") or f"{r['home']}-{r['away']}"
        tip_id = f"hqtip-a-{matchid}{c['sfx']}"
        category = c.get("_category", c.get("_ptype", "value"))
        lcode = (r.get("lcode") or "").strip().lower()
        cc = (r.get("cc") or "").strip().lower()
        # STABILITY (owner): once a match has a pick in this category, keep it FIXED
        # (same market + same odds) until kickoff — never swap it on later runs.
        prior = await db.tips.find_one({
            "source": "hq-auto", "status": "pending", "category": category,
            "home_team": r["home"], "away_team": r["away"]})
        if prior:
            if lcode and prior.get("league_code") != lcode:
                await db.tips.update_one(
                    {"id": prior["id"]}, {"$set": {"league_code": lcode, "country": cc}})
            continue
        if await db.tips.find_one({"id": tip_id}):
            continue
        home, away = r["home"], r["away"]
        ptype = c.get("_ptype", "value")
        # Safety net (owner rule): a bet-builder containing "Beide Teams treffen"
        # must NEVER also carry "Über 1.5 Tore" — BTTS already guarantees ≥2 goals.
        if ptype == "combo":
            _legs = c.get("_legs", [])
            if any((lg.get("kind") == "btts" or "beide teams treffen" in (lg.get("market", "") or "").lower())
                   for lg in _legs):
                # strip ONLY the redundant full-match "Über 1.5 Tore" — never the
                # first-half "Über 1.5 Tore 1. Halbzeit" leg (owner's Anderlecht builder).
                def _is_redundant_o15(lg):
                    mk = (lg.get("market", "") or "").lower()
                    if "halbzeit" in mk or "hz" in mk:
                        return False
                    return lg.get("kind") == "o15" or "über 1.5 tore" in mk
                _kept = [lg for lg in _legs if not _is_redundant_o15(lg)]
                if len(_kept) != len(_legs):
                    c["_legs"] = _kept
                    _p = 1.0
                    for lg in _kept:
                        _p *= float(lg.get("odds") or 1.0)
                    c["_odd"] = round(_p, 2)
                    _others = [lg for lg in _kept if lg.get("kind") != "btts"
                               and "beide teams treffen" not in (lg.get("market", "") or "").lower()]
                    c["market"] = (f"Beide Teams treffen + {_others[0].get('market', '')} ({len(_kept)}er-Bet-Builder)"
                                   if _others else "Beide Teams treffen")
        market = c["market"]
        odds, real = c["_odd"], c["_real"]
        # Stars now come straight from the win probability (owner rule): the old 8.5
        # ceiling is gone — a ≥96% pick shows the full 10 stars, 90% → 9, etc.
        stars = max(1, min(10, round(winprob * 10)))
        # Owner (2026-07-10): a "Beide Teams treffen" market is a wobbly bet — cap it at
        # 6★ so it can never look like a near-certain 9/10★ pick.
        if "beide teams treffen" in market.lower():
            stars = min(stars, 6)
        rating = float(stars)
        score = r.get("score") or "?"
        avg = r.get("avg") or "?"
        is_combo = ptype == "combo"
        n_legs = len(c.get("_legs", []))
        if is_combo:
            builder = ("Bet-Builder: beide Teams treffen + höhere Torlinie (ohne redundante Legs) aus EINEM Spiel"
                       if n_legs >= 3 else
                       "Bet-Builder: klassisches beide Teams treffen aus EINEM Spiel")
            analysis = (
                f"TipJarHQ-Kombi ({n_legs}er-Leg): {market} — höheres Risiko, Quote {odds:.2f}. "
                f"Erwartetes Ergebnis {score}, Ø {avg} Tore. Anstoß {kickoff}. "
                f"{builder} — automatisch von TipJarHQ."
            )
        elif ptype == "banker":
            analysis = (
                f"TipJarHQ-Banker: {market} — {stars}/10 Sterne, sicherer Banker (Quote {odds:.2f}). "
                f"Erwartetes Ergebnis {score}, Ø {avg} Tore. "
                f"Anstoß {kickoff}. {'Echte Buchmacher-Quote. ' if real else ''}"
                f"Ideal für Kombi- & Systemwetten — automatisch von TipJarHQ."
            )
        else:
            analysis = (
                f"TipJarHQ-Value: {market} — {stars}/10 Sterne bei Quote {odds:.2f}. "
                f"Erwartetes Ergebnis {score}, Ø {avg} Tore. "
                f"Anstoß {kickoff}. {'Echte Buchmacher-Quote. ' if real else ''}"
                f"Datenbasierter Value-Pick — automatisch von TipJarHQ."
            )
        combo_legs = c.get("_legs", []) if is_combo else []
        # Frontend-friendly single-match display: one fixture row with all selection
        # chips (settlement uses the separate `combo_legs` with kind/team info).
        display_legs = []
        if is_combo:
            display_legs = [{
                "match": f"{home} – {away}",
                "league": r.get("league") or (lcode.upper() if lcode else ""),
                "kickoff": kickoff,
                "selections": [lg["market"] for lg in combo_legs],
                "sel_odds": [f"{lg['odds']:.2f}" for lg in combo_legs],
            }]
        # Always show the real competition on the tip (owner: "bei Single-Tipps muss das
        # Turnier drauf sein"). Friendlies are NOT blocked — they're clearly labelled.
        _raw_lg = (r.get("league") or "").strip()
        _lg_hay = f"{_raw_lg} {lcode} {cc}".lower()
        if "friendl" in _lg_hay or "freundschaft" in _lg_hay or "testspiel" in _lg_hay:
            league_disp = "Freundschaftsspiel"
        elif _raw_lg:
            league_disp = _raw_lg.title()
        elif lcode:
            league_disp = lcode.upper()
        else:
            league_disp = cc or "TipJarHQ Pick"
        tip = {
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away,
            "match_time": kickoff,
            "country": cc, "league": league_disp, "league_code": lcode,
            "market": market,
            "odds": f"{odds:.2f}", "ai_rating": rating, "ai_analysis": analysis,
            "win_prob": round(winprob, 3), "pick_type": ptype, "category": category,
            "legs": display_legs, "combo_legs": combo_legs, "is_parlay": is_combo,
            "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": now,
        }
        await db.tips.insert_one(tip)
        posted += 1
        logger.info(f"HQ auto-posted (A/{ptype}): {home} vs {away} — {market} "
                    f"({round(winprob*100)}% @ {odds:.2f})")
    await _dedupe_hq_tips()
    return {"posted": posted, "scanned": len(rows), "candidates": len(candidates)}


async def forebet_loop():
    await asyncio.sleep(30)  # let startup settle
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            if await ensure_chromium():
                res = await forebet_autopost()
                logger.info(f"HQ loop A: {res}")
                logger.info(f"Expired auto-tips purged: {await purge_expired_autotips()}")
            else:
                logger.error("HQ loop A skipped: chromium unavailable — retrying in 20 min")
                await asyncio.sleep(20 * 60)
                continue
        except Exception as e:
            logger.error(f"HQ loop A error: {e}")
        await asyncio.sleep(3 * 3600)  # every 3 hours



# ---------------------------------------------------------------------------
# Predictz auto-tips: TipJarHQ reads predictz.com and auto-posts SAFE goals
# markets ("10-star" bankers: Over 0.5 / Over 1.5) ~24-72h before kickoff, so
# the user has ~50h lead time to build their system bets. Posts to the normal
# Rate Wall (no separate tab). German market labels.
# ---------------------------------------------------------------------------
PREDICTZ_MAX_PER_RUN = 15   # cap new safe picks per run
_MONTHS = {1: "Jan", 2: "Feb", 3: "Mär", 4: "Apr", 5: "Mai", 6: "Jun",
           7: "Jul", 8: "Aug", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Dez"}


def _predictz_date_paths() -> list[str]:
    """Tomorrow + day-after-tomorrow pages (covers the ~50h look-ahead window)."""
    today = datetime.now(timezone.utc).date()
    d2 = today + timedelta(days=2)
    return ["/predictions/tomorrow/", f"/predictions/{d2.strftime('%Y%m%d')}/"]


def _predictz_kickoff(r: dict, base_date) -> str:
    """Kickoff string for a predictz row: reuse forebet's exact time if the same
    match is on forebet, else use predictz's own HH:MM, else fall back to date."""
    matched = FOREBET_TIME_INDEX.get(f"{_norm_team(r.get('home'))}|{_norm_team(r.get('away'))}")
    if matched:
        return matched
    fuzzy = _forebet_time_for(r.get("home"), r.get("away"))
    if fuzzy:
        return fuzzy
    md = base_date + timedelta(days=r.get("day_offset", 1))
    tm = (r.get("time") or "").strip()
    m = re.match(r"^(\d{1,2}):([0-5]\d)$", tm)
    if m:
        return f"{md.strftime('%d/%m/%Y')} {int(m.group(1)):02d}:{m.group(2)}"
    return f"{md.day}. {_MONTHS.get(md.month, '')} {md.year}"


def _conf_adj(rating: float, conf: str) -> float:
    if conf == "ngreen":
        return min(10.0, rating + 0.5)
    if conf == "nred":
        return rating - 1.5
    return rating


def _predictz_candidates(r: dict) -> list[dict]:
    """Predictz is treated as SUPPLEMENTARY only — its predicted scores are unreliable
    (a '4-1' can end '0-2'), so we NEVER give its picks 9-10★. We derive only the
    genuinely safe 1+ goal market from the score, plus Predictz's own O/U-2.5 & BTTS
    tip columns, all capped low."""
    conf = r.get("conf")
    out = []
    # 1) Only the safe 1+ goal market from the (unreliable) predicted score
    ps = parse_pred_score(r.get("pred"))
    if ps and (ps[0] + ps[1]) >= 1:
        out.append({"sfx": "-g", "market": "Über 0.5 Tore", "odds": "1.08", "rating": _conf_adj(8.0, conf)})
    # 2) Over 2.5 tip (predictz O/U page) — capped, supplementary
    if (r.get("ou_tip") or "").strip().lower() == "over 2.5":
        out.append({"sfx": "-o25", "market": "Über 2.5 Tore", "odds": "1.55", "rating": _conf_adj(7.5, conf)})
    # 3) BTTS Yes tip (predictz BTTS page) — capped, supplementary
    if (r.get("btts_tip") or "").strip().lower() == "btts yes":
        out.append({"sfx": "-btts", "market": "Beide Teams treffen (BTTS)", "odds": "1.70", "rating": _conf_adj(7.5, conf)})
    return [c for c in out if round(c["rating"], 1) >= 7.5]


async def _index_forebet_times(url: str, limit: int = 250) -> int:
    """Populate FOREBET_TIME_INDEX from a forebet page (times only, no posting)
    so predictz future matches can display an exact kickoff time."""
    try:
        rows = await asyncio.wait_for(scrape_forebet_today(limit, url=url), timeout=SCRAPE_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning(f"forebet time-index scrape timed out ({url})")
        return 0
    except Exception as e:
        logger.warning(f"forebet time-index scrape failed ({url}): {e}")
        return 0
    n = 0
    for r in rows:
        if r.get("home") and r.get("away") and r.get("datetime"):
            _remember_forebet_match(r["home"], r["away"], _forebet_datetime(r["datetime"]))
            n += 1
    logger.info(f"Indexed {n} forebet kickoff times from {url.rsplit('/', 1)[-1]}")
    return n


async def predictz_autopost() -> dict:
    """Scrape predictz upcoming days, publish safe goals-market bankers as TipJarHQ."""
    if AUTOPOST_PAUSED:
        return {"posted": 0, "reason": "autopost paused (curated mode)"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    # Only auto-post from the start of TOMORROW (UTC) — today stays curated.
    _AUTOPOST_MIN_KO = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0)
    # enrich the kickoff-time index with forebet's tomorrow page (exact HH:MM)
    await _index_forebet_times("https://www.forebet.com/en/football-tips-and-predictions-for-tomorrow")
    try:
        rows = await asyncio.wait_for(scrape_predictz(_predictz_date_paths()), timeout=SCRAPE_TIMEOUT * 2)
    except asyncio.TimeoutError:
        logger.error("Predictz scrape timed out")
        return {"posted": 0, "reason": "scrape timeout"}
    except Exception as e:
        logger.error(f"Predictz scrape failed: {e}")
        return {"posted": 0, "reason": f"scrape error: {e}"}

    candidates = []
    _today = datetime.now(timezone.utc).date()
    for r in rows:
        if _league_blocked_predictz(r.get("league")):
            continue
        # store full match prediction (feeds the multi-system builder)
        try:
            home, away = r.get("home"), r.get("away")
            kickoff = _predictz_kickoff(r, _today)
            ps = parse_pred_score(r.get("pred"))
            ph, pa = ps if ps else (None, None)
            predl = (r.get("pred") or "").lower()
            if "home" in predl or (ps and ph > pa):
                fav = "home"
            elif "away" in predl or (ps and pa > ph):
                fav = "away"
            else:
                fav = "draw"
            btts = ((r.get("btts_tip") or "").strip().lower() == "btts yes") or \
                   bool(ps and ph >= 1 and pa >= 1)
            over25 = ((r.get("ou_tip") or "").strip().lower() == "over 2.5") or \
                     bool(ps and (ph + pa) >= 3)
            await store_match_prediction(
                "predictz", r.get("matchid") or f"{home}-{away}", home, away, kickoff,
                ph, pa, fav, None, btts, over25, r.get("conf"),
                league=(r.get("league") or "").title())
        except Exception as e:
            logger.warning(f"predictz prediction store failed: {e}")
        for c in _predictz_candidates(r):
            candidates.append((round(c["rating"], 1), r, c))
    candidates.sort(key=lambda x: x[0], reverse=True)

    # Predictz is only trusted when FOREBET agrees on the same match (owner rule).
    fb_docs = await db.match_predictions.find(
        {"source": "forebet"},
        {"_id": 0, "home": 1, "away": 1, "ph": 1, "pa": 1, "total": 1, "btts": 1, "over25": 1},
    ).to_list(2000)
    fb_map = {_match_key(x.get("home"), x.get("away")): x for x in fb_docs}

    def _forebet_agrees(market: str, fb: dict) -> bool:
        if not fb:
            return False
        m = (market or "").lower()
        total = fb.get("total") or 0
        if "über 0.5 tore" in m:
            return total >= 2
        if "über 2.5 tore" in m:
            return bool(fb.get("over25")) or total >= 3
        if "beide teams treffen" in m or "btts" in m:
            return bool(fb.get("btts")) or ((fb.get("ph") or 0) >= 1 and (fb.get("pa") or 0) >= 1)
        return False

    posted = 0
    now = datetime.now(timezone.utc).isoformat()
    d = datetime.now(timezone.utc).date()
    for rating, r, c in candidates:
        if posted >= PREDICTZ_MAX_PER_RUN:
            break
        matchid = r.get("matchid") or f"{r['home']}-{r['away']}"
        tip_id = f"hqtip-b-{matchid}{c['sfx']}"
        market = c["market"]
        home, away = r["home"], r["away"]
        # owner: recognised, bettable leagues only (+ no women/youth)
        _lg = (r.get("league") or "").lower()
        if _is_women_or_youth(home) or _is_women_or_youth(away) or \
           any(b in f" {_lg} " for b in SLIP_BLOCK_KEYWORDS) or \
           not any(k in _lg for k in SLIP_LEAGUE_KEYWORDS):
            continue
        if _team_or_league_blocked(home, away, r.get("league")):
            continue  # owner blacklist (teams/leagues)
        # Owner rule: only trust Predictz when Forebet agrees on the same match.
        if not _forebet_agrees(market, fb_map.get(_match_key(home, away))):
            continue
        match_time = _predictz_kickoff(r, d)
        _ko = _parse_kickoff(match_time)
        if _ko and _ko < _AUTOPOST_MIN_KO:
            continue  # today stays curated — only post tomorrow onward
        existing = await db.tips.find_one({"id": tip_id}, {"match_time": 1})
        if existing:
            # backfill kickoff time onto tips posted before we scraped times
            if ":" in match_time and existing.get("match_time") != match_time:
                await db.tips.update_one({"id": tip_id}, {"$set": {"match_time": match_time}})
            continue
        odds, real = await apply_real_odds(market, c["odds"], home, away, match_time)
        # Owner rule: never post coin-flip markets. Low-odd safe goals ARE allowed as
        # bankers (useful for combos). Tag value (odd≥1.60) vs banker.
        try:
            _od = float(odds)
        except Exception:
            _od = 0.0
        if _market_family(market) in {"btts", "o25", "o25_btts", "gamble"}:
            continue
        ptype = "value" if _od >= VALUE_MIN_ODDS else "banker"
        # Predictz picks also carry a Banker/Value category so they surface in the
        # Single-Picks filters (sweet-spot 1.40–2.60 = Value, safer = Banker).
        pcategory = "value" if 1.40 <= _od <= 2.60 else "banker"
        # STABILITY (owner): keep the first pick per match+category fixed — don't add a
        # second (e.g. Predictz value on a match Forebet already gave a value pick).
        if await db.tips.find_one({
            "source": "hq-auto", "status": "pending", "category": pcategory,
            "home_team": home, "away_team": away}):
            continue
        league = (r.get("league") or "").title() or "TipJarHQ Pick"
        if "friendl" in league.lower() or "freundschaft" in league.lower():
            league = "Freundschaftsspiel"
        analysis = (
            f"Sicherer Tor-Banker: erwartetes Ergebnis {r.get('pred')}. "
            f"{market} ist bei diesem Spielbild ein starker Pick. "
            f"{'Echte Buchmacher-Quote. ' if real else ''}"
            f"Rechtzeitig gepostet, damit du dein Systemwette-Programm aufbauen kannst — "
            f"automatisch von TipJarHQ."
        )
        tip = {
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away,
            "match_time": match_time,
            "country": "", "league": league, "market": market,
            "odds": odds, "ai_rating": rating, "ai_analysis": analysis,
            "pick_type": ptype, "category": pcategory,
            "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": now,
        }
        await db.tips.insert_one(tip)
        posted += 1
        logger.info(f"HQ auto-posted (B): {home} vs {away} — {market} ({rating})")
    await _dedupe_hq_tips()
    return {"posted": posted, "scanned": len(rows), "candidates": len(candidates)}


async def predictz_loop():
    await asyncio.sleep(90)  # let startup + forebet (fills time index) settle first
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            if await ensure_chromium():
                res = await predictz_autopost()
                logger.info(f"HQ loop B: {res}")
            else:
                logger.error("HQ loop B skipped: chromium unavailable — retrying in 20 min")
                await asyncio.sleep(20 * 60)
                continue
        except Exception as e:
            logger.error(f"HQ loop B error: {e}")
        await asyncio.sleep(3 * 3600)  # every 3 hours


# ---------------------------------------------------------------------------
# Smart Bet: data-driven PLAYER PROPS from API-Football season statistics.
# API-Football does NOT provide prop predictions/odds, so we compute them from
# each player's real season stats (shots, shots on target, fouls, cards, saves,
# goals) for the regular starters of the teams in our upcoming whitelist matches.
# NOTE: markets NOT covered by API-Football data (offsides, corners, throw-ins,
# free-kicks, headed/long-range goals, corners-by-10min) are intentionally omitted.
# ---------------------------------------------------------------------------
PLAYER_CACHE_TTL_H = 24
SMART_MAX_MATCHES = 14       # upcoming matches processed per run
SMART_PROPS_PER_TEAM = 6     # best props kept per team (1 per player) — massive builder
SMART_MIN_RATING = 7.0
SMART_LOOKAHEAD_H = 120      # only matches within the next 5 days

# Top leagues where bookmakers offer PLAYER prop markets (owner: Smart Picks only here —
# NOT qualifiers 'wcq/ecq/cq', NOT Brazil 'br1/br2', NOT minor South-American/Asian leagues).
SMART_LEAGUE_CODES = {
    # National-team finals (owner: "Smart Picks für die WM" ok) — NOT qualifiers
    "wc", "ec", "euro",
    # Top European leagues (1st/2nd tier) — real player markets
    "en1", "en2", "ge1", "ge2", "sp1", "sp2", "it1", "it2", "fr1", "fr2",
    "ne1", "po1", "be1", "tu1", "sc1",
    # USA + Saudi
    "mls", "ml1", "us1", "sa1",
}


async def _apifootball_async(path: str, params: dict):
    return await asyncio.to_thread(_apifootball, path, params)


# ---------------------------------------------------------------------------
# Real bookmaker odds (API-Football /odds) — replaces the old hard-coded odds so
# every tip carries a realistic quote. Fetched per match, 6h-cached in odds_cache.
# ---------------------------------------------------------------------------
ODDS_CACHE_TTL_H = 6


def _find_fixture_id(team_id: int, opponent_name: str, dates: list, year: int):
    for date in dates:
        for season in (year, year - 1):
            fixtures = _apifootball("/fixtures", {"team": team_id, "date": date, "season": season})
            if not fixtures:
                continue
            for fx in fixtures:
                th = fx.get("teams", {}).get("home", {}).get("name", "")
                ta = fx.get("teams", {}).get("away", {}).get("name", "")
                if _teams_match(th, opponent_name) or _teams_match(ta, opponent_name):
                    return fx.get("fixture", {}).get("id"), season
            break
    return None, None


def _parse_odds(resp) -> dict:
    """Normalise API-Football /odds response into {market_key: float}. First
    bookmaker offering a market wins."""
    out = {}
    if not resp:
        return out

    def setd(k, val):
        if val and k not in out:
            try:
                out[k] = round(float(val), 2)
            except Exception:
                pass

    for entry in resp:
        for bm in entry.get("bookmakers", []):
            for bet in bm.get("bets", []):
                nm = (bet.get("name") or "").strip()
                vals = {v.get("value"): v.get("odd") for v in bet.get("values", [])}
                if nm == "Goals Over/Under":
                    setd("over05", vals.get("Over 0.5"))
                    setd("over15", vals.get("Over 1.5"))
                    setd("over25", vals.get("Over 2.5"))
                    setd("under25", vals.get("Under 2.5"))
                    setd("under35", vals.get("Under 3.5"))
                elif nm in ("Both Teams Score", "Both Teams To Score"):
                    setd("btts", vals.get("Yes"))
                elif nm == "Home/Away":  # = Draw No Bet
                    setd("dnb_home", vals.get("Home"))
                    setd("dnb_away", vals.get("Away"))
                elif nm == "Match Winner":
                    setd("win_home", vals.get("Home"))
                    setd("win_away", vals.get("Away"))
                elif nm == "Double Chance":
                    setd("dc_1x", vals.get("Home/Draw"))
                    setd("dc_x2", vals.get("Draw/Away"))
                    setd("dc_12", vals.get("Home/Away"))
    return out


async def ensure_match_odds(home: str, away: str, kickoff: str) -> dict:
    """Fetch + 6h-cache real bookmaker odds for a match. Returns {} if unavailable."""
    if not API_FOOTBALL_KEY or not home or not away:
        return {}
    ko = _parse_kickoff(kickoff)
    if not ko:
        return {}
    key = _match_key(home, away)
    now = datetime.now(timezone.utc)
    cached = await db.odds_cache.find_one({"key": key})
    if cached:
        try:
            if now - datetime.fromisoformat(cached["cached_at"]) < timedelta(hours=ODDS_CACHE_TTL_H):
                return cached.get("odds", {})
        except Exception:
            pass
    tid = await resolve_team_id(home)
    opp = away
    if not tid:
        tid = await resolve_team_id(away)
        opp = home
    odds = {}
    if tid:
        dates = [ko.date().isoformat(),
                 (ko + timedelta(days=1)).date().isoformat(),
                 (ko - timedelta(days=1)).date().isoformat()]
        fid, season = await asyncio.to_thread(_find_fixture_id, tid, opp, dates, ko.year)
        if fid:
            resp = await _apifootball_async("/odds", {"fixture": fid, "season": season or ko.year})
            odds = _parse_odds(resp)
    await db.odds_cache.update_one(
        {"key": key}, {"$set": {"key": key, "odds": odds, "cached_at": now.isoformat()}}, upsert=True)
    return odds


def _real_odd_for(market: str, odds: dict, home: str, away: str):
    """Map one of our German market strings to a real bookmaker odd, or None."""
    if not odds:
        return None
    m = (market or "").lower()
    if "über 2.5 tore" in m:
        return odds.get("over25")
    if "über 1.5 tore" in m:
        return odds.get("over15")
    if "über 0.5 tore" in m:
        return odds.get("over05")
    if "unter 2.5 tore" in m:
        return odds.get("under25")
    if "unter 3.5 tore" in m:
        return odds.get("under35")
    if "beide teams treffen" in m or "btts" in m:
        return odds.get("btts")
    if "doppelte chance" in m and "+" not in m:
        if "1x" in m:
            return odds.get("dc_1x")
        if "x2" in m:
            return odds.get("dc_x2")
        if "12" in m:
            return odds.get("dc_12")
    if "draw no bet" in m:
        if home and home.lower() in m:
            return odds.get("dnb_home")
        if away and away.lower() in m:
            return odds.get("dnb_away")
    return None


async def apply_real_odds(market, fallback, home, away, kickoff):
    """Return (odds_str, is_real). Real bookmaker odд if available, else fallback."""
    try:
        odds = await ensure_match_odds(home, away, kickoff)
    except Exception as e:
        logger.warning(f"odds fetch failed {home} vs {away}: {e}")
        odds = {}
    real = _real_odd_for(market, odds, home, away)
    if real:
        return f"{real:.2f}", True
    return str(fallback), False



def _smart_seasons(kickoff_str: str) -> list[int]:
    ko = _parse_kickoff(kickoff_str)
    yr = ko.year if ko else datetime.now(timezone.utc).year
    return [yr, yr - 1]  # summer months = new season may be empty → fall back


def _prob_over(line: float, lam: float) -> float:
    """Poisson P(count >= ceil(line))."""
    if lam <= 0:
        return 0.0
    need = int(math.floor(line)) + 1  # 0.5→1, 1.5→2, 2.5→3
    cdf = sum(math.exp(-lam) * lam ** k / math.factorial(k) for k in range(need))
    return max(0.0, min(0.99, 1 - cdf))


def _rating_from_prob(p: float) -> float:
    # 9-10★ reserved for near-certain props (must not lose); calibrated conservatively
    if p >= 0.90: return 9.5
    if p >= 0.84: return 9.0
    if p >= 0.77: return 8.5
    if p >= 0.70: return 8.0
    if p >= 0.62: return 7.5
    return 7.0


def _odds_from_prob(p: float) -> str:
    if p <= 0:
        return "2.00"
    return f"{max(1.05, round(1 / p, 2)):.2f}"


def _build_player_props(pstat: dict) -> list[dict]:
    """Return candidate props for one player's season stat block."""
    player = pstat.get("player", {}) or {}
    name = player.get("name") or ""
    stats = (pstat.get("statistics") or [{}])[0] or {}
    games = stats.get("games") or {}
    apps = games.get("appearences") or 0
    lineups = games.get("lineups") or 0
    pos = (games.get("position") or "").lower()
    if not name or apps < 6:
        return []
    is_gk = pos.startswith("goal")
    # need a regular starter (assumed to start the next match); GKs judged by apps
    if not is_gk and lineups < 8:
        return []
    denom = max(lineups, 1) if not is_gk else max(apps, 1)

    shots = stats.get("shots") or {}
    goals = stats.get("goals") or {}
    fouls = stats.get("fouls") or {}
    cards = stats.get("cards") or {}
    sot = (shots.get("on") or 0) / denom
    sh = (shots.get("total") or 0) / denom
    fc = (fouls.get("committed") or 0) / denom
    fd = (fouls.get("drawn") or 0) / denom
    gl = (goals.get("total") or 0) / denom
    sv = (goals.get("saves") or 0) / max(apps, 1)
    yc = (cards.get("yellow") or 0) / max(apps, 1)

    cands = []

    def add(line, lam, label, kind):
        p = _prob_over(line, lam)
        cands.append({"market": f"{name} — {label}", "prob": p,
                      "rating": _rating_from_prob(p), "odds": _odds_from_prob(p),
                      "kind": kind, "avg": lam, "line": line, "player": name})

    if is_gk:
        if sv >= 3.0:
            add(2.5 if sv >= 4.0 else 1.5, sv,
                "Über 2,5 Paraden" if sv >= 4.0 else "Über 1,5 Paraden", "saves")
    else:
        if sot >= 1.1:
            add(0.5, sot, "Über 0,5 Schüsse aufs Tor (1+)", "sot")
        if sh >= 2.6:
            add(1.5, sh, "Über 1,5 Schüsse (2+)", "shots")
        elif sh >= 1.6:
            add(0.5, sh, "Über 0,5 Schüsse (1+)", "shots")
        if fc >= 1.3:
            add(0.5, fc, "Über 0,5 Fouls begangen", "fouls_c")
        if fd >= 1.3:
            add(0.5, fd, "Über 0,5 mal gefoult", "fouls_d")
        if gl >= 0.5:
            # anytime scorer: cap rating (inherently riskier)
            p = _prob_over(0.5, gl)
            cands.append({"market": f"{name} — Torschütze (Anytime)", "prob": p,
                          "rating": min(8.0, _rating_from_prob(p)),
                          "odds": _odds_from_prob(p), "kind": "scorer", "avg": gl,
                          "line": 0.5, "player": name})
        if yc >= 0.45:
            p = min(0.85, yc)
            cands.append({"market": f"{name} — sieht eine Karte", "prob": p,
                          "rating": min(7.5, _rating_from_prob(p)),
                          "odds": _odds_from_prob(p), "kind": "card", "avg": yc,
                          "line": 0.5, "player": name})

    return [c for c in cands if c["rating"] >= SMART_MIN_RATING]


async def get_team_players(team_id: int, seasons: list[int]) -> list[dict]:
    """Fetch (and 24h-cache) all players + season stats for a team."""
    now = datetime.now(timezone.utc)
    cached = await db.player_stats_cache.find_one({"team_id": team_id})
    if cached:
        ts = cached.get("cached_at")
        try:
            age = now - datetime.fromisoformat(ts)
            if age < timedelta(hours=PLAYER_CACHE_TTL_H):
                return cached.get("players", [])
        except Exception:
            pass
    players = []
    for season in seasons:
        page = 1
        got = []
        while page <= 5:
            resp = await _apifootball_async("/players", {"team": team_id, "season": season, "page": page})
            if not resp:
                break
            got.extend(resp)
            # paging info isn't returned by _apifootball (it strips to 'response'); stop when short page
            if len(resp) < 20:
                break
            page += 1
        if got:
            players = got
            break
    await db.player_stats_cache.update_one(
        {"team_id": team_id},
        {"$set": {"team_id": team_id, "players": players, "cached_at": now.isoformat()}},
        upsert=True)
    return players


async def _team_best_props(team_name: str, seasons: list[int]) -> list[dict]:
    tid = await resolve_team_id(team_name)
    if not tid:
        return []
    players = await get_team_players(tid, seasons)
    all_props = []
    for pstat in players:
        all_props.extend(_build_player_props(pstat))
    all_props.sort(key=lambda c: c["rating"], reverse=True)
    # one prop per player, keep the best few
    seen, out = set(), []
    for c in all_props:
        pl = c["market"].split(" — ")[0]
        if pl in seen:
            continue
        seen.add(pl)
        out.append(c)
        if len(out) >= SMART_PROPS_PER_TEAM:
            break
    return out


async def smart_autopost() -> dict:
    """Generate player-prop 'Smart Bet' tips — ONLY for top leagues where bookmakers
    actually offer player markets (Premier League, La Liga, World Cup, UCL …). Owner:
    NO player markets for qualifiers, Brazilian or other minor leagues."""
    if not API_FOOTBALL_KEY:
        return {"posted": 0, "reason": "API_FOOTBALL_KEY not configured"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    now = datetime.now(timezone.utc)
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1000)
    # upcoming, TOP-league only, within lookahead window, de-duped
    upcoming, seen = [], set()
    for p in preds:
        if not _pred_whitelisted(p):
            continue
        if (p.get("league_code") or "").strip().lower() not in SMART_LEAGUE_CODES:
            continue  # player markets only exist for major leagues
        ko = _parse_kickoff(p.get("kickoff"))
        if not ko:
            continue
        h = (ko - now).total_seconds() / 3600
        if h < 2 or h > SMART_LOOKAHEAD_H:
            continue
        key = _match_key(p.get("home"), p.get("away"))
        if key in seen:
            continue
        seen.add(key)
        upcoming.append((ko, p))
    upcoming.sort(key=lambda x: x[0])
    posted, scanned, candidates = 0, 0, 0
    for ko, p in upcoming[:SMART_MAX_MATCHES]:
        scanned += 1
        seasons = _smart_seasons(p.get("kickoff"))
        home, away = p.get("home"), p.get("away")
        home_props = await _team_best_props(home, seasons)
        away_props = await _team_best_props(away, seasons)
        for c in home_props:
            c["team"] = home
        for c in away_props:
            c["team"] = away
        props = home_props + away_props
        candidates += len(props)
        mkey = hashlib.md5(_match_key(home, away).encode()).hexdigest()[:8]
        # Owner (2026-07-11): bundle ALL props of a match into ONE massive Bet-Builder
        # instead of many separate picks. Includes shots / shots-on-target / fouls / cards
        # (from _build_player_props) + a corner market. Player props can't auto-settle, so
        # the whole builder stays pending until resolved in the admin Pick-Manager.
        if len(props) < 2:
            continue
        tip_id = f"smart-{mkey}-builder"
        if await db.tips.find_one({"id": tip_id}, {"_id": 1}):
            continue
        combo_legs = [{"home": home, "away": away, "market": c["market"],
                       "odds": str(c["odds"]), "kind": c.get("kind", "player"),
                       "player": c.get("player", ""), "line": c.get("line"),
                       "team": c.get("team", ""), "status": "open"}
                      for c in props]
        combo_legs.append({"home": home, "away": away, "market": "Über 8.5 Ecken",
                           "odds": "1.80", "kind": "corner_o", "line": 8.5,
                           "team": "", "status": "open"})
        prod = 1.0
        for lg in combo_legs:
            try:
                prod *= float(lg["odds"])
            except Exception:
                pass
        # Frontend display leg (one match, all selections bundled) — mirrors AI bet-builders
        display_legs = [{
            "match": f"{home} – {away}",
            "league": "TipJarHQ Smart Pick",
            "kickoff": p.get("kickoff") or "",
            "selections": [lg["market"] for lg in combo_legs],
            "sel_odds": [str(lg["odds"]) for lg in combo_legs],
            "status": "pending",
        }]
        avg_rating = round(sum(c["rating"] for c in props) / len(props), 1)
        analysis = (
            f"TipJarHQ Mega Bet-Builder: {len(combo_legs)} datenbasierte Spieler-Props & Team-Märkte "
            f"(Schüsse, Schüsse aufs Tor, Fouls, Ecken …) für {home} vs {away}. "
            f"Anstoß {p.get('kickoff')}. Quoten sind Schätzungen."
        )
        await db.tips.insert_one({
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away,
            "match_time": p.get("kickoff") or "",
            "country": p.get("country") or "", "league": "TipJarHQ Smart Pick",
            "league_code": p.get("league_code") or "",
            "market": f"{home} vs {away} — Mega Bet-Builder ({len(combo_legs)} Legs)",
            "odds": f"{round(prod, 2)}", "combo_legs": combo_legs, "is_parlay": True,
            "ai_rating": avg_rating, "ai_analysis": analysis,
            "legs": display_legs, "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "smart", "created_at": datetime.now(timezone.utc).isoformat(),
        })
        posted += 1
    logger.info(f"Smart Bet run: posted {posted}, matches {scanned}, candidates {candidates}")
    return {"posted": posted, "matches": scanned, "candidates": candidates}


async def generate_smart_from_idea(text: str, images_b64: list | None = None) -> dict | None:
    """Turn a fan's free-text insider hint (optionally with stat/table screenshots) into
    a clever 'Smart Bet'. The KI decides the teams, a smart low/mid-risk market, a rating
    and a short German analysis. Returns None when the idea isn't actionable enough."""
    if (not text and not images_b64) or not EMERGENT_LLM_KEY:
        return None
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"smartidea-{uuid.uuid4()}",
            system_message=(
                "You are TipJar's Smart Bet strategist. A football fan sends an insider hint or a "
                "screenshot — a free-text tip, a bet-builder / accumulator slip, a stats sheet, or a "
                "hand-written analysis notebook — about an UPCOMING match. Turn it into ONE clever "
                "'smart bet' for the SINGLE most prominent match on the input. If several selections "
                "belong to that match (a bet-builder), COMBINE them into one market string joined with "
                " ' · ' (e.g. 'El Aynaoui 1+ Foul · Über 1 Tor · Beide treffen'). If the input is a "
                "multi-match accumulator, pick the single headline/most interesting match and build the "
                "smart bet from it. Identify the two REAL teams (full names, keep the language used, "
                "e.g. 'Frankreich', 'Marokko'). "
                "Respond with ONLY a compact JSON object, no markdown, with keys: "
                "actionable (bool), home_team (str), away_team (str), market (str, in German), "
                "match_time (str: the match date & kickoff EXACTLY as printed if visible, normalised to "
                "'DD/MM/YYYY HH:MM' when possible, e.g. a slip showing 'THU 9 JUL 21:00' → '09/07/2026 21:00'; "
                "empty string if no date is shown), "
                "rating (number 1-10), odds (string like '1.85' or '' if unknown), "
                "analysis (str, a punchy 1-4 sentence German breakdown of the selections). "
                "Set actionable=false ONLY if you truly cannot identify a home team or any usable bet."
            ),
        ).with_model(AI_MODEL_PROVIDER, AI_MODEL)
        kwargs = {"text": f"Fan hint: {text[:600] if text else '(see images)'}"}
        if images_b64:
            kwargs["file_contents"] = [ImageContent(image_base64=b) for b in images_b64[:3]]
        resp = await chat.send_message(UserMessage(**kwargs))
        raw = (resp if isinstance(resp, str) else str(resp)).strip()
        s, e = raw.find("{"), raw.rfind("}")
        if s == -1 or e == -1:
            return None
        data = json.loads(raw[s:e + 1])
        if not data.get("actionable") or not data.get("market") or not data.get("home_team"):
            return None
        return data
    except Exception as ex:
        logger.error(f"generate_smart_from_idea failed: {ex}")
        return None


def find_upcoming_fixture(team_id: int, opponent_name: str):
    """Find the team's next scheduled fixture vs the given opponent — used to attach a
    REAL kickoff date/time to KI-generated smart picks (we never post without a time)."""
    resp = _apifootball("/fixtures", {"team": team_id, "next": 15})
    if not resp:
        return None
    for fx in resp:
        th = (fx.get("teams", {}).get("home", {}) or {}).get("name", "")
        ta = (fx.get("teams", {}).get("away", {}) or {}).get("name", "")
        if _teams_match(th, opponent_name) or _teams_match(ta, opponent_name):
            lg = fx.get("league") or {}
            return {"home_name": th, "away_name": ta,
                    "date_iso": (fx.get("fixture") or {}).get("date"),
                    "league": lg.get("name", ""), "country": lg.get("country", "")}
    return None


async def smart_loop():
    await asyncio.sleep(150)  # let predictions populate (forebet+predictz) first
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            if API_FOOTBALL_KEY:
                logger.info(f"HQ loop C (Smart): {await smart_autopost()}")
        except Exception as e:
            logger.error(f"smart_loop error: {e}")
        await asyncio.sleep(12 * 3600)  # every 12 hours (season stats change slowly)


# ---------------------------------------------------------------------------
# LIVE engine: re-offer our pending pre-match AI picks (8-9★ Über 0.5 / BTTS /
# Über 2.5 …) while their match is IN-PLAY and the bet has not yet landed, at the
# now-higher live odds — but ONLY when there is still real pressure (shots/corners).
# Dead, flat games are skipped. Live tips auto-settle from the final score.
# ---------------------------------------------------------------------------
LIVE_INPLAY_STATUSES = {"1H", "2H", "ET", "BT", "P", "LIVE", "INT"}
LIVE_MAX_TIPS = 12
LIVE_POLL_SECONDS = 3 * 60
LIVE_STAT_CALL_CAP = 20  # max /fixtures/statistics calls per live run (quota guard)


def _market_team_side(market: str, home: str, away: str):
    """Which side a team-specific market refers to ('home'/'away') using the team's
    UNIQUE tokens, so 'Atletico Madrid Über 0.5' → away even in Real–Atlético."""
    mt = _sig_tokens(market)
    if not mt:
        return None
    ht, at = _sig_tokens(home), _sig_tokens(away)
    h_only = (ht - at) & mt
    a_only = (at - ht) & mt
    if a_only and not h_only:
        return "away"
    if h_only and not a_only:
        return "home"
    return None


def _live_bet_landed(market: str, hg, ag, home: str, away: str):
    """True=won, False=not yet/lost, None=not a goal-progress market (skip)."""
    m = (market or "").lower()
    hg, ag = hg or 0, ag or 0
    total = hg + ag
    if any(k in m for k in ("draw no bet", "doppelte chance", "genaues ergebnis", "unentschieden")):
        return None
    if "über 2.5" in m and ("beide" in m or "btts" in m):
        return total >= 3 and hg >= 1 and ag >= 1
    if "beide teams treffen" in m or "btts" in m:
        return hg >= 1 and ag >= 1
    if "über 2.5" in m:
        return total >= 3
    if "über 1.5" in m:
        return total >= 2
    if "über 0.5" in m:
        side = _market_team_side(market, home, away)
        if side == "home":
            return hg >= 1
        if side == "away":
            return ag >= 1
        return total >= 1
    return None


def _poisson_at_least(k: int, lam: float) -> float:
    """P(X >= k) for a Poisson(lam) variable — used to price live goal markets."""
    if k <= 0:
        return 1.0
    cum, term = 0.0, math.exp(-lam)
    for i in range(0, k):
        if i > 0:
            term *= lam / i
        cum += term
    return max(0.0, min(1.0, 1.0 - cum))


def _live_odd(market: str, minute: int, total_goals: int = 0) -> float:
    """Realistic live odds derived from goals STILL needed + time remaining (not just
    the minute). Prevents the inflated odds we used to show (e.g. Über 1.5 at 45'/0:0
    was 3.75 vs a real ~2.15)."""
    m = (market or "").lower()
    rem = max(90 - min(max(minute, 0), 90), 1)
    RATE_TOTAL = 0.034   # total goals per minute in a live, pressure-checked game
    RATE_TEAM = 0.018    # a single specific team scoring, per minute
    gm = re.search(r"über\s+(\d+)\.5", m)
    if gm and "über 0.5" not in m and "beide" not in m and "btts" not in m:
        line = int(gm.group(1))
        needed = (line + 1) - int(total_goals or 0)
        p = _poisson_at_least(needed, RATE_TOTAL * rem)
    elif "beide teams treffen" in m or "btts" in m:
        pe = _poisson_at_least(1, RATE_TEAM * rem)
        p = pe * pe
    elif "über 0.5" in m:
        p = _poisson_at_least(1, RATE_TEAM * rem)
    else:
        p = _poisson_at_least(1, RATE_TOTAL * rem)
    p = max(0.04, min(0.96, p))
    return round(max(1.05, min(1.0 / p, 15.0)), 2)


def _live_stat_totals(stats):
    sog = corners = shots = 0
    for team in (stats or []):
        for s in (team.get("statistics") or []):
            typ = (s.get("type") or "").lower()
            val = s.get("value")
            if isinstance(val, str):
                val = int(re.sub(r"[^0-9]", "", val) or 0)
            val = val or 0
            if "shots on goal" in typ:
                sog += val
            elif "corner" in typ:
                corners += val
            elif "total shots" in typ:
                shots += val
    return sog, corners, shots


def _live_pressure_ok(stats, minute: int) -> bool:
    """Owner's 'be careful' guard: only re-offer if the game is still live-dangerous."""
    if not stats:
        return minute < 60  # no live stats (obscure league) → only early, plenty of time
    sog, corners, shots = _live_stat_totals(stats)
    if minute >= 80:
        return sog >= 4 or corners >= 8
    if minute >= 60:
        return sog >= 2 or corners >= 4 or shots >= 8
    return sog >= 1 or corners >= 2 or shots >= 4


def _align_goals(fx, home_team):
    """Return goals oriented to OUR tip's home/away (fixture order may differ).
    Uses token-overlap COUNT (not a boolean match) so same-city derbies like
    Real–Atlético (shared 'Madrid') are oriented correctly."""
    teams = fx.get("teams") or {}
    th = (teams.get("home") or {}).get("name") or ""
    ta = (teams.get("away") or {}).get("name") or ""
    g = fx.get("goals") or {}
    gh, ga = g.get("home") or 0, g.get("away") or 0
    ho = _sig_tokens(home_team)
    hh = len(_sig_tokens(th) & ho)
    ha = len(_sig_tokens(ta) & ho)
    return (gh, ga) if hh >= ha else (ga, gh)


def _find_live_fixture(live, home, away):
    def amatch(a, b):
        ca, cb = _team_core(a), _team_core(b)
        if ca and cb and (ca == cb or ca in cb or cb in ca):
            return True  # alias/accent/language-aware (Deutschland==Germany)
        return _teams_match(a, b)
    for f in live:
        teams = f.get("teams") or {}
        th = (teams.get("home") or {}).get("name") or ""
        ta = (teams.get("away") or {}).get("name") or ""
        if (amatch(th, home) and amatch(ta, away)) or \
           (amatch(th, away) and amatch(ta, home)):
            return f
    return None


def _fixture_league_label(fx) -> str:
    """Human-readable competition name for a live fixture (owner: every live pick MUST
    show its league). Friendlies are labelled 'Club Friendlies' / 'Freundschaftsspiel'.
    Country is shown separately by the frontend, so it is NOT baked into the name."""
    lg = (fx or {}).get("league") or {}
    name = (lg.get("name") or "").strip()
    country = (lg.get("country") or "").strip()
    low = f"{name} {country}".lower()
    if "friendl" in low or "freundschaft" in low:
        return "Club Friendlies" if "club" in low else "Freundschaftsspiel"
    return name or "Live-Spiel"


def _fixture_country(fx) -> str:
    """Country for the live pick, blank for global 'World' competitions (friendlies)."""
    country = (((fx or {}).get("league") or {}).get("country") or "").strip()
    return "" if country.lower() in ("world", "") else country



async def live_autopost() -> dict:
    if not API_FOOTBALL_KEY:
        return {"posted": 0, "reason": "no API-Football key"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    live = _apifootball("/fixtures", {"live": "all"}) or []
    live_by_id = {str((f.get("fixture") or {}).get("id")): f for f in live}
    now = datetime.now(timezone.utc).isoformat()

    # 1) settle/close live tips whose match has ended. A live pick is graded the moment
    #    its fixture reports a finished status (FT/AET/PEN) — even if the match still
    #    lingers in the live=all feed for a few minutes. Stale, unresolvable and clearly
    #    over (>3.5h since kickoff) tips are settled via a team lookup or dropped, so a
    #    live pick never stays "open" once the game is over.
    closed = 0
    existing = await db.tips.find({"source": "hq-live", "status": "live"}, {"_id": 0}).to_list(200)
    now_dt = datetime.now(timezone.utc)
    for lt in existing:
        fid = str(lt.get("fixture_id") or "")
        f0 = live_by_id.get(fid)
        if not f0 and fid:
            fxs = _apifootball("/fixtures", {"id": fid})
            f0 = fxs[0] if fxs else None
        ko = _parse_kickoff(lt.get("match_time"))
        stale = bool(ko and ko < now_dt - timedelta(hours=LIVE_MAX_OPEN_HOURS))
        # 1) finished fixture in feed → grade from its final score (most accurate)
        if f0:
            short = ((f0.get("fixture") or {}).get("status") or {}).get("short")
            if short in FINISHED_STATUSES:
                hg, ag = _align_goals(f0, lt["home_team"])
                res = _live_bet_landed(lt.get("market"), hg, ag, lt["home_team"], lt["away_team"])
                new_status = "won" if res else ("lost" if res is False else "void")
                await db.tips.update_one({"id": lt["id"]}, {"$set": {
                    "status": new_status, "final_home": hg, "final_away": ag,
                    "settled_by": "auto-live", "settled_at": now}})
                closed += 1
                continue
            # EARLY SETTLE: over/BTTS live markets are IRREVERSIBLE once they land
            # (goals only ever go up). The moment the bet is mathematically won we move
            # it straight to Abgerechnet as WON — no waiting for the final whistle.
            if short in LIVE_STATUSES:
                hg, ag = _align_goals(f0, lt["home_team"])
                if _live_bet_landed(lt.get("market"), hg, ag, lt["home_team"], lt["away_team"]) is True:
                    minute = ((f0.get("fixture") or {}).get("status") or {}).get("elapsed") or 0
                    await db.tips.update_one({"id": lt["id"]}, {"$set": {
                        "status": "won", "final_home": hg, "final_away": ag,
                        "live_score": f"{hg}:{ag}", "live_minute": minute,
                        "settled_by": "auto-live-early", "settled_at": now}})
                    closed += 1
                    continue
            # still genuinely in-play and not overdue → keep it open
            if short in LIVE_STATUSES and not stale:
                continue
            # otherwise (postponed/cancelled/abandoned, or an in-play game that never
            # closes) fall through to the force-settle sweep below
        elif not stale:
            # no fixture data yet and not overdue → give it more time
            continue
        # 2) force-settle sweep: the pick is overdue or its fixture is in a terminal
        #    non-finished state. Try a team-based finished lookup; if none, void it so
        #    it always leaves the Live area and lands in Abgerechnet — never lingers.
        dates = None
        if ko:
            dates = [ko.date().isoformat(),
                     (ko + timedelta(days=1)).date().isoformat(),
                     (ko - timedelta(days=1)).date().isoformat()]
        tid = await resolve_team_id(lt["home_team"]) if dates else None
        fx = find_finished_fixture(tid, lt["away_team"], dates) if (tid and dates) else None
        if fx:
            hg, ag = fx["home_goals"] or 0, fx["away_goals"] or 0
            res = _live_bet_landed(lt.get("market"), hg, ag, lt["home_team"], lt["away_team"])
            new_status = "won" if res else ("lost" if res is False else "void")
            await db.tips.update_one({"id": lt["id"]}, {"$set": {
                "status": new_status, "final_home": hg, "final_away": ag,
                "settled_by": "auto-live", "settled_at": now}})
        else:
            await db.tips.update_one({"id": lt["id"]}, {"$set": {
                "status": "void", "settled_by": "auto-live", "settled_at": now}})
        closed += 1

    if not live:
        return {"posted": 0, "closed": closed, "live": 0}

    # 2) re-offer pending pre-match AI goal-picks that are live & not yet landed
    tips = await db.tips.find({"source": "hq-auto", "status": "pending"}, {"_id": 0}).to_list(300)
    posted = 0
    for t in tips:
        if posted >= LIVE_MAX_TIPS:
            break
        fx = _find_live_fixture(live, t.get("home_team"), t.get("away_team"))
        if not fx:
            continue
        hg, ag = _align_goals(fx, t["home_team"])
        landed = _live_bet_landed(t.get("market"), hg, ag, t["home_team"], t["away_team"])
        if landed is not False:  # None (result market) or True (already hit) → skip
            continue
        minute = ((fx.get("fixture") or {}).get("status") or {}).get("elapsed") or 0
        fid = str((fx.get("fixture") or {}).get("id"))
        stats = _apifootball("/fixtures/statistics", {"fixture": fid})
        if not _live_pressure_ok(stats, minute):
            continue  # dead/flat game → be careful, skip
        sog, corners, _ = _live_stat_totals(stats)
        odd = _live_odd(t.get("market"), minute, hg + ag)
        live_id = f"hqlive-{fid}-{t['id']}"
        if (sog + corners) > 0:
            press_txt = f"{sog} Schüsse aufs Tor · {corners} Ecken — Druck vorhanden."
        else:
            press_txt = f"Noch {max(90 - minute, 0)} Min. Spielzeit."
        analysis = (
            f"LIVE nachgereicht ({minute}'): {t.get('market')} — Stand {hg}:{ag}. "
            f"Noch nicht gefallen. {press_txt} "
            f"Ursprünglich {t.get('ai_rating')}★ Vor-Spiel-Pick — jetzt live zu {odd}."
        )
        await db.tips.update_one({"id": live_id}, {
            "$set": {
                "market": t.get("market"), "odds": f"{odd:.2f}",
                "ai_rating": min(7.0, float(t.get("ai_rating") or 7.0)), "win_prob": 0.7,
                "ai_analysis": analysis, "status": "live", "match_time": t.get("match_time"),
                "league": t.get("league") or "Live-Spiel",
                "country": t.get("country", ""), "league_code": t.get("league_code", ""),
                "live_minute": minute, "live_score": f"{hg}:{ag}", "updated_at": now,
            },
            "$setOnInsert": {
                "id": live_id, "user_id": hq["id"], "username": "TipJarHQ",
                "raw_text": "", "image_path": None,
                "home_team": t["home_team"], "away_team": t["away_team"],
                "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
                "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
                "source": "hq-live", "fixture_id": fid, "created_at": now,
            },
        }, upsert=True)
        posted += 1
        logger.info(f"LIVE re-offer: {t['home_team']} vs {t['away_team']} — {t.get('market')} @ {odd} ({minute}')")

    # 3) NEW: generate FRESH live goal-picks for currently in-play games that show
    #    real scoring pressure (so the KI always populates the Live channel, not just
    #    re-offering our own pre-match picks). Quota-capped stat lookups.
    have_fids = {str(x.get("fixture_id")) for x in
                 await db.tips.find({"source": "hq-live", "status": "live"},
                                    {"_id": 0, "fixture_id": 1}).to_list(400)}
    stat_calls = 0
    for fx in live:
        if posted >= LIVE_MAX_TIPS or stat_calls >= LIVE_STAT_CALL_CAP:
            break
        fid = str((fx.get("fixture") or {}).get("id") or "")
        if not fid or fid in have_fids:
            continue
        minute = ((fx.get("fixture") or {}).get("status") or {}).get("elapsed") or 0
        if minute < 10 or minute > 80:
            continue  # too early = no signal, too late = little time to land
        teams = fx.get("teams") or {}
        home = ((teams.get("home") or {}).get("name")) or ""
        away = ((teams.get("away") or {}).get("name")) or ""
        if not home or not away:
            continue
        if _team_or_league_blocked(home, away, ""):
            continue
        goals = fx.get("goals") or {}
        total = (goals.get("home") or 0) + (goals.get("away") or 0)
        if total > 1:
            continue  # 0-0 or one goal → "Über 1.5/2.5" stays realistic & settleable
        line = "1.5" if total == 0 else "2.5"
        stats = _apifootball("/fixtures/statistics", {"fixture": fid})
        stat_calls += 1
        if not _live_pressure_ok(stats, minute):
            continue
        sog, corners, _ = _live_stat_totals(stats)
        market = f"Über {line} Tore"
        odd = _live_odd(market, minute, total)
        analysis = (
            f"LIVE-Pick ({minute}'): {market} — Stand {goals.get('home') or 0}:{goals.get('away') or 0}. "
            f"Druck vorhanden: {sog} Schüsse aufs Tor · {corners} Ecken. "
            f"Noch {max(90 - minute, 0)} Min. Spielzeit — live zu {odd}."
        )
        live_id = f"hqlive-fresh-{fid}"
        await db.tips.update_one({"id": live_id}, {
            "$set": {
                "market": market, "odds": f"{odd:.2f}", "ai_rating": 7.0,
                "ai_analysis": analysis, "status": "live",
                "win_prob": 0.7,
                "league": _fixture_league_label(fx),
                "country": _fixture_country(fx),
                "league_code": "",
                "live_minute": minute, "live_score": f"{goals.get('home') or 0}:{goals.get('away') or 0}",
                "updated_at": now,
            },
            "$setOnInsert": {
                "id": live_id, "user_id": hq["id"], "username": "TipJarHQ",
                "raw_text": "", "image_path": None,
                "home_team": home, "away_team": away,
                "match_time": ((fx.get("fixture") or {}).get("date") or ""),
                "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
                "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
                "source": "hq-live", "fixture_id": fid, "created_at": now,
            },
        }, upsert=True)
        posted += 1
        logger.info(f"LIVE fresh: {home} vs {away} — {market} @ {odd} ({minute}')")
    return {"posted": posted, "closed": closed, "live": len(live)}


async def live_loop():
    await asyncio.sleep(200)  # let the pre-match picks populate first
    while True:
        if not _is_leader():
            await asyncio.sleep(45)
            continue
        try:
            if API_FOOTBALL_KEY:
                logger.info(f"HQ loop D (Live): {await live_autopost()}")
        except Exception as e:
            logger.error(f"live_loop error: {e}")
        await asyncio.sleep(LIVE_POLL_SECONDS)


# The Live CHANNEL is decided at post time (create_tip: posted while the match is
# in-play). This loop does NOT move tips between channels — it only ANNOTATES any
# non-finished single-match tip with its current live minute + score (live_state), so
# the red LIVE badge can appear everywhere a tipped game is running. When a match ends
# the annotation is cleared.
MEMBER_LIVE_POLL_SECONDS = 90


async def live_annotate_sync() -> dict:
    if not API_FOOTBALL_KEY:
        return {"annotated": 0, "cleared": 0}
    live = await asyncio.to_thread(_apifootball, "/fixtures", {"live": "all"}) or []
    tips = await db.tips.find(
        {"status": {"$in": ["pending", "live"]}, "is_parlay": {"$ne": True},
         "home_team": {"$nin": ["", None]}, "away_team": {"$nin": ["", None]}},
        {"_id": 0, "id": 1, "home_team": 1, "away_team": 1, "live_state": 1}).to_list(1500)
    annotated = cleared = 0
    for t in tips:
        fx = _find_live_fixture(live, t["home_team"], t["away_team"])
        if fx:
            g = fx.get("goals") or {}
            st = {"minute": ((fx.get("fixture") or {}).get("status") or {}).get("elapsed"),
                  "score": f"{g.get('home') or 0}:{g.get('away') or 0}"}
            if t.get("live_state") != st:
                await db.tips.update_one({"id": t["id"]}, {"$set": {"live_state": st}})
            annotated += 1
        elif t.get("live_state"):
            await db.tips.update_one({"id": t["id"]}, {"$unset": {"live_state": ""}})
            cleared += 1
    return {"annotated": annotated, "cleared": cleared}


async def member_live_loop():
    while True:
        if not _is_leader():
            await asyncio.sleep(45)
            continue
        try:
            res = await live_annotate_sync()
            if res["annotated"] or res["cleared"]:
                logger.info(f"Live annotate: {res}")
        except Exception as e:
            logger.error(f"live_annotate_loop error: {e}")
        await asyncio.sleep(MEMBER_LIVE_POLL_SECONDS)






async def backfill_leg_odds_once():
    """One-time-ish: fill missing per-leg odds on existing member parlay tips by
    re-reading their stored slip image (idempotent — skips tips that already have odds)."""
    await asyncio.sleep(25)
    try:
        tips = await db.tips.find({
            "source": {"$nin": ["hq-auto", "smart"]},
            "is_parlay": True,
            "image_path": {"$nin": [None, ""]},
        }, {"_id": 0, "id": 1, "image_path": 1, "legs": 1}).limit(15).to_list(15)
        done = 0
        for t in tips:
            legs = t.get("legs") or []
            if not legs or any(l.get("sel_odds") for l in legs):
                continue
            try:
                raw, _ct = get_object(t["image_path"])
                parsed = await analyze_tip(base64.b64encode(raw).decode("utf-8"), "")
            except Exception as ex:
                logger.error(f"backfill parse failed {t['id']}: {ex}")
                continue
            new_legs = parsed.get("legs") or []
            by_key = {_match_key(*_split_match(l.get("match", ""))): l for l in new_legs}
            for i, l in enumerate(legs):
                src = by_key.get(_match_key(*_split_match(l.get("match", ""))))
                if not src and i < len(new_legs):
                    src = new_legs[i]
                if src and src.get("sel_odds"):
                    l["sel_odds"] = src["sel_odds"]
            await db.tips.update_one({"id": t["id"]}, {"$set": {"legs": legs}})
            done += 1
        if done:
            logger.info(f"Backfilled per-leg odds on {done} member tips")
    except Exception as e:
        logger.error(f"backfill_leg_odds_once failed: {e}")


@app.on_event("startup")
async def startup():
    # Email is optional now: unique only when present (partial index). Drop old strict index if needed.
    try:
        existing = await db.users.index_information()
        if "email_1" in existing and not existing["email_1"].get("partialFilterExpression"):
            await db.users.drop_index("email_1")
    except Exception as e:
        logger.error(f"email index migration: {e}")
    await db.users.create_index(
        "email", unique=True,
        partialFilterExpression={"email": {"$type": "string"}},
    )
    await db.users.create_index("username", unique=True)
    await db.tips.create_index("status")
    await db.tip_ratings.create_index([("tip_id", 1), ("user_id", 1)])
    await db.users.create_index("referral_code")
    await db.tips.create_index([("user_id", 1), ("created_at", -1)])
    await db.tips.create_index([("status", 1), ("created_at", -1)])
    await db.credit_transactions.create_index([("from_user", 1), ("created_at", -1)])
    await db.credit_transactions.create_index([("to_user", 1), ("created_at", -1)])
    await db.tips.create_index([("avg_rating", -1), ("ratings_count", -1)])
    await db.tips.create_index([("ai_rating", -1)])
    # Initialize storage BEFORE any seeding that uploads images
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    # Run purge/admin-seed/showcase-seed in the background so the readiness probe
    # is never blocked by DB/storage latency (prevents deploy timeouts).
    asyncio.create_task(_startup_seed())
    _BG_TASKS.append(asyncio.create_task(_leadership_loop()))
    _BG_TASKS.append(asyncio.create_task(settlement_loop()))
    _BG_TASKS.append(asyncio.create_task(forebet_loop()))
    _BG_TASKS.append(asyncio.create_task(predictz_loop()))
    _BG_TASKS.append(asyncio.create_task(smart_loop()))
    _BG_TASKS.append(asyncio.create_task(live_loop()))
    _BG_TASKS.append(asyncio.create_task(member_live_loop()))
    _BG_TASKS.append(asyncio.create_task(push_watch_loop()))
    _BG_TASKS.append(asyncio.create_task(backfill_leg_odds_once()))
    if API_FOOTBALL_KEY:
        logger.info("Auto-settlement engine enabled (API-Football)")
    else:
        logger.info("Auto-settlement idle — set API_FOOTBALL_KEY to enable")


async def _cleanup_smart_junk():
    """Owner rules (runs on startup, incl. production):
    1) Remove blank 'Eingegangene Ideen' — image-only or empty-text idea records that
       render as blank cards in the Smart-Lab feed (a failed/blank upload must never show).
    2) Remove stale Smart 'report' picks (informational WC-style analyses) once the match
       is long over: reports older than 3 days, dateless reports, and any 'void' smart pick.
       This clears finished cards like the old France–Marokko report."""
    try:
        blank = await db.smart_ideas.delete_many(
            {"$or": [{"text": {"$in": ["", None]}},
                     {"text": {"$regex": r"^\s*$"}},
                     {"status": {"$ne": "used"}}]}
        )
        cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        stale_reports = await db.tips.delete_many(
            {"source": "smart",
             "$or": [
                 {"report": True, "created_at": {"$lt": cutoff}},
                 {"status": "void"},
             ]}
        )
        # Owner (2026-07-15): a pending Smart Pick whose match kicked off long ago and
        # never auto-settled (e.g. no API fixture / friendly) must NOT linger until the
        # 36h purge. Drop any pending smart pick > 8h past kickoff.
        stuck = 0
        now = datetime.now(timezone.utc)
        async for t in db.tips.find({"source": "smart", "status": "pending"},
                                    {"id": 1, "match_time": 1}):
            ko = _parse_kickoff(t.get("match_time"))
            if ko and ko < now - timedelta(hours=8):
                await db.tips.delete_one({"id": t["id"]})
                stuck += 1
        if blank.deleted_count or stale_reports.deleted_count or stuck:
            logger.info(f"Smart cleanup: {blank.deleted_count} blank ideas, "
                        f"{stale_reports.deleted_count} stale/void reports, "
                        f"{stuck} stuck expired smart picks removed")
    except Exception as e:
        logger.error(f"Smart cleanup failed: {e}")


async def _migrate_stars_and_categories():
    """One-time, idempotent data migration so ALREADY-posted picks match the current
    owner rules (runs on startup, incl. production): stars from win_prob (≤10, no more
    8.5 cap), 9/10-star singles → Banker, and strip the old '% Trefferchance' text."""
    try:
        docs = await db.tips.find(
            {"source": "hq-auto", "status": "pending"},
            {"_id": 0, "id": 1, "win_prob": 1, "ai_rating": 1, "ai_analysis": 1,
             "is_parlay": 1, "category": 1, "market": 1, "combo_legs": 1, "legs": 1},
        ).to_list(3000)
        changed = 0
        for d in docs:
            upd = {}
            wp = d.get("win_prob")
            stars = None
            if wp is not None:
                stars = max(1, min(10, round(wp * 10)))
                if float(d.get("ai_rating") or 0) != float(stars):
                    upd["ai_rating"] = float(stars)
            ml = (d.get("market") or "").lower()
            is_handicap15 = ("-1.5" in ml or "-1,5" in ml) and "handicap" in ml
            if is_handicap15 and not d.get("is_parlay"):
                # Owner rule: every -1.5 handicap single is a RISK pick.
                if d.get("category") != "risk":
                    upd["category"] = "risk"
                    upd["pick_type"] = "risk"
            elif stars is not None and stars >= 9 and not d.get("is_parlay") \
                    and d.get("category") != "risk":
                # 9/10-star singles → banker (never touch risk handicaps or combos)
                if d.get("category") != "banker":
                    upd["category"] = "banker"
                    upd["pick_type"] = "banker"
            # strip percentages from existing analysis prose
            txt = d.get("ai_analysis") or ""
            if "%" in txt:
                star_txt = f"{stars if stars is not None else int(round(float(d.get('ai_rating') or 8)))}/10 Sterne"
                new = re.sub(r"ca\.\s*\d+\s*%\s*Trefferchance", star_txt, txt)
                new = re.sub(r"\s*\(Value\s*≥\s*1[.,]60\)", "", new).replace("  ", " ")
                if new != txt:
                    upd["ai_analysis"] = new
            # Old BTTS bet-builders show two per-team "Über 0.5 Tore" chips — merge them
            # into ONE "Beide Teams treffen" leg AND drop the redundant "Über 1.5 Tore"
            # leg (BTTS already guarantees ≥2 goals). Odds/market/combo_legs rebuilt to
            # match so settlement stays correct.
            if d.get("is_parlay"):
                clegs = d.get("combo_legs") or []
                team_legs = [l for l in clegs if (l.get("kind") == "team_o05")
                             or ("über 0.5 tore" in (l.get("market", "") or "").lower() and l.get("team"))]
                if len(team_legs) >= 2:
                    btts_odd = 1.0
                    for l in team_legs:
                        btts_odd *= float(l.get("odds") or 1.30)
                    # keep every other leg EXCEPT the redundant Über 1.5 / o15
                    others = [l for l in clegs if l not in team_legs
                              and l.get("kind") != "o15"
                              and "über 1.5 tore" not in (l.get("market", "") or "").lower()]
                    btts_leg = {"market": "Beide Teams treffen", "odds": round(btts_odd, 2),
                                "kind": "btts", "team": ""}
                    new_clegs = [btts_leg] + others
                    total = btts_odd
                    for l in others:
                        total *= float(l.get("odds") or 1.0)
                    upd["combo_legs"] = new_clegs
                    upd["odds"] = f"{total:.2f}"
                    if others:
                        upd["market"] = (f"Beide Teams treffen + {others[0].get('market','')} "
                                         f"({len(new_clegs)}er-Bet-Builder)")
                    else:
                        upd["market"] = "Beide Teams treffen"
                    disp = d.get("legs") or []
                    if disp:
                        disp[0]["selections"] = [l["market"] for l in new_clegs]
                        disp[0]["sel_odds"] = [f"{float(l['odds']):.2f}" for l in new_clegs]
                        upd["legs"] = disp
            if upd:
                await db.tips.update_one({"id": d["id"]}, {"$set": upd})
                changed += 1
        if changed:
            logger.info(f"Star/category migration updated {changed} picks")
    except Exception as e:
        logger.error(f"Star/category migration failed: {e}")


async def _startup_seed():
    try:
        await purge_demo_tips()
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@tipjar.com").lower()
        admin_pw = os.environ.get("ADMIN_PASSWORD", "admin123")
        existing = await db.users.find_one({"email": admin_email})
        if not existing:
            await db.users.insert_one({
                "id": str(uuid.uuid4()), "email": admin_email, "password_hash": hash_password(admin_pw),
                "username": "TipJarAdmin", "role": "admin", "timezone": "UTC", "language": "en",
                "credits": 0, "received_credits": 0, "streak": 0, "last_rated_date": None,
                "ratings_given": 0, "created_at": datetime.now(timezone.utc).isoformat(),
            })
        elif not verify_password(admin_pw, existing["password_hash"]):
            await db.users.update_one({"email": admin_email},
                                      {"$set": {"password_hash": hash_password(admin_pw), "role": "admin"}})
        # Promote the owner's personal account(s) to admin so they can reach /insights
        # without logging into the dedicated admin account. Idempotent; only touches
        # accounts that already exist.
        owner_emails = ["kontakt@tipjarglobal.com"]
        extra = os.environ.get("OWNER_ADMIN_EMAILS", "")
        owner_emails += [e.strip().lower() for e in extra.split(",") if e.strip()]
        for oe in owner_emails:
            await db.users.update_one({"email": oe.lower(), "role": {"$ne": "admin"}},
                                      {"$set": {"role": "admin"}})
        await seed_showcase()
        await _migrate_stars_and_categories()
        await _cleanup_smart_junk()
    except Exception as e:
        logger.error(f"Startup seed failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    for task in _BG_TASKS:
        task.cancel()
    if _BG_TASKS:
        await asyncio.gather(*_BG_TASKS, return_exceptions=True)
    client.close()
