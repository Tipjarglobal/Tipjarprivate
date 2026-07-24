"""TipJar background-task loops (extracted from server.py 2026-07 refactor).

Thin orchestrator loops + the self-contained Web-Push engine. The heavier
engines they drive (smart_autopost, live_autopost, snapshot_systems, member
live) and the leader flag (_is_leader) stay in server.py and are imported here.
server.py imports the loop entrypoints near the bottom (after all shared helpers
are defined) so this circular import resolves.
"""
import asyncio
from datetime import datetime, timezone, timedelta

from pywebpush import webpush, WebPushException

import json

from server import (
    API_FOOTBALL_KEY,
    LIVE_POLL_SECONDS,
    MEMBER_LIVE_POLL_SECONDS,
    VAPID_PRIVATE_KEY,
    VAPID_SUBJECT,
    _INSTANCE_ID,
    _IS_LEADER,
    _LEADER_TTL_SECONDS,
    _berlin_now,
    _is_leader,
    _purge_unclarified_slips,
    _system_cycle_day,
    build_qualifier_briefing,
    db,
    enrich_member_picks,
    favourite_smart_autopost,
    live_annotate_sync,
    live_autopost,
    logger,
    mental_autopost,
    qualifier_autopost,
    smart_autopost,
    snapshot_systems,
)


def _send_web_push(subscription: dict, payload: dict):
    webpush(
        subscription_info={"endpoint": subscription["endpoint"], "keys": subscription["keys"]},
        data=json.dumps(payload),
        vapid_private_key=VAPID_PRIVATE_KEY,
        vapid_claims={"sub": VAPID_SUBJECT},
        ttl=3600,
    )


async def notify_all_push(payload: dict):
    """Send a Web Push to every stored subscription; prune dead ones (404/410).
    Respects per-device area preferences: a device that turned an area off (e.g. AI
    tips) is skipped for that area. Subs without stored prefs receive everything."""
    if not VAPID_PRIVATE_KEY:
        return 0
    area = payload.get("area")
    subs = await db.push_subscriptions.find({}, {"_id": 0}).to_list(20000)
    sent = 0
    for s in subs:
        prefs = s.get("areas") or {}
        if area and prefs.get(area) is False:
            continue
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


def _tip_push_area(tip: dict) -> str:
    is_ai = tip.get("source") in ("hq-auto", "hq-live", "hq-system", "smart")
    if tip.get("status") == "live" or tip.get("source") == "hq-live":
        # Live is the only area where KI and Community post together. KI-live is further
        # split by category so a user can (un)subscribe to Banker / Value / Banger live
        # alerts separately; community-live stays its own area.
        if is_ai:
            cat = (tip.get("category") or "").lower()
            if cat in ("banker", "value", "banger"):
                return f"live_{cat}"
            return "live_value"
        return "live"
    src = tip.get("source")
    return "ai" if src == "hq-auto" else ("smart" if src == "smart" else "members")


def _push_stars(tip: dict) -> int:
    """Best star rating for a push (1-10): AI win-prob for KI picks, else the highest
    of the AI/self/crowd ratings for member picks. 0 = unknown (hide)."""
    cand = []
    try:
        wp = tip.get("win_prob")
        if wp:
            cand.append(float(wp) * 10)
    except Exception:
        pass
    for k in ("ai_rating", "self_rating", "avg_rating"):
        try:
            v = tip.get(k)
            if v:
                cand.append(float(v))
        except Exception:
            pass
    s = max(cand) if cand else 0
    return max(1, min(10, round(s))) if s else 0


def _push_payload_for_tip(tip: dict) -> dict:
    """Build a game/market-detailed push. Live picks get the blue LIVE styling.
    High-impact picks get a punchier title + a richer sound the foreground app
    plays: 10★ → coin+explosion ('explosion'), 9★ → coin+fire ('fire').
    Member picks carry the poster's @username + their star rating on the pop."""
    home, away = tip.get("home_team") or "", tip.get("away_team") or ""
    match = f"{home} vs {away}" if away else (home or "TipJar")
    market = tip.get("market") or ""
    odds = tip.get("odds")
    detail = f"{match} — {market}" + (f" @ {odds}" if odds else "")
    stars = _push_stars(tip)
    sound = "explosion" if stars >= 10 else ("fire" if stars == 9 else "coin")
    is_live = tip.get("status") == "live" or tip.get("source") == "hq-live"
    pid = tip.get("id")
    src = tip.get("source")
    area = _tip_push_area(tip)
    uname = (tip.get("username") or "").strip()
    community = src not in ("hq-auto", "hq-live", "hq-system", "smart")
    star_txt = f"⭐ {stars}/10 · " if stars else ""
    if is_live:
        # Owner (2026-07-10): live in-play bets are never "impossible to lose" — cap at
        # 7★ and never fire the 9/10★ explosion sound. Each live class gets its OWN look
        # so Banker / Value / Banger alerts are instantly distinguishable.
        stars = min(stars, 7)
        star_txt = f"⭐ {stars}/10 · " if stars else ""
        cat = (tip.get("category") or "").lower()
        if cat == "banger":
            l_title, l_icon, l_sound = "🔥 BANGER LIVE", "/push-live.png", "fire"
            l_vibrate = [200, 80, 200, 80, 300]
        elif cat == "banker":
            l_title, l_icon, l_sound = "🟢 LIVE-Banker", "/push-live.png", "coin"
            l_vibrate = [80, 40, 80, 40, 120]
        elif cat == "value":
            l_title, l_icon, l_sound = "🔵 LIVE-Value", "/push-live.png", "coin"
            l_vibrate = [80, 40, 80, 40, 120]
        else:
            l_title, l_icon, l_sound = "🔴 LIVE-Pick", "/push-live.png", "coin"
            l_vibrate = [80, 40, 80, 40, 120]
        if community and uname:
            l_title = f"{l_title} · @{uname}"
        return {"title": l_title, "body": f"{star_txt}{detail}", "url": f"/?pick={pid}&area=live",
                "kind": "live", "sound": l_sound, "pick_id": pid, "area": area,
                "vibrate": l_vibrate,
                "actions": [{"action": "open", "title": "Zum Pick ansehen →"}],
                "icon": l_icon, "badge": "/push-live.png", "tag": "tipjar-live"}
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
    elif community and uname:
        title = f"👥 @{uname}"
    else:
        title = "👥 Neuer Community-Tipp"
    # Fixed tag so a burst of queued pushes COLLAPSES into one visible notification
    # (newest wins) instead of stacking → no endless-swipe. Community picks use their OWN
    # tag so a member post never overwrites/merges with a KI pick (owner: distinct alert).
    tag = "tipjar-community" if community else "tipjar-pick"
    return {"title": title, "body": f"{star_txt}{detail}", "url": f"/?pick={pid}&area={area}", "kind": "tip",
            "sound": sound, "pick_id": pid, "area": area,
            "actions": [{"action": "open", "title": "Zum Pick ansehen →"}],
            "icon": "/icon-192.png", "badge": "/icon-192.png", "tag": tag}


