"""
Shared self-learning layer for TipJar (owner 2026-06).

Reads REAL settled outcomes (won/lost) from the DB and derives, per system
(master / hq / code) and per market "pattern bucket", an honest hit-rate.
Pick builders consult `learn_verdict()` to VETO patterns that keep losing and
to BOOST patterns that keep winning. Nothing is guessed — every number here
comes from a settled result.
"""
import re
from core import db, logger

# In-place, shared cache. server.py imports this very object; refresh mutates it.
# shape: {"master": {bucket: {"won":int,"lost":int,"n":int,"rate":float}}, "hq": {...}, "code": {...}}
_LEARN: dict = {"master": {}, "hq": {}, "code": {}}

MIN_N = 6           # need at least this many settled samples before we trust a bucket
VETO_RATE = 0.40    # below this hit-rate → stop offering this pattern
BOOST_RATE = 0.70   # at/above this → pattern is a proven winner


def learn_bucket(market: str) -> str:
    """Normalize a (German) market string into a coarse learnable pattern bucket."""
    m = (market or "").lower()
    if not m:
        return "other"
    if "halbzeit" in m or "1. hz" in m or "erste hz" in m:
        return "ht_goals"
    if any(k in m for k in ("torschütze", "torschutze", "doppelpack", "2+ tore", "brace", "scorer")):
        return "player_scorer"
    if "beide teams treffen" in m or "btts" in m or "beide treffen" in m:
        return "btts"
    if "doppelte chance" in m or re.search(r"\b(1x|x2|12)\b", m):
        return "double_chance"
    if "handicap" in m:
        return "handicap"
    if "ecken" in m or "corner" in m:
        return "corners"
    if "über 0.5" in m or "uber 0.5" in m or "trifft" in m:
        return "team_over_0.5"
    if "unter" in m or "under" in m:
        return "under_goals"
    if "über" in m or "uber" in m or "over" in m:
        return "over_goals"
    if any(k in m for k in ("sieg", "gewinnt", " win", "1x2", "match result", "match winner")):
        return "match_result"
    return "other"


def _finalize(sysmap: dict):
    for b, s in sysmap.items():
        n = s["won"] + s["lost"]
        s["n"] = n
        s["rate"] = round(s["won"] / n, 3) if n else 0.0


def _bump(sysmap: dict, bucket: str, outcome: str):
    s = sysmap.setdefault(bucket, {"won": 0, "lost": 0, "n": 0, "rate": 0.0})
    if outcome == "won":
        s["won"] += 1
    elif outcome == "lost":
        s["lost"] += 1


def _markets_of_tip(t: dict) -> list:
    """The learnable bucket(s) for one settled tip."""
    if t.get("is_parlay"):
        out = ["parlay"]
        mc = t.get("master_category")
        if mc:
            out.append(f"cat_{mc}")
        cat = t.get("category")
        if cat and cat not in ("value",):
            out.append(f"cat_{cat}")
        return out
    return [learn_bucket(t.get("market", ""))]


async def refresh_learning() -> dict:
    """Aggregate all settled outcomes into the shared _LEARN cache + persist a snapshot."""
    fresh = {"master": {}, "hq": {}, "code": {}}
    try:
        cursor = db.tips.find(
            {"status": {"$in": ["won", "lost"]},
             "source": {"$in": ["hq-master", "hq-system", "hq-auto", "smart", "hq-live"]}},
            {"_id": 0, "source": 1, "market": 1, "status": 1, "is_parlay": 1,
             "master_category": 1, "category": 1, "legs": 1})
        async for t in cursor:
            system = "master" if t.get("source") == "hq-master" else "hq"
            for b in _markets_of_tip(t):
                _bump(fresh[system], b, t["status"])
            # owner 2026-06: the Master must LEARN FROM ITS MISTAKES. Learn per-LEG from its
            # own settled slips so the single-market veto/boost has real samples — and learn
            # BANKER mistakes as their own bucket (a lost banker kills the whole system, so a
            # market that keeps failing AS A BANKER must be avoided as a banker in future).
            if system == "master" and t.get("is_parlay"):
                for lg in (t.get("legs") or []):
                    lst = lg.get("status")
                    if lst not in ("won", "lost"):
                        continue
                    for sel in (lg.get("selections") or [lg.get("market", "")]):
                        bk = learn_bucket(sel)
                        _bump(fresh["master"], bk, lst)
                        if lg.get("banker"):
                            _bump(fresh["master"], "banker_" + bk, lst)
        async for r in db.code_reads.find(
                {"outcome": {"$in": ["won", "lost"]}},
                {"_id": 0, "pattern": 1, "outcome": 1}):
            _bump(fresh["code"], r.get("pattern") or "other", r["outcome"])
        for sysmap in fresh.values():
            _finalize(sysmap)
        # mutate the shared object IN PLACE so importers see the update
        for k in ("master", "hq", "code"):
            _LEARN[k] = fresh[k]
        try:
            await db.learn_stats.update_one(
                {"_id": "snapshot"},
                {"$set": {"data": fresh}}, upsert=True)
        except Exception as e:
            logger.warning(f"learn snapshot persist failed: {e}")
    except Exception as e:
        logger.error(f"refresh_learning failed: {e}")
    total = sum(len(v) for v in _LEARN.values())
    logger.info(f"learning refreshed: {total} buckets "
                f"(master={len(_LEARN['master'])}, hq={len(_LEARN['hq'])}, code={len(_LEARN['code'])})")
    return _LEARN


def learn_verdict(system: str, key: str, raw_bucket: bool = False,
                  min_n: int = MIN_N, veto_rate: float = VETO_RATE):
    """('veto'|'boost'|'ok', rate, n) for a market/pattern in a system.
    Conservative: returns 'ok' until we have >= min_n settled samples."""
    bucket = key if raw_bucket else learn_bucket(key)
    s = _LEARN.get(system, {}).get(bucket)
    if not s or s["n"] < min_n:
        return ("ok", (s or {}).get("rate", 0.0), (s or {}).get("n", 0))
    if s["rate"] < veto_rate:
        return ("veto", s["rate"], s["n"])
    if s["rate"] >= BOOST_RATE:
        return ("boost", s["rate"], s["n"])
    return ("ok", s["rate"], s["n"])
