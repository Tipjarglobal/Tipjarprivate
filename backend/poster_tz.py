"""Per-poster kickoff timezone learning.

Owner rule (2026-08): all kickoff times are shown in the viewer's chosen home city, but
members type kickoffs in THEIR own local time. The owner sits in Berlin, Polaris posts from
Athens (Berlin +1h) → his times must be shifted -1h to the Berlin base, etc.

We never ask the poster for a timezone: the system LEARNS it by comparing the wall-clock a
poster typed against the real (UTC) kickoff from API-Football. The learned offset (poster
minus Berlin, in minutes) is stored per poster. A short rolling window makes it vacation-aware:
if the recent samples agree on a new offset, we adopt it as a temporary correction.
"""
from datetime import datetime, timezone
from collections import Counter
from zoneinfo import ZoneInfo

from core import db

BERLIN = ZoneInfo("Europe/Berlin")
_WINDOW = 8          # rolling samples kept per poster
_MIN_AGREE = 2       # need >=2 agreeing recent samples before trusting a (new) offset


def _to_utc(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def get_offset(username: str) -> int:
    """Learned offset in minutes (poster local minus Berlin). 0 if unknown."""
    if not username:
        return 0
    doc = await db.poster_tz.find_one({"username": username}, {"_id": 0, "offset_min": 1})
    return int((doc or {}).get("offset_min") or 0)


async def get_offsets(usernames) -> dict:
    """Batch variant for feed serialisation."""
    names = [u for u in set(usernames) if u]
    if not names:
        return {}
    out = {}
    async for d in db.poster_tz.find({"username": {"$in": names}}, {"_id": 0, "username": 1, "offset_min": 1}):
        out[d["username"]] = int(d.get("offset_min") or 0)
    return out


async def record_offset(username: str, posted_wall: datetime, true_utc):
    """Learn from one observation. posted_wall = naive datetime the poster typed (their local
    wall clock); true_utc = the real kickoff (UTC / ISO string / aware datetime)."""
    if not username or posted_wall is None or true_utc is None:
        return
    if isinstance(true_utc, str):
        try:
            true_utc = datetime.fromisoformat(true_utc.replace("Z", "+00:00"))
        except Exception:
            return
    true_utc = _to_utc(true_utc)
    if posted_wall.tzinfo:
        posted_wall = posted_wall.replace(tzinfo=None)
    berlin_wall = true_utc.astimezone(BERLIN).replace(tzinfo=None)
    diff_min = (posted_wall - berlin_wall).total_seconds() / 60.0
    off = int(round(diff_min / 15.0) * 15)   # snap to 15-min grid
    if abs(off) > 720:                        # >12h → bad parse, ignore
        return
    doc = await db.poster_tz.find_one({"username": username}) or {}
    samples = (doc.get("samples") or [])[-(_WINDOW - 1):] + [off]
    mode, cnt = Counter(samples).most_common(1)[0]
    # keep the trusted offset until the recent window clearly agrees on a new one (vacation)
    offset_min = mode if cnt >= _MIN_AGREE else int(doc.get("offset_min") or off)
    await db.poster_tz.update_one(
        {"username": username},
        {"$set": {"offset_min": offset_min, "samples": samples,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
