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
SETTLE_BATCH_CAP = 50   # max tips processed per settlement run (Pro plan: 7500 req/day)
FINISHED_STATUSES = {"FT", "AET", "PEN"}

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
        "week": datetime.now(timezone.utc).strftime("KW %V"),
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
    now = datetime.now(timezone.utc)
    ai_docs = await db.tips.find(
        {"source": "hq-auto", "status": "pending", "is_parlay": {"$ne": True}},
        {"match_time": 1}).to_list(500)
    ai = sum(1 for d in ai_docs if _in_kickoff_window(d.get("match_time"), "24", now))
    ai_total = len(ai_docs)
    members = await db.tips.count_documents({"source": {"$nin": ["hq-auto", "smart"]}, "status": "pending"})
    live = await db.tips.count_documents({"status": "live"})
    smart = await db.tips.count_documents({"source": "smart", "status": "pending"})
    try:
        sysdata = await build_systems()
        systems_n = sum(1 for s in sysdata["systems"] if len(s["selections"]) >= 2)
    except Exception:
        systems_n = 0
    return {"ai": ai, "ai_total": ai_total, "members": members, "live": live, "systems": systems_n, "smart": smart}




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
class RegisterInput(BaseModel):
    email: Optional[EmailStr] = None
    password: str = Field(min_length=6)
    username: str = Field(min_length=2, max_length=24)
    timezone: str = "UTC"
    language: str = "en"
    ref: Optional[str] = None
    origin_url: Optional[str] = None


class VerifyInput(BaseModel):
    token: str


class OriginInput(BaseModel):
    origin_url: Optional[str] = None


