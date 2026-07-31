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
    _api_quota_exhausted,
    _api_reserve_locked,
    _API_DAY,
    apifootball_predictions_autopost,
    VAPID_PRIVATE_KEY,
    VAPID_SUBJECT,
    _INSTANCE_ID,
    _IS_LEADER,
    _LEADER_TTL_SECONDS,
    _berlin_now,
    _is_leader,
    _kickoff_is_date_only,
    _parse_kickoff,
    _purge_unclarified_slips,
    _system_cycle_day,
    build_qualifier_briefing,
    db,
    enrich_member_picks,
    favourite_smart_autopost,
    gift_of_the_day,
    knockout_tie_autopost,
    live_annotate_sync,
    live_autopost,
    logger,
    mental_autopost,
    qualifier_autopost,
    smart_autopost,
    smart_h2h_autopost,
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
    stars = payload.get("stars") or 0
    is_live_area = (area or "").startswith("live")
    subs = await db.push_subscriptions.find({}, {"_id": 0}).to_list(20000)
    sent = 0
    for s in subs:
        prefs = s.get("areas") or {}
        if area and prefs.get(area) is False:
            continue
        # Owner rule: the star threshold (per device) governs which picks push through.
        # Live picks are time-critical and always bypass it (mirrors the in-app behaviour).
        min_stars = s.get("min_stars")
        if min_stars and stars and not is_live_area and stars < min_stars:
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
    # The Master gets his OWN dedicated alert area so users can subscribe to him alone.
    if tip.get("is_master") or tip.get("source") == "hq-master":
        return "master"
    # Cloned tipster bots (Orion / Vega / …) get their OWN generic "experts" alert area
    # so users can toggle expert picks independently — no per-bot boxes.
    if tip.get("is_expert"):
        return "experts"
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
                "vibrate": l_vibrate, "stars": stars,
                "actions": [{"action": "open", "title": "Zum Pick ansehen →"}],
                "icon": l_icon, "badge": "/push-live.png", "tag": "tipjar-live"}
    cat = (tip.get("category") or "").lower()
    if tip.get("avatar_call"):
        # Owner 2026-07-30: the Master AVATAR's confident minute-goal call gets its OWN push —
        # crystal-ball crown + the concrete minute.
        minute = tip.get("avatar_minute") or 90
        return {"title": f"🔮 Sicherer Master-Call · bis {minute}.'",
                "body": f"{detail}",
                "url": f"/?pick={pid}&area={area}&sub=avatar",
                "kind": "tip", "sound": "fire", "pick_id": pid, "area": area,
                "vibrate": [140, 60, 140, 60, 240], "stars": stars,
                "actions": [{"action": "open", "title": "Zum Call ansehen →"}],
                "icon": "/push-master.png", "badge": "/push-master.png", "tag": "tipjar-master"}
    if tip.get("is_master") or src == "hq-master":
        # The Master gets his OWN look: crown + a dedicated RED logo (owner request).
        title = "👑 Master Doppelpack" if tip.get("master_doublepack") else "👑 Master-Pick"
        sub = tip.get("master_category") or "slips"
        return {"title": title, "body": f"{star_txt}{detail}",
                "url": f"/?pick={pid}&area={area}&sub={sub}",
                "kind": "tip", "sound": "coin", "pick_id": pid, "area": area,
                "vibrate": [120, 60, 120, 60, 200], "stars": stars,
                "actions": [{"action": "open", "title": "Zum Pick ansehen →"}],
                "icon": "/push-master.png", "badge": "/push-master.png", "tag": "tipjar-master"}
    if tip.get("is_expert"):
        # Experts get their OWN look: a GOLDEN crystal ball logo (owner request), distinct
        # from the Master's red crown and the KI/community picks.
        title = f"🔮 Experten-Tipp · {uname}" if uname else "🔮 Neuer Experten-Tipp"
        return {"title": title, "body": f"{star_txt}{detail}", "url": f"/?pick={pid}&area={area}",
                "kind": "tip", "sound": "expert", "pick_id": pid, "area": area,
                "vibrate": [90, 50, 90, 50, 160], "stars": stars,
                "actions": [{"action": "open", "title": "Zum Pick ansehen →"}],
                "icon": "/push-expert.png", "badge": "/push-expert.png", "tag": "tipjar-expert"}
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
    tag = "tipjar-expert" if tip.get("is_expert") else ("tipjar-community" if community else "tipjar-pick")
    icon = "/push-expert.png" if tip.get("is_expert") else "/icon-192.png"
    return {"title": title, "body": f"{star_txt}{detail}", "url": f"/?pick={pid}&area={area}", "kind": "tip",
            "sound": sound, "pick_id": pid, "area": area, "stars": stars,
            "actions": [{"action": "open", "title": "Zum Pick ansehen →"}],
            "icon": icon, "badge": "/icon-192.png", "tag": tag}


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
    max_stars = max((_push_stars(t) for t in tips), default=0)
    is_expert = area == "experts"
    title = (f"🔮 {n} neue Experten-Tipps" if is_expert
             else f"⚡ {n} neue Picks" + (f" ({live_n}× 🔵 LIVE)" if live_n else ""))
    return {"title": title, "body": body, "url": f"/?area={area}" if area else "/",
            "kind": "digest", "sound": "expert" if is_expert else "coin", "area": area,
            "stars": max_stars,
            "actions": [{"action": "open", "title": "Ansehen →"}],
            "icon": "/push-expert.png" if is_expert else "/icon-192.png",
            "badge": "/push-expert.png" if is_expert else "/icon-192.png", "tag": "tipjar-expert" if is_expert else "tipjar-pick"}

