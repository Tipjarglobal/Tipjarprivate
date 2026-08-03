"""TipJar settlement engine (extracted from server.py 2026-07 refactor).

All auto-settlement / grading logic: per-leg goal & player grading, fixture
resolution (find_finished_fixture / date-scan), market judging, and the
settle_* routines for single tips, HQ combos and multimatch parlays, plus the
settlement background loop. Shared API-Football helpers, team resolution,
block-lists and config stay in server.py / core.py and are imported here.
server.py imports the public settle entrypoints near the bottom (after all
shared helpers are defined) so this circular import resolves.
"""
import re
import asyncio
from datetime import datetime, timezone, timedelta

import uuid
from emergentintegrations.llm.chat import LlmChat, UserMessage

from server import (
    AI_MODEL,
    AI_MODEL_PROVIDER,
    API_FOOTBALL_KEY,
    COUNTRY_NAME_EN,
    EMERGENT_LLM_KEY,
    EXPIRE_GRACE_HOURS,
    FINISHED_STATUSES,
    GRADE_VOID,
    PARLAY_JUDGE_CAP,
    PLAYER_LEG_KINDS,
    SETTLE_BATCH_CAP,
    SETTLE_INTERVAL_SECONDS,
    SETTLE_MAX_ATTEMPTS,
    _API_QUOTA,
    _api_quota_exhausted,
    _apifootball,
    _canonical_team_name,
    _corner_total_for_fixture,
    _cr_sort_dt,
    _finished_eligible,
    _fmt_selection,
    _is_corner_market,
    _is_leader,
    _kickoff_dt,
    _name_key,
    _norm,
    _parse_kickoff,
    _parse_player_market,
    _player_stats_for_fixture,
    _record_league_hit,
    _reset_api_quota_flag,
    _sig_tokens,
    _split_match,
    _teams_match,
    db,
    logger,
    resolve_team_id,
    resolve_unparseable_kickoffs,
    resolve_prediction_kickoffs,
    warm_goal_thirst_cache,
    snapshot_systems,
)
from poster_tz import record_offset


def _special_gift_kind(market: str):
    """Detect the owner's special GIFTS from the market text."""
    m = (market or "").lower()
    if "mindestens eine halbzeit" in m:
        return "half_any"
    if "nicht beide halbzeiten" in m:
        return "not_both_halves"
    if "ersten 2 tore" in m or "erste 2 tore" in m or "ersten zwei tore" in m:
        return "first_two"
    # owner 2026-08: cleaner half-based gifts
    if ("1. halbzeit und" in m or "hz und" in m) and "spiel" in m and "gewinnt" in m:
        return "ht_ft"                                   # wins 1st half AND the match
    if "gewinnt" in m and ("1. halbzeit" in m or "erste halbzeit" in m or "1. hz" in m):
        return "ht_win"                                  # wins the 1st half
    if ("halbzeit" in m and ("unter 2.5" in m or "unter 2,5" in m)
            and ("über 1.5" in m or "uber 1.5" in m or "über 0.5" in m or "uber 0.5" in m)):
        return "ht_combo"                                # 1st half under 2.5 + full-match over
    return None


def _fav_side_in_fixture(market: str, home_c: str, away_c: str, fx: dict) -> str:
    """Which fixture side (home/away) is the favourite named at the START of a special-gift
    market string ('<Fav> gewinnt ...' / '<Fav> schießt ...')."""
    fname = market.split(" gewinnt")[0].split(" schießt")[0].strip()
    if _teams_match(fx.get("home_name", ""), fname):
        return "home"
    if _teams_match(fx.get("away_name", ""), fname):
        return "away"
    return "home" if _teams_match(fx.get("home_name", ""), home_c) else "away"


def _grade_special_gift(kind: str, market: str, home_c: str, away_c: str, fx: dict):
    """Grade the owner's special gifts from a FINISHED fixture. Returns True/False, or None if
    it can't be judged yet (→ retry). half_any / not_both_halves use the half-time & full-time
    scores; first_two uses the goal-event order."""
    hg, ag = fx.get("home_goals"), fx.get("away_goals")
    if hg is None or ag is None:
        return None
    side = _fav_side_in_fixture(market, home_c, away_c, fx)

    def orient(h, a):
        return (h, a) if side == "home" else (a, h)

    if kind in ("half_any", "not_both_halves"):
        hh, ha = fx.get("ht_home"), fx.get("ht_away")
        if hh is None or ha is None:
            return None
        f1, o1 = orient(hh, ha)                       # 1st-half goals (fav, opp)
        f2, o2 = orient(hg - hh, ag - ha)             # 2nd-half goals
        win1, win2 = f1 > o1, f2 > o2
        if kind == "half_any":
            return bool(win1 or win2)
        return not (win1 and win2)                    # NOT both halves won
    if kind in ("ht_win", "ht_ft"):
        hh, ha = fx.get("ht_home"), fx.get("ht_away")
        if hh is None or ha is None:
            return None
        f1, o1 = orient(hh, ha)                       # 1st-half goals (fav, opp)
        if kind == "ht_win":
            return f1 > o1                            # favourite wins the 1st half
        fF, oF = orient(hg, ag)                        # full-time goals (fav, opp)
        return (f1 > o1) and (fF > oF)                # wins 1st half AND the match
    if kind == "ht_combo":
        hh, ha = fx.get("ht_home"), fx.get("ht_away")
        if hh is None or ha is None:
            return None
        ht_total = (hh or 0) + (ha or 0)
        ft_total = (hg or 0) + (ag or 0)
        mlow = (market or "").lower()
        ft_line = 1.5 if ("über 1.5" in mlow or "uber 1.5" in mlow) else 0.5
        return (ht_total < 2.5) and (ft_total > ft_line)
    if kind == "first_two":
        try:
            events = _apifootball("/fixtures/events", {"fixture": fx.get("fixture_id")}) or []
        except Exception:
            return None
        goals = []
        for e in events:
            if (e.get("type") or "").lower() != "goal":
                continue
            detail = (e.get("detail") or "").lower()
            if "missed" in detail:
                continue                              # missed penalty is not a goal
            tname = ((e.get("team") or {}).get("name")) or ""
            scorer_home = _teams_match(fx.get("home_name", ""), tname)
            if "own goal" in detail:
                scorer_home = not scorer_home         # own goal counts for the opponent
            tm = (e.get("time") or {})
            minute = (tm.get("elapsed") or 0) + (tm.get("extra") or 0)
            goals.append((minute, "home" if scorer_home else "away"))
        if hg + ag >= 2 and len(goals) < 2:
            return None                               # events not populated yet → retry
        if len(goals) < 2:
            return False                              # fewer than 2 goals → gift lost
        goals.sort(key=lambda x: x[0])
        return {goals[0][1], goals[1][1]} == {side}   # first two goals BOTH by the favourite
    return None