class LoginInput(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: str


class ProfileUpdate(BaseModel):
    username: Optional[str] = Field(default=None, min_length=2, max_length=24)
    timezone: Optional[str] = None
    language: Optional[str] = None


class TipSaveInput(BaseModel):
    raw_text: str = ""
    image_path: Optional[str] = None
    home_team: str = ""
    away_team: str = ""
    match_time: str = ""
    country: str = ""
    league: str = ""
    market: str = ""
    odds: str = ""
    ai_rating: float = 0
    ai_analysis: str = ""
    legs: Optional[List[dict]] = None
    is_parlay: bool = False
    stake: str = ""
    potential_return: str = ""


class RateInput(BaseModel):
    stars: int = Field(ge=1, le=10)


class GiftInput(BaseModel):
    to_username: str
    amount: int = Field(gt=0)


class CheckoutInput(BaseModel):
    package_id: str
    origin_url: str


class SubscribeInput(BaseModel):
    anon_id: str


class StatusInput(BaseModel):
    status: str  # won | lost | pending


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
    "'Djurgarden Total Over 0.5', 'Fouls Over 21.5'\"]}), "
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
                out.append({
                    "match": str(lg.get("match", "") or ""),
                    "league": str(lg.get("league", "") or ""),
                    "kickoff": str(lg.get("kickoff", "") or ""),
                    "selections": [str(s) for s in sels if s][:10],
                })
    return out[:12]


async def analyze_tip(image_b64: Optional[str], text: str) -> dict:
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
        if image_b64:
            kwargs["file_contents"] = [ImageContent(image_base64=image_b64)]
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
async def analyze(file: Optional[UploadFile] = File(default=None), text: str = Form(default=""),
                  user: dict = Depends(get_current_user)):
    image_b64 = None
    raw_bytes = None
    file_meta = None
    if file is not None:
        raw_bytes = await file.read()
        image_b64 = base64.b64encode(raw_bytes).decode("utf-8")
        file_meta = file
    # Moderate (image + text) FIRST — never store or publish unsafe content.
    detected = await analyze_tip(image_b64, text)
    if not detected.get("safe", True):
        raise HTTPException(
            status_code=422,
            detail=(detected.get("flag_reason")
                    or "This content can't be posted (offensive or not a bet slip)."),
        )
    # Only now upload the image to storage.
    image_path = None
    if raw_bytes is not None:
        ext = (file_meta.filename.rsplit(".", 1)[-1] if file_meta.filename and "." in file_meta.filename else "png").lower()
        path = f"{APP_NAME}/tips/{user['id']}/{uuid.uuid4()}.{ext}"
        try:
            result = put_object(path, raw_bytes, file_meta.content_type or "image/png")
            image_path = result["path"]
            await db.files.insert_one({
                "id": str(uuid.uuid4()), "storage_path": image_path,
                "original_filename": file_meta.filename, "content_type": file_meta.content_type,
                "owner": user["id"], "is_deleted": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.error(f"upload failed: {e}")
    detected["image_path"] = image_path
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


@api_router.post("/tips")
async def create_tip(inp: TipSaveInput, user: dict = Depends(get_current_user)):
    legs = _sanitize_legs(inp.legs)
    is_parlay = inp.is_parlay or (inp.legs is not None and len(inp.legs) > 1)
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
    tip = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "username": user["username"],
        "raw_text": inp.raw_text,
        "image_path": inp.image_path,
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
        "status": "pending",
        "sum_stars": 0,
        "ratings_count": 0,
        "avg_rating": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tips.insert_one(tip)
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
                    limit: int = 50):
    q = {}
    if status:
        q["status"] = status
    if source == "ai":
        q["source"] = "hq-auto"
    elif source == "smart":
        q["source"] = "smart"
    elif source == "members":
        q["source"] = {"$nin": ["hq-auto", "smart"]}
    limit = max(1, min(limit, 100))
    fetch = 300 if window in ("24", "48", "48plus") else limit
    if sort == "top":
        cursor = db.tips.find(q, {"_id": 0}).sort([("avg_rating", -1), ("ratings_count", -1)]).limit(fetch)
    elif sort == "hype":
        cursor = db.tips.find(q, {"_id": 0}).sort("ai_rating", -1).limit(fetch)
    else:
        cursor = db.tips.find(q, {"_id": 0}).sort("created_at", -1).limit(fetch)
    tips = await cursor.to_list(fetch)
    if window in ("24", "48", "48plus") and status in (None, "pending"):
        now = datetime.now(timezone.utc)
        tips = [t for t in tips if _in_kickoff_window(t.get("match_time"), window, now)][:limit]
    return tips


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

    fresh = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    return {"tip": fresh, "streak": streak, "your_stars": inp.stars}


@api_router.put("/tips/{tip_id}/status")
async def set_status(tip_id: str, inp: StatusInput, admin: dict = Depends(require_admin)):
    if inp.status not in ("won", "lost", "pending"):
        raise HTTPException(status_code=400, detail="Invalid status")
    res = await db.tips.update_one({"id": tip_id}, {"$set": {"status": inp.status}})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tip not found")
    tip = await db.tips.find_one({"id": tip_id}, {"_id": 0})
    return tip


# ------------------------------------------------------------------ leaderboard
@api_router.get("/leaderboard")
async def leaderboard():
    pipeline = [
        {"$group": {
            "_id": "$user_id",
            "username": {"$first": "$username"},
            "total": {"$sum": 1},
            "won": {"$sum": {"$cond": [{"$eq": ["$status", "won"]}, 1, 0]}},
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
WIN_MIN_PLAYED_LEGS = 5          # a played-along slip must have >= 5 legs
WIN_MIN_SYSTEM_MATCH = 3         # >= 3 legs must match a TipJar system (anti-fraud)
WIN_LIVE_MIN_LEGS = 4            # live streak: 4 in a row
WIN_LIVE_MIN_ODDS = 1.60         # each live leg must be > 1.60
WIN_POSTED_CREDITS = 20
WIN_LIVE_CREDITS = 20
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
            '{"status":"won|lost|open","total_odds":<number>,"stake":"","winnings":"",'
            '"legs":[{"home":"","away":"","market":"","odds":<number>,"result":"won|lost|open"}]}. '
            "status is the overall slip result. Extract every leg. If a value is missing use empty/0."
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
    try:
        data = await build_systems()
    except Exception:
        return set()
    keys = set()
    for sysd in data.get("systems", []):
        for sel in sysd.get("selections", []):
            keys.add(_match_key(sel.get("home_team"), sel.get("away_team")))
    return keys


@api_router.post("/wins/claim")
async def claim_win(file: UploadFile = File(...), type: str = Form(...),
                    user: dict = Depends(get_current_user)):
    ctype = (type or "").strip().lower()
    if ctype not in ("played", "posted", "live"):
        raise HTTPException(status_code=400, detail="Invalid claim type")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="No file uploaded")
    image_b64 = base64.b64encode(raw).decode("utf-8")
    slip = await extract_win_slip(image_b64)

    if slip["status"] != "won":
        raise HTTPException(status_code=422, detail="Nur GEWONNENE Scheine zählen (Slip ist nicht 'Won').")
    legs = slip["legs"]
    legs_n = len(legs)
    if legs_n < 2:
        raise HTTPException(status_code=422, detail="Kein gültiger Kombi-Schein erkannt.")

    # anti-duplicate: same set of legs can't be claimed twice
    sig = hashlib.md5(("|".join(sorted(f"{l['home']}-{l['away']}-{l['market']}" for l in legs))
                       + f"|{slip['total_odds']}").encode()).hexdigest()
    if await db.win_claims.find_one({"sig": sig}):
        raise HTTPException(status_code=409, detail="Dieser Schein wurde bereits eingereicht.")

    sys_keys = await _system_match_keys()
    matched = sum(1 for l in legs if _match_key(l["home"], l["away"]) in sys_keys)

    if ctype == "live":
        if legs_n < WIN_LIVE_MIN_LEGS:
            raise HTTPException(status_code=422, detail=f"Live-Serie braucht mind. {WIN_LIVE_MIN_LEGS} Picks.")
        if any((l["odds"] or 0) <= WIN_LIVE_MIN_ODDS for l in legs):
            raise HTTPException(status_code=422, detail=f"Jede Live-Auswahl muss Quote > {WIN_LIVE_MIN_ODDS} haben.")
        credits = WIN_LIVE_CREDITS
    else:
        if matched < WIN_MIN_SYSTEM_MATCH:
            raise HTTPException(status_code=422,
                                detail="Das zählt nicht als mitgespielt — der Schein passt zu keinem TipJar-System.")
        if ctype == "played":
            if legs_n < WIN_MIN_PLAYED_LEGS:
                raise HTTPException(status_code=422, detail=f"Mitgespielter Schein braucht mind. {WIN_MIN_PLAYED_LEGS} Legs.")
            credits = min(WIN_MAX_CREDITS, WIN_MIN_PLAYED_LEGS + (legs_n - WIN_MIN_PLAYED_LEGS))
        else:  # posted
            credits = WIN_POSTED_CREDITS

    # store image now that the claim is valid
    ext = (file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png").lower()
    image_path = None
    try:
        result = put_object(f"{APP_NAME}/wins/{user['id']}/{uuid.uuid4()}.{ext}", raw,
                            file.content_type or "image/png")
        image_path = result["path"]
    except Exception as ex:
        logger.error(f"win image upload failed: {ex}")

    claim = {
        "id": str(uuid.uuid4()), "sig": sig, "user_id": user["id"], "username": user["username"],
        "type": ctype, "image_path": image_path, "legs": legs, "legs_count": legs_n,
        "matched_legs": matched, "total_odds": slip["total_odds"], "stake": slip["stake"],
        "winnings": slip["winnings"], "credits": credits, "status": "approved",
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
    return {"subscribed": True, "subscriber_count": count}


@api_router.post("/notifications/unsubscribe")
async def unsubscribe(inp: SubscribeInput):
    await db.subscribers.delete_one({"anon_id": inp.anon_id})
    count = await db.subscribers.count_documents({})
    return {"subscribed": False, "subscriber_count": count}


@api_router.get("/stats")
async def community_stats():
    members = await db.users.count_documents({"role": {"$ne": "admin"}})
    subs = await db.subscribers.count_documents({})
    tips = await db.tips.count_documents({})
    return {"members": members, "goal": 1000, "subscribers": subs, "total_tips": tips}


@api_router.get("/notifications/stats")
async def notif_stats():
    count = await db.subscribers.count_documents({})
    total = await db.tips.count_documents({})
    return {"subscriber_count": count, "total_tips": total}


# ------------------------------------------------------------------ files
@api_router.get("/files/{path:path}")
async def download_file(path: str):
    record = await db.files.find_one({"storage_path": path, "is_deleted": False})
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    data, content_type = get_object(path)
    return Response(content=data, media_type=record.get("content_type") or content_type)


# ------------------------------------------------------------------ results engine (API-Football)
def _norm(s: str) -> str:
    return "".join(c for c in (s or "").lower() if c.isalnum() or c.isspace()).strip()


def _teams_match(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    ta, tb = set(na.split()), set(nb.split())
    common = ta & tb
    stop = {"fc", "cf", "sc", "ac", "club", "de", "the", "and"}
    common = {w for w in common if w not in stop and len(w) > 2}
    return len(common) >= 1


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
                        return {
                            "home_name": th, "away_name": ta,
                            "home_goals": fx.get("goals", {}).get("home"),
                            "away_goals": fx.get("goals", {}).get("away"),
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
        {"status": "pending", "is_parlay": {"$ne": True}, "source": {"$ne": "smart"},
         "home_team": {"$nin": ["", None]}, "away_team": {"$nin": ["", None]}},
        {"_id": 0},
    ).sort("created_at", 1).to_list(300)
    # only spend API calls on matches that have actually finished (kickoff > 2h ago)
    # and that we haven't already failed to resolve several times (quota protection)
    finished = []
    for t in raw:
        ko = _parse_kickoff(t.get("match_time"))
        if ko and ko < now - timedelta(hours=2) and t.get("settle_attempts", 0) < 4:
            finished.append((ko, t))
    finished.sort(key=lambda x: x[0])  # oldest finished first
    checked, settled, details = 0, 0, []
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
        if not team_id:
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
            continue
        fx = find_finished_fixture(team_id, opponent, dates)
        if not fx:
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
            continue
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


@api_router.post("/admin/settle-now")
async def settle_now(admin: dict = Depends(require_admin)):
    return await settle_pending_tips()


@api_router.post("/admin/live-run")
async def admin_live_run(admin: dict = Depends(require_admin)):
    return await live_autopost()


async def settlement_loop():
    while True:
        await asyncio.sleep(SETTLE_INTERVAL_SECONDS)
        try:
            if API_FOOTBALL_KEY:
                result = await settle_pending_tips()
                logger.info(f"Auto-settlement run: {result.get('settled')} settled / {result.get('checked')} checked")
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

    # Authoritative: TipJarHQ owns the 2 showcase tips + any auto-posted Forebet picks (id forebet-*).
    # Delete any OTHER TipJarHQ-authored tips (e.g. old/ugly duplicate slips) in every env on startup.
    allowed_ids = ["seed-portugal-messi", "seed-hacken-parlay", "seed-swiss-colombia-multibet"]
    await db.tips.delete_many({
        "user_id": hq["id"],
        "id": {"$nin": allowed_ids, "$not": {"$regex": "^hqtip-"}},
    })

    # Portugal & Messi — authoritative: always re-upload the tax-free image + force-update the tip
    messi_image = None
    try:
        img_file = os.path.join(os.path.dirname(__file__), "seed_assets", "portugal_messi.jpg")
        with open(img_file, "rb") as f:
            data = f.read()
        path = f"{APP_NAME}/tips/{hq['id']}/seed-portugal-messi-notax.jpg"
        messi_image = put_object(path, data, "image/jpeg")["path"]
        await db.files.update_one(
            {"storage_path": messi_image},
            {"$set": {"owner": hq["id"], "content_type": "image/jpeg", "is_deleted": False},
             "$setOnInsert": {"id": str(uuid.uuid4()), "original_filename": "portugal_messi.jpg", "created_at": now}},
            upsert=True,
        )
    except Exception as e:
        logger.error(f"seed image upload failed: {e}")

    await db.tips.update_one(
        {"id": "seed-portugal-messi"},
        {"$set": {
            "user_id": hq["id"], "username": "TipJarHQ", "image_path": messi_image,
            "home_team": "Portugal & Lionel Messi", "away_team": "",
            "match_time": "19/07/2026 21:00", "country": "International",
            "league": "World Cup – Player Specials", "market": "Winner & Top Scorer",
            "odds": "35.00", "ai_rating": 2.0,
            "ai_analysis": "Pure fan-favourite gamble: Messi banging in goals against easy opponents, chasing the Golden Boot — and the football gods teasing a dream Portugal vs Argentina final, Ronaldo vs Messi last dance. Unrealistic? Sure. Irresistible? Absolutely.",
            "legs": [], "is_parlay": False, "stake": "25,00 €", "potential_return": "875,00 €",
            "status": "lost",
        },
         "$setOnInsert": {"raw_text": "", "sum_stars": 0,
                          "ratings_count": 0, "avg_rating": 0, "created_at": now}},
        upsert=True,
    )
    logger.info("Seeded/updated showcase tip: Portugal & Messi")

    # Häcken multibet — 4 legs, each spread into its own block (no smushed market string)
    await db.tips.update_one(
        {"id": "seed-hacken-parlay"},
        {"$set": {
            "user_id": hq["id"], "username": "TipJarHQ", "image_path": None,
            "home_team": "", "away_team": "",
            "match_time": "06/07/2026 19:00 & 21:00", "country": "Sweden / International",
            "league": "Allsvenskan / Länderspiel",
            "market": "",
            "odds": "2.47", "ai_rating": 7.0,
            "ai_analysis": "Tor-Legs sind konservativ & sehr wahrscheinlich (Over 1,5, Djurgården trifft, Portugal–Spanien Over 1,5). Das gesamte Risiko hing am Fouls-Over-21,5-Leg — das kam, aber Portugal–Spanien Over 1,5 fiel nicht. Kombi damit verloren. Apex 7/10.",
            "legs": [
                {"match": "BK Häcken – Djurgården", "league": "Allsvenskan", "kickoff": "06/07 19:00", "status": "won", "selections": ["Total Über 1,5", "Djurgården Team Über 0,5"]},
                {"match": "Portugal – Spanien", "league": "Länderspiel", "kickoff": "06/07 21:00", "status": "lost", "selections": ["Total Über 1,5"]},
                {"match": "Portugal – Spanien", "league": "Länderspiel", "kickoff": "06/07 21:00", "status": "won", "selections": ["Fouls Über 21,5"]},
            ],
            "is_parlay": True, "stake": "53,23 €", "potential_return": "131,48 €",
            "status": "lost",
        },
         "$setOnInsert": {"raw_text": "", "sum_stars": 0,
                          "ratings_count": 0, "avg_rating": 0, "created_at": now}},
        upsert=True,
    )
    logger.info("Seeded/updated showcase tip: Häcken parlay (settled: lost)")

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
                {"match": "Víkingur Reykjavík – Győr ETO", "league": "Champions-League-Quali", "kickoff": "07/07 21:00", "status": "won", "selections": ["Víkingur Reykjavík Total Über 0,5"]},
                {"match": "Schweiz – Kolumbien", "league": "WM-Quali", "kickoff": "07/07 22:00", "status": "won", "selections": ["Doppelte Chance X2 (Kolumbien)"]},
                {"match": "Schweiz – Kolumbien", "league": "WM-Quali", "kickoff": "07/07 22:00", "status": "won", "selections": ["Luis Díaz: Über 0,5 Torschüsse aufs Tor"]},
            ],
            "is_parlay": True, "stake": "", "potential_return": "",
            "status": "won", "settled_by": "manual", "settled_at": now,
        },
         "$setOnInsert": {"raw_text": "", "sum_stars": 0,
                          "ratings_count": 0, "avg_rating": 0, "created_at": now}},
        upsert=True,
    )
    logger.info("Seeded/updated showcase tip: Swiss-Colombia multibet (settled: won)")


# ---------------------------------------------------------------------------
# Forebet auto-tips: TipJarHQ reads forebet.com daily and auto-posts strong picks
# ---------------------------------------------------------------------------
FOREBET_MIN_PROB = 55      # DNB: only when the favoured side is at least this likely
FOREBET_MAX_PER_RUN = 20   # cap new tips per run to avoid flooding the wall

# Leagues TipJar must NEVER touch (amateur / not offered by bookmakers).
# Forebet league short-codes (lowercased): Us4 = USA USL League Two, Fi3 = Finland 3rd tier.
FOREBET_BLOCKED_CODES = {"us4", "fi3", "sl1", "cn3"}
# Predictz league-string substrings to block (predictz has no short-code).
PREDICTZ_BLOCKED_KW = ("usl league two", "league two usa", "kakkonen")


def _league_blocked_forebet(r: dict) -> bool:
    return (r.get("lcode") or "").strip().lower() in FOREBET_BLOCKED_CODES


def _league_blocked_predictz(league: str) -> bool:
    lg = (league or "").lower()
    return any(kw in lg for kw in PREDICTZ_BLOCKED_KW)


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
    "brazil serie", "brasileir", "argentina", "liga mx", "liga profesional",
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


def _match_key(home: str, away: str) -> str:
    """Order-independent, prefix-insensitive key so 'SD Aucas' == 'Aucas'."""
    def core(n: str) -> str:
        toks = [t for t in re.sub(r"[^a-z0-9 ]", " ", (n or "").lower()).split()
                if t and t not in _CLUB_NOISE]
        return "".join(sorted(toks)) or (n or "").lower().replace(" ", "")
    return f"{core(home)}|{core(away)}"


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
        "week": datetime.now(timezone.utc).strftime("KW %V"),
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
    return {
        "week": datetime.now(timezone.utc).strftime("KW %V"),
        "systems": [
            _finalize_system(safe, len(safe), "lock", "Sicherheits-Kombi der Woche",
                             "4 Banker · mind. 1 Tor pro Spiel — auf Gewinnen gebaut", "safe"),
            _finalize_system(bankers, len(bankers), "value", "Banker-Kombi der Woche",
                             "5 stärkste Favoriten · Doppelte Chance · echte Quoten", "value"),
            _finalize_system(vals, 2, "smartvalue", "Value-Kombi der Woche",
                             "Tor-Value: BTTS & Über 2.5 · mittlere Quote", "value"),
            _finalize_system(risks, 0, "risk", "Risk-Kombi der Woche",
                             "Doppelte Chance + Beide treffen · höhere Quote", "risk"),
            _finalize_system(gambles, 0, "gamble", "Jackpot-Kombi der Woche",
                             "Zocker-Jagd auf die große Quote (70x+)", "gamble"),
        ],
    }

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
    # Goals markets derived from the predicted correct score.
    sc = parse_pred_score(r.get("score"))
    try:
        avg = float((r.get("avg") or "0").replace(",", "."))
    except Exception:
        avg = 0.0
    if sc:
        ph, pa = sc
        total = ph + pa
        # underdog team-to-score (owner idea) — passes the gate only if the book
        # prices it >= 1.60 while our winprob is high enough.
        if pred == "1" and pa >= 1:
            opts.append({"sfx": "-utg", "market": f"{away} Über 0.5 Tore",
                         "odds": "1.45", "rating": 8.0, "winprob": 0.66})
        elif pred == "2" and ph >= 1:
            opts.append({"sfx": "-utg", "market": f"{home} Über 0.5 Tore",
                         "odds": "1.45", "rating": 8.0, "winprob": 0.66})
        # Über 1.5 in a clearly high-scoring game = PRIME 80%+ value market.
        if total >= 5 and avg >= 3.5:
            opts.append({"sfx": "-o15", "market": "Über 1.5 Tore", "odds": "1.60",
                         "rating": 8.0, "winprob": 0.84})
        elif total >= 4 and avg >= 3.2:
            opts.append({"sfx": "-o15", "market": "Über 1.5 Tore", "odds": "1.50",
                         "rating": 8.0, "winprob": 0.80})
        elif total >= 3:
            opts.append({"sfx": "-o15", "market": "Über 1.5 Tore", "odds": "1.35",
                         "rating": 7.5, "winprob": 0.72})
        # Über 0.5 (very safe but low odds — usually filtered out by the 1.60 rule).
        if total >= 2:
            opts.append({"sfx": "-g", "market": "Über 0.5 Tore", "odds": "1.08",
                         "rating": 8.5, "winprob": 0.90 if total >= 3 else 0.85})
        elif total == 1:
            opts.append({"sfx": "-g", "market": "Über 0.5 Tore", "odds": "1.05",
                         "rating": 8.0, "winprob": 0.80})
    return opts


async def forebet_autopost() -> dict:
    """Scrape forebet, publish DNB + safe goals bankers (with kickoff time) as TipJarHQ."""
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    try:
        rows = await asyncio.wait_for(scrape_forebet_today(60), timeout=SCRAPE_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error("Forebet scrape timed out")
        return {"posted": 0, "reason": "scrape timeout"}
    except Exception as e:
        logger.error(f"Forebet scrape failed: {e}")
        return {"posted": 0, "reason": f"scrape error: {e}"}

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
        if _is_women_or_youth(home) or _is_women_or_youth(away):
            continue  # owner: only recognised, bettable men's competitions
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
        value_opts, banker_opts = [], []
        for o in _forebet_candidates(r):
            if _market_family(o["market"]) in banned:
                continue
            ro = _real_odd_for(o["market"], odds_map, home, away)
            final_odd = float(ro) if ro else float(o["odds"])
            o2 = dict(o)
            o2["_odd"], o2["_real"] = round(final_odd, 2), bool(ro)
            if o["winprob"] >= WIN_PROB_MIN and final_odd >= VALUE_MIN_ODDS:
                o2["_ptype"] = "value"
                value_opts.append(o2)
            elif o["winprob"] >= BANKER_WIN_PROB:
                o2["_ptype"] = "banker"
                banker_opts.append(o2)
        # prefer a real VALUE pick; else fall back to the safest BANKER
        if value_opts:
            best = max(value_opts, key=lambda o: (o["winprob"], o["_odd"]))
        elif banker_opts:
            best = max(banker_opts, key=lambda o: (o["winprob"], o["_odd"]))
        else:
            continue
        candidates.append((best["winprob"], r, best, kickoff))
    # value picks first (they carry higher odds), then safest bankers
    candidates.sort(key=lambda x: (x[2].get("_ptype") == "value", x[0], x[2]["_odd"]), reverse=True)
    ordered = candidates

    posted = 0
    now = datetime.now(timezone.utc).isoformat()
    for winprob, r, c, kickoff in ordered:
        if posted >= FOREBET_MAX_PER_RUN:
            break
        matchid = r.get("matchid") or f"{r['home']}-{r['away']}"
        tip_id = f"hqtip-a-{matchid}{c['sfx']}"
        lcode = (r.get("lcode") or "").strip().lower()
        cc = (r.get("cc") or "").strip().lower()
        # Enforce ONE pick per match: drop any other pending hq-auto tip for this game.
        await db.tips.delete_many({
            "source": "hq-auto", "status": "pending",
            "home_team": r["home"], "away_team": r["away"], "match_time": kickoff,
            "id": {"$ne": tip_id}})
        existing = await db.tips.find_one({"id": tip_id})
        if existing:
            if existing.get("league_code") != lcode:
                await db.tips.update_one(
                    {"id": tip_id}, {"$set": {"league_code": lcode, "country": cc}})
            continue
        home, away = r["home"], r["away"]
        market = c["market"]
        odds, real = c["_odd"], c["_real"]
        ptype = c.get("_ptype", "value")
        rating = round(c["rating"], 1)
        score = r.get("score") or "?"
        avg = r.get("avg") or "?"
        if ptype == "banker":
            analysis = (
                f"TipJarHQ-Banker: {market} — ca. {round(winprob * 100)}% Trefferchance "
                f"(sicherer Banker, Quote {odds:.2f}). Erwartetes Ergebnis {score}, Ø {avg} Tore. "
                f"Anstoß {kickoff}. {'Echte Buchmacher-Quote. ' if real else ''}"
                f"Ideal für Kombi- & Systemwetten — automatisch von TipJarHQ."
            )
        else:
            analysis = (
                f"TipJarHQ-Value: {market} — ca. {round(winprob * 100)}% Trefferchance bei "
                f"Quote {odds:.2f} (Value ≥ 1,60). Erwartetes Ergebnis {score}, Ø {avg} Tore. "
                f"Anstoß {kickoff}. {'Echte Buchmacher-Quote. ' if real else ''}"
                f"Datenbasierter Value-Pick — automatisch von TipJarHQ."
            )
        tip = {
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away,
            "match_time": kickoff,
            "country": cc, "league": "TipJarHQ Pick", "league_code": lcode,
            "market": market,
            "odds": f"{odds:.2f}", "ai_rating": rating, "ai_analysis": analysis,
            "win_prob": round(winprob, 3), "pick_type": ptype,
            "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": now,
        }
        await db.tips.insert_one(tip)
        posted += 1
        logger.info(f"HQ auto-posted (A/{ptype}): {home} vs {away} — {market} "
                    f"({round(winprob*100)}% @ {odds:.2f})")
    return {"posted": posted, "scanned": len(rows), "candidates": len(candidates)}


async def forebet_loop():
    await asyncio.sleep(30)  # let startup settle
    while True:
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
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
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
           not any(k in _lg for k in SLIP_LEAGUE_KEYWORDS):
            continue
        # Owner rule: only trust Predictz when Forebet agrees on the same match.
        if not _forebet_agrees(market, fb_map.get(_match_key(home, away))):
            continue
        match_time = _predictz_kickoff(r, d)
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
        league = (r.get("league") or "").title() or "TipJarHQ Pick"
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
            "pick_type": ptype,
            "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": now,
        }
        await db.tips.insert_one(tip)
        posted += 1
        logger.info(f"HQ auto-posted (B): {home} vs {away} — {market} ({rating})")
    return {"posted": posted, "scanned": len(rows), "candidates": len(candidates)}


async def predictz_loop():
    await asyncio.sleep(90)  # let startup + forebet (fills time index) settle first
    while True:
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
SMART_PROPS_PER_TEAM = 4     # best props kept per team (1 per player)
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
    if "beide teams treffen" in m or "btts" in m:
        return odds.get("btts")
    if "doppelte chance" in m and "+" not in m:
        if "1x" in m:
            return odds.get("dc_1x")
        if "x2" in m:
            return odds.get("dc_x2")
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
                      "kind": kind, "avg": lam})

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
                          "odds": _odds_from_prob(p), "kind": "scorer", "avg": gl})
        if yc >= 0.45:
            p = min(0.85, yc)
            cands.append({"market": f"{name} — sieht eine Karte", "prob": p,
                          "rating": min(7.5, _rating_from_prob(p)),
                          "odds": _odds_from_prob(p), "kind": "card", "avg": yc})

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
        props = (await _team_best_props(home, seasons)) + (await _team_best_props(away, seasons))
        candidates += len(props)
        mkey = hashlib.md5(_match_key(home, away).encode()).hexdigest()[:8]
        for c in props:
            slug = re.sub(r"[^a-z0-9]+", "-", c["market"].lower()).strip("-")[:40]
            tip_id = f"smart-{mkey}-{slug}"
            if await db.tips.find_one({"id": tip_id}, {"_id": 1}):
                continue
            pct = round(c["prob"] * 100)
            analysis = (
                f"TipJarHQ Smart Bet: {c['market']}. Saison-Ø {c['avg']:.2f} pro Spiel "
                f"→ ~{pct}% Trefferwahrscheinlichkeit. Datenbasierter Spieler-Prop, "
                f"Anstoß {p.get('kickoff')}. Quote ist eine Schätzung."
            )
            await db.tips.insert_one({
                "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
                "raw_text": "", "image_path": None,
                "home_team": home, "away_team": away,
                "match_time": p.get("kickoff") or "",
                "country": p.get("country") or "", "league": "TipJarHQ Smart Bet",
                "league_code": p.get("league_code") or "",
                "market": c["market"], "odds": str(c["odds"]),
                "ai_rating": c["rating"], "ai_analysis": analysis,
                "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
                "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
                "source": "smart", "created_at": datetime.now(timezone.utc).isoformat(),
            })
            posted += 1
    logger.info(f"Smart Bet run: posted {posted}, matches {scanned}, candidates {candidates}")
    return {"posted": posted, "matches": scanned, "candidates": candidates}


