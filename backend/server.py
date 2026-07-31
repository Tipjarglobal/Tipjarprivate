from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import re
import json
import math
import random
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
from statarea import scrape_statarea
from betting_logic import dedupe_implied_legs, scoreline_to_combo
import match_stats
from models import (
    RegisterInput, VerifyInput, OriginInput, LoginInput, ProfileUpdate, TipSaveInput,
    RateInput, GiftInput, CheckoutInput, SubscribeInput, StatusInput, SmartIdeaInput,
    IdeaRateInput, VisitInput, PushSubIn, PushPrefsIn, ClarifyInput,
)
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout, CheckoutSessionResponse, CheckoutStatusResponse, CheckoutSessionRequest,
)

# ------------------------------------------------------------------ config (extracted → core.py)
from pywebpush import webpush, WebPushException
from core import (
    mongo_url, client, db,
    JWT_SECRET, JWT_ALGORITHM, EMERGENT_LLM_KEY, STRIPE_API_KEY,
    AI_MODEL_PROVIDER, AI_MODEL, AI_TEXT_MODEL, API_FOOTBALL_KEY, API_FOOTBALL_BASE, SETTLE_INTERVAL_SECONDS,
    VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT,
    SETTLE_BATCH_CAP, SETTLE_MAX_ATTEMPTS, FINISHED_STATUSES,
    SUBSCRIBER_DISPLAY_BOOST, SUBSCRIBER_BOOST_UNTIL, MEMBER_DISPLAY_BOOST, MEMBER_BOOST_UNTIL,
    _member_boost, _sub_boost,
    LIVE_STATUSES, LIVE_MAX_OPEN_HOURS,
    APP_NAME, STORAGE_URL,
    CREDIT_PACKAGES, CREDIT_CURRENCY, GIFT_FEE, REFERRAL_REWARD, REDEEM_THRESHOLD, REDEEM_EUR_PER_1000,
    RESEND_API_KEY, SENDER_EMAIL,
    logger,
    _API_QUOTA, _api_quota_exhausted, _reset_api_quota_flag, _apifootball, _apifootball_async,
    _api_reserve_locked, _API_DAY,
)
from learning import refresh_learning, learn_verdict, learn_bucket, _LEARN

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
        "expert_trial": user.get("expert_trial", False),
        "ratings_given": user.get("ratings_given", 0),
        "email_verified": user.get("email_verified", False),
        "referral_code": user.get("referral_code"),
        "created_at": user.get("created_at"),
    }


WELCOME_INBOX_TITLE = "Willkommen bei TipJar! 🎉"
WELCOME_INBOX_BODY = ("Schön, dass du dabei bist! Poste deine Tipps, bewerte die Picks der Community "
                      "und sichere dir Credits. Viel Erfolg! ⚽")
EXPERT_INVITE_TITLE = "Werde TipJar-Experte 🎯"
EXPERT_INVITE_BODY = ("Wir suchen Experten! Als Experte werden deine Tipps hervorgehoben und für die "
                      "ganze Community sichtbar. Möchtest du Experte werden? (Es gilt eine Probezeit.)")


async def _seed_inbox_for_new_user(user: dict, with_invite: bool = True):
    """Drop a welcome message (and an optional Expert invitation) into a user's mailbox."""
    now = datetime.now(timezone.utc).isoformat()
    msgs = [{
        "id": str(uuid.uuid4()), "user_id": user["id"], "type": "welcome",
        "title": WELCOME_INBOX_TITLE, "body": WELCOME_INBOX_BODY,
        "cta": None, "read": False, "handled": False, "created_at": now,
    }]
    if with_invite:
        msgs.append({
            "id": str(uuid.uuid4()), "user_id": user["id"], "type": "expert_invite",
            "title": EXPERT_INVITE_TITLE, "body": EXPERT_INVITE_BODY,
            "cta": "expert_invite", "read": False, "handled": False, "created_at": now,
        })
    await db.inbox_messages.insert_many(msgs)
    await db.users.update_one({"id": user["id"]}, {"$set": {"inbox_seeded": True}})


async def _tag_expert(tips: list) -> list:
    """Flag tips authored by an Expert so the UI can render them with the orange theme."""
    uids = list({t.get("user_id") for t in tips if t.get("user_id")})
    if not uids:
        return tips
    experts = await db.users.find(
        {"id": {"$in": uids}, "role": "expert"}, {"_id": 0, "id": 1}).to_list(len(uids))
    eset = {e["id"] for e in experts}
    for t in tips:
        if t.get("user_id") in eset and not t.get("is_master"):
            t["is_expert"] = True
        _disguise_stakes(t)
    return tips


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


@api_router.post("/admin/apifootball/predictions/run")
async def admin_apifootball_predictions_run(admin: dict = Depends(require_admin)):
    """Manually trigger the API-Football predictions gap-filler (quota-bounded)."""
    return await apifootball_predictions_autopost()


@api_router.post("/admin/statarea/run")
async def admin_statarea_run(admin: dict = Depends(require_admin)):
    """Manually trigger the Statarea prediction scraper (no API quota)."""
    if not await ensure_chromium():
        return {"posted": 0, "reason": "chromium unavailable in this environment"}
    return await statarea_autopost()


@api_router.post("/admin/footballpredictions/run")
async def admin_footballpredictions_run(admin: dict = Depends(require_admin)):
    """Manually trigger the FootballPredictions.com scraper (static, no API/Chromium)."""
    return await footballpredictions_autopost()



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
    a = await smart_autopost()
    b = await favourite_smart_autopost()
    c = await mental_autopost()
    return {"player_props": a, "favourites": b, "mental": c}


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


@api_router.get("/scorers/today")
async def scorers_today():
    """"Wer trifft heute?" — Torjäger-Radar. Ranks the teams most likely to SCORE in
    today's (and tonight's) matches, derived purely from the stored Forebet/Predictz
    predictions (no extra API-Football quota). Owner idea: just tell me who scores."""
    now = datetime.now(timezone.utc)
    preds = await db.match_predictions.find(
        {"status": "pending"}, {"_id": 0}).to_list(1500)
    _SRC_PRIO = {"forebet": 0, "predictz": 1, "statarea": 2, "apifootball": 3}
    preds.sort(key=lambda x: _SRC_PRIO.get(x.get("source"), 2))
    out = []
    seen = set()
    for p in preds:
        if not _pred_whitelisted(p):
            continue
        ko = _parse_kickoff(p.get("kickoff"))
        # today window: from 3h ago (in-play) up to +20h (tonight's late games)
        if ko is not None and not (now - timedelta(hours=3) <= ko <= now + timedelta(hours=20)):
            continue
        home, away = p.get("home"), p.get("away")
        ph, pa = p.get("ph"), p.get("pa")
        if not home or not away or ph is None or pa is None:
            continue
        conf = p.get("conf")
        try:
            conf_val = int(float(str(conf)))
        except Exception:
            conf_val = None
        btts, over25 = bool(p.get("btts")), bool(p.get("over25"))
        league = p.get("league") or ""
        ko_iso = ko.isoformat() if ko else ""
        for team, pg, opp in ((home, ph, away), (away, pa, home)):
            key = f"{team}|{opp}"
            if key in seen:
                continue
            # confidence that THIS team scores >= 1 goal
            if pg >= 2:
                c = 88
            elif pg >= 1:
                c = 78
            else:
                c = 46
            if btts:
                c += 6
            if over25:
                c += 3
            if conf_val:
                c = int(0.6 * c + 0.4 * min(conf_val, 95))
            c = max(30, min(97, c))
            if c < 68:
                continue  # only confident "will score" calls
            seen.add(key)
            out.append({
                "team": team, "opponent": opp, "league": league,
                "kickoff": ko_iso, "confidence": c,
                "predicted": f"{ph}-{pa}", "btts": btts, "over25": over25,
                "reason": (
                    f"Vorhersage {ph}:{pa}"
                    + (" · beide treffen" if btts else "")
                    + (" · über 2,5 Tore" if over25 else "")
                ),
            })
    out.sort(key=lambda x: (-x["confidence"], x["kickoff"] or "z"))
    return {"count": len(out), "scorers": out[:60], "generated_at": now.isoformat()}


async def _team_last_scored(team_name, allow_api=True):
    """Goals the team scored in its most recent FINISHED match. Cached 12h by team NAME so we
    never touch the API (resolve_team_id/fixtures) unless allowed AND the cache is stale.
    Returns (scored:int|None, api_used:bool, api_ok:bool)."""
    if not team_name:
        return None, False, True
    now = datetime.now(timezone.utc)
    doc = await db.team_form_cache.find_one({"team": team_name}, {"_id": 0})
    if doc:
        try:
            fresh = (now - datetime.fromisoformat(doc["checked_at"])).total_seconds() < 12 * 3600
        except Exception:
            fresh = False
        if fresh:
            return doc.get("scored_last"), False, True
    if not allow_api:
        return (doc.get("scored_last") if doc else None), False, True
    tid = await resolve_team_id(team_name)
    if not tid:
        return (doc.get("scored_last") if doc else None), True, True
    fx = await _apifootball_async("/fixtures", {"team": tid, "last": 3}) or []
    if not fx:
        return (doc.get("scored_last") if doc else None), True, False
    scored = None
    for m in fx:
        st = ((m.get("fixture") or {}).get("status") or {}).get("short")
        if st not in ("FT", "AET", "PEN"):
            continue
        teams, goals = m.get("teams") or {}, m.get("goals") or {}
        if (teams.get("home") or {}).get("id") == tid:
            scored = goals.get("home")
        elif (teams.get("away") or {}).get("id") == tid:
            scored = goals.get("away")
        if scored is not None:
            break
    if scored is not None:
        await db.team_form_cache.update_one(
            {"team": team_name},
            {"$set": {"team_id": tid, "team": team_name, "scored_last": int(scored),
                      "checked_at": now.isoformat()}}, upsert=True)
    return scored, True, True


@api_router.get("/goal-thirst")
async def goal_thirst():
    """"Dursty for goals" — teams that did NOT score in their last match (90' scoreless) and
    play again within 7 days. Owner idea: a side like Pogon can't stay scoreless for 180' — so
    we back it to score in the next game. Drought = last finished match with 0 goals (API-Football,
    cached 12h). Opponent 'victim' quality comes from the stored predictions (quota-free)."""
    now = datetime.now(timezone.utc)
    preds = await db.match_predictions.find({"status": "pending"}, {"_id": 0}).to_list(2000)
    _SRC_PRIO = {"forebet": 0, "predictz": 1, "statarea": 2, "apifootball": 3}
    preds.sort(key=lambda x: _SRC_PRIO.get(x.get("source"), 2))
    cands, seen = [], set()
    gift_map = await _gift_stance_map()
    for p in preds:
        if not _pred_whitelisted(p):
            continue
        ko = _parse_kickoff(p.get("kickoff"))
        if ko is None or not (now - timedelta(hours=2) <= ko <= now + timedelta(days=7)):
            continue
        home, away = p.get("home"), p.get("away")
        ph, pa = p.get("ph"), p.get("pa")
        if not home or not away or ph is None or pa is None:
            continue
        league = p.get("league") or ""
        btts, over25 = bool(p.get("btts")), bool(p.get("over25"))
        fav = p.get("fav")
        try:
            fp = int(float(p.get("fav_prob") or 0))
        except (TypeError, ValueError):
            fp = 0
        try:
            conf_val = int(float(str(p.get("conf"))))
        except Exception:
            conf_val = None
        for team, pg, opp, opp_conc in ((home, ph, away, pa), (away, pa, home, ph)):
            if team in seen:
                continue
            if not (pg >= 1 or btts):
                continue  # only teams our model expects to score → credible "will score"
            # owner learning 2026-07-30: don't back a CLEAR underdog to score (e.g. Hajduk
            # 0:2 down away). Skip the weak side of a strong favourite unless our model still
            # expects it to score 2+ on its own.
            is_underdog = fp >= 62 and ((fav == "home" and team == away) or (fav == "away" and team == home))
            if is_underdog and pg < 2:
                continue
            # owner 2026-07-30: a GIFT is the source of truth — never show "{team} trifft" if a
            # gift called that team/match low-scoring.
            if _conflicts_with_gift(f"{team} trifft", home, away,
                                    gift_map.get(_match_key(home, away))):
                continue
            seen.add(team)
            c = 84 if pg >= 2 else (76 if pg >= 1 else 58)
            if btts:
                c += 6
            if over25:
                c += 3
            if conf_val:
                c = int(0.6 * c + 0.4 * min(conf_val, 95))
            c = max(40, min(96, c))
            cands.append({"team": team, "opponent": opp, "kickoff": ko.isoformat(),
                          "league": league, "predicted": f"{ph}-{pa}",
                          "opp_concede": opp_conc, "btts": btts, "over25": over25,
                          "confidence": c})
    cands.sort(key=lambda x: (x["kickoff"] or "z", -x["confidence"]))
    cands = cands[:200]
    out, budget, allow_api = [], 12, True
    for cand in cands:
        if len(out) >= 40:
            break
        scored, used, ok = await _team_last_scored(cand["team"], allow_api and budget > 0)
        if used:
            budget -= 1
        if not ok:
            allow_api = False
        if scored is None or scored != 0:
            continue  # unknown or scored last match → no 90' drought
        opp_lvl = "high" if cand["opp_concede"] >= 2 else ("mid" if cand["opp_concede"] >= 1 else "low")
        out.append({**cand, "last_scored": scored, "opp_level": opp_lvl})
    out.sort(key=lambda x: (-x["confidence"], x["kickoff"] or "z"))
    return {"count": len(out), "teams": out[:40], "generated_at": now.isoformat()}



@api_router.get("/ht-goal-forecast")
async def ht_goal_forecast():
    """Spiele mit SEHR wahrscheinlichem Tor in der 1. Halbzeit ("Über 0.5 Tore 1. Halbzeit").
    Quota-frei aus den gespeicherten Forebet/Predictz-Vorhersagen (ph/pa/BTTS/Over2.5).
    Owner-Idee: torreiche Spiele treffen fast immer schon vor der Pause."""
    now = datetime.now(timezone.utc)
    preds = await db.match_predictions.find({"status": "pending"}, {"_id": 0}).to_list(2000)
    _SRC_PRIO = {"forebet": 0, "predictz": 1, "statarea": 2, "apifootball": 3}
    preds.sort(key=lambda x: _SRC_PRIO.get(x.get("source"), 2))
    out, seen = [], set()
    for p in preds:
        if not _pred_whitelisted(p):
            continue
        ko = _parse_kickoff(p.get("kickoff"))
        if ko is None or not (now - timedelta(hours=2) <= ko <= now + timedelta(days=7)):
            continue
        home, away = p.get("home"), p.get("away")
        ph, pa = p.get("ph"), p.get("pa")
        if not home or not away or ph is None or pa is None:
            continue
        key = _match_key(home, away)
        if key in seen:
            continue
        total = float(ph) + float(pa)
        btts, over25 = bool(p.get("btts")), bool(p.get("over25"))
        # Only genuinely goal-heavy games qualify as a "sure" first-half goal.
        if not (total >= 3 or (over25 and total >= 2.5)):
            continue
        seen.add(key)
        c = 90 if total >= 4 else (84 if total >= 3 else 76)
        if btts:
            c += 3
        if over25:
            c += 2
        try:
            conf_val = int(float(str(p.get("conf"))))
            c = int(0.65 * c + 0.35 * min(conf_val, 95))
        except Exception:
            pass
        c = max(60, min(95, c))
        out.append({"home": home, "away": away, "league": p.get("league") or "",
                    "kickoff": ko.isoformat(), "predicted": f"{ph}-{pa}",
                    "total": round(total, 1), "btts": btts, "over25": over25,
                    "confidence": c, "market": "Über 0.5 Tore 1. Halbzeit"})
    out.sort(key=lambda x: (-x["confidence"], x["kickoff"] or "z"))
    return {"count": len(out), "matches": out[:40], "generated_at": now.isoformat()}


@api_router.get("/goals-forecast")
async def goals_forecast():
    """Tor-Prognose-Tabelle — zeigt pro Spiel, wie viele Tore JEDES Team laut
    Vorhersage schießt (⚽ = 1 vorhergesagtes Tor). Kommt ausschließlich aus den
    gespeicherten Forebet/Predictz-Vorhersagescores (ph/pa) — NICHT aus der Quote.
    Owner-Regel: keine Bälle nur weil ein Favorit @1.20 steht; die Prognose muss passen.
    0:0-anfällige Spiele (beide 0) werden ehrlich als 'kein Tor erwartet' gezeigt."""
    now = datetime.now(timezone.utc)
    preds = await db.match_predictions.find(
        {"status": "pending"}, {"_id": 0}).to_list(1500)
    _SRC_PRIO = {"forebet": 0, "predictz": 1, "statarea": 2, "apifootball": 3}
    preds.sort(key=lambda x: _SRC_PRIO.get(x.get("source"), 2))
    out, seen = [], set()
    for p in preds:
        if not _pred_whitelisted(p):
            continue
        ko = _parse_kickoff(p.get("kickoff"))
        if ko is not None and not (now - timedelta(hours=3) <= ko <= now + timedelta(hours=30)):
            continue
        home, away = p.get("home"), p.get("away")
        ph, pa = p.get("ph"), p.get("pa")
        if not home or not away or ph is None or pa is None:
            continue
        key = _match_key(home, away)
        if key in seen:
            continue
        seen.add(key)
        try:
            ph, pa = int(round(float(ph))), int(round(float(pa)))
        except Exception:
            continue
        ph, pa = max(0, min(ph, 6)), max(0, min(pa, 6))
        total = ph + pa
        try:
            conf_val = int(float(str(p.get("conf"))))
        except Exception:
            conf_val = None
        btts, over25 = bool(p.get("btts")), bool(p.get("over25"))
        zz = _zero_zero_assessment(p)
        if total == 0:
            note = "Torlos erwartet — 0:0 möglich, Vorsicht mit Über-Wetten"
        elif ph == 0 or pa == 0:
            scorer = home if ph > 0 else away
            note = f"Nur {scorer} trifft laut Prognose"
        elif btts:
            note = "Beide Teams treffen"
        else:
            note = "Torreiches Spiel erwartet" if total >= 3 else "Wenige Tore erwartet"
        out.append({
            "home": home, "away": away,
            "home_goals": ph, "away_goals": pa, "total": total,
            "league": p.get("league") or "", "kickoff": ko.isoformat() if ko else "",
            "btts": btts, "over25": over25,
            "confidence": max(30, min(97, conf_val)) if conf_val else None,
            "zero_zero": zz["level"], "zero_zero_label": zz["label"],
            "over_safe": zz["over_safe"],
            "note": note,
        })
    # 0:0-unwahrscheinliche (Über-sichere) Spiele nach oben, dann Torschnitt
    out.sort(key=lambda x: (not x["over_safe"], -x["total"], x["kickoff"] or "z"))
    return {"count": len(out), "matches": out[:80], "generated_at": now.isoformat()}


@api_router.get("/smart/qualifier-briefing")
async def qualifier_briefing():
    """Weekly European-qualifier briefing for the Smart Picks intro. Returns the cached
    briefing; if it is missing or older than BRIEFING_TTL_H, a rebuild is kicked off in
    the background (the current cache is returned immediately, no request blocking)."""
    doc = await db.briefing_cache.find_one({"id": "qualifier"}, {"_id": 0})
    now = datetime.now(timezone.utc)
    stale = True
    if doc:
        try:
            gen = datetime.fromisoformat(doc.get("generated_at"))
            stale = (now - gen) > timedelta(hours=BRIEFING_TTL_H)
        except Exception:
            stale = True
    if stale:
        _BG_TASKS.append(asyncio.create_task(build_qualifier_briefing()))
    if not doc:
        return {"count": 0, "matches": [], "narrative": "", "generated_at": "", "building": True}
    return {**doc, "building": stale}


@api_router.get("/master/avatar")
async def master_avatar():
    """TipJarMaster Avatar calls for today — confident minute-goal predictions (speech bubbles).
    Powers the crown avatar + speech bubble at the top of the Master channel."""
    day = _berlin_now().date().isoformat()
    docs = await db.tips.find(
        {"source": "hq-master", "master_category": "avatar",
         "$or": [{"master_day": day}, {"status": {"$in": ["pending", "live"]}}]},
        {"_id": 0, "id": 1, "home_team": 1, "away_team": 1, "league": 1, "market": 1,
         "odds": 1, "match_time": 1, "avatar_minute": 1, "avatar_text": 1,
         "avatar_confidence": 1, "drought": 1, "status": 1,
         "avatar_player": 1, "avatar_scorer": 1}
    ).sort("created_at", -1).to_list(20)
    return {"count": len(docs), "calls": docs, "generated_at": day}





@api_router.get("/tips/counts")
async def tips_counts():
    """Post counts per picks area — powers the homepage badges & area alerts.
    The AI badge reflects the next-24h picks (the default view) so it stays realistic."""
    await purge_expired_autotips()
    await expire_stale_pending()
    await purge_settled_tips()
    now = datetime.now(timezone.utc)
    # AI badge = every pending Single-Game pick (singles + bet-builder combos, all
    # days) so it matches the bundled red "new" count and the Banker/Value/Risk tabs.
    ai_docs = await db.tips.find(
        {"source": "hq-auto", "status": "pending"}, {"match_time": 1}).to_list(1000)
    ai = len(ai_docs)
    ai_total = ai
    members = await db.tips.count_documents({
        "source": {"$nin": ["hq-auto", "smart", "hq-live", "hq-system", "hq-master", *SILENT_SOURCE_SLUGS]},
        "username": {"$nin": ["TipJarHQ", "TipJarHQ System"]},
        "hidden": {"$ne": True},
        "status": "pending"})
    _KILIVE_SOURCES = ["hq-auto", "hq-live", "hq-system", "smart"]
    live = await db.tips.count_documents({"status": "live", "hidden": {"$ne": True},
                                          "source": {"$in": _KILIVE_SOURCES}})
    community_live = await db.tips.count_documents({
        "status": "live", "hidden": {"$ne": True},
        "source": {"$nin": ["hq-auto", "smart", "hq-live", "hq-system", "hq-master", *SILENT_SOURCE_SLUGS]},
        "username": {"$nin": ["TipJarHQ", "TipJarHQ System"]}})
    master = await db.tips.count_documents({"source": "hq-master", "hidden": {"$ne": True},
                                            "status": {"$in": ["pending", "live"]}})
    smart = await db.tips.count_documents({"source": "smart", "status": "pending"})
    settled = await db.tips.count_documents({"status": {"$in": ["won", "lost", "cashed_out"]}, "hidden": {"$ne": True}})
    won_n = await db.tips.count_documents({"status": "won", "hidden": {"$ne": True}})
    lost_n = await db.tips.count_documents({"status": "lost", "hidden": {"$ne": True}})
    cashed_n = await db.tips.count_documents({"status": "cashed_out", "hidden": {"$ne": True}})
    void_n = await db.tips.count_documents({"status": "void", "id": {"$not": {"$regex": "^seed-"}}})
    bestwon_n = await db.tips.count_documents({
        "status": "won",
        "id": {"$not": {"$regex": "^seed-"}},
        "hidden": {"$ne": True},
        "$or": [
            {"source": "smart"},
            {"source": "hq-system"},
            {"source": "hq-auto", "category": "risk"},
            {"source": {"$nin": ["hq-auto", "smart", "hq-live", "hq-system", "hq-master"]}},
        ],
    })
    won_normal_n = await db.tips.count_documents({
        "status": "won",
        "id": {"$not": {"$regex": "^seed-"}},
        "hidden": {"$ne": True},
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
    # Codemining: how many codes are currently mined pre-game (active, not yet settled).
    _now_iso = datetime.now(timezone.utc).isoformat()
    codereading = await db.code_reads.count_documents(
        {"expires_at": {"$gt": _now_iso}, "outcome": {"$exists": False}})
    return {"ai": ai, "ai_total": ai_total, "members": members, "live": live,
            "community_live": community_live, "codereading": codereading,
            "systems": systems_n, "smart": smart, "settled": settled, "master": master,
            "won": won_n, "lost": lost_n, "cashed": cashed_n, "bestwon": bestwon_n,
            "won_normal": won_normal_n, "void": void_n}




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
    "bet_type (\"system\" ONLY if the slip is explicitly a SYSTEM/combination bet — look for labels like "
    "'System', 'Systemwette', 'System 2/3', '3 aus 4', '12 aus 14', '12/14', 'X von Y', 'Kombi X/Y'; "
    "otherwise \"\"). "
    "system_from (integer X = minimum winning legs, e.g. 12 in '12 aus 14'; 0 if not a system) and "
    "system_total (integer Y = total legs, e.g. 14 in '12 aus 14'; 0 if not a system). "
    "legs (array with ONE object per MATCH, each: {\"match\": \"Home - Away\", "
    "\"league\": \"competition/league name, e.g. 'Allsvenskan', 'La Liga', 'UEFA Nations League'\", "
    "\"kickoff\": \"HH:MM or ''\", \"selections\": [\"exact market lines, e.g. 'Total Over 1.5', "
    "'Djurgaren Total Over 0.5', 'Fouls Over 21.5'\"], "
    "\"sel_odds\": [\"the decimal odd for EACH selection in the SAME order, e.g. '1.24'; use '' if a "
    "selection's odd is not shown\"], "
    "\"combo_odds\": \"if this ONE match is a bet-builder (2+ selections combined into a SINGLE odd on "
    "the slip), put that single combined decimal odd here as a string (e.g. '1.40'); else ''\"}), "
    "home_team, away_team, match_time, country, league, "
    "market (a short human summary of all selections), odds (total/combined odds as a string), "
    "stake (string, '' if unknown), "
    "potential_return (string): ALWAYS compute it as stake MULTIPLIED BY odds (stake x odds) and "
    "IGNORE any tax, fees or deductions shown on the slip; use '' only if stake or odds is unknown. "
    "match_time MUST contain the match DATE and kickoff TIME whenever they appear on the slip (e.g. '19/07/2026 21:00'). "
    "rating (1-10) = how SAFE / likely-to-win the whole slip is — NOT its payout value. "
    "IMPORTANT: rate SAFETY, never penalise a slip for having low total odds. A slip built purely "
    "from near-certain selections (very short odds such as Over 0.5, low Unders like Under 4.5/5.5, "
    "clear favourites, Double Chance, Draw No Bet on a big favourite) MUST score HIGH (9-10) even "
    "when the combined odds are tiny (e.g. 1.4). If EVERY selection is a near-lock (each individual "
    "odd is roughly 1.40 or lower), give the FULL 10. Give a MID rating (5-7) to slips mixing safe legs "
    "with one or two moderately risky picks. Give a LOW rating (1-4) ONLY to genuinely risky or "
    "illogical slips: long-shot/underdog backs, exact scores, correlated or logically redundant "
    "risky legs, or high-variance markets. "
    "analysis (one short punchy sentence, max 160 chars): describe the safety of the slip; do NOT "
    "call low odds 'poor value' or 'little value' — a near-certain slip is a strong, safe play. "
    "In the analysis, if the slip contains a LOGICALLY REDUNDANT selection — one already implied by "
    "the others (e.g. 'Over 3.5' or a team's 'Over 2.5' when the slip already has '<Fav> -1.5 "
    "Handicap' + 'Both Teams To Score', since a 2+ goal win with BTTS forces 3+ total goals) — briefly "
    "point it out (which pick adds no value). Understand handicaps: -1.5 = win by 2+, -2.5 = win by 3+, "
    "+1.5 = must not lose by 2+. "
    "ALSO act as a content-moderator on BOTH the image and the written text and add two keys: "
    "safe (boolean) and flag_reason (short string). Set safe=false if the image or text contains ANY "
    "of: nudity or sexual/pornographic content, graphic violence or gore, hate speech, insults, "
    "harassment or profanity directed at people, or content that is clearly NOT a football bet slip/tip "
    "(spam, random selfies, unrelated pictures). Otherwise safe=true and flag_reason=''. "
    "TEAM & PLAYER NAMES: always output the OFFICIAL, internationally-known LATIN (English) name of the "
    "club/player — NEVER a phonetic transliteration of a foreign script. Translate names written in Greek, "
    "Cyrillic or Arabic to their real Latin name (e.g. 'Κρουζ Αζουλ'→'Cruz Azul', 'Μπάχια'→'Bahia', "
    "'Ερυθρός Αστέρας'/'Τσρβένα Ζβέζντα'→'Crvena Zvezda', 'Ολυμπιακός'→'Olympiacos'). Keep the HOME team "
    "on the LEFT and the AWAY team on the RIGHT exactly as printed on the slip — do not swap them. "
    "MARKET / SELECTION: normalize EVERY selection to STANDARD ENGLISH betting terminology — do NOT leave it "
    "in Greek/Cyrillic/Arabic and do NOT transliterate phonetically. Map e.g. 'Τελικό αποτέλεσμα'→'Final "
    "Result', 'Να σκοράρουν και οι δύο ομάδες'→'Both Teams to Score', 'Πάνω από X'→'Over X', 'Κάτω από "
    "X'→'Under X', 'Διπλή ευκαιρία'→'Double Chance', 'Ημίχρονο'→'1st Half'. Keep any line/number exactly. "
    "DATE & TIME: copy the kickoff DATE and TIME exactly as printed on the slip (format 'DD/MM/YYYY HH:MM'); "
    "never guess, invent or shift the time. If a field is unknown use an empty string. Never invent scores. "
    "For an INDIVIDUAL / TEAM total (labels like 'Individual Total Team 1/2', 'Individuel Asian over 1', "
    "'Ομαδικό Asian over 1', 'Team Total'): PREFIX the selection with the EXACT team name it refers to — "
    "Team/Total 1 = the HOME team, Team/Total 2 = the AWAY team — e.g. 'FC Kopenhagen Asian Over 1.0'. "
    "ALWAYS keep the word 'Asian' in the selection whenever the line is an Asian total/handicap."
)


_PLACEHOLDER_TEAMS = {
    "", "unknown", "unknown team", "unknown teams", "unbekannt", "n/a", "na", "n.a.",
    "tbd", "tba", "?", "-", "—", "–", "none", "null", "keine angabe", "not visible",
    "nicht sichtbar", "team a", "team b", "home", "away", "heim", "auswärts",
}


def _clean_placeholder(s) -> str:
    """Turn AI placeholder values ('Unknown', 'N/A', 'TBD', 'Team A' …) into '' so a
    slip whose teams weren't readable never shows 'Unknown' — it triggers the (minimal)
    clarify flow instead so the poster fills the real teams in."""
    v = str(s or "").strip()
    return "" if v.lower() in _PLACEHOLDER_TEAMS else v


def _tip_has_known_teams(tip: dict) -> bool:
    """True if we know the actual teams (tip-level or in any leg). A member slip whose
    teams the AI couldn't read ('Unknown') must NEVER go public (owner 2026-07-23)."""
    if _clean_placeholder(tip.get("home_team")) or _clean_placeholder(tip.get("away_team")):
        return True
    for lg in (tip.get("legs") or []):
        m = str(lg.get("match", "") or "")
        parts = re.split(r"\s(?:vs\.?|[–—-])\s", m, maxsplit=1)
        if any(_clean_placeholder(p) for p in parts):
            return True
    return False


def _safe_int(v) -> int:
    try:
        return int(float(str(v).strip()))
    except (ValueError, TypeError):
        return 0



def _sanitize_legs(legs) -> list:
    out = []
    if isinstance(legs, list):
        for lg in legs:
            if isinstance(lg, dict):
                sels = lg.get("selections") or []
                sodds = lg.get("sel_odds") or []
                match = str(lg.get("match", "") or "")
                # strip a match that's just a placeholder ("Unknown", "Team A vs Team B" …)
                parts = re.split(r"\s(?:vs\.?|[–—-])\s", match, maxsplit=1)
                if parts and all(not _clean_placeholder(p) for p in parts):
                    match = ""
                out.append({
                    "match": match,
                    "league": str(lg.get("league", "") or ""),
                    "kickoff": str(lg.get("kickoff", "") or ""),
                    "selections": [str(s) for s in sels if s][:10],
                    "sel_odds": [str(o or "") for o in sodds][:10],
                    "combo_odds": str(lg.get("combo_odds", "") or ""),
                    "banker": bool(lg.get("banker", False)),
                })
    return out[:12]


async def analyze_tip(images_b64: Optional[List[str]], text: str) -> dict:
    fallback = {
        "home_team": "", "away_team": "", "match_time": "", "country": "",
        "league": "", "market": text.strip()[:60], "odds": "",
        "rating": 5.0, "analysis": "Auto-rating unavailable, rated neutral.",
        "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
        "bet_type": "", "system_from": 0, "system_total": 0,
        "safe": True, "flag_reason": "", "ai_error": False,
    }
    if not EMERGENT_LLM_KEY:
        return {**fallback, "ai_error": True}
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
            "For a multi-leg slip, each leg is an object; if the user marks a game as 'Banker', "
            "'Bank', 'sicher' or 'lock' (the safest anchor picks), set that leg's \"banker\": true, "
            "otherwise \"banker\": false. "
            "IMPORTANT: for ANY field you cannot clearly read, return an EMPTY string \"\" — "
            "NEVER write 'Unknown', 'N/A', 'TBD', 'Team A', '?' or any placeholder. "
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
            return {**fallback, "ai_error": True}
        rating = float(data.get("rating", 5) or 5)
        rating = max(1.0, min(10.0, rating))
        return {
            "home_team": _clean_placeholder(data.get("home_team")),
            "away_team": _clean_placeholder(data.get("away_team")),
            "match_time": str(data.get("match_time", "") or ""),
            "country": str(data.get("country", "") or ""),
            "league": str(data.get("league", "") or ""),
            "market": str(data.get("market", "") or "") or text.strip()[:60],
            "odds": str(data.get("odds", "") or ""),
            "stake": str(data.get("stake", "") or ""),
            "potential_return": compute_return(data.get("stake"), data.get("odds"), str(data.get("potential_return", "") or "")),
            "legs": _sanitize_legs(data.get("legs")),
            "is_parlay": bool(data.get("is_parlay", False)),
            "bet_type": ("system" if str(data.get("bet_type", "")).lower() == "system" else ""),
            "system_from": _safe_int(data.get("system_from")),
            "system_total": _safe_int(data.get("system_total")),
            "rating": round(rating, 1),
            "analysis": str(data.get("analysis", "") or "")[:200],
            "safe": bool(data.get("safe", True)),
            "flag_reason": str(data.get("flag_reason", "") or "")[:160],
            "ai_error": False,
        }
    except Exception as e:
        logger.error(f"AI analyze failed: {e}")
        return {**fallback, "ai_error": True}


_ANALYST_SYSTEM = (
    "Du bist der scharfsinnige Chef-Analyst von TipJar — im Stil eines Top-Tippgebers auf X: "
    "selbstbewusst, konkret, meinungsstark. Schreibe eine KURZE (2–4 Sätze), einzigartige "
    "deutsche Analyse zu GENAU diesem Spiel. Baue die Begründung logisch auf: Favoritenstärke bzw. "
    "Offensivkraft, defensive Anfälligkeit, Torerwartung, ggf. Aggregat/Belastung bei Rückspielen — "
    "und schließe mit einem klaren, zugespitzten Fazit, WARUM die Wette fällt. "
    "STRIKTE REGELN: (1) Erfinde NIEMALS Statistiken, Quoten oder Trefferquoten (kein 'X von Y'), "
    "wenn sie nicht in den Daten stehen — nutze NUR die dir gegebenen Fakten. "
    "(2) Nenne NIE ein exaktes Endergebnis als Tipp — denke in Marktkombinationen "
    "(Handicap + BTTS + Über/Unter). (3) Verstehe Handicaps korrekt: '-1.5' = Sieg mit 2+ Toren, "
    "'-2.5' = Sieg mit 3+ Toren, '+1.5' = darf höchstens knapp verlieren. Erkläre bei Handicap-Wetten "
    "kurz, welches Ergebnis dafür nötig ist. (4) KEINE Standardfloskeln, kein Wiederholen von "
    "Quote/Sternen, kein 'automatisch von TipJarHQ'. Variiere Stil und Einstieg. Höchstens 1 Emoji. "
    "Antworte NUR mit dem Analysetext, ohne Anführungszeichen."
)


async def llm_pick_analysis(context: str, stats_line: str = "") -> str:
    """Generate a unique, opinionated German analysis for a pick. Returns "" on failure so
    the caller keeps its template fallback. `stats_line` (if given) are REAL numbers the
    model may cite — it must not invent others."""
    if not EMERGENT_LLM_KEY:
        return ""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"anal-{uuid.uuid4()}",
            system_message=_ANALYST_SYSTEM,
        ).with_model(AI_MODEL_PROVIDER, AI_TEXT_MODEL)
        extra = (f"\n\nECHTE Statistiken (zitiere passende Zahlen hieraus, erfinde KEINE weiteren):\n{stats_line}"
                 if stats_line else "")
        resp = await chat.send_message(UserMessage(text=f"Spiel-Daten:\n{context}{extra}\n\nSchreibe die Analyse."))
        out = (resp if isinstance(resp, str) else str(resp)).strip()
        if out.startswith(('"', "„", "»")):
            out = out.strip('"„»«”')
        return out[:600]
    except Exception as e:
        logger.error(f"llm_pick_analysis failed: {e}")
        return ""



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
        ).with_model(AI_MODEL_PROVIDER, AI_TEXT_MODEL)
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
    await _seed_inbox_for_new_user(user)
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


# --- AI-pick correction (owner 2026-07-29) ------------------------------------------
# ANY logged-in user can correct a KI pick by uploading an image of the REAL, existing
# selection + odds (e.g. the model wrote "Kopenhagen +1.5" which doesn't exist → send an
# image with "1X"). Vision reads ONLY the selection + odds; the STAKE is never touched.
_CORRECTABLE_SOURCES = ("hq-auto", "hq-live", "hq-system", "smart", "hq-master")


def _odds_product(vals) -> float:
    p = 1.0
    for v in vals:
        try:
            p *= float(str(v).replace(",", "."))
        except (ValueError, TypeError):
            pass
    return round(p, 2)


@api_router.post("/tips/{tip_id}/correct")
async def correct_tip(tip_id: str,
                      file: Optional[UploadFile] = File(default=None),
                      files: List[UploadFile] = File(default=[]),
                      text: str = Form(default=""),
                      user: dict = Depends(get_current_user)):
    tip = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    if tip.get("source") not in _CORRECTABLE_SOURCES:
        raise HTTPException(status_code=422, detail="Only AI tips can be corrected.")
    if tip.get("status") not in ("pending", "live"):
        raise HTTPException(status_code=422, detail="Only open tips can be corrected.")
    uploads = [f for f in ([file] + list(files or []))
               if f is not None and getattr(f, "filename", None)][:4]
    if not uploads:
        raise HTTPException(status_code=422, detail="Please attach an image of the correct selection/odds.")
    images_b64 = [base64.b64encode(await f.read()).decode("utf-8") for f in uploads]
    detected = await analyze_tip(images_b64, text)
    if not detected.get("safe", True):
        raise HTTPException(status_code=422, detail=detected.get("flag_reason") or "Image rejected.")
    ext_legs = detected.get("legs") or []
    upd, changed = {}, []
    if tip.get("is_parlay") and tip.get("legs"):
        legs = [dict(l) for l in tip["legs"]]
        used = set()
        for el in ext_legs:
            esel = [str(s) for s in (el.get("selections") or []) if s][:10]
            if not esel:
                continue
            eodds = [str(o) for o in (el.get("sel_odds") or []) if o][:10]
            em = _norm(el.get("match", ""))
            etok = set(em.split())
            target, ti = None, None
            for idx, lg in enumerate(legs):
                if idx in used:
                    continue
                lm = _norm(lg.get("match", ""))
                if lm and em and (lm in em or em in lm or len(set(lm.split()) & etok) >= 1):
                    target, ti = lg, idx
                    break
            if target is None and len(legs) == 1 and 0 not in used:
                target, ti = legs[0], 0
            if target is not None:
                target["selections"] = esel
                if eodds:
                    target["sel_odds"] = eodds
                used.add(ti)
                changed.append(f"{target.get('match', '')}: {', '.join(esel)}")
        if not changed:
            raise HTTPException(status_code=422, detail="Could not match any leg from the image to this slip.")
        all_odds = [o for lg in legs for o in (lg.get("sel_odds") or [])]
        total = _odds_product(all_odds)
        upd["legs"] = legs
        if total > 1.0:
            upd["odds"] = str(total)
    else:
        new_market = detected.get("market") or (
            ext_legs[0]["selections"][0] if ext_legs and ext_legs[0].get("selections") else "")
        new_odds = detected.get("odds") or (
            ext_legs[0]["sel_odds"][0] if ext_legs and ext_legs[0].get("sel_odds") else "")
        if not new_market:
            raise HTTPException(status_code=422, detail="Could not read a valid selection from the image.")
        upd["market"] = new_market
        changed.append(new_market)
        if new_odds:
            upd["odds"] = str(new_odds)
    # STAKE stays untouched — only recompute the potential return with the NEW odds.
    if upd.get("odds"):
        upd["potential_return"] = compute_return(tip.get("stake") or "", upd["odds"], "")
    upd["corrected"] = True
    upd["corrected_by"] = user.get("username") or user.get("id")
    upd["corrected_at"] = datetime.now(timezone.utc).isoformat()
    upd["settle_attempts"] = 0  # re-grade the corrected pick cleanly
    sel_txt = " · ".join(changed)
    _new_odds = upd.get("odds")
    upd["ai_analysis"] = (f"Manuell korrigiert auf: {sel_txt}"
                          + (f" (Gesamtquote {_new_odds})" if _new_odds else "")
                          + ". Einsatz unverändert.")
    await db.tips.update_one({"id": tip_id}, {"$set": upd})
    doc = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    return {"ok": True, "corrected": changed, "tip": doc}



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


def _fmt_usd(v: float) -> str:
    """US-style money with a $ suffix; drop a trailing .00 so whole stakes look natural."""
    s = f"{v:,.2f}"
    if s.endswith(".00"):
        s = s[:-3]
    return f"{s} $"


def _parse_units(s):
    """A stake expressed in betting UNITS (e.g. '1u', '2 units', '1.5 u') → float units."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:u\b|units?\b)", str(s or ""), re.I)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", "."))
    except ValueError:
        return None


def _asian_over1_in_text(txt: str) -> bool:
    """True when a selection line is an Asian 'Über/Over 1.0' total (team or match) — a
    near-lock 'gift' (push at exactly 1 goal). Never matches Über 1.5."""
    m = (txt or "").lower()
    return bool(("asian" in m or "asiat" in m)
                and re.search(r"(über|over)\s*1(\.0)?(?![.\d])", m)
                and "1.5" not in m)


def _tip_has_asian_over1(tip: dict) -> bool:
    if _asian_over1_in_text(tip.get("market")):
        return True
    for lg in (tip.get("legs") or []):
        for sel in (lg.get("selections") or []):
            if _asian_over1_in_text(sel):
                return True
    return False



def _disguise_stakes(tip: dict) -> dict:
    """Owner rule (2026-07): mask that expert picks are cloned, and ALWAYS show $.
    - Expert bots: display 12x LESS than the source's real stake; unit-based stakes ('1u')
      become a VARIED $ amount so it never looks formulaic.
    - TipJarLogic: always show DOUBLE the posted stake.
    - Everyone else: keep the amount, only switch the currency symbol to $.
    Winnings are recomputed as stake x odds so the ticket stays consistent."""
    raw = tip.get("stake")
    if raw is None or not str(raw).strip():
        return tip  # nothing to show
    username = tip.get("username") or ""
    odds = _parse_num(tip.get("odds"))
    rnd = random.Random(str(tip.get("id", "")) + str(raw))
    units = _parse_units(raw)
    amount = _parse_num(raw)
    disp = None
    if username == "TipJarLogic":
        base = amount if amount is not None else (round(units * rnd.uniform(12, 24)) if units else None)
        disp = base * 2 if base is not None else None
    elif tip.get("is_expert") and not tip.get("is_master"):
        if units is not None:
            disp = round(units * rnd.uniform(12, 24))  # varied $/unit → organic amounts
        elif amount is not None:
            disp = round(amount / 12.0, 2)
    else:
        disp = amount  # keep the amount, only the currency symbol changes
    if disp is None or disp <= 0:
        return tip
    tip["stake"] = _fmt_usd(disp)
    if odds and odds > 0:
        tip["potential_return"] = _fmt_usd(disp * odds)
    elif tip.get("potential_return") and _parse_num(tip.get("potential_return")) is not None:
        tip["potential_return"] = _fmt_usd(_parse_num(tip.get("potential_return")))
    return tip


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



async def _slip_needs_clarification(tip: dict) -> list:
    """Which fields the member MUST fill in — kept deliberately minimal (owner 2026-07-23:
    'don't show the team-names window unless totally necessary'). We ONLY ask when the AI
    couldn't even read the team names off the slip. If both team names are present we accept
    the slip silently and let the background enrichment/settlement resolve league/kickoff
    (robust datescan fallbacks already handle minor leagues that API-Football can't verify)."""
    need = []
    home, away = _tip_match_teams(tip)
    if not (home and away):
        need.append("teams")
        # Only for a truly unreadable slip do we also ask for league/kickoff context.
        league = (tip.get("league") or "").strip()
        leg_leagues = any((l.get("league") or "").strip() for l in (tip.get("legs") or []))
        if not league and not leg_leagues:
            need.append("league")
        mt = (tip.get("match_time") or "").strip()
        leg_ko = any((l.get("kickoff") or "").strip() for l in (tip.get("legs") or []))
        if (not mt or mt == "Multibet") and not leg_ko:
            need.append("datetime")
    return need


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
            # Don't reject — accept the slip and ask the member to clarify the kickoff
            # afterwards (so players don't give up).
            match_time = ""
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
    # LIVE at post time — owner 2026-06: a COMMUNITY slip lands in the small "Community Live"
    # area ONLY when the member explicitly posts it as LIVE (timing == "live"). Long pregame
    # community slips must ALWAYS stay in the pregame community area — never auto-promoted to
    # live just because one leg happens to be in-play right now.
    now_dt = datetime.now(timezone.utc)
    timing = (inp.timing or "").strip().lower()
    is_live_post = timing == "live"
    # System-bet "Maximalquote" / fill an empty total: if no total odds were given, derive it
    # from the legs (per game: manual combo odd, else product of the selection odds).
    stored_odds = (inp.odds or "").strip()
    if not stored_odds and legs:
        gtotal, seen = 1.0, False
        for lg in legs:
            co = _parse_num(lg.get("combo_odds"))
            if co and co > 1.0:
                gtotal *= co
                seen = True
            else:
                prod = _odds_product([o for o in (lg.get("sel_odds") or []) if o])
                if prod and prod > 1.0:
                    gtotal *= prod
                    seen = True
        if seen and gtotal > 1.0:
            stored_odds = f"{round(gtotal, 2)}"
    bet_type = "system" if (inp.bet_type or "").lower() == "system" and inp.system_total else ""
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
        "odds": stored_odds,
        "ai_rating": inp.ai_rating,
        "ai_analysis": inp.ai_analysis,
        "legs": legs,
        "is_parlay": is_parlay,
        "bet_type": bet_type,
        "system_from": inp.system_from if bet_type else 0,
        "system_total": inp.system_total if bet_type else 0,
        "stake": inp.stake,
        "potential_return": compute_return(inp.stake, stored_odds, inp.potential_return),
        "status": "live" if is_live_post else "pending",
        "member_timing": timing or None,
        "sum_stars": inp.self_rating,
        "ratings_count": 1,
        "avg_rating": float(inp.self_rating),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # Owner rule 2026-07-29: an Asian "Über 1.0" leg (push at exactly 1 goal) is a valuable
    # near-lock → surface it in the "Geschenke" (Gifts) tab.
    if _tip_has_asian_over1(tip):
        tip["is_gift"] = True
    # Ask the member a friendly follow-up (never reject) when the AI struggled to
    # resolve teams/league/kickoff — so players don't give up.
    clarify = await _slip_needs_clarification(tip)
    # If the member already told us the timing (live/today/later), don't nag for kickoff.
    if timing in ("live", "today", "later") and "datetime" in clarify:
        clarify.remove("datetime")
    tip["needs_clarification"] = bool(clarify)
    tip["clarification_fields"] = clarify
    await db.tips.insert_one(tip)
    # record the owner's own rating so it counts and shows as "your rating"
    await db.tip_ratings.insert_one({
        "id": str(uuid.uuid4()), "tip_id": tip["id"], "user_id": user["id"],
        "stars": inp.self_rating, "created_at": tip["created_at"],
    })
    tip.pop("_id", None)
    return tip


# --- One unique in-house expert bot per monitored tipster channel ---------
# Each scraped source channel maps to exactly ONE anonymous bot persona. Add a new
# entry here (unique name + email) whenever a new tipster channel is scraped — never
# reuse Orion for a different source. Keys are channel names / X handles (lowercase).
_DEFAULT_EXPERT_BOT = {
    "email": "orion@tipjar.com", "name": "Orion",
    "bio": "In-house Value-Analyst — kuratierte Multis & Bet-Builder.",
}
_CHANNEL_BOTS = {
    "emptipstele": _DEFAULT_EXPERT_BOT,   # EMP Tips Telegram channel
    "emptips": _DEFAULT_EXPERT_BOT,       # EMP Tips X/Twitter handle
    "levykingtips": {                     # LEVY (@LevyKingTips) X/Twitter handle
        "email": "vega@tipjar.com", "name": "Vega",
        "bio": "In-house Sports-Analyst — datenbasierte Tipps für Fußball & Basketball.",
    },
    "thesuperbets": {                     # Super bets (t.me/thesuperbets) Telegram channel
        "email": "nova@tipjar.com", "name": "Nova",
        "bio": "In-house Value-Scout — sorgfältig kuratierte Multis & Einzeltipps.",
    },
    "chrisbetsbets": {                    # Chris bets (t.me/Chrisbetsbets) Telegram channel
        "email": "sirius@tipjar.com", "name": "Sirius",
        "bio": "In-house Tipp-Analyst — scharfe Value-Picks & Bet-Builder.",
    },
    "grizzlybetslive": {                  # Grizzly Bets (@grizzlybetslive) X/Twitter handle
        "email": "rigel@tipjar.com", "name": "Rigel",
        "bio": "In-house Analyst — datengetriebene Freepicks & Live-Tipps.",
    },
    "bet_of_the_day_tips_free": {         # BET OF THE DAY TIPS FREE (Telegram channel)
        "email": "polaris@tipjar.com", "name": "Polaris",
        "bio": "In-house Analyst — täglicher Value-Pick des Tages.",
    },
    "betmastersfreee": {                  # BET KING.gr (t.me/betmastersfreee) Telegram channel
        "email": "altair@tipjar.com", "name": "Altair",
        "bio": "In-house Analyst — kuratierte Tages-Tipps & Kombis.",
    },
    "bettingfriendss": {                  # Betting Friends (@bettingfriendss) X/Twitter handle
        "email": "lyra@tipjar.com", "name": "Lyra",
        "bio": "In-house Analyst — Accas, Inplays & Value-Picks.",
    },
    "dgdfreetips": {                      # DGD Football Tips (@DGDFreeTips) X/Twitter handle
        "email": "vela@tipjar.com", "name": "Vela",
        "bio": "In-house Analyst — Pre-Match & In-Play Bet-Builder.",
    },
    "bettingwithtyga": {                  # betting with tyga (t.me/bettingwithtyga) Telegram channel
        "email": "antares@tipjar.com", "name": "Antares",
        "bio": "In-house Analyst — Daily Slips & VIP-Value.",
    },
    "andrikopoulosbet": {                 # AndrikopoulosBet FREE (t.me/andrikopoulosbet) Telegram
        "email": "deneb@tipjar.com", "name": "Deneb",
        "bio": "In-house Analyst — griechische Ligen & Value-Kombis.",
    },
    "docbettingg": {                      # The Doc (t.me/DocBettingg) Telegram channel
        "email": "capella@tipjar.com", "name": "Capella",
        "bio": "In-house Analyst — scharfe Singles & Kombis.",
        "silent": True,                   # silent scraper: feeds the Master, never posts publicly
    },
    "totissports": {                      # Totis Sports website (totissports.gr) — all tipsters
        "email": "atlas@tipjar.com", "name": "Atlas",
        "bio": "In-house Analyst — tägliche Value-Analysen aus GR-Experten-Pool.",
    },
    # Future tipster channels → add a UNIQUE bot here, e.g.:
    # "somechannel": {"email": "spica@tipjar.com", "name": "Spica", "bio": "..."},
}


# Source slugs of SILENT scrapers (e.g. Capella) — they feed the Master in the background
# but must NEVER surface in any public feed. Derived from the bot personas so a bot marked
# silent is excluded everywhere, even for legacy picks stored before the `hidden` flag
# existed (belt-and-suspenders alongside q["hidden"]={"$ne":True}).
SILENT_SOURCE_SLUGS = sorted({
    re.sub(r'[^a-z0-9]+', '', (cfg.get("name") or "").lower())
    for cfg in _CHANNEL_BOTS.values() if cfg.get("silent")
} - {""})


def _exclude_silent_sources(q: dict) -> None:
    """Merge the silent-scraper source exclusion into a tips query without clobbering an
    existing `source` constraint."""
    if not SILENT_SOURCE_SLUGS:
        return
    existing = q.get("source")
    if existing is None:
        q["source"] = {"$nin": list(SILENT_SOURCE_SLUGS)}
    elif isinstance(existing, dict) and "$nin" in existing:
        existing["$nin"] = sorted(set(existing["$nin"]) | set(SILENT_SOURCE_SLUGS))
    # A specific string source is never a silent slug in practice → leave it untouched.


def _bot_for_channel(channel: str) -> dict:
    """Resolve the unique expert bot persona for a given source channel/handle."""
    key = (channel or "").lstrip("@").strip().lower()
    return _CHANNEL_BOTS.get(key, _DEFAULT_EXPERT_BOT)


async def _get_expert_bot(bot_cfg: dict = None):
    """Anonymous in-house expert persona (one per tipster channel). Monitored slips are
    re-posted under this bot (role=expert → orange card + Experte badge in the community
    feed). Source channels are never revealed."""
    cfg = bot_cfg or _DEFAULT_EXPERT_BOT
    bot = await db.users.find_one({"email": cfg["email"]})
    if bot:
        return bot
    now = datetime.now(timezone.utc).isoformat()
    bot = {
        "id": str(uuid.uuid4()), "email": cfg["email"], "username": cfg["name"],
        "password_hash": "", "role": "expert", "is_verified": True, "verified": True,
        "credits": 0, "received_credits": 0, "referral_code": uuid.uuid4().hex[:8],
        "apex_flame": False, "streak": 0, "ratings_given": 0, "created_at": now, "is_bot": True,
        "silent": bool(cfg.get("silent")),
        "bio": cfg.get("bio", ""),
    }
    await db.users.insert_one(bot)
    logger.info(f"Created expert bot '{cfg['name']}'")
    return bot


def _scrub_source(text: str) -> str:
    """Remove anything that could reveal the original tipster/channel."""
    t = re.sub(r'https?://\S+|t\.me/\S+|@\w+', '', text or '')
    t = re.sub(r'(?i)\bemp\s*tips?\b', '', t)
    return re.sub(r'[ \t]{2,}', ' ', t).strip()


def _expert_playable_time(match_time, legs, now) -> bool:
    """Owner 2026-07 ('the tip arrived after the games were over — useless'): an expert
    slip must be posted while it's STILL PLAYABLE, i.e. BEFORE the (earliest) kickoff.
    A pre-match parlay/single whose kickoff has already passed can't be placed anymore, so
    we drop it instead of posting a dead tip. Small grace for scrape/vision latency."""
    times = [match_time] + [lg.get("kickoff") for lg in (legs or [])]
    has_time = any((t or "").strip() for t in times)
    if not has_time:
        return False  # no time at all → reject at ingest
    # Only judge kickoffs that carry an actual clock time (date-only slips can't be timed).
    timed = [ko for t in times
             if (ko := _parse_kickoff(t)) and not _kickoff_is_date_only(t)]
    if not timed:
        return True  # date-only / unparseable time present → allow (can't prove it's past)
    return min(timed) >= now - timedelta(minutes=10)


async def _ingest_emptips(images_b64, image_blobs, text, source_url="", skip_if_empty=False, bot_cfg=None):
    """Shared core: vision-AI a betslip (image/text) → re-post it ANONYMOUSLY as an expert
    community pick (orange), enriched with real hit-rate stats. The posting bot is resolved
    from bot_cfg (one unique persona per source channel). image_blobs = list of
    (bytes, ext, content_type). When skip_if_empty (auto path), returns None for promo/results
    posts with no real pick."""
    bot = await _get_expert_bot(bot_cfg)
    bot_name = bot.get("username") or (bot_cfg or _DEFAULT_EXPERT_BOT)["name"]
    bot_slug = re.sub(r'[^a-z0-9]+', '', bot_name.lower()) or "expert"
    detected = await analyze_tip(images_b64 or None, text)
    if not detected.get("safe", True):
        if skip_if_empty:
            return None
        raise HTTPException(status_code=422, detail=detected.get("flag_reason") or "Inhalt nicht erlaubt.")
    legs = _sanitize_legs(detected.get("legs"))
    if skip_if_empty and not legs and not (detected.get("market") or "").strip() and not (detected.get("odds") or "").strip():
        return None  # promo / results / hype post → not an actual pick
    # Enforce a recognized, still-playable match time before posting (feed quality).
    if not _expert_playable_time(detected.get("match_time", ""), legs, datetime.now(timezone.utc)):
        if skip_if_empty:
            return None
        raise HTTPException(status_code=422,
                            detail="Kein gültiger Spielzeitpunkt erkannt — Schein nicht veröffentlicht.")
    image_paths = []
    for rb, ext, ct in image_blobs:
        path = f"{APP_NAME}/expert/{uuid.uuid4()}.{ext}"
        try:
            res = put_object(path, rb, ct or "image/png")
            image_paths.append(res["path"])
        except Exception as e:
            logger.warning(f"expert-bot image store failed: {e}")
    is_parlay = bool(detected.get("is_parlay") or len(legs) > 1
                     or (legs and len(legs[0].get("selections", [])) > 1))
    stats_line = ""
    if detected.get("home_team") and detected.get("away_team"):
        stats_line = await _pick_stats_line({"home": detected["home_team"], "away": detected["away_team"]})
    analysis = _scrub_source(detected.get("analysis") or "")
    analysis = f"🔮 {bot_name}: {analysis}" if analysis else f"🔮 {bot_name} Pick"
    if stats_line:
        analysis += f"\n\n📊 {stats_line}"
    tip = {
        "id": f"{bot_slug}-{uuid.uuid4().hex[:10]}",
        "user_id": bot["id"], "username": bot_name,
        "raw_text": _scrub_source(text), "is_expert": True,
        "image_path": image_paths[0] if image_paths else None,
        "image_paths": image_paths,
        "home_team": detected.get("home_team", ""), "away_team": detected.get("away_team", ""),
        "match_time": detected.get("match_time", ""),
        "country": detected.get("country", ""), "league": detected.get("league", ""),
        "market": detected.get("market", ""), "odds": detected.get("odds", ""),
        "ai_rating": detected.get("rating", 7.0), "ai_analysis": analysis,
        "stats_line": stats_line,
        "legs": legs, "is_parlay": is_parlay,
        "stake": detected.get("stake", ""),
        "potential_return": detected.get("potential_return", ""),
        "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
        "source": bot_slug, "category": "value",
        "hidden": bool((bot_cfg or {}).get("silent")),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tips.insert_one(tip)
    tip.pop("_id", None)
    return tip


@api_router.post("/admin/emptips/ingest")
async def admin_emptips_ingest(
    file: Optional[UploadFile] = File(default=None),
    files: List[UploadFile] = File(default=[]),
    text: str = Form(default=""),
    admin: dict = Depends(require_admin),
):
    """Manually ingest an EMP Tips betslip (screenshot(s) and/or text)."""
    uploads = [f for f in ([file] + list(files)) if f is not None and getattr(f, "filename", None)][:4]
    images_b64, image_blobs = [], []
    for f in uploads:
        rb = await f.read()
        images_b64.append(base64.b64encode(rb).decode("utf-8"))
        ext = (f.filename.rsplit(".", 1)[-1] if f.filename and "." in f.filename else "png").lower()
        image_blobs.append((rb, ext, f.content_type or "image/png"))
    if not images_b64 and not text.strip():
        raise HTTPException(status_code=400, detail="Bitte ein Wettschein-Bild oder Text angeben.")
    tip = await _ingest_emptips(images_b64, image_blobs, text)
    return {"ok": True, "tip": tip}


@api_router.post("/admin/emptips/run")
async def admin_emptips_run(admin: dict = Depends(require_admin)):
    """Trigger the auto EMP reader in the BACKGROUND (vision-AI on betslips is slow, so we
    don't block the request past the gateway timeout). Check results via the tips feed."""
    _BG_TASKS.append(asyncio.create_task(emptips_autopost()))
    return {"ok": True, "scheduled": True, "note": "Running in background; new EMP picks appear in the feed shortly."}


EMPTIPS_HANDLE = os.environ.get("EMPTIPS_HANDLE", "").strip()
# Source of truth = code (works in production without env juggling). Each channel/handle
# MUST have a matching persona in _CHANNEL_BOTS. Env vars only ADD extra sources.
_CODE_TG_CHANNELS = ["EMPTipsTele", "thesuperbets", "Chrisbetsbets", "bet_of_the_day_tips_free", "betmastersfreee", "bettingwithtyga", "andrikopoulosbet", "DocBettingg"]   # public Telegram channels
_CODE_X_HANDLES = ["EmpTips", "LevyKingTips", "grizzlybetslive", "bettingfriendss", "DGDFreeTips"]          # public X/Twitter handles
_env_tg = [c.strip().lstrip("@") for c in
           (os.environ.get("WATCH_TG_CHANNELS", "") or os.environ.get("EMPTIPS_TG_CHANNEL", "")).split(",") if c.strip()]
_env_x = [h.strip().lstrip("@") for h in
          (os.environ.get("WATCH_X_HANDLES", "") or EMPTIPS_HANDLE).split(",") if h.strip()]
# code list first, env additions appended, de-duplicated (case-insensitive).
def _merge_sources(base, extra):
    out, low = [], set()
    for s in base + extra:
        k = s.lower()
        if k not in low:
            low.add(k); out.append(s)
    return out
WATCH_TG_CHANNELS = _merge_sources(_CODE_TG_CHANNELS, _env_tg)
WATCH_X_HANDLES = _merge_sources(_CODE_X_HANDLES, _env_x)
_EMP_RESULT_KW = re.compile(
    r'(boo+m|fl(y|ies|ys)\s*in|winner+|congrats|landed|cash(ed)?|smashed|\bgreen\b|'
    r'\+\d+(\.\d+)?u\b|nap won|banked|paid out)', re.I)


async def emptips_autopost() -> dict:
    """Auto-read EMP Tips' latest posts for FREE (public Telegram web preview first, then X
    via Nitter mirrors), turn each NEW betslip post into a public 'EMP Tips' pick via vision-AI.
    No API/keys/cost. Results/hype posts (no real pick) are skipped. Tracked in db.emptips_seen."""
    if not WATCH_TG_CHANNELS and not WATCH_X_HANDLES:
        return {"posted": 0, "reason": "no source configured"}
    import emptips_watch
    posts = []
    for ch in WATCH_TG_CHANNELS:
        chan_posts = await asyncio.to_thread(emptips_watch.fetch_telegram, ch)
        for p in chan_posts:
            p["_channel"] = ch  # remember source → resolve its unique bot later
        posts += chan_posts
    for h in WATCH_X_HANDLES:
        x_posts = await asyncio.to_thread(emptips_watch.fetch_timeline, h)
        for p in x_posts:
            p["_channel"] = h
        posts += x_posts
    if not posts:
        return {"posted": 0, "reason": "source unavailable"}
    # First activation: baseline the current backlog as 'seen' WITHOUT posting stale tips.
    if await db.emptips_seen.count_documents({}) == 0:
        base = [{"id": tw["id"], "at": datetime.now(timezone.utc).isoformat(),
                 "posted": False, "baseline": True} for tw in posts]
        if base:
            await db.emptips_seen.insert_many(base)
        return {"posted": 0, "baseline": len(base)}
    MAX_PER_RUN = 8  # bound slow vision-AI calls per run (fast loop clears backlog quickly)
    posted, scanned = 0, 0
    for tw in reversed(posts):  # newest first
        if scanned >= MAX_PER_RUN:
            break
        if await db.emptips_seen.find_one({"id": tw["id"]}, {"_id": 1}):
            continue
        text = tw["text"] or ""
        low = text.lower()
        looks_tip = ("add to your bet slip" in low
                     or (bool(tw["images"]) and not _EMP_RESULT_KW.search(text)))
        seen_doc = {"id": tw["id"], "at": datetime.now(timezone.utc).isoformat(), "posted": False}
        if not looks_tip:
            await db.emptips_seen.insert_one(seen_doc)
            continue
        scanned += 1
        images_b64, image_blobs = [], []
        for iu in tw["images"][:4]:
            raw = await asyncio.to_thread(emptips_watch.fetch_image, iu)
            if raw:
                images_b64.append(base64.b64encode(raw).decode("utf-8"))
                image_blobs.append((raw, "jpg", "image/jpeg"))
        try:
            bot_cfg = _bot_for_channel(tw.get("_channel", ""))
            tip = await _ingest_emptips(images_b64, image_blobs, text, source_url=tw["url"], skip_if_empty=True, bot_cfg=bot_cfg)
            if tip:
                seen_doc.update({"posted": True, "tip_id": tip["id"]})
                posted += 1
        except Exception as e:
            logger.warning(f"emptips auto-ingest failed for {tw['id']}: {e}")
        await db.emptips_seen.insert_one(seen_doc)
    return {"posted": posted, "scanned": scanned, "fetched": len(posts)}


async def emptips_loop():
    await asyncio.sleep(120)
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            res = await emptips_autopost()
            logger.info(f"EMP Tips watch loop: {res}")
        except Exception as e:
            logger.error(f"EMP Tips watch loop error: {e}")
        await asyncio.sleep(7 * 60)  # every 7 minutes — expert tips land BEFORE kickoff


# --- Totis Sports website scraper (totissports.gr) — all tipsters → one bot "Atlas" -------
TOTISSPORTS_PAGES = [
    ("totis", "https://totissports.gr/analysi-agona-tis-imeras/"),
    ("zak", "https://totissports.gr/analysis-agonon/analysi-agona-apo-zak/"),
    ("dallop", "https://totissports.gr/analysis-agonon/analysi-agona-apo-dallop/"),
    ("betstriker", "https://totissports.gr/analysis-agonon/analysi-agona-apo-betstriker/"),
    ("arxigos", "https://totissports.gr/analysis-agonon/analysi-agona-apo-arxigos/"),
]


def _totissports_extract(html: str) -> str:
    """Pull the compact pick block (teams + kickoff + Greek estimation w/ odds) from a
    Totis Sports analysis page. Returns '' if no pick found. Feeds the LLM parser."""
    # strip tags → plain text lines
    txt = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.DOTALL | re.I)
    txt = re.sub(r"<[^>]+>", "\n", txt)
    txt = re.sub(r"&nbsp;|&#160;", " ", txt)
    txt = re.sub(r"&amp;", "&", txt)
    lines = [l.strip() for l in txt.split("\n") if l.strip()]
    joined = "\n".join(lines)
    _BAD = ("TOTIS", "ANALYS", "ΑΝΑΛΥΣ", "SPORT", "ΠΡΟΓΝΩΣ", "STOIXIMA", "ΣΤΟΙΧΗΜΑ",
            "COOKIE", "MENU", "HOME", "ΑΡΧΙΚΗ")
    def _looks_matchup(l):
        if len(l) > 55 or ("-" not in l and "–" not in l and " vs" not in l.lower()):
            return False
        if re.search(r"\d", l) or any(b in l.upper() for b in _BAD):
            return False
        letters = sum(c.isalpha() for c in l)
        return letters >= 6
    kick = re.search(r"(\d{2}/\d{2}/\d{2,4}\s+\d{1,2}:\d{2})", joined)
    # matchup: prefer a line right around the kickoff date, else first plausible one
    teams_line = ""
    date_idx = next((i for i, l in enumerate(lines) if kick and kick.group(1) in l), -1)
    if date_idx >= 0:
        for l in lines[max(0, date_idx - 3): date_idx + 4]:
            if _looks_matchup(l):
                teams_line = l
                break
    if not teams_line:
        for l in lines:
            if _looks_matchup(l):
                teams_line = l
                break
    # estimation paragraph: after a line containing "Εκτίμηση"
    est = ""
    for i, l in enumerate(lines):
        if "κτίμηση" in l and i + 1 < len(lines):
            est = lines[i + 1]
            break
    if not est:
        # fallback: first line that contains odds like 1.62 / 2.10
        for l in lines:
            if re.search(r"\b\d\.\d{2}\b", l) and len(l) > 25:
                est = l
                break
    if not est or not re.search(r"\b\d\.\d{2}\b", est):
        return ""  # no clear pick/odds → skip
    if not teams_line:
        return ""  # no identifiable matchup → skip (keep expert feed clean)
    return " | ".join([f"Spiel: {teams_line}",
                       *( [f"Anpfiff {kick.group(1)}"] if kick else [] ),
                       f"Tipster-Einschätzung: {est}"])


async def totissports_autopost() -> dict:
    """Scrape all Totis Sports tipster pages → post each daily pick ANONYMOUSLY under the
    single 'Atlas' expert bot (owner: all tipsters together, one expert). Dedup per pick."""
    bot_cfg = _CHANNEL_BOTS["totissports"]
    posted = 0
    for tipster, url in TOTISSPORTS_PAGES:
        try:
            r = await asyncio.to_thread(
                lambda: requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20))
        except Exception as e:
            logger.warning(f"totissports fetch {tipster}: {e}")
            continue
        if not getattr(r, "ok", False):
            continue
        block = _totissports_extract(r.text)
        if not block:
            continue
        key = "tot-" + tipster + "-" + hashlib.md5(block.encode("utf-8")).hexdigest()[:12]
        if await db.emptips_seen.find_one({"id": key}, {"_id": 1}):
            continue
        try:
            tip = await _ingest_emptips([], [], block, source_url=url,
                                        skip_if_empty=True, bot_cfg=bot_cfg)
            await db.emptips_seen.insert_one({
                "id": key, "at": datetime.now(timezone.utc).isoformat(),
                "posted": bool(tip)})
            if tip:
                posted += 1
        except Exception as e:
            logger.warning(f"totissports ingest {tipster}: {e}")
    if posted:
        logger.info(f"Totis Sports: posted {posted} pick(s) as Atlas")
    return {"posted": posted}


async def totissports_loop():
    await asyncio.sleep(180)
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            res = await totissports_autopost()
            logger.info(f"Totis Sports loop: {res}")
        except Exception as e:
            logger.error(f"Totis Sports loop error: {e}")
        await asyncio.sleep(30 * 60)  # every 30 minutes — post tips close to real-time





@api_router.post("/tips/{tip_id}/clarify")
async def clarify_tip(tip_id: str, inp: ClarifyInput, user: dict = Depends(get_current_user)):
    """Member fills in the fields the AI couldn't resolve (teams/league/kickoff).
    Clears the clarification flag and lets the enrichment retry."""
    tip = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    if tip.get("user_id") != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not your tip")
    upd = {"needs_clarification": False, "clarification_fields": [], "enrich_tries": 0}
    if inp.league and inp.league.strip():
        upd["league"] = inp.league.strip()
    if inp.match_time and inp.match_time.strip():
        upd["match_time"] = inp.match_time.strip()
    legs = tip.get("legs") or []
    if inp.home_team and inp.away_team and inp.home_team.strip() and inp.away_team.strip():
        upd["home_team"] = inp.home_team.strip()
        upd["away_team"] = inp.away_team.strip()
        if len(legs) == 1:
            legs[0]["match"] = f"{inp.home_team.strip()} \u2013 {inp.away_team.strip()}"
    if len(legs) == 1:
        if upd.get("league"):
            legs[0]["league"] = upd["league"]
        if upd.get("match_time"):
            legs[0]["kickoff"] = upd["match_time"]
    if legs:
        upd["legs"] = legs
    await db.tips.update_one({"id": tip_id}, {"$set": upd})
    return {"ok": True}
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


# Real (human) members only: excludes admin, automated test/bot accounts (@t.com
# emails, created by tests/E2E) and the internal HQ posting account. Used for the
# "registered members" analytics so the count reflects actual people, not seeds/bots.
REAL_MEMBER_QUERY = {
    "role": {"$ne": "admin"},
    "$nor": [{"email": {"$regex": r"@t\.com$"}}, {"email": "hq@tipjar.com"}],
}


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


# ------------------------------------------------------------ dynamic i18n
# Free-form prose (KI-Analysen, Smart-Berichte, Master-Texte) is generated/stored in one
# language. To show it in ALL 8 UI languages we translate on demand via the Emergent LLM
# key and cache each (text, lang) permanently in db.translation_cache. First view of a
# string in a language costs one LLM call; every later view is instant from cache.
_LANG_NAMES = {"en": "English", "de": "German", "es": "Spanish", "el": "Greek",
               "fr": "French", "it": "Italian", "ar": "Arabic", "tr": "Turkish"}


def _extract_json_obj(raw: str):
    import json
    s = (raw or "").strip()
    a, b = s.find("{"), s.rfind("}")
    if a == -1 or b == -1 or b <= a:
        return None
    try:
        return json.loads(s[a:b + 1])
    except Exception:
        return None


async def _translate_batch(texts, lang: str) -> dict:
    target = _LANG_NAMES.get(lang)
    out, missing = {}, []
    for txt in texts:
        if not txt or not isinstance(txt, str):
            continue
        if txt in out:
            continue
        key = hashlib.sha1(f"{lang}:{txt}".encode("utf-8")).hexdigest()
        doc = await db.translation_cache.find_one({"_id": key}, {"t": 1})
        if doc:
            out[txt] = doc["t"]
        else:
            missing.append((key, txt))
    if not missing:
        return out
    if not (target and EMERGENT_LLM_KEY):
        for _, t in missing:
            out[t] = t
        return out
    for i in range(0, len(missing), 15):
        chunk = missing[i:i + 15]
        numbered = "\n".join(f"[{j}] {t}" for j, (_, t) in enumerate(chunk))
        data = None
        try:
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY, session_id=f"tr-{uuid.uuid4()}",
                system_message=(
                    f"You are a professional translator for a football betting-tips app. "
                    f"Translate each numbered item into {target}. Keep team names, player names, "
                    f"league names, numbers, odds and market lines (e.g. 'Über 2.5 Tore') intact and "
                    f"natural. Preserve emojis and line breaks. If an item is already in {target}, return "
                    f"it unchanged. Reply with ONLY a JSON object mapping each index as a string to its "
                    f"translation, e.g. {{\"0\":\"…\",\"1\":\"…\"}}. No commentary."),
            ).with_model(AI_MODEL_PROVIDER, AI_TEXT_MODEL)
            resp = await chat.send_message(UserMessage(text=numbered))
            data = _extract_json_obj(resp if isinstance(resp, str) else str(resp))
        except Exception as e:
            logger.error(f"translate batch failed: {e}")
        for j, (key, t) in enumerate(chunk):
            tr = (data or {}).get(str(j)) if data else None
            tr = tr if (isinstance(tr, str) and tr.strip()) else t
            out[t] = tr
            if data is not None:
                await db.translation_cache.update_one(
                    {"_id": key}, {"$set": {"t": tr, "lang": lang}}, upsert=True)
    return out


class TranslateReq(BaseModel):
    lang: str
    texts: List[str]


@api_router.post("/i18n/translate")
async def i18n_translate(req: TranslateReq):
    """Translate a batch of prose strings into req.lang (cached). German is the source
    language of most content, so it is returned unchanged."""
    if not req.lang or req.lang == "de" or not req.texts:
        return {"map": {}}
    return {"map": await _translate_batch(req.texts[:60], req.lang)}



@api_router.get("/tips")
async def list_tips(status: Optional[str] = None, sort: str = "new",
                    source: Optional[str] = None, window: Optional[str] = None,
                    category: Optional[str] = None, mcat: Optional[str] = None,
                    limit: int = 50):
    q = {}
    # Silent scrapers (e.g. Capella) feed the Master in the background but never surface
    # publicly — hide their picks from every feed.
    q["hidden"] = {"$ne": True}
    if status:
        q["status"] = status
    # Every AI single lands in exactly one bucket. Banker/Risk are strict;
    # VALUE is the catch-all so no pick can ever fall through the cracks.
    if category == "banker":
        q["category"] = "banker"
    elif category == "risk":
        q["category"] = "risk"
    elif category == "banger":
        q["category"] = "banger"
    elif category == "mental":
        q["category"] = "mental"
    elif category == "value":
        q["category"] = {"$nin": ["banker", "risk", "banger", "mental", "gift"]}
    elif category == "gifts":
        # "Δώρα" (Gifts): cross-cutting — generous odds for a likely-ish outcome.
        # Flagged on the pick itself (singles & bet-builder combos), any base category.
        q["is_gift"] = True
    if source == "ai":
        # Gifts are cross-cutting (KI singles/combos AND owner-posted near-lock slips like
        # Asian Über 1.0). Don't restrict the Gifts tab to hq-auto so those safe gifts show up.
        if category != "gifts":
            q["source"] = "hq-auto"
        if category not in ("mental", "banker", "risk", "banger", "value", "gifts"):
            q["category"] = {"$ne": "mental"}   # mental only in its own tab
    elif source == "smart":
        q["source"] = "smart"
    elif source == "master":
        q["source"] = "hq-master"
        # Master sub-categories: Einfach / Mittel / Challenge packs carry a
        # master_category; "slips" = the consensus + live-alternative picks (no category).
        if mcat in ("einfach", "mittel", "challenge"):
            q["master_category"] = mcat
        elif mcat == "safe":
            q["master_category"] = "safe"
        elif mcat == "special":
            q["master_category"] = "special"
        elif mcat == "avatar":
            q["master_category"] = "avatar"
        elif mcat == "hotscorer":
            q["master_category"] = "hotscorer"
        elif mcat == "slips":
            q["master_category"] = {"$exists": False}
    elif source == "members":
        # Community = ONLY real member picks. All KI/HQ sources (AI singles, systems,
        # live-AI, smart, Master) are excluded so no bot ever posts into Community.
        q["source"] = {"$nin": ["hq-auto", "smart", "hq-live", "hq-system", "hq-master"]}
        q["username"] = {"$nin": ["TipJarHQ", "TipJarHQ System"]}
    elif source == "kilive":
        # "Live KI Picks" — only the KI-generated live picks (no community members).
        q["source"] = {"$in": ["hq-auto", "hq-live", "hq-system", "smart"]}
    elif source == "bestwon":
        # "Best Won" bucket (owner): all winning Smart + Risk-single + Community +
        # System picks — the special wins the owner wants to track (esp. systems).
        q["$or"] = [
            {"source": "smart"},
            {"source": "hq-system"},
            {"source": "hq-auto", "category": "risk"},
            {"source": {"$nin": ["hq-auto", "smart", "hq-live", "hq-system", "hq-master"]}},
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
    # Silent scrapers (Capella) must never surface — enforced by source, not just `hidden`.
    _exclude_silent_sources(q)
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
    # Never surface a team-less ('Unknown') slip publicly — the poster is asked to fill
    # the teams first; until then it stays out of every feed (owner rule 2026-07-23).
    tips = [t for t in tips if _tip_has_known_teams(t)]
    # A pick flagged 'in danger' live is ALWAYS shown as risk (never banker), regardless
    # of any write-path race that might leave a stale category on the document.
    for t in tips:
        if t.get("live_danger"):
            t["category"] = "risk"
    # Owner 2026-07-30: mark every feed pick whose match has an open GIFT (🎁 "vom Master
    # gedeckt") so the whole feed shows the gift's coverage at a glance.
    gift_keys = await _gift_match_keys()
    if gift_keys:
        for t in tips:
            if t.get("is_gift"):
                continue
            h, a = t.get("home_team"), t.get("away_team")
            if h and a and _match_key(h, a) in gift_keys:
                t["gift_covered"] = True
    return await _tag_expert(tips[:limit])


def _in_kickoff_window(match_time: str, window: str, now) -> bool:
    ko = _parse_kickoff(match_time)
    if not ko:
        return True  # no parseable time → always show, never hide a tip
    hours = (ko - now).total_seconds() / 3600
    # Owner rule 2026-07-24: NEVER show a pick whose match already kicked off >3h ago
    # (it's finished / in-play, not a placeable "upcoming" pick) — this is what caused
    # yesterday's played games to keep showing in the KI feed.
    if hours < -3:
        return False
    if window == "24":
        return hours < 24
    if window == "48":
        return 24 <= hours < 48
    return hours >= 48  # "48plus"


@api_router.get("/tips/mine")
async def my_tips(user: dict = Depends(get_current_user)):
    tips = await db.tips.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return [_disguise_stakes(t) for t in tips]


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


# ------------------------------------------------------------------ admin slip editor
def _admin_sanitize_legs(legs) -> list:
    """Preserve everything an admin may edit on a leg — including `status` (which the
    normal member sanitizer drops)."""
    out = []
    for lg in (legs or []):
        if not isinstance(lg, dict):
            continue
        sels = [str(s).strip() for s in (lg.get("selections") or []) if str(s).strip()][:10]
        sodds = [str(o or "").strip() for o in (lg.get("sel_odds") or [])][:10]
        clean = {
            "match": str(lg.get("match", "") or "").strip(),
            "league": str(lg.get("league", "") or "").strip(),
            "kickoff": str(lg.get("kickoff", "") or "").strip(),
            "selections": sels,
            "sel_odds": sodds,
            "banker": bool(lg.get("banker", False)),
        }
        st = lg.get("status")
        if st in ("pending", "live", "won", "lost", "void"):
            clean["status"] = st
        out.append(clean)
    return out[:12]


@api_router.patch("/admin/tips/{tip_id}")
async def admin_edit_tip(tip_id: str, payload: dict, admin: dict = Depends(require_admin)):
    """Admin correction of any existing slip: fix kickoff/times, team names & positions,
    league/country, market/odds/stake, and edit or remove individual legs (incl. per-leg
    status, banker, selections & odds)."""
    tip = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    upd = {}
    for fld in ("match_time", "home_team", "away_team", "league", "country", "market", "odds", "stake"):
        if fld in payload and payload[fld] is not None:
            upd[fld] = str(payload[fld]).strip()
    if payload.get("swap_teams"):
        h = upd.get("home_team", tip.get("home_team", "") or "")
        a = upd.get("away_team", tip.get("away_team", "") or "")
        upd["home_team"], upd["away_team"] = a, h
    if isinstance(payload.get("legs"), list):
        legs = _admin_sanitize_legs(payload["legs"])
        upd["legs"] = legs
        upd["is_parlay"] = len(legs) > 1 or (len(legs) == 1 and len(legs[0].get("selections", [])) > 1)
    new_odds = upd.get("odds", tip.get("odds", "") or "")
    new_stake = upd.get("stake", tip.get("stake", "") or "")
    if "odds" in upd or "stake" in upd:
        upd["potential_return"] = compute_return(new_stake, new_odds, "")
    upd["admin_edited"] = True
    upd["admin_edited_at"] = datetime.now(timezone.utc).isoformat()
    upd["settle_attempts"] = 0  # re-grade cleanly after an edit
    await db.tips.update_one({"id": tip_id}, {"$set": upd})
    return await db.tips.find_one({"id": tip_id}, {"_id": 0})


@api_router.post("/admin/tips/{tip_id}/settle-now")
async def admin_settle_tip_now(tip_id: str, admin: dict = Depends(require_admin)):
    """Manual 'Spiel zuende' trigger — forces the AI results engine to re-check THIS slip.
    Resets its retry budget then runs the matching settle pass. Returns the fresh slip;
    `settled` is true only when the engine actually resolved it (won/lost/void/cashed)."""
    tip = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    await db.tips.update_one({"id": tip_id}, {"$set": {"settle_attempts": 0}})
    _reset_api_quota_flag()
    result = {}
    try:
        if tip.get("is_parlay"):
            result["parlays"] = await settle_multimatch_parlays()
        else:
            result["singles"] = await settle_pending_tips()
    except Exception as e:
        logger.error(f"manual settle failed for {tip_id}: {e}")
        result["error"] = str(e)
    fresh = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    result["tip"] = fresh
    result["settled"] = bool(fresh and fresh.get("status") not in ("pending", "live"))
    if _api_quota_exhausted():
        result["reason"] = "API-Football Tageslimit erreicht – bitte später erneut versuchen."
    elif not result["settled"]:
        result["reason"] = "Spiel noch nicht als beendet erkannt – bitte kurz nach Abpfiff erneut versuchen."
    return result


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


from ticket_render import (  # noqa: E402  (extracted ticket renderer)
    _fmt_selection, _to_float, _split_match, _tip_to_render_legs,
    _render_slip_image, FONT_DIR, CREST_PATH, _TICKET_LABELS,
)


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
    stake, winnings = _money_to_usd(stake), _money_to_usd(winnings)  # always $
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


def _is_house_single(username: str, is_parlay=None, legs_count=None) -> bool:
    """Owner rule: TipJarHQ AND TipJarMaster earn a Hall-of-Fame spot ONLY with their
    systems/parlays — never with single picks."""
    u = (username or "")
    house = u.startswith("TipJarHQ") or u == "TipJarMaster"
    if not house:
        return False
    if is_parlay is not None:
        return not is_parlay
    return (legs_count or 1) <= 1


# Owner 2026-07-26: the Hall of Fame officially opens 1 Aug 2026 — nothing before that date
# is ever shown. It holds SYSTEMS ONLY (≥ 2 legs) with a minimum total quote; TipJarHQ's own
# systems must clear a much higher bar (20.00) than community/expert/Master systems (3.00).
HOF_START = datetime(2026, 8, 1, tzinfo=timezone.utc)
HOF_MIN_ODDS_HOUSE = 20.0
HOF_MIN_ODDS_DEFAULT = 3.0


def _hof_min_odds(username: str) -> float:
    u = (username or "")
    return HOF_MIN_ODDS_HOUSE if (u.startswith("TipJarHQ") or u == "TipJarMaster") else HOF_MIN_ODDS_DEFAULT


def _hof_after_start(iso: str) -> bool:
    d = _parse_kickoff(iso or "")
    return bool(d and d >= HOF_START)


def _money_to_usd(s):
    """Reformat any money string to a $ amount (keeps the number, swaps the symbol)."""
    n = _parse_num(s)
    if n is not None and n > 0:
        return _fmt_usd(n)
    return (str(s or "").replace("€", "$").replace("£", "$").replace("EUR", "$"))


@api_router.get("/wins/hall-of-fame")
async def hall_of_fame():
    raw = await db.win_claims.find(
        {"status": "approved"}, {"_id": 0, "sig": 0, "user_id": 0}
    ).sort("total_odds", -1).limit(200).to_list(200)
    # Owner rule 2026-07-26: HoF opens 1 Aug 2026. SYSTEMS ONLY (≥ 2 legs). Minimum total
    # quote is 3.00 — EXCEPT TipJarHQ's own systems, which must clear 20.00.
    docs = [d for d in raw
            if (d.get("legs_count") or 1) >= 2
            and _to_float(d.get("total_odds")) >= _hof_min_odds(d.get("username"))
            and _hof_after_start(d.get("created_at"))][:24]
    for d in docs:  # trophies always show $ too (owner rule)
        if d.get("stake"):
            d["stake"] = _money_to_usd(d.get("stake"))
        if d.get("winnings"):
            d["winnings"] = _money_to_usd(d.get("winnings"))
    # Cashed-out slips are trophies too — SAME rule: systems + quote ≥ bar + on/after 1 Aug.
    cashed = await db.tips.find(
        {"status": "cashed_out"}, {"_id": 0}
    ).sort("settled_at", -1).limit(24).to_list(24)
    for tp in cashed:
        if not tp.get("is_parlay"):
            continue  # no single picks in the Hall of Fame
        if _to_float(tp.get("odds")) < _hof_min_odds(tp.get("username")):
            continue
        if not _hof_after_start(tp.get("settled_at") or tp.get("created_at")):
            continue
        docs.append({
            "id": tp["id"], "type": "cashed", "username": tp.get("username", "anon"),
            "total_odds": _to_float(tp.get("odds")),
            "winnings": _money_to_usd(tp.get("winnings") or tp.get("potential_return") or ""),
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
    for d in docs:  # always show $ (owner rule)
        if d.get("stake"):
            d["stake"] = _money_to_usd(d.get("stake"))
        if d.get("winnings"):
            d["winnings"] = _money_to_usd(d.get("winnings"))
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
    members = await db.users.count_documents(REAL_MEMBER_QUERY)
    subs = await db.subscribers.count_documents({})
    tips = await db.tips.count_documents({})
    return {"members": members + _member_boost(), "goal": 1000, "subscribers": subs + _sub_boost(), "total_tips": tips}


@api_router.get("/notifications/stats")
async def notif_stats():
    count = await db.subscribers.count_documents({})
    total = await db.tips.count_documents({})
    return {"subscriber_count": count + _sub_boost(), "total_tips": total}


@api_router.post("/track/visit")
async def track_visit(inp: VisitInput, request: Request):
    """Anonymous, cookieless visit ping (visitor_id is a random localStorage id).
    Deduped per visitor per day so we can report both hits and unique visitors.
    Admin visits are flagged (and never counted) — the owner opens the site hourly
    and must not inflate the analytics."""
    vid = (inp.visitor_id or "").strip()[:64]
    user = None
    try:
        user = await get_current_user(request)
    except Exception:
        user = None
    uid = str(user.get("id")) if user else ""
    is_admin = bool(user and user.get("role") == "admin")
    # Identity: logged-in users are deduped per ACCOUNT across every device (so 4
    # logins from one person = 1 visitor); anonymous visitors are deduped per device.
    identity = f"u:{uid}" if uid else (f"d:{vid}" if vid else "")
    if not identity:
        return {"ok": True}
    now = datetime.now(timezone.utc)
    day = now.strftime("%Y-%m-%d")
    if is_admin:
        # retroactively flag every past visit from this account AND this device so the
        # owner's own opens (logged in or not) drop out of the historical counts too.
        await db.visits.update_many(
            {"$or": [{"identity": identity}, {"visitor_id": vid}]} if vid else {"identity": identity},
            {"$set": {"is_admin": True}},
        )
    await db.visits.update_one(
        {"identity": identity, "day": day},
        {"$inc": {"hits": 1},
         "$set": {"last_ts": now.isoformat(), "path": (inp.path or "")[:120],
                  "is_admin": is_admin, "visitor_id": vid, "user_id": uid},
         "$setOnInsert": {"first_ts": now.isoformat()}},
        upsert=True,
    )
    return {"ok": True}


@api_router.get("/admin/visits")
async def admin_visits(admin: dict = Depends(require_admin)):
    """Private analytics — admin only. Never exposed publicly. Admin/owner visits
    are excluded (is_admin flag)."""
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")
    days = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
    # A visit's identity = the account (u:<id>) when logged in, else the device
    # (d:<visitor_id>). Old docs predate the `identity` field, so fall back to the
    # device id. Admin/owner visits (is_admin) are always excluded.
    ident_expr = {"$ifNull": ["$identity", {"$concat": ["d:", {"$ifNull": ["$visitor_id", ""]}]}]}
    not_admin = {"is_admin": {"$ne": True}}
    daily_map = {}
    _is_mem = {"$eq": [{"$substrCP": ["$_id.ident", 0, 2]}, "u:"]}
    async for row in db.visits.aggregate([
        {"$match": {"day": {"$in": days}, **not_admin}},
        {"$group": {"_id": {"day": "$day", "ident": ident_expr}, "hits": {"$sum": "$hits"}}},
        {"$group": {"_id": "$_id.day", "unique": {"$sum": 1}, "hits": {"$sum": "$hits"},
                    "members": {"$sum": {"$cond": [_is_mem, 1, 0]}},
                    "anon": {"$sum": {"$cond": [_is_mem, 0, 1]}}}},
    ]):
        daily_map[row["_id"]] = {"unique": row["unique"], "hits": row["hits"],
                                 "members": row["members"], "anon": row["anon"]}
    daily = [{"day": d, "unique": daily_map.get(d, {}).get("unique", 0),
              "hits": daily_map.get(d, {}).get("hits", 0),
              "members": daily_map.get(d, {}).get("members", 0),
              "anon": daily_map.get(d, {}).get("anon", 0)} for d in days]
    total_row = {"total_unique": 0, "total_hits": 0}
    async for row in db.visits.aggregate([
        {"$match": not_admin},
        {"$group": {"_id": ident_expr, "hits": {"$sum": "$hits"}}},
        {"$group": {"_id": None, "total_unique": {"$sum": 1}, "total_hits": {"$sum": "$hits"}}},
    ]):
        total_row = row
    total_unique = total_row["total_unique"]
    total_hits = total_row["total_hits"]
    today_row = next((x for x in daily if x["day"] == today), {"unique": 0, "hits": 0})
    week = daily[-7:]
    members = await db.users.count_documents(REAL_MEMBER_QUERY)
    subs = await db.subscribers.count_documents({})
    # Split unique visitors into logged-in members (identity "u:") vs anonymous ("d:").
    is_member = {"$eq": [{"$substrCP": ["$_id", 0, 2]}, "u:"]}
    async def _split(match):
        res = {"members": 0, "anon": 0}
        async for row in db.visits.aggregate([
            {"$match": {**match, **not_admin}},
            {"$group": {"_id": ident_expr}},
            {"$group": {"_id": None,
                        "members": {"$sum": {"$cond": [is_member, 1, 0]}},
                        "anon": {"$sum": {"$cond": [is_member, 0, 1]}}}},
        ]):
            res = {"members": row["members"], "anon": row["anon"]}
        return res
    today_split = await _split({"day": today})
    total_split = await _split({})
    return {
        "total_unique": total_unique, "total_hits": total_hits,
        "today_unique": today_row["unique"], "today_hits": today_row["hits"],
        "week_unique": sum(x["unique"] for x in week), "week_hits": sum(x["hits"] for x in week),
        "daily": daily, "members": members, "subscribers": subs,
        "today_members": today_split["members"], "today_anon": today_split["anon"],
        "total_members": total_split["members"], "total_anon": total_split["anon"],
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
    fields = {"endpoint": sub.endpoint, "keys": sub.keys,
              "user_id": (user or {}).get("id"), "updated_at": now}
    if sub.areas is not None:
        fields["areas"] = sub.areas
    if sub.min_stars is not None:
        fields["min_stars"] = sub.min_stars
    await db.push_subscriptions.update_one(
        {"endpoint": sub.endpoint},
        {"$set": fields, "$setOnInsert": {"created_at": now}},
        upsert=True)
    return {"ok": True, "count": await db.push_subscriptions.count_documents({})}


@api_router.post("/push/preferences")
async def push_preferences(prefs: PushPrefsIn):
    """Store per-device notification-area preferences (e.g. AI tips on/off) + the star
    threshold so the server-side Web Push respects them, not just the in-app popups."""
    upd = {"areas": prefs.areas}
    if prefs.min_stars is not None:
        upd["min_stars"] = prefs.min_stars
    await db.push_subscriptions.update_one(
        {"endpoint": prefs.endpoint}, {"$set": upd})
    return {"ok": True}


@api_router.post("/push/unsubscribe")
async def push_unsubscribe(sub: PushSubIn):
    await db.push_subscriptions.delete_one({"endpoint": sub.endpoint})
    return {"ok": True}


@api_router.post("/push/test")
async def push_test(sub: PushSubIn):
    """Send a single test Web Push to the caller's own subscription so a user can
    verify that notifications actually arrive on their device."""
    if not VAPID_PRIVATE_KEY:
        return {"ok": False, "reason": "push not configured"}
    s = await db.push_subscriptions.find_one({"endpoint": sub.endpoint}, {"_id": 0})
    if not s:
        return {"ok": False, "reason": "not-subscribed"}
    payload = {"title": "TipJar 🔔", "body": "Test-Benachrichtigung — Push funktioniert!",
               "url": "/", "area": "test"}
    try:
        await asyncio.to_thread(_send_web_push, s, payload)
        return {"ok": True}
    except WebPushException as exc:
        code = getattr(getattr(exc, "response", None), "status_code", None)
        if code in (404, 410):
            await db.push_subscriptions.delete_one({"endpoint": sub.endpoint})
            return {"ok": False, "reason": "expired"}
        return {"ok": False, "reason": f"push-error-{code}"}
    except Exception as e:
        return {"ok": False, "reason": str(e)[:100]}

















@api_router.get("/users/search")
async def search_users(q: str = "", limit: int = 15):
    """Search members by username (partial, case-insensitive). Also matches the
    Latin transliteration so a Greek/Cyrillic username is findable by Latin input."""
    q = (q or "").strip()
    if len(q) < 2:
        return {"results": []}
    rx = re.escape(q)
    docs = await db.users.find(
        {"username": {"$regex": rx, "$options": "i"}}, {"_id": 0}
    ).limit(200).to_list(200)
    # transliteration fallback: match normalized Latin form of stored usernames
    if len(docs) < limit:
        qn = _norm(q)
        seen = {d["username"] for d in docs}
        extra = await db.users.find({}, {"_id": 0, "username": 1, "id": 1, "created_at": 1,
                                         "received_credits": 1, "streak": 1, "apex_flame": 1}).to_list(5000)
        for d in extra:
            un = d.get("username") or ""
            if un in seen:
                continue
            forms = [_norm(x) for x in _latin_variants(un)]
            if any(qn and qn in f for f in forms):
                docs.append(d)
                seen.add(un)
    results = []
    for u in docs[:limit]:
        results.append({
            "username": u.get("username"),
            "apex_flame": u.get("apex_flame", False),
            "received_credits": u.get("received_credits", 0),
            "streak": u.get("streak", 0),
            "tips_count": await db.tips.count_documents({"user_id": u.get("id")}),
        })

    # Also search active picks by team/league (with transliteration) so a user can find
    # a game like "Makara" even though it's not a member name.
    games, seen_g = [], set()
    qforms = {_norm(x) for x in _latin_variants(q)}
    active = await db.tips.find(
        {"status": {"$in": ["pending", "live"]}},
        {"_id": 0, "id": 1, "home_team": 1, "away_team": 1, "league": 1,
         "market": 1, "status": 1, "source": 1, "legs": 1, "username": 1}).to_list(3000)
    for tp in active:
        hay = " ".join(str(tp.get(k) or "") for k in ("home_team", "away_team", "league"))
        legs = tp.get("legs") or []
        hay += " " + " ".join(str(l.get("match") or "") for l in legs)
        hay_forms = {_norm(x) for x in _latin_variants(hay)}
        if any(qf and any(qf in hf for hf in hay_forms) for qf in qforms):
            if tp["id"] in seen_g:
                continue
            seen_g.add(tp["id"])
            h, a = _tip_match_teams(tp)
            games.append({
                "id": tp["id"],
                "home_team": h or tp.get("home_team") or "",
                "away_team": a or tp.get("away_team") or "",
                "league": tp.get("league") or "",
                "status": tp.get("status"),
                "source": tp.get("source"),
                "username": tp.get("username"),
            })
        if len(games) >= limit:
            break
    return {"results": results, "games": games}


# ------------------------------------------------------------------ files
@api_router.get("/users/public/{username}")
async def public_profile(username: str):
    u = await db.users.find_one({"username": username})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    tips_count = await db.tips.count_documents({"user_id": u["id"]})
    # "Gewinne" = the member's own tips that landed as won/cashed-out + any win-claim trophies
    won_tips = await db.tips.count_documents(
        {"user_id": u["id"], "status": {"$in": ["won", "cashed_out"]}})
    win_claims_n = await db.win_claims.count_documents({"user_id": u["id"]})
    wins_count = won_tips + win_claims_n
    return {
        "username": u.get("username"),
        "created_at": u.get("created_at"),
        "received_credits": u.get("received_credits", 0),
        "streak": u.get("streak", 0),
        "apex_flame": u.get("apex_flame", False),
        "role": u.get("role", "user"),
        "expert_trial": u.get("expert_trial", False),
        "tips_count": tips_count,
        "wins_count": wins_count,
    }


@api_router.get("/experts")
async def list_experts():
    """Public list of Experts for the site-wide banner."""
    experts = await db.users.find(
        {"role": "expert", "is_master": {"$ne": True}, "silent": {"$ne": True}},
        {"_id": 0, "id": 1, "username": 1, "apex_flame": 1}).to_list(50)
    out = []
    for e in experts:
        tips_count = await db.tips.count_documents({"user_id": e["id"]})
        out.append({"username": e.get("username"), "apex_flame": e.get("apex_flame", False),
                    "tips_count": tips_count})
    out.sort(key=lambda x: x["tips_count"], reverse=True)
    return {"experts": out}


@api_router.get("/inbox")
async def get_inbox(user: dict = Depends(get_current_user)):
    msgs = await db.inbox_messages.find(
        {"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    unread = sum(1 for m in msgs if not m.get("read"))
    return {"messages": msgs, "unread": unread}


@api_router.post("/inbox/{msg_id}/read")
async def mark_inbox_read(msg_id: str, user: dict = Depends(get_current_user)):
    await db.inbox_messages.update_one(
        {"id": msg_id, "user_id": user["id"]}, {"$set": {"read": True}})
    return {"ok": True}


@api_router.post("/inbox/read-all")
async def mark_inbox_read_all(user: dict = Depends(get_current_user)):
    await db.inbox_messages.update_many(
        {"user_id": user["id"], "read": {"$ne": True}}, {"$set": {"read": True}})
    return {"ok": True}


@api_router.post("/inbox/expert-accept")
async def inbox_expert_accept(user: dict = Depends(get_current_user)):
    """User accepts the Expert invitation -> becomes Expert immediately (trial)."""
    now = datetime.now(timezone.utc).isoformat()
    if user.get("role") == "user":
        await db.users.update_one({"id": user["id"]},
            {"$set": {"role": "expert", "expert_since": now, "expert_trial": True}})
    await db.inbox_messages.update_many(
        {"user_id": user["id"], "cta": "expert_invite"},
        {"$set": {"read": True, "handled": True, "cta": None}})
    await db.inbox_messages.insert_one({
        "id": str(uuid.uuid4()), "user_id": user["id"], "type": "expert_welcome",
        "title": "Du bist jetzt Experte! 🎯",
        "body": ("Herzlichen Glückwunsch! Deine Tipps werden ab sofort als Experten-Tipps "
                 "hervorgehoben. Die Probezeit läuft — zeig der Community, was du drauf hast! 🔥"),
        "cta": None, "read": False, "handled": False, "created_at": now,
    })
    fresh = await db.users.find_one({"id": user["id"]})
    return {"ok": True, "user": public_user(fresh)}


@api_router.post("/inbox/expert-decline")
async def inbox_expert_decline(user: dict = Depends(get_current_user)):
    await db.inbox_messages.update_many(
        {"user_id": user["id"], "cta": "expert_invite"},
        {"$set": {"read": True, "handled": True, "cta": None}})
    return {"ok": True}



# Bump this whenever _render_slip_image output changes, so cached share images regenerate.
SHARE_RENDER_VER = 5


@api_router.post("/tips/{tip_id}/share-image")
async def tip_share_image(tip_id: str, lang: str = "de"):
    """Generate a TipJar-branded shareable slip image for a member pick, tagged with
    the channel it comes from (COMMUNITY PICK for pending, LIVE PICK for live). The image
    text follows the viewer's selected app language (owner 2026-06)."""
    lang = (lang or "de").split("-")[0].lower()
    if lang not in _TICKET_LABELS:
        lang = "de"
    tip = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    if tip.get("source") in ("hq-auto", "smart"):
        raise HTTPException(status_code=400, detail="Only member tips can be shared")
    ctype = "live_pending" if tip.get("status") == "live" else "pending"
    # Serve the cached image if we already built it for THIS language — frozen posted member
    # picks are immutable, so re-rendering (up to ~20s for a 15-leg slip) is pure waste. BUT
    # bump SHARE_RENDER_VER whenever the renderer changes so old cached images regenerate.
    cached = tip.get("share_images") or {}
    if (tip.get("status") != "live" and tip.get("share_image_ver") == SHARE_RENDER_VER
            and cached.get(lang)):
        existing = await db.files.find_one(
            {"storage_path": cached[lang], "is_deleted": False}, {"_id": 1})
        if existing:
            return {"path": cached[lang]}
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
    _disguise_stakes(tip)  # $ + expert 12x / TipJarLogic x2 must match the card
    # offload the CPU-heavy PIL render + the storage upload so we never block the event loop
    img = await asyncio.to_thread(
        _render_slip_image, rlegs, _to_float(tip.get("odds")), tip.get("stake", ""),
        tip.get("potential_return", ""), tip.get("username", "TipJar"), ctype, live_info,
        lang, tip.get("bet_type", ""), tip.get("system_from", 0), tip.get("system_total", 0))
    try:
        result = await asyncio.to_thread(
            put_object, f"{APP_NAME}/shares/{tip_id}.{lang}.webp", img, "image/webp")
        path = result["path"]
        await db.files.insert_one({
            "id": str(uuid.uuid4()), "storage_path": path,
            "original_filename": "tipjar-share.webp", "content_type": "image/webp",
            "owner": tip.get("user_id"), "is_deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        set_fields = {f"share_images.{lang}": path, "share_image_ver": SHARE_RENDER_VER,
                      "share_image_path": path}
        if tip.get("share_image_ver") != SHARE_RENDER_VER:
            # renderer changed → drop stale per-language cache so every language re-renders
            await db.tips.update_one({"id": tip_id}, {"$unset": {"share_images": ""}})
        await db.tips.update_one({"id": tip_id}, {"$set": set_fields})
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


_GREEK_RE = re.compile(r"[\u0370-\u03FF]")
_NON_LATIN_RE = re.compile(r"[^\u0000-\u024F]")
_GR_MONO = {
    "α": "a", "β": "v", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "i",
    "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "x",
    "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "y",
    "φ": "f", "χ": "ch", "ψ": "ps", "ω": "o",
}


def _translit_greek(s: str, hard: bool) -> str:
    """Modern-Greek → Latin. Digraphs μπ/ντ/ου are ambiguous: the 'hard' variant
    maps μπ→b, ντ→d, ου→u (→ 'Μπλούμεναου'→'blumenau'); the 'soft' variant keeps
    μπ→mp, ντ→nt, ου→ou (→ 'Ολυμπιακός'→'olympiakos'). We try both when resolving."""
    s = unicodedata.normalize("NFD", (s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    for a, b in [("μπ", "b" if hard else "mp"), ("ντ", "d" if hard else "nt"),
                 ("γκ", "g"), ("γγ", "ng"), ("τσ", "ts"), ("τζ", "tz"),
                 ("ου", "u" if hard else "ou"), ("αυ", "av"), ("ευ", "ev")]:
        s = s.replace(a, b)
    return "".join(_GR_MONO.get(c, c) for c in s)


def _latin_variants(name: str) -> list:
    """Latin transliteration candidates for a possibly non-Latin team name (Greek
    gets both digraph variants; Cyrillic/other via unidecode). Original included."""
    name = (name or "").strip()
    out = [name]
    if _GREEK_RE.search(name):
        out.append(_translit_greek(name, False))
        out.append(_translit_greek(name, True))
    elif _NON_LATIN_RE.search(name):
        try:
            from unidecode import unidecode
            out.append(unidecode(name))
        except Exception:
            pass
    seen, res = set(), []
    for x in out:
        if x and x not in seen:
            seen.add(x)
            res.append(x)
    return res


def _match_norm(na: str, nb: str) -> bool:
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


def _teams_match(a: str, b: str) -> bool:
    fa = {_norm(x) for x in _latin_variants(a)}
    fb = {_norm(x) for x in _latin_variants(b)}
    for na in fa:
        for nb in fb:
            if _match_norm(na, nb):
                return True
    return False


# API-Football low-level client + quota flag now live in core.py (imported at top).


# National-team names in the app's languages → API-Football's English name. Smart Picks
# (WC/EC) store localized names like 'Frankreich'/'Spanien'; without this map the
# settlement engine can't resolve the team → the slip never settles.
COUNTRY_NAME_EN = {
    "frankreich": "France", "francia": "France", "france": "France",
    "spanien": "Spain", "espana": "Spain", "espagne": "Spain", "spagna": "Spain",
    "deutschland": "Germany", "allemagne": "Germany", "alemania": "Germany", "germania": "Germany",
    "italien": "Italy", "italie": "Italy", "italia": "Italy",
    "england": "England", "inghilterra": "England", "inglaterra": "England", "angleterre": "England",
    "niederlande": "Netherlands", "holland": "Netherlands", "hollande": "Netherlands",
    "paesi bassi": "Netherlands", "paises bajos": "Netherlands",
    "belgien": "Belgium", "belgique": "Belgium", "belgica": "Belgium", "belgio": "Belgium",
    "portugal": "Portugal", "portogallo": "Portugal",
    "kroatien": "Croatia", "croatie": "Croatia", "croacia": "Croatia", "croazia": "Croatia",
    "schweiz": "Switzerland", "suisse": "Switzerland", "suiza": "Switzerland", "svizzera": "Switzerland",
    "osterreich": "Austria", "autriche": "Austria", "austria": "Austria",
    "danemark": "Denmark", "danemark": "Denmark", "dinamarca": "Denmark", "danimarca": "Denmark", "dane": "Denmark",
    "polen": "Poland", "pologne": "Poland", "polonia": "Poland",
    "schweden": "Sweden", "suede": "Sweden", "suecia": "Sweden", "svezia": "Sweden",
    "norwegen": "Norway", "norvege": "Norway", "noruega": "Norway", "norvegia": "Norway",
    "turkei": "Turkey", "turquie": "Turkey", "turquia": "Turkey", "turchia": "Turkey", "turkiye": "Turkey",
    "griechenland": "Greece", "grece": "Greece", "grecia": "Greece",
    "brasilien": "Brazil", "bresil": "Brazil", "brasil": "Brazil", "brasile": "Brazil",
    "argentinien": "Argentina", "argentine": "Argentina", "argentina": "Argentina",
    "marokko": "Morocco", "maroc": "Morocco", "marruecos": "Morocco", "marocco": "Morocco",
    "kolumbien": "Colombia", "colombie": "Colombia", "colombia": "Colombia",
    "vereinigte staaten": "USA", "usa": "USA", "etats-unis": "USA", "estados unidos": "USA",
    "mexiko": "Mexico", "mexique": "Mexico", "mexico": "Mexico", "messico": "Mexico",
    "japan": "Japan", "japon": "Japan", "giappone": "Japan",
    "sudkorea": "South Korea", "coree du sud": "South Korea", "corea del sur": "South Korea",
    "kroatie": "Croatia", "serbien": "Serbia", "serbie": "Serbia", "serbia": "Serbia",
    "uruguay": "Uruguay", "senegal": "Senegal", "ghana": "Ghana", "nigeria": "Nigeria",
}


async def _canonical_league_name(name: str):
    """Greek league/country labels ('Ευρώπη - Φιλικά', 'Φινλανδία') → their common English
    name ('Friendlies', 'Finland'). Cached in label_alias. None for already-Latin/unknown."""
    name = (name or "").strip()
    if not name or not _NON_LATIN_RE.search(name):
        return None
    key = _norm(name)
    cached = await db.label_alias.find_one({"key": key})
    if cached:
        return cached.get("alias") or None
    if not EMERGENT_LLM_KEY:
        return None
    alias = None
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"lbl-{uuid.uuid4()}",
            system_message=("You convert football league/competition or country names into their "
                            "common English name as used by bookmakers. Reply with ONLY the name."),
        ).with_model(AI_MODEL_PROVIDER, AI_TEXT_MODEL)
        resp = await chat.send_message(UserMessage(text=(
            f"Label (may be Greek): '{name}'.\n"
            "Examples: 'Ευρώπη - Φιλικά' -> Friendlies; 'Φινλανδία' -> Finland; "
            "'Φιλικά' -> Friendlies; 'Αγγλία - Πρέμιερ Λιγκ' -> Premier League.\n"
            "Give the English name only.")))
        alias = (resp if isinstance(resp, str) else str(resp)).strip().strip('".\n ')
        if not alias or len(alias) > 60 or _NON_LATIN_RE.search(alias):
            alias = None
    except Exception as e:
        logger.warning(f"league alias LLM failed for {name}: {e}")
        alias = None
    if alias:
        await db.label_alias.update_one(
            {"key": key}, {"$set": {"key": key, "alias": alias, "src": name}}, upsert=True)
    return alias


async def _canonicalize_display(t: dict) -> dict:
    """Rewrite a tip's Greek team/league/country labels into canonical English for DISPLAY
    (and so live-score / settlement name-matching works), independent of any fixture lookup.
    Returns the $set update dict (empty when nothing changed)."""
    upd = {}
    legs = t.get("legs") or []
    legs_changed = False
    for lg in legs:
        lh, la = _leg_teams(lg)
        if lh and la:
            lh_c = await _canonical_team_name(lh) or lh
            la_c = await _canonical_team_name(la) or la
            newm = f"{lh_c} \u2013 {la_c}"
            if newm != (lg.get("match") or ""):
                lg["match"] = newm
                legs_changed = True
        # Canonicalize each selection's market text (Greek → standard German label with
        # canonical team names) so the leg boxes read cleanly and settle reliably.
        sels = lg.get("selections") or []
        new_sels = []
        sels_changed = False
        for s in sels:
            if isinstance(s, str) and _NON_LATIN_RE.search(s):
                cs = await _canonical_selection(s)
                if cs and cs != s:
                    new_sels.append(cs)
                    sels_changed = True
                    continue
            new_sels.append(s)
        if sels_changed:
            lg["selections"] = new_sels
            legs_changed = True
        lgl = lg.get("league") or ""
        if _NON_LATIN_RE.search(lgl):
            lc = await _canonical_league_name(lgl)
            if lc and lc != lgl:
                lg["league"] = lc
                legs_changed = True
    if legs_changed:
        upd["legs"] = legs
    for fld in ("league", "country"):
        val = t.get(fld) or ""
        if _NON_LATIN_RE.search(val):
            cv = await _canonical_league_name(val)
            if cv and cv != val:
                upd[fld] = cv
    for fld, raw in (("home_team_latin", t.get("home_team")), ("away_team_latin", t.get("away_team"))):
        if not t.get(fld) and raw and _NON_LATIN_RE.search(raw):
            cv = await _canonical_team_name(raw)
            if cv:
                upd[fld] = cv
    # Top-level market summary (shown on the card header) → clean German label.
    mk = t.get("market") or ""
    if _NON_LATIN_RE.search(mk):
        cm = await _canonical_selection(mk)
        if cm and cm != mk:
            upd["market"] = cm
    return upd


async def _canonical_team_name(name: str):
    """Greek (and other non-Latin) team names from GR/foreign tipsters → the club's
    canonical English/international name as used by API-Football & bookmakers
    (e.g. 'ΛΟΥΚΕΡΝΗ' → 'Luzern', 'Τουν' → 'Thun', 'Χιρόνα' → 'Girona'). Cached in
    team_alias. Returns None for already-Latin names or when unavailable."""
    name = (name or "").strip()
    if not name or not _NON_LATIN_RE.search(name):
        return None
    key = _norm(name)
    cached = await db.team_alias.find_one({"key": key})
    if cached:
        return cached.get("alias") or None
    if not EMERGENT_LLM_KEY:
        return None
    alias = None
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"team-{uuid.uuid4()}",
            system_message=("You convert football (soccer) club or national-team names into "
                            "their common English/international name exactly as API-Football and "
                            "bookmakers spell it. Reply with ONLY the name — no quotes, no notes."),
        ).with_model(AI_MODEL_PROVIDER, AI_TEXT_MODEL)
        resp = await chat.send_message(UserMessage(text=(
            f"Team name (may be Greek): '{name}'.\n"
            "Examples: 'Λουκέρνη' -> Luzern; 'Τουν' -> Thun; 'Χιρόνα' -> Girona; "
            "'Αλαβές' -> Alaves; 'Άλκμααρ' -> AZ Alkmaar; 'Ολυμπιακός' -> Olympiacos; "
            "'Ελντένσε' -> Eldense; 'Αλ Ετιφάκ' -> Al-Ettifaq.\n"
            "Give the canonical English name only.")))
        alias = (resp if isinstance(resp, str) else str(resp)).strip().strip('".\n ')
        if not alias or len(alias) > 60 or _NON_LATIN_RE.search(alias):
            alias = None
    except Exception as e:
        logger.warning(f"team alias LLM failed for {name}: {e}")
        alias = None
    if alias:
        await db.team_alias.update_one(
            {"key": key}, {"$set": {"key": key, "alias": alias, "src": name}}, upsert=True)
    return alias

async def _canonical_selection(sel: str):
    """A Greek (or other non-Latin) betting SELECTION from a foreign tipster slip →
    a clean, standard GERMAN market label that our settlement engine understands, with
    canonical team names. E.g. 'Κρουζ Αζουλ - Τελικό Αποτέλεσμα' → 'Cruz Azul Sieg';
    'Ναι (GG) - Να σκοράρουν και οι 2 ομάδες' → 'Beide Teams treffen';
    'Άνω 1.5 - 1ο Ημίχρονο' → '1. Halbzeit Über 1.5 Tore'. Cached in sel_alias.
    Returns None for already-Latin selections or when unavailable."""
    sel = (sel or "").strip()
    if not sel or not _NON_LATIN_RE.search(sel):
        return None
    key = _norm(sel)
    cached = await db.sel_alias.find_one({"key": key})
    if cached:
        return cached.get("alias") or None
    if not EMERGENT_LLM_KEY:
        return None
    alias = None
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"sel-{uuid.uuid4()}",
            system_message=(
                "You convert a football betting SELECTION (often written in Greek) into a "
                "clean, STANDARD GERMAN market label. Use canonical English/international team "
                "names (as bookmakers spell them). Use EXACTLY these German market terms:\n"
                "- Team to win / final result for one team → '<Team> Sieg'\n"
                "- Double chance → '<Team> Doppelte Chance 1X' or 'X2'\n"
                "- Both teams to score (Να σκοράρουν και οι 2 ομάδες / GG / Nai) → 'Beide Teams treffen'\n"
                "- No BTTS → 'Beide Teams treffen Nein'\n"
                "- Over/Under total goals → 'Über X.5 Tore' / 'Unter X.5 Tore'\n"
                "- First-half markets (1ο Ημίχρονο) → prefix '1. Halbzeit '\n"
                "- Team total goals → '<Team> Über X.5 Tore'\n"
                "- Draw (Ισοπαλία / Χ) → 'Unentschieden'\n"
                "Reply with ONLY the German label — no odds, no quotes, no notes."),
        ).with_model(AI_MODEL_PROVIDER, AI_TEXT_MODEL)
        resp = await chat.send_message(UserMessage(text=(
            f"Selection: '{sel}'.\n"
            "Examples: 'Κρουζ Αζουλ - Τελικό Αποτέλεσμα' -> Cruz Azul Sieg; "
            "'Ντεπορτές Τολίμα - Τελικό Αποτέλεσμα' -> Deportes Tolima Sieg; "
            "'Ναι (GG) - Να σκοράρουν και οι 2 ομάδες' -> Beide Teams treffen; "
            "'Άνω 2.5 - Γκολ' -> Über 2.5 Tore; "
            "'Άνω 1.5 - 1ο Ημίχρονο - Γκολ' -> 1. Halbzeit Über 1.5 Tore.\n"
            "Give the German market label only.")))
        alias = (resp if isinstance(resp, str) else str(resp)).strip().strip('".\n ')
        if not alias or len(alias) > 80 or _NON_LATIN_RE.search(alias):
            alias = None
    except Exception as e:
        logger.warning(f"selection alias LLM failed for {sel!r}: {e}")
        alias = None
    if alias:
        await db.sel_alias.update_one(
            {"key": key}, {"$set": {"key": key, "alias": alias, "src": sel}}, upsert=True)
    return alias




async def resolve_team_id(name: str):
    if not name or len(name.strip()) < 3:
        return None
    key = _norm(name)
    cached = await db.team_cache.find_one({"key": key})
    if cached and cached.get("team_id") is not None:
        return cached.get("team_id")
    # localized national-team name → API-Football English name (e.g. Frankreich → France)
    base_name = COUNTRY_NAME_EN.get(key, name.strip())
    candidates = _latin_variants(base_name) or [base_name]
    # Greek/foreign club names → canonical English (LLM, cached) so the search actually hits.
    alias = await _canonical_team_name(name)
    if alias:
        candidates = [alias] + [c for c in candidates if c != alias]
    # Try each candidate until one resolves.
    team_id = None
    for search_name in candidates:
        resp = _apifootball("/teams", {"search": search_name})
        # fallbacks for name mismatches (hyphens, city suffixes)
        if not resp:
            simplified = re.sub(r"[-_]", " ", search_name).strip()
            if simplified.lower() != search_name.lower():
                resp = _apifootball("/teams", {"search": simplified})
        if not resp:
            first = re.sub(r"[^A-Za-z0-9 ]", " ", search_name).split()
            if first and len(first[0]) >= 4:
                resp = _apifootball("/teams", {"search": first[0]})
        if resp:
            for item in resp:
                if _teams_match(item.get("team", {}).get("name", ""), search_name):
                    team_id = item["team"]["id"]
                    break
            if team_id is None:
                team_id = resp[0].get("team", {}).get("id")
        if team_id is not None:
            break
    await db.team_cache.update_one({"key": key}, {"$set": {"key": key, "team_id": team_id}}, upsert=True)
    return team_id


async def _pick_stats_line(p) -> str:
    """Real hit-rates (form / BTTS / Over 2.5 / H2H) for a prediction, cited from
    API-Football last-N fixtures. '' when data/quota unavailable (never fabricated)."""
    try:
        home, away = p.get("home"), p.get("away")
        hid = await resolve_team_id(home)
        aid = await resolve_team_id(away)
        hf = await match_stats.team_form(hid)
        af = await match_stats.team_form(aid)
        h2h = await match_stats.h2h_stats(hid, aid)
        return match_stats.stats_summary_text(home, away, hf, af, h2h)
    except Exception as e:
        logger.warning(f"stats line failed for {p.get('home')} vs {p.get('away')}: {e}")
        return ""


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
            full = _norm(name)
            if full:
                # full-name key disambiguates players who share a last name
                # (e.g. two "Castillo") so a scorer isn't overwritten by a namesake.
                pmap[f"full:{full}"] = rec
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








GRADE_VOID = "void"   # sentinel: leg is a PUSH (stake refunded) — never True/False/None


















PARLAY_JUDGE_CAP = 40   # max LLM settlement calls per multi-match run (quota guard)









@api_router.post("/admin/settle-now")
async def settle_now(admin: dict = Depends(require_admin)):
    _reset_api_quota_flag()
    res = await settle_pending_tips()
    res["systems_snapshot"] = await snapshot_systems()
    res["combos"] = await settle_hq_combos()
    res["parlays"] = await settle_multimatch_parlays()
    res["expired"] = await expire_stale_pending()
    try:
        res["live"] = await live_autopost()
    except Exception as e:
        res["live"] = {"error": str(e)}
    # If the daily API-Football quota is exhausted no fixture can be resolved, so tell the
    # admin exactly why nothing settled instead of showing a misleading "0 settled".
    if _api_quota_exhausted():
        res["ok"] = False
        res["reason"] = ("API-Football Tageslimit erreicht – Abrechnung pausiert. "
                         "Sobald das Kontingent zurückgesetzt ist, werden alle fertigen "
                         "Spiele automatisch abgerechnet (kein Versuch geht verloren).")
    return res


@api_router.get("/admin/cleanup-log")
async def admin_cleanup_log(admin: dict = Depends(require_admin)):
    """Log of abgelaufene-Picks-Bereinigungen — entries exist ONLY for runs that actually
    cleaned something (no empty/zero rows). Shows counts + affected leagues so the owner can
    spot leagues that repeatedly can't settle (candidates to drop from the scraper)."""
    rows = await db.cleanup_log.find({}, {"_id": 0}).sort("at", -1).to_list(100)
    return {"count": len(rows), "entries": rows}



    """Auto-learning league blacklist: which leagues never settle (uncoverable by
    API-Football) and were auto-blocked, plus the raw hit/miss counters."""
    rows = await db.league_settle_health.find({}, {"_id": 0}).sort("misses", -1).to_list(500)
    return {"blocked": sorted(_BLOCKED_LEAGUES), "min_misses_to_block": _LEAGUE_BLOCK_MIN_MISSES,
            "leagues": rows}


@api_router.post("/admin/league-health/unblock")
async def admin_unblock_league(payload: dict, admin: dict = Depends(require_admin)):
    """Manually re-enable a league (e.g. once API-Football adds coverage). Resets counters."""
    code = (payload.get("code") or "").strip().lower()
    if not code:
        return {"ok": False, "reason": "code required"}
    await db.league_settle_health.update_one(
        {"code": code}, {"$set": {"blocked": False, "hits": 0, "misses": 0}}, upsert=True)
    _BLOCKED_LEAGUES.discard(code)
    return {"ok": True, "code": code}



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



EXPIRE_GRACE_HOURS = 30  # > 24h so a daily API-quota outage can't delete a still-settleable pick







@api_router.get("/")
async def root():
    return {"message": "TipJar API live"}


# NOTE: api_router is included at the VERY BOTTOM of this module (after ALL routes are
# defined) so late-defined endpoints (code-reading, learning, …) are registered too.
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
                         "prievidza", "inter bratislava",
                         "agama", "hardrock", "ekibastuz", "ontustik",
                         "astana ii", "triangle united",
                         # owner-flagged 2026-07-24 (obscure/untrustworthy fixtures)
                         "abaseya", "reyadi", "asiagoal", "buxtu", "pakhator",
                         "oshmu", "aldier", "qiziriq", "olimpik-mobiuz", "mobiuz",
                         "goulburn", "springvale", "ozgon", "ilbirs", "maldonado",
                         # owner 2026-06: Tasmanian regional leagues aren't offered by
                         # bookmakers → block the whole competition (Somerset–Burnie Utd,
                         # Tasmania Northern Championship, etc.).
                         "tasmania", "tasmanian", "burnie",
                         # owner 2026-07-26: Germany boycotts ALL Russian football —
                         # block every Russian league & top-flight club by keyword too
                         # (country/code block is the primary lever; these catch untagged data).
                         "russia", "russian", "zenit", "cska moscow", "spartak moscow",
                         "lokomotiv moscow", "dynamo moscow", "dinamo moscow", "krasnodar",
                         "fc rostov", "baltika", "akhmat", "rubin kazan", "krylia sovetov",
                         "orenburg", "fakel", "pari nn", "nizhny novgorod", "khimki",
                         "fc ural", "fc sochi", "akron togliatti", "fc dynamo makhachkala")

# Owner MATCH blacklist: block ONE specific fixture only (BOTH team keywords must match).
# Used when the teams themselves are legit clubs we must NOT ban globally (e.g. CSKA Moscow,
# Baltika are Russian top-flight sides — only this particular game is excluded).
MATCH_BLACKLIST = (
    ("cska moscow", "baltika"),
)


def _team_or_league_blocked(home: str, away: str, league: str = "") -> bool:
    h, a = (home or "").lower(), (away or "").lower()
    hay = f" {h} {a} {(league or '').lower()} "
    if any(kw in hay for kw in TEAM_LEAGUE_BLACKLIST):
        return True
    for x, y in MATCH_BLACKLIST:
        if (x in h and y in a) or (x in a and y in h):
            return True
    return False


# Owner-flagged football nations whose leagues are obscure / uncoverable — block ALL their
# competitions at once. Kyrgyzstan stays fully blocked. Uzbekistan is NOT here anymore:
# the owner confirmed the top flight (Uzbekistan Super League) is bettable & scores goals —
# only the 2nd tier ("Pro League A") + the specific flagged clubs stay blocked (below).
COUNTRY_BLACKLIST = ("kyrgyzstan", "russia", "russian")
# Germany boycotts ALL Russian football (owner 2026-07-26). Used to purge any Russian
# fixture that slipped into the feed before the scrapers were locked down.
RUSSIA_KEYWORDS = ("russia", "russian", "zenit", "cska moscow", "spartak moscow",
                   "lokomotiv moscow", "dynamo moscow", "dinamo moscow", "krasnodar",
                   "fc rostov", "baltika", "akhmat", "rubin kazan", "krylia sovetov",
                   "orenburg", "fakel", "pari nn", "nizhny novgorod", "khimki",
                   "fc ural", "fc sochi", "akron togliatti", "makhachkala")
COUNTRY_CODE_BLACKLIST = ("kg", "ru")


def _country_blocked(country: str = "", code: str = "") -> bool:
    c = (country or "").strip().lower()
    if c and any(b in c for b in COUNTRY_BLACKLIST):
        return True
    cc = (code or "").strip().lower()
    return len(cc) >= 2 and cc[:2] in COUNTRY_CODE_BLACKLIST


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
    "se1", "sv1", "fi1", "ua1", "pl1", "cz1", "cr1", "sr1", "hr1", "ro1",
    # Americas
    "br1", "br2", "ar1", "us1", "ml1", "mls", "mx1", "co1", "cl1", "ec1",
    "pe1", "ur1",
    # Asia
    "jp1", "kr1", "ko1", "cn1", "sa1", "qa1", "ae1",
}


# ── Auto-learning league blacklist ───────────────────────────────────────────
# Some whitelisted Forebet leagues (e.g. the current Chinese Super League) simply are NOT
# in API-Football, so their tips can never auto-settle. Instead of hand-maintaining the
# whitelist we LEARN it: every scraper tip that settles is a "hit" for its league; every
# finished scraper tip that had to be purged still-unsettled is a "miss". A league with
# several misses and ZERO hits is uncoverable → we stop posting new tips from it. A league
# that settles fine (e.g. 'ecl') is never blocked even if the odd fixture fails on naming.
_LEAGUE_BLOCK_MIN_MISSES = 6
_BLOCKED_LEAGUES: set = set()


async def _refresh_blocked_leagues():
    global _BLOCKED_LEAGUES
    try:
        docs = await db.league_settle_health.find({"blocked": True}, {"_id": 0, "code": 1}).to_list(500)
        _BLOCKED_LEAGUES = {d["code"] for d in docs if d.get("code")}
    except Exception as e:
        logger.error(f"refresh blocked leagues: {e}")


def _is_league_auto_blocked(code: str) -> bool:
    return bool(code) and code.strip().lower() in _BLOCKED_LEAGUES


async def _record_league_hit(code: str):
    code = (code or "").strip().lower()
    if not code:
        return
    await db.league_settle_health.update_one({"code": code}, {"$inc": {"hits": 1}}, upsert=True)


async def _record_league_miss(code: str):
    code = (code or "").strip().lower()
    if not code:
        return
    await db.league_settle_health.update_one({"code": code}, {"$inc": {"misses": 1}}, upsert=True)
    doc = await db.league_settle_health.find_one({"code": code})
    if doc and not doc.get("blocked") and doc.get("hits", 0) == 0 \
            and doc.get("misses", 0) >= _LEAGUE_BLOCK_MIN_MISSES:
        await db.league_settle_health.update_one(
            {"code": code},
            {"$set": {"blocked": True, "blocked_at": datetime.now(timezone.utc).isoformat()}})
        _BLOCKED_LEAGUES.add(code)
        logger.warning(f"Auto-blocked uncoverable league '{code}' "
                       f"({doc.get('misses')} misses, 0 settled)")



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
    # Uzbekistan 2nd tier (owner: keep the Super League, drop the Pro League A where the
    # flagged BuxTu / Pakhtakor II / Olimpik-Mobiuz / Qiziriq play).
    "pro league a",
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
        lc = (tip.get("league_code") or "").strip().lower()
        return lc in FOREBET_SLIP_CODES and not _is_league_auto_blocked(lc)
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


def _consensus_map(preds: list) -> dict:
    """Cross-source agreement per fixture: how many DISTINCT predictor sources (betarades,
    matchmoney, foxbet, kingbet, bethome, socialgamblers, forebet, predictz, statarea, …) back
    the same favourite / Over 2.5 / BTTS. Lets the Master PREFER games many sources agree on."""
    from collections import defaultdict
    by_fix = defaultdict(list)
    for p in preds:
        h, a = p.get("home"), p.get("away")
        if h and a:
            by_fix[_match_key(h, a)].append(p)
    out = {}
    for k, lst in by_fix.items():
        fav_src, over_src, btts_src, all_src = defaultdict(set), set(), set(), set()
        for p in lst:
            src = p.get("source") or "?"
            all_src.add(src)
            if p.get("fav") in ("home", "away", "draw"):
                fav_src[p["fav"]].add(src)
            if p.get("over25"):
                over_src.add(src)
            if p.get("btts"):
                btts_src.add(src)
        maj_fav, maj_n = None, 0
        for f, s in fav_src.items():
            if len(s) > maj_n:
                maj_fav, maj_n = f, len(s)
        out[k] = {"fav": maj_fav, "fav_n": maj_n,
                  "fav_src": {f: len(s) for f, s in fav_src.items()},
                  "over_n": len(over_src), "btts_n": len(btts_src), "n": len(all_src)}
    return out


def _consensus_for(cmap: dict, home: str, away: str, fav: str = None) -> dict:
    """Consensus info for one fixture. If `fav` is given, `agree` = distinct sources backing
    THAT favourite; otherwise it reflects the majority favourite across all sources."""
    info = cmap.get(_match_key(home, away))
    if not info:
        return {"n": 0, "agree": 0, "fav": None, "over_n": 0, "btts_n": 0}
    agree = info["fav_src"].get(fav, 0) if fav else info.get("fav_n", 0)
    return {"n": info.get("n", 0), "agree": agree, "fav": info.get("fav"),
            "over_n": info.get("over_n", 0), "btts_n": info.get("btts_n", 0)}


def _favourite_side_map(preds: list, min_prob: int = 60) -> dict:
    """Per fixture, the CLEAR favourite side ('home'/'away') when the model is confident
    (fav_prob >= min_prob). Lets the Master back the STRONG side and drop legs that back a
    clear underdog (owner learning 2026-07-30: never back a trailing away underdog like
    HB Torshavn 0:2 down, Hajduk 0:2 down — always the aggregate-leading / strong side)."""
    best = {}
    for p in preds:
        h, a = p.get("home"), p.get("away")
        fav, fp = p.get("fav"), p.get("fav_prob") or 0
        if not (h and a) or fav not in ("home", "away"):
            continue
        try:
            fp = int(float(fp))
        except (TypeError, ValueError):
            fp = 0
        if fp < min_prob:
            continue
        k = _match_key(h, a)
        if k not in best or fp > best[k][1]:
            best[k] = (fav, fp)
    return best


# team-specific markets whose success depends on ONE named side performing well
_TEAM_SIDE_MKT_RE = re.compile(
    r'(sieg|gewinnt|\bwin\b|handicap|\+\s*\d|\-\s*\d|trifft|über\s*0\.5|uber\s*0\.5|'
    r'over\s*0\.5|über\s*1\.5|uber\s*1\.5|team\s*total|asian)', re.I)


def _leg_backs_clear_underdog(market: str, home: str, away: str, fav_side: str) -> bool:
    """True when `market` is a TEAM-SPECIFIC bet on the CLEAR UNDERDOG side (win/handicap/
    team-scores). Neutral markets (match total Über X.5, both-teams-to-score, draw) are never
    flagged. fav_side is 'home' or 'away'."""
    m = market or ""
    if not fav_side or not _TEAM_SIDE_MKT_RE.search(m):
        return False
    ml = m.lower()
    underdog = away if fav_side == "home" else home
    favourite = home if fav_side == "home" else away
    under_core = _team_core(underdog)
    fav_core = _team_core(favourite)
    mcore = _norm(m).replace(" ", "")
    # explicit home/away keywords
    home_kw = any(k in ml for k in ("heimsieg", "heim sieg", "home win"))
    away_kw = any(k in ml for k in ("auswärtssieg", "auswartssieg", "gastsieg", "away win"))
    backs_under = (
        (fav_side == "home" and away_kw) or (fav_side == "away" and home_kw)
        or (under_core and under_core in mcore and not (fav_core and fav_core in mcore))
    )
    return bool(backs_under)




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
        {"source": {"$in": ["hq-auto", "smart"]}, "status": "pending"},
        {"id": 1, "match_time": 1, "league_code": 1, "source": 1}).to_list(1000)
    stale_docs = [d for d in docs
                  if (ko := _parse_kickoff(d.get("match_time"))) and ko < cutoff]
    stale = [d["id"] for d in stale_docs]
    if stale:
        await db.tips.delete_many({"id": {"$in": stale}})
        # A finished scraper tip that never settled before purge = the league couldn't be
        # resolved in API-Football → count a "miss" so uncoverable leagues get auto-blocked.
        for d in stale_docs:
            if d.get("source") == "hq-auto":
                await _record_league_miss(d.get("league_code"))
    # hq-system AI slips (multi-match parlays) for leagues API-Football doesn't cover can
    # NEVER auto-settle, so they'd otherwise pile up as "pending" forever. Remove them once
    # their LATEST leg kicked off > 48h ago (generous — plenty of time for FT to publish).
    sys_cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
    sys_docs = await db.tips.find(
        {"source": "hq-system", "status": {"$in": ["pending", "live"]}},
        {"id": 1, "match_time": 1, "legs": 1}).to_list(1000)
    sys_stale = []
    for d in sys_docs:
        kos = [k for k in (_parse_kickoff(l.get("kickoff")) for l in (d.get("legs") or [])) if k]
        latest = max(kos) if kos else _parse_kickoff(d.get("match_time"))
        if latest and latest < sys_cutoff:
            sys_stale.append(d["id"])
    if sys_stale:
        await db.tips.delete_many({"id": {"$in": sys_stale}})
        logger.info(f"Purged {len(sys_stale)} stale unsettleable hq-system slips (>48h past kickoff)")
    preds = await db.match_predictions.find({}, {"id": 1, "kickoff": 1}).to_list(1000)
    stale_p = [p["id"] for p in preds
               if (ko := _parse_kickoff(p.get("kickoff"))) and ko < cutoff]
    if stale_p:
        await db.match_predictions.delete_many({"id": {"$in": stale_p}})
    return len(stale) + len(sys_stale)


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
    if _team_or_league_blocked(p.get("home"), p.get("away"), p.get("league")):
        return False
    if _country_blocked(p.get("country"), p.get("league_code")):
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
    if _country_blocked(country, league_code) or _team_or_league_blocked(home, away, league):
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
    # Double-chance fair-odds estimate, calibrated 2026-07-24 to real bookmaker bet-builder
    # pricing (owner: "lern von mir" — e.g. an away/modest favourite's X2 is ~1.5-1.7, not 1.2).
    if fav_prob is None:
        return 1.33
    if fav_prob >= 68:
        return 1.18
    if fav_prob >= 60:
        return 1.25
    if fav_prob >= 52:
        return 1.35
    if fav_prob >= 45:
        return 1.50
    return 1.72


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


_GOAL_MKT_RE = re.compile(
    r'(tore\b|\btor\b|beide teams|btts|\bgg\b|both teams|goals?\b|halbzeit)', re.I)


def _correlated_combo_odds(legs) -> float:
    """Realistic Same-Game-Multi price. The naive product OVERSTATES a single-match builder
    that stacks correlated GOAL markets (Über 1.5 HZ, BTTS, Über 2.5 … all rise/fall
    together). We shrink ONLY the goal-cluster's profit portion the more goal-legs stack.
    Everything else (Handicap, 1X2/Sieg, Doppelte Chance, Ecken, Spieler-Props) keeps its
    FULL odds — those legitimately carry high prices (a Handicap-1X2 pays far more than a
    plain win) and must not be dampened."""
    goal_odds, other_odds = [], []
    for lg in legs:
        try:
            o = float(lg.get("odds"))
        except (TypeError, ValueError):
            o = 0.0
        if o <= 1:
            continue
        if _GOAL_MKT_RE.search(str(lg.get("market") or "")):
            goal_odds.append(o)
        else:
            other_odds.append(o)
    if not goal_odds and not other_odds:
        return 0.0
    goal_prod = 1.0
    for o in goal_odds:
        goal_prod *= o
    if len(goal_odds) >= 2:  # correlated goal cluster → dampen its profit portion only
        shrink = {2: 0.55, 3: 0.40, 4: 0.30}.get(len(goal_odds), 0.24)
        goal_prod = 1.0 + (goal_prod - 1.0) * shrink
    other_prod = 1.0
    for o in other_odds:
        other_prod *= o
    return round(goal_prod * other_prod, 2)


def _dedupe_builder_legs(combo_legs, home, away):
    """Owner rule (2026-07-24): drop any selection whose outcome is logically ENTAILED
    by the combination of the other legs (adds no odds/value), e.g. a favourite's
    'Über 2.5 Tore' when the slip already has '<Fav> -1.5 Handicap' + BTTS. Understands
    handicaps and totals. Returns the cleaned leg list (never empty)."""
    try:
        kept, dropped = dedupe_implied_legs(combo_legs, home, away)
        if dropped:
            logger.info(f"Bet-builder dedupe {home} vs {away}: dropped "
                        f"{[d.get('market') for d in dropped]}")
        return kept or combo_legs
    except Exception as e:
        logger.warning(f"dedupe failed for {home} vs {away}: {e}")
        return combo_legs



def _split_match_names(match: str):
    """Split a leg 'match' label ('Home – Away' / 'Home - Away') into (home, away)."""
    for sep in (" – ", " - ", " vs ", " v ", "–", " gegen "):
        if sep in (match or ""):
            parts = match.split(sep, 1)
            return parts[0].strip(), parts[1].strip()
    return (match or "").strip(), ""


def _dedupe_multigame_legs(legs) -> float:
    """Per-GAME redundancy strip for multi-match parlays whose legs carry
    `selections`/`sel_odds` (Master Special / Doppelpack / Safe Bets). Removes any
    selection that is logically ENTAILED by the other selections OF THE SAME GAME
    (e.g. 'Über 1.5 Tore' when that game already has 'Beide Teams treffen' or
    'Über 2.5 Tore'). Never touches selections across different games. Recomputes and
    returns the new combined odds product. Mutates each leg in place."""
    prod = 1.0
    for leg in legs:
        sels = leg.get("selections") or []
        odds = leg.get("sel_odds") or []
        if len(sels) <= 1:
            for o in odds:
                try:
                    prod *= float(str(o).replace(",", "."))
                except (ValueError, TypeError):
                    pass
            continue
        home, away = _split_match_names(leg.get("match") or "")
        rows = [{"market": s, "_odd": odds[i] if i < len(odds) else None}
                for i, s in enumerate(sels)]
        try:
            kept, dropped = dedupe_implied_legs(rows, home, away)
        except Exception:
            kept, dropped = rows, []
        if dropped:
            logger.info(f"Master dedupe {leg.get('match')}: dropped "
                        f"{[d.get('market') for d in dropped]}")
        leg["selections"] = [r["market"] for r in kept]
        leg["sel_odds"] = [r["_odd"] for r in kept if r.get("_odd") is not None]
        for o in leg["sel_odds"]:
            try:
                prod *= float(str(o).replace(",", "."))
            except (ValueError, TypeError):
                pass
    return round(prod, 2)


async def master_dedupe_open_slips() -> dict:
    """Clean ALL open Master multi-match slips (Special/Doppelpack/Safe): (1) drop any leg
    whose game / league is now blacklisted (e.g. Tasmania) — owner: "das Spiel wird vom
    Schein entfernt"; (2) strip per-game redundant selections (BTTS ⇒ Über 1.5). Rewrites
    the displayed total odds + leg count. Runs each master cycle so slips get fixed
    automatically (incl. on production after a deploy)."""
    fixed = 0
    slips = await db.tips.find(
        {"source": "hq-master", "is_parlay": True, "combo_legs": {"$exists": False},
         "status": {"$in": ["pending", "live"]}, "legs.0": {"$exists": True}},
        {"_id": 0, "id": 1, "legs": 1, "odds": 1, "market": 1}).to_list(200)
    for s in slips:
        legs = s.get("legs") or []
        before = [((l.get("match") or ""), (l.get("selections") or [])[:]) for l in legs]
        # 1) remove legs on a blacklisted game / league
        kept_legs = []
        for l in legs:
            lh, la = _split_match_names(l.get("match") or "")
            if _team_or_league_blocked(lh, la, l.get("league") or ""):
                logger.info(f"Master slip {s['id']}: dropped blacklisted leg {l.get('match')!r}")
                continue
            # 2) strip half-time selections (owner 2026-06: HT markets aren't offered for the
            #    lower leagues the Special draws from → keep only realistically-playable markets).
            sels = l.get("selections") or []
            odds = l.get("sel_odds") or []
            new_sels, new_odds = [], []
            for i, sel in enumerate(sels):
                st = (sel if isinstance(sel, str) else "").lower()
                if any(k in st for k in ("halbzeit", "1. hz", "erste hz", "1.halbzeit", "1. hälfte")):
                    continue
                new_sels.append(sel)
                if i < len(odds):
                    new_odds.append(odds[i])
            if not new_sels:
                logger.info(f"Master slip {s['id']}: dropped HT-only leg {l.get('match')!r}")
                continue  # leg had only a half-time market → drop the whole game
            l["selections"], l["sel_odds"] = new_sels, new_odds
            kept_legs.append(l)
        legs = kept_legs
        # 3) strip per-game redundant selections + recompute odds
        prod = _dedupe_multigame_legs(legs)
        after = [((l.get("match") or ""), (l.get("selections") or [])) for l in legs]
        if before != after:
            n = len(legs)
            setd = {"legs": legs, "odds": f"{prod:.2f}"}
            # keep the '... N Spiele Bet-Builder' label + the analysis narrative in sync
            mk = s.get("market") or ""
            m2 = re.sub(r"\d+\s+Spiele", f"{n} Spiele", mk)
            if m2 != mk:
                setd["market"] = m2
            games = ", ".join((l.get("match") or "") for l in legs)
            kind = "Doppelpack" if "Doppelpack" in mk else ("Special" if "Special" in mk else "Kombi")
            setd["ai_analysis"] = (
                f"👑 TipJarMaster {kind}: {n} gut gelesene Spiele ({games}) mit korrelierten "
                f"Wetten. Gesamtquote {prod:.2f}. Immer mit kontrolliertem Einsatz.")
            await db.tips.update_one({"id": s["id"]},
                                     {"$set": setd, "$unset": {"share_image_path": ""}})
            fixed += 1
    return {"fixed": fixed}


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

    # 4) RISK-KOMBI — Doppelte Chance + VARIIERENDER Tor-Leg. Owner 2026-07-24: NICHT stur
    #    "beide treffen" anhängen — ein klarer Favorit kann zu Null gewinnen (0:2-Überraschung)
    #    und der BTTS-Leg platzt. "Beide treffen" NUR wenn beide Seiten realistisch treffen
    #    (kein einseitiger Favorit, schwächeres Team trifft laut Prognose auch). Sonst Über
    #    1.5/2.5 Tore (ein 2:0 gewinnt die trotzdem). Märkte rotieren → kein monotoner Schein.
    risks = []
    _risk_rot = 0
    for p in fav_sorted:
        team = _fav_team(p)
        if not team:
            continue
        fp = p.get("fav_prob") or 0
        ph, pa = p.get("ph") or 0, p.get("pa") or 0
        total = p.get("total") or (ph + pa)
        dc = "1X" if p["fav"] == "home" else "X2"
        underdog_goals = pa if p["fav"] == "home" else ph
        # favourite may keep a clean sheet (0:2 surprise) → BTTS is a trap for weaker sides
        lopsided = fp >= 58 or underdog_goals == 0
        both_score = bool(p.get("btts")) and ph >= 1 and pa >= 1 and not lopsided
        if both_score and _risk_rot % 2 == 0:
            leg2, mult = "Beide treffen", 1.62
        elif total >= 4 and (p.get("over25") or both_score):
            leg2, mult = "Über 2.5 Tore", 1.55
        else:
            leg2, mult = "Über 1.5 Tore", 1.35
        _risk_rot += 1
        od = round(_dc_odds(fp) * mult, 2)
        risks.append(_apply_real(_sel(p, f"{team} Doppelte Chance {dc} + {leg2}", od, 6.5)))
        if len(risks) >= 5:
            break

    # 5) JACKPOT — big-odds lottery. Owner rule: NEVER an exact/correct score. Each match's
    # predicted scoreline is expressed as a NON-redundant market COMBINATION (handicap + BTTS
    # + over line that actually adds value), priced as the product of the sub-market odds.
    cs_cands = []
    for p in preds:
        ph, pa = p.get("ph"), p.get("pa")
        if ph is None or pa is None:
            continue
        cs_cands.append((_cs_odds(ph, pa), p, ph, pa))
    cs_cands.sort(key=lambda x: x[0])  # most likely (lowest odds) first
    gambles = []
    for od, p, ph, pa in cs_cands:
        combo = scoreline_to_combo(ph, pa, p.get("home"), p.get("away"))
        if not combo:
            continue
        prod_od = 1.0
        for sub in combo:
            ss = _apply_real(_sel(p, sub, 2.0, 7.0))
            try:
                prod_od *= float(ss.get("odds") or 2.0)
            except Exception:
                prod_od *= 2.0
        sel = _sel(p, " + ".join(combo), round(max(prod_od, 1.5), 2), 3.0)
        sel["combo_markets"] = combo
        gambles.append(sel)
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
        lg_dicts = []
        for mk, base in legs:
            s = _apply_real(_sel(p, mk, base, 7.0))
            lg_dicts.append({"market": mk, "odds": s.get("odds") or base})
        return _correlated_combo_odds(lg_dicts)

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

    # 6) TIPJARLOGIC-KOMBI — the owner's proven "safe slip" style: 3 tiny legs (each
    #    ~1.10-1.20) from different high-scoring games that combine to ~1.4-1.6 total and
    #    "just go through". Über 1.5 Tore in torreiche Spiele + Über 0.5 Tore als Absicherung.
    #    Every leg settles deterministically from the final score.
    tjlogic, used_tj = [], set()
    for p in goals_sorted:
        if p["id"] in used_tj:
            continue
        # Owner-Regel: nur Spiele, bei denen ein 0:0 praktisch ausgeschlossen ist —
        # keine nordischen/defensiven Über-Fallen (Örgryte–Djurgården 0:0 lässt grüßen).
        if not _zero_zero_assessment(p)["over_safe"] or _bad_for_overs(p):
            continue
        t_goals = p.get("total") or 0
        if t_goals >= 3:
            mk, base, rt = "Über 1.5 Tore", 1.18, 8.5
        elif t_goals >= 2:
            mk, base, rt = "Über 0.5 Tore", 1.08, 9.0
        else:
            continue
        used_tj.add(p["id"])
        tjlogic.append(_apply_real(_sel(p, mk, base, rt)))
        if len(tjlogic) >= 3:
            break

    # 7) WOCHEN-PFEFFER-KOMBI (owner 2026-07-21): zwei große Kombi-Scheine, die den STARKEN
    #    FAVORITEN folgen — nicht mehr von schwachen Teams abhängen (Lincoln traf gg. Mjällby
    #    3:0 NICHT → so etwas fliegt raus). Fenster 1: Di→Fr 12:00. Fenster 2: Fr→Di 12:00.
    #    Jeder Banker ist favoriten-verankert: der Favorit verliert nicht UND liefert die Tore.
    now_pw = datetime.now(timezone.utc)
    _tue0 = (now_pw - timedelta(days=(now_pw.weekday() - 1) % 7)).replace(hour=0, minute=0, second=0, microsecond=0)
    fri_noon = _tue0 + timedelta(days=3, hours=12)
    next_tue_noon = _tue0 + timedelta(days=7, hours=12)
    win_floor = now_pw - timedelta(hours=3)

    def _pepper_dc(p):
        team = _fav_team(p)
        if not team:
            return None
        dc = "1X" if p.get("fav") == "home" else "X2"
        return f"{team} Doppelte Chance {dc}", (1.28 if (p.get("fav_prob") or 0) >= 55 else 1.34)

    def _fav_goals(p):
        if p.get("fav") == "home":
            return p.get("ph") or 0
        if p.get("fav") == "away":
            return p.get("pa") or 0
        return 0

    def _pepper_qualifies(p):
        # Anchored on a strong favourite that is predicted to score enough, OR a true goal-fest.
        fav_prob = p.get("fav_prob") or 0
        if _fav_team(p) and fav_prob >= 52 and _fav_goals(p) >= 2:
            return True
        return (p.get("total") or 0) >= 4 and bool(p.get("btts"))

    def _fav_over(p):
        # "{Favourite} Über 1.5 Tore" — the strong side must score 2+ (winner's pattern:
        # Sturm/Crvena Zvezda/Lech alle 4 Tore). Nur wenn der Favorit auch 2+ erwartet.
        team, fg = _fav_team(p), _fav_goals(p)
        if not team or fg < 2:
            return None
        line = "1.5" if fg >= 2 else "0.5"
        od = 1.55 if fg >= 3 else 1.75
        return f"{team} Über {line} Tore", od

    def _build_pepper_slip(win_start, win_end, key, title, sub):
        pool = []
        for p in goals_sorted:
            ko = _parse_kickoff(p.get("kickoff"))
            if not ko or not (win_start <= ko <= win_end):
                continue
            if _bad_for_overs(p) or not _zero_zero_assessment(p)["over_safe"]:
                continue
            if not _pepper_qualifies(p):
                continue
            pool.append(p)
        # dominant favourites first (winner's style), goal-fests only as filler
        pool.sort(key=lambda p: (
            not (_fav_team(p) and (p.get("fav_prob") or 0) >= 52 and _fav_goals(p) >= 2),
            -(_fav_goals(p)), -((p.get("fav_prob") or 0)), -(p.get("total") or 0)))
        sels, used = [], set()
        # 6 BANKER — SICHERE Kombi (Owner 2026-07-22): "{Favorit} Doppelte Chance + Über 1.5 (Spiel)".
        # Wichtig: DC + Spiel-Über-1.5 → ein 1:1 REICHT bereits (Favorit verliert nicht + 2 Tore
        # im Spiel). NICHT teamspezifisch (das würde 2 Tore vom Favoriten verlangen = riskanter).
        for p in pool:
            if len(sels) >= 6 or p["id"] in used:
                continue
            dc, total = _pepper_dc(p), p.get("total") or 0
            if dc:                              # Favorit verliert nicht + Spiel Über 1.5 (1:1 reicht)
                legA, legB = dc, ("Über 1.5 Tore", 1.30)
            elif total >= 4:
                legA, legB = ("Über 2.5 Tore", 1.75), ("Unter 5.5 Tore", 1.28)
            else:
                legA, legB = ("Über 1.5 Tore", 1.30), ("Unter 4.5 Tore", 1.32)
            used.add(p["id"])
            s = _sel(p, f"{legA[0]} + {legB[0]}", round(legA[1] * legB[1], 2), 8.0)
            s["combo_markets"], s["banker"] = [legA[0], legB[0]], True
            sels.append(s)
        # up to 9 VALUE single legs → 15 games total
        for p in pool:
            if len(sels) >= 15 or p["id"] in used:
                continue
            dc, total = _pepper_dc(p), p.get("total") or 0
            if dc and (p.get("fav_prob") or 0) >= 55:
                mk, od = dc
            elif total >= 4:
                mk, od = "Über 2.5 Tore", 1.55
            else:
                mk, od = "Über 1.5 Tore", 1.30
            # owner 2026-06: HQ learning — if this market-type keeps LOSING, fall back to a safer line
            if learn_verdict("hq", mk)[0] == "veto":
                for alt in (("Über 1.5 Tore", 1.30), ("Unter 4.5 Tore", 1.32), ("Unter 3.5 Tore", 1.45)):
                    if learn_verdict("hq", alt[0])[0] != "veto":
                        mk, od = alt
                        break
            used.add(p["id"])
            s = _sel(p, mk, od, 7.5)
            s["banker"] = False
            sels.append(s)
        if len(sels) < 2:
            return None
        n_bank = sum(1 for s in sels if s.get("banker"))
        return _finalize_system(sels, n_bank, key, title,
                                f"{len(sels)} Favoriten-Spiele · {n_bank} Banker · {sub}", "risk")

    pepper_mid = _build_pepper_slip(
        max(win_floor, _tue0), fri_noon, "pepper",
        "Pfeffer-Kombi (Di→Fr 12:00)", f"läuft bis Fr {fri_noon.strftime('%d.%m. %H:%M')}")
    pepper_wknd = _build_pepper_slip(
        max(win_floor, fri_noon), next_tue_noon, "pepperwk",
        "Pfeffer-Kombi (Fr→Di 12:00)", f"läuft bis Di {next_tue_noon.strftime('%d.%m. %H:%M')}")

    # 8) BOMBEN-KOMBI (owner 2026: großer täglicher 15er-Mega-Schein). 15 Legs aus den
    #    nächsten 48h, gemischt aus HOCHWERT-Mustern, die sich ALLE deterministisch aus dem
    #    ENDSTAND abrechnen lassen (kein LLM-Rätsel, keine Halbzeit-Lücke).
    #    WICHTIG (owner 2026-07-24): NUR NOCH NICHT ANGEPFIFFENE Spiele (ko > jetzt+10min) —
    #    keine abgelaufenen/laufenden Spiele im Schein. Und: KLARER FAVORIT wird IMMER auf
    #    den Favoriten gespielt (Palmeiras=Auswärtssieg, Braga gewinnt+trifft), NIE als Remis
    #    oder Über 3.5 in einem einseitigen Spiel. "Riecht nach X" nur bei echten engen
    #    Remis-Spielen OHNE klaren Favoriten. Über 3.5 NUR wenn BEIDE Teams treffen.
    bomben_lo, bomben_hi = now_dt + timedelta(minutes=10), now_dt + timedelta(hours=48)
    bomben_pool = sorted(
        [(ko, p) for p in preds
         if (ko := _parse_kickoff(p.get("kickoff"))) and bomben_lo <= ko <= bomben_hi],
        key=lambda x: x[0])

    def _bomben_pick(p):
        fav, team = p.get("fav"), _fav_team(p)
        ph, pa = p.get("ph"), p.get("pa")
        total, fav_prob = p.get("total") or 0, p.get("fav_prob") or 0
        btts = bool(p.get("btts"))
        over_safe = _zero_zero_assessment(p)["over_safe"] and not _bad_for_overs(p)
        fg = _fav_goals(p)
        og = (pa if fav == "home" else ph if fav == "away" else 0) or 0
        margin = fg - og
        # 1) KLARER FAVORIT → immer den Favoriten spielen (nie X / nie Über 3.5 einseitig).
        #    Deckt Palmeiras (starker Auswärtssieger) & Braga (gewinnt + trifft) ab.
        if team and fav_prob >= 58 and margin >= 3:
            return (f"{team} -2.5 Handicap", 2.60, 7.0, "heavy")
        if team and fav_prob >= 55 and margin >= 2:
            return (f"{team} -1.5 Handicap", 1.90, 7.5, "heavy")
        if team and fav_prob >= 55 and fg >= 2:
            return (f"{team} Über 1.5 Tore", 1.75, 7.5, "favgoals")
        if team and fav_prob >= 60:
            dc = "1X" if fav == "home" else "X2"
            return (f"{team} Doppelte Chance {dc}", round(_dc_odds(fav_prob), 2), 8.0, "favdc")
        # 2) ECHTE Value-X ("riecht nach Remis") — Prognose = Remis ODER exakt gleiches
        #    Ergebnis (1:1). Kommt ERST nach den Favoriten-Zweigen: ein klarer Favorit
        #    (Palmeiras/Braga) ist oben schon abgefangen und wird NIE als X gespielt.
        if fav == "draw" or (ph is not None and pa is not None and ph == pa):
            return ("Unentschieden (X)", 3.30, 6.0, "draw")
        # 3) TORFESTIVAL Über 3.5 — NUR wenn BEIDE Teams treffen (kein 0:x-Favoritensieg).
        if over_safe and total >= 4 and btts and (ph or 0) >= 1 and (pa or 0) >= 1:
            return ("Über 3.5 Tore", 2.10, 7.0, "goals")
        return None

    def _bomben_filler(p):
        team, fav_prob = _fav_team(p), p.get("fav_prob") or 0
        total = p.get("total") or 0
        over_safe = _zero_zero_assessment(p)["over_safe"] and not _bad_for_overs(p)
        # prefer backing a favourite (owner style) before a blind goals leg
        if team and fav_prob >= 52:
            dc = "1X" if p.get("fav") == "home" else "X2"
            return (f"{team} Doppelte Chance {dc}", round(_dc_odds(fav_prob), 2), 8.0, "fill")
        if over_safe and total >= 3:
            return ("Über 1.5 Tore", 1.30, 8.0, "fill")
        if over_safe and total >= 2:
            return ("Über 0.5 Tore", 1.08, 8.5, "fill")
        return None

    bomben_sels, used_bomb, tag_count = [], set(), {}
    # per-Muster-Obergrenzen halten den Schein GEMISCHT (kein 14×-Über-3.5-Klumpen)
    _TAG_CAP = {"goals": 6, "draw": 6}
    # pass 1 — HOCHWERT-Picks mit Obergrenzen für eine ausgewogene Mischung
    for _ko, p in bomben_pool:
        if len(bomben_sels) >= 15 or p["id"] in used_bomb:
            continue
        pick = _bomben_pick(p)
        if not pick:
            continue
        mk, od, rt, tag = pick
        cap = _TAG_CAP.get(tag)
        if cap is not None and tag_count.get(tag, 0) >= cap:
            continue
        used_bomb.add(p["id"])
        tag_count[tag] = tag_count.get(tag, 0) + 1
        s = _apply_real(_sel(p, mk, od, rt))
        s["bomben_tag"] = tag
        bomben_sels.append(s)
    # pass 2 — sichere Filler-Legs, falls noch keine 15 zusammen sind
    for _ko, p in bomben_pool:
        if len(bomben_sels) >= 15 or p["id"] in used_bomb:
            continue
        fill = _bomben_filler(p)
        if not fill:
            continue
        mk, od, rt, tag = fill
        used_bomb.add(p["id"])
        s = _apply_real(_sel(p, mk, od, rt))
        s["bomben_tag"] = tag
        bomben_sels.append(s)

    bomben = None
    if len(bomben_sels) >= 8:
        n_draw = sum(1 for s in bomben_sels if s.get("bomben_tag") == "draw")
        n_fav = sum(1 for s in bomben_sels
                    if s.get("bomben_tag") in ("heavy", "favgoals", "favdc", "fill"))
        n_goals = sum(1 for s in bomben_sels if s.get("bomben_tag") == "goals")
        bomben = _finalize_system(
            bomben_sels, 0, "bomben", "Bomben-Kombi des Tages",
            f"{len(bomben_sels)} Legs · nächste 48h (nur kommende Spiele) · {n_fav}× Favorit · "
            f"{n_draw}× Value-X · {n_goals}× Über 3.5 · der große Zocker-Wumms", "gamble")

    # Favoriten-Tracker: starke Favoriten (fav_prob>=60) sammeln → wächst zur ~50-Team-Liste,
    # Grundlage fürs Lernen aus Ergebnissen ("Mach dir Notizen aus Ergebnissen").
    try:
        for p in preds:
            if (p.get("fav_prob") or 0) >= 60 and _fav_team(p) and not _bad_for_overs(p):
                await db.favourite_teams.update_one(
                    {"name": _fav_team(p)},
                    {"$inc": {"seen": 1}, "$set": {"last_seen": now_pw.isoformat(),
                     "league": p.get("league") or ""}}, upsert=True)
    except Exception as _e:
        logger.warning(f"favourite_teams track failed: {_e}")

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
    if len(tjlogic) >= 2:
        systems.insert(0, _finalize_system(
            tjlogic, len(tjlogic), "tjlogic", "TipJarLogic Sicherheits-Kombi",
            "3 Mini-Quoten aus Top-Spielen · ~1,5 gesamt · gebaut zum Durchgehen", "safe"))
    if hour:
        systems.insert(0, _finalize_system(
            hour, 0, "hour", "System der Stunde",
            "Το Σύστημα της Ώρας · startet ~1 Std. vor Anpfiff · Gesamtquote 3.6+", "value"))
    # both pepper windows; the currently-active window ends up on top
    for _pw in (pepper_wknd, pepper_mid):
        if _pw:
            systems.insert(0, _pw)
    # the daily 15-leg Bomben-Kombi sits at the very top (biggest ticket of the day)
    if bomben:
        systems.insert(0, bomben)

    # Time bucket per slip so the UI can split System Picks into
    # "Fängt jetzt an" / "Heute" / "Diese Woche". Every slip lands in EXACTLY one.
    now_b = datetime.now(timezone.utc)
    def _system_time_bucket(sys):
        if sys.get("key") == "hour":
            return "now"
        kos = [ko for sel in (sys.get("selections") or [])
               if (ko := _parse_kickoff(sel.get("match_time")))]
        if not kos:
            return "week"
        upcoming = [k for k in kos if k >= now_b - timedelta(hours=3)]
        ref = min(upcoming) if upcoming else min(kos)
        if ref <= now_b + timedelta(hours=3):
            return "now"
        if ref.date() == now_b.date():
            return "today"
        return "week"
    for s in systems:
        s["time_bucket"] = _system_time_bucket(s)

    return {
        "week": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
        "systems": systems,
    }


def _berlin_now() -> datetime:
    """Current time in Europe/Berlin (DST-aware)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Berlin"))
    except Exception:
        return datetime.now(timezone.utc) + timedelta(hours=2)  # summer fallback


def _system_cycle_day() -> str:
    """The daily system-picks cycle resets at 14:00 Europe/Berlin. A cycle is dated by the
    calendar day it STARTED (before 14:00 → still yesterday's cycle)."""
    b = _berlin_now()
    ref = b - timedelta(hours=14)  # shift so the 14:00 boundary becomes midnight
    return ref.strftime("%Y-%m-%d")


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
    day = _system_cycle_day()
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
            "banker": bool(sel.get("banker")),
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






# --- Owner value rule (2026-07-08): only give bets we win ~80% of the time AND at
# odds > 1.60 (genuine value). No 50/50 markets. Markets that lose too often over
# time are auto-disabled (self-learning). ---
VALUE_MIN_ODDS = 1.60
WIN_PROB_MIN = 0.72          # value pick: ≥72% win chance (owner) — clearly no coin-flip
BANKER_WIN_PROB = 0.85       # separate safe "banker" category (low odds, ~85%+), for combos


# Owner rule (2026-07): a BANKER must be near-certain. Full-match "at least 1 goal"
# (Über 0.5 — incl. a strong team scoring), Double Chance, Draw No Bet and safe unders
# (Unter 3.5/4.5) are ALWAYS bankers. Goal-OVER markets (Über 1.5/2.5, or a FIRST-HALF goal)
# are bankers ONLY on a strong offensive/consensus signal — i.e. a 0-0 (first half) is
# basically impossible (very high win-prob from krass offensive teams / experts / forebet HT).
BANKER_GOAL_WINPROB = 0.88
_BANKER_HARD_NO_RE = re.compile(
    r'(über|over)\s*(3\.5|4\.5|5\.5)|(unter|under)\s*(0\.5|1\.5|2\.5)|'
    r'beide|btts|\bgg\b|handicap|-\s*\d|\bsieg\b|gewinnt|\bwin\b', re.I)
_BANKER_ALWAYS_RE = re.compile(
    r'(über|over)\s*0\.5\s*tore\s*$|doppelte chance|double chance|draw no bet|\bdnb\b|'
    r'(unter|under)\s*(3\.5|4\.5)', re.I)
_GOAL_OVER_RE = re.compile(r'(über|over)\s*(0\.5|1\.5|2\.5)', re.I)


def _is_banker_safe(market: str, winprob=None) -> bool:
    """True only for markets safe enough to be a banker. Full-match Über 0.5 / DC / DNB /
    safe unders are always fine. A first-half goal or Über 1.5/2.5 qualifies ONLY when the
    win-prob is very high (offensive teams / expert consensus — a 0-0 is near-impossible)."""
    m = (market or "").strip()
    if _BANKER_HARD_NO_RE.search(m):
        return False
    if _BANKER_ALWAYS_RE.search(m):
        return True
    if _GOAL_OVER_RE.search(m):
        try:
            return winprob is not None and float(winprob) >= BANKER_GOAL_WINPROB
        except (TypeError, ValueError):
            return False
    return False

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


_SCAND_KEYS = (
    "allsvenskan", "superettan", "veikkausliiga", "veikkausliga", "ykkonen", "ykkönen",
    "ykkosliiga", "ykkösliiga", "eliteserien", "obos-ligaen", "obos ligaen",
    "superligaen", "danish superliga", "besta deild", "úrvalsdeild", "urvalsdeild",
    "1. deild", "norway", "sweden", "finland", "denmark", "iceland",
    "norwegen", "schweden", "finnland", "dänemark", "danemark", "island", "suomi",
)


def _is_scandinavian(*vals) -> bool:
    """True if any of the given league/country strings looks Scandinavian/Nordic.
    Owner rule: these leagues are too unpredictable for Double-Chance bankers."""
    s = " ".join(str(v or "").lower() for v in vals)
    return any(k in s for k in _SCAND_KEYS)


# Leagues the owner REFUSES to use for OVER-goals / Pfeffer picks. Predictions there
# routinely over-estimate goals (0:0 / 1:0 grind, then a late goal) — Brazil above all
# ("Ich hasse es, Brasilien als Pfeffer zu benutzen", 2026-07-21). Atletico Mineiro (pred 5, real 1:1)
# and Gremio Novorizontino (pred 4, real 0:1) proved it. They stay bettable elsewhere, just NOT overs.
_NO_OVER_LEAGUE_KEYS = ("brazil", "brasil", "brasile", "brazilian")


def _bad_for_overs(p: dict) -> bool:
    s = f"{p.get('league', '')} {p.get('league_code', '')} {p.get('country', '')}".lower()
    return any(k in s for k in _NO_OVER_LEAGUE_KEYS)


def _zero_zero_assessment(p: dict) -> dict:
    """Owner-Philosophie (2026-07-20): manche Spiele enden 0:0 (Örgryte–Djurgården,
    Hafnarfjörður–Breidablik). Über-Wetten sind NUR sicher, wenn ein 0:0 praktisch
    ausgeschlossen ist. Diese Heuristik bewertet die 0:0-Wahrscheinlichkeit aus den
    gespeicherten Prognose-Signalen (KEIN extra API-Quota):
      • hoher vorhergesagter Torschnitt → 0:0 unwahrscheinlich
      • beide Teams treffen (btts) / über 2,5 → 0:0 unwahrscheinlich
      • skandinavische/nordische Ligen → 0:0 realistisch (Owner-Erfahrung)
    Rückgabe: level = 'unlikely' | 'medium' | 'possible', over_safe (bool), label."""
    total = p.get("total") or 0
    ph, pa = p.get("ph") or 0, p.get("pa") or 0
    btts = bool(p.get("btts"))
    over25 = bool(p.get("over25"))
    scand = _is_scandinavian(p.get("league"), p.get("league_code"), p.get("country"))
    try:
        conf = int(float(str(p.get("conf"))))
    except Exception:
        conf = 0
    score = 0
    score += 42 if total >= 4 else 30 if total >= 3 else 14 if total >= 2 else -12
    if btts:
        score += 26
    if over25:
        score += 14
    if ph >= 1 and pa >= 1:
        score += 10
    if total <= 1:
        score -= 26
    if scand:
        score -= 32          # nordic/defensive: a 0:0 is genuinely on the cards
    if conf >= 80:
        score += 6
    if score >= 52:
        level, over_safe, label = "unlikely", True, "0:0 praktisch ausgeschlossen"
    elif score >= 28:
        level, over_safe, label = "medium", False, "0:0 eher unwahrscheinlich"
    else:
        level, over_safe, label = "possible", False, "0:0 möglich — Vorsicht mit Über"
    return {"level": level, "over_safe": over_safe, "label": label, "score": score}





# Owner curated-mode (2026-07-09): the Single-Picks feed is a hand-curated list
# (exact bookmaker legs & odds). While True, the Forebet/Predictz auto-scrapers do
# NOT post or overwrite single picks. Set to False to resume full automation.
# Owner curated-mode toggle. When True the Forebet/Predictz auto-scrapers do NOT
# post single picks at all. When False they post, but ONLY for tomorrow onward —
# today's Single-Picks stay hand-curated (see _AUTOPOST_MIN_KO usage below).
AUTOPOST_PAUSED = False
FOREBET_TOMORROW_URL = "https://www.forebet.com/en/football-tips-and-predictions-for-tomorrow"







# ---------------------------------------------------------------------------
# Predictz auto-tips: TipJarHQ reads predictz.com and auto-posts SAFE goals
# markets ("10-star" bankers: Over 0.5 / Over 1.5) ~24-72h before kickoff, so
# the user has ~50h lead time to build their system bets. Posts to the normal
# Rate Wall (no separate tab). German market labels.
# ---------------------------------------------------------------------------
PREDICTZ_MAX_PER_RUN = 15   # cap new safe picks per run
_MONTHS = {1: "Jan", 2: "Feb", 3: "Mär", 4: "Apr", 5: "Mai", 6: "Jun",
           7: "Jul", 8: "Aug", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Dez"}
















# ---------------------------------------------------------------------------
# API-Football /predictions — a THIRD, independent prediction source that widens
# match coverage beyond the Forebet/Predictz scrapers. Additive & quota-bounded:
# only upcoming top-league fixtures NOT already predicted by another source are
# fetched (1 request/fixture), capped per run and 24h-cached. Stored as source
# "apifootball"; consumers (Scorer-Radar / Tor-Prognose / Systeme) treat it as the
# lowest-priority gap-filler so the scraper data always wins on shared matches.
# ---------------------------------------------------------------------------
APIFOOTBALL_PRED_MAX_PER_RUN = 20   # fixtures fetched per run (quota guard)
APIFOOTBALL_PRED_CACHE_TTL_H = 24


















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


# _apifootball_async now lives in core.py (imported at top).


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
                    setd("over35", vals.get("Over 3.5"))
                    setd("under15", vals.get("Under 1.5"))
                    setd("under25", vals.get("Under 2.5"))
                    setd("under35", vals.get("Under 3.5"))
                elif nm in ("Both Teams Score", "Both Teams To Score"):
                    setd("btts", vals.get("Yes"))
                elif nm == "Home/Away":  # = Draw No Bet
                    setd("dnb_home", vals.get("Home"))
                    setd("dnb_away", vals.get("Away"))
                elif nm == "Match Winner":
                    setd("win_home", vals.get("Home"))
                    setd("win_draw", vals.get("Draw"))
                    setd("win_away", vals.get("Away"))
                elif nm == "Double Chance":
                    setd("dc_1x", vals.get("Home/Draw"))
                    setd("dc_x2", vals.get("Draw/Away"))
                    setd("dc_12", vals.get("Home/Away"))
                else:
                    # Team totals (home/away over/under X.5). API-Football names vary
                    # ("Total - Home", "Home Team Total", …) → detect by keywords.
                    lown = nm.lower()
                    if "total" in lown and "corner" not in lown and "card" not in lown:
                        pre = None
                        if "home" in lown:
                            pre = "home"
                        elif "away" in lown:
                            pre = "away"
                        if pre:
                            for ln in ("0.5", "1.5", "2.5", "3.5"):
                                setd(f"{pre}_over{ln.replace('.', '')}", vals.get(f"Over {ln}"))
                                setd(f"{pre}_under{ln.replace('.', '')}", vals.get(f"Under {ln}"))
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


def _side_in_market(m: str, home: str, away: str):
    """Detect whether a market string references the HOME or AWAY side, via the German
    'Heim'/'Gast'/'Auswärts' keywords or a significant word of the team's name."""
    def _words(name):
        return [w for w in (name or "").lower().split() if len(w) > 3]
    if "heim" in m or any(w in m for w in _words(home)):
        return "home"
    if "gast" in m or "auswärt" in m or "auswaert" in m or any(w in m for w in _words(away)):
        return "away"
    return None


def _real_odd_for(market: str, odds: dict, home: str, away: str):
    """Map one of our German market strings to a real bookmaker odd, or None.
    Bet-builder combos ("X2 + Über 1.5") aren't priced by API-Football, so we build them
    from the REAL individual leg odds (product) — matches how bookmakers price them."""
    if not odds:
        return None
    m = (market or "").lower()
    if " + " in market:
        vals = [_real_odd_for(pt, odds, home, away) for pt in market.split(" + ")]
        if vals and all(v for v in vals):
            prod = 1.0
            for v in vals:
                prod *= float(v)
            return round(prod, 2)
        return None
    # Team totals ("Heim/Gast über X.5", "{Team} über X.5") — check BEFORE the match-total
    # lines so a team-specific market is never mis-mapped to the whole-match total.
    tt = re.search(r"(über|over|unter|under)\s*(\d)\.5", m)
    if tt:
        side = _side_in_market(m, home, away)
        if side:
            over = tt.group(1) in ("über", "over")
            return odds.get(f"{side}_{'over' if over else 'under'}{tt.group(2)}5")
    if "über 3.5 tore" in m:
        return odds.get("over35")
    if "über 2.5 tore" in m:
        return odds.get("over25")
    if "über 1.5 tore" in m:
        return odds.get("over15")
    if "über 0.5 tore" in m:
        return odds.get("over05")
    if "unter 1.5 tore" in m:
        return odds.get("under15")
    if "unter 2.5 tore" in m:
        return odds.get("under25")
    if "unter 3.5 tore" in m:
        return odds.get("under35")
    if "beide" in m and "treffen" in m or "btts" in m:
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
    # Straight match winner ("{Team} Sieg"): use real 1X2 odds by team orientation.
    if "sieg" in m and "doppelte" not in m and "draw no bet" not in m and "+" not in m:
        if home and home.lower() in m:
            return odds.get("win_home")
        if away and away.lower() in m:
            return odds.get("win_away")
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


async def _hot_scorer_for_team(team_name: str, seasons: list[int]) -> dict | None:
    """Owner 2026-07-30 (Pavlidis 4 Tore für Benfica): find a team's IN-FORM key striker —
    the top season scorer who is a regular starter. Reuses the 24h-cached player stats
    (get_team_players) so it costs NO extra API quota beyond the smart-props pipeline.
    Returns {name, goals, gl (goals/start), prob (anytime-scorer prob), odds} or None."""
    tid = await resolve_team_id(team_name)
    if not tid:
        return None
    players = await get_team_players(tid, seasons)
    best = None
    for pstat in players or []:
        player = pstat.get("player") or {}
        name = player.get("name")
        stats = (pstat.get("statistics") or [{}])[0] or {}
        games = stats.get("games") or {}
        lineups = games.get("lineups") or 0
        pos = (games.get("position") or "").lower()
        goals = (stats.get("goals") or {}).get("total") or 0
        if not name or pos.startswith("goal"):
            continue
        if lineups < 6 or goals < 4:  # a prolific, regular starter only
            continue
        gl = goals / max(lineups, 1)
        prob = _prob_over(0.5, gl)
        if not best or goals > best["goals"]:
            best = {"name": name, "goals": int(goals), "gl": round(gl, 2),
                    "prob": round(prob, 3), "odds": _odds_from_prob(prob)}
    return best


QUAL_KEYWORDS = ("qualif", "champions", "europa", "conference", "uefa", "libertadores",
                 "sudamericana", "afc ", "caf ", "concacaf", "play-off", "playoff",
                 "preliminary", "wcq", "ecq")


def _looks_two_legged(pred) -> bool:
    txt = f"{pred.get('league','')} {pred.get('league_code','')} {pred.get('country','')}".lower()
    return any(k in txt for k in QUAL_KEYWORDS)


async def qualifier_autopost() -> dict:
    """Two-legged-tie awareness: for return legs of qualifier ties, look up the FIRST-leg
    result (H2H) and post the smartest safe Smart Pick — '{Leader} qualifiziert sich'
    (+ Über 1.5 Tore when the tie is goal-heavy) for a clear aggregate lead, or a double
    Asian-handicap ±1.5 (no team wins by 2) for a level tie. Aggregate-settled after FT."""
    if not API_FOOTBALL_KEY:
        return {"posted": 0, "reason": "API_FOOTBALL_KEY not configured"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    now = datetime.now(timezone.utc)
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1000)
    upcoming, seen = [], set()
    for p in preds:
        if not _looks_two_legged(p):
            continue
        ko = _parse_kickoff(p.get("kickoff"))
        if not ko:
            continue
        h = (ko - now).total_seconds() / 3600
        if h < 2 or h > 60:
            continue
        key = _match_key(p.get("home"), p.get("away"))
        if key in seen:
            continue
        seen.add(key)
        upcoming.append((ko, p))
    upcoming.sort(key=lambda x: x[0])
    posted, scanned = 0, 0
    for ko, p in upcoming[:12]:
        scanned += 1
        home, away = p.get("home"), p.get("away")
        mkey = hashlib.md5(_match_key(home, away).encode()).hexdigest()[:8]
        tip_id = f"qual-{mkey}"
        if await db.tips.find_one({"id": tip_id}, {"_id": 1}):
            continue
        # One smart pick per fixture: skip if a Favoriten-Kombi already covers this match.
        if await db.tips.find_one({"id": f"smartfav-{mkey}", "status": {"$in": ["pending", "live"]}}, {"_id": 1}):
            continue
        id_h = await resolve_team_id(home)
        id_a = await resolve_team_id(away)
        if not (id_h and id_a):
            continue
        first = _h2h_first_leg(id_h, id_a, ko)
        if not first:
            continue  # no recent prior meeting → not a two-legged tie we can reason about
        # map first-leg goals onto teamA(=return-leg home)/teamB(=return-leg away)
        if _teams_match(first["home_name"], home):
            a1, b1 = first["hg"], first["ag"]
        else:
            a1, b1 = first["ag"], first["hg"]
        total1 = a1 + b1
        # Fixture congestion between the legs: Scandinavian sides play their summer league
        # in between (tired); teams from countries in summer break only play the tie (fresh).
        try:
            fl_dt = datetime.fromisoformat(first["date"])
        except (ValueError, TypeError):
            fl_dt = ko - timedelta(days=7)
        rest_home = _matches_between(id_h, fl_dt, ko)
        rest_away = _matches_between(id_a, fl_dt, ko)

        def _load_txt(name, rest):
            n, detail = rest
            if n <= 0:
                return f"{name} ausgeruht (Sommerpause, kein Spiel zwischen den Duellen)"
            return f"{name} belastet ({n} Spiel dazwischen: {detail})"
        load_bits = [_load_txt(home, rest_home), _load_txt(away, rest_away)]
        load_note = " Belastung: " + "; ".join(load_bits) + "."
        legs = []
        rating = 8.0
        if a1 != b1:
            leader = home if a1 > b1 else away
            lead = abs(a1 - b1)
            leader_rest = (rest_home if leader == home else rest_away)[0]
            opp_rest = (rest_away if leader == home else rest_home)[0]
            q_odds = "1.12" if lead >= 2 else "1.35"
            legs.append({"home": home, "away": away,
                         "market": f"{leader} qualifiziert sich", "kind": "qualify",
                         "odds": q_odds, "status": "open",
                         "qual_ctx": {"team": leader, "a1": a1, "b1": b1,
                                      "teamA": home, "teamB": away}})
            if total1 >= 2:  # tie already produced goals → back more goals
                legs.append({"home": home, "away": away, "market": "Über 1.5 Tore",
                             "kind": "total_o", "line": 1.5, "odds": "1.40", "status": "open"})
            # congestion factor: a tired leader vs a rested underdog is more upset-prone
            if leader_rest and leader_rest >= 1 and (opp_rest == 0):
                rating = max(5.5, rating - 2.0)
            elif (leader_rest == 0) and opp_rest and opp_rest >= 1:
                rating = min(9.0, rating + 0.5)
            subtitle = (f"{leader} führt nach Hinspiel (aggregat {a1}:{b1}). "
                        f"Wir setzen auf Weiterkommen"
                        + (" + Tore, da das Hinspiel torreich war." if total1 >= 2 else "."))
        else:
            # level tie between two even sides → nobody wins by 2 goals (double AH ±1.5)
            legs.append({"home": home, "away": away, "market": f"{home} +1.5",
                         "kind": "ah15_home", "odds": "1.30", "status": "open"})
            legs.append({"home": home, "away": away, "market": f"{away} +1.5",
                         "kind": "ah15_away", "odds": "1.30", "status": "open"})
            rating = 7.5
            subtitle = (f"Enges Duell (Hinspiel {a1}:{b1}). Doppel-Handicap ±1,5: "
                        f"gewinnt, solange keine Mannschaft mit 2+ Toren gewinnt.")
        prod = 1.0
        for lg in legs:
            try:
                prod *= float(lg["odds"])
            except Exception:
                pass
        display_legs = [{
            "match": f"{home} – {away}", "league": p.get("league") or "Qualifikation",
            "kickoff": p.get("kickoff") or "",
            "selections": [lg["market"] for lg in legs],
            "sel_odds": [lg["odds"] for lg in legs], "status": "pending",
        }]
        base_analysis = f"Hinspiel-basiert: {subtitle}{load_note} (Gesamtquote {round(prod, 2)})."
        _ctx = (f"Rückspiel eines Qualifikations-Duells über zwei Spiele. "
                f"Spiel: {home} (Heim) vs {away} (Auswärts), {p.get('league') or 'Qualifikation'}. "
                f"Hinspiel-Aggregat: {home} {a1} : {b1} {away}. "
                f"Unsere Wette: {', '.join(lg['market'] for lg in legs)} (Gesamtquote {round(prod, 2)}). "
                f"Spielbelastung zwischen den Duellen — {load_note.strip()} "
                f"Erkläre in 2-3 Sätzen, warum das ein guter Pick ist: berücksichtige Aggregat "
                f"(zurückliegendes Team MUSS offensiv spielen → Tore/Verlängerung), Weiterkommen "
                f"und Belastung/mögliche Rotation, falls ein Team ein schlechtes Ligaspiel dazwischen hatte.")
        _llm = await llm_pick_analysis(_ctx, await _pick_stats_line(p))
        analysis = _llm or base_analysis
        await db.tips.insert_one({
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away, "match_time": p.get("kickoff") or "",
            "country": p.get("country") or "", "league": "TipJarHQ Qualifikations-Pick",
            "league_code": p.get("league_code") or "",
            "market": f"{home} vs {away} — Qualifikations-Pick",
            "odds": f"{round(prod, 2)}", "combo_legs": legs, "is_parlay": True,
            "ai_rating": round(rating, 1), "win_prob": 0.0,
            "ai_analysis": analysis,
            "legs": display_legs, "stake": "", "potential_return": "",
            "status": "pending", "source": "smart", "category": "banker",
            "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "created_at": now.isoformat(),
        })
        posted += 1
    return {"posted": posted, "scanned": scanned}


# ---------------------------------------------------------------------------
# QUALIFIER BRIEFING (owner request 2026-07-21): a short intro in Smart Picks about
# this week's European qualifier ties — for each team, which LEAGUE game they play
# before/after, how they performed there (shots), schedule congestion / rotation
# risk, and whether the next league game matters / involves far travel. Quota-capped
# and 8h-cached so it never hammers API-Football or the LLM key.
# ---------------------------------------------------------------------------
BRIEFING_TTL_H = 8
BRIEFING_MAX_MATCHES = 10
_BRIEFING_BUILDING = False


def _is_domestic_league_fx(fx: dict) -> bool:
    """True for a normal domestic LEAGUE fixture (not a UEFA/qualifier tie, cup or
    friendly). NOTE: API-Football's /fixtures response does NOT populate league.type
    (that only exists on /leagues), so we classify by the league NAME instead."""
    name = ((fx.get("league") or {}).get("name") or "").lower()
    if not name:
        return False
    if any(k in name for k in QUAL_KEYWORDS):
        return False
    if any(k in name for k in ("friendl", "cup", "pokal", "coppa", "copa del",
                               "trophy", "supercup", "super cup", "super lig cup")):
        return False
    return True


def _fx_shots_for_team(fid, team_id):
    """(total shots, shots on goal) for a team in a finished fixture, else (None, None)."""
    stats = _apifootball("/fixtures/statistics", {"fixture": fid}) or []
    for block in stats:
        if (block.get("team") or {}).get("id") == team_id:
            sh = sog = None
            for row in block.get("statistics") or []:
                t = (row.get("type") or "").lower()
                if t == "total shots":
                    sh = row.get("value")
                elif t == "shots on goal":
                    sog = row.get("value")
            return sh, sog
    return None, None


async def _team_league_context(team_id: int, team_name: str, qko: datetime) -> dict:
    """Last domestic-league game BEFORE the qualifier (result + shots) and next
    domestic-league game AFTER it (opponent, home/away, city, days rest)."""
    recent = await _apifootball_async("/fixtures", {"team": team_id, "last": 6}) or []
    upcoming = await _apifootball_async("/fixtures", {"team": team_id, "next": 6}) or []

    def _dt(fx):
        try:
            return datetime.fromisoformat(((fx.get("fixture") or {}).get("date") or "").replace("Z", "+00:00"))
        except Exception:
            return None

    out = {"team": team_name, "last_league": None, "next_league": None}

    # LAST finished domestic-league game before the qualifier
    prev = [fx for fx in recent if _is_domestic_league_fx(fx)
            and ((fx.get("fixture") or {}).get("status") or {}).get("short") in FINISHED_STATUSES
            and (_dt(fx) is not None and _dt(fx) < qko)]
    prev.sort(key=lambda fx: _dt(fx) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    if prev:
        fx = prev[0]
        fid = (fx.get("fixture") or {}).get("id")
        teams = fx.get("teams") or {}
        is_home = (teams.get("home") or {}).get("id") == team_id
        opp = ((teams.get("away") if is_home else teams.get("home")) or {}).get("name") or "?"
        hg, ag = _reg_goals(fx)
        gf, ga = (hg, ag) if is_home else (ag, hg)
        sh, sog = _fx_shots_for_team(fid, team_id)
        d = _dt(fx)
        out["last_league"] = {
            "opponent": opp, "home": is_home, "gf": gf, "ga": ga,
            "shots": sh, "sot": sog, "league": (fx.get("league") or {}).get("name") or "",
            "date": d.isoformat() if d else "",
            "days_before": round((qko - d).total_seconds() / 86400, 1) if d else None,
        }

    # NEXT domestic-league game after the qualifier
    nxt = [fx for fx in upcoming if _is_domestic_league_fx(fx)
           and (_dt(fx) is not None and _dt(fx) > qko)]
    nxt.sort(key=lambda fx: _dt(fx) or datetime.max.replace(tzinfo=timezone.utc))
    if nxt:
        fx = nxt[0]
        teams = fx.get("teams") or {}
        is_home = (teams.get("home") or {}).get("id") == team_id
        opp = ((teams.get("away") if is_home else teams.get("home")) or {}).get("name") or "?"
        venue = (fx.get("fixture") or {}).get("venue") or {}
        d = _dt(fx)
        out["next_league"] = {
            "opponent": opp, "home": is_home,
            "city": venue.get("city") or "", "league": (fx.get("league") or {}).get("name") or "",
            "date": d.isoformat() if d else "",
            "days_after": round((d - qko).total_seconds() / 86400, 1) if d else None,
        }
    return out


_BRIEFING_SYSTEM = (
    "Du bist der Chef-Analyst von TipJar. Schreibe ein ULTRA-KURZES deutsches Briefing zu den "
    "Europapokal-Quali-Spielen dieser Woche. REGELN: KEIN Intro, KEINE Floskeln, KEIN Gelaber. "
    "NUR konkrete, wett-relevante Fakten. Pro Spiel GENAU EINE Zeile im Format: "
    "'⚽ Heim – Auswärts: <der eine wichtigste Fakt/Tipp-Winkel>.' Der Winkel muss ETWAS aussagen — "
    "z.B. Rotationsrisiko wegen engem Ligaspiel in X Tagen, starke/schwache Form aus dem letzten "
    "Ligaspiel (Ergebnis nennen), oder weite Auswärtsreise. Wenn zu einem Spiel KEINE verwertbaren "
    "Daten da sind, LASS DIE ZEILE KOMPLETT WEG (lieber weniger Zeilen als leeres Gelaber). "
    "KEINE erfundenen Zahlen. Maximal 8 Zeilen insgesamt. Keine Überschriften, keine Zusammenfassung."
)


async def build_qualifier_briefing() -> dict:
    """Gather this week's qualifier ties + each team's league context and let the LLM
    write the German briefing. Cached in db.briefing_cache (id='qualifier')."""
    global _BRIEFING_BUILDING
    if _BRIEFING_BUILDING:
        return {"skipped": True}
    _BRIEFING_BUILDING = True
    try:
        return await _build_qualifier_briefing_inner()
    finally:
        _BRIEFING_BUILDING = False


async def _build_qualifier_briefing_inner() -> dict:
    now = datetime.now(timezone.utc)
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(2000)
    ties, seen = [], set()
    for p in preds:
        if not _looks_two_legged(p):
            continue
        ko = _parse_kickoff(p.get("kickoff"))
        if not ko:
            continue
        h = (ko - now).total_seconds() / 3600
        if h < -3 or h > 24 * 7:
            continue
        key = _match_key(p.get("home"), p.get("away"))
        if key in seen:
            continue
        seen.add(key)
        ties.append((ko, p))
    ties.sort(key=lambda x: x[0])
    ties = ties[:BRIEFING_MAX_MATCHES]

    matches = []
    for ko, p in ties:
        home, away = p.get("home"), p.get("away")
        id_h = await resolve_team_id(home)
        id_a = await resolve_team_id(away)
        ctx_h = await _team_league_context(id_h, home, ko) if id_h else {"team": home, "last_league": None, "next_league": None}
        ctx_a = await _team_league_context(id_a, away, ko) if id_a else {"team": away, "last_league": None, "next_league": None}
        matches.append({
            "home": home, "away": away, "league": p.get("league") or "Qualifikation",
            "kickoff": ko.isoformat(), "teams": [ctx_h, ctx_a],
        })

    # Build a compact structured prompt for the LLM.
    def _team_line(c):
        parts = [f"  Team: {c['team']}"]
        ll = c.get("last_league")
        if ll:
            venue = "Heim" if ll["home"] else "Auswärts"
            shots = f", {ll['shots']} Schüsse ({ll.get('sot') or '?'} aufs Tor)" if ll.get("shots") is not None else ""
            parts.append(f"    Letztes Ligaspiel ({venue}, vor {ll.get('days_before')} Tagen): "
                         f"{ll['gf']}:{ll['ga']} gg. {ll['opponent']} [{ll['league']}]{shots}")
        else:
            parts.append("    Letztes Ligaspiel: keine Daten (evtl. Liga in Sommerpause)")
        nl = c.get("next_league")
        if nl:
            venue = "zuhause" if nl["home"] else f"auswärts in {nl.get('city') or '?'}"
            parts.append(f"    Nächstes Ligaspiel (in {nl.get('days_after')} Tagen, {venue}): "
                         f"gg. {nl['opponent']} [{nl['league']}]")
        else:
            parts.append("    Nächstes Ligaspiel: keine Daten")
        return "\n".join(parts)

    lines = []
    for m in matches:
        ko_txt = ""
        try:
            ko_txt = datetime.fromisoformat(m["kickoff"]).strftime("%d.%m. %H:%M")
        except Exception:
            pass
        lines.append(f"Quali-Spiel ({ko_txt}): {m['home']} vs {m['away']} [{m['league']}]\n"
                     + "\n".join(_team_line(c) for c in m["teams"]))
    data_block = "\n\n".join(lines) if lines else "Diese Woche keine Qualifikationsspiele gefunden."

    narrative = ""
    if EMERGENT_LLM_KEY and matches:
        try:
            chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"brief-{uuid.uuid4()}",
                           system_message=_BRIEFING_SYSTEM).with_model(AI_MODEL_PROVIDER, AI_TEXT_MODEL)
            resp = await chat.send_message(UserMessage(
                text=f"Daten der Qualifikationswoche:\n\n{data_block}\n\nSchreibe das Briefing."))
            narrative = (resp if isinstance(resp, str) else str(resp)).strip()[:900]
        except Exception as e:
            logger.error(f"briefing LLM failed: {e}")

    doc = {"id": "qualifier", "generated_at": now.isoformat(),
           "count": len(matches), "matches": matches, "narrative": narrative}
    await db.briefing_cache.update_one({"id": "qualifier"}, {"$set": doc}, upsert=True)
    logger.info(f"Qualifier briefing built: {len(matches)} ties")
    return doc



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
        prod = _correlated_combo_odds(combo_legs)
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


async def favourite_smart_autopost() -> dict:
    """Owner-Wunsch (2026-07-22): Smart Picks sollen dominante FAVORITEN als saubere 2-Leg-
    Kombis mit Sterne-Rating & Begründung anbieten (wie der Gewinner: Lech +Handicap + Über 1.5).
    SICHER: '{Favorit} Doppelte Chance + Über 1.5' (ein 1:1 reicht). PFEFFER für sehr dominante:
    '{Favorit} -1.5 Handicap + Über 1.5' (Favorit gewinnt mit 2+). Kein Brasilien, keine 0:0-Fallen."""
    if not API_FOOTBALL_KEY:
        return {"posted": 0, "reason": "API_FOOTBALL_KEY not configured"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    now = datetime.now(timezone.utc)
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1000)
    cmap = _consensus_map(preds)
    cand, seen = [], set()
    for p in preds:
        if not _pred_whitelisted(p) or _bad_for_overs(p):
            continue
        fav = _fav_team(p)
        fav_prob = p.get("fav_prob") or 0
        fg = (p.get("ph") or 0) if p.get("fav") == "home" else (p.get("pa") or 0)
        if not fav or fav_prob < 58 or fg < 2:
            continue
        if not _zero_zero_assessment(p)["over_safe"]:
            continue
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
        cons = _consensus_for(cmap, p.get("home"), p.get("away"), p.get("fav"))["agree"]
        cand.append((cons, fav_prob, fg, ko, p, fav))
    # owner 2026-07-30 Konsens-Booster: prefer fixtures more prediction sources agree on
    cand.sort(key=lambda x: (-x[0], -x[1], -x[2]))
    posted = 0
    for cons, fav_prob, fg, ko, p, fav in cand[:SMART_MAX_MATCHES]:
        home, away = p.get("home"), p.get("away")
        dc = "1X" if p.get("fav") == "home" else "X2"
        mkey = hashlib.md5(_match_key(home, away).encode()).hexdigest()[:8]
        tip_id = f"smartfav-{mkey}"
        if await db.tips.find_one({"id": tip_id}, {"_id": 1}):
            continue
        # One smart pick per fixture: if a Qualifikations-Pick already covers this match,
        # don't also post a Favoriten-Kombi (owner 2026-07-29: no duplicate smart tips).
        if await db.tips.find_one({"id": f"qual-{mkey}", "status": {"$in": ["pending", "live"]}}, {"_id": 1}):
            continue
        very_dominant = fav_prob >= 66 and fg >= 3
        if very_dominant:
            legs_spec = [(f"{fav} -1.5 Handicap", 1.85, ""),
                         ("Über 1.5 Tore", 1.30, "")]
            why = (f"{fav} ist klarer Favorit (Sieg-Wahrscheinlichkeit {fav_prob}%) und wird "
                   f"laut Prognose {fg} Tore schießen — Kombi zielt auf einen Sieg mit 2+ Toren Vorsprung.")
        else:
            legs_spec = [(f"{fav} Doppelte Chance {dc}", 1.30, "dc_1x" if dc == "1X" else "dc_x2"),
                         ("Über 1.5 Tore", 1.30, "")]
            why = (f"{fav} ist starker Favorit ({fav_prob}%). SICHER gebaut: {fav} verliert nicht "
                   f"UND es fallen 2+ Tore — schon ein 1:1 reicht für diesen Schein.")
        combo_legs = [{"home": home, "away": away, "market": mk, "odds": str(od),
                       "kind": kd, "team": fav if "-1.5" in mk or "Chance" in mk else "",
                       "status": "open"} for (mk, od, kd) in legs_spec]
        combo_legs = _dedupe_builder_legs(combo_legs, home, away)
        prod = _correlated_combo_odds(combo_legs)
        display_legs = [{
            "match": f"{home} – {away}", "league": p.get("league") or "TipJarHQ Smart Pick",
            "kickoff": p.get("kickoff") or "",
            "selections": [lg["market"] for lg in combo_legs],
            "sel_odds": [lg["odds"] for lg in combo_legs], "status": "pending",
        }]
        rating = 7.0 + (1 if fav_prob >= 62 else 0) + (1 if fav_prob >= 70 else 0) \
            + (0.5 if p.get("btts") else 0) + (0.5 if fg >= 3 else 0) \
            + (0.5 if cons >= 3 else 0) + (0.5 if cons >= 5 else 0)
        rating = round(min(10.0, rating), 1)
        stars = "⭐" * int(round(rating))
        analysis = (f"{stars} Favoriten-Smart-Pick: {why} Anstoß {p.get('kickoff')}. "
                    f"Genau das Muster erfolgreicher Tipper — auf den dominanten Favoriten setzen, "
                    f"der selbst für die Tore sorgt. Quoten sind Schätzungen.")
        if cons >= 3:
            analysis += (f" 🔗 Konsens: {cons} unabhängige Prognose-Quellen sehen denselben "
                         f"Favoriten — starkes Übereinstimmungssignal.")
        stats_line = await _pick_stats_line(p)
        if stats_line:
            analysis += f"\n\n📊 {stats_line}"
        await db.tips.insert_one({
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away, "match_time": p.get("kickoff") or "",
            "country": p.get("country") or "", "league": p.get("league") or "TipJarHQ Smart Pick",
            "league_code": p.get("league_code") or "",
            "market": (f"{fav} — Favoriten-Kombi (" + " + ".join(lg["market"] for lg in combo_legs) + ")")
                      if len(combo_legs) > 1 else combo_legs[0]["market"],
            "odds": f"{round(prod, 2)}", "combo_legs": combo_legs,
            "is_parlay": len(combo_legs) > 1,
            "ai_rating": rating, "ai_analysis": analysis, "stats_line": stats_line,
            "legs": display_legs, "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "smart", "created_at": datetime.now(timezone.utc).isoformat(),
        })
        posted += 1
    logger.info(f"Favourite Smart run: posted {posted} of {len(cand)} candidates")
    return {"posted": posted, "candidates": len(cand)}


GIFT_MAX_PER_RUN = 3  # owner: 2-3 "Geschenke" (Asian Über 1.0) per day


async def gift_of_the_day() -> dict:
    """Owner 2026-07-29: auto-post SAFE 'Geschenke' — an Asian 'Über 1.0' team total on a
    clear favourite that has a REAL chance of 2+ goals (push at exactly 1 → no loss). Only
    fires when the favourite's own WIN odds sit ~1.50-1.85 (so the Asian Über 1.0 lands near
    the sweet ~1.34 gift price — a heavier favourite would price it too low to be worth it).
    Posts as a KI single (hq-auto, is_gift=True) → shows in the 🎁 Geschenke tab, auto-settled."""
    if not API_FOOTBALL_KEY:
        return {"posted": 0, "reason": "API_FOOTBALL_KEY not configured"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    now = datetime.now(timezone.utc)
    day = now.date().isoformat()
    made = await db.tips.count_documents(
        {"source": "hq-auto", "is_gift": True, "gift_kind": "asian_o1", "gift_day": day})
    if made >= GIFT_MAX_PER_RUN:
        return {"posted": 0, "reason": "daily cap reached"}
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1000)
    cand, seen = [], set()
    for p in preds:
        if not _pred_whitelisted(p) or _bad_for_overs(p):
            continue
        fav = _fav_team(p)
        fav_prob = p.get("fav_prob") or 0
        fg = (p.get("ph") or 0) if p.get("fav") == "home" else (p.get("pa") or 0)
        if not fav or fav_prob < 60 or fg < 2:
            continue  # clear favourite AND predicted to score 2+
        if not _zero_zero_assessment(p)["over_safe"]:
            continue
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
        cand.append((fav_prob, fg, ko, p, fav))
    cand.sort(key=lambda x: (-x[0], -x[1]))
    posted = 0
    for fav_prob, fg, ko, p, fav in cand:
        if made + posted >= GIFT_MAX_PER_RUN:
            break
        home, away = p.get("home"), p.get("away")
        mkey = hashlib.md5(_match_key(home, away).encode()).hexdigest()[:8]
        tip_id = f"gift-{mkey}"
        if await db.tips.find_one({"id": tip_id}, {"_id": 1}):
            continue
        # Owner rule: the favourite's WIN odds must be ~1.50-1.85 so the Asian Über 1.0 gift
        # prices around 1.34 (a heavier favourite would make it too cheap to bother).
        try:
            odds = await ensure_match_odds(home, away, p.get("kickoff") or "")
        except Exception:
            odds = {}
        win_od = odds.get("win_home") if p.get("fav") == "home" else odds.get("win_away")
        try:
            win_od = float(win_od)
        except (TypeError, ValueError):
            continue  # need a real win price to qualify the gift
        if not (1.50 <= win_od <= 1.85):
            continue
        # Estimate the Asian Über 1.0 team-total price from the win odds (~1.30 at 1.50 win,
        # ~1.42 at 1.85 win). Kept as a plausible estimate — the micro-line isn't in the feed.
        gift_od = round(min(1.42, max(1.28, 1.30 + (win_od - 1.50) / 0.35 * 0.12)), 2)
        market = f"{fav} Asian Über 1.0 Tore"
        analysis = (
            f"🎁 Geschenk des Tages: {fav} ist klarer Favorit (Sieg-Wahrscheinlichkeit {fav_prob}%, "
            f"Sieg-Quote {win_od:.2f}) und laut Prognose mit {fg} Toren eingeplant. "
            f"Asiatisch Über 1.0 — {fav} trifft 2+ = gewonnen, GENAU 1 Tor = Einsatz zurück (Push), "
            f"0 = verloren. Sichere Absicherung bei genau 1 Tor. Quote geschätzt."
        )
        await db.tips.insert_one({
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away, "match_time": p.get("kickoff") or "",
            "country": p.get("country") or "", "league": p.get("league") or "TipJarHQ Geschenk",
            "league_code": p.get("league_code") or "",
            "market": market, "odds": f"{gift_od:.2f}",
            "ai_rating": 9.0, "win_prob": round(fav_prob / 100.0, 2),
            "ai_analysis": analysis,
            "is_gift": True, "gift_kind": "asian_o1", "gift_day": day,
            "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
            "category": "value",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": datetime.now(timezone.utc).isoformat(),
        })
        posted += 1
        logger.info(f"Gift of the day: {fav} Asian Über 1.0 @ {gift_od} (win {win_od}, {fg} goals pred)")
    return {"posted": posted, "candidates": len(cand)}


# European two-legged knockout ties: qualifiers + main-stage KO rounds.
EURO_KO_KEYWORDS = (
    "champions league", "europa league", "conference league", "uefa", "champions-league",
    "europa-league", "conference-league", "champions", "super cup",
)
KO_MAX_PER_RUN = 4  # aggressive KO-tie specials per day


async def _first_leg_result(home: str, away: str, kickoff_dt):
    """For a suspected 2nd leg, fetch H2H and return the FIRST-leg score as
    (fl_home_name, fl_home_goals, fl_away_name, fl_away_goals) — the most recent prior
    meeting 3-30 days before kickoff with the venue reversed. None when not found."""
    tid_h = await resolve_team_id(home)
    tid_a = await resolve_team_id(away)
    if not tid_h or not tid_a:
        return None
    resp = await _apifootball_async("/fixtures/headtohead", {"h2h": f"{tid_h}-{tid_a}", "last": 8}) or []
    best = None
    for fx in resp:
        st = ((fx.get("fixture") or {}).get("status") or {}).get("short")
        if st != "FT":
            continue
        dstr = (fx.get("fixture") or {}).get("date") or ""
        try:
            fdt = datetime.fromisoformat(dstr.replace("Z", "+00:00"))
        except Exception:
            continue
        days = (kickoff_dt - fdt).total_seconds() / 86400.0
        if days < 3 or days > 30:
            continue
        teams = fx.get("teams") or {}
        fh = (teams.get("home") or {}).get("name") or ""
        fa = (teams.get("away") or {}).get("name") or ""
        # venue must be reversed: the FIRST leg host is the SECOND leg's away side
        if not (_teams_match(fh, away) and _teams_match(fa, home)):
            continue
        goals = fx.get("goals") or {}
        gh, ga = goals.get("home"), goals.get("away")
        if gh is None or ga is None:
            continue
        if best is None or fdt > best[0]:
            best = (fdt, fh, int(gh), fa, int(ga))
    return best[1:] if best else None


async def knockout_tie_autopost() -> dict:
    """Owner 2026-07-30: aggressive 'K.o.-Duell' specials for European two-legged ties.
    Detects the RETURN leg (H2H shows a reversed meeting 3-30 days earlier), reads the first-leg
    score and posts a bold same-game multi into the RISK category: the first-leg WINNER to win the
    return leg + plenty of goals (the trailing side must attack). Big lead → Über 3.5, tight → Über
    2.5 (+ BTTS if both scored first leg). One per tie, max a few per day, auto-settled."""
    if not API_FOOTBALL_KEY:
        return {"posted": 0, "reason": "API_FOOTBALL_KEY not configured"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    now = datetime.now(timezone.utc)
    day = now.date().isoformat()
    made = await db.tips.count_documents({"source": "hq-auto", "ko_tie": True, "gift_day": day})
    if made >= KO_MAX_PER_RUN:
        return {"posted": 0, "reason": "daily cap reached"}
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1500)
    posted, checked = 0, 0
    for p in preds:
        if made + posted >= KO_MAX_PER_RUN:
            break
        lg = (p.get("league") or "").lower()
        if not any(k in lg for k in EURO_KO_KEYWORDS):
            continue
        ko = _parse_kickoff(p.get("kickoff"))
        if not ko:
            continue
        h = (ko - now).total_seconds() / 3600
        if h < 2 or h > SMART_LOOKAHEAD_H:
            continue
        home, away = p.get("home"), p.get("away")
        mkey = hashlib.md5(_match_key(home, away).encode()).hexdigest()[:8]
        tip_id = f"ko-{mkey}"
        if await db.tips.find_one({"id": tip_id}, {"_id": 1}):
            continue
        checked += 1
        fl = await _first_leg_result(home, away, ko)
        if not fl:
            continue  # not a detectable return leg
        fl_h, fl_hg, fl_a, fl_ag = fl  # first-leg host = current AWAY side
        # first-leg winner (name) and margin
        if fl_hg == fl_ag:
            continue  # drawn first leg → no clear favourite angle
        winner = fl_h if fl_hg > fl_ag else fl_a
        margin = abs(fl_hg - fl_ag)
        both_scored = fl_hg > 0 and fl_ag > 0
        try:
            odds = await ensure_match_odds(home, away, p.get("kickoff") or "")
        except Exception:
            odds = {}
        win_od = odds.get("win_home") if _teams_match(winner, home) else odds.get("win_away")
        try:
            win_od = float(win_od)
        except (TypeError, ValueError):
            win_od = 1.90  # estimate when the feed has no price
        over_line = "3.5" if margin >= 2 else "2.5"
        over_od = 2.45 if over_line == "3.5" else 1.90
        legs = [
            {"sel": f"{winner} Sieg", "od": win_od, "team": winner, "kind": "win"},
            {"sel": f"Über {over_line} Tore", "od": over_od, "team": "", "kind": ""},
        ]
        if both_scored:
            legs.append({"sel": "Beide Teams treffen", "od": 1.72, "team": "", "kind": "btts"})
        combo = 1.0
        for l in legs:
            combo *= l["od"]
        combo = round(combo, 2)
        packed = [{"match": f"{home} - {away}", "league": p.get("league") or "UEFA",
                   "kickoff": p.get("kickoff") or "", "status": "pending",
                   "selections": [l["sel"]], "sel_odds": [f"{l['od']:.2f}"]} for l in legs]
        combo_legs = [{"home": home, "away": away, "market": l["sel"],
                       "odds": l["od"], "kind": l["kind"], "team": l["team"]} for l in legs]
        analysis = (
            f"🔥 K.o.-Duell (Rückspiel): Hinspiel {fl_h} {fl_hg}:{fl_ag} {fl_a}. "
            f"{winner} führt im Duell{' klar' if margin >= 2 else ''} — der Rückständige MUSS aufmachen. "
            f"Aggressiv: {winner} gewinnt + Über {over_line} Tore"
            f"{' + beide treffen' if both_scored else ''}. Gesamtquote {combo:.2f}. Hohes Risiko, hohe Quote."
        )
        await db.tips.insert_one({
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away, "match_time": p.get("kickoff") or "",
            "country": p.get("country") or "", "league": p.get("league") or "UEFA K.o.-Duell",
            "market": f"K.o.-Duell {len(legs)}-fach", "odds": f"{combo:.2f}",
            "ai_rating": 6.5, "win_prob": 0.0,
            "ai_analysis": analysis,
            "ko_tie": True, "gift_day": day,
            "legs": packed, "combo_legs": combo_legs, "is_parlay": True, "stake": "", "potential_return": "",
            "category": "risk",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": datetime.now(timezone.utc).isoformat(),
        })
        posted += 1
        logger.info(f"K.o.-Duell: {winner} + Über {over_line} ({home} v {away}, "
                    f"first leg {fl_hg}:{fl_ag}) @ {combo}")
    return {"posted": posted, "checked": checked}




async def mental_autopost() -> dict:
    """Owner-Wunsch (2026-07-22): 'Mental'-Kategorie im Single-Pick-Bereich — verrückte
    Long-Shot-Bet-Builder auf EIN Spiel mit riesiger Gesamtquote (Über 4.5 Tore, beide
    Halbzeiten, Favorit-Handicap usw.). Hoher Nervenkitzel, kleine Trefferchance. Alle Legs
    text-abrechenbar (settle_hq_combos), category='mental', source='hq-auto'."""
    if not API_FOOTBALL_KEY:
        return {"posted": 0, "reason": "API_FOOTBALL_KEY not configured"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    now = datetime.now(timezone.utc)
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1000)
    cand, seen = [], set()
    gift_map = await _gift_stance_map()
    for p in preds:
        if not _pred_whitelisted(p) or _bad_for_overs(p):
            continue
        if (p.get("total") or 0) < 4 or not _zero_zero_assessment(p)["over_safe"]:
            continue
        # owner 2026-07-30: a GIFT is the source of truth — if a gift called this match/team
        # low-scoring, the Mental goal-fest (Über 4.5 etc.) must NOT be offered here.
        if _gift_under_lean(gift_map.get(_match_key(p.get("home"), p.get("away")))):
            continue
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
        cand.append((p.get("total") or 0, ko, p))
    cand.sort(key=lambda x: -x[0])
    posted = 0
    for total, ko, p in cand[:6]:
        home, away = p.get("home"), p.get("away")
        mkey = hashlib.md5(_match_key(home, away).encode()).hexdigest()[:8]
        tip_id = f"mental-{mkey}"
        if await db.tips.find_one({"id": tip_id}, {"_id": 1}):
            continue
        fav = _fav_team(p)
        dc_side = p.get("fav")
        legs = [("Über 4.5 Tore", 6.5, ""),
                ("Beide Teams treffen", 1.55, "btts"),
                ("Tor in jeder Halbzeit", 1.80, "")]
        if fav and dc_side in ("home", "away"):
            legs.append((f"{fav} -1.5 Handicap", 2.10, ""))
            legs.append((f"{fav} Über 2.5 Tore", 3.80, ""))
        else:
            legs.append(("Über 5.5 Tore", 3.40, ""))
            legs.append(("Über 3.5 Tore", 1.55, ""))
        combo_legs = [{"home": home, "away": away, "market": mk, "odds": str(od),
                       "kind": kd, "team": fav if ("-1.5" in mk or "Über 2.5" in mk and fav and fav in mk) else "",
                       "status": "open"} for (mk, od, kd) in legs]
        combo_legs = _dedupe_builder_legs(combo_legs, home, away)
        prod = 1.0
        for lg in combo_legs:
            prod *= float(lg["odds"])
        display_legs = [{
            "match": f"{home} – {away}", "league": p.get("league") or "TipJarHQ Mental",
            "kickoff": p.get("kickoff") or "",
            "selections": [lg["market"] for lg in combo_legs],
            "sel_odds": [lg["odds"] for lg in combo_legs], "status": "pending",
        }]
        analysis = (f"🤯 MENTAL-Pick — Jackpot-Bet-Builder auf EIN Spiel bei ~{round(prod)}/1! "
                    f"{home} vs {away} ist ein absolutes Torfest-Kandidat (Prognose {p.get('ph')}:{p.get('pa')}). "
                    f"Kleiner Einsatz, riesiger Traum — genau EIN Leg reicht zum Zittern. Nur mit Spaßgeld spielen! "
                    f"Quoten sind Schätzungen.")
        stats_line = await _pick_stats_line(p)
        if stats_line:
            analysis += f"\n\n📊 {stats_line}"
        await db.tips.insert_one({
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away, "match_time": p.get("kickoff") or "",
            "country": p.get("country") or "", "league": p.get("league") or "TipJarHQ Mental",
            "league_code": p.get("league_code") or "",
            "market": f"{home} vs {away} — MENTAL Bet-Builder ({len(combo_legs)} Legs)",
            "odds": f"{round(prod, 2)}", "combo_legs": combo_legs, "is_parlay": True,
            "ai_rating": 3.5, "ai_analysis": analysis, "category": "mental",
            "stats_line": stats_line,
            "legs": display_legs, "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": datetime.now(timezone.utc).isoformat(),
        })
        posted += 1
    logger.info(f"Mental run: posted {posted} of {len(cand)} candidates")
    return {"posted": posted, "candidates": len(cand)}



def _parse_smart_json(resp) -> dict | None:
    """Extract the JSON object from an LLM Smart-Bet reply (tolerates markdown/prose)."""
    raw = (resp if isinstance(resp, str) else str(resp)).strip()
    s, e = raw.find("{"), raw.rfind("}")
    if s == -1 or e == -1:
        return None
    try:
        return json.loads(raw[s:e + 1])
    except Exception:
        return None


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
                "You are TipJar's Smart Bet strategist — a confident, realistic football tipster. "
                "A fan sends an insider hint, a QUESTION about a match (e.g. 'Was hältst du von "
                "Frankreich - England?' or 'Hast du was zu Bayern - Dortmund?'), or a screenshot "
                "(free-text tip, bet-builder / accumulator slip, stats sheet, hand-written analysis) "
                "about an UPCOMING match. Your job: give ONE clever, REALISTIC smart bet for the "
                "SINGLE most prominent match. "
                "IMPORTANT BEHAVIOUR: If the fan only ASKS about a match (no concrete bet), treat it "
                "as a request for YOUR expert recommendation and confidently propose your single best "
                "realistic bet for that match. NEVER reveal or hint that the input lacked a concrete "
                "bet. NEVER write meta phrases such as 'da noch keine konkrete Wette im Raum steht', "
                "'keine konkrete Wette', 'da keine Wette vorliegt' or similar — always write as if this "
                "is your own confident analysis. "
                "REALISM RULES: pick a sensible, realistic market that genuinely fits the two "
                "teams' real strength and form. Use realistic odds, typically 1.40–2.60. Do NOT "
                "invent aggressive/absurd bets. "
                "BET-QUALITY RULES (owner, very important): give a SPECIFIC, insightful primary "
                "bet — NOT a lazy generic one. Prefer, depending on your read of the match: "
                "(1) a CONCRETE team to score ('<Team> trifft / <Team> Über 0.5 Tore') when a side "
                "is clearly too strong to be kept scoreless; (2) DOPPELTE CHANCE ('<Team> Doppelte "
                "Chance 1X/X2') when a team realistically cannot lose; (3) HANDICAP ('<Team> "
                "Handicap +1.5') when the underdog at worst loses by one; (4) a goal in the 2nd half "
                "or a team scoring before minute 70; (5) Draw No Bet or a clear match result. State "
                "clearly WHICH team won't lose or WHICH team will surely score. "
                "STRICT: NEVER make a plain full-match 'Über 0.5 Tore' (whole game) the bet — it is "
                "near-certain and worthless alone. A full-match 'Über 0.5 Tore' may ONLY appear as a "
                "SECOND leg in a bet-builder, combined with a strong primary selection (e.g. '<Team> "
                "Doppelte Chance 1X · Über 0.5 Tore'). Team-specific '<Team> Über 0.5 Tore' (that team "
                "scores) IS allowed as a primary bet. "
                "If several selections belong to one match (a bet-builder) COMBINE them into one "
                "market string joined with ' · '. For a multi-match accumulator, pick the single "
                "headline match. Identify the two REAL teams (full names, keep the language used, "
                "e.g. 'Frankreich', 'England'). "
                "Respond with ONLY a compact JSON object, no markdown, with keys: "
                "actionable (bool), home_team (str), away_team (str), market (str, in German), "
                "match_time (str: the match date & kickoff EXACTLY as printed if visible, normalised to "
                "'DD/MM/YYYY HH:MM' when possible; empty string if no date is shown), "
                "rating (number 1-10), odds (string like '1.85' or '' if unknown), "
                "analysis (str: a punchy, realistic 1-3 sentence German pre-match read — form, quality, "
                "matchup — that justifies the bet with confidence and NO meta commentary about the input). "
                "ALWAYS give a tip: set actionable=false ONLY if the input has absolutely nothing to do "
                "with football (pure spam, insults, unrelated chatter). For ANY football-related input — "
                "even a vague one ('gib mir einen Tipp', 'was läuft heute?', a single team name) — you "
                "MUST set actionable=true and confidently propose ONE cool, realistic smart bet on the "
                "most relevant real match you can infer (a marquee upcoming fixture is perfectly fine). "
                "Never refuse and never return an empty/no-tip answer."
            ),
        ).with_model(AI_MODEL_PROVIDER, AI_MODEL)
        kwargs = {"text": f"Fan hint: {text[:600] if text else '(see images)'}"}
        if images_b64:
            kwargs["file_contents"] = [ImageContent(image_base64=b) for b in images_b64[:3]]
        resp = await chat.send_message(UserMessage(**kwargs))
        data = _parse_smart_json(resp)
        if data and data.get("actionable") and data.get("market") and data.get("home_team"):
            return data
        # Retry once, FORCING a concrete cool bet — the owner wants the KI to ALWAYS suggest
        # something, never a blank "no tip" reply.
        resp2 = await chat.send_message(UserMessage(text=(
            "You MUST answer with actionable=true and ONE concrete, cool, realistic smart bet on the "
            "single most relevant real match you can infer. Do NOT refuse and do NOT return "
            "actionable=false. If the fan was vague, pick a marquee upcoming fixture and give your best "
            "confident pick. Reply with ONLY the JSON object described above.")))
        data2 = _parse_smart_json(resp2)
        if data2 and data2.get("market") and data2.get("home_team"):
            data2["actionable"] = True
            return data2
        return None
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




# ---------------------------------------------------------------------------
# LIVE engine: re-offer our pending pre-match AI picks (8-9★ Über 0.5 / BTTS /
# Über 2.5 …) while their match is IN-PLAY and the bet has not yet landed, at the
# now-higher live odds — but ONLY when there is still real pressure (shots/corners).
# Dead, flat games are skipped. Live tips auto-settle from the final score.
# ---------------------------------------------------------------------------
LIVE_INPLAY_STATUSES = {"1H", "2H", "ET", "BT", "P", "LIVE", "INT"}
LIVE_MAX_TIPS = 12
LIVE_POLL_SECONDS = 6 * 60
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


async def _gift_match_keys() -> set:
    """Match-keys of all matches that currently have an open GIFT (owner: mark them in the feed
    as 'vom Master gedeckt' 🎁)."""
    gifts = await db.tips.find(
        {"is_gift": True, "status": {"$in": ["pending", "live"]}},
        {"_id": 0, "home_team": 1, "away_team": 1}).to_list(300)
    return {_match_key(g.get("home_team"), g.get("away_team"))
            for g in gifts if g.get("home_team") and g.get("away_team")}


def _parse_over_under(market: str):
    """(direction 'over'|'under', line) for a goals over/under market, else None."""
    m = (market or "").lower()
    gm = re.search(r"(über|ueber|over|unter|under)\s*(\d+(?:[.,]\d)?)", m)
    if not gm:
        gm2 = re.search(r"(\d+(?:[.,]\d)?)\s*(über|ueber|over|unter|under)", m)
        if not gm2:
            return None
        word, num = gm2.group(2), gm2.group(1)
    else:
        word, num = gm.group(1), gm.group(2)
    direction = "over" if word in ("über", "ueber", "over") else "under"
    try:
        line = float(num.replace(",", "."))
    except ValueError:
        return None
    return direction, line


async def _gift_stance_map() -> dict:
    """Owner 2026-07-30: GIFT tips are the source of truth — NO other AI (Master, statistics,
    mental) may contradict them for the same match. Returns match_key → stance with the sets
    team_over/team_under (_team_core of teams the gift says will/won't produce goals) and the
    lists match_over/match_under (match total lines the gift called over/under)."""
    gifts = await db.tips.find(
        {"is_gift": True, "status": {"$in": ["pending", "live"]}},
        {"_id": 0, "home_team": 1, "away_team": 1, "market": 1}).to_list(300)
    out = {}
    for g in gifts:
        home, away = g.get("home_team") or "", g.get("away_team") or ""
        if not home or not away:
            continue
        pu = _parse_over_under(g.get("market", ""))
        if not pu:
            continue
        direction, line = pu
        key = _match_key(home, away)
        st = out.setdefault(key, {"team_over": set(), "team_under": set(),
                                  "match_over": [], "match_under": []})
        side = _market_team_side(g.get("market", ""), home, away)
        team = home if side == "home" else away if side == "away" else None
        if team:
            (st["team_over"] if direction == "over" else st["team_under"]).add(_team_core(team))
        else:
            (st["match_over"] if direction == "over" else st["match_under"]).append(line)
    return out


def _gift_under_lean(st: dict) -> bool:
    """The gift leans LOW-SCORING for this match (a match-under or any team-under)."""
    return bool(st) and (bool(st["match_under"]) or bool(st["team_under"]))


def _conflicts_with_gift(market: str, home: str, away: str, st: dict) -> bool:
    """True if `market` CONTRADICTS the gift stance `st` for this match (owner rule):
    e.g. gift 'Qarabag unter 2.5' ⇒ block 'Qarabag trifft', 'Qarabag über 2.5', match 'über 4.5'."""
    if not st:
        return False
    ml = (market or "").lower()
    pu = _parse_over_under(market)
    side = _market_team_side(market, home, away)
    team = _team_core(home) if side == "home" else _team_core(away) if side == "away" else None
    scores = any(k in ml for k in ("trifft", "torschütze", "torschutze", "scores", "anytime")) \
        or (pu and pu[0] == "over" and "0.5" in ml)
    noscore = any(k in ml for k in ("trifft nicht", "kein tor", "zu null", "clean sheet", "keine tore")) \
        or (pu and pu[0] == "under" and "0.5" in ml)
    # 1) gift: this team stays LOW → block hyping it to score / any over on it
    if team and team in st["team_under"] and (scores or (pu and pu[0] == "over")):
        return True
    # a team-under also implies a low-scoring lean → block a big MATCH over (e.g. mental Über 4.5)
    if st["team_under"] and team is None and pu and pu[0] == "over" and pu[1] >= 3.5:
        return True
    # 2) gift: this team SCORES → block predicting it won't score
    if team and team in st["team_over"] and noscore:
        return True
    # 3) gift: MATCH under L → block a match over reaching it, and any 'team trifft' hype
    for L in st["match_under"]:
        if pu and pu[0] == "over" and pu[1] >= L - 1:
            return True
        if scores:
            return True
    # 4) gift: MATCH over L → block a match under
    for L in st["match_over"]:
        if pu and pu[0] == "under" and pu[1] <= L + 1:
            return True
    return False


# ── CODE READING (owner 2026-07-30) ────────────────────────────────────────────
# Read SpinBetter's "accumulator of the day" legs and play AGAINST them or NO BET.
def _code_side(market: str, home: str, away: str):
    """Which side a SpinBetter leg refers to: handles 'Team 1/2', 'S1/S2', '1./2.' and names."""
    m = (market or "").lower()
    if re.search(r"team\s*1|(^|[^0-9x])s?1\b|\b1\.", m) and not re.search(r"team\s*2|s?2\b", m):
        return "home"
    if re.search(r"team\s*2|(^|[^0-9x])s?2\b|\b2\.", m):
        return "away"
    return _market_team_side(market, home, away)


def _code_team_total_under(market: str):
    """Detect a TEAM/individual total-UNDER leg. Returns (line, negated) or None.
    'Gesamtzahl 1 1.5 Unter' → (1.5, False); 'Gesamtzahl 2 Unter 2.5 - Nein' → (2.5, True)."""
    m = (market or "").lower()
    if not re.search(r"gesamtzahl|team\s*[12]|individual|einzel", m):
        return None
    if "unter" not in m and "under" not in m:
        return None
    dm = re.search(r"(\d+\.\d+)", m)          # the decimal line (0.5/1.5/2.5…)
    if not dm:
        return None
    line = float(dm.group(1))
    negated = any(k in m for k in ("nein", " no", "- no", "nicht"))
    return (line, negated)


def _code_apply_learn(res: dict) -> dict:
    """If a code-reading pattern has proven to lose too often, force it to NO BET."""
    pat = res.get("pattern")
    if res.get("read") == "counter" and pat:
        verdict, rate, n = learn_verdict("code", pat, raw_bucket=True)
        if verdict == "veto":
            return {"read": "no_bet", "code": res.get("code"), "pattern": pat,
                    "reason": f"Gelernt: Muster verliert zu oft ({int(rate*100)}% aus {n} Spielen) → No Bet."}
        if verdict == "boost":
            res["reason"] = f"{res['reason']} (bewährt: {int(rate*100)}% aus {n})"
    return res


def _code_read_interpret(market: str, home: str, away: str) -> dict:
    """Turn ONE bookmaker accumulator leg into OUR counter-pick or a NO BET (owner rules)."""
    m = (market or "").lower()
    home = home or "Heim"
    away = away or "Gast"
    side = _code_side(market, home, away)
    team = home if side == "home" else away if side == "away" else None

    # (Team-total) SpinBetter bets a TEAM stays low / goes 3+ → owner counter-reads.
    tt = _code_team_total_under(market)
    if tt is not None:
        line, negated = tt
        tgt = team or home
        if negated:
            # "Team Gesamtzahl Unter x.5 – Nein" = they need the team to bang 3+ → we DECKEL it.
            return _code_apply_learn({
                "read": "counter", "our_market": f"{tgt} Unter 3.5 Tore",
                "alt_market": f"{tgt} 1–3 Tore", "code": market, "pattern": "team_total_over_cap",
                "reason": f"Code will {tgt} mit 3+ Toren — das ist selten. Wir deckeln: {tgt} Unter 3.5 Tore.",
                "stars": 7})
        if line <= 2.5:
            # "Team Gesamtzahl Unter 1.5/2.5" = they say the team barely scores → we back it TO score.
            return _code_apply_learn({
                "read": "counter", "our_market": f"{tgt} Über 0.5 Tore",
                "alt_market": "Beide Teams treffen", "code": market, "pattern": "team_total_under_low",
                "reason": f"Code sagt {tgt} trifft kaum ({market}). Wir gehen dagegen: {tgt} Über 0.5 Tore — vor allem zuhause / wenn der Gegner ein wichtigeres Spiel vor der Brust hat.",
                "stars": 7})
        return {"read": "no_bet", "code": market, "pattern": "team_total_under_high",
                "reason": f"Code deckelt {tgt} schon hoch (Unter {line}) — kein Gegenwert. No Bet."}

    # (a) SpinBetter: a team WON'T score (win + 'Über 0.5 – Nein' / clean sheet) → we take that
    #     team TO score / BTTS. "Nicht dass es 0:1 endet."
    if ("0.5" in m) and any(k in m for k in ("nein", "no", "kein", "nicht", "under", "unter")):
        tgt = team or away
        return _code_apply_learn({"read": "counter", "our_market": f"{tgt} trifft (Über 0.5 Tore)",
                "alt_market": "Beide Teams treffen", "code": market, "pattern": "team_scores_counter",
                "reason": f"Code sagt: {tgt} trifft NICHT. Wir gehen dagegen — {tgt} trifft (oder beide treffen). Nicht dass es 0:1 endet.",
                "stars": 7})

    # (b) SpinBetter: early draw / result at ~15. Minute → we expect a goal by then.
    if re.search(r"\b(15|20|30)(th)?\b", m) and any(k in m for k in
            ("unentschieden", "remis", "draw", "ergebnis", "result", "erstes tor", "1. tor", " x ")):
        return _code_apply_learn({"read": "counter", "our_market": "Über 0.5 Tore 1. Halbzeit",
                "code": market, "pattern": "early_goal",
                "reason": "Code erwartet früh noch 0:0/Unentschieden — wir sagen, bis dahin fällt ein Tor: Über 0.5 Tore 1. Halbzeit.",
                "stars": 10})

    # (c) SpinBetter: team scores LATE (last goal 55–90 / 2nd half) → we say it scores BY ~60.
    if any(k in m for k in ("55", "60", "letztes tor", "last goal", "2. halbzeit", "second half", "spät")) \
            and (team or "trifft" in m or "tor" in m):
        tgt = team or home
        return _code_apply_learn({"read": "counter", "our_market": f"{tgt} trifft bis zur 60. Minute",
                "code": market, "pattern": "early_scorer",
                "reason": f"Code sieht {tgt} SPÄT treffen — wir sagen: bis zur 55.–60. Minute ist die Bude drin. Ziemlich sicher.",
                "stars": 8})

    # (d) SpinBetter: match total Über 2.5+ → too loose for us → NO BET.
    ou = _parse_over_under(market)
    if ou and ou[0] == "over" and ou[1] >= 2.5 and team is None:
        return {"read": "no_bet", "code": market, "pattern": "match_over_nobet",
                "reason": "Code gibt Über 2.5+ Tore — zu unsicher für uns. No Bet."}

    # (e) SpinBetter: straight win / double chance / handicap → NO BET ('nicht normal, 1X zu gehen').
    if any(k in m for k in ("sieg", "gewinnt", " win", "1x", "x2", "doppelte", "double chance",
                            "handicap", "1x2")) or re.match(r"^\s*s?[12]\b", m):
        return {"read": "no_bet", "code": market, "pattern": "straight_win_nobet",
                "reason": "Code gibt einen glatten Sieg (1/2/1X). Es ist nicht normal, 1X zu gehen. No Bet."}

    return {"read": "no_bet", "code": market, "pattern": "no_value",
            "reason": "Kein klarer Gegen-Wert. No Bet."}


async def _code_read_scan_images(images_b64: List[str]) -> list:
    """Vision-OCR a trap-bookie boosted/'accumulator of the day' screenshot AND decide our
    counter-read per game in ONE call, following the owner's Code-Reading philosophy."""
    prompt = (
        "These are screenshots of a trap-bookmaker's ready-made / boosted betslips (e.g. 'Accumulator of the day'). "
        "They are built to make the player LOSE. Extract EVERY football (soccer) game and, for each, decide OUR pick "
        "following this exact philosophy (owner's rules):\n"
        "1) Keep ONLY what is LOGICAL / clearly makes sense. Prefer one safe single over combos. If nothing looks logical → NO BET.\n"
        "2) If they cap a TEAM low or back a team to just score (e.g. 'Team Total Under 1.5', 'Team Over 0.5', "
        "'Team total goals Over 0.5') → KEEP '<Team> Über 0.5 Tore' as our safe single — a team scoring at least once "
        "is usually the logical part. Only choose NO BET here if that team faces a very strong defensive favourite likely to shut them out.\n"
        "3) If they NEED a team to score 3+ (e.g. 'Team Total Under 2.5 – No') → cap them: '<Team> Unter 3.5 Tore'.\n"
        "4) A WHOLE-MATCH total like 'Over 2.5' / 'Under 2.5' with no clear edge → NO BET.\n"
        "5) Straight win / 1X2 / double chance / handicap → NO BET (we NEVER buy a plain win/1X).\n"
        "6) ANY first-half / half-time goals bet (e.g. '1st half Over 0.5', '1. Halbzeit Über 0.5', 'HT Over 0.5'), "
        "OR an early draw/result at minute 15-30 → KEEP 'Über 0.5 Tore 1. Halbzeit' (they expect an early goal — usually a safe single). stars 8-10.\n"
        "7) A team's LAST goal 55-90' / scores late → '<Team> trifft bis zur 60. Minute'.\n"
        "8) 'Team does NOT score' / 'Over 0.5 – No' → play against: '<Team> trifft (Über 0.5 Tore)'.\n"
        "Identify WHICH team a total refers to and put the team name into our_market. "
        "PRESERVE period info in code_market (e.g. '1. Halbzeit', '1st half', 'HT', minute). "
        "reason: a SHORT but CONCRETE explanation in GERMAN of WHY this pick is safe — name the real football reason "
        "(z.B. Heimteam extrem torgefährlich und trifft fast jede erste Halbzeit; Gegner hat in wenigen Tagen ein "
        "wichtigeres Spiel und rotiert; Team trifft in fast jedem Spiel). Nicht nur die Regel wiederholen. "
        "Bei NO BET: erkläre, warum es nicht sicher genug ist. stars: 6-10 for a counter pick, 0 for no_bet.\n"
        "Reply ONLY JSON: {\"legs\":[{\"home\":\"\",\"away\":\"\",\"league\":\"\",\"kickoff\":\"\","
        "\"code_market\":\"\",\"read\":\"counter|no_bet\",\"our_market\":\"\",\"reason\":\"\",\"stars\":0}]}")
    chat = LlmChat(api_key=EMERGENT_LLM_KEY, session_id=f"coderead-{uuid.uuid4()}",
                   system_message="You are TipJar's Code-Reader. You read trap-bookie slips and give ONE safe counter-pick per game or NO BET. Output strict JSON."
                   ).with_model(AI_MODEL_PROVIDER, AI_MODEL)
    resp = await chat.send_message(UserMessage(
        text=prompt, file_contents=[ImageContent(image_base64=b) for b in images_b64[:4]]))
    try:
        data = json.loads(re.sub(r"^```json|^```|```$", "", (resp or "").strip(), flags=re.M))
        return data.get("legs", []) if isinstance(data, dict) else []
    except Exception:
        logger.warning(f"code-read scan parse failed: {(resp or '')[:200]}")
        return []


@api_router.get("/code-reading")
async def code_reading():
    """The Code-Reading channel: our counter-reads of SpinBetter's accumulator of the day."""
    now = datetime.now(timezone.utc).isoformat()
    reads = await db.code_reads.find(
        {"expires_at": {"$gt": now}}, {"_id": 0}).sort("created_at", -1).to_list(60)
    return {"count": len(reads), "reads": reads}


_CR_SCAN_JOBS: dict = {}  # job_id -> {status, scanned, reads, note/error}


async def _run_code_scan(job_id: str, images: list):
    """Background worker: OCR + interpret + store (kept off the 60s request path)."""
    try:
        legs = await _code_read_scan_images(images)
        if not legs:
            _CR_SCAN_JOBS[job_id] = {"status": "done", "scanned": 0, "reads": 0,
                                     "note": "Keine Fußball-Legs erkannt (oder LLM-Budget)."}
            return
        now = datetime.now(timezone.utc)
        day = _berlin_now().date().isoformat()
        stored = []
        for lg in legs:
            home, away = (lg.get("home") or "").strip(), (lg.get("away") or "").strip()
            market = (lg.get("code_market") or lg.get("market") or "").strip()
            if not (home and away):
                continue
            await db.code_reads.delete_many({"day": day, "home": home, "away": away, "outcome": {"$exists": False}})
            read = lg.get("read") if lg.get("read") in ("counter", "no_bet") else None
            if read:
                our_market = (lg.get("our_market") or "").strip() or None
                if read == "counter" and not our_market:
                    read = None
            if read:
                try:
                    stars = max(0, min(10, int(lg.get("stars") or (7 if read == "counter" else 0))))
                except (ValueError, TypeError):
                    stars = 7 if read == "counter" else 0
                interp = {"read": read, "our_market": (lg.get("our_market") or "").strip() or None,
                          "alt_market": None, "reason": (lg.get("reason") or "").strip() or "—",
                          "pattern": f"ai_{read}", "stars": stars}
                interp = _code_apply_learn(interp)
            else:
                if not market:
                    continue
                interp = _code_read_interpret(market, home, away)
            doc = {
                "id": f"cr-{uuid.uuid4().hex[:10]}", "day": day,
                "home": home, "away": away, "league": lg.get("league") or "",
                "kickoff": lg.get("kickoff") or "", "code_market": market,
                "code_odds": lg.get("odds") or "",
                "read": interp["read"], "our_market": interp.get("our_market"),
                "alt_market": interp.get("alt_market"), "reason": interp["reason"],
                "pattern": interp.get("pattern"), "stars": interp.get("stars", 0),
                "created_at": now.isoformat(),
                "expires_at": (now + timedelta(hours=30)).isoformat(),
            }
            await db.code_reads.insert_one({k: v for k, v in doc.items() if k != "_id"})
            stored.append(doc)
        _CR_SCAN_JOBS[job_id] = {"status": "done", "scanned": len(legs), "reads": len(stored)}
    except Exception as e:
        logger.error(f"code scan job {job_id} failed: {e}")
        _CR_SCAN_JOBS[job_id] = {"status": "error", "error": str(e)[:200]}
    # keep the jobs dict small
    if len(_CR_SCAN_JOBS) > 50:
        for k in list(_CR_SCAN_JOBS)[:-25]:
            _CR_SCAN_JOBS.pop(k, None)


@api_router.post("/admin/code-reading/scan")
async def admin_code_reading_scan(payload: dict, admin: dict = Depends(require_admin)):
    """Kick off an async scan (avoids the 60s proxy timeout for multi-image Vision calls)."""
    images = payload.get("images") or []
    if not images:
        raise HTTPException(status_code=400, detail="no images")
    job_id = uuid.uuid4().hex[:12]
    _CR_SCAN_JOBS[job_id] = {"status": "processing"}
    asyncio.create_task(_run_code_scan(job_id, images))
    return {"job_id": job_id, "status": "processing"}


@api_router.get("/admin/code-reading/scan-status/{job_id}")
async def admin_code_reading_scan_status(job_id: str, admin: dict = Depends(require_admin)):
    return _CR_SCAN_JOBS.get(job_id, {"status": "unknown"})


async def _grade_code_our_market(our_market: str, home: str, away: str, fx: dict):
    """Grade OUR code-reading counter-pick against the real finished fixture.
    Returns 'won' / 'lost' / None (undecidable)."""
    m = (our_market or "").lower()
    mn = _norm(our_market)
    hg, ag = fx.get("home_goals"), fx.get("away_goals")
    if hg is None or ag is None:
        return None
    if "halbzeit" in m:                       # "Über 0.5 Tore 1. Halbzeit" (total, orientation-free)
        hh, ha = fx.get("ht_home"), fx.get("ht_away")
        if hh is None or ha is None:
            return None
        return "won" if (hh + ha) >= 1 else "lost"
    # map OUR home/away onto the fixture's orientation
    if _teams_match(fx.get("home_name", ""), home) or _teams_match(fx.get("away_name", ""), away):
        gh, ga = hg, ag
    else:
        gh, ga = ag, hg
    tg = gh if (_norm(home) and _norm(home) in mn) else (ga if (_norm(away) and _norm(away) in mn) else None)
    if tg is not None:
        if "unter 3.5" in m or "1–3" in m or "1-3" in m:
            return "won" if tg <= 3 else "lost"
        if "über 0.5" in m or "uber 0.5" in m or "trifft" in m:
            return "won" if tg >= 1 else "lost"
    try:
        out = await judge_market(our_market, home, away, hg, ag)
        return out if out in ("won", "lost") else None
    except Exception:
        return None


async def settle_code_reads() -> dict:
    """Auto-settle open code-reading counter-picks against real results (owner: 'Ergebnisse gucken')."""
    if not API_FOOTBALL_KEY:
        return {"ok": False, "settled": 0}
    now = datetime.now(timezone.utc)
    reads = await db.code_reads.find(
        {"read": "counter", "outcome": {"$exists": False}, "our_market": {"$nin": [None, ""]}},
        {"_id": 0}).sort("created_at", 1).to_list(120)
    settled = 0
    date_cache: dict = {}
    for r in reads:
        if _api_quota_exhausted():
            break
        if r.get("cr_settle_attempts", 0) >= 8:
            continue
        ko = _parse_kickoff(r.get("kickoff"))
        try:
            created = datetime.fromisoformat(r["created_at"])
        except Exception:
            created = now
        ref = ko or created
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=timezone.utc)
        if now - ref < timedelta(hours=2):
            continue  # match not finished yet
        home, away = r["home"], r["away"]
        tid = await resolve_team_id(home)
        oid = await resolve_team_id(away)
        dates = sorted({ref.date().isoformat(), (ref + timedelta(days=1)).date().isoformat(),
                        created.date().isoformat()})
        fx = find_finished_fixture(tid, away, dates, oid) if tid else None
        if not fx and oid:
            fx = find_finished_fixture(oid, home, dates, tid)
        if not fx:
            fx = _datescan_fixture(home, away, dates, date_cache)
        if not fx:
            await db.code_reads.update_one({"id": r["id"]}, {"$inc": {"cr_settle_attempts": 1}})
            continue
        outcome = await _grade_code_our_market(r["our_market"], home, away, fx)
        if outcome not in ("won", "lost"):
            await db.code_reads.update_one({"id": r["id"]}, {"$inc": {"cr_settle_attempts": 1}})
            continue
        await db.code_reads.update_one({"id": r["id"]}, {"$set": {
            "outcome": outcome, "score": f"{fx.get('home_goals')}-{fx.get('away_goals')}",
            "settled_at": now.isoformat()}})
        settled += 1
    return {"ok": True, "settled": settled, "checked": len(reads)}


async def learning_loop():
    """Owner 2026-06: keep all 3 systems (master/hq/code) learning from REAL results."""
    await asyncio.sleep(60)
    try:
        await refresh_learning()
    except Exception as e:
        logger.error(f"initial refresh_learning error: {e}")
    while True:
        try:
            await settle_code_reads()
            await refresh_learning()
        except Exception as e:
            logger.error(f"learning_loop error: {e}")
        await asyncio.sleep(1200)  # every 20 min


@api_router.get("/learning/stats")
async def learning_stats():
    """Honest hit-rate per market pattern & system, derived from settled results."""
    def _fmt(sysmap):
        rows = [{"pattern": b, "won": s["won"], "lost": s["lost"], "n": s["n"],
                 "rate": s["rate"],
                 "verdict": ("veto" if s["n"] >= 6 and s["rate"] < 0.40
                             else "boost" if s["n"] >= 6 and s["rate"] >= 0.70 else "ok")}
                for b, s in sysmap.items() if s["n"] > 0]
        return sorted(rows, key=lambda r: (-r["n"], -r["rate"]))
    return {"master": _fmt(_LEARN.get("master", {})),
            "hq": _fmt(_LEARN.get("hq", {})),
            "code": _fmt(_LEARN.get("code", {})),
            "min_n": 6, "veto_rate": 0.40}


@api_router.post("/admin/learning/refresh")
async def admin_learning_refresh(admin: dict = Depends(require_admin)):
    cr = await settle_code_reads()
    await refresh_learning()
    return {"ok": True, "code_reads": cr, "stats": _LEARN}


@api_router.post("/admin/code-reading/manual")
async def admin_code_reading_manual(payload: dict, admin: dict = Depends(require_admin)):
    """Admin writes ONE code-read by hand (single selection, not a slip)."""
    home = (payload.get("home") or "").strip()
    away = (payload.get("away") or "").strip()
    if not (home and away):
        raise HTTPException(status_code=400, detail="home and away required")
    read = payload.get("read") if payload.get("read") in ("counter", "no_bet") else "counter"
    try:
        stars = max(0, min(10, int(payload.get("stars") or 0)))
    except (ValueError, TypeError):
        stars = 0
    now = datetime.now(timezone.utc)
    doc = {
        "id": f"cr-{uuid.uuid4().hex[:10]}", "day": _berlin_now().date().isoformat(),
        "home": home, "away": away, "league": (payload.get("league") or "").strip(),
        "kickoff": (payload.get("kickoff") or "").strip(),
        "code_market": (payload.get("code_market") or "").strip(),
        "code_odds": (payload.get("code_odds") or "").strip(),
        "read": read,
        "our_market": ((payload.get("our_market") or "").strip() or None) if read == "counter" else None,
        "alt_market": (payload.get("alt_market") or "").strip() or None,
        "reason": (payload.get("reason") or "").strip(),
        "pattern": "manual", "stars": stars,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=30)).isoformat(),
    }
    await db.code_reads.insert_one({k: v for k, v in doc.items() if k != "_id"})
    return {"ok": True, "read": doc}


@api_router.delete("/admin/code-reading/{read_id}")
async def admin_code_reading_delete(read_id: str, admin: dict = Depends(require_admin)):
    res = await db.code_reads.delete_one({"id": read_id})
    return {"ok": True, "deleted": res.deleted_count}



def _live_bet_landed(market: str, hg, ag, home: str, away: str):
    """True=won, False=not yet/lost, None=not a goal-progress market (skip)."""
    m = (market or "").lower()
    hg, ag = hg or 0, ag or 0
    total = hg + ag
    # Asian Über 2.0 Tore ("Banger"): won at 3+ goals, PUSH (stake back → void) at
    # exactly 2 goals, lost at <= 1 goal. None here means "push/void" at full-time.
    if "asian" in m and ("über 2.0" in m or "über 2 tore" in m or "over 2.0" in m):
        if total >= 3:
            return True
        if total == 2:
            return None
        return False
    # Asian Über 1.0 (team or match): win as soon as the relevant goals reach 2 (exactly-1
    # push and 0-loss are resolved at full-time; live only settles WINS early).
    if "asian" in m and re.search(r"(über|over)\s*1(\.0)?(?![.\d])", m) and "1.5" not in m:
        side = _market_team_side(market, home, away)
        g = hg if side == "home" else (ag if side == "away" else total)
        return True if g >= 2 else False
    if any(k in m for k in ("draw no bet", "doppelte chance", "genaues ergebnis", "unentschieden")):
        return None
    if "über 2.5" in m and ("beide" in m or "btts" in m):
        return total >= 3 and hg >= 1 and ag >= 1
    if "beide teams treffen" in m or "btts" in m:
        return hg >= 1 and ag >= 1
    # Generic FULL-MATCH over-line "Über N.5 Tore" (N up to any number → goal-fest bangers
    # like 'Über 3.5/4.5/6.5 Tore'). Team-specific lines fall through to the team branch.
    _gm = re.search(r"über\s+(\d+)\.5", m)
    if _gm and "über 0.5" not in m and _market_team_side(market, home, away) is None:
        return total >= int(_gm.group(1)) + 1
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
    if "asian" in m and ("über 2.0" in m or "über 2 tore" in m):
        # Asian Über 2.0: full win at 3+ goals; the exact-2 push protects part of the
        # stake, so the effective win probability is a bit higher than a hard "3+" line.
        needed = max(1, 3 - int(total_goals or 0))
        p = min(0.96, _poisson_at_least(needed, RATE_TOTAL * rem) + 0.10)
    elif gm and "über 0.5" not in m and "beide" not in m and "btts" not in m:
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


def _live_red_cards(stats) -> int:
    """Red cards currently on the pitch — read from the SAME live statistics payload
    (no extra API call). Owner 2026-07-30: a red card can break the flow of goals."""
    reds = 0
    for team in (stats or []):
        for s in (team.get("statistics") or []):
            typ = (s.get("type") or "").lower()
            if "red card" in typ:
                val = s.get("value")
                if isinstance(val, str):
                    val = int(re.sub(r"[^0-9]", "", val) or 0)
                reds += val or 0
    return reds


_KO_LIVE_KEYWORDS = QUAL_KEYWORDS + ("cup", "pokal", "coupe", "copa", "coppa", "beker",
                                     "knockout", "k.o", "supercup", "super cup", "trophy")


def _is_knockout_label(*vals) -> bool:
    txt = " ".join(str(v or "") for v in vals).lower()
    return any(k in txt for k in _KO_LIVE_KEYWORDS)


def _live_overline_penalty(gh: int, ag: int, reds: int, league_label: str, country: str):
    """Owner 2026-07-30: 'ein Aggregat 5:1 mit roter Karte kann das Spiel früher enden.'
    A live OVER-line ('needs another goal') is riskier when the game is a decided blowout,
    when it is a knockout tie (leading side protects the aggregate) or after a red card.
    Returns (star_penalty, reasons[]). Balanced, open, non-KO games get NO penalty — some
    Über-4.5 spots really are safe."""
    penalty, reasons = 0.0, []
    margin = abs((gh or 0) - (ag or 0))
    if margin >= 3:
        penalty += 2.0
        reasons.append("klarer Vorsprung — die führende Mannschaft verwaltet oft")
    elif margin == 2:
        penalty += 0.8
    if reds >= 1:
        penalty += 1.0
        reasons.append("eine rote Karte kann den Torfluss brechen")
    if _is_knockout_label(league_label, country):
        penalty += 1.5
        reasons.append("K.o.-Duell — bei entschiedenem Aggregat wird das Spiel oft heruntergespielt")
    return penalty, reasons


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
    gh, ga = _reg_goals(fx)
    gh, ga = gh or 0, ga or 0
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
    # Backfill a category on any live pick that predates the Banker/Value/Banger split so
    # the 3 Live sub-tabs populate immediately (banger picks already carry theirs).
    for lt in existing:
        if lt.get("category") in ("banker", "value", "banger"):
            continue
        try:
            _od = float(str(lt.get("odds") or "0").replace(",", "."))
        except Exception:
            _od = 0.0
        _cat = "banger" if (lt.get("id", "").startswith("hqlive-banger-")) else ("banker" if (_od < 1.60 and _is_banker_safe(lt.get("market"))) else "value")
        await db.tips.update_one({"id": lt["id"]}, {"$set": {"category": _cat}})
        lt["category"] = _cat
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

    # 1b) EARLY-SETTLE — any PENDING single over-goals / BTTS pick (expert bots, HQ-auto,
    #     members) is moved straight to WON the moment its live match reaches the required
    #     goals (owner 2026-07: "über 2.5 / beide treffen → sofort abrechnen, sobald 3 Tore
    #     fallen oder beide treffen"). Goals only rise, so an early WIN is irreversible. We
    #     never LOSE early — that still waits for full time.
    early = 0
    if live:
        cand = await db.tips.find(
            {"status": {"$in": ["pending", "live"]}, "is_parlay": {"$ne": True},
             "home_team": {"$nin": ["", None]}, "away_team": {"$nin": ["", None]}},
            {"_id": 0, "id": 1, "market": 1, "home_team": 1, "away_team": 1,
             "fixture_id": 1}).to_list(3000)
        for t in cand:
            m = (t.get("market") or "").lower()
            if not ("über" in m or "over" in m or "beide" in m or "btts" in m):
                continue
            side = _market_team_side(t.get("market"), t["home_team"], t["away_team"])
            # team-specific over ≥1.5 lines aren't reliably early-gradable from total goals
            if side is not None and re.search(r"(über|over)\s*[1-9]\.5", m):
                continue
            fx = live_by_id.get(str(t.get("fixture_id") or "")) or _find_live_fixture(live, t["home_team"], t["away_team"])
            if not fx:
                continue
            short = ((fx.get("fixture") or {}).get("status") or {}).get("short")
            if short not in LIVE_STATUSES:
                continue
            hg, ag = _align_goals(fx, t["home_team"])
            if _live_bet_landed(t.get("market"), hg, ag, t["home_team"], t["away_team"]) is True:
                minute = ((fx.get("fixture") or {}).get("status") or {}).get("elapsed") or 0
                await db.tips.update_one({"id": t["id"]}, {"$set": {
                    "status": "won", "final_home": hg, "final_away": ag,
                    "live_score": f"{hg}:{ag}", "live_minute": minute,
                    "settled_by": "auto-live-early", "settled_at": now}})
                early += 1
    if early:
        logger.info(f"Early-settled {early} live over/BTTS tips as WON")

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
                "category": ("banker" if (odd < 1.60 and _is_banker_safe(t.get("market"))) else "value"),
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
                "category": ("banker" if (odd < 1.60 and _is_banker_safe(t.get("market"))) else "value"),
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

    # 4) BANGER picks (owner, v2) — genuine 10★ in-play "goal-fest" bets.
    #    • Goal-fest continuation (total >= 3): the game is already a shootout (France–England
    #      4:6 style) → ride the momentum with a HIGHER over-line that's still very likely.
    #    • Open game (total <= 1) under heavy pressure → "Asian Über 2.0 Tore" (money back at
    #      exactly 2 goals; recovery angle if a side trails).
    #    Low-scoring/defensive leagues (Brazil especially — nothing happens, then a stoppage-time
    #    goal) are SKIPPED: over-bangers there are traps.
    banger_calls = 0
    for fx in live:
        if posted >= LIVE_MAX_TIPS or banger_calls >= max(4, LIVE_STAT_CALL_CAP // 2):
            break
        fid = str((fx.get("fixture") or {}).get("id") or "")
        if not fid:
            continue
        banger_id = f"hqlive-banger-{fid}"
        if await db.tips.find_one({"id": banger_id, "status": "live"}, {"_id": 1}):
            continue
        minute = ((fx.get("fixture") or {}).get("status") or {}).get("elapsed") or 0
        if minute < 15 or minute > 72:
            continue
        teams = fx.get("teams") or {}
        home = ((teams.get("home") or {}).get("name")) or ""
        away = ((teams.get("away") or {}).get("name")) or ""
        if not home or not away or _team_or_league_blocked(home, away, ""):
            continue
        goals = fx.get("goals") or {}
        gh, ag = goals.get("home") or 0, goals.get("away") or 0
        total = gh + ag
        if total == 2:
            continue  # no clean banger line at exactly 2 goals
        stats = _apifootball("/fixtures/statistics", {"fixture": fid})
        stat_calls += 1
        banger_calls += 1
        sog, corners, shots = _live_stat_totals(stats)
        # STRICT pressure gate — a banger must be a genuinely likely goal-fest.
        strong = (sog >= 3 or corners >= 6 or shots >= 10) if minute <= 55 else (sog >= 5 or corners >= 9)
        if not strong:
            continue
        if total >= 3:
            # GOAL-FEST continuation → pick the highest over-line still in the banger window.
            best = None
            for line in (total + 1, total):
                m_try = f"Über {line}.5 Tore"
                o_try = _live_odd(m_try, minute, total)
                if 1.40 <= o_try <= 3.20:
                    best = (m_try, o_try)
                    break
            if not best:
                continue
            market, odd = best
            # Owner 2026-07-30: a live "needs another goal" bet is NEVER a 10★ lock — a red
            # card or time-wasting kills it (e.g. Austria Über 4.5 died at 0:4→game shut down).
            # Rating is HONEST (from the live odds) and capped at 7★, THEN context-penalised:
            # a decided blowout / knockout tie / red card lowers it further (owner: "aggregate
            # 5:1 mit roter Karte kann das Spiel früher enden"). Open, balanced games keep 7★.
            wp = min(0.90, 1.0 / odd)
            rating = min(7.0, max(3.0, round(wp * 10, 1)))
            reds = _live_red_cards(stats)
            pen, reasons = _live_overline_penalty(
                gh, ag, reds, _fixture_league_label(fx), _fixture_country(fx))
            if pen > 0:
                rating = max(2.5, round(rating - pen, 1))
            if rating < 3.0:
                continue  # too many danger signals → don't offer this over-line at all
            warn = (" Achtung: " + "; ".join(reasons) + ".") if reasons else ""
            note = (f"Tor-Festival! Schon {total} Tore gefallen — das Spiel ist offen und schnell. "
                    f"ABER: live nie eine Bank — eine rote Karte oder Zeitspiel kann es kippen.{warn}")
        else:
            # OPEN game (0 or 1 goal) → Asian Über 2.0 (money back at exactly 2 goals).
            market = "Asian Über 2.0 Tore"
            odd = _live_odd(market, minute, total)
            if odd < 1.40 or odd > 2.60:
                continue
            # money-back-at-2 insurance → a touch safer than the raw prob, still capped at 7★.
            wp = min(0.90, 1.0 / odd + 0.05)
            rating = min(7.0, max(3.0, round(wp * 10, 1)))
            if total == 1:
                trailing = away if gh > ag else home
                note = (f"{trailing} liegt zurück und drückt auf den Ausgleich — bei GENAU 2 Toren "
                        f"gibt's den Einsatz zurück (Asian-Absicherung).")
            else:
                note = "Beide drücken bei 0:0 — bei GENAU 2 Toren gibt's den Einsatz zurück (Asian-Absicherung)."
        analysis = (
            f"BANGER ({minute}'): {market} — Stand {gh}:{ag}. {note} "
            f"Druck: {sog} Schüsse aufs Tor · {corners} Ecken. Live zu {odd}. "
            f"Timing: am besten sofort spielen, solange die Quote hoch ist."
        )
        await db.tips.update_one({"id": banger_id}, {
            "$set": {
                "market": market, "odds": f"{odd:.2f}", "ai_rating": rating,
                "ai_analysis": analysis, "status": "live", "win_prob": wp,
                "category": "banger",
                "league": _fixture_league_label(fx), "country": _fixture_country(fx),
                "league_code": "", "live_minute": minute, "live_score": f"{gh}:{ag}",
                "updated_at": now,
            },
            "$setOnInsert": {
                "id": banger_id, "user_id": hq["id"], "username": "TipJarHQ",
                "raw_text": "", "image_path": None, "home_team": home, "away_team": away,
                "match_time": ((fx.get("fixture") or {}).get("date") or ""),
                "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
                "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
                "source": "hq-live", "fixture_id": fid, "created_at": now,
            },
        }, upsert=True)
        posted += 1
        logger.info(f"LIVE banger: {home} vs {away} — {market} @ {odd} ({minute}', {gh}:{ag})")

    # 5) LIVE SICHERHEITS-KOMBI (owner-style) — bundle 2-4 ALREADY-secured over-legs from
    #    different in-play games into ONE ~1.5 combo (exactly the owner's winning slips). An
    #    over-line, once met, can never be un-won (goals only go up) → every leg is locked
    #    and the whole combo is a genuine banker. Rebuilt only when no active combo exists.
    #    No stat calls needed → quota-free. Settles via settle_multimatch_parlays at FT.
    has_active_kombi = await db.tips.find_one(
        {"source": "hq-live", "is_parlay": True, "status": "live",
         "id": {"$regex": "^hqlive-kombi-"}}, {"_id": 1})
    if not has_active_kombi and posted < LIVE_MAX_TIPS:
        cands, seen_fx = [], set()
        for fx in live:
            fid = str((fx.get("fixture") or {}).get("id") or "")
            if not fid or fid in seen_fx:
                continue
            minute = ((fx.get("fixture") or {}).get("status") or {}).get("elapsed") or 0
            if minute < 25 or minute > 87:
                continue
            teams = fx.get("teams") or {}
            home = ((teams.get("home") or {}).get("name")) or ""
            away = ((teams.get("away") or {}).get("name")) or ""
            if not home or not away or _team_or_league_blocked(home, away, ""):
                continue
            g = fx.get("goals") or {}
            total = (g.get("home") or 0) + (g.get("away") or 0)
            if total < 1:
                continue  # only ALREADY-secured lines → the leg is locked
            if total >= 3:
                mk, odd = "Über 2.5 Tore", 1.22
            elif total >= 2:
                mk, odd = "Über 1.5 Tore", 1.18
            else:
                mk, odd = "Über 0.5 Tore", 1.13
            seen_fx.add(fid)
            cands.append({
                "match": f"{home} \u2013 {away}",
                "league": _fixture_league_label(fx),
                "kickoff": ((fx.get("fixture") or {}).get("date") or ""),
                "selections": [mk], "sel_odds": [f"{odd:.2f}"], "_odd": odd,
            })
        cands.sort(key=lambda c: c["_odd"])  # safest first
        chosen, prod = [], 1.0
        for c in cands:
            chosen.append(c)
            prod *= c["_odd"]
            if len(chosen) >= 4 or (len(chosen) >= 3 and prod >= 1.45):
                break
        if len(chosen) >= 2 and prod >= 1.28:
            total_odds = round(prod, 2)
            for c in chosen:
                c.pop("_odd", None)
            analysis = (
                f"Live Sicherheits-Kombi ({len(chosen)} Legs): nahezu sichere Über-Wetten aus "
                f"laufenden Spielen — jede Linie ist bereits erfüllt und kann nicht mehr verloren "
                f"gehen. Gesamtquote {total_odds}. Am besten sofort spielen, solange die Spiele laufen."
            )
            await db.tips.insert_one({
                "id": f"hqlive-kombi-{int(now_dt.timestamp())}",
                "user_id": hq["id"], "username": "TipJarHQ",
                "raw_text": "", "image_path": None, "image_paths": [],
                "home_team": "", "away_team": "", "match_time": "Multibet",
                "country": "", "league": "", "market": f"{len(chosen)}er Live-Kombi",
                "odds": f"{total_odds:.2f}", "ai_rating": 9.0, "ai_analysis": analysis,
                "legs": chosen, "is_parlay": True, "stake": "", "potential_return": "",
                "status": "live", "category": "banker", "source": "hq-live",
                "live_kombi": True, "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
                "created_at": now,
            })
            posted += 1
            logger.info(f"LIVE Sicherheits-Kombi: {len(chosen)} legs @ {total_odds}")

    return {"posted": posted, "closed": closed, "live": len(live)}




# The Live CHANNEL is decided at post time (create_tip: posted while the match is
# in-play). This loop does NOT move tips between channels — it only ANNOTATES any
# non-finished single-match tip with its current live minute + score (live_state), so
# the red LIVE badge can appear everywhere a tipped game is running. When a match ends
# the annotation is cleared.
MEMBER_LIVE_POLL_SECONDS = 90


def _is_member_tip(t: dict) -> bool:
    """A pick posted by a real human member (not KI/HQ)."""
    return (t.get("source") not in ("hq-auto", "hq-live", "hq-system", "smart", "hq-master")
            and t.get("username") not in ("TipJarHQ", "TipJarHQ System"))


def _tip_match_teams(t: dict):
    """Home/away teams for a tip — the canonical (Latin) names when known, else the raw
    fields, else parsed from a single-game parlay's leg ("A – B"). Preferring the Latin
    names makes live-score / settlement / consensus matching work for Greek-named tips.
    Returns (None, None) for multi-game parlays."""
    home = t.get("home_team_latin") or t.get("home_team")
    away = t.get("away_team_latin") or t.get("away_team")
    if home and away:
        return home, away
    legs = t.get("legs") or []
    if len(legs) == 1:
        mt = legs[0].get("match") or ""
        for sep in (" \u2013 ", " - ", " vs ", " v "):
            if sep in mt:
                a, b = mt.split(sep, 1)
                return a.strip(), b.strip()
    return None, None


def _leg_teams(leg: dict):
    """Parse (home, away) from a parlay leg's \"A – B\" match string."""
    mt = (leg or {}).get("match") or ""
    for sep in (" \u2013 ", " - ", " vs ", " v "):
        if sep in mt:
            a, b = mt.split(sep, 1)
            return a.strip(), b.strip()
    return None, None


def _parlay_live_fixture(live, legs):
    """For a MULTI-game parlay: return the first leg's fixture that is currently in-play
    (so an in-play treble is routed to the LIVE area, not Community)."""
    for lg in (legs or []):
        lh, la = _leg_teams(lg)
        if lh and la:
            fx = _find_live_fixture(live, lh, la)
            if fx:
                return fx
    return None


def _live_pick_in_danger(market, kind, gh, ga, minute) -> bool:
    """Heuristic: is a goals/result pick clearly IN TROUBLE given the LIVE score + minute?
    Conservative — only fires when the pick is unlikely to come good in the time left, so
    a 'banker' Über-1.5 on a 0-0 at the 80' stops pretending to be a safe banker (owner)."""
    if minute is None:
        return False
    m = (market or "").lower()
    k = (kind or "").lower()
    gh, ga = gh or 0, ga or 0
    total = gh + ga
    late = minute >= 70
    verylate = minute >= 80
    # Over X.5 total goals ("Über 2.5 Tore"). Team-named lines fall back to the match
    # total (safe side: if the match already cleared the line, it's not "in danger").
    gm = re.search(r"über\s+(\d+)\.5", m)
    if gm and "halbzeit" not in m and " hz" not in m:
        remaining = (int(gm.group(1)) + 1) - total
        if remaining <= 0:
            return False
        return (remaining >= 2 and late) or (remaining >= 1 and verylate)
    if ("über 0.5" in m or "over 0.5" in m) and "halbzeit" not in m:
        return total < 1 and verylate
    if ("über 1.0" in m or "over 1.0" in m) and "halbzeit" not in m:
        return total < 2 and verylate
    if k == "btts" or "beide teams treffen" in m:
        return (gh == 0 or ga == 0) and verylate
    losing_home, losing_away = ga > gh, gh > ga
    if k == "res_1" or "heimsieg" in m:
        return losing_home and late
    if k == "res_2" or "auswärtssieg" in m or "away win" in m:
        return losing_away and late
    if k == "dc_1x" or " 1x" in f" {m}":
        return losing_home and verylate
    if k == "dc_x2" or " x2" in f" {m}":
        return losing_away and verylate
    return False


def _derate_fields(t: dict, danger: bool) -> dict:
    """Return the $set fields that down-rate (or restore) a single-match pick whose live
    state has turned against it: strip the 'banker' category and drop the star rating while
    it is in danger; put both back if the game turns and the pick recovers."""
    upd = {}
    cur_cat = t.get("category")
    cur_rating = t.get("ai_rating")
    if danger:
        if not t.get("live_danger"):
            if t.get("category_orig") is None and cur_cat is not None:
                upd["category_orig"] = cur_cat
            if t.get("ai_rating_orig") is None and cur_rating is not None:
                upd["ai_rating_orig"] = cur_rating
            upd["live_danger"] = True
            if cur_cat == "banker":
                upd["category"] = "risk"
            try:
                if cur_rating is None or float(cur_rating) > 3.0:
                    upd["ai_rating"] = 3.0
            except (TypeError, ValueError):
                pass
    elif t.get("live_danger"):
        upd["live_danger"] = False
        if t.get("category_orig") is not None:
            upd["category"] = t["category_orig"]
        if t.get("ai_rating_orig") is not None:
            upd["ai_rating"] = t["ai_rating_orig"]
    return upd


async def live_annotate_sync() -> dict:
    if not API_FOOTBALL_KEY:
        return {"annotated": 0, "cleared": 0, "to_live": 0}
    live = await asyncio.to_thread(_apifootball, "/fixtures", {"live": "all"}) or []
    _live_proj = {"_id": 0, "id": 1, "home_team": 1, "away_team": 1, "live_state": 1, "match_time": 1,
                  "is_parlay": 1, "source": 1, "username": 1, "status": 1, "legs": 1,
                  "market": 1, "kind": 1, "category": 1, "ai_rating": 1,
                  "home_team_latin": 1, "away_team_latin": 1,
                  "category_orig": 1, "ai_rating_orig": 1, "live_danger": 1}
    tips = await db.tips.find(
        {"status": {"$in": ["pending", "live"]},
         "home_team": {"$nin": ["", None]}, "away_team": {"$nin": ["", None]}},
        _live_proj).to_list(1500)
    # single-game member parlays too (home_team empty, teams live inside the one leg)
    parlays = await db.tips.find(
        {"status": {"$in": ["pending", "live"]}, "is_parlay": True,
         "$or": [{"home_team": {"$in": ["", None]}}, {"away_team": {"$in": ["", None]}}]},
        _live_proj).to_list(1500)
    annotated = cleared = to_live = 0
    now_utc = datetime.now(timezone.utc)
    for t in tips + parlays:
        # STUCK-LIVE guard (quota-independent): if kickoff was clearly long ago (>2.5h) the
        # match is over — force-clear any frozen live_state and hand it back to settlement so
        # it can't hang on LIVE forever if the live feed froze mid-match (owner 2026-07-26).
        _ko = t.get("match_time") or next((l.get("kickoff") for l in (t.get("legs") or [])
                                           if l.get("kickoff")), "")
        _kd = _kickoff_dt(_ko) if _ko else None
        if _kd and (now_utc - _kd).total_seconds() > 2.5 * 3600:
            upd = {}
            if t.get("live_state"):
                upd["$unset"] = {"live_state": ""}
            if t.get("status") == "live":
                upd.setdefault("$set", {})["status"] = "pending"
            if upd:
                await db.tips.update_one({"id": t["id"]}, upd)
                cleared += 1
            continue
        home, away = _tip_match_teams(t)
        fx = _find_live_fixture(live, home, away) if (home and away) else None
        # Multi-game parlay (no single home/away): live if ANY leg is currently in-play.
        if not fx and (t.get("legs") or []):
            fx = _parlay_live_fixture(live, t.get("legs"))
        if fx:
            g = fx.get("goals") or {}
            st = {"minute": ((fx.get("fixture") or {}).get("status") or {}).get("elapsed"),
                  "score": f"{g.get('home') or 0}:{g.get('away') or 0}"}
            upd = {}
            if t.get("live_state") != st:
                upd["live_state"] = st
            # A live member pick belongs in the LIVE area, not Community → flip status.
            if _is_member_tip(t) and t.get("status") != "live":
                upd["status"] = "live"
                to_live += 1
            # Master-correction: a single-match pick whose live state has turned against it
            # loses its 'banker' badge & star rating until (if) the game turns (owner).
            if home and away and not t.get("is_parlay"):
                _gh, _ga = _align_goals(fx, home)
                _dg = _live_pick_in_danger(t.get("market"), t.get("kind"), _gh, _ga, st.get("minute"))
                upd.update(_derate_fields(t, _dg))
            if upd:
                await db.tips.update_one({"id": t["id"]}, {"$set": upd})
            annotated += 1
        elif t.get("live_state"):
            await db.tips.update_one({"id": t["id"]}, {"$unset": {"live_state": ""}})
            cleared += 1
        # PER-LEG live score — every running game in a parlay gets its own live score,
        # not just the first one (owner 2026-07-24: "jedes live-spiel braucht ein live score").
        legs = t.get("legs") or []
        if len(legs) >= 1:
            leg_changed = False
            for lg in legs:
                lh, la = _leg_teams(lg)
                if not lh or not la:
                    lh, la = (lh or home), (la or away)
                lfx = _find_live_fixture(live, lh, la) if (lh and la) else None
                if lfx:
                    hg, ag = _align_goals(lfx, lh)
                    lscore = f"{hg}:{ag}"
                    lmin = ((lfx.get("fixture") or {}).get("status") or {}).get("elapsed")
                    if (not lg.get("live") or lg.get("live_score") != lscore
                            or lg.get("live_minute") != lmin):
                        lg["live"], lg["live_score"], lg["live_minute"] = True, lscore, lmin
                        leg_changed = True
                    # Master-correction per leg: a 'banker' leg going against us live is
                    # stripped of its banker badge and flagged in danger (owner).
                    _sel_txt = " ".join(_fmt_selection(s) for s in (lg.get("selections") or []))
                    _ldg = _live_pick_in_danger(_sel_txt or lg.get("market"), lg.get("kind"), hg, ag, lmin)
                    if _ldg and not lg.get("live_danger"):
                        lg["live_danger"] = True
                        if lg.get("banker"):
                            lg["banker_was"] = True
                            lg["banker"] = False
                        leg_changed = True
                    elif not _ldg and lg.get("live_danger"):
                        lg["live_danger"] = False
                        if lg.get("banker_was"):
                            lg["banker"] = True
                        leg_changed = True
                elif lg.get("live"):
                    lg.pop("live", None)
                    lg.pop("live_score", None)
                    lg.pop("live_minute", None)
                    leg_changed = True
            if leg_changed:
                await db.tips.update_one(
                    {"id": t["id"]},
                    {"$set": {"legs": legs}, "$unset": {"share_image_path": ""}})
    return {"annotated": annotated, "cleared": cleared, "to_live": to_live}


# ----------------------------------------------------------- TipJarMaster
# The father of HQ: the best curator of all. Watches every expert, plays a safer live
# alternative when an HQ pick turns, and publishes ONLY the geballten Experten-Konsens
# as his own pick (red cards, own red button). Learns statistically from each expert's
# hit-rate and favours the ones who actually deliver.
_MASTER_BOT = {
    "email": "master@tipjar.com", "name": "TipJarMaster",
    "bio": "TipJarMaster vom HQ — lernt von allen Experten, spielt live die sichere "
           "Alternative und veröffentlicht den geballten Experten-Konsens.",
}
MASTER_CONSENSUS_MIN = 5  # ≥5 experts must agree before TipJarMaster publishes it


async def _get_master_bot():
    bot = await db.users.find_one({"email": _MASTER_BOT["email"]})
    if bot:
        return bot
    now = datetime.now(timezone.utc).isoformat()
    bot = {
        "id": str(uuid.uuid4()), "email": _MASTER_BOT["email"], "username": _MASTER_BOT["name"],
        "password_hash": "", "role": "expert", "is_verified": True, "verified": True,
        "credits": 0, "received_credits": 0, "referral_code": uuid.uuid4().hex[:8],
        "apex_flame": True, "created_at": now, "is_bot": True, "is_master": True,
        "bio": _MASTER_BOT["bio"],
    }
    await db.users.insert_one(bot)
    logger.info("Created TipJarMaster bot")
    return bot


def _safer_live_alternative(market, kind, gh, ga, minute):
    """An HQ pick is in danger live → return (new_market, category, odds, note) for a
    SAFER in-play bet on the SAME match, or None if we can't genuinely improve it."""
    m = (market or "").lower()
    total = (gh or 0) + (ga or 0)
    gm = re.search(r"über\s+(\d+)\.5", m)
    if gm and "halbzeit" not in m and " hz" not in m:
        orig_line = int(gm.group(1))
        new_line = total  # one more goal makes it → "Über {total}.5"
        if new_line < orig_line:
            odds = {0: "1.30", 1: "1.45", 2: "1.60", 3: "1.75"}.get(new_line, "1.50")
            return (f"Über {new_line}.5 Tore", "banker", odds,
                    f"Master live: die sichere Linie Über {new_line}.5.")
        return None
    losing_home, losing_away = (ga or 0) > (gh or 0), (gh or 0) > (ga or 0)
    if kind == "res_1" or "heimsieg" in m:
        if losing_home:
            return ("Doppelte Chance 1X", "banker", "1.50",
                    "Master live: absichern mit 1X.")
    if kind == "res_2" or "auswärtssieg" in m or "away win" in m:
        if losing_away:
            return ("Doppelte Chance X2", "banker", "1.50",
                    "Master live: absichern mit X2.")
    return None


async def master_live_alternatives() -> dict:
    """Phase 2: for every HQ single pick that has turned 'in danger' live, TipJarMaster
    publishes ONE safer in-play alternative on the same match (red master card)."""
    if not API_FOOTBALL_KEY:
        return {"posted": 0}
    dangers = await db.tips.find(
        {"source": {"$in": ["hq-auto", "hq-live"]}, "live_danger": True,
         "is_parlay": {"$ne": True}, "master_alt_done": {"$ne": True},
         "status": {"$in": ["pending", "live"]}},
        {"_id": 0}).to_list(100)
    if not dangers:
        return {"posted": 0}
    bot = await _get_master_bot()
    live = await asyncio.to_thread(_apifootball, "/fixtures", {"live": "all"}) or []
    posted = 0
    for src in dangers:
        home, away = src.get("home_team"), src.get("away_team")
        fx = _find_live_fixture(live, home, away) if home and away else None
        if not fx:
            await db.tips.update_one({"id": src["id"]}, {"$set": {"master_alt_done": True}})
            continue
        gh, ga = _align_goals(fx, home)
        minute = ((fx.get("fixture") or {}).get("status") or {}).get("elapsed")
        alt = _safer_live_alternative(src.get("market"), src.get("kind"), gh, ga, minute)
        if not alt:
            await db.tips.update_one({"id": src["id"]}, {"$set": {"master_alt_done": True}})
            continue
        new_market, category, odds, note = alt
        teams = fx.get("teams") or {}
        tid = f"master-{uuid.uuid4().hex[:10]}"
        tip = {
            "id": tid, "user_id": bot["id"], "username": bot["username"],
            "is_master": True, "is_expert": False,
            "home_team": home, "away_team": away,
            "home_team_latin": (teams.get("home") or {}).get("name") or home,
            "away_team_latin": (teams.get("away") or {}).get("name") or away,
            "match_time": src.get("match_time", ""), "country": src.get("country", ""),
            "league": src.get("league", "") or _fixture_league_label(fx),
            "league_code": src.get("league_code", ""),
            "market": new_market, "odds": odds, "category": category,
            "ai_rating": 8.5, "ai_analysis": f"👑 TipJarMaster: {note}",
            "legs": [], "is_parlay": False,
            "status": "live", "live_state": {"minute": minute, "score": f"{gh}:{ga}"},
            "live_minute": minute, "live_score": f"{gh}:{ga}",
            "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-master", "master_origin": src["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.tips.insert_one(tip)
        await db.tips.update_one({"id": src["id"]}, {"$set": {"master_alt_done": True}})
        posted += 1
    return {"posted": posted}


def _market_family(market: str):
    """Coarse market family so different phrasings of the same bet group together."""
    m = (market or "").lower()
    if not m:
        return None
    if "beide teams treffen" in m or "btts" in m:
        return "btts"
    gm = re.search(r"über\s+(\d+)\.5", m)
    if gm and "halbzeit" not in m:
        return f"over{gm.group(1)}5"
    um = re.search(r"unter\s+(\d+)\.5", m)
    if um and "halbzeit" not in m:
        return f"under{um.group(1)}5"
    if "1x" in m:
        return "dc1x"
    if "x2" in m:
        return "dcx2"
    return None


async def _expert_hitrates() -> dict:
    """Phase 4 'learning': username → win ratio from that expert's settled picks."""
    rows = await db.tips.aggregate([
        {"$match": {"is_expert": True, "status": {"$in": ["won", "lost"]}}},
        {"$group": {"_id": "$username",
                    "won": {"$sum": {"$cond": [{"$eq": ["$status", "won"]}, 1, 0]}},
                    "total": {"$sum": 1}}},
    ]).to_list(500)
    return {r["_id"]: round(r["won"] / r["total"], 3) for r in rows if r.get("total")}


async def master_consensus() -> dict:
    """Phase 3+4: when ≥MASTER_CONSENSUS_MIN experts back the SAME fixture with a
    compatible market, TipJarMaster publishes it as his own pick (weighted by hit-rate)."""
    tips = await db.tips.find(
        {"is_expert": True, "status": "pending", "source": {"$ne": "hq-master"}},
        {"_id": 0, "id": 1, "username": 1, "home_team": 1, "away_team": 1, "market": 1,
         "home_team_latin": 1, "away_team_latin": 1,
         "legs": 1, "odds": 1, "match_time": 1, "league": 1, "league_code": 1,
         "country": 1}).to_list(3000)
    hit = await _expert_hitrates()
    groups = {}
    for t in tips:
        home, away = _tip_match_teams(t)
        market = t.get("market") or ""
        if not market and (t.get("legs") or []):
            first = (t["legs"][0].get("selections") or [])
            market = " ".join(_fmt_selection(s) for s in first)
        fam = _market_family(market)
        if not home or not away or not fam:
            continue
        fixkey = "|".join(sorted([_norm(home), _norm(away)]))
        key = (fixkey, fam)
        g = groups.setdefault(key, {"experts": {}, "home": home, "away": away,
                                    "market": market, "odds": t.get("odds", ""),
                                    "match_time": t.get("match_time", ""),
                                    "league": t.get("league", ""),
                                    "league_code": t.get("league_code", ""),
                                    "country": t.get("country", "")})
        g["experts"][t["username"]] = hit.get(t["username"], 0.5)
    bot = None
    posted = 0
    for (fixkey, fam), g in groups.items():
        if len(g["experts"]) < MASTER_CONSENSUS_MIN:
            continue
        ckey = f"{fixkey}|{fam}"
        if await db.tips.find_one({"source": "hq-master", "consensus_key": ckey}):
            continue
        if bot is None:
            bot = await _get_master_bot()
        n = len(g["experts"])
        avg_hit = round(100 * sum(g["experts"].values()) / n)
        tid = f"master-{uuid.uuid4().hex[:10]}"
        tip = {
            "id": tid, "user_id": bot["id"], "username": bot["username"],
            "is_master": True, "is_expert": False,
            "home_team": g["home"], "away_team": g["away"],
            "match_time": g["match_time"], "country": g["country"],
            "league": g["league"], "league_code": g["league_code"],
            "market": g["market"], "odds": g["odds"], "category": "banker",
            "ai_rating": 9.0,
            "ai_analysis": (f"👑 TipJarMaster: {n} Experten sind sich einig ("
                            f"Ø Trefferquote {avg_hit}%) — TipJarMaster veröffentlicht den Konsens."),
            "legs": [], "is_parlay": False,
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-master", "consensus_key": ckey, "consensus_n": n,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.tips.insert_one(tip)
        posted += 1
    return {"posted": posted}


# ---------- Master packs: Einfach / Mittel / Challenge (owner 2026-06) ----------
CHALLENGE_START = 10.0
CHALLENGE_STEPS = 4


def _plausible_odds(market: str, odds: float) -> bool:
    """Reject implausibly low odds for a market so the Master never uses bad source data
    (e.g. 'Heim über 1.5 Tore @1.12' — a team scoring 2+ is realistically ~1.5+). Keeps the
    packs' odds honest without a live-odds feed."""
    m = (market or "").lower()
    if odds <= 1.0:
        return False
    team_ref = bool(re.search(r"heim|gast|home|away", m)) or bool(
        re.search(r"^\s*\S.*\s(über|unter|over|under)\b", m))
    if re.search(r"(über|over)\s*1\.5", m):
        return odds >= (1.45 if team_ref else 1.18)   # team scores 2+ vs total >1.5
    if re.search(r"(über|over)\s*2\.5", m):
        return odds >= 1.40
    if re.search(r"(über|over)\s*3\.5", m):
        return odds >= 1.55
    if re.search(r"(über|over)\s*0\.5", m):
        return odds >= (1.15 if team_ref else 1.03)   # team scores vs any goal
    if re.search(r"-1\.5|handicap.*-1", m):
        return odds >= 1.70
    return odds >= 1.08


async def _master_leg_candidates(now, min_odds, max_odds):
    """Upcoming (pregame) single picks — from experts (weighted by hit-rate) and the
    HQ-auto pool — usable as parlay legs. One leg per fixture, odds within [min,max]."""
    tips = await db.tips.find(
        {"status": "pending", "source": {"$ne": "hq-master"}, "is_parlay": {"$ne": True},
         "hidden": {"$ne": True},
         "home_team": {"$nin": ["", None]}, "away_team": {"$nin": ["", None]}},
        {"_id": 0, "home_team": 1, "away_team": 1, "home_team_latin": 1,
         "away_team_latin": 1, "market": 1, "odds": 1, "match_time": 1,
         "league": 1, "is_expert": 1, "username": 1}).to_list(3000)
    hit = await _expert_hitrates()
    preds = await db.match_predictions.find(
        {}, {"_id": 0, "home": 1, "away": 1, "fav": 1, "fav_prob": 1}).to_list(2000)
    fav_map = _favourite_side_map(preds, min_prob=62)
    gift_map = await _gift_stance_map()
    seen = {}
    for t in tips:
        ko = _parse_kickoff(t.get("match_time"))
        if not ko or ko <= now + timedelta(minutes=20):
            continue  # only clearly upcoming games (pregame)
        try:
            od = float(str(t.get("odds") or "0").replace(",", "."))
        except (ValueError, TypeError):
            od = 0
        if not (min_odds <= od <= max_odds):
            continue
        market = (t.get("market") or "").strip()
        if not market:
            continue
        if not _plausible_odds(market, od):
            continue
        home = t.get("home_team_latin") or t.get("home_team")
        away = t.get("away_team_latin") or t.get("away_team")
        # owner learning 2026-07-30: NEVER back the clear underdog side (e.g. a trailing
        # away team like HB Torshavn/Hajduk). Skip team-specific legs on the weak side.
        fav = fav_map.get(_match_key(home, away))
        if fav and _leg_backs_clear_underdog(market, home, away, fav[0]):
            continue
        # owner 2026-07-30: GIFTS are the source of truth — no Master leg may contradict a gift
        # (e.g. gift 'Qarabag unter 2.5' ⇒ never a 'Qarabag über 2.5' / 'Qarabag trifft' leg).
        if _conflicts_with_gift(market, home, away, gift_map.get(_match_key(home, away))):
            continue
        # owner 2026-06: learning — drop leg market-types that keep LOSING (from real results)
        if learn_verdict("master", market)[0] == "veto":
            continue
        fixkey = "|".join(sorted([_norm(home), _norm(away)]))
        weight = hit.get(t.get("username"), 0.5) if t.get("is_expert") else 0.55
        cand = {"match": f"{home} – {away}", "home": home, "away": away, "market": market,
                "odds": od, "kickoff": ko, "match_time": t.get("match_time"),
                "league": t.get("league", ""), "weight": weight, "fixkey": fixkey}
        if fixkey not in seen or weight > seen[fixkey]["weight"]:
            seen[fixkey] = cand
    return sorted(seen.values(), key=lambda c: (-c["weight"], c["odds"]))


async def _enrich_legs_real_odds(chosen):
    """Replace pool odds with REAL bookmaker odds (API-Football /odds, 6h-cached) for the
    chosen legs — incl. team-total markets (Heim/Gast über X.5), now priced via the feed.
    Keeps the plausibility-filtered pool odds when the feed has no price. Returns (chosen, product)."""
    prod = 1.0
    for c in chosen:
        try:
            odds = await ensure_match_odds(c.get("home", ""), c.get("away", ""), c.get("match_time", ""))
            real = _real_odd_for(c.get("market", ""), odds, c.get("home", ""), c.get("away", ""))
        except Exception:
            real = None
        if real and float(real) >= 1.01:
            c["odds"] = round(float(real), 2)
            c["real"] = True
        prod *= c["odds"]
    return chosen, round(prod, 2)


def _assemble_parlay(cands, target, min_legs, max_legs):
    """Greedily combine distinct-fixture legs until the odds product nears target."""
    chosen, prod = [], 1.0
    for c in cands:
        if len(chosen) >= max_legs:
            break
        chosen.append(c)
        prod *= c["odds"]
        if len(chosen) >= min_legs and prod >= target * 0.85:
            break  # close enough — don't overshoot the band
    if len(chosen) < min_legs or prod < target * 0.7:
        return None, 0.0
    return chosen, round(prod, 2)


def _pack_legs(chosen, banker_matches=None):
    bm = banker_matches or set()
    return [{"match": c["match"], "league": c["league"], "kickoff": c["match_time"],
             "status": "pending", "selections": [c["market"]],
             "sel_odds": [f"{c['odds']:.2f}"], "banker": c["match"] in bm} for c in chosen]


_WIN_MKT_RE = re.compile(
    r'(heimsieg|heim\s*sieg|auswärtssieg|auswarts\s*sieg|gastsieg|\bsieg\b|gewinnt|'
    r'to win|match winner|\bwin\b|home win|away win|\b1x2\b)', re.I)


def _win_team_name(market: str, home: str, away: str) -> str:
    m = (market or "").lower()
    if "heim" in m or "home" in m:
        return home
    if "gast" in m or "auswärts" in m or "auswarts" in m or "away" in m:
        return away
    for team in (home, away):
        if team and team.lower() in m:
            return team
    return home


async def master_doublepack() -> dict:
    """Owner 2026-06: the headline 'Doppelpack' — the Master READS 2 games well and builds a
    SMART correlated same-game builder for each (e.g. favourite wins + both score, Double Chance
    + Over, 1st-half goal + Over — mirrors the owner's Lens–Arsenal 1-1→2-1 winner). The target
    odds are irrelevant ("egal, Hauptsache du liest zwei Spiele gut"); what matters is the read.
    Two games, correlated legs per game, auto-settled leg-by-leg. Only one open at a time."""
    now = datetime.now(timezone.utc)
    if await db.tips.count_documents(
            {"source": "hq-master", "master_doublepack": True,
             "status": {"$in": ["pending", "live"]}}):
        return {"skipped": "open"}
    # Pool: goal-friendly, high-confidence upcoming games with a CLEAR favourite (a strong
    # read). Sort strongest-favourite first (that is the game we can "read well").
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1500)
    cmap = _consensus_map(preds)
    cands, seen = [], set()
    gift_map = await _gift_stance_map()
    for p in preds:
        if not _pred_whitelisted(p) or _bad_for_overs(p):
            continue
        if not _zero_zero_assessment(p)["over_safe"]:
            continue
        if (p.get("fav_prob") or 0) < 58:  # need a clear favourite to read the game well
            continue
        # owner 2026-07-30: gifts win — skip any match a gift called low-scoring (the Doppelpack
        # builds goal/over legs which would contradict a gift 'unter').
        if _gift_under_lean(gift_map.get(_match_key(p.get("home"), p.get("away")))):
            continue
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
        p["_cons"] = _consensus_for(cmap, p.get("home"), p.get("away"), p.get("fav"))["agree"]
        cands.append((ko, p))
    if len(cands) < 2:
        return {"skipped": "not-enough", "have": len(cands)}
    # owner 2026-07-30 Konsens-Booster: games most sources agree on first, then favourite strength
    cands.sort(key=lambda x: ((x[1].get("_cons") or 0), (x[1].get("fav_prob") or 0),
                              (x[1].get("total") or 0)), reverse=True)
    picks = cands[:2]
    legs, combo = [], 1.0
    for i, (ko, p) in enumerate(picks):
        # offset the pattern index so the two games don't get identical builders
        sels, sodds = _special_legs_for(p, i * 2)
        for o in sodds:
            combo *= float(o)
        legs.append({"match": f"{p.get('home')} - {p.get('away')}",
                     "league": p.get("league") or "", "kickoff": p.get("kickoff") or "",
                     "status": "pending", "selections": sels, "sel_odds": sodds,
                     "_ko": ko})
    combo = round(combo, 2)
    first_ko = min(l["_ko"] for l in legs)
    for l in legs:
        l.pop("_ko", None)
    combo = _dedupe_multigame_legs(legs)  # defensive: strip per-game implied legs
    cons_pair = [pk[1].get("_cons") or 0 for pk in picks]
    cons_line = (f" Beide Spiele mit breitem Quellen-Konsens ({cons_pair[0]} bzw. {cons_pair[1]} "
                 f"Prognose-Quellen einig)." if min(cons_pair) >= 2 else "")
    home_names = [pk[1].get("home") for pk in picks]
    away_names = [pk[1].get("away") for pk in picks]
    bot = await _get_master_bot()
    tid = f"master-{uuid.uuid4().hex[:10]}"
    tip = {
        "id": tid, "user_id": bot["id"], "username": bot["username"],
        "is_master": True, "is_expert": False, "master_doublepack": True,
        "home_team": "", "away_team": "", "match_time": first_ko.isoformat(),
        "market": "Doppelpack — 2 Spiele Bet-Builder", "odds": f"{combo:.2f}",
        "category": "value", "ai_rating": 9.0,
        "ai_analysis": (f"👑 TipJarMaster Doppelpack: 2 gut gelesene Spiele "
                        f"({home_names[0]} – {away_names[0]} · {home_names[1]} – {away_names[1]}) "
                        f"mit je korrelierten Wetten (Favorit-Sieg/Doppelte Chance + Tore). "
                        f"Gesamtquote {combo:.2f}.{cons_line} Immer mit kontrolliertem Einsatz."),
        "legs": legs, "is_parlay": True,
        "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
        "source": "hq-master", "created_at": now.isoformat(),
    }
    await db.tips.insert_one(tip)
    logger.info(f"Master Doppelpack: 2-game bet-builder @ {combo}")
    return {"posted": 1, "odds": combo, "games": len(legs)}


async def master_build_packs() -> dict:
    """Einfach (2–4 Spiele ~3.0) & Mittel (3–5 Spiele ~6–8): the Master publishes up to
    2 of each per day, only when a solid combination can be assembled from the pool."""
    now = datetime.now(timezone.utc)
    day = now.date().isoformat()
    posted, bot = {}, None
    # Owner rule 2026-07-26: Easy & Medium must NEVER share a match. If a shared game loses,
    # BOTH parlays die — so the daily "win at least one" goal is impossible. We track every
    # fixture already used (by today's open Easy/Medium packs AND within this run) and exclude
    # it from the other pack.
    used_fixkeys = set()
    existing_packs = await db.tips.find(
        {"source": "hq-master", "master_category": {"$in": ["einfach", "mittel"]},
         "status": {"$in": ["pending", "live"]}},
        {"_id": 0, "legs": 1}).to_list(50)
    for ep in existing_packs:
        for lg in (ep.get("legs") or []):
            m = (lg.get("match") or "")
            parts = re.split(r"\s[–-]\s", m, maxsplit=1)
            if len(parts) == 2:
                used_fixkeys.add("|".join(sorted([_norm(parts[0]), _norm(parts[1])])))
    specs = [
        ("einfach", 3.0, 2, 4, 1.25, 1.80),
        ("mittel", 7.0, 3, 5, 1.40, 2.40),
    ]
    # Owner 2026-07-30: on busy match days the Master should fill MORE slips. Allow up to
    # PACK_DAILY_CAP per category per day and PACK_MAX_OPEN open at once (still never sharing a
    # match, enforced via used_fixkeys). Build as many as the pool cleanly supports per run.
    PACK_DAILY_CAP, PACK_MAX_OPEN = 4, 3
    for cat, target, minl, maxl, lo, hi in specs:
        made = await db.tips.count_documents(
            {"source": "hq-master", "master_category": cat, "master_day": day})
        openx = await db.tips.count_documents(
            {"source": "hq-master", "master_category": cat, "status": {"$in": ["pending", "live"]}})
        while made < PACK_DAILY_CAP and openx < PACK_MAX_OPEN:
            cands = await _master_leg_candidates(now, lo, hi)
            # Exclude any fixture already used by another open pack / earlier this run.
            cands = [c for c in cands if c.get("fixkey") not in used_fixkeys]
            cands = sorted(cands, key=lambda c: c["odds"])  # build up gradually → hit target tightly
            chosen, prod = _assemble_parlay(cands, target, minl, maxl)
            if not chosen:
                break  # pool exhausted → stop for this category
            for c in chosen:  # reserve these fixtures so the next pack can't reuse them
                if c.get("fixkey"):
                    used_fixkeys.add(c["fixkey"])
            chosen, prod = await _enrich_legs_real_odds(chosen)  # real bookmaker odds where available
            if bot is None:
                bot = await _get_master_bot()
            tid = f"master-{uuid.uuid4().hex[:10]}"
            first_ko = min(c["kickoff"] for c in chosen)
            label = "Einfach" if cat == "einfach" else "Mittel"
            n = len(chosen)
            # Owner 2026-06: the Master should occasionally post a SAFE SYSTEM bet so the
            # community sees the mechanic live. Once per day the first Mittel pack with >=3
            # games becomes a "one may miss" system (N-1)/N — it still pays if a single leg
            # loses. Kept to Mittel where X-of-Y is meaningful (Einfach can be 2 legs).
            make_system = False
            if cat == "mittel" and n >= 3:
                sys_today = await db.tips.count_documents(
                    {"source": "hq-master", "master_category": cat, "master_day": day,
                     "bet_type": "system"})
                make_system = sys_today == 0
            banker_matches = set()
            if make_system:
                sf = n - 1
                nb = 2 if n >= 5 else 1
                # Owner teaching 2026-06: MARK BANKERS on the slip. Bankers = the safest legs
                # (lowest odds), but the Master LEARNS FROM MISTAKES — it avoids market-types
                # with a poor banker record (a lost banker kills the whole system). State only
                # which system was chosen; no long explanation.
                def _brank(c):
                    b = learn_bucket(c["market"])
                    vb = learn_verdict("master", "banker_" + b, raw_bucket=True)[0]
                    vm = learn_verdict("master", c["market"])[0]
                    score = 2 if (vb == "veto" or vm == "veto") else (0 if (vb == "boost" or vm == "boost") else 1)
                    return (score, c["odds"])
                bankers = sorted(chosen, key=_brank)[:nb]
                banker_matches = {c["match"] for c in bankers}
                market = f"System {sf}/{n}"
                analysis = f"👑 TipJarMaster System {sf}/{n} · {nb} Banker."
            else:
                market = f"{n}-fach Kombi"
                analysis = f"👑 TipJarMaster {label}: {n} Spiele, Gesamtquote {prod:.2f}."
            tip = {
                "id": tid, "user_id": bot["id"], "username": bot["username"],
                "is_master": True, "is_expert": False,
                "home_team": "", "away_team": "", "match_time": first_ko.isoformat(),
                "market": market, "odds": f"{prod:.2f}",
                "category": "banker" if cat == "einfach" else "value",
                "master_category": cat, "master_day": day, "ai_rating": 8.5,
                "ai_analysis": analysis,
                "bet_type": "system" if make_system else "",
                "system_from": (n - 1) if make_system else 0,
                "system_total": n if make_system else 0,
                "legs": _pack_legs(chosen, banker_matches), "is_parlay": True,
                "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
                "source": "hq-master", "created_at": now.isoformat(),
            }
            await db.tips.insert_one(tip)
            posted[cat] = posted.get(cat, 0) + 1
            made += 1
            openx += 1
    return {"posted": posted}


async def _master_challenge_state():
    st = await db.master_challenge.find_one({"id": "state"})
    if not st:
        st = {"id": "state", "step": 1, "stake": CHALLENGE_START, "status": "idle",
              "current_tip_id": None, "updated_at": datetime.now(timezone.utc).isoformat()}
        await db.master_challenge.insert_one(st)
    return st


async def master_challenge() -> dict:
    """One active Challenge at a time: start 10 €, roll the FULL win over 4 steps.
    Each step = 2 safe low-odds picks (~1.2 & ~1.3). Loss → reset to step 1. Only opens
    a new step when a genuinely safe combination is available (no fixed rhythm)."""
    now = datetime.now(timezone.utc)
    st = await _master_challenge_state()
    action = None
    if st.get("current_tip_id"):
        cur = await db.tips.find_one({"id": st["current_tip_id"]},
                                     {"_id": 0, "status": 1, "odds": 1})
        if not cur:
            await db.master_challenge.update_one({"id": "state"}, {"$set": {"current_tip_id": None}})
            st["current_tip_id"] = None
        else:
            cst = cur.get("status")
            if cst == "won":
                try:
                    od = float(str(cur.get("odds") or "1").replace(",", "."))
                except (ValueError, TypeError):
                    od = 1.0
                won_amount = round(st["stake"] * od, 2)
                if st["step"] >= CHALLENGE_STEPS:
                    await db.master_challenge.update_one({"id": "state"}, {"$set": {
                        "step": 1, "stake": CHALLENGE_START, "status": "idle",
                        "current_tip_id": None, "last_result": "completed",
                        "last_win": won_amount, "updated_at": now.isoformat()}})
                    return {"action": "completed", "win": won_amount}
                await db.master_challenge.update_one({"id": "state"}, {"$set": {
                    "step": st["step"] + 1, "stake": won_amount, "status": "active",
                    "current_tip_id": None, "updated_at": now.isoformat()}})
                st["step"] += 1
                st["stake"] = won_amount
                st["current_tip_id"] = None
                action = "advanced"
            elif cst == "lost":
                await db.master_challenge.update_one({"id": "state"}, {"$set": {
                    "step": 1, "stake": CHALLENGE_START, "status": "idle",
                    "current_tip_id": None, "last_result": "lost", "updated_at": now.isoformat()}})
                return {"action": "reset_lost"}
            elif cst == "void":
                await db.master_challenge.update_one({"id": "state"},
                                                     {"$set": {"current_tip_id": None}})
                st["current_tip_id"] = None
            else:
                return {"action": "waiting", "step": st["step"]}
    if st.get("current_tip_id"):
        return {"action": action or "waiting", "step": st["step"]}
    # Open the next step only on a genuinely safe opportunity (2 low-odds picks).
    cands = await _master_leg_candidates(now, 1.20, 1.60)
    safe = [c for c in cands if re.search(
        r"über 0\.5|über 1\.5|doppelte chance|1x|x2|beide teams treffen", c["market"].lower())]
    pool = sorted(safe or cands, key=lambda c: c["odds"])
    chosen = pool[:2]
    if len(chosen) < 2:
        return {"action": "no_opportunity", "step": st["step"]}
    chosen, prod = await _enrich_legs_real_odds(chosen)  # real bookmaker odds where available
    stake = st["stake"]
    pot = round(stake * prod, 2)
    bot = await _get_master_bot()
    tid = f"master-{uuid.uuid4().hex[:10]}"
    first_ko = min(c["kickoff"] for c in chosen)
    tip = {
        "id": tid, "user_id": bot["id"], "username": bot["username"],
        "is_master": True, "is_expert": False,
        "home_team": "", "away_team": "", "match_time": first_ko.isoformat(),
        "market": f"Challenge Stufe {st['step']}/{CHALLENGE_STEPS}", "odds": f"{prod:.2f}",
        "category": "banker", "master_category": "challenge", "master_day": now.date().isoformat(),
        "challenge_step": st["step"], "stake": f"{stake:.2f} €", "potential_return": f"{pot:.2f} €",
        "ai_rating": 9.0,
        "ai_analysis": (f"👑 TipJarMaster Challenge — Stufe {st['step']}/{CHALLENGE_STEPS}. "
                        f"Einsatz {stake:.2f} €, Quote {prod:.2f} → {pot:.2f} €. "
                        f"Zwei sichere Picks; der komplette Gewinn rollt weiter."),
        "legs": _pack_legs(chosen), "is_parlay": True,
        "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
        "source": "hq-master", "created_at": now.isoformat(),
    }
    await db.tips.insert_one(tip)
    await db.master_challenge.update_one({"id": "state"}, {"$set": {
        "current_tip_id": tid, "status": "active", "updated_at": now.isoformat()}})
    return {"action": "opened", "step": st["step"], "odds": prod}


def _fav_side(c: dict, odds: dict):
    """Return (fav_team, fav_odd) — the favourite side of a fixture from real 1X2 odds."""
    wh, wa = odds.get("win_home"), odds.get("win_away")
    try:
        wh = float(wh) if wh is not None else None
    except (TypeError, ValueError):
        wh = None
    try:
        wa = float(wa) if wa is not None else None
    except (TypeError, ValueError):
        wa = None
    if wh is not None and (wa is None or wh <= wa):
        return c["home"], wh
    if wa is not None:
        return c["away"], wa
    return None, None


async def master_safe_bets_build() -> dict:
    """Owner 00:30 slip: an 8-leg "Safe Bets" parlay built ONLY from near-certain
    selections — win favourites (real 1X2), Team über 0.5 Tore (real team-total odds),
    and player props (>0.5 Fouls/Schüsse/Paraden). The micro-prop prices aren't in the
    odds feed, so those legs carry a plausible quasi-safe ESTIMATE (owner-approved).
    One slip per Berlin day; needs at least 6 solid legs to post."""
    now = datetime.now(timezone.utc)
    day = _berlin_now().date().isoformat()
    if await db.tips.count_documents(
            {"source": "hq-master", "master_category": "safe",
             "status": {"$in": ["pending", "live"]}}):
        return {"skipped": "open"}
    if await db.tips.count_documents(
            {"source": "hq-master", "master_category": "safe", "master_day": day}):
        return {"skipped": "done-today"}
    cands = await _master_leg_candidates(now, 1.01, 999)
    fixtures, seen_fx = [], set()
    for c in cands:
        if c["fixkey"] in seen_fx:
            continue
        seen_fx.add(c["fixkey"])
        fixtures.append(c)
        if len(fixtures) >= 24:
            break
    legs, used_fx = [], set()
    odds_by_fx = {}

    async def _odds_for(c):
        if c["fixkey"] not in odds_by_fx:
            try:
                odds_by_fx[c["fixkey"]] = await ensure_match_odds(
                    c.get("home", ""), c.get("away", ""), c.get("match_time", "")) or {}
            except Exception:
                odds_by_fx[c["fixkey"]] = {}
        return odds_by_fx[c["fixkey"]]

    def _add(c, market, odd, kind, prob=None):
        legs.append({"match": c["match"], "league": c["league"], "kickoff": c["match_time"],
                     "match_time": c["match_time"], "kickoff_dt": c["kickoff"],
                     "market": market, "odds": round(float(odd), 2), "kind": kind,
                     "prob": prob})
        used_fx.add(c["fixkey"])

    # 1) Win favourites — up to 3, real 1X2 odds, clear favourite (≤ ~1.65)
    for c in fixtures:
        if len([l for l in legs if l["kind"] == "win"]) >= 3:
            break
        odds = await _odds_for(c)
        fav, fav_od = _fav_side(c, odds)
        if fav and fav_od and 1.10 <= fav_od <= 1.65:
            _add(c, f"{fav} Sieg", fav_od, "win")

    # 2) Team über 0.5 Tore — up to 3, real team-total odds for the favourite team
    for c in fixtures:
        if c["fixkey"] in used_fx:
            continue
        if len([l for l in legs if l["kind"] == "team_o05"]) >= 3:
            break
        odds = await _odds_for(c)
        fav, _ = _fav_side(c, odds)
        if not fav:
            continue
        market = f"{fav} über 0.5 Tore"
        real = _real_odd_for(market, odds, c["home"], c["away"])
        if real and 1.03 <= float(real) <= 1.45:
            _add(c, market, real, "team_o05")

    # 3) Player props (>0.5 Fouls/Schüsse/Paraden) — estimated quasi-safe odds
    SAFE_KINDS = ("fouls_c", "fouls_d", "sot", "shots", "saves")
    for c in fixtures:
        if len(legs) >= 8:
            break
        if c["fixkey"] in used_fx:
            continue
        odds = await _odds_for(c)
        fav, _ = _fav_side(c, odds)
        team = fav or c["home"]
        try:
            props = await _team_best_props(team, _smart_seasons(c.get("match_time")))
        except Exception:
            props = []
        pick = None
        for p in props:
            if p.get("kind") not in SAFE_KINDS:
                continue
            if (p.get("prob") or 0) < 0.72:
                continue
            try:
                od = float(str(p.get("odds") or "0"))
            except (ValueError, TypeError):
                continue
            if 1.05 <= od <= 1.30:
                pick = (p, od)
                break
        if pick:
            p, od = pick
            _add(c, p["market"], od, "prop", p.get("prob"))

    if len(legs) < 6:
        return {"skipped": "not-enough", "legs": len(legs)}
    legs = legs[:8]
    prod = 1.0
    for l in legs:
        prod *= l["odds"]
    prod = round(prod, 2)
    bot = await _get_master_bot()
    tid = f"master-{uuid.uuid4().hex[:10]}"
    first_ko = min(l["kickoff_dt"] for l in legs)
    packed = [{"match": l["match"], "league": l["league"], "kickoff": l["match_time"],
               "status": "pending", "selections": [l["market"]],
               "sel_odds": [f"{l['odds']:.2f}"]} for l in legs]
    tip = {
        "id": tid, "user_id": bot["id"], "username": bot["username"],
        "is_master": True, "is_expert": False,
        "home_team": "", "away_team": "", "match_time": first_ko.isoformat(),
        "market": f"Safe Bets — {len(legs)}-fach", "odds": f"{prod:.2f}",
        "category": "value", "master_category": "safe", "master_day": day,
        "ai_rating": 9.0,
        "ai_analysis": (f"👑 TipJarMaster Safe Bets: {len(legs)} quasi-sichere Beine "
                        f"(Sieg-Favoriten, Team über 0.5 Tore, Spieler-Props), "
                        f"Gesamtquote {prod:.2f}. Spieler-Prop-Quoten sind plausible "
                        f"Schätzungen. Immer mit kontrolliertem Einsatz."),
        "legs": packed, "is_parlay": True,
        "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
        "source": "hq-master", "created_at": now.isoformat(),
    }
    await db.tips.insert_one(tip)
    return {"posted": 1, "odds": prod, "legs": len(legs)}



def _special_legs_for(p, idx=0):
    """Build a SMART, non-redundant same-game bet-builder (1-2 legs) that 'photographs' the
    likely result with goal fluctuation — favourite wins + both score, Double Chance (won't lose)
    + goals, etc. Uses ONLY FULL-MATCH markets that every bookmaker offers (owner 2026-06:
    half-time markets often don't exist for the lower leagues the Special draws from → keep it
    realistically playable). Never combines logically implied legs (BTTS/Über 2.5 force Über 1.5).
    All markets are settlement-verified."""
    total = p.get("total") or 0
    btts = bool(p.get("btts"))
    over25 = bool(p.get("over25")) or total >= 2.6
    fav = _fav_team(p)
    fav_prob = p.get("fav_prob") or 0
    o25 = ("Über 2.5 Tore", 1.80)
    o15 = ("Über 1.5 Tore", 1.25)
    bt = ("Beide Teams treffen", 1.75)
    win = (f"{fav} Sieg", 1.70) if fav and fav_prob >= 62 else None
    dc = None
    if fav and fav_prob >= 55:
        dc = (f"{fav} Doppelte Chance {'1X' if p.get('fav') == 'home' else 'X2'}", 1.25)
    pats = []  # each pattern is non-redundant + universally available (no half-time markets)
    if win and btts:
        pats.append([win, bt])            # Favorit gewinnt + beide treffen (aggressiv)
    if dc and over25:
        pats.append([dc, o25])            # verliert nicht + über 2.5
    if win and over25:
        pats.append([win, o15])           # Favorit gewinnt + über 1.5 (Sieg impliziert keine Tore)
    if dc and btts:
        pats.append([dc, bt])             # verliert nicht + beide treffen
    if over25:
        pats.append([o25])
    if btts:
        pats.append([bt])
    if win:
        pats.append([win])                # Einzel-Bein zur Abwechslung
    pats.append([o15])
    chosen = pats[idx % len(pats)]
    return [c[0] for c in chosen], [f"{c[1]:.2f}" for c in chosen]


async def master_special_build() -> dict:
    """Owner 2026-07-30: the Master 'Special' — ALWAYS a 4-game bet-builder combo (learned from
    the owner's winning Betano/Stoiximan bet-builder slips). Each of the 4 games contributes a
    2-selection same-game builder from goal markets (HT Über 0.5, Über 1.5/2.5, Beide treffen), so
    the whole thing auto-settles leg-by-leg. One Special per Berlin day."""
    now = datetime.now(timezone.utc)
    day = _berlin_now().date().isoformat()
    if await db.tips.count_documents(
            {"source": "hq-master", "master_category": "special",
             "status": {"$in": ["pending", "live"]}}):
        return {"skipped": "open"}
    if await db.tips.count_documents(
            {"source": "hq-master", "master_category": "special", "master_day": day}):
        return {"skipped": "done-today"}
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1500)
    cmap = _consensus_map(preds)
    cands, seen = [], set()
    gift_map = await _gift_stance_map()
    for p in preds:
        if not _pred_whitelisted(p) or _bad_for_overs(p):
            continue
        if not _zero_zero_assessment(p)["over_safe"]:
            continue  # only goal-friendly games for a goals bet-builder
        # owner 2026-07-30: gifts win — skip a match a gift called low-scoring.
        if _gift_under_lean(gift_map.get(_match_key(p.get("home"), p.get("away")))):
            continue
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
        ci = _consensus_for(cmap, p.get("home"), p.get("away"), p.get("fav"))
        p["_cons"] = ci["over_n"] + ci["btts_n"]
        cands.append((ko, p))
    if len(cands) < 4:
        return {"skipped": "not-enough", "have": len(cands)}
    # owner 2026-07-30 Konsens-Booster: goals-consensus first (sources agreeing on Over/BTTS)
    cands.sort(key=lambda x: ((x[1].get("_cons") or 0), (x[1].get("total") or 0),
                              (x[1].get("fav_prob") or 0)), reverse=True)
    picks = cands[:4]
    legs, combo = [], 1.0
    for i, (ko, p) in enumerate(picks):
        sels, sodds = _special_legs_for(p, i)
        for o in sodds:
            combo *= float(o)
        legs.append({"match": f"{p.get('home')} - {p.get('away')}",
                     "league": p.get("league") or "", "kickoff": p.get("kickoff") or "",
                     "status": "pending", "selections": sels, "sel_odds": sodds,
                     "_ko": ko})
    combo = round(combo, 2)
    first_ko = min(l["_ko"] for l in legs)
    for l in legs:
        l.pop("_ko", None)
    combo = _dedupe_multigame_legs(legs)  # strip per-game implied legs (BTTS ⇒ Über 1.5, …)
    cons_avg = round(sum((pk[1].get("_cons") or 0) for pk in picks) / max(len(picks), 1), 1)
    cons_line = (f" Ø {cons_avg} Quellen pro Spiel einig bei den Tor-Märkten." if cons_avg >= 2 else "")
    bot = await _get_master_bot()
    tid = f"master-{uuid.uuid4().hex[:10]}"
    tip = {
        "id": tid, "user_id": bot["id"], "username": bot["username"],
        "is_master": True, "is_expert": False,
        "home_team": "", "away_team": "", "match_time": first_ko.isoformat(),
        "market": "Special — 4 Spiele Bet-Builder", "odds": f"{combo:.2f}",
        "category": "value", "master_category": "special", "master_day": day,
        "ai_rating": 8.0,
        "ai_analysis": (f"🎯 Master Special: 4-Spiele-Bet-Builder mit je 2 korrelierten Toren-Wetten "
                        f"(1. HZ Über 0.5, Über 1.5/2.5, beide treffen). Gesamtquote {combo:.2f}.{cons_line} "
                        f"Aggressiv nach Vorbild echter Gewinn-Scheine — mit kontrolliertem Einsatz."),
        "legs": legs, "is_parlay": True,
        "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
        "source": "hq-master", "created_at": now.isoformat(),
    }
    await db.tips.insert_one(tip)
    logger.info(f"Master Special: 4-game bet-builder @ {combo}")
    return {"posted": 1, "odds": combo, "games": len(legs)}


def _avatar_goal_minute(fg, total, over25, btts, drought) -> int:
    """Owner learning 2026-07-30: predict a CONCRETE goal-minute window (40/60/75/90) instead
    of a vague late goal. Goal-heavy / drought sides score EARLY."""
    if fg >= 2 or total >= 4:
        m = 40
    elif fg >= 2 or over25 or total >= 3:
        m = 60
    elif fg >= 1 or btts:
        m = 75
    else:
        m = 90
    if drought and m > 40:  # a hungry side that failed to score last time attacks earlier
        m = {60: 40, 75: 60, 90: 75}.get(m, m)
    return m


async def master_avatar_calls() -> dict:
    """Owner 2026-07-30: the TipJarMaster AVATAR — a confident expert who, once per Berlin day,
    calls up to 3 near-lock goal predictions with a CONCRETE minute window (40/60/75/90) and a
    speech-bubble text. Backs ONLY the clear, STRONG favourite (never a weak underdog — Torshavn
    learning); recognises goal 'droughts' (a fav that failed to score last game is hungry now →
    earlier goal). Each call is a REAL, auto-settleable single pick (HT-goal for ≤45', else the
    favourite Über 0.5 Tore) so it is playable AND settles cleanly."""
    now = datetime.now(timezone.utc)
    day = _berlin_now().date().isoformat()
    if await db.tips.count_documents(
            {"source": "hq-master", "master_category": "avatar",
             "status": {"$in": ["pending", "live"]}}):
        return {"skipped": "open"}
    if await db.tips.count_documents(
            {"source": "hq-master", "master_category": "avatar", "master_day": day}):
        return {"skipped": "done-today"}
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1500)
    cmap = _consensus_map(preds)
    cands, seen = [], set()
    gift_map = await _gift_stance_map()
    for p in preds:
        if not _pred_whitelisted(p) or _bad_for_overs(p):
            continue
        fav = _fav_team(p)
        fp = p.get("fav_prob") or 0
        try:
            fp = int(float(fp))
        except (TypeError, ValueError):
            fp = 0
        if not fav or fp < 62:  # STRONG side only (never a weak underdog)
            continue
        # owner 2026-07-30: gifts win — the avatar backs the favourite to score, so skip any
        # match a gift called low-scoring / that favourite low.
        if _conflicts_with_gift(f"{fav} trifft", p.get("home"), p.get("away"),
                                gift_map.get(_match_key(p.get("home"), p.get("away")))):
            continue
        fg0 = (p.get("ph") or 0) if p.get("fav") == "home" else (p.get("pa") or 0)
        try:
            fg0 = int(round(float(fg0)))
        except (TypeError, ValueError):
            fg0 = 0
        # the favourite must be expected to score (a "fav trifft" call), OR a 0:0 is
        # practically excluded (a first-half-goal call). Never call on a game we don't trust.
        if not (fg0 >= 1 or _zero_zero_assessment(p)["over_safe"]):
            continue
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
        ci = _consensus_for(cmap, p.get("home"), p.get("away"), p.get("fav"))
        p["_cons"] = ci.get("agree", 0) + ci.get("over_n", 0)
        cands.append((ko, p))
    if not cands:
        return {"skipped": "no-candidates"}
    cands.sort(key=lambda x: ((x[1].get("_cons") or 0), (x[1].get("fav_prob") or 0),
                              (x[1].get("total") or 0)), reverse=True)
    bot = await _get_master_bot()
    posted = 0
    for ko, p in cands:
        if posted >= 3:
            break
        fav = _fav_team(p)
        home, away = p.get("home"), p.get("away")
        # VERIFY the fixture is a REAL, upcoming game (owner 2026-07-30: "Spiel existiert nicht").
        # Only post an avatar call when API-Football confirms the exact fixture; use its real
        # names / kickoff / league so no phantom pairing ever appears.
        real_ko = p.get("kickoff") or ko.isoformat()
        real_league, real_country = p.get("league") or "", p.get("country") or ""
        if API_FOOTBALL_KEY:
            tidh = await resolve_team_id(home)
            fx = find_upcoming_fixture(tidh, away) if tidh else None
            if not fx:
                tida = await resolve_team_id(away)
                fx2 = find_upcoming_fixture(tida, home) if tida else None
                if fx2:
                    fx = {"home_name": fx2.get("away_name"), "away_name": fx2.get("home_name"),
                          "date_iso": fx2.get("date_iso"), "league": fx2.get("league"),
                          "country": fx2.get("country")}
            if not fx or not fx.get("date_iso"):
                logger.info(f"Master Avatar: skip unverifiable fixture {home} v {away}")
                continue
            try:
                ko_dt = datetime.fromisoformat(fx["date_iso"].replace("Z", "+00:00"))
                hrs = (ko_dt - now).total_seconds() / 3600
                if not (0 <= hrs <= SMART_LOOKAHEAD_H):
                    continue  # game already started or too far out
                real_ko = ko_dt.strftime("%d/%m/%Y %H:%M")
                home = fx.get("home_name") or home
                away = fx.get("away_name") or away
                if fav == p.get("home"):
                    fav = home
                elif fav == p.get("away"):
                    fav = away
                real_league = fx.get("league") or real_league
                real_country = fx.get("country") or real_country
            except Exception:
                continue
        fg = (p.get("ph") or 0) if p.get("fav") == "home" else (p.get("pa") or 0)
        try:
            fg = int(round(float(fg)))
        except (TypeError, ValueError):
            fg = 0
        total = p.get("total") or 0
        over25, btts = bool(p.get("over25")), bool(p.get("btts"))
        # drought (cache-only, NO extra API quota)
        scored_last, _, _ = await _team_last_scored(fav, allow_api=False)
        drought = scored_last == 0
        minute = _avatar_goal_minute(fg, total, over25, btts, drought)
        at_home = p.get("fav") == "home"
        # In-form striker signal (owner Pavlidis-4-Tore learning). Cache-backed → cheap.
        avatar_player, avatar_scorer = None, False
        player_kind, player_line = None, None
        hs = await _hot_scorer_for_team(fav, _smart_seasons(real_ko))
        if hs and hs["prob"] >= 0.52:
            avatar_player, avatar_scorer = hs["name"], True
            player_kind = "scorer"
            brace_prob = _prob_over(1.5, hs["gl"])
            if hs["gl"] >= 0.8 and brace_prob >= 0.18:
                # red-hot striker → aim for the Doppelpack (owner: 'Pavlidis über 1.5')
                market = f"{hs['name']} — 2+ Tore (Doppelpack)"
                odds = float(_odds_from_prob(brace_prob))
                player_line = 1  # need = line+1 = 2 goals
                form = (f"hat zuletzt getroffen und ist nicht zu stoppen"
                        if not drought else f"ist heißhungrig")
                call = (f"{hs['name']} {form} — ich traue ihm in {home} – {away} einen DOPPELPACK "
                        f"zu ({hs['goals']} Saisontore). Bis zur {minute}. Minute liegt die erste Bude drin.")
                conf = min(82, int(round(brace_prob * 100)) + 30)
            else:
                market = f"{hs['name']} — Torschütze (Anytime)"
                odds = float(hs["odds"])
                player_line = 0  # need = 1 goal (anytime)
                form = (f"hat zuletzt NICHT getroffen und ist deshalb erst recht heiß"
                        if drought else f"ist in Galaform ({hs['goals']} Saisontore)")
                call = (f"{hs['name']} {form} — der trifft auch in {home} – {away}. "
                        f"Ich sehe sein Tor bis zur {minute}. Minute. {fav} setzt sich durch.")
                conf = min(90, int(round(hs["prob"] * 100)) + (5 if fg >= 2 else 0)
                           + (4 if drought else 0))
        elif minute <= 45:
            market = "Über 0.5 Tore 1. Halbzeit"
            odds = 1.30
            call = (f"In {home} – {away} sehe ich früh ein Tor. {fav} ist "
                    f"{'zuhause' if at_home else 'auswärts'} brandgefährlich — die Bude fällt "
                    f"schon in der 1. Halbzeit, bis zur {minute}. Minute. Klare Sache.")
            conf = min(96, 70 + (10 if fg >= 2 else 4) + (6 if over25 else 0)
                       + (4 if btts else 0) + (4 if drought else 0))
        else:
            market = f"{fav} Über 0.5 Tore"
            odds = 1.22 if fg >= 2 else 1.32
            call = (f"{fav} trifft in {home} – {away} — da bin ich mir sicher. "
                    f"{'Zuhause' if at_home else 'Auswärts'} zu stark; das Tor fällt bis zur "
                    f"{minute}. Minute.")
            if drought:
                call = (f"{fav} hat zuletzt NICHT getroffen — und genau deshalb sitzt sie diesmal. "
                        + call)
            conf = min(96, 70 + (10 if fg >= 2 else 4) + (6 if over25 else 0)
                       + (4 if btts else 0) + (4 if drought else 0))
        tid = f"master-av-{uuid.uuid4().hex[:8]}"
        await db.tips.insert_one({
            "id": tid, "user_id": bot["id"], "username": bot["username"],
            "is_master": True, "is_expert": False,
            "home_team": home, "away_team": away, "match_time": real_ko,
            "country": real_country, "league": real_league,
            "market": market, "odds": f"{odds:.2f}",
            "category": "banker", "master_category": "avatar", "master_day": day,
            "avatar_call": True, "avatar_minute": minute, "avatar_text": call,
            "avatar_confidence": conf, "drought": drought,
            "avatar_player": avatar_player, "avatar_scorer": avatar_scorer,
            "kind": player_kind, "line": player_line, "player": avatar_player,
            "ai_rating": round(min(9.6, 8.0 + conf / 100), 1),
            "ai_analysis": call,
            "legs": [], "is_parlay": False,
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-master", "created_at": now.isoformat(),
        })
        posted += 1
        logger.info(f"Master Avatar call: {fav} goal by {minute}' ({home} v {away}) — {market}")
    return {"posted": posted}


async def master_hotscorer_combo() -> dict:
    """Owner 2026-07-30 ('Konstantelias UND Pavlidis über 1.5 Tore → Hall of Fame'): once per
    Berlin day, combine 2-3 IN-FORM strikers from different verified fixtures into ONE aggressive
    'Doppelpack'-parlay ({Spieler} trifft 2+). High odds → a genuine Hall-of-Fame candidate."""
    now = datetime.now(timezone.utc)
    day = _berlin_now().date().isoformat()
    if await db.tips.count_documents(
            {"source": "hq-master", "master_category": "hotscorer",
             "status": {"$in": ["pending", "live"]}}):
        return {"skipped": "open"}
    if await db.tips.count_documents(
            {"source": "hq-master", "master_category": "hotscorer", "master_day": day}):
        return {"skipped": "done-today"}
    preds = await db.match_predictions.find({}, {"_id": 0}).to_list(1500)
    gift_map = await _gift_stance_map()
    picks, seen = [], set()
    for p in preds:
        if len(picks) >= 3:
            break
        if not _pred_whitelisted(p):
            continue
        fav = _fav_team(p)
        try:
            fp = int(float(p.get("fav_prob") or 0))
        except (TypeError, ValueError):
            fp = 0
        if not fav or fp < 60:
            continue
        ko = _parse_kickoff(p.get("kickoff"))
        if not ko:
            continue
        h = (ko - now).total_seconds() / 3600
        if h < 2 or h > SMART_LOOKAHEAD_H:
            continue
        key = _match_key(p.get("home"), p.get("away"))
        if key in seen:
            continue
        hs = await _hot_scorer_for_team(fav, _smart_seasons(p.get("kickoff")))
        if not hs or hs["gl"] < 0.6:  # brace-capable, genuinely prolific striker only
            continue
        brace_prob = _prob_over(1.5, hs["gl"])
        if brace_prob < 0.12:
            continue
        market = f"{hs['name']} trifft 2+ (Doppelpack)"
        if _conflicts_with_gift(market, p.get("home"), p.get("away"), gift_map.get(key)):
            continue
        # verify the fixture is real (no phantom games)
        home, away = p.get("home"), p.get("away")
        real_ko = p.get("kickoff") or ko.isoformat()
        if API_FOOTBALL_KEY:
            tidh = await resolve_team_id(home)
            fx = find_upcoming_fixture(tidh, away) if tidh else None
            if not fx or not fx.get("date_iso"):
                continue
            try:
                ko_dt = datetime.fromisoformat(fx["date_iso"].replace("Z", "+00:00"))
            except Exception:
                continue
            home = fx.get("home_name") or home
            away = fx.get("away_name") or away
            real_ko = ko_dt.strftime("%d/%m/%Y %H:%M")
        seen.add(key)
        picks.append({"match": f"{home} - {away}", "league": p.get("league") or "",
                      "kickoff": real_ko, "status": "pending",
                      "selections": [market], "sel_odds": [hs["odds"]],
                      "player": hs["name"], "goals": hs["goals"], "_ko": ko})
    if len(picks) < 2:
        return {"skipped": "not-enough", "have": len(picks)}
    combo = 1.0
    for pk in picks:
        combo *= float(pk["sel_odds"][0])
    combo = round(combo, 2)
    first_ko = min(pk["_ko"] for pk in picks)
    names = ", ".join(pk["player"] for pk in picks)
    for pk in picks:
        pk.pop("_ko", None)
    bot = await _get_master_bot()
    tid = f"master-hs-{uuid.uuid4().hex[:10]}"
    await db.tips.insert_one({
        "id": tid, "user_id": bot["id"], "username": bot["username"],
        "is_master": True, "is_expert": False,
        "home_team": "", "away_team": "", "match_time": first_ko.isoformat(),
        "market": f"🔥 Torjäger-Kombi — {len(picks)} Stürmer im Doppelpack", "odds": f"{combo:.2f}",
        "category": "value", "master_category": "hotscorer", "master_day": day,
        "ai_rating": 8.4,
        "ai_analysis": (f"🔥 Hall-of-Fame-Kandidat: {names} sind in Galaform und sollen JE einen "
                        f"Doppelpack (2+ Tore) schnüren. Aggressive Kombi mit Gesamtquote {combo:.2f} — "
                        f"kleiner Einsatz, großer Traum. Nur mit Köpfchen spielen."),
        "legs": picks, "is_parlay": True,
        "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
        "source": "hq-master", "created_at": now.isoformat(),
    })
    logger.info(f"Master Hot-Scorer combo: {names} @ {combo}")
    return {"posted": 1, "odds": combo, "players": len(picks)}




async def master_loop():
    await asyncio.sleep(240)  # let experts + live states populate first
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            if API_FOOTBALL_KEY:
                alt = await master_live_alternatives()
                con = await master_consensus()
                dp = await master_doublepack()
                packs = await master_build_packs()
                chal = await master_challenge()
                # Owner: the 8-leg "Safe Bets" slip fires at 00:30 Europe/Berlin.
                safe = {}
                b = _berlin_now()
                if b.hour == 0 and b.minute >= 30:
                    safe = await master_safe_bets_build()
                # Owner "Special": ALWAYS a fresh 4-game bet-builder combo each day.
                special = await master_special_build()
                # Owner "Avatar": up to 3 confident minute-goal calls per day (speech bubble).
                avatar = await master_avatar_calls()
                # Owner "Torjäger-Kombi": daily hot-scorer Doppelpack parlay (Hall-of-Fame shot).
                hotc = await master_hotscorer_combo()
                # Clean legacy slips of per-game redundant legs (BTTS ⇒ Über 1.5 etc.).
                await master_dedupe_open_slips()
                if alt.get("posted") or con.get("posted") or packs.get("posted") or dp.get("posted") \
                        or safe.get("posted") or special.get("posted") or avatar.get("posted") \
                        or hotc.get("posted") \
                        or chal.get("action") in ("opened", "advanced", "completed", "reset_lost"):
                    logger.info(f"Master: live-alt {alt}; consensus {con}; doublepack {dp}; packs {packs}; safe {safe}; special {special}; avatar {avatar}; hotscorer {hotc}; challenge {chal}")
        except Exception as e:
            logger.error(f"master_loop error: {e}")
        await asyncio.sleep(120)


async def enrich_member_picks() -> dict:
    """Member slips are AI-transliterated (e.g. Greek → 'Makara – Masoyk Royna') and
    often lack league / kickoff. Resolve the real fixture via API-Football and fill the
    canonical team names, league and match_time so the slip reads correctly for everyone."""
    if not API_FOOTBALL_KEY:
        return {"enriched": 0}
    picks = await db.tips.find(
        {"status": {"$in": ["pending", "live"]},
         "source": {"$nin": ["hq-auto", "hq-live", "hq-system", "smart", "hq-master"]},
         "username": {"$nin": ["TipJarHQ", "TipJarHQ System"]},
         "$or": [{"home_team_latin": {"$in": [None, ""]}},
                 {"league": {"$in": [None, ""]}},
                 {"league": {"$regex": "[Α-Ωα-ω]"}},
                 {"country": {"$regex": "[Α-Ωα-ω]"}},
                 {"legs.match": {"$regex": "[Α-Ωα-ω]"}},
                 {"legs.selections": {"$regex": "[Α-Ωα-ω]"}},
                 {"market": {"$regex": "[Α-Ωα-ω]"}},
                 {"match_time": {"$in": [None, "", "Multibet"]}}]},
        {"_id": 0, "id": 1, "home_team": 1, "away_team": 1, "league": 1, "country": 1,
         "home_team_latin": 1, "away_team_latin": 1,
         "match_time": 1, "legs": 1, "enrich_tries": 1}).to_list(400)
    live = None
    enriched = 0
    for t in picks:
        # Display fix (independent of any fixture): Greek team/league/country labels →
        # canonical English, and rewrite each leg's "A – B" so both the card AND the
        # live-score / settlement name-matching use real names (owner: "schreib die Teams
        # immer richtig"). Runs every pass but is idempotent (cached, no-op when clean).
        disp = await _canonicalize_display(t)
        if disp:
            disp["ai_corrected"] = True
            await db.tips.update_one({"id": t["id"]}, {"$set": disp, "$unset": {"share_image_path": ""}})
            for k, v in disp.items():
                t[k] = v
            enriched += 1
        if (t.get("enrich_tries") or 0) >= 6:
            continue
        home, away = _tip_match_teams(t)
        if not home or not away:
            # MULTI-GAME parlay: enrich each leg's league/kickoff individually so every
            # game shows its competition (owner 2026-07-24: "ich brauche die liga an jedes spiel").
            legs = t.get("legs") or []
            leg_changed = False
            for lg in legs:
                if (lg.get("league") or "").strip():
                    continue
                lh, la = _leg_teams(lg)
                if not lh or not la:
                    continue
                lmeta = None
                lh_c = await _canonical_team_name(lh) or lh
                la_c = await _canonical_team_name(la) or la
                ltid = await resolve_team_id(lh)
                if ltid:
                    lmeta = await asyncio.to_thread(find_upcoming_fixture, ltid, la_c)
                if not lmeta:
                    if live is None:
                        live = await asyncio.to_thread(_apifootball, "/fixtures", {"live": "all"}) or []
                    lfx = _find_live_fixture(live, lh_c, la_c)
                    if lfx:
                        lmeta = {"home_name": (lfx.get("teams", {}).get("home", {}) or {}).get("name", ""),
                                 "away_name": (lfx.get("teams", {}).get("away", {}) or {}).get("name", ""),
                                 "league": _fixture_league_label(lfx),
                                 "date_iso": (lfx.get("fixture") or {}).get("date")}
                if lmeta and (lmeta.get("league") or "").strip():
                    lg["league"] = lmeta["league"].strip()
                    # Canonical fixture team names → the leg's "match" string is rewritten so
                    # live-score matching (which parses match) works on real API names, not the
                    # transliterated ones (owner 2026-07-24: "jedes live-spiel braucht live score").
                    hn, an = (lmeta.get("home_name") or "").strip(), (lmeta.get("away_name") or "").strip()
                    if hn and an:
                        if _teams_match(an, lh_c) or _teams_match(hn, la_c):
                            hn, an = an, hn  # leg is reversed vs fixture
                        lg["match"] = f"{hn} \u2013 {an}"
                    if not (lg.get("kickoff") or "").strip() and lmeta.get("date_iso"):
                        try:
                            lko = datetime.fromisoformat(lmeta["date_iso"].replace("Z", "+00:00"))
                            lg["kickoff"] = lko.strftime("%d/%m/%Y %H:%M")
                        except Exception:
                            pass
                    leg_changed = True
                elif (lh_c != lh or la_c != la):
                    # No fixture yet, but fix the DISPLAY names from the canonical aliases.
                    lg["match"] = f"{lh_c} \u2013 {la_c}"
                    leg_changed = True
            if leg_changed:
                await db.tips.update_one(
                    {"id": t["id"]},
                    {"$set": {"legs": legs, "ai_corrected": True}, "$inc": {"enrich_tries": 1},
                     "$unset": {"share_image_path": ""}})
                enriched += 1
            else:
                await db.tips.update_one({"id": t["id"]}, {"$inc": {"enrich_tries": 1}})
            continue
        meta = None
        home_c = await _canonical_team_name(home) or home
        away_c = await _canonical_team_name(away) or away
        tid = await resolve_team_id(home)
        if tid:
            meta = await asyncio.to_thread(find_upcoming_fixture, tid, away_c)
        if not meta:  # currently in-play?
            if live is None:
                live = await asyncio.to_thread(_apifootball, "/fixtures", {"live": "all"}) or []
            fx = _find_live_fixture(live, home_c, away_c)
            if fx:
                meta = {"home_name": (fx.get("teams", {}).get("home", {}) or {}).get("name", ""),
                        "away_name": (fx.get("teams", {}).get("away", {}) or {}).get("name", ""),
                        "date_iso": (fx.get("fixture") or {}).get("date"),
                        "league": _fixture_league_label(fx)}
        if not meta or not meta.get("home_name"):
            # No fixture (past / not on API-Football) → still fix the DISPLAY names from the
            # canonical aliases so "ΛΟΥΚΕΡΝΗ" shows as "Luzern", not phonetic "LOYKERNI".
            partial = {}
            if _NON_LATIN_RE.search(home) and home_c and home_c != home:
                partial["home_team_latin"] = home_c
            if _NON_LATIN_RE.search(away) and away_c and away_c != away:
                partial["away_team_latin"] = away_c
            if partial:
                partial["ai_corrected"] = True
                await db.tips.update_one(
                    {"id": t["id"]},
                    {"$set": partial, "$inc": {"enrich_tries": 1},
                     "$unset": {"share_image_path": ""}})
                enriched += 1
            else:
                await db.tips.update_one({"id": t["id"]}, {"$inc": {"enrich_tries": 1}})
            continue
        if _teams_match(meta["away_name"], home_c) or _teams_match(meta["home_name"], away_c):
            hl, al = meta["away_name"], meta["home_name"]   # tip is reversed vs fixture
        else:
            hl, al = meta["home_name"], meta["away_name"]   # default: fixture home/away order
        upd = {"home_team_latin": hl, "away_team_latin": al,
               "needs_clarification": False, "clarification_fields": []}
        league_val = (meta.get("league") or "").strip()
        kickoff_val = ""
        if meta.get("date_iso"):
            try:
                ko = datetime.fromisoformat(meta["date_iso"].replace("Z", "+00:00"))
                kickoff_val = ko.strftime("%d/%m/%Y %H:%M")
            except Exception:
                kickoff_val = ""
        if league_val and not (t.get("league") or "").strip():
            upd["league"] = league_val
        if kickoff_val and (t.get("match_time") or "").strip() in ("", "Multibet"):
            upd["match_time"] = kickoff_val
        legs = t.get("legs") or []
        if len(legs) == 1:
            legs[0]["match"] = f"{hl} \u2013 {al}"
            if league_val and not (legs[0].get("league") or "").strip():
                legs[0]["league"] = league_val
            if kickoff_val and not (legs[0].get("kickoff") or "").strip():
                legs[0]["kickoff"] = kickoff_val
            upd["legs"] = legs
        if hl != home or al != away or "match_time" in upd:
            upd["ai_corrected"] = True
        await db.tips.update_one({"id": t["id"]}, {"$set": upd, "$inc": {"enrich_tries": 1}})
        enriched += 1
    return {"enriched": enriched}


async def _purge_unclarified_slips() -> int:
    """Auto-delete member slips whose teams the AI never understood and that the
    member didn't clarify within 12h (owner request 2026-07-16). Only fires when
    'teams' is still unresolved — enrichment clears the flag once teams are known."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=12)
    q = {"needs_clarification": True, "clarification_fields": "teams",
         "source": {"$nin": ["hq-auto", "hq-live", "hq-system", "smart", "hq-master"]}}
    stale = []
    for t in await db.tips.find(q, {"id": 1, "created_at": 1}).to_list(500):
        try:
            created = datetime.fromisoformat((t.get("created_at") or "").replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created <= cutoff:
                stale.append(t["id"])
        except Exception:
            continue
    if stale:
        await db.tips.delete_many({"id": {"$in": stale}})
        await db.tip_ratings.delete_many({"tip_id": {"$in": stale}})
        logger.info(f"Purged {len(stale)} unclarified slip(s) (teams unknown >12h)")
    return len(stale)








async def _regenerate_win_slips_once():
    """Re-render existing Hall-of-Fame win-claim slips with the current renderer.
    Idempotent via a 'slip_v5' flag so it only runs once per slip per renderer version."""
    await asyncio.sleep(20)
    try:
        claims = await db.win_claims.find(
            {"status": "approved", "slip_v5": {"$ne": True}},
            {"_id": 0}).to_list(200)
        n = 0
        for c in claims:
            legs = c.get("legs") or []
            if not legs:
                await db.win_claims.update_one({"id": c["id"]}, {"$set": {"slip_v5": True}})
                continue
            try:
                img = await asyncio.to_thread(
                    _render_slip_image, legs, c.get("total_odds") or 0, c.get("stake", ""),
                    c.get("winnings", ""), c.get("username", "TipJar"), c.get("type", "played"))
                res = await asyncio.to_thread(
                    put_object, f"{APP_NAME}/wins/{c.get('user_id', 'x')}/{uuid.uuid4()}.webp",
                    img, "image/webp")
                await db.files.insert_one({
                    "id": str(uuid.uuid4()), "storage_path": res["path"],
                    "original_filename": "win.webp", "content_type": "image/webp",
                    "owner": c.get("user_id", "system"), "is_deleted": False,
                    "created_at": datetime.now(timezone.utc).isoformat()})
                await db.win_claims.update_one(
                    {"id": c["id"]}, {"$set": {"image_path": res["path"], "slip_v5": True}})
                n += 1
            except Exception as ex:
                logger.error(f"regenerate slip {c.get('id')} failed: {ex}")
        if n:
            logger.info(f"Regenerated {n} Hall-of-Fame slip(s) with v4 renderer")
    except Exception as e:
        logger.error(f"regenerate win slips failed: {e}")


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


# --- Settlement engine extracted → settlement.py. Imported here (near the bottom)
# so every shared helper above is defined when settlement does `from server import ...`. ---
from settlement import (
    _h2h_first_leg, _matches_between, _reg_goals,
    find_finished_fixture, _datescan_fixture, _teams_match,
    judge_market,
    settle_pending_tips, settle_hq_combos, settle_multimatch_parlays,
    purge_settled_tips, expire_stale_pending, settlement_loop,
)


# --- Autopost scrapers extracted → scrapers_autopost.py. Imported here (near the
# bottom) so every shared helper above is already defined when that module does
# `from server import ...` (resolves the intentional circular import). ---
from scrapers_autopost import (
    forebet_autopost, forebet_loop,
    predictz_autopost, predictz_loop,
    apifootball_predictions_autopost, apifootball_predictions_loop,
    statarea_autopost, statarea_loop,
    footballpredictions_autopost, footballpredictions_loop,
    footballinsight_autopost, footballinsight_loop,
    betarades_autopost, betarades_loop,
    matchmoney_autopost, matchmoney_loop,
    foxbet_autopost, foxbet_loop,
    socialgamblers_autopost, socialgamblers_loop,
    bethome_autopost, bethome_loop,
    kingbet_autopost, kingbet_loop,
)


# --- Background-task loops + Web-Push engine extracted → background_tasks.py.
# Imported near the bottom so the engines above are defined when that module
# does `from server import ...` (resolves the intentional circular import). ---
from background_tasks import (
    _send_web_push, push_watch_loop, system_reset_loop, _leadership_loop,
    smart_loop, live_loop, member_live_loop, hide_unplayable_loop, api_burner_loop,
)


EXPERT_INACTIVITY_DAYS = 7


async def expire_inactive_experts() -> int:
    """Experts (real users, NOT in-house tipster bots) lose their title after 7 days without
    a new tip. They receive a mail with a 2-click reactivation CTA and can instantly become
    expert again. In-house bots (Orion/Vega/Nova/Sirius) are exempt (permanent personas)."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=EXPERT_INACTIVITY_DAYS)
    demoted = 0
    experts = await db.users.find(
        {"role": "expert", "is_bot": {"$ne": True}, "expert_permanent": {"$ne": True}},
        {"_id": 0, "id": 1, "expert_since": 1, "created_at": 1}).to_list(2000)
    for e in experts:
        last_tip = await db.tips.find_one(
            {"user_id": e["id"]}, sort=[("created_at", -1)], projection={"created_at": 1})
        ref = (last_tip or {}).get("created_at") or e.get("expert_since") or e.get("created_at")
        try:
            last_active = datetime.fromisoformat(ref)
            if last_active.tzinfo is None:
                last_active = last_active.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if last_active >= cutoff:
            continue  # still active within the last week
        await db.users.update_one(
            {"id": e["id"]},
            {"$set": {"role": "user", "expert_trial": False,
                      "expert_expired_at": now.isoformat()},
             "$unset": {"expert_since": ""}})
        demoted += 1
        # Reactivation letter — reuses the expert_invite CTA which /inbox/expert-accept
        # handles (2 clicks: open mail → "Wieder Experte werden"). Skip if one is pending.
        already = await db.inbox_messages.find_one(
            {"user_id": e["id"], "type": "expert_expired", "handled": {"$ne": True}})
        if not already:
            await db.inbox_messages.insert_one({
                "id": str(uuid.uuid4()), "user_id": e["id"], "type": "expert_expired",
                "title": "Dein Experten-Status ist pausiert ⏳",
                "body": ("Du warst 7 Tage inaktiv, daher haben wir deinen Experten-Titel "
                         "vorübergehend pausiert. Kein Problem — hol ihn dir mit nur 2 Klicks "
                         "sofort zurück und poste weiter deine Tipps! 🔥"),
                "cta": "expert_invite", "read": False, "handled": False,
                "created_at": now.isoformat(),
            })
    if demoted:
        logger.info(f"Expert expiry: {demoted} inactive expert(s) demoted + mailed")
    return demoted


async def expert_expiry_loop():
    """Checks for inactive experts a few times a day."""
    await asyncio.sleep(90)
    while True:
        try:
            await expire_inactive_experts()
        except Exception as e:
            logger.error(f"expert_expiry_loop error: {e}")
        await asyncio.sleep(6 * 3600)


async def daily_hof_autofill(max_new: int = 6) -> int:
    """Keep the Hall of Fame fresh: turn the best recent WON tips into branded trophy slips
    (auto-approved win_claims). Runs daily. Dedup by source tip id, so each win is added once."""
    now = datetime.now(timezone.utc)
    if now < HOF_START:
        return 0  # Hall of Fame officially opens 1 Aug 2026 — nothing before that
    since = (now - timedelta(days=7)).isoformat()
    won = await db.tips.find(
        {"status": "won", "created_at": {"$gte": since}, "hidden": {"$ne": True}}, {"_id": 0}).to_list(500)
    won.sort(key=lambda t: (_to_float(t.get("odds")) + (1.0 if t.get("is_parlay") else 0.0)),
             reverse=True)
    added = 0
    for tp in won:
        if added >= max_new:
            break
        # Owner rule 2026-07-26: SYSTEMS ONLY (parlays). TipJarHQ systems need quote ≥ 20.00,
        # everyone else ≥ 3.00. Single picks are forbidden — from ANY author.
        if not tp.get("is_parlay"):
            continue
        odds = _to_float(tp.get("odds"))
        if odds < _hof_min_odds(tp.get("username")):
            continue
        if await db.win_claims.find_one({"source_tip_id": tp["id"]}, {"_id": 1}):
            continue
        try:
            rlegs = _tip_to_render_legs(tp)
            if not rlegs:
                continue
            _disguise_stakes(tp)  # HoF trophies match the feed: $ + expert 12x / TipJarLogic x2
            stake = tp.get("stake") or "10 $"
            winnings = tp.get("potential_return") or _fmt_usd(odds * 10)
            img = await asyncio.to_thread(
                _render_slip_image, rlegs, odds, stake, winnings,
                tp.get("username", "TipJar"), "played")
            res = await asyncio.to_thread(
                put_object, f"{APP_NAME}/wins/hof/{uuid.uuid4()}.webp", img, "image/webp")
            path = res["path"]
            await db.files.insert_one({
                "id": str(uuid.uuid4()), "storage_path": path,
                "original_filename": "tipjar-hof.webp", "content_type": "image/webp",
                "owner": "tipjar-hof", "is_deleted": False, "created_at": now.isoformat()})
            await db.win_claims.insert_one({
                "id": str(uuid.uuid4()), "source_tip_id": tp["id"], "user_id": "tipjar-hof",
                "username": tp.get("username", "TipJar"), "type": "played", "image_path": path,
                "legs": rlegs, "legs_count": len(rlegs), "matched_legs": len(rlegs),
                "total_odds": odds, "stake": stake, "winnings": winnings,
                "credits": 0, "status": "approved", "auto_hof": True,
                "created_at": now.isoformat()})
            added += 1
        except Exception as ex:
            logger.error(f"daily HoF autofill failed for {tp.get('id')}: {ex}")
    if added:
        logger.info(f"Daily HoF autofill: added {added} trophy slip(s)")
    return added


async def daily_hof_loop():
    await asyncio.sleep(120)
    while True:
        try:
            await daily_hof_autofill()
        except Exception as e:
            logger.error(f"daily_hof_loop error: {e}")
        await asyncio.sleep(24 * 3600)  # once a day


async def expert_bot_voting() -> dict:
    """Owner 2026-07: in-house expert bots quietly rate each other's and the Master's tips
    (a few random star votes per day). One vote-day advances a rating streak; a 30-day streak
    unlocks the 🔥 Apex-Flamme — so experts EARN the badge over time instead of being handed
    it. Flames only become visible on 1 Sep 2026 (flamesActive), by which point streaks are up."""
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    bots = await db.users.find({"is_bot": True, "role": "expert"}, {"_id": 0}).to_list(200)
    if not bots:
        return {"voted": 0}
    pool = await db.tips.find(
        {"$or": [{"is_expert": True}, {"is_master": True}, {"source": "hq-master"}],
         "hidden": {"$ne": True}},
        {"_id": 0, "id": 1, "user_id": 1, "sum_stars": 1, "ratings_count": 1}
    ).sort("created_at", -1).to_list(400)
    voted = 0
    for bot in bots:
        if bot.get("last_rated_date") == today:
            continue  # one streak-step per bot per day
        # a flame handed out at creation is reset so it is genuinely earned via the streak
        if bot.get("apex_flame") and bot.get("streak", 0) < APEX_FLAME_STREAK:
            await db.users.update_one({"id": bot["id"]}, {"$set": {"apex_flame": False}})
        targets = [t for t in pool if t.get("user_id") != bot["id"]]
        if not targets:
            continue
        random.shuffle(targets)
        for t in targets[:random.randint(1, 4)]:  # sparse: a few peer tips per day
            if await db.tip_ratings.find_one({"tip_id": t["id"], "user_id": bot["id"]}):
                continue
            stars = random.choices([3, 4, 5], weights=[2, 4, 5])[0]
            await db.tip_ratings.insert_one({
                "id": str(uuid.uuid4()), "tip_id": t["id"], "user_id": bot["id"],
                "stars": stars, "created_at": now.isoformat()})
            new_sum = (t.get("sum_stars", 0) or 0) + stars
            new_count = (t.get("ratings_count", 0) or 0) + 1
            await db.tips.update_one({"id": t["id"]}, {"$set": {
                "sum_stars": new_sum, "ratings_count": new_count,
                "avg_rating": round(new_sum / new_count, 1)}})
        await _bump_rating_streak(bot, now)  # +1 streak day → 🔥 at 30 (existing helper)
        voted += 1
    return {"voted": voted}


async def expert_vote_loop():
    await asyncio.sleep(300)
    while True:
        if not _is_leader():
            await asyncio.sleep(120)
            continue
        try:
            res = await expert_bot_voting()
            if res.get("voted"):
                logger.info(f"Expert bot voting: {res}")
        except Exception as e:
            logger.error(f"expert_vote_loop error: {e}")
        await asyncio.sleep(3 * 3600)  # a few times/day; per-day guard prevents duplicates


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
    # Pre-seed the one league we've CONFIRMED is uncoverable by API-Football (current Chinese
    # Super League 'cn1' — teams resolve but have zero fixtures). $setOnInsert keeps it a
    # one-time seed so a later manual unblock (if API-Football adds coverage) is respected.
    try:
        await db.league_settle_health.update_one(
            {"code": "cn1"},
            {"$setOnInsert": {"code": "cn1", "blocked": True, "hits": 0, "misses": 999,
                              "blocked_at": datetime.now(timezone.utc).isoformat(),
                              "note": "auto-seed: not covered by API-Football"}},
            upsert=True)
    except Exception as e:
        logger.error(f"cn1 blacklist seed: {e}")
    await _refresh_blocked_leagues()
    asyncio.create_task(_startup_seed())
    _BG_TASKS.append(asyncio.create_task(_leadership_loop()))
    _BG_TASKS.append(asyncio.create_task(settlement_loop()))
    _BG_TASKS.append(asyncio.create_task(learning_loop()))
    _BG_TASKS.append(asyncio.create_task(forebet_loop()))
    _BG_TASKS.append(asyncio.create_task(predictz_loop()))
    _BG_TASKS.append(asyncio.create_task(apifootball_predictions_loop()))
    _BG_TASKS.append(asyncio.create_task(statarea_loop()))
    _BG_TASKS.append(asyncio.create_task(footballpredictions_loop()))
    _BG_TASKS.append(asyncio.create_task(footballinsight_loop()))
    _BG_TASKS.append(asyncio.create_task(betarades_loop()))
    _BG_TASKS.append(asyncio.create_task(matchmoney_loop()))
    _BG_TASKS.append(asyncio.create_task(foxbet_loop()))
    _BG_TASKS.append(asyncio.create_task(socialgamblers_loop()))
    _BG_TASKS.append(asyncio.create_task(bethome_loop()))
    _BG_TASKS.append(asyncio.create_task(kingbet_loop()))
    _BG_TASKS.append(asyncio.create_task(emptips_loop()))
    _BG_TASKS.append(asyncio.create_task(totissports_loop()))
    _BG_TASKS.append(asyncio.create_task(smart_loop()))
    _BG_TASKS.append(asyncio.create_task(live_loop()))
    _BG_TASKS.append(asyncio.create_task(member_live_loop()))
    _BG_TASKS.append(asyncio.create_task(push_watch_loop()))
    _BG_TASKS.append(asyncio.create_task(backfill_leg_odds_once()))
    _BG_TASKS.append(asyncio.create_task(_regenerate_win_slips_once()))
    _BG_TASKS.append(asyncio.create_task(daily_hof_loop()))
    _BG_TASKS.append(asyncio.create_task(system_reset_loop()))
    _BG_TASKS.append(asyncio.create_task(expert_expiry_loop()))
    _BG_TASKS.append(asyncio.create_task(expert_vote_loop()))
    _BG_TASKS.append(asyncio.create_task(master_loop()))
    _BG_TASKS.append(asyncio.create_task(hide_unplayable_loop()))
    _BG_TASKS.append(asyncio.create_task(api_burner_loop()))
    if API_FOOTBALL_KEY:
        logger.info("Auto-settlement engine enabled (API-Football)")
    else:
        logger.info("Auto-settlement idle — set API_FOOTBALL_KEY to enable")


async def _seed_showcase_wins():
    """Idempotently seed owner-curated Hall-of-Fame showcase slips (runs on startup, incl.
    production). Data — not code — so a deploy alone wouldn't carry it over; this seed inserts
    it into whichever DB the backend connects to, guarded by the leg signature (never dupes)."""
    showcase = [
        {
            "username": "TipJarLogic", "type": "played",
            "total_odds": 12.25, "stake": "4 $", "winnings": "49 $",
            "legs": [
                {"home": "Hammarby IF", "away": "RSC Anderlecht", "market": "Unentschieden (X)",
                 "odds": 3.50, "result": "1:1", "league": "UEFA Europa League", "date": "",
                 "time": "23.07. \u00b7 19:00"},
                {"home": "FK Panevezys", "away": "Tobol Kostanay", "market": "Unentschieden (X)",
                 "odds": 3.50, "result": "1:1", "league": "UCL Quali", "date": "",
                 "time": "23.07. \u00b7 17:30"},
            ],
        },
    ]
    for s in showcase:
        try:
            legs = s["legs"]
            sig = hashlib.md5(("|".join(sorted(f"{l['home']}-{l['away']}-{l['market']}" for l in legs))
                               + f"|{s['total_odds']}").encode()).hexdigest()
            if await db.win_claims.find_one({"sig": sig}):
                continue
            img = await asyncio.to_thread(
                _render_slip_image, legs, s["total_odds"], s["stake"], s["winnings"],
                s["username"], s["type"])
            res = await asyncio.to_thread(
                put_object, f"{APP_NAME}/wins/showcase/{uuid.uuid4()}.webp", img, "image/webp")
            image_path = res["path"]
            now = datetime.now(timezone.utc).isoformat()
            await db.files.insert_one({
                "id": str(uuid.uuid4()), "storage_path": image_path,
                "original_filename": "tipjar-slip.webp", "content_type": "image/webp",
                "owner": "tipjar-showcase", "is_deleted": False, "created_at": now})
            await db.win_claims.insert_one({
                "id": str(uuid.uuid4()), "sig": sig, "user_id": "tipjar-showcase",
                "username": s["username"], "type": s["type"], "image_path": image_path,
                "legs": legs, "legs_count": len(legs), "matched_legs": len(legs),
                "total_odds": s["total_odds"], "stake": s["stake"], "winnings": s["winnings"],
                "credits": 0, "status": "approved", "created_at": now})
            logger.info(f"Seeded showcase win: {s['username']} @ {s['total_odds']}")
        except Exception as ex:
            logger.error(f"showcase win seed failed: {ex}")



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
        if blank.deleted_count or stale_reports.deleted_count:
            logger.info(f"Smart cleanup: {blank.deleted_count} blank ideas, "
                        f"{stale_reports.deleted_count} stale/void smart reports removed")
        # Drop failed team-name resolutions so the localized-name map (Frankreich→France)
        # takes effect on the next settlement pass.
        await db.team_cache.delete_many({"team_id": None})
        # Give stuck parlays (smart / system / member) a fresh settlement chance after the
        # engine fixes (localized team names, datescan, aggregate grading). Their retry
        # budget may have been burned by the OLD code that couldn't resolve teams.
        reset = await db.tips.update_many(
            {"is_parlay": True, "status": {"$in": ["pending", "live"]},
             "settle_attempts": {"$gt": 0}},
            {"$set": {"settle_attempts": 0}})
        if reset.modified_count:
            logger.info(f"Reset settle_attempts on {reset.modified_count} stuck parlays")
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


async def _delete_stuck_makara_pick():
    """One-off (owner request 2026-07-16): remove james76's unresolvable live slip
    'Makara – Masoyk Royna'. Matched narrowly on username + garbled team text so
    nothing else is touched. Runs on deploy; safe/idempotent."""
    try:
        rx = {"$regex": "makar|masoyk|royna", "$options": "i"}
        q = {"username": {"$regex": "^james", "$options": "i"},
             "$or": [{"home_team": rx}, {"away_team": rx},
                     {"legs.match": rx}]}
        ids = [t["id"] for t in await db.tips.find(q, {"id": 1}).to_list(50)]
        if ids:
            await db.tips.delete_many({"id": {"$in": ids}})
            await db.tip_ratings.delete_many({"tip_id": {"$in": ids}})
            logger.info(f"Deleted stuck Makara pick(s): {len(ids)}")
    except Exception as e:
        logger.error(f"Makara cleanup failed: {e}")


async def _delete_owner_flagged_tips():
    """Owner-requested removals (2026-07-16), runs on every startup incl. production;
    idempotent — only deletes when the flagged records still exist.
    1) A garbled 'Makara/Mascara' slip in Community (member picks only, never HQ/AI).
    2) A stale 'Frankreich' (France / Marokko) pick in Smart Picks."""
    try:
        # 1) Community 'mascara/makara' member slip
        mrx = {"$regex": "makar|mascar|masoyk", "$options": "i"}
        member_q = {
            "source": {"$nin": ["hq-auto", "hq-system", "hq-live", "smart"]},
            "$or": [{"home_team": mrx}, {"away_team": mrx},
                    {"legs.match": mrx}, {"market": mrx}],
        }
        mids = [t["id"] for t in await db.tips.find(member_q, {"id": 1}).to_list(100)]
        # 2) Smart 'Frankreich / France / Marokko' pick
        frx = {"$regex": "frankreich|france|marokko|morocco", "$options": "i"}
        smart_q = {
            "source": "smart",
            "$or": [{"home_team": frx}, {"away_team": frx},
                    {"legs.match": frx}, {"market": frx}, {"ai_analysis": frx}],
        }
        sids = [t["id"] for t in await db.tips.find(smart_q, {"id": 1}).to_list(100)]
        ids = list(set(mids + sids))
        if ids:
            await db.tips.delete_many({"id": {"$in": ids}})
            await db.tip_ratings.delete_many({"tip_id": {"$in": ids}})
            logger.info(f"Owner-flagged cleanup: removed {len(mids)} community + {len(sids)} smart pick(s)")
        # Remove the matching 'Eingegangene Idee' feed card(s): the France/England question
        # that got published as a weak pick (linked via tip_id) so the input disappears too.
        idea_res = await db.smart_ideas.delete_many({
            "$or": [{"tip_id": {"$in": ids}} if ids else {"_id": None},
                    {"text": {"$regex": "frankreich.*england|england.*frankreich|france.*england|england.*france",
                              "$options": "i"}}]})
        if getattr(idea_res, "deleted_count", 0):
            logger.info(f"Owner-flagged cleanup: removed {idea_res.deleted_count} smart idea(s)")
    except Exception as e:
        logger.error(f"Owner-flagged cleanup failed: {e}")


async def _backfill_inbox():
    """Idempotently give existing regular members a welcome + Expert-invite in their
    mailbox (runs on startup, incl. production). Admins and users already seeded are skipped."""
    try:
        users = await db.users.find(
            {"inbox_seeded": {"$ne": True}, "role": "user"},
            {"_id": 0, "id": 1}).to_list(10000)
        for u in users:
            await _seed_inbox_for_new_user(u)
        if users:
            logger.info(f"Backfilled mailbox for {len(users)} users")
    except Exception as e:
        logger.error(f"Inbox backfill failed: {e}")


async def _seed_hof_showcase_slip():
    """Idempotently add tipster 'tipjarlogic's won treble to the Hall of Fame (owner
    request 2026-07-17). Fixed id → runs once; only (re)renders if the image is missing."""
    claim_id = "seed-tipjarlogic-treble-5199919010"
    legs = [
        {"home": "Univ Cluj", "away": "Dynamo Kyiv", "league": "UEFA Champions League – Quali",
         "date": "16.07.2026", "time": "19:30", "market": "Dynamo Kyiv qualifiziert sich",
         "odds": 1.36, "result": "0:0", "won": True},
        {"home": "CRB", "away": "Nautico", "league": "Brasilien Série B",
         "date": "17.07.2026", "time": "01:00", "market": "CRB Über 0,5 + Über 1,5 Tore",
         "odds": 1.35, "result": "2:1", "won": True},
        {"home": "Valerenga IF", "away": "Aalesunds", "league": "Norwegen Eliteserien",
         "date": "16.07.2026", "time": "19:00", "market": "Doppelte Chance 12",
         "odds": 1.19, "result": "6:1", "won": True},
    ]
    total_odds, stake, winnings = 2.19, "20,00 €", "43,83 €"
    existing = await db.win_claims.find_one({"id": claim_id})
    if existing and existing.get("image_path"):
        return
    user = await db.users.find_one({"username": {"$regex": "^tipjarlogic$", "$options": "i"}})
    uid = user["id"] if user else "tipjarlogic"
    uname = user["username"] if user else "tipjarlogic"
    image_path = None
    try:
        img = await asyncio.to_thread(_render_slip_image, legs, total_odds, stake, winnings, uname, "played")
        res = await asyncio.to_thread(
            put_object, f"{APP_NAME}/wins/{uid}/{uuid.uuid4()}.webp", img, "image/webp")
        image_path = res["path"]
        await db.files.insert_one({
            "id": str(uuid.uuid4()), "storage_path": image_path,
            "original_filename": "tipjar-slip.webp", "content_type": "image/webp",
            "owner": uid, "is_deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat()})
    except Exception as ex:
        logger.error(f"HoF showcase slip render failed: {ex}")
        return
    await db.win_claims.update_one({"id": claim_id}, {"$set": {
        "id": claim_id, "user_id": uid, "username": uname, "type": "played",
        "image_path": image_path, "legs": legs, "legs_count": 3, "matched_legs": 3,
        "total_odds": total_odds, "stake": stake, "winnings": winnings, "credits": 0,
        "status": "approved", "slip_v5": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }}, upsert=True)
    logger.info("Seeded Hall-of-Fame showcase slip for @tipjarlogic")


async def _startup_seed():
    try:
        await purge_demo_tips()
        await _delete_stuck_makara_pick()
        await _delete_owner_flagged_tips()
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
        # Ensure ALL configured tipster-clone bots exist so every expert (Orion/Vega/Nova/
        # Sirius) always shows in the "Our Experts" showcase — not only after first post.
        _seen_bot = set()
        for _cfg in _CHANNEL_BOTS.values():
            if _cfg["email"] in _seen_bot:
                continue
            _seen_bot.add(_cfg["email"])
            try:
                await _get_expert_bot(_cfg)
            except Exception as e:
                logger.warning(f"seed expert bot {_cfg.get('name')}: {e}")
        # Backfill mailbox (welcome + expert invite) for existing users who never got one.
        await _backfill_inbox()
        await seed_showcase()
        await _migrate_stars_and_categories()
        await _cleanup_smart_junk()
        # Owner rule 2026-07-26: Hall of Fame opens 1 Aug 2026 and holds SYSTEMS ONLY.
        # Purge every single-pick and every trophy created before the official start, plus
        # any system below its author's quote bar (TipJarHQ ≥ 20.00, others ≥ 3.00).
        await db.win_claims.delete_many(
            {"$or": [{"legs_count": {"$lt": 2}},
                     {"total_odds": {"$lt": HOF_MIN_ODDS_DEFAULT}},
                     {"created_at": {"$lt": HOF_START.isoformat()}}]})
        async for c in db.win_claims.find(
                {"total_odds": {"$lt": HOF_MIN_ODDS_HOUSE}},
                {"_id": 1, "username": 1, "total_odds": 1}):
            if _to_float(c.get("total_odds")) < _hof_min_odds(c.get("username")):
                await db.win_claims.delete_one({"_id": c["_id"]})
        # Germany boycotts ALL Russian football — hide any open Russian fixture that slipped
        # into the feed before the scraper lock-down (runs on prod too after deploy).
        rus_re = re.compile("|".join(re.escape(k) for k in RUSSIA_KEYWORDS), re.I)
        await db.tips.update_many(
            {"status": {"$in": ["pending", "live"]}, "hidden": {"$ne": True},
             "$or": [{"home_team": rus_re}, {"away_team": rus_re}, {"league": rus_re},
                     {"legs.match": rus_re}, {"legs.league": rus_re}]},
            {"$set": {"hidden": True, "hidden_reason": "russia_boycott"}})
        # De-duplicate the Smart feed: one pick per fixture (owner 2026-07-29 saw the same tip
        # multiple times). Prefer the Qualifikations-Pick (qual-) over the Favoriten-Kombi.
        smart_open = await db.tips.find(
            {"source": "smart", "status": {"$in": ["pending", "live"]}, "hidden": {"$ne": True}},
            {"_id": 0, "id": 1, "home_team": 1, "away_team": 1}).to_list(1000)
        seen_fix, dup_ids = {}, []
        for tp in sorted(smart_open, key=lambda x: 0 if str(x.get("id", "")).startswith("qual-") else 1):
            fk = _norm(f"{tp.get('home_team', '')} {tp.get('away_team', '')}")
            if not fk:
                continue
            if fk in seen_fix:
                dup_ids.append(tp["id"])
            else:
                seen_fix[fk] = tp["id"]
        if dup_ids:
            await db.tips.update_many(
                {"id": {"$in": dup_ids}},
                {"$set": {"hidden": True, "hidden_reason": "smart_dup"}})
            logger.info(f"Smart de-dup: hid {len(dup_ids)} duplicate smart picks")
    except Exception as e:
        logger.error(f"Startup seed failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    for task in _BG_TASKS:
        task.cancel()
    if _BG_TASKS:
        await asyncio.gather(*_BG_TASKS, return_exceptions=True)
    client.close()


# Include ALL API routes now that every endpoint above is defined (fixes late-defined
# routes like /code-reading, /learning/stats never being registered).
app.include_router(api_router)