def _earliest_kickoff(tip: dict):
    """Earliest parsed (UTC) kickoff across a tip's own time + all legs, or None when
    no clock-timed kickoff is present. Used to skip pushing pre-match picks whose game
    already started."""
    times = [tip.get("match_time")]
    for lg in (tip.get("legs") or []):
        times.append(lg.get("kickoff"))
    for lg in (tip.get("combo_legs") or []):
        times.append(lg.get("kickoff") or lg.get("match_time"))
    kos = []
    for tt in times:
        if not (tt or "").strip():
            continue
        if _kickoff_is_date_only(tt):
            continue  # date-only slips stay playable all day → don't gate the push
        ko = _parse_kickoff(tt)
        if ko:
            kos.append(ko)
    return min(kos) if kos else None




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
                now_dt = datetime.now(timezone.utc)
                grace = now_dt - timedelta(minutes=15)
                for tp in fresh:
                    ko = _earliest_kickoff(tp)
                    if tp.get("status") == "live":
                        # A genuine in-play pick's kickoff is recent. If it is more than 3h in
                        # the past the match is long over → never fire a "live" push for a
                        # finished game (fixes stale pushes that deep-link to nothing).
                        if ko is not None and ko < (now_dt - timedelta(hours=3)):
                            continue
                    else:
                        # Owner rule: notify ONLY about tips you can still play. A pre-match pick
                        # whose kickoff already passed is skipped.
                        if ko is not None and ko < grace:
                            continue
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
                logger.info(f"HQ loop C (H2H-Zyklus): {await smart_h2h_autopost()}")
                logger.info(f"HQ loop C (Gift): {await gift_of_the_day()}")
                logger.info(f"HQ loop C (K.o.-Duell): {await knockout_tie_autopost()}")
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
        # API-Football daily quota gone → back off so the settlement engine keeps its
        # budget instead of both loops hammering the exhausted quota.
        if _api_quota_exhausted():
            await asyncio.sleep(LIVE_POLL_SECONDS * 4)
            continue
        # Daytime budget reserve: defer live polling until the evening so settlement + expert
        # odds keep their energy for the prime kickoff window (owner request).
        if _api_reserve_locked():
            await asyncio.sleep(LIVE_POLL_SECONDS * 4)
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
        if _api_quota_exhausted():
            await asyncio.sleep(MEMBER_LIVE_POLL_SECONDS * 4)
            continue
        if _api_reserve_locked():
            await asyncio.sleep(MEMBER_LIVE_POLL_SECONDS * 4)
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



