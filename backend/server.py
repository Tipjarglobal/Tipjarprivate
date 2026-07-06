from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import re
import json
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
SETTLE_BATCH_CAP = 20   # max tips processed per settlement run (respects free-tier limits)
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
    email: EmailStr
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
    email: EmailStr
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
        }
    except Exception as e:
        logger.error(f"AI analyze failed: {e}")
        return fallback


# ------------------------------------------------------------------ auth routes
@api_router.post("/auth/register")
async def register(inp: RegisterInput):
    email = inp.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    if await db.users.find_one({"username": inp.username}):
        raise HTTPException(status_code=400, detail="Username already taken")
    referred_by = None
    if inp.ref:
        ref_user = await db.users.find_one({"referral_code": inp.ref})
        if ref_user:
            referred_by = ref_user["id"]
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "password_hash": hash_password(inp.password),
        "username": inp.username,
        "role": "user",
        "timezone": inp.timezone,
        "language": inp.language,
        "credits": 100,          # welcome credits
        "received_credits": 0,
        "streak": 0,
        "last_rated_date": None,
        "ratings_given": 0,
        "email_verified": False,
        "referral_code": gen_referral_code(),
        "referred_by": referred_by,
        "referral_rewarded": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    vtoken = secrets.token_urlsafe(24)
    await db.email_verification_tokens.insert_one({
        "token": vtoken, "user_id": user["id"],
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
    })
    email_res = await send_verification_email(email, vtoken, inp.origin_url or "")
    token = create_access_token(user["id"], email)
    resp = {"token": token, "user": public_user(user), "email_sent": email_res.get("sent", False)}
    if not email_res.get("sent"):
        resp["verify_link"] = email_res.get("link")  # dev aid until Resend key is set
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
    user = await db.users.find_one({"email": inp.email.lower()})
    if not user or not verify_password(inp.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["email"])
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
    image_path = None
    if file is not None:
        data = await file.read()
        image_b64 = base64.b64encode(data).decode("utf-8")
        ext = (file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "png").lower()
        path = f"{APP_NAME}/tips/{user['id']}/{uuid.uuid4()}.{ext}"
        try:
            result = put_object(path, data, file.content_type or "image/png")
            image_path = result["path"]
            await db.files.insert_one({
                "id": str(uuid.uuid4()), "storage_path": image_path,
                "original_filename": file.filename, "content_type": file.content_type,
                "owner": user["id"], "is_deleted": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception as e:
            logger.error(f"upload failed: {e}")
    detected = await analyze_tip(image_b64, text)
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
    if not (inp.match_time or "").strip():
        raise HTTPException(status_code=400, detail="Tip needs a match date & time — add the kickoff to publish.")
    tip = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "username": user["username"],
        "raw_text": inp.raw_text,
        "image_path": inp.image_path,
        "home_team": inp.home_team,
        "away_team": inp.away_team,
        "match_time": inp.match_time,
        "country": inp.country,
        "league": inp.league,
        "market": inp.market,
        "odds": inp.odds,
        "ai_rating": inp.ai_rating,
        "ai_analysis": inp.ai_analysis,
        "legs": _sanitize_legs(inp.legs),
        "is_parlay": inp.is_parlay or (inp.legs is not None and len(inp.legs) > 1),
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
    testers = await db.users.find({"email": {"$regex": r"@t\.com$"}}, {"id": 1, "_id": 0}).to_list(100000)
    ids = [u["id"] for u in testers]
    if not ids:
        return 0
    tips = await db.tips.find({"user_id": {"$in": ids}}, {"id": 1, "_id": 0}).to_list(100000)
    tip_ids = [t["id"] for t in tips]
    if not tip_ids:
        return 0
    await db.tips.delete_many({"id": {"$in": tip_ids}})
    await db.tip_ratings.delete_many({"tip_id": {"$in": tip_ids}})
    logger.info(f"Purged {len(tip_ids)} demo/test tips")
    return len(tip_ids)


@api_router.get("/tips")
async def list_tips(status: Optional[str] = None, sort: str = "new", limit: int = 50):
    q = {}
    if status:
        q["status"] = status
    limit = max(1, min(limit, 100))
    if sort == "top":
        cursor = db.tips.find(q, {"_id": 0}).sort([("avg_rating", -1), ("ratings_count", -1)]).limit(limit)
    elif sort == "hype":
        cursor = db.tips.find(q, {"_id": 0}).sort("ai_rating", -1).limit(limit)
    else:
        cursor = db.tips.find(q, {"_id": 0}).sort("created_at", -1).limit(limit)
    tips = await cursor.to_list(limit)
    return tips


@api_router.get("/tips/mine")
async def my_tips(user: dict = Depends(get_current_user)):
    tips = await db.tips.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return tips


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
    team_id = None
    if resp:
        # prefer an exact-ish name match, else first result
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
        fixtures = _apifootball("/fixtures", {"team": team_id, "date": date})
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
    pending = await db.tips.find(
        {"status": "pending", "home_team": {"$nin": ["", None]}, "away_team": {"$nin": ["", None]}},
        {"_id": 0},
    ).sort("created_at", 1).to_list(SETTLE_BATCH_CAP)
    checked, settled, details = 0, 0, []
    for tip in pending:
        checked += 1
        created = tip.get("created_at", "")[:10]
        try:
            base = datetime.fromisoformat(created) if created else datetime.now(timezone.utc)
        except Exception:
            base = datetime.now(timezone.utc)
        dates = [(base + timedelta(days=d)).date().isoformat() for d in (0, 1, 2, -1)]
        team_id = await resolve_team_id(tip["home_team"])
        if not team_id:
            team_id = await resolve_team_id(tip["away_team"])
            if team_id:
                opponent = tip["home_team"]
            else:
                continue
        else:
            opponent = tip["away_team"]
        fx = find_finished_fixture(team_id, opponent, dates)
        if not fx:
            continue
        outcome = await judge_market(tip.get("market", ""), tip["home_team"], tip["away_team"],
                                     fx["home_goals"], fx["away_goals"])
        new_status = outcome if outcome in ("won", "lost") else "void"
        if new_status == "void":
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
        },
         "$setOnInsert": {"raw_text": "", "status": "pending", "sum_stars": 0,
                          "ratings_count": 0, "avg_rating": 0, "created_at": now}},
        upsert=True,
    )
    logger.info("Seeded/updated showcase tip: Portugal & Messi")

    await db.tips.update_one(
        {"id": "seed-hacken-parlay"},
        {"$set": {
            "user_id": hq["id"], "username": "TipJarHQ", "image_path": None,
            "home_team": "BK Häcken – Djurgården", "away_team": "Portugal – Spanien",
            "match_time": "06/07/2026 19:00 & 21:00", "country": "Sweden / International",
            "league": "Allsvenskan / Länderspiel",
            "market": "Häcken–Djurgården: Total Über 1,5 · Djurgården Team Über 0,5  |  Portugal–Spanien: Total Über 1,5 · Fouls Über 21,5",
            "odds": "2.47", "ai_rating": 7.0,
            "ai_analysis": "Tor-Legs sind konservativ & sehr wahrscheinlich (Over 1,5, Djurgården trifft, Portugal–Spanien Over 1,5). Das gesamte Risiko hängt am Fouls-Over-21,5-Leg. Solider Value bei 2,47 — Apex 7/10.",
            "legs": [
                {"match": "BK Häcken – Djurgården", "league": "Allsvenskan", "kickoff": "06/07 19:00", "status": "won", "selections": ["Total Über 1,5", "Djurgården Team Über 0,5"]},
                {"match": "Portugal – Spanien", "league": "Länderspiel", "kickoff": "06/07 21:00", "status": "pending", "selections": ["Total Über 1,5", "Fouls Über 21,5"]},
            ],
            "is_parlay": True, "stake": "53,23 €", "potential_return": "131,48 €",
        },
         "$setOnInsert": {"raw_text": "", "status": "pending", "sum_stars": 0,
                          "ratings_count": 0, "avg_rating": 0, "created_at": now}},
        upsert=True,
    )
    logger.info("Seeded/updated showcase tip: Häcken parlay")


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
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
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    asyncio.create_task(settlement_loop())
    if API_FOOTBALL_KEY:
        logger.info("Auto-settlement engine enabled (API-Football)")
    else:
        logger.info("Auto-settlement idle — set API_FOOTBALL_KEY to enable")


@app.on_event("shutdown")
async def shutdown():
    client.close()
