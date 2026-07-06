from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import uuid
import json
import base64
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional

import jwt
import bcrypt
import requests
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

APP_NAME = "tipjar"
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"

# Credit economy config
CREDIT_PACKAGES = {
    "starter": {"credits": 500, "price": 5.0, "label": "Starter"},
    "pro": {"credits": 1200, "price": 10.0, "label": "Pro"},
    "whale": {"credits": 2600, "price": 20.0, "label": "Whale"},
}
GIFT_FEE = 0.10                 # platform keeps 10% of gifted credits
REDEEM_THRESHOLD = 10000        # received credits needed to redeem
REDEEM_USD_PER_1000 = 1.0       # 1000 credits => $1

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


# ------------------------------------------------------------------ models
class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    username: str = Field(min_length=2, max_length=24)
    timezone: str = "UTC"
    language: str = "en"


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
    "bet slip and/or the user's written tip. Identify the match and evaluate the bet. "
    "Return ONLY strict JSON, no markdown, with keys: home_team, away_team, match_time, "
    "country, league, market, odds, rating, analysis. "
    "'match_time' is a human readable kickoff (e.g. 'Sat 21:00' or 'Live 63''). "
    "'rating' is a number from 1 to 10 (10 = strongest, well-reasoned value bet). "
    "'analysis' is one short punchy sentence (max 160 chars). "
    "If something is unknown use an empty string. Never invent scores/results."
)


async def analyze_tip(image_b64: Optional[str], text: str) -> dict:
    fallback = {
        "home_team": "", "away_team": "", "match_time": "", "country": "",
        "league": "", "market": text.strip()[:60], "odds": "",
        "rating": 5.0, "analysis": "Auto-rating unavailable, rated neutral.",
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
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    token = create_access_token(user["id"], email)
    return {"token": token, "user": public_user(user)}


@api_router.post("/auth/login")
async def login(inp: LoginInput):
    user = await db.users.find_one({"email": inp.email.lower()})
    if not user or not verify_password(inp.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["email"])
    return {"token": token, "user": public_user(user)}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
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


@api_router.post("/tips")
async def create_tip(inp: TipSaveInput, user: dict = Depends(get_current_user)):
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


@api_router.get("/tips")
async def list_tips(status: Optional[str] = None, sort: str = "new", limit: int = 50):
    q = {}
    if status:
        q["status"] = status
    cursor = db.tips.find(q, {"_id": 0})
    tips = await cursor.to_list(500)
    if sort == "top":
        tips.sort(key=lambda t: (t.get("avg_rating", 0), t.get("ratings_count", 0)), reverse=True)
    elif sort == "hype":
        tips.sort(key=lambda t: t.get("ai_rating", 0), reverse=True)
    else:
        tips.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return tips[:limit]


@api_router.get("/tips/mine")
async def my_tips(user: dict = Depends(get_current_user)):
    tips = await db.tips.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    tips.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return tips


@api_router.post("/tips/{tip_id}/rate")
async def rate_tip(tip_id: str, inp: RateInput, user: dict = Depends(get_current_user)):
    tip = await db.tips.find_one({"id": tip_id})
    if not tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    existing = await db.tip_ratings.find_one({"tip_id": tip_id, "user_id": user["id"]})
    now = datetime.now(timezone.utc)
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
    req = CheckoutSessionRequest(amount=float(pkg["price"]), currency="usd",
                                 success_url=success_url, cancel_url=cancel_url, metadata=metadata)
    session: CheckoutSessionResponse = await stripe.create_checkout_session(req)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user["id"],
        "package_id": inp.package_id,
        "credits": pkg["credits"],
        "amount": float(pkg["price"]),
        "currency": "usd",
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
    payout = round((rc / 1000.0) * REDEEM_USD_PER_1000, 2)
    await db.users.update_one({"id": user["id"]}, {"$set": {"received_credits": 0}})
    redemption = {
        "id": str(uuid.uuid4()), "user_id": user["id"], "username": fresh["username"],
        "credits": rc, "amount_usd": payout, "status": "requested",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.redemptions.insert_one(redemption)
    redemption.pop("_id", None)
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"redemption": redemption, "user": public_user(updated)}


@api_router.get("/credits/transactions")
async def credit_txns(user: dict = Depends(get_current_user)):
    txns = await db.credit_transactions.find(
        {"$or": [{"from_user": user["id"]}, {"to_user": user["id"]}]}, {"_id": 0}).to_list(100)
    txns.sort(key=lambda t: t.get("created_at", ""), reverse=True)
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


@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    await db.tips.create_index("status")
    await db.tip_ratings.create_index([("tip_id", 1), ("user_id", 1)])
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
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.error(f"Storage init failed: {e}")


@app.on_event("shutdown")
async def shutdown():
    client.close()