def _grade_player_leg(leg, pmap, team_cards, fx):
    """Grade a single player-prop / team-card / qualifier / handicap leg from a finished
    match. Returns True (won), False (lost) or None (cannot grade → do NOT settle)."""
    market = leg.get("market") or ""
    m = market.lower()
    kind0 = (leg.get("kind") or "").lower()
    hg0, ag0 = fx.get("home_goals") or 0, fx.get("away_goals") or 0
    # Two-legged tie: aggregate-aware qualification (uses the stored first-leg result).
    if kind0 == "qualify":
        qc = leg.get("qual_ctx") or {}
        agg_a = (qc.get("a1") or 0) + hg0   # teamA = return-leg HOME
        agg_b = (qc.get("b1") or 0) + ag0   # teamB = return-leg AWAY
        hw, aw = fx.get("home_winner"), fx.get("away_winner")
        if agg_a > agg_b:
            qualifier = qc.get("teamA")
        elif agg_b > agg_a:
            qualifier = qc.get("teamB")
        elif hw:
            qualifier = qc.get("teamA")
        elif aw:
            qualifier = qc.get("teamB")
        else:
            return None  # aggregate level & no ET/pen winner flag → can't determine
        return _norm(qc.get("team") or "") == _norm(qualifier or "")
    # Asian handicap ±1.5 (wins as long as the team does NOT lose by 2+ goals).
    if kind0 == "ah15_home":
        return (hg0 + 1.5) > ag0
    if kind0 == "ah15_away":
        return (ag0 + 1.5) > hg0
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
    rec = pmap.get(f"full:{_norm(player)}") or pmap.get(key)
    if not rec:
        for k, v in pmap.items():
            if k.startswith("full:"):
                continue
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
        return rec["goals"] >= need
    if kind == "card":
        return rec["cards"] >= 1
    if kind == "saves":
        return rec["saves"] >= need
    return None


