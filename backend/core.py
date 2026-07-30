"""TipJar shared core (extracted from server.py 2026-07 refactor).

Holds runtime configuration, the MongoDB connection, the logger and the
low-level API-Football client. Imported by server.py and the extracted
scraper / background-task modules so they can share a single db handle and
one quota flag instead of duplicating them.
"""
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

import os
import logging
import requests
from datetime import datetime, timezone

import resend
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

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
# Cheap text-only model — used for translation, moderation, name/label/selection
# canonicalisation, analysis prose and the qualifier briefing. Vision OCR (slip reading)
# stays on the expensive AI_MODEL for accuracy. Cost-optimisation (owner 2026-07-30).
AI_TEXT_MODEL = "gemini-2.5-flash"
API_FOOTBALL_KEY = os.environ.get('API_FOOTBALL_KEY')
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"
SETTLE_INTERVAL_SECONDS = 15 * 60

# ── Web Push (VAPID) ────────────────────────────────────────────────────────
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

# ------------------------------------------------------------------ API-Football client
# API-Football silently returns an empty `response` array with an `errors` payload once the
# per-minute request quota is exhausted. We track that here so the settlement engine can
# PAUSE instead of silently treating every empty response as "match not found" — which
# would wrongly burn each tip's `settle_attempts` budget and give the admin no feedback.
_API_QUOTA = {"exhausted": False, "at": None, "msg": ""}
# Daily budget tracking (from API-Football response headers) so we can RESERVE energy for
# the evening (prime kickoff + settlement window) instead of burning it all during the day.
_API_DAY = {"remaining": None, "limit": None, "day": None}
API_EVENING_UTC_HOUR = 15  # ≈ 17:00 CEST — from here the daily budget is used freely
API_DAY_RESERVE_FRAC = 0.5  # before evening, protect this fraction of the daily budget


def _api_quota_exhausted() -> bool:
    return _API_QUOTA["exhausted"]


def _reset_api_quota_flag():
    _API_QUOTA.update({"exhausted": False, "at": None, "msg": ""})


def _api_note_headers(headers):
    today = datetime.now(timezone.utc).date().isoformat()
    if _API_DAY["day"] != today:
        _API_DAY.update({"day": today, "remaining": None, "limit": None})
    for key, hdr in (("remaining", "x-ratelimit-requests-remaining"),
                     ("limit", "x-ratelimit-requests-limit")):
        val = headers.get(hdr)
        if val is not None:
            try:
                _API_DAY[key] = int(val)
            except (ValueError, TypeError):
                pass


def _api_reserve_locked() -> bool:
    """True when a NON-CRITICAL API-Football call should be deferred to protect the evening
    budget. Only matters on SMALL plans (free/basic) — on large plans (Ultra/Mega, thousands
    of requests/day) there's plenty of budget, so we never throttle. Settlement of due matches
    never calls this and always gets budget."""
    rem, lim = _API_DAY.get("remaining"), _API_DAY.get("limit")
    if not rem or not lim:
        return False
    if lim >= 1000:
        return False  # large plan (e.g. Ultra 75k/day) — no need to ration
    if datetime.now(timezone.utc).hour >= API_EVENING_UTC_HOUR:
        return False  # evening — use the budget freely
    return rem <= int(lim * API_DAY_RESERVE_FRAC)


def _apifootball(path: str, params: dict):
    if not API_FOOTBALL_KEY:
        return None
    try:
        r = requests.get(f"{API_FOOTBALL_BASE}{path}", params=params,
                         headers={"x-apisports-key": API_FOOTBALL_KEY}, timeout=20)
        r.raise_for_status()
        _api_note_headers(r.headers)
        j = r.json()
        errs = j.get("errors")
        if isinstance(errs, dict) and (errs.get("requests") or errs.get("rateLimit")):
            _API_QUOTA.update({"exhausted": True,
                               "at": datetime.now(timezone.utc).isoformat(),
                               "msg": errs.get("requests") or errs.get("rateLimit")})
            logger.warning(f"API-Football quota exhausted: {_API_QUOTA['msg']}")
            return None
        return j.get("response", [])
    except Exception as e:
        logger.error(f"API-Football {path} failed: {e}")
        return None


async def _apifootball_async(path: str, params: dict):
    return await asyncio.to_thread(_apifootball, path, params)