def _is_unplayable(tip: dict, now) -> bool:
    """True when a pick can no longer be played as a pre-match bet:
    - a clock-timed kickoff has passed (15 min grace), OR
    - a date-only slip whose day is already over (yesterday's games), OR
    - no usable time at all AND it was posted > 24h ago (stale).
    Parlays use the EARLIEST leg (once any leg starts the slip isn't placeable)."""
    # Owner 2026-07-30: ALWAYS take a fresh community pick immediately. For the first 20
    # minutes after posting we never auto-hide it — even if the AI mis-read the kickoff time
    # (wrong date/timezone) — so the member sees their slip landed and can still correct it.
    # Settlement is unaffected (it works by id, never filters `hidden`).
    ca0 = _parse_kickoff(tip.get("created_at") or "")
    if ca0 and ca0 > now - timedelta(minutes=20):
        return False
    times = [tip.get("match_time")]
    for lg in (tip.get("legs") or []):
        times.append(lg.get("kickoff"))
    for lg in (tip.get("combo_legs") or []):
        times.append(lg.get("kickoff") or lg.get("match_time"))
    deadlines = []
    for tt in times:
        if not (tt or "").strip():
            continue
        ko = _parse_kickoff(tt)
        if not ko:
            continue
        if _kickoff_is_date_only(tt):
            deadlines.append(ko.replace(hour=23, minute=59, second=59))  # playable until end of that day
        else:
            deadlines.append(ko + timedelta(minutes=15))  # small grace past kickoff
    if deadlines:
        return min(deadlines) < now
    ca = _parse_kickoff(tip.get("created_at") or "")
    return bool(ca and ca < now - timedelta(hours=24))


async def hide_unplayable_loop():
    """Keep the OPEN feed clean automatically: hide any PENDING pick once it's no longer
    playable (kickoff passed, or a date-only day that's over, or a stale timeless slip).
    Settlement still processes it by id (never filters `hidden`), so win/loss is unaffected —
    this only removes dead slips from the live feed even when the API quota delays grading."""
    await asyncio.sleep(90)
    while True:
        try:
            if _is_leader():
                now = datetime.now(timezone.utc)
                docs = await db.tips.find(
                    {"status": "pending", "hidden": {"$ne": True}},
                    {"_id": 0, "id": 1, "match_time": 1, "legs": 1, "combo_legs": 1, "created_at": 1}).to_list(6000)
                stale = [t["id"] for t in docs if _is_unplayable(t, now)]
                if stale:
                    r = await db.tips.update_many(
                        {"id": {"$in": stale}},
                        {"$set": {"hidden": True, "hidden_reason": "not_playable"}})
                    logger.info(f"hide_unplayable: hid {r.modified_count} non-playable pending picks")
        except Exception as e:
            logger.error(f"hide_unplayable_loop error: {e}")
        await asyncio.sleep(10 * 60)


async def api_burner_loop():
    """Owner: around 23:00 Europe/Berlin, if the API-Football daily budget still has
    plenty left (Ultra plan), aggressively fetch predictions for the next 48h to
    prepopulate the DB before the daily quota resets at midnight. Runs at most once per
    Berlin day (leader only); never touches the reserve if the budget is already tight."""
    await asyncio.sleep(120)
    while True:
        try:
            if _is_leader() and API_FOOTBALL_KEY:
                b = _berlin_now()
                day = b.date().isoformat()
                if b.hour == 23:
                    state = await db.api_burner_state.find_one({"id": "burner"})
                    if (state or {}).get("day") != day:
                        rem = _API_DAY.get("remaining")
                        lim = _API_DAY.get("limit")
                        # Only burn when there's a real surplus so tomorrow never starts starved.
                        surplus = bool(rem and lim and rem > max(500, int(lim * 0.25)))
                        res = {}
                        if surplus and not _api_quota_exhausted():
                            res = await apifootball_predictions_autopost(
                                day_offsets=(0, 1, 2), max_per_run=300)
                        await db.api_burner_state.update_one(
                            {"id": "burner"},
                            {"$set": {"id": "burner", "day": day, "surplus": surplus,
                                      "remaining": rem, "limit": lim, "result": res,
                                      "ran_at": datetime.now(timezone.utc).isoformat()}},
                            upsert=True)
                        logger.info(f"23:00 API burner (day {day}, surplus={surplus}, "
                                    f"rem={rem}/{lim}): {res}")
        except Exception as e:
            logger.error(f"api_burner_loop error: {e}")
        await asyncio.sleep(300)