def _digest_payload_for_tips(tips: list, area: str = None) -> dict:
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
    return {"title": title, "body": body, "url": f"/?area={area}" if area else "/",
            "kind": "digest", "sound": "coin", "area": area,
            "actions": [{"action": "open", "title": "Ansehen →"}],
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
                # Group by area (ai/smart/members/live) so each push carries one area
                # and can be filtered per-device. One detailed push per single pick,
                # one bundled digest per area with multiple.
                by_area = {}
                for tp in fresh:
                    by_area.setdefault(_tip_push_area(tp), []).append(tp)
                for a, tps in by_area.items():
                    if len(tps) == 1:
                        await notify_all_push(_push_payload_for_tip(tps[0]))
                    else:
                        await notify_all_push(_digest_payload_for_tips(tps, a))
                if fresh:
                    last = fresh[-1]["created_at"]
                    await db.push_state.update_one({"key": "last_push"},
                                                   {"$set": {"value": last}}, upsert=True)
        except Exception as e:
            logger.error(f"push_watch_loop error: {e}")
        await asyncio.sleep(45)


async def system_reset_loop():
    """Owner 2026-07-24: HARD daily reset of the system picks at 14:00 Europe/Berlin —
    wipe the still-pending frozen system slips and rebuild a fresh set for the new cycle.
    Only the elected leader runs it (no double-purge across prod replicas)."""
    await asyncio.sleep(30)
    while True:
        try:
            if _is_leader():
                b = _berlin_now()
                cycle = _system_cycle_day()
                state = await db.system_reset_state.find_one({"id": "sysreset"})
                if b.hour >= 14 and (state or {}).get("cycle") != cycle:
                    res = await db.tips.delete_many({"source": "hq-system", "status": "pending"})
                    await snapshot_systems()
                    await db.system_reset_state.update_one(
                        {"id": "sysreset"},
                        {"$set": {"id": "sysreset", "cycle": cycle,
                                  "reset_at": datetime.now(timezone.utc).isoformat(),
                                  "purged": res.deleted_count}}, upsert=True)
                    logger.info(f"Daily 14:00 Berlin system reset (cycle {cycle}, "
                                f"purged {res.deleted_count} pending system slips, rebuilt fresh)")
        except Exception as e:
            logger.error(f"system_reset_loop: {e}")
        await asyncio.sleep(300)


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


async def smart_loop():
    await asyncio.sleep(150)  # let predictions populate (forebet+predictz) first
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            if API_FOOTBALL_KEY:
                logger.info(f"HQ loop C (Smart): {await smart_autopost()}")
                logger.info(f"HQ loop C (FavSmart): {await favourite_smart_autopost()}")
                logger.info(f"HQ loop C (Mental): {await mental_autopost()}")
                logger.info(f"HQ loop C (Qualifier): {await qualifier_autopost()}")
                logger.info(f"HQ loop C (Briefing): {(await build_qualifier_briefing()).get('count')} ties")
        except Exception as e:
            logger.error(f"smart_loop error: {e}")
        await asyncio.sleep(12 * 3600)  # every 12 hours (season stats change slowly)


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


async def member_live_loop():
    while True:
        if not _is_leader():
            await asyncio.sleep(45)
            continue
        try:
            res = await live_annotate_sync()
            if res["annotated"] or res["cleared"]:
                logger.info(f"Live annotate: {res}")
            enr = await enrich_member_picks()
            if enr["enriched"]:
                logger.info(f"Member enrich: {enr}")
            await _purge_unclarified_slips()
        except Exception as e:
            logger.error(f"live_annotate_loop error: {e}")
        await asyncio.sleep(MEMBER_LIVE_POLL_SECONDS)