def _h2h_first_leg(id1: int, id2: int, before_dt):
    """First leg of a two-legged tie: the most recent FINISHED head-to-head meeting in
    the ~30 days before the return leg. Returns {home_name, away_name, hg, ag, ...} or None."""
    if not id1 or not id2:
        return None
    resp = _apifootball("/fixtures/headtohead", {"h2h": f"{id1}-{id2}"})
    if not resp:
        return None
    best = None
    for fx in resp:
        st = fx.get("fixture", {}).get("status", {}).get("short")
        if st not in FINISHED_STATUSES:
            continue
        d = fx.get("fixture", {}).get("date")
        try:
            fdt = datetime.fromisoformat((d or "").replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if fdt >= before_dt or fdt < before_dt - timedelta(days=30):
            continue
        if best is None or fdt > best[0]:
            best = (fdt, fx)
    if not best:
        return None
    fx = best[1]
    return {
        "home_name": fx.get("teams", {}).get("home", {}).get("name", ""),
        "away_name": fx.get("teams", {}).get("away", {}).get("name", ""),
        "hg": fx.get("goals", {}).get("home") or 0,
        "ag": fx.get("goals", {}).get("away") or 0,
        "date": best[0].isoformat(),
        "fixture_id": fx.get("fixture", {}).get("id"),
    }


def _matches_between(team_id: int, after_dt, before_dt):
    """Fixture load a team carried BETWEEN the two qualifier legs. Returns
    (count, detail) where detail lists each result from the team's view
    ("0:3 verloren; 2:1 gewonnen"). 0 → rested (league in summer break)."""
    if not team_id:
        return 0, ""
    resp = _apifootball("/fixtures", {"team": team_id, "last": 8})
    if not resp:
        return 0, ""
    out = []
    for fx in resp:
        st = fx.get("fixture", {}).get("status", {}).get("short")
        if st not in FINISHED_STATUSES:
            continue
        d = fx.get("fixture", {}).get("date")
        try:
            fdt = datetime.fromisoformat((d or "").replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if not (after_dt < fdt < before_dt):
            continue
        hg = fx.get("goals", {}).get("home") or 0
        ag = fx.get("goals", {}).get("away") or 0
        is_home = fx.get("teams", {}).get("home", {}).get("id") == team_id
        gf, ga = (hg, ag) if is_home else (ag, hg)
        res = "gewonnen" if gf > ga else ("verloren" if gf < ga else "unentschieden")
        out.append(f"{gf}:{ga} {res}")
    return len(out), "; ".join(out)


def _grade_goal_leg(kind, market, team, fx):
    """Deterministically grade a single-match goal / half-time / corner leg from a
    finished fixture. Returns True (won), False (lost), GRADE_VOID (push/refund) or
    None (kind can't be graded → the caller must NOT settle, so a leg we don't
    understand never fakes a result)."""
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
    # ── 1X2 match result: "{team} Sieg" / "{team} gewinnt" — the named team must WIN the
    #    match (winner flag covers extra time / penalties; goals as fallback). ──
    if (("sieg" in m or "gewinnt" in m or "to win" in m)
            and "über" not in m and "unter" not in m and "halbzeit" not in m
            and "beide" not in m and "doppel" not in m):
        hn, an = fx.get("home_name", ""), fx.get("away_name", "")
        hw, aw = fx.get("home_winner"), fx.get("away_winner")
        side = None
        if hn and _sig_tokens(hn) and _sig_tokens(hn) & _sig_tokens(m):
            side = "home"
        elif an and _sig_tokens(an) and _sig_tokens(an) & _sig_tokens(m):
            side = "away"
        elif team and _teams_match(hn, team):
            side = "home"
        elif team and _teams_match(an, team):
            side = "away"
        if side == "home":
            return hw if hw is not None else (hg > ag)
        if side == "away":
            return aw if aw is not None else (ag > hg)
        return None
    # ── Asian "Über 1.0 Tore 1. Halbzeit" (Asiatisch): exactly 1 HT goal REFUNDS the
    #    stake (push/void), 2+ wins, 0 loses. Owner rule 2026-07-23. ──
    _asian_ht1 = k == "ht_asian_o1" or (
        "1.0" in m
        and ("halbzeit" in m or " hz" in m or "hälfte" in m or "first half" in m or "1st half" in m)
        and ("asiat" in m or "asian" in m or "über 1.0" in m or "over 1.0" in m))
    if _asian_ht1:
        if not ht_known:
            return None
        if ht_total >= 2:
            return True
        if ht_total == 1:
            return GRADE_VOID
        return False
    # ── Asian FULL-TIME "Über 1.0" (team OR match total): 2+ goals WIN, exactly 1 goal
    #    REFUNDS the stake (push/void), 0 loses. Owner rule 2026-07-29 ("Individuel/Ομαδικό
    #    Asian over 1" = a near-lock gift). Team side resolved from the named team, an explicit
    #    Heim/Gast · Team 1/2 indicator, or (fallback) the whole-match total. ──
    _asian_o1 = (
        ("asian" in m or "asiat" in m)
        and re.search(r"(über|over)\s*1(\.0)?(?![.\d])", m)
        and "1.5" not in m and "halbzeit" not in m and " hz" not in m and "1. halb" not in m)
    if _asian_o1:
        hn, an = fx.get("home_name", ""), fx.get("away_name", "")
        side = None
        if hn and _sig_tokens(hn) and _sig_tokens(hn) & _sig_tokens(m):
            side = "home"
        elif an and _sig_tokens(an) and _sig_tokens(an) & _sig_tokens(m):
            side = "away"
        elif team and _teams_match(hn, team):
            side = "home"
        elif team and _teams_match(an, team):
            side = "away"
        if side is None:
            if re.search(r"(individuel|ομαδικ|gesamtzahl|total)[^0-9]*\b1\b", m) or "heim" in m or " home" in m:
                side = "home"
            elif re.search(r"(individuel|ομαδικ|gesamtzahl|total)[^0-9]*\b2\b", m) or "gast" in m or "auswärts" in m or "auswarts" in m or " away" in m:
                side = "away"
        g = hg if side == "home" else (ag if side == "away" else total)
        if g >= 2:
            return True
        if g == 1:
            return GRADE_VOID
        return False
    # ── Asian FULL-TIME "Über 2.0" (match OR team total): 3+ goals WIN, exactly 2 goals
    #    REFUNDS the stake (push/void), <=1 loses. Owner rule 2026-06 (British-Isles gift:
    #    'Über 2 asiatische Tore' instead of a Lotto 1X2 / first-2-goals pick). ──
    _asian_o2 = (
        ("asian" in m or "asiat" in m)
        and re.search(r"(über|over)\s*2(\.0)?(?![.\d])", m)
        and "2.5" not in m and "halbzeit" not in m and " hz" not in m and "1. halb" not in m)
    if _asian_o2:
        hn, an = fx.get("home_name", ""), fx.get("away_name", "")
        side = None
        if hn and _sig_tokens(hn) and _sig_tokens(hn) & _sig_tokens(m):
            side = "home"
        elif an and _sig_tokens(an) and _sig_tokens(an) & _sig_tokens(m):
            side = "away"
        elif team and _teams_match(hn, team):
            side = "home"
        elif team and _teams_match(an, team):
            side = "away"
        g = hg if side == "home" else (ag if side == "away" else total)
        if g >= 3:
            return True
        if g == 2:
            return GRADE_VOID
        return False
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
    # 1st / 2nd-half total goals line, e.g. "Über 0.5 Tore 1. Halbzeit", "Unter 1.5 2. Halbzeit".
    # (Owner P0 2026-08-03: these must be GRADED from the half score, never blindly voided.)
    _hm = re.search(r"(über|ueber|over|unter|under)\s+(\d+)\.5", m)
    if _hm and ("halbzeit" in m or " hz" in m or "hälfte" in m or "halfte" in m
                or "first half" in m or "1st half" in m or "second half" in m or "2nd half" in m):
        if not ht_known:
            return None                       # no half score available → can't grade yet
        line = int(_hm.group(2))
        over = _hm.group(1) in ("über", "ueber", "over")
        second = any(x in m for x in ("2. halb", "2.halb", "zweite halb", "2. hz", "2.hz",
                                      "2. hälfte", "2.hälfte", "second half", "2nd half"))
        hgoals = sh_total if second else ht_total
        return (hgoals >= line + 1) if over else (hgoals <= line)
    # full-time total goals line, e.g. "Über 2.5 Tore" — but if the market NAMES a team
    # (e.g. "Crvena Zvezda Über 1.5 Tore"), grade that team's goals instead of the match.
    gm = re.search(r"über\s+(\d+)\.5", m)
    if gm and "halbzeit" not in m and "hz" not in m:
        line = int(gm.group(1))
        hn, an = fx.get("home_name", ""), fx.get("away_name", "")
        if hn and _sig_tokens(hn) and _sig_tokens(hn) & _sig_tokens(m):
            return hg >= line + 1
        if an and _sig_tokens(an) and _sig_tokens(an) & _sig_tokens(m):
            return ag >= line + 1
        if not team:
            return total >= line + 1
    # full-time UNDER line, e.g. "Unter 3.5 Tore". If the market NAMES a team
    # (e.g. "Braga Unter 3.5 Tore" → that team scores at most 3), grade that team.
    um = re.search(r"unter\s+(\d+)\.5", m)
    if um and "halbzeit" not in m and "hz" not in m:
        line = int(um.group(1))
        hn, an = fx.get("home_name", ""), fx.get("away_name", "")
        if hn and _sig_tokens(hn) and _sig_tokens(hn) & _sig_tokens(m):
            return hg <= line
        if an and _sig_tokens(an) and _sig_tokens(an) & _sig_tokens(m):
            return ag <= line
        if k == "team_u35" and team:
            if _teams_match(hn, team):
                return hg <= line
            if _teams_match(an, team):
                return ag <= line
        if not team:
            return total <= line
    if k == "team_o05" or ("über 0.5" in m and team):
        if _teams_match(fx.get("home_name", ""), team):
            return hg >= 1
        if _teams_match(fx.get("away_name", ""), team):
            return ag >= 1
        return hg >= 1 or ag >= 1
    if k == "btts" or ("beide teams treffen" in m and "halbzeit" not in m and "hz" not in m):
        return hg >= 1 and ag >= 1
    # "Tor in jeder Halbzeit" — a goal in BOTH halves (team-agnostic, text-gradeable)
    if k in ("goal_each_half", "o05_each_txt") or "jeder halbzeit" in m or "beide halbzeiten" in m:
        if not ht_known:
            return None
        return ht_total >= 1 and sh_total >= 1
    # team-specific "Über 1.5 Tore" (this team scores 2+)
    if k == "team_o15":
        if _teams_match(fx.get("home_name", ""), team):
            return hg >= 2
        if _teams_match(fx.get("away_name", ""), team):
            return ag >= 2
        return None
    # team +2.5 handicap (team does not lose by 3+ goals)
    if k in ("ah25_home", "ah25_away"):
        if k == "ah25_home" or _teams_match(fx.get("home_name", ""), team):
            return (hg - ag) > -3
        return (ag - hg) > -3
    # text-based handicaps naming a team: "{Team} -1.5 Handicap" / "{Team} +2.5 Handicap"
    if "halbzeit" not in m and ("handicap" in m or "-1.5" in m or "+2.5" in m):
        hn, an = fx.get("home_name", ""), fx.get("away_name", "")
        side = None
        if hn and _sig_tokens(hn) and _sig_tokens(hn) & _sig_tokens(m):
            side = "home"
        elif an and _sig_tokens(an) and _sig_tokens(an) & _sig_tokens(m):
            side = "away"
        if side:
            diff = (hg - ag) if side == "home" else (ag - hg)
            if "-1.5" in m:
                return diff >= 2          # team wins by 2+
            if "+2.5" in m:
                return diff > -3          # team does not lose by 3+
            if "-2.5" in m:
                return diff >= 3
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
    if k in ("ht_o05", "ht_o15", "ht_o25", "sh_o05", "o05_each", "ht_u25", "ht_u35", "ht1_win", "btts_ht", "btts_sh"):
        if not ht_known:
            return None                  # no half-time data → don't guess
        if k == "ht_o05":
            return ht_total >= 1
        if k == "btts_ht":
            return hth >= 1 and hta >= 1
        if k == "btts_sh":
            return (hg - hth) >= 1 and (ag - hta) >= 1
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


def _en_name(name: str) -> str:
    """Localized national-team name → API-Football English name (else unchanged)."""
    return COUNTRY_NAME_EN.get(_norm(name or ""), name)


def _reg_goals(fx: dict):
    """Regulation-time (90') goals, EXCLUDING extra time / penalties. Owner rule:
    Über/Unter-Tore und Spieler-Props (z.B. 'Über 1.5 Tore', 'Messi Über 0.5 Torschüsse')
    gelten NUR für die reguläre Spielzeit. API-Football `goals` enthält bei AET/PEN die
    Verlängerung; `score.fulltime` ist der Stand nach 90 Minuten. Fällt auf `goals` zurück,
    wenn fulltime fehlt (z.B. laufende Spiele)."""
    ft = (fx.get("score") or {}).get("fulltime") or {}
    g = fx.get("goals") or {}
    hg = ft.get("home") if ft.get("home") is not None else g.get("home")
    ag = ft.get("away") if ft.get("away") is not None else g.get("away")
    return hg, ag


def _datescan_fixture(home_name: str, away_name: str, dates: list, cache: dict = None):
    """Robust fallback: scan ALL fixtures on the kickoff date and match BOTH team
    names (either orientation). Independent of team-id/season resolution, which
    fails for many summer-qualifier leagues (diacritics, city suffixes). Returns a
    finished-fixture dict like find_finished_fixture, else None."""
    home_name = _en_name(home_name)
    away_name = _en_name(away_name)
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
                _rhg, _rag = _reg_goals(fx)
                return {
                    "home_name": th, "away_name": ta,
                    "fixture_id": fx.get("fixture", {}).get("id"),
                    "kickoff_utc": fx.get("fixture", {}).get("date"),
                    "home_goals": _rhg,
                    "away_goals": _rag,
                    "ht_home": ht.get("home"), "ht_away": ht.get("away"),
                    "home_winner": fx.get("teams", {}).get("home", {}).get("winner"),
                    "away_winner": fx.get("teams", {}).get("away", {}).get("winner"),
                    "status": status,
                }
    return None


def find_finished_fixture(team_id: int, opponent_name: str, dates: list, opponent_id: int = None,
                          self_name: str = None):
    opponent_name = _en_name(opponent_name)
    self_c = _en_name(self_name) if self_name else None

    def _self_ok(fx):
        # Guard against resolve_team_id() cross-league collisions (e.g. an Argentinian club
        # id-matching a German one → grading a SA game against a German result). The fixture side
        # that carries team_id MUST match the club name we actually searched for.
        if not self_c:
            return True
        hid = fx.get("teams", {}).get("home", {}).get("id")
        th = fx.get("teams", {}).get("home", {}).get("name", "")
        ta = fx.get("teams", {}).get("away", {}).get("name", "")
        self_side = th if hid == team_id else ta
        return _teams_match(self_side, self_c)

    for di, date in enumerate(dates):
        try:
            yr = int(date[:4])
        except (ValueError, TypeError):
            continue
        for season in (yr, yr - 1):  # July matches = new season(yr); Jan = prev season(yr-1)
            fixtures = _apifootball("/fixtures", {"team": team_id, "date": date, "season": season})
            if not fixtures:
                continue
            finished = [fx for fx in fixtures
                        if fx.get("fixture", {}).get("status", {}).get("short") in FINISHED_STATUSES]
            chosen = None
            for fx in finished:
                if not _self_ok(fx):
                    continue  # this fixture's resolved side isn't even our team → skip
                th = fx.get("teams", {}).get("home", {}).get("name", "")
                ta = fx.get("teams", {}).get("away", {}).get("name", "")
                hid = fx.get("teams", {}).get("home", {}).get("id")
                aid = fx.get("teams", {}).get("away", {}).get("id")
                # Match by opponent TEAM-ID first (robust against Forebet↔API-Football naming
                # differences, e.g. 'Henan Jianye' vs 'Henan Songshan Longmen'), else by name.
                if (opponent_id and opponent_id in (hid, aid)) or \
                   _teams_match(th, opponent_name) or _teams_match(ta, opponent_name):
                    chosen = fx
                    break
            # Fallback: a club plays at most ONE match per calendar day. If neither id nor
            # name matched the opponent but the resolved team has exactly ONE finished fixture
            # on its EXACT kickoff date, that game IS the match → settle it. Only accept it when
            # the resolved side genuinely matches our team name (prevents wrong-fixture grading).
            if chosen is None and di == 0 and len(finished) == 1 and _self_ok(finished[0]):
                chosen = finished[0]
            if chosen is not None:
                th = chosen.get("teams", {}).get("home", {}).get("name", "")
                ta = chosen.get("teams", {}).get("away", {}).get("name", "")
                ht = chosen.get("score", {}).get("halftime", {}) or {}
                _rhg, _rag = _reg_goals(chosen)
                return {
                    "home_name": th, "away_name": ta,
                    "fixture_id": chosen.get("fixture", {}).get("id"),
                    "kickoff_utc": chosen.get("fixture", {}).get("date"),
                    "home_goals": _rhg,
                    "away_goals": _rag,
                    "ht_home": ht.get("home"), "ht_away": ht.get("away"),
                    "home_winner": chosen.get("teams", {}).get("home", {}).get("winner"),
                    "away_winner": chosen.get("teams", {}).get("away", {}).get("winner"),
                    "status": chosen.get("fixture", {}).get("status", {}).get("short"),
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
    _reset_api_quota_flag()
    for ko, tip in finished[:SETTLE_BATCH_CAP]:
        if _api_quota_exhausted():
            break  # daily API quota gone → stop; retry next run (budget not burned)
        checked += 1
        dates = [ko.date().isoformat(),
                 (ko + timedelta(days=1)).date().isoformat(),
                 (ko - timedelta(days=1)).date().isoformat()]
        team_id = await resolve_team_id(tip["home_team"])
        opponent = tip["away_team"]
        if not team_id:
            team_id = await resolve_team_id(tip["away_team"])
            opponent = tip["home_team"]
        # Correct (canonical English) names for reliable fixture matching — from the
        # enriched *_latin fields, or resolved on the fly for Greek/foreign names.
        home_c = tip.get("home_team_latin") or (await _canonical_team_name(tip["home_team"])) or tip["home_team"]
        away_c = tip.get("away_team_latin") or (await _canonical_team_name(tip["away_team"])) or tip["away_team"]
        opponent = away_c if opponent == tip["away_team"] else home_c
        opponent_id = await resolve_team_id(opponent)
        self_c = home_c if opponent == away_c else away_c
        fx = find_finished_fixture(team_id, opponent, dates, opponent_id, self_name=self_c) if team_id else None
        if not fx:
            # Fallback: scan the date's fixtures and match both team names directly.
            fx = _datescan_fixture(home_c, away_c, dates, date_cache)
        if not fx:
            if _api_quota_exhausted():
                checked -= 1
                break  # quota ran out mid-lookup → don't burn this tip's retry budget
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
            continue
        outcome_market = tip.get("market", "")
        # learn this poster's kickoff timezone: the wall-clock they typed vs the real UTC kickoff.
        # Only for MEMBER/expert posts (not the HQ scrapers, whose times are handled separately).
        try:
            _mtr = tip.get("match_time") or ""
            if (tip.get("source") not in ("hq-auto", "hq-live")
                    and re.match(r"^\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}", _mtr) and fx.get("kickoff_utc")):
                _pw = _parse_kickoff(_mtr)
                if _pw:
                    await record_offset(tip.get("username"), _pw.replace(tzinfo=None), fx.get("kickoff_utc"))
        except Exception:
            pass
        # Player-prop SINGLE (member or HQ): grade from the finished match's per-player
        # stats (scorer / shots / shots on target / fouls / cards / saves) instead of the
        # score-only judge. The grading logic already exists (used for combos) — reuse it
        # so member-posted player tips auto-settle too.
        _pk = _parse_player_market(outcome_market)[0]
        _lk = (tip.get("kind") or tip.get("leg_kind") or "").lower()
        is_player_single = (
            _lk in PLAYER_LEG_KINDS or _pk is not None
            or ("beide teams" in outcome_market.lower() and "karte" in outcome_market.lower())
        )
        if is_player_single:
            pmap, team_cards = _player_stats_for_fixture(fx.get("fixture_id"))
            if not pmap and not team_cards:
                if _api_quota_exhausted():
                    checked -= 1
                    break
                await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
                continue
            leg = {"market": outcome_market, "kind": _lk, "line": tip.get("line"),
                   "player": tip.get("player") or "", "team": tip.get("team", ""),
                   "home": home_c, "away": away_c}
            res = _grade_player_leg(leg, pmap or {}, team_cards or {}, fx)
            if res is None:
                await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
                continue
            new_status = "won" if res else "lost"
        elif _special_gift_kind(outcome_market):
            _sgk = _special_gift_kind(outcome_market)
            res = _grade_special_gift(_sgk, outcome_market, home_c, away_c, fx)
            if res is None:
                await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
                continue
            new_status = "won" if res else "lost"
        elif _is_corner_market(outcome_market):
            fx["corners"] = _corner_total_for_fixture(fx.get("fixture_id"))
            res = _grade_goal_leg("corner_o" if "über" in outcome_market.lower() else "corner_u",
                                  outcome_market, "", fx)
            if res is None:
                await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
                continue
            new_status = "won" if res else "lost"
        else:
            outcome = await judge_market(tip.get("market", ""), home_c, away_c,
                                         fx["home_goals"], fx["away_goals"])
            new_status = outcome if outcome in ("won", "lost") else "void"
        if new_status == "void":
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
            continue
        # canonical (Latin) team names from API-Football, mapped to the tip's orientation,
        # so non-Greek readers see "Blumenau SC" instead of "Μπλούμεναου".
        if _teams_match(fx.get("home_name", ""), home_c) or \
           _teams_match(fx.get("away_name", ""), away_c):
            home_latin, away_latin = fx.get("home_name"), fx.get("away_name")
        else:
            home_latin, away_latin = fx.get("away_name"), fx.get("home_name")
        await db.tips.update_one({"id": tip["id"]}, {"$set": {
            "status": new_status,
            "final_home": fx["home_goals"], "final_away": fx["away_goals"],
            "home_team_latin": home_latin, "away_team_latin": away_latin,
            "settled_by": "auto", "settled_at": datetime.now(timezone.utc).isoformat(),
        }})
        settled += 1
        await _record_league_hit(tip.get("league_code"))
        details.append({"tip": tip["id"], "match": f"{tip['home_team']} vs {tip['away_team']}",
                        "score": f"{fx['home_goals']}-{fx['away_goals']}", "result": new_status})
    return {"ok": True, "checked": checked, "settled": settled, "details": details,
            "quota_exhausted": _api_quota_exhausted(), "quota_msg": _API_QUOTA["msg"]}


async def settle_hq_combos() -> dict:
    """Settle TipJarHQ bet-builders: the 2-leg goal builders (source=hq-auto) AND the
    Smart Mega-Bet-Builders (source=smart) with player-prop legs. Every leg lives on the
    SAME match, so legs are graded deterministically from the final score / fixture &
    player statistics. Win → 'Best Won', loss → 'Lost'."""
    if not API_FOOTBALL_KEY:
        return {"ok": False, "settled": 0}
    now = datetime.now(timezone.utc)
    combos = await db.tips.find(
        {"source": {"$in": ["hq-auto", "smart", "hq-master"]}, "status": "pending", "is_parlay": True,
         "combo_legs": {"$exists": True}},
        {"_id": 0}).sort("created_at", 1).to_list(200)
    settled = 0
    for tip in combos:
        if _api_quota_exhausted():
            break
        if tip.get("settle_attempts", 0) >= SETTLE_MAX_ATTEMPTS:
            continue
        ko = _parse_kickoff(tip.get("match_time"))
        if not _finished_eligible(tip.get("match_time"), ko, now):
            continue
        dates = [ko.date().isoformat(),
                 (ko + timedelta(days=1)).date().isoformat(),
                 (ko - timedelta(days=1)).date().isoformat()]
        home = tip.get("home_team_latin") or (await _canonical_team_name(tip["home_team"])) or tip["home_team"]
        away = tip.get("away_team_latin") or (await _canonical_team_name(tip["away_team"])) or tip["away_team"]
        team_id = await resolve_team_id(home)
        opponent = away
        if not team_id:
            team_id = await resolve_team_id(away)
            opponent = home
        opponent_id = await resolve_team_id(opponent)
        self_c = home if opponent == away else away
        fx = find_finished_fixture(team_id, opponent, dates, opponent_id, self_name=self_c) if team_id else None
        if not fx:
            fx = _datescan_fixture(home, away, dates)
        if not fx:
            if _api_quota_exhausted():
                break
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
        all_won, any_lost, ungradeable = True, False, False
        void_count, void_factor = 0, 1.0
        for lg in combo_legs:
            lg.setdefault("home", home)
            lg.setdefault("away", away)
            res = _grade_goal_leg(lg.get("kind"), lg.get("market"), lg.get("team"), fx)
            if res is None:
                res = _grade_player_leg(lg, pmap or {}, team_cards or {}, fx)
            if res is None:
                ungradeable = True   # e.g. missing half-time data for an obscure league
                all_won = False
                continue
            if res == GRADE_VOID:
                # PUSH: this leg's stake is refunded → its odds count as 1.0 and it can
                # neither win nor lose the slip (owner: Asian Über 1.0 HZ, exactly 1 goal).
                void_count += 1
                try:
                    void_factor *= float(lg.get("odds") or 1) or 1.0
                except Exception:
                    pass
                lg["status"] = "void"
                continue
            if not res:
                any_lost = True
                all_won = False
        # A single LOST leg loses the whole builder immediately — even if another leg can't
        # be graded yet (owner bug 2026-07-17: combos with 1 lost + 1 ungradeable leg used to
        # get stuck 'pending' forever). Only a WIN needs every leg to be gradeable.
        if any_lost:
            new_status = "lost"
        elif ungradeable:
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
            continue
        elif void_count and void_count == len(combo_legs):
            new_status = "void"          # every leg pushed → whole slip refunded
        else:
            new_status = "won"
        upd = {
            "status": new_status,
            "final_home": hg, "final_away": ag,
            "settled_by": "auto", "settled_at": datetime.now(timezone.utc).isoformat(),
        }
        # If some (not all) legs pushed on a WON slip, divide the voided odds out of the
        # total so the payout reflects the refunded legs (their odds become 1.0).
        if new_status == "won" and void_count and void_factor > 1.0:
            try:
                eff = round(float(tip.get("odds") or 0) / void_factor, 2)
                if eff >= 1.0:
                    upd["odds"] = f"{eff:.2f}"
                    upd["combo_legs"] = combo_legs
                    try:
                        st = float(re.sub(r"[^0-9.]", "", str(tip.get("stake") or "").replace(",", ".")) or 0)
                    except Exception:
                        st = 0
                    if st:
                        upd["potential_return"] = f"{round(st * eff, 2):.2f} €"
            except Exception:
                pass
        await db.tips.update_one({"id": tip["id"]}, {"$set": upd})
        settled += 1
        await _record_league_hit(tip.get("league_code"))
    return {"ok": True, "settled": settled, "quota_exhausted": _api_quota_exhausted()}


async def purge_settled_tips() -> int:
    """Settled slips (won/lost/void) are auto-removed once EITHER the settlement is >24h
    old OR the MATCH itself has been over for >24h — so a late/delayed settlement can no
    longer leave an old game's slip hanging around (owner 2026-07-21). The 'Abgerechnet'
    area (inkl. 'Best Won') only ever shows the last day. Seed showcase tips are kept.
    The public HALL OF FAME (db.win_claims) is a SEPARATE collection and is never touched
    here — it stays forever ('Best Won weg, Hall of Fame steht')."""
    now = datetime.now(timezone.utc)
    cutoff_dt = now - timedelta(hours=24)
    cutoff = cutoff_dt.isoformat()
    docs = await db.tips.find(
        {"status": {"$in": ["won", "lost", "void"]}, "id": {"$not": {"$regex": "^seed-"}}},
        {"_id": 0, "id": 1, "settled_at": 1, "created_at": 1, "source": 1, "status": 1,
         "match_time": 1, "legs": 1}).to_list(5000)

    def _match_over_24h(d) -> bool:
        kos = [k for k in (_parse_kickoff(l.get("kickoff")) for l in (d.get("legs") or [])) if k]
        ko = max(kos) if kos else _parse_kickoff(d.get("match_time"))
        return bool(ko and ko < cutoff_dt)

    stale = [d["id"] for d in docs
             if (d.get("settled_at") or d.get("created_at") or "") < cutoff
             or _match_over_24h(d)]
    if not stale:
        return 0
    await db.tips.delete_many({"id": {"$in": stale}})
    await db.tip_ratings.delete_many({"tip_id": {"$in": stale}})
    logger.info(f"Purged {len(stale)} settled tips (settled >24h or match over >24h)")
    return len(stale)


def _grade_ht_selection(selection, ht_h, ht_a):
    """Grade a FIRST-HALF goals market from the half-time score.
    Returns 'won' / 'lost' / 'void' (Asian Über 1.0 HZ push) / 'open' (HT market but no
    HT data yet) / None (not a HT market)."""
    s = (selection or "").lower()
    is_ht = any(k in s for k in (
        "1. halbzeit", "erste halbzeit", "1.halbzeit", "1. hz", "erste hz",
        "1. hälfte", "1.hälfte", "first half", "1st half", "ht ", " ht", "halftime"))
    if not is_ht:
        return None
    if ht_h is None or ht_a is None:
        return "open"
    total = (ht_h or 0) + (ht_a or 0)
    # Asian "Über 1.0" first half: exactly 1 HT goal = push/refund, 2+ = won, 0 = lost.
    if ("1.0" in s) and ("asiat" in s or "asian" in s or "über 1.0" in s or "over 1.0" in s):
        if total >= 2:
            return "won"
        if total == 1:
            return "void"
        return "lost"
    m = re.search(r"(\d)[.,]5", s)
    line = (int(m.group(1)) + 0.5) if m else 0.5
    if "unter" in s or "under" in s:
        return "won" if total < line else "lost"
    return "won" if total > line else "lost"


def _leg_combined_odd(leg: dict) -> float:
    """Product of a leg's selection odds (its effective decimal price). 1.0 if unknown."""
    tot = 1.0
    for od in (leg.get("sel_odds") or []):
        try:
            v = float(str(od).replace(",", "."))
            if v > 1.0:
                tot *= v
        except (TypeError, ValueError):
            pass
    return tot


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
    scan_cache = {}
    for tip in parlays:
        if _api_quota_exhausted():
            break  # daily API quota gone → stop; don't burn parlay retry budgets
        is_cashed = tip.get("status") == "cashed_out"
        legs = tip.get("legs") or []
        # Only enforce the retry cap once EVERY match is over. A slip created ~1h before
        # kickoff would otherwise burn its whole attempt budget while games are still
        # upcoming/in-play and never settle after full-time.
        kos = [k for k in (_kickoff_dt(l.get("kickoff")) for l in legs) if k]
        if not kos:
            k0 = _kickoff_dt(tip.get("match_time"))
            kos = [k0] if k0 else []
        due = bool(kos) and now >= max(kos) + timedelta(hours=2)
        if due and tip.get("settle_attempts", 0) >= (24 if is_cashed else 12):
            continue
        changed = any_lost = False
        all_won = all_resolved = True
        won_cnt = void_cnt = lost_cnt = 0
        void_factor = 1.0
        # Community/expert LIVE slips: the match is known in-play/over, so judge each leg as
        # soon as it's plausibly full-time (~105 min after kickoff) instead of the 2h pre-match
        # cushion — find_finished_fixture only returns FT games, so this never settles early.
        elig_gap = timedelta(minutes=105) if tip.get("status") == "live" else timedelta(hours=2)
        for leg in legs:
            st = leg.get("status")
            if st == "won":
                won_cnt += 1
                continue
            if st == "lost":
                any_lost, all_won = True, False
                lost_cnt += 1
                continue
            if st == "void":
                void_cnt += 1
                void_factor *= _leg_combined_odd(leg)
                continue
            home, away = _split_match(leg.get("match") or "")
            # Correct (canonical) names for reliable fixture matching (Greek → English).
            if home:
                home = (await _canonical_team_name(home)) or home
            if away:
                away = (await _canonical_team_name(away)) or away
            ko = _kickoff_dt(leg.get("kickoff")) or _kickoff_dt(tip.get("match_time"))
            if not home or not away or not (ko and ko < now - elig_gap):
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
            opp_id = await resolve_team_id(opp)
            self_c = home if opp == away else away
            fx = find_finished_fixture(team_id, opp, dates, opp_id, self_name=self_c) if team_id else None
            if not fx:
                # robust fallback for obscure clubs (diacritics, city suffixes, season
                # detection): scan all fixtures on the date and match both team names.
                fx = _datescan_fixture(home, away, dates, scan_cache)
            if not fx:
                # match is clearly over but the fixture can't be resolved (obscure league,
                # missing data) → VOID just this leg (push) so it strikes through and the rest
                # of the slip still settles, instead of freezing the whole parlay forever.
                if ko and ko < now - timedelta(hours=14):
                    leg["status"] = "void"
                    leg.pop("final", None)
                    void_cnt += 1
                    void_factor *= _leg_combined_odd(leg)
                    changed = True
                else:
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
                # Player-scorer selection (hot-scorer combo, owner 2026-07-30) → grade from
                # THIS leg's fixture player stats, not the score-only judge.
                if _parse_player_market(sel_txt)[0] is not None:
                    pm, tc = _player_stats_for_fixture(fx.get("fixture_id"))
                    if not pm and not tc:
                        leg_open = True
                        break
                    pres = _grade_player_leg(
                        {"market": sel_txt, "home": home, "away": away}, pm or {}, tc or {}, fx)
                    if pres is None:
                        leg_open = True
                        break
                    if pres is False:
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
                lost_cnt += 1
            else:
                won_cnt += 1
        # Void legs (un-settleable/annulled) count as a PUSH: neutral for win/loss. The slip
        # wins when every remaining leg won, loses on any lost leg, and is fully void only when
        # no leg won. Legs still awaiting a result keep the slip pending (all_resolved=False).
        # SYSTEM bets (owner 2026-06, e.g. "System 3/4") settle X-of-Y: they WIN as soon as X
        # legs are won (some legs may lose), and LOSE only once reaching X is impossible. Void
        # legs drop out of the total (Y shrinks); the required hits never exceed what's left.
        is_system = (tip.get("bet_type") or "").lower() == "system" and int(tip.get("system_total") or 0) > 0
        if is_system:
            # A lost BANKER kills the whole system (bankers are fixed in every column).
            banker_lost = any(l.get("status") == "lost" and l.get("banker") for l in legs)
            eff_total = len(legs) - void_cnt
            need = min(int(tip.get("system_from") or 0), eff_total)
            if banker_lost:
                new_status = "lost"
            elif need <= 0:
                new_status = "void" if void_cnt else None
            elif won_cnt >= need:
                new_status = "won"
            elif (eff_total - lost_cnt) < need:
                new_status = "lost"
            else:
                new_status = None  # still reachable → keep pending
        elif any_lost:
            new_status = "lost"
        elif all_resolved:
            new_status = "won" if won_cnt > 0 else ("void" if void_cnt else None)
        else:
            new_status = None
        upd = {}
        if changed:
            upd["legs"] = legs
        # If some (not all) legs pushed on a WON parlay, divide the voided legs' odds out of
        # the total so the payout reflects the refunded legs (mirrors settle_hq_combos).
        if new_status == "won" and void_cnt and void_factor > 1.0 and not is_cashed:
            try:
                eff = round(float(str(tip.get("odds") or 0).replace(",", ".")) / void_factor, 2)
                if eff >= 1.0:
                    upd["odds"] = f"{eff:.2f}"
                    stk = float(re.sub(r"[^0-9.]", "", str(tip.get("stake") or "").replace(",", ".")) or 0)
                    if stk:
                        upd["potential_return"] = f"{round(stk * eff, 2):.2f} €"
            except Exception:
                pass
        # never overwrite an "Ausgezahlt" slip — only its legs are auto-graded.
        if new_status and not is_cashed:
            upd.update({"status": new_status, "settled_by": "auto", "settled_at": now.isoformat()})
        if upd:
            await db.tips.update_one({"id": tip["id"]}, {"$set": upd})
        if new_status and not is_cashed:
            settled += 1
        elif due and not (all_resolved and is_cashed) and not _api_quota_exhausted():
            await db.tips.update_one({"id": tip["id"]}, {"$inc": {"settle_attempts": 1}})
    return {"ok": True, "settled": settled, "judged": judged,
            "quota_exhausted": _api_quota_exhausted()}


async def expire_stale_pending() -> dict:
    """Any pick still 'pending'/'live' long after its (last) kickoff can't be settled
    (obscure league not in API-Football, missing stats, …). Leaving them OFFEN forever is
    unacceptable — so AI picks (hq-*/smart) are DELETED and member/community picks are VOIDed
    (moved to 'Abgerechnet' as void). Runs on every settlement cycle so nothing lingers."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=EXPIRE_GRACE_HOURS)
    docs = await db.tips.find(
        {"status": {"$in": ["pending", "live"]}},
        {"_id": 0, "id": 1, "source": 1, "match_time": 1, "legs": 1, "created_at": 1,
         "home_team": 1, "away_team": 1, "league": 1, "league_code": 1}).to_list(5000)
    ai_ids, member_ids, affected = [], [], []
    league_hits = {}
    # Auto-generated AI noise (hq-auto/hq-live/hq-system) is DELETED when stale. SMART picks
    # are curated community-insider picks the owner tracks — they are VOIDed (kept, shown in
    # 'Abgerechnet' → Annulliert), never silently deleted (owner 2026-07-26, option A).
    ai_src = ("hq-auto", "hq-live", "hq-system", "hq-master")
    for d in docs:
        legs = d.get("legs") or []
        kos = [k for k in (_kickoff_dt(l.get("kickoff")) for l in legs) if k]
        latest = max(kos) if kos else _parse_kickoff(d.get("match_time"))
        is_ai = d.get("source") in ai_src
        if latest is None:
            # Undateable pick (no kickoff on the tip or its legs). AI picks must NEVER
            # linger forever (owner 2026-07-24: 25 timeless KI picks stuck 'pending') →
            # expire them by CREATION age. Member picks are left alone (they may be live).
            if not is_ai:
                continue
            try:
                created = datetime.fromisoformat((d.get("created_at") or "").replace("Z", "+00:00"))
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
            except Exception:
                created = None
            if not created or created >= cutoff:
                continue
        elif latest >= cutoff:
            continue
        (ai_ids if d.get("source") in ai_src else member_ids).append(d["id"])
        match = f"{d.get('home_team', '?')} – {d.get('away_team', '?')}"
        lg = d.get("league") or d.get("league_code") or ""
        affected.append({"match": match, "league": lg, "source": d.get("source", "")})
        if lg:
            league_hits[lg] = league_hits.get(lg, 0) + 1
    if ai_ids:
        await db.tips.delete_many({"id": {"$in": ai_ids}})
        await db.tip_ratings.delete_many({"tip_id": {"$in": ai_ids}})
    if member_ids:
        await db.tips.update_many(
            {"id": {"$in": member_ids}},
            {"$set": {"status": "void", "settled_by": "expired",
                      "settled_at": now.isoformat()}})
        # strike through any leg that never settled on a now-voided member slip
        mset = set(member_ids)
        for d in docs:
            if d["id"] not in mset:
                continue
            legs = d.get("legs") or []
            ch = False
            for lg in legs:
                if lg.get("status") not in ("won", "lost", "void"):
                    lg["status"] = "void"
                    ch = True
            if ch:
                await db.tips.update_one({"id": d["id"]}, {"$set": {"legs": legs}})
    # Only write a cleanup-log entry when something was ACTUALLY cleaned — no empty/zero noise.
    if ai_ids or member_ids:
        logger.info(f"Expired stale picks: deleted {len(ai_ids)} AI, voided {len(member_ids)} member")
        await db.cleanup_log.insert_one({
            "id": str(uuid.uuid4()), "at": now.isoformat(),
            "deleted": len(ai_ids), "voided": len(member_ids),
            "grace_hours": EXPIRE_GRACE_HOURS,
            "leagues": sorted(league_hits.items(), key=lambda x: -x[1]),
            "matches": affected[:40],
        })
    return {"deleted": len(ai_ids), "voided": len(member_ids)}


def _grade_window_min(market, legs) -> int:
    """Minutes after kickoff by which a slip's outcome is DECIDED (period-aware).
    A first-half market (e.g. 'Team trifft das erste Tor in der 1. Halbzeit') is settled
    at half-time, so it must not linger for hours — clean it ~1h after kickoff. Full-match
    markets are decided at full time (~2h) → clean window 2.5h."""
    legs = legs or []
    text = ((market or "") + " " + " ".join(
        (l.get("market") or "") + " " + " ".join(l.get("selections") or [])
        for l in legs)).lower()
    is_first_half = bool(re.search(
        r"halbzeit|1\.?\s*hz|first half|1st half|halftime|ημίχρον|ημιχρον", text))
    single = len(legs) <= 1  # a parlay with a full-match leg must still wait for full time
    return 60 if (is_first_half and single) else 150


async def void_stale_expert_slips() -> dict:
    """Owner 2026-06/07 cleanup. Runs AFTER the settle pass so gradeable slips are already
    won/lost and gone. A still-pending expert slip is voided when it is:
      • timeless (no recognizable kickoff → can never settle), or
      • past its period window (first-half markets ~1h after kickoff, full-match ~2.5h) AND
        either the market is a first-half market (our engine can't grade those → clean on time)
        OR settlement already engaged it once (settle_attempts>=1 → tried & un-gradeable), or
      • past 12h (dead-slip backstop).
    Full-match slips the engine hasn't reached yet (attempts==0, e.g. during a quota outage)
    are kept until the 12h backstop so a gradeable slip is settled, never voided prematurely.
    NOTE: feeds post LOCAL kickoff times read as UTC, so the real match is usually older."""
    now = datetime.now(timezone.utc)
    hard = now - timedelta(hours=12)
    # Self-heal (owner 2026-08): the scraper posts kickoffs as 'DD/MM HH:MM' / 'HH:MM' which the
    # plain parser can't read → a PREVIOUS run wrongly voided still-UPCOMING expert slips as
    # 'timeless', so whole experts vanished. Revive any expert slip we voided-as-expired whose
    # (robustly re-parsed) kickoff is still in the FUTURE — a game not yet kicked off is never void.
    revived = 0
    stale_void = await db.tips.find(
        {"is_expert": True, "status": "void", "settled_by": "expired"},
        {"_id": 0, "id": 1, "match_time": 1, "legs": 1, "created_at": 1}).to_list(5000)
    revive_ids = []
    for d in stale_void:
        created = d.get("created_at") or ""
        kos = [k for k in (_cr_sort_dt(l.get("kickoff"), created) for l in (d.get("legs") or [])) if k]
        latest = max(kos) if kos else _cr_sort_dt(d.get("match_time"), created)
        if latest and latest > now + timedelta(minutes=10):
            revive_ids.append(d["id"])
    if revive_ids:
        await db.tips.update_many(
            {"id": {"$in": revive_ids}},
            {"$set": {"status": "pending"}, "$unset": {"settled_by": "", "settled_at": ""}})
        revived = len(revive_ids)
    docs = await db.tips.find(
        {"is_expert": True, "status": {"$in": ["pending", "live"]}},
        {"_id": 0, "id": 1, "match_time": 1, "legs": 1, "settle_attempts": 1,
         "market": 1, "created_at": 1}).to_list(5000)
    void_ids = []
    bad_date_ids = []
    for d in docs:
        legs = d.get("legs") or []
        created = d.get("created_at") or ""
        # Owner 2026-08 (b): a multi-leg expert slip must be date-consistent — every leg with a
        # parseable kickoff has to sit within ±3 days of when the slip was cloned. Cloned accas
        # sometimes bundle a STALE game (e.g. an international played a month ago, or a fixture
        # dated months ahead like '22/11/2026') with today's games → discard the WHOLE slip.
        if len(legs) >= 2:
            base = _parse_kickoff(created) or now
            mixed = False
            for lg in legs:
                kd = _cr_sort_dt(lg.get("kickoff") or "", created)
                if kd and abs((kd - base).total_seconds()) > 3 * 86400:
                    mixed = True
                    break
            if mixed:
                bad_date_ids.append(d["id"])
                continue
        # robust kickoff read: understands 'DD/MM HH:MM', 'HH:MM', 'DD.MM. HH:MM', ISO …
        kos = [k for k in (_cr_sort_dt(l.get("kickoff"), created) for l in legs) if k]
        latest = max(kos) if kos else _cr_sort_dt(d.get("match_time"), created)
        attempts = d.get("settle_attempts", 0) or 0
        if latest is None:
            void_ids.append(d["id"])
            continue
        if latest < hard:
            void_ids.append(d["id"])
            continue
        win = _grade_window_min(d.get("market"), legs)
        if latest < now - timedelta(minutes=win) and (win <= 60 or attempts >= 1):
            void_ids.append(d["id"])
    if bad_date_ids:
        await db.tips.update_many(
            {"id": {"$in": bad_date_ids}},
            {"$set": {"status": "void", "settled_by": "inconsistent_date",
                      "hidden": True, "settled_at": now.isoformat()}})
        logger.info(f"Voided {len(bad_date_ids)} date-inconsistent expert slips (wrong games mixed)")
    if void_ids:
        await db.tips.update_many(
            {"id": {"$in": void_ids}},
            {"$set": {"status": "void", "settled_by": "expired",
                      "settled_at": now.isoformat()}})
        logger.info(f"Voided {len(void_ids)} stale/timeless expert slips")
    if revived:
        logger.info(f"Revived {revived} wrongly-expired upcoming expert slips")
    return {"voided": len(void_ids), "bad_date": len(bad_date_ids), "revived": revived}



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
                expired = await expire_stale_pending()
                voided_exp = await void_stale_expert_slips()
                purged = await purge_settled_tips()
                try:
                    await resolve_unparseable_kickoffs()
                    await resolve_prediction_kickoffs()
                    await warm_goal_thirst_cache()
                except Exception as _e:
                    logger.error(f"kickoff fallback error: {_e}")
                logger.info(f"Auto-settlement run: {result.get('settled')} settled / {result.get('checked')} checked; "
                            f"combos {combos.get('settled')}; parlays {parlays.get('settled')}; systems snap {snap}; "
                            f"expired {expired}; voided_exp {voided_exp}; purged24h {purged}")
        except Exception as e:
            logger.error(f"settlement_loop error: {e}")