async def smart_loop():
    await asyncio.sleep(150)  # let predictions populate (forebet+predictz) first
    while True:
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


def _live_odd(market: str, minute: int) -> float:
    m = (market or "").lower()
    frac = min(max(minute, 0), 90) / 90.0
    if "über 2.5" in m and ("beide" in m or "btts" in m):
        base, top = 2.5, 12.0
    elif "über 2.5" in m:
        base, top = 1.9, 8.0
    elif "beide teams treffen" in m or "btts" in m:
        base, top = 1.8, 7.0
    elif "über 1.5" in m:
        base, top = 1.5, 6.0
    else:  # Über 0.5 (match or team)
        base, top = 1.25, 4.5
    return round(base + (top - base) * frac, 2)


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
    for f in live:
        teams = f.get("teams") or {}
        th = (teams.get("home") or {}).get("name") or ""
        ta = (teams.get("away") or {}).get("name") or ""
        if (_teams_match(th, home) and _teams_match(ta, away)) or \
           (_teams_match(th, away) and _teams_match(ta, home)):
            return f
    return None


async def live_autopost() -> dict:
    if not API_FOOTBALL_KEY:
        return {"posted": 0, "reason": "no API-Football key"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    live = _apifootball("/fixtures", {"live": "all"}) or []
    live_by_id = {str((f.get("fixture") or {}).get("id")): f for f in live}
    now = datetime.now(timezone.utc).isoformat()

    # 1) settle/close live tips whose match has ended
    closed = 0
    existing = await db.tips.find({"source": "hq-live", "status": "live"}, {"_id": 0}).to_list(200)
    for lt in existing:
        fid = str(lt.get("fixture_id") or "")
        if fid and fid in live_by_id:
            continue  # still in play
        fxs = _apifootball("/fixtures", {"id": fid}) if fid else None
        if fxs:
            f0 = fxs[0]
            short = ((f0.get("fixture") or {}).get("status") or {}).get("short")
            hg, ag = _align_goals(f0, lt["home_team"])
            if short in FINISHED_STATUSES:
                res = _live_bet_landed(lt.get("market"), hg, ag, lt["home_team"], lt["away_team"])
                new_status = "won" if res else ("lost" if res is False else "void")
                await db.tips.update_one({"id": lt["id"]}, {"$set": {
                    "status": new_status, "final_home": hg, "final_away": ag,
                    "settled_by": "auto-live", "settled_at": now}})
                closed += 1
                continue
        await db.tips.delete_one({"id": lt["id"]})  # unknown/stale → drop
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
        odd = _live_odd(t.get("market"), minute)
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
                "market": t.get("market"), "odds": f"{odd:.2f}", "ai_rating": t.get("ai_rating"),
                "ai_analysis": analysis, "status": "live", "match_time": t.get("match_time"),
                "live_minute": minute, "live_score": f"{hg}:{ag}", "updated_at": now,
            },
            "$setOnInsert": {
                "id": live_id, "user_id": hq["id"], "username": "TipJarHQ",
                "raw_text": "", "image_path": None,
                "home_team": t["home_team"], "away_team": t["away_team"],
                "country": t.get("country", ""), "league": "TipJarHQ Live",
                "league_code": t.get("league_code", ""),
                "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
                "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
                "source": "hq-live", "fixture_id": fid, "created_at": now,
            },
        }, upsert=True)
        posted += 1
        logger.info(f"LIVE re-offer: {t['home_team']} vs {t['away_team']} — {t.get('market')} @ {odd} ({minute}')")
    return {"posted": posted, "closed": closed, "live": len(live)}


async def live_loop():
    await asyncio.sleep(200)  # let the pre-match picks populate first
    while True:
        try:
            if API_FOOTBALL_KEY:
                logger.info(f"HQ loop D (Live): {await live_autopost()}")
        except Exception as e:
            logger.error(f"live_loop error: {e}")
        await asyncio.sleep(LIVE_POLL_SECONDS)






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
    _BG_TASKS.append(asyncio.create_task(settlement_loop()))
    _BG_TASKS.append(asyncio.create_task(forebet_loop()))
    _BG_TASKS.append(asyncio.create_task(predictz_loop()))
    _BG_TASKS.append(asyncio.create_task(smart_loop()))
    _BG_TASKS.append(asyncio.create_task(live_loop()))
    if API_FOOTBALL_KEY:
        logger.info("Auto-settlement engine enabled (API-Football)")
    else:
        logger.info("Auto-settlement idle — set API_FOOTBALL_KEY to enable")


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
        await seed_showcase()
    except Exception as e:
        logger.error(f"Startup seed failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    for task in _BG_TASKS:
        task.cancel()
    if _BG_TASKS:
        await asyncio.gather(*_BG_TASKS, return_exceptions=True)
    client.close()
