"""TipJar autopost scrapers (extracted from server.py 2026-07 refactor).

The four site scrapers (Forebet, Predictz, API-Football predictions, Statarea)
plus their private candidate/parse helpers and background loops. Shared betting
helpers, block-lists, odds and prediction storage stay in server.py and are
imported here. server.py imports the public loop/autopost entrypoints near the
bottom (after all shared helpers are defined), so this circular import resolves.
"""
import re
import asyncio
from typing import Optional
from datetime import datetime, timezone, timedelta

from forebet import scrape_forebet_today
from predictz import scrape_predictz, parse_pred_score
from statarea import scrape_statarea
from footballpredictions import scrape_footballpredictions

from server import (
    APIFOOTBALL_PRED_CACHE_TTL_H,
    APIFOOTBALL_PRED_MAX_PER_RUN,
    API_FOOTBALL_KEY,
    AUTOPOST_PAUSED,
    BANKER_WIN_PROB,
    FOREBET_MAX_PER_RUN,
    FOREBET_MIN_PROB,
    FOREBET_SLIP_CODES,
    FOREBET_TIME_INDEX,
    FOREBET_TOMORROW_URL,
    PREDICTZ_MAX_PER_RUN,
    SCRAPE_TIMEOUT,
    SLIP_BLOCK_KEYWORDS,
    SLIP_LEAGUE_KEYWORDS,
    VALUE_MIN_ODDS,
    _MONTHS,
    _api_quota_exhausted,
    _apifootball_async,
    _banned_market_families,
    _dedupe_hq_tips,
    _forebet_time_for,
    _is_leader,
    _is_league_auto_blocked,
    _is_scandinavian,
    _is_women_or_youth,
    _league_blocked_forebet,
    _league_blocked_predictz,
    _market_family,
    _is_banker_safe,
    _match_key,
    _norm_team,
    _parse_kickoff,
    _pois_line_odds,
    _real_odd_for,
    _refresh_blocked_leagues,
    _remember_forebet_match,
    _team_or_league_blocked,
    apply_real_odds,
    db,
    ensure_chromium,
    ensure_match_odds,
    llm_pick_analysis,
    logger,
    purge_expired_autotips,
    store_match_prediction,
)


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
    scand = _is_scandinavian(r.get("league"), r.get("lcode"))
    if pred in ("1", "2") and len(probs) >= 3:
        if pred == "1":
            win, loss, team, dc = probs[0], probs[2], home, "1X"
        else:
            win, loss, team, dc = probs[2], probs[0], away, "X2"
        if win >= FOREBET_MIN_PROB:
            # Owner rule (2026-07-20): NO Double Chance (1X/X2) in Scandinavian leagues —
            # they are far too unpredictable for a "team doesn't win" banker (Ilves lost us one).
            if not scand:
                dc_wp = min(0.97, (win + draw) / 100.0)
                opts.append({"sfx": "-dc", "market": f"{team} Doppelte Chance {dc}",
                             "odds": f"{max(1.05, 1 / max(dc_wp, 0.01)):.2f}",
                             "rating": 8.5, "winprob": dc_wp})
            dnb_wp = win / max(win + loss, 1)
            opts.append({"sfx": "-dnb", "market": f"{team} (Draw No Bet)",
                         "odds": f"{max(1.05, 1 / max(dnb_wp, 0.01)):.2f}",
                         "rating": 8.5 if win >= 72 else 8.0 if win >= 63 else 7.5,
                         "winprob": dnb_wp})
        # Underdog handicap +1.5 ONLY. Owner rule (2026-07-20): +2.5/+3.5 handicaps are
        # WORTHLESS (real odds ~1.005–1.05) — no value, dropped. +1.5 keeps real value (~1.55).
        und = away if pred == "1" else home
        opts.append({"sfx": "-hcp15", "market": f"{und} Handicap +1.5",
                     "odds": "1.55", "rating": 7.5, "winprob": 0.73})
    # Doppelte Chance 12 (Heim ODER Auswärts, kein Remis) — value when a draw is
    # unlikely. Owner rule: skip in Scandinavian leagues (draws are too common there).
    if len(probs) >= 3 and not scand:
        dc12_wp = min(0.97, (probs[0] + probs[2]) / 100.0)
        if dc12_wp >= 0.60:
            opts.append({"sfx": "-dc12", "market": "Doppelte Chance 12",
                         "odds": f"{max(1.05, 1 / max(dc12_wp, 0.01)):.2f}",
                         "rating": 8.0, "winprob": dc12_wp})
    # Goals markets derived from the predicted correct score.
    sc = parse_pred_score(r.get("score"))
    try:
        avg = float((r.get("avg") or "0").replace(",", "."))
    except Exception:
        avg = 0.0
    # Expected total goals from Forebet ("avg"). Used to gate aggressive over/first-half
    # markets so a weak, low-scoring fixture never anchors a "2 goals in the 1st half" bet.
    xg = avg if (avg and avg > 0) else 0.0
    if sc:
        ph, pa = sc
        total = ph + pa
        # Favourite handicap -1.5 is produced ONLY by the RISK generator below
        # (single -1.5 handicap per match, realistic odds) — no duplicate here.
        # underdog team-to-score (owner idea) — passes the gate only if the book
        # prices it >= 1.60 while our winprob is high enough.
        # Owner (2026-07-10): FAVOURITE to score over 0.5 (safe — a clear favourite
        # almost always scores). The risky UNDERDOG-to-score single was removed after
        # France–Morocco (the weak side that can't create chances must never anchor a pick).
        if pred == "1" and ph >= 1:
            opts.append({"sfx": "-ftg", "market": f"{home} Über 0.5 Tore",
                         "odds": "1.22", "rating": 8.5, "winprob": 0.88})
        elif pred == "2" and pa >= 1:
            opts.append({"sfx": "-ftg", "market": f"{away} Über 0.5 Tore",
                         "odds": "1.22", "rating": 8.5, "winprob": 0.88})
        # DYNAMIC single-game bet-builder (owner: "as many legs from one game as you
        # want — just win, but NEVER add a redundant leg"). Both teams to score already
        # guarantees at least 2 goals, so 'Über 1.5 Tore' is IMPLIED and must never be
        # added on top. We only stack goal-lines that are NOT implied (Über 2.5+) and
        # only with a 1-goal safety buffer under the predicted total. If nothing extra
        # qualifies we simply keep the classic 'both teams to score'.
        if sc and pred in ("1", "2") and ph >= 1 and pa >= 1 and total >= 3:
            # Owner (2026-07-10): the risky "Beide Teams treffen" builder is replaced by a
            # FAVOURITE-anchored combo that never needs the underdog to score:
            #   {Favourite} Über 0.5 Tore  +  Über 1.5 Tore gesamt  (+ Über 0.5 Tore 2. HZ)
            # Games like France–Morocco (weak side kept scoreless) now still win. Every
            # leg settles deterministically via _grade_goal_leg.
            fav_team = home if pred == "1" else away
            clegs = [
                {"market": f"{fav_team} Über 0.5 Tore", "base_odd": 1.10,
                 "kind": "team_o05", "team": fav_team},
                {"market": "Über 1.5 Tore", "base_odd": 1.38, "kind": "o15"},
            ]
            if total >= 4:
                clegs.append({"market": "Über 0.5 Tore 2. Halbzeit",
                              "base_odd": 1.40, "kind": "sh_o05"})
            n = len(clegs)
            others = " + ".join(l["market"] for l in clegs[1:])
            cmarket = f"{fav_team} Über 0.5 Tore + {others} ({n}er-Bet-Builder)"
            wp = 0.72 if n == 2 else 0.60
            opts.append({
                "sfx": "-favbb", "combo": True, "rating": 7.5, "winprob": wp,
                "market": cmarket, "legs": clegs,
            })
        # ── Extra sensible single-game builders (owner-requested variety). Every leg is
        # deterministically settleable via _grade_goal_leg, so nothing can get stuck. ──
        fav_side = pred if pred in ("1", "2") else None
        # (a) Favourite Über 0.5 Tore + Doppelte Chance (both backed by the strong side —
        # replaces the old BTTS+DC builder; the underdog is never required to score).
        if sc and total >= 2 and fav_side:
            fav_team = home if fav_side == "1" else away
            dc_kind, dc_lbl = ("dc_1x", "1X") if fav_side == "1" else ("dc_x2", "X2")
            opts.append({
                "sfx": "-favdc", "combo": True, "rating": 7.5, "winprob": 0.70,
                "market": f"{fav_team} Über 0.5 Tore + Doppelte Chance {dc_lbl} (Bet-Builder)",
                "legs": [
                    {"market": f"{fav_team} Über 0.5 Tore", "base_odd": 1.10,
                     "kind": "team_o05", "team": fav_team},
                    {"market": f"Doppelte Chance {dc_lbl}", "base_odd": 1.28, "kind": dc_kind},
                ],
            })
        # (a1) SAFE-FAVOURITE "Braga" builder (owner 2026-07-23): a strong favourite that
        # wins narrowly & low-scoring — doesn't lose AND scores 1–3 goals. Very safe → 10★.
        #   Doppelte Chance 1X/X2  +  {Fav} Über 0.5 Tore  +  {Fav} Unter 3.5 Tore
        if sc and fav_side:
            _fg = ph if fav_side == "1" else pa
            if 1 <= _fg <= 3:
                fav_team = home if fav_side == "1" else away
                dc_kind, dc_lbl = ("dc_1x", "1X") if fav_side == "1" else ("dc_x2", "X2")
                opts.append({
                    "sfx": "-favsafe", "combo": True, "rating": 8.5, "winprob": 0.66,
                    "market": (f"Doppelte Chance {dc_lbl} + {fav_team} Über 0.5 Tore "
                               f"+ {fav_team} Unter 3.5 Tore (3er-Bet-Builder)"),
                    "legs": [
                        {"market": f"Doppelte Chance {dc_lbl}", "base_odd": 1.30, "kind": dc_kind},
                        {"market": f"{fav_team} Über 0.5 Tore", "base_odd": 1.10,
                         "kind": "team_o05", "team": fav_team},
                        {"market": f"{fav_team} Unter 3.5 Tore", "base_odd": 1.15,
                         "kind": "team_u35", "team": fav_team},
                    ],
                })
        # (a2) HOT high-scoring "Anderlecht-style" builder (owner 2026-07-11): for open,
        # goal-heavy games → Über 1.5 Tore 1. Halbzeit + Beide Teams treffen + Über 2.5 Tore.
        # Higher odds/risk; every leg settles deterministically (ht_o15 / btts / o25).
        # Owner (2026-07-16): the aggressive "2 Tore in der 1. Halbzeit" leg must NEVER be
        # anchored by a weak, low-scoring side (e.g. Dila Gori 0:0). A lopsided predicted
        # scoreline alone (total>=4 from a 3:1) is not enough — we now ALSO require a genuinely
        # high goal expectation from Forebet (xg/avg >= 3.4), so only true high-scoring, open
        # games (Iceland/Australia/Norway-style) qualify.
        if sc and total >= 4 and ph >= 1 and pa >= 1 and xg >= 3.4:
            opts.append({
                "sfx": "-hot", "combo": True, "hot": True, "rating": 7.0, "winprob": 0.40,
                "market": "Über 1.5 Tore 1. Halbzeit + Beide Teams treffen + Über 2.5 Tore (3er-Bet-Builder)",
                "legs": [
                    {"market": "Über 1.5 Tore 1. Halbzeit", "base_odd": 2.60, "kind": "ht_o15"},
                    {"market": "Beide Teams treffen", "base_odd": 1.65, "kind": "btts"},
                    {"market": "Über 2.5 Tore", "base_odd": 1.70, "kind": "o25"},
                ],
            })
        # (a3) RISK: "Beide Teams treffen in JEDER Halbzeit" (both sides score in BOTH halves).
        # Owner idea (2026-07-16): the smart high-scoring-league risk bet. Only for genuinely
        # goal-heavy, open games where BOTH teams are predicted to score AND the goal
        # expectation is very high (xg/avg >= 3.5). Very tough → lives in the RISK filter with
        # big odds. Both legs settle deterministically from the HT + FT score (btts_ht / btts_sh).
        if sc and ph >= 1 and pa >= 1 and xg >= 3.5:
            opts.append({
                "sfx": "-btts2h", "combo": True, "hot": True, "rating": 6.5, "winprob": 0.22,
                "market": "Beide Teams treffen 1. Halbzeit + Beide Teams treffen 2. Halbzeit (Risk-Bet-Builder)",
                "legs": [
                    {"market": "Beide Teams treffen 1. Halbzeit", "base_odd": 2.60, "kind": "btts_ht"},
                    {"market": "Beide Teams treffen 2. Halbzeit", "base_odd": 2.50, "kind": "btts_sh"},
                ],
            })
        # (a4) VALUE-BANKER (owner 2026-07-23): "Tor in jeder Halbzeit + {Favourite} trifft".
        # The smart safe combo for open, goal-carrying games — needs a goal in BOTH halves
        # plus the favourite to score at least once. Both legs settle deterministically
        # (goal_each_half + team_o05). Lives as a high-rated value pick.
        if sc and fav_side and total >= 3 and xg >= 2.8:
            fav_team = home if fav_side == "1" else away
            _fg = ph if fav_side == "1" else pa
            if _fg >= 1:
                opts.append({
                    "sfx": "-valuebanker", "combo": True, "rating": 8.0, "winprob": 0.58,
                    "market": (f"Tor in jeder Halbzeit + {fav_team} Über 0.5 Tore "
                               f"(Value-Banker)"),
                    "legs": [
                        {"market": "Tor in jeder Halbzeit", "base_odd": 1.55, "kind": "goal_each_half"},
                        {"market": f"{fav_team} Über 0.5 Tore", "base_odd": 1.10,
                         "kind": "team_o05", "team": fav_team},
                    ],
                })
        # (a5) ASIAN VALUE-BANKER (owner 2026-07-23): "{Favourite} trifft + Über 1.0 Tore
        # 1. Halbzeit (Asiatisch)". The Asian HT leg is INSURED — exactly 1 first-half goal
        # refunds that leg (push) instead of losing, so a cagey first half doesn't kill the
        # slip. Only for open games with a decent first-half goal expectation.
        if sc and fav_side and total >= 3 and xg >= 3.0:
            fav_team = home if fav_side == "1" else away
            _fg = ph if fav_side == "1" else pa
            if _fg >= 1:
                opts.append({
                    "sfx": "-asianbanker", "combo": True, "rating": 7.5, "winprob": 0.50,
                    "market": (f"{fav_team} Über 0.5 Tore + Über 1.0 Tore 1. Halbzeit "
                               f"(Asiatisch) (Value-Banker)"),
                    "legs": [
                        {"market": f"{fav_team} Über 0.5 Tore", "base_odd": 1.10,
                         "kind": "team_o05", "team": fav_team},
                        {"market": "Über 1.0 Tore 1. Halbzeit (Asiatisch)", "base_odd": 1.70,
                         "kind": "ht_asian_o1"},
                    ],
                })
        # (b) Über 2.5 Tore + Doppelte Chance 12 (high-scoring game, draw unlikely)
        if sc and total >= 4 and len(probs) >= 3 and (probs[0] + probs[2]) >= 60:
            opts.append({
                "sfx": "-o25dc", "combo": True, "rating": 7.5, "winprob": 0.48,
                "market": "Über 2.5 Tore + Doppelte Chance 12 (Bet-Builder)",
                "legs": [
                    {"market": "Über 2.5 Tore", "base_odd": 1.70, "kind": "o25"},
                    {"market": "Doppelte Chance 12", "base_odd": 1.35, "kind": "dc_12"},
                ],
            })
        # (c) Über 0.5 Tore je Halbzeit (both halves see a goal) — needs an open game
        if sc and total >= 3 and ph >= 1 and pa >= 1:
            opts.append({
                "sfx": "-o05each", "combo": True, "rating": 7.5, "winprob": 0.52,
                "market": "Über 0.5 Tore in jeder Halbzeit (Bet-Builder)",
                "legs": [
                    {"market": "Über 0.5 Tore 1. Halbzeit", "base_odd": 1.55, "kind": "ht_o05"},
                    {"market": "Über 0.5 Tore 2. Halbzeit", "base_odd": 1.40, "kind": "sh_o05"},
                ],
            })
        # (c2) VALUE-BANKER "Austria-Wien" builder (owner 2026-07-23): an early goal is very
        # likely in open games → "Über 0.5 Tore 1. Halbzeit" (asian HT goal) anchored by the
        # favourite also scoring. Both legs settle deterministically (ht_o05 / team_o05).
        if sc and fav_side and (xg >= 2.6 or total >= 3):
            fav_team = home if fav_side == "1" else away
            opts.append({
                "sfx": "-htvalue", "combo": True, "rating": 8.0, "winprob": 0.62,
                "market": (f"Über 0.5 Tore 1. Halbzeit + {fav_team} Über 0.5 Tore "
                           f"(Value-Bet-Builder)"),
                "legs": [
                    {"market": "Über 0.5 Tore 1. Halbzeit", "base_odd": 1.55, "kind": "ht_o05"},
                    {"market": f"{fav_team} Über 0.5 Tore", "base_odd": 1.10,
                     "kind": "team_o05", "team": fav_team},
                ],
            })
        # ── Goal-line markets with REALISTIC, match-specific odds (owner fed real
        # bookmaker samples). Odds are derived from a Poisson model on the expected
        # total goals (lam), so 'Über 2.5' in a 1.5-goal game and a 3.5-goal game get
        # very different, believable prices instead of a fixed fantasy number. ──
        lam = avg if (avg and avg > 0) else float(total)
        # Over lines. Owner rule (2026-07-18): a plain full-match "Über 0.5 Tore" is
        # worthless as a standalone headline bet — it may ONLY appear as a SECONDARY leg
        # inside a bet-builder (handled above). So the 0.5 line is no longer offered as a
        # single here; keep the team-specific "<Team> Über 0.5 Tore" primary (line ~4969).
        for line, sfx, rt in ((1.5, "-o15", 8.0), (2.5, "-o25", 7.5)):
            od, p = _pois_line_odds(lam, line, over=True)
            opts.append({"sfx": sfx, "market": f"Über {line} Tore", "odds": f"{od:.2f}",
                         "rating": rt, "winprob": p})
        # Under lines
        for line, sfx, rt in ((2.5, "-u25", 8.0), (3.5, "-u35", 8.5)):
            od, p = _pois_line_odds(lam, line, over=False)
            opts.append({"sfx": sfx, "market": f"Unter {line} Tore", "odds": f"{od:.2f}",
                         "rating": rt, "winprob": p})
        # ── Corner (Ecken) markets. Corners have no dedicated data feed, so we estimate
        # an expected total-corners rate from the goal expectation (open, attacking games
        # produce more corners) and price Over/Under lines with the same Poisson model.
        # These settle deterministically from API-Football fixture statistics. ──
        corner_lam = max(7.0, min(14.0, 6.5 + 1.4 * lam))
        for line, sfx, rt in ((7.5, "-co75", 8.0), (8.5, "-co85", 7.5)):
            od, p = _pois_line_odds(corner_lam, line, over=True)
            opts.append({"sfx": sfx, "market": f"Über {line} Ecken", "odds": f"{od:.2f}",
                         "rating": rt, "winprob": p})
        for line, sfx, rt in ((11.5, "-cu115", 8.0), (10.5, "-cu105", 7.5)):
            od, p = _pois_line_odds(corner_lam, line, over=False)
            opts.append({"sfx": sfx, "market": f"Unter {line} Ecken", "odds": f"{od:.2f}",
                         "rating": rt, "winprob": p})
        # Corner bet-builder: goals + corners from ONE match (owner request).
        if total >= 3:
            opts.append({
                "sfx": "-cornerbb", "combo": True, "rating": 7.5, "winprob": 0.55,
                "market": "Über 1.5 Tore + Über 8.5 Ecken (Bet-Builder)",
                "legs": [
                    {"market": "Über 1.5 Tore", "base_odd": 1.38, "kind": "o15"},
                    {"market": "Über 8.5 Ecken", "base_odd": 1.55, "kind": "corner_o"},
                ],
            })
        # RISK: favourite -1.5 handicap (win by 2+). Odds/probability scale with the
        # predicted winning margin. High-odds ones land in the "Risk" filter.
        if pred in ("1", "2"):
            fav = home if pred == "1" else away
            margin = abs(ph - pa)
            if margin >= 3:
                h_od, h_wp = 1.65, 0.60
            elif margin == 2:
                h_od, h_wp = 1.95, 0.50
            elif margin == 1:
                h_od, h_wp = 2.60, 0.38
            else:
                h_od, h_wp = None, None
            if h_od:
                opts.append({"sfx": "-hcap15", "market": f"{fav} -1.5 (Handicap)",
                             "odds": f"{h_od:.2f}", "rating": 6.5, "winprob": h_wp})
    return opts

async def forebet_autopost() -> dict:
    """Scrape forebet, publish DNB + safe goals bankers (with kickoff time) as TipJarHQ."""
    if AUTOPOST_PAUSED:
        return {"posted": 0, "reason": "autopost paused (curated mode)"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    await _refresh_blocked_leagues()
    # Only auto-post from the start of TOMORROW (UTC) — today stays curated.
    _now = datetime.now(timezone.utc)
    _AUTOPOST_MIN_KO = (_now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        rows_today = await asyncio.wait_for(scrape_forebet_today(60), timeout=SCRAPE_TIMEOUT)
    except Exception as e:
        logger.error(f"Forebet today scrape failed: {e}")
        rows_today = []
    try:
        rows_tomorrow = await asyncio.wait_for(
            scrape_forebet_today(60, url=FOREBET_TOMORROW_URL), timeout=SCRAPE_TIMEOUT)
    except Exception as e:
        logger.warning(f"Forebet tomorrow scrape failed: {e}")
        rows_tomorrow = []
    rows = rows_today + rows_tomorrow
    if not rows:
        return {"posted": 0, "reason": "scrape empty"}

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
        # Owner: today's Single-Picks are hand-curated → the auto-scraper only creates
        # picks from tomorrow onward. (Predictions for today are still stored above so
        # the System-Slip keeps working.)
        _ko = _parse_kickoff(kickoff)
        if _ko and _ko < _AUTOPOST_MIN_KO:
            continue
        if _is_women_or_youth(home) or _is_women_or_youth(away):
            continue  # owner: only recognised, bettable men's competitions
        if _team_or_league_blocked(home, away, r.get("league") or r.get("lcode")):
            continue  # owner blacklist (teams/leagues)
        # owner: only give picks from recognised, bookmaker-available leagues (same
        # whitelist as the system slips) — no Somalia/obscure lower divisions.
        if (r.get("lcode") or "").strip().lower() not in FOREBET_SLIP_CODES:
            continue
        # skip leagues we've LEARNED are uncoverable by API-Football (never settle → no point
        # posting tips that would only pile up as permanently 'pending').
        if _is_league_auto_blocked(r.get("lcode")):
            continue
        # VALUE + BANKER gate (owner): apply real bookmaker odds; keep VALUE picks
        # (≥72% win AND odd≥1.60) or, as a separate safe category, BANKER picks (≥85%
        # win, any odd — great for combos). Drop self-learning-disabled families.
        try:
            odds_map = await ensure_match_odds(home, away, kickoff)
        except Exception:
            odds_map = {}
        value_opts, banker_opts, risk_opts, combo_opts, gift_opts = [], [], [], [], []
        for o in _forebet_candidates(r):
            if o.get("combo"):
                legs, prod = [], 1.0
                for lg in o["legs"]:
                    ro = _real_odd_for(lg["market"], odds_map, home, away)
                    od = round(float(ro) if ro else float(lg["base_odd"]), 2)
                    prod *= od
                    legs.append({"home": home, "away": away, "market": lg["market"],
                                 "odds": od, "kind": lg["kind"], "team": lg.get("team", "")})
                # Bet-Builder combos are the owner's favourite "nice" tips (goals each
                # half, favourite scores + DC, Über 2.5 + DC12 …). They live in VALUE
                # within 1.40–3.0. The HOT high-scoring builder allows bigger odds and
                # lands in the RISK filter (but stays a settleable combo).
                if o.get("hot"):
                    if 3.0 <= prod <= 15.0:
                        o2 = dict(o)
                        o2["_odd"], o2["_legs"] = round(prod, 2), legs
                        o2["_ptype"], o2["_real"] = "combo", True
                        risk_opts.append(o2)
                elif 1.40 <= prod <= 3.0:
                    o2 = dict(o)
                    o2["_odd"], o2["_legs"] = round(prod, 2), legs
                    o2["_ptype"], o2["_real"] = "combo", True
                    value_opts.append(o2)
                continue
            if _market_family(o["market"]) in banned:
                continue
            ro = _real_odd_for(o["market"], odds_map, home, away)
            final_odd = float(ro) if ro else float(o["odds"])
            o2 = dict(o)
            o2["_odd"], o2["_real"], o2["_legs"] = round(final_odd, 2), bool(ro), []
            ml = o["market"].lower()
            # Categorise every single pick into Banker / Value / Risk (owner rule):
            #  • RISK  = ONLY favourite -1.5 handicaps (must win by 2+).
            #  • VALUE = the sweet-spot 1.40–2.50 tips (goals lines, unders, DC12, team goals).
            #  • BANKER = very safe low-odds picks (ideal for combos / systems).
            if "-1.5" in ml and "handicap" in ml:
                o2["_ptype"] = "risk"
                risk_opts.append(o2)
            elif round(o["winprob"] * 10) >= 9 and _is_banker_safe(o["market"], o["winprob"]):
                # Owner rule: a 9-/10-star single is a Banker only if it's near-certain —
                # full-match Über 0.5 / team scores / DC / DNB, OR a goal-over on a strongly
                # offensive matchup (winprob ≥ 0.88 = a 0-0 is basically impossible).
                o2["_ptype"] = "banker"
                banker_opts.append(o2)
            elif 1.40 <= final_odd <= 2.60 and o["winprob"] >= 0.62:
                o2["_ptype"] = "value"
                value_opts.append(o2)
            elif o["winprob"] >= BANKER_WIN_PROB and final_odd >= 1.03 and _is_banker_safe(o["market"], o["winprob"]):
                o2["_ptype"] = "banker"
                banker_opts.append(o2)
            elif 2.00 <= final_odd <= 3.60 and o["winprob"] >= 0.55:
                # "Δώρο" (Gift): generous odds (≥2.00) for a still-likely outcome (≥55%).
                # These would otherwise be dropped (odds too high for VALUE) — we keep the
                # best one per match so the Gifts tab always has real value bombs.
                o2["_ptype"] = "gift"
                gift_opts.append(o2)
            # else: DROP it (owner 2026-07-10: fewer picks, but only ones we actually win.
            # A single with <62% win chance is a coin-flip and is no longer posted.)
        # Post the best pick of EACH available category for this match so all three
        # filters (Banker / Value / Risk) stay populated.
        cat_best = []
        if banker_opts:
            cat_best.append(("banker", max(banker_opts, key=lambda o: (o["winprob"], o["_odd"]))))
        if value_opts:
            cat_best.append(("value", max(value_opts, key=lambda o: (o["_ptype"] == "combo", o["winprob"], o["_odd"]))))
        if risk_opts:
            cat_best.append(("risk", max(risk_opts, key=lambda o: o["_odd"])))
        if gift_opts:
            cat_best.append(("gift", max(gift_opts, key=lambda o: (o["winprob"], o["_odd"]))))
        if not cat_best:
            continue
        for cat, best in cat_best:
            b = dict(best)
            b["_category"] = cat
            candidates.append((best["winprob"], r, b, kickoff))
    # order: value first, then risk, then bankers; within each by confidence/odds
    _catrank = {"value": 3, "combo": 3, "risk": 2, "gift": 2, "banker": 1}
    candidates.sort(key=lambda x: (_catrank.get(x[2].get("_ptype"), 0), x[0], x[2]["_odd"]), reverse=True)
    ordered = candidates

    posted = 0
    now = datetime.now(timezone.utc).isoformat()
    for winprob, r, c, kickoff in ordered:
        if posted >= FOREBET_MAX_PER_RUN:
            break
        matchid = r.get("matchid") or f"{r['home']}-{r['away']}"
        tip_id = f"hqtip-a-{matchid}{c['sfx']}"
        category = c.get("_category", c.get("_ptype", "value"))
        lcode = (r.get("lcode") or "").strip().lower()
        cc = (r.get("cc") or "").strip().lower()
        # STABILITY (owner): once a match has a pick in this category, keep it FIXED
        # (same market + same odds) until kickoff — never swap it on later runs.
        prior = await db.tips.find_one({
            "source": "hq-auto", "status": "pending", "category": category,
            "home_team": r["home"], "away_team": r["away"]})
        if prior:
            if lcode and prior.get("league_code") != lcode:
                await db.tips.update_one(
                    {"id": prior["id"]}, {"$set": {"league_code": lcode, "country": cc}})
            continue
        if await db.tips.find_one({"id": tip_id}):
            continue
        home, away = r["home"], r["away"]
        ptype = c.get("_ptype", "value")
        # Safety net (owner rule): a bet-builder containing "Beide Teams treffen"
        # must NEVER also carry "Über 1.5 Tore" — BTTS already guarantees ≥2 goals.
        if ptype == "combo":
            _legs = c.get("_legs", [])
            if any((lg.get("kind") == "btts" or "beide teams treffen" in (lg.get("market", "") or "").lower())
                   for lg in _legs):
                # strip ONLY the redundant full-match "Über 1.5 Tore" — never the
                # first-half "Über 1.5 Tore 1. Halbzeit" leg (owner's Anderlecht builder).
                def _is_redundant_o15(lg):
                    mk = (lg.get("market", "") or "").lower()
                    if "halbzeit" in mk or "hz" in mk:
                        return False
                    return lg.get("kind") == "o15" or "über 1.5 tore" in mk
                _kept = [lg for lg in _legs if not _is_redundant_o15(lg)]
                if len(_kept) != len(_legs):
                    c["_legs"] = _kept
                    _p = 1.0
                    for lg in _kept:
                        _p *= float(lg.get("odds") or 1.0)
                    c["_odd"] = round(_p, 2)
                    _others = [lg for lg in _kept if lg.get("kind") != "btts"
                               and "beide teams treffen" not in (lg.get("market", "") or "").lower()]
                    c["market"] = (f"Beide Teams treffen + {_others[0].get('market', '')} ({len(_kept)}er-Bet-Builder)"
                                   if _others else "Beide Teams treffen")
        market = c["market"]
        odds, real = c["_odd"], c["_real"]
        # Stars now come straight from the win probability (owner rule): the old 8.5
        # ceiling is gone — a ≥96% pick shows the full 10 stars, 90% → 9, etc.
        stars = max(1, min(10, round(winprob * 10)))
        # Owner (2026-07-10): a "Beide Teams treffen" market is a wobbly bet — cap it at
        # 6★ so it can never look like a near-certain 9/10★ pick.
        if "beide teams treffen" in market.lower():
            stars = min(stars, 6)
        rating = float(stars)
        score = r.get("score") or "?"
        avg = r.get("avg") or "?"
        is_combo = ptype == "combo"
        n_legs = len(c.get("_legs", []))
        if is_combo:
            builder = ("Bet-Builder: beide Teams treffen + höhere Torlinie (ohne redundante Legs) aus EINEM Spiel"
                       if n_legs >= 3 else
                       "Bet-Builder: klassisches beide Teams treffen aus EINEM Spiel")
            analysis = (
                f"TipJarHQ-Kombi ({n_legs}er-Leg): {market} — höheres Risiko, Quote {odds:.2f}. "
                f"Erwartetes Ergebnis {score}, Ø {avg} Tore. Anstoß {kickoff}. "
                f"{builder} — automatisch von TipJarHQ."
            )
        elif ptype == "banker":
            analysis = (
                f"TipJarHQ-Banker: {market} — {stars}/10 Sterne, sicherer Banker (Quote {odds:.2f}). "
                f"Erwartetes Ergebnis {score}, Ø {avg} Tore. "
                f"Anstoß {kickoff}. {'Echte Buchmacher-Quote. ' if real else ''}"
                f"Ideal für Kombi- & Systemwetten — automatisch von TipJarHQ."
            )
        else:
            analysis = (
                f"TipJarHQ-Value: {market} — {stars}/10 Sterne bei Quote {odds:.2f}. "
                f"Erwartetes Ergebnis {score}, Ø {avg} Tore. "
                f"Anstoß {kickoff}. {'Echte Buchmacher-Quote. ' if real else ''}"
                f"Datenbasierter Value-Pick — automatisch von TipJarHQ."
            )
        # Unique, opinionated analysis via LLM (falls back to the template above on failure).
        _ctx = (f"Wettbewerb: {r.get('league') or lcode}. Spiel: {home} vs {away}. "
                f"Markt/Tipp: {market}. Quote: {odds:.2f}. Sterne: {stars}/10. "
                f"Erwartetes Ergebnis {score}, Ø {avg} Tore. Typ: {ptype}. Anstoß {kickoff}.")
        _llm = await llm_pick_analysis(_ctx)
        if _llm:
            analysis = _llm
        combo_legs = c.get("_legs", []) if is_combo else []
        # "Δώρο" (Gift) flag — cross-cutting highlight for generous odds on a likely
        # outcome (dedicated gift-category rescues, high-odds combos, or ≥2.20 value).
        is_gift = (category == "gift") or (is_combo and odds >= 2.00) \
            or (odds >= 2.20 and winprob >= 0.55)
        # Frontend-friendly single-match display: one fixture row with all selection
        # chips (settlement uses the separate `combo_legs` with kind/team info).
        display_legs = []
        if is_combo:
            display_legs = [{
                "match": f"{home} – {away}",
                "league": r.get("league") or (lcode.upper() if lcode else ""),
                "kickoff": kickoff,
                "selections": [lg["market"] for lg in combo_legs],
                "sel_odds": [f"{lg['odds']:.2f}" for lg in combo_legs],
            }]
        # Always show the real competition on the tip (owner: "bei Single-Tipps muss das
        # Turnier drauf sein"). Friendlies are NOT blocked — they're clearly labelled.
        _raw_lg = (r.get("league") or "").strip()
        _lg_hay = f"{_raw_lg} {lcode} {cc}".lower()
        if "friendl" in _lg_hay or "freundschaft" in _lg_hay or "testspiel" in _lg_hay:
            league_disp = "Freundschaftsspiel"
        elif _raw_lg:
            league_disp = _raw_lg.title()
        elif lcode:
            league_disp = lcode.upper()
        else:
            league_disp = cc or "TipJarHQ Pick"
        tip = {
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away,
            "match_time": kickoff,
            "country": cc, "league": league_disp, "league_code": lcode,
            "market": market,
            "odds": f"{odds:.2f}", "ai_rating": rating, "ai_analysis": analysis,
            "win_prob": round(winprob, 3), "pick_type": ptype, "category": category,
            "is_gift": is_gift,
            "legs": display_legs, "combo_legs": combo_legs, "is_parlay": is_combo,
            "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": now,
        }
        await db.tips.insert_one(tip)
        posted += 1
        logger.info(f"HQ auto-posted (A/{ptype}): {home} vs {away} — {market} "
                    f"({round(winprob*100)}% @ {odds:.2f})")
    await _dedupe_hq_tips()
    return {"posted": posted, "scanned": len(rows), "candidates": len(candidates)}

async def forebet_loop():
    await asyncio.sleep(30)  # let startup settle
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
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
        await asyncio.sleep(30 * 60)  # every 30 minutes — post tips close to real-time

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
    # Owner rule (2026-07-18): NEVER post a standalone full-match "Über 0.5 Tore" — it is
    # near-certain and worthless as a headline bet. It may only ever appear as a SECONDARY
    # leg inside a bet-builder (handled by _forebet_candidates), never as a single here.
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
    if AUTOPOST_PAUSED:
        return {"posted": 0, "reason": "autopost paused (curated mode)"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    # Only auto-post from the start of TOMORROW (UTC) — today stays curated.
    _AUTOPOST_MIN_KO = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0)
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
           any(b in f" {_lg} " for b in SLIP_BLOCK_KEYWORDS) or \
           not any(k in _lg for k in SLIP_LEAGUE_KEYWORDS):
            continue
        if _team_or_league_blocked(home, away, r.get("league")):
            continue  # owner blacklist (teams/leagues)
        # Owner rule: only trust Predictz when Forebet agrees on the same match.
        if not _forebet_agrees(market, fb_map.get(_match_key(home, away))):
            continue
        match_time = _predictz_kickoff(r, d)
        _ko = _parse_kickoff(match_time)
        if _ko and _ko < _AUTOPOST_MIN_KO:
            continue  # today stays curated — only post tomorrow onward
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
        # Owner rule: the BANKER button must stay rare. A short-odds pick is a banker ONLY
        # if it's near-certain (Über 0.5 / DC / DNB / safe unders). A sub-1.40 pick that is
        # NOT banker-safe is neither a banker nor real value → DROP it (never dump in Value).
        if _od < 1.40:
            if _is_banker_safe(market):
                pcategory = "banker"
            else:
                continue
        elif _od <= 2.60:
            pcategory = "value"
        else:
            continue
        # STABILITY (owner): keep the first pick per match+category fixed — don't add a
        # second (e.g. Predictz value on a match Forebet already gave a value pick).
        if await db.tips.find_one({
            "source": "hq-auto", "status": "pending", "category": pcategory,
            "home_team": home, "away_team": away}):
            continue
        league = (r.get("league") or "").title() or "TipJarHQ Pick"
        if "friendl" in league.lower() or "freundschaft" in league.lower():
            league = "Freundschaftsspiel"
        analysis = (
            f"Sicherer Tor-Banker: erwartetes Ergebnis {r.get('pred')}. "
            f"{market} ist bei diesem Spielbild ein starker Pick. "
            f"{'Echte Buchmacher-Quote. ' if real else ''}"
            f"Rechtzeitig gepostet, damit du dein Systemwette-Programm aufbauen kannst — "
            f"automatisch von TipJarHQ."
        )
        _ctx = (f"Wettbewerb: {league}. Spiel: {home} vs {away}. Markt/Tipp: {market}. "
                f"Quote: {odds}. Sterne: {rating}/10. Erwartetes Ergebnis {r.get('pred')}. "
                f"Anstoß {match_time}.")
        _llm = await llm_pick_analysis(_ctx)
        if _llm:
            analysis = _llm
        tip = {
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away,
            "match_time": match_time,
            "country": "", "league": league, "market": market,
            "odds": odds, "ai_rating": rating, "ai_analysis": analysis,
            "pick_type": ptype, "category": pcategory,
            "is_gift": (_od >= 2.20 and float(rating) >= 5.5),
            "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": now,
        }
        await db.tips.insert_one(tip)
        posted += 1
        logger.info(f"HQ auto-posted (B): {home} vs {away} — {market} ({rating})")
    await _dedupe_hq_tips()
    return {"posted": posted, "scanned": len(rows), "candidates": len(candidates)}

async def predictz_loop():
    await asyncio.sleep(90)  # let startup + forebet (fills time index) settle first
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
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
        await asyncio.sleep(30 * 60)  # every 30 minutes — post tips close to real-time

def _goal_est(line) -> int:
    """Estimate a team's predicted goals from API-Football's goal-line advice string
    (e.g. '-1.5' → 1, '-2.5' → 2, '+2.5' → 3). Clamped to 0..4."""
    try:
        x = float(str(line).replace(" ", ""))
    except Exception:
        return 1
    est = round(abs(x) - 0.5) if x < 0 else round(abs(x) + 0.5)
    return max(0, min(4, int(est)))

def _parse_apifootball_prediction(entry: dict):
    """Turn one /predictions response element into (ph, pa, fav, fav_prob, btts, over25)
    or None if it can't be parsed."""
    pred = (entry or {}).get("predictions") or {}
    percent = pred.get("percent") or {}

    def _pct(v):
        try:
            return int(str(v).replace("%", "").strip())
        except Exception:
            return 0
    ph_p, pd_p, pa_p = _pct(percent.get("home")), _pct(percent.get("draw")), _pct(percent.get("away"))
    if ph_p == 0 and pd_p == 0 and pa_p == 0:
        return None
    if ph_p >= pa_p and ph_p >= pd_p:
        fav, fav_prob = "home", ph_p
    elif pa_p >= ph_p and pa_p >= pd_p:
        fav, fav_prob = "away", pa_p
    else:
        fav, fav_prob = "draw", pd_p
    goals = pred.get("goals") or {}
    ph = _goal_est(goals.get("home"))
    pa = _goal_est(goals.get("away"))
    advice = (pred.get("advice") or "").lower()
    total = ph + pa
    btts = ("both teams" in advice) or (ph >= 1 and pa >= 1)
    over25 = ("over 2.5" in advice) or ("+2.5" in str(pred.get("under_over") or "")) or total >= 3
    return ph, pa, fav, fav_prob, btts, over25

async def apifootball_predictions_autopost(day_offsets=(0, 1, 2), max_per_run=None) -> dict:
    """Fetch API-Football's own predictions for upcoming top-league fixtures the
    scrapers missed, and store them (source=apifootball) so Scorer-Radar / Tor-Prognose
    gain coverage. Quota-bounded and 24h-cached. `day_offsets`/`max_per_run` let the
    23:00 quota-burner widen the window + cap when there's surplus daily budget."""
    if not API_FOOTBALL_KEY:
        return {"posted": 0, "reason": "no API key"}
    cap = max_per_run or APIFOOTBALL_PRED_MAX_PER_RUN
    now = datetime.now(timezone.utc)
    # already-covered matches (any source) — we only FILL GAPS, never duplicate work
    existing = await db.match_predictions.find(
        {"status": "pending"}, {"_id": 0, "home": 1, "away": 1}).to_list(3000)
    covered = {_match_key(x.get("home"), x.get("away")) for x in existing}
    dates = [(now + timedelta(days=d)).date().isoformat() for d in day_offsets]
    posted, scanned, calls = 0, 0, 0
    for d in dates:
        if posted >= cap or _api_quota_exhausted():
            break
        fixtures = await _apifootball_async("/fixtures", {"date": d}) or []
        for fx in fixtures:
            if posted >= cap or _api_quota_exhausted():
                break
            status = ((fx.get("fixture") or {}).get("status") or {}).get("short")
            if status != "NS":
                continue  # only not-started matches
            lg = ((fx.get("league") or {}).get("name") or "")
            lgl = lg.lower()
            if not any(k in lgl for k in SLIP_LEAGUE_KEYWORDS):
                continue
            if any(b in f" {lgl} " for b in SLIP_BLOCK_KEYWORDS):
                continue
            teams = fx.get("teams") or {}
            home = (teams.get("home") or {}).get("name") or ""
            away = (teams.get("away") or {}).get("name") or ""
            if not home or not away or _is_women_or_youth(home) or _is_women_or_youth(away):
                continue
            if _team_or_league_blocked(home, away, lg):
                continue
            mkey = _match_key(home, away)
            if mkey in covered:
                continue  # a scraper already predicts this match → skip
            fid = str((fx.get("fixture") or {}).get("id"))
            if not fid:
                continue
            cache = await db.apifootball_pred_cache.find_one({"fixture_id": fid})
            if cache:
                try:
                    if now - datetime.fromisoformat(cache["cached_at"]) < timedelta(hours=APIFOOTBALL_PRED_CACHE_TTL_H):
                        continue  # fetched recently → don't spend quota again
                except Exception:
                    pass
            scanned += 1
            resp = await _apifootball_async("/predictions", {"fixture": fid})
            calls += 1
            await db.apifootball_pred_cache.update_one(
                {"fixture_id": fid}, {"$set": {"fixture_id": fid, "cached_at": now.isoformat()}}, upsert=True)
            if not resp:
                continue
            parsed = _parse_apifootball_prediction(resp[0])
            if not parsed:
                continue
            ph, pa, fav, fav_prob, btts, over25 = parsed
            kickoff = (fx.get("fixture") or {}).get("date") or ""
            country = ((fx.get("league") or {}).get("country") or "")
            try:
                await store_match_prediction(
                    "apifootball", fid, home, away, kickoff, ph, pa, fav, fav_prob,
                    btts, over25, fav_prob, league=lg, country=country)
                covered.add(mkey)
                posted += 1
            except Exception as e:
                logger.warning(f"apifootball prediction store failed: {e}")
    return {"posted": posted, "scanned": scanned, "api_calls": calls,
            "quota_exhausted": _api_quota_exhausted()}

async def apifootball_predictions_loop():
    await asyncio.sleep(120)  # let scrapers populate first so we only fill gaps
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            res = await apifootball_predictions_autopost()
            logger.info(f"HQ loop E (API-Football predictions): {res}")
        except Exception as e:
            logger.error(f"HQ loop E error: {e}")
        await asyncio.sleep(6 * 3600)  # every 6 hours

# ---------------------------------------------------------------------------
# Statarea scraper — a THIRD prediction source (1X2 + Over/Under probabilities).
# No API-Football quota cost (pure scrape). Stored as source "statarea"; treated
# as a gap-filler (priority below Forebet/Predictz) in the consumers.
# ---------------------------------------------------------------------------
def _statarea_est_score(p1, px, p2, over25):
    """Estimate a predicted scoreline from 1X2 + Over 2.5 probabilities so Statarea
    matches can feed the Scorer-Radar / Tor-Prognose. The favourite always scores
    at least as many as the underdog."""
    total = 3 if (over25 or 0) >= 52 else 2
    if p1 >= px and p1 >= p2:          # home favourite
        return (2, 1) if total >= 3 else (1, 0)
    if p2 >= p1 and p2 >= px:          # away favourite
        return (1, 2) if total >= 3 else (0, 1)
    return 1, 1                        # draw lean

async def statarea_autopost() -> dict:
    """Scrape Statarea and store today's whitelisted upcoming matches as match
    predictions (source=statarea). Additive gap-filler; no API quota used."""
    try:
        rows = await asyncio.wait_for(scrape_statarea(), timeout=SCRAPE_TIMEOUT)
    except Exception as e:
        logger.error(f"Statarea scrape failed: {e}")
        return {"posted": 0, "reason": "scrape failed"}
    if not rows:
        return {"posted": 0, "reason": "scrape empty"}
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    posted = 0
    for r in rows:
        home, away = r.get("home"), r.get("away")
        if not home or not away:
            continue
        if r.get("score"):
            continue  # already kicked off / finished → not a pre-match prediction
        if _is_women_or_youth(home) or _is_women_or_youth(away):
            continue
        if _team_or_league_blocked(home, away, r.get("league") or ""):
            continue
        p1, px, p2 = r.get("p1") or 0, r.get("px") or 0, r.get("p2") or 0
        if (p1 + px + p2) == 0:
            continue
        over25 = r.get("over25")
        sc = r.get("score")
        ph, pa = (sc[0], sc[1]) if sc else _statarea_est_score(p1, px, p2, over25)
        if p1 >= px and p1 >= p2:
            fav, fav_prob = "home", p1
        elif p2 >= p1 and p2 >= px:
            fav, fav_prob = "away", p2
        else:
            fav, fav_prob = "draw", px
        btts = ph >= 1 and pa >= 1
        over25_flag = (over25 or 0) >= 52 or (ph + pa) >= 3
        time = (r.get("time") or "").strip()
        kickoff = f"{today}T{time}:00+00:00" if time else f"{today}T18:00:00+00:00"
        league = (r.get("league") or "").strip()
        try:
            await store_match_prediction(
                "statarea", f"{home}-{away}", home, away, kickoff, ph, pa, fav,
                fav_prob, btts, over25_flag, fav_prob, league=league,
                country=r.get("country", ""))
            posted += 1
        except Exception as e:
            logger.warning(f"statarea prediction store failed: {e}")
    return {"posted": posted, "scanned": len(rows)}

async def statarea_loop():
    await asyncio.sleep(150)  # after forebet/predictz so it only fills gaps
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            if await ensure_chromium():
                res = await statarea_autopost()
                logger.info(f"HQ loop F (Statarea): {res}")
            else:
                logger.error("HQ loop F skipped: chromium unavailable — retry in 20 min")
                await asyncio.sleep(20 * 60)
                continue
        except Exception as e:
            logger.error(f"HQ loop F error: {e}")
        await asyncio.sleep(30 * 60)  # every 30 minutes — post tips close to real-time


async def footballpredictions_autopost() -> dict:
    """Scrape FootballPredictions.com (static HTML, no API quota / no Chromium) and
    store today's + upcoming predicted scorelines as match predictions
    (source=footballpred). Additive gap-filler that widens pre-match coverage."""
    try:
        rows = await scrape_footballpredictions()
    except Exception as e:
        logger.error(f"FootballPredictions scrape failed: {e}")
        return {"posted": 0, "reason": "scrape failed"}
    if not rows:
        return {"posted": 0, "reason": "scrape empty"}
    posted = 0
    for r in rows:
        home, away = r.get("home"), r.get("away")
        if not home or not away:
            continue
        if _is_women_or_youth(home) or _is_women_or_youth(away):
            continue
        league = (r.get("league") or "").strip()
        if _team_or_league_blocked(home, away, league):
            continue
        ph, pa = r.get("ph"), r.get("pa")
        if ph is None or pa is None:
            continue
        if ph > pa:
            fav, margin = "home", ph - pa
        elif pa > ph:
            fav, margin = "away", pa - ph
        else:
            fav, margin = "draw", 0
        fav_prob = {1: 55, 2: 63}.get(margin, 70) if fav != "draw" else 40
        btts = ph >= 1 and pa >= 1
        over25 = (ph + pa) >= 3
        try:
            await store_match_prediction(
                "footballpred", f"fp-{home}-{away}", home, away, r.get("kickoff") or "",
                ph, pa, fav, fav_prob, btts, over25, fav_prob,
                league=league, country=r.get("country", ""))
            posted += 1
        except Exception as e:
            logger.warning(f"footballpred store failed: {e}")
    return {"posted": posted, "scanned": len(rows)}


async def footballpredictions_loop():
    await asyncio.sleep(180)  # after the Chromium scrapers; static source needs no browser
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            res = await footballpredictions_autopost()
            logger.info(f"HQ loop G (FootballPredictions): {res}")
        except Exception as e:
            logger.error(f"HQ loop G error: {e}")
        await asyncio.sleep(30 * 60)  # every 30 minutes — post tips close to real-time



# --- footballinsight01 ("Magic Betting Tips") Telegram text-tip scraper ------------------
# Owner: use this channel as a SCRAPER feeding the TipJarHQ hq-auto pool — NOT as a new
# expert bot. Each post is a clean single pick (teams · market · league · kickoff).
FOOTBALLINSIGHT_CHANNEL = "footballinsight01"
FOOTBALLINSIGHT_MAX_PER_RUN = 8


def _fi_market(pick: str):
    """Map footballinsight's pick text → (German market label, fallback odds, family).
    Returns None for markets we don't post (corners/cards/unknown/odd goal lines)."""
    p = (pick or "").strip().lower()
    # never post non-goal markets (corners, cards, bookings, fouls, offsides, throw-ins)
    if any(w in p for w in ("corner", "card", "booking", "yellow", "red card",
                            "foul", "offside", "throw")):
        return None
    _GOAL_LINES = {"0.5", "1.5", "2.5", "3.5", "4.5"}
    m = re.search(r"over\s*(\d(?:\.\d)?)", p)
    mu = re.search(r"under\s*(\d(?:\.\d)?)", p)
    is_home = "home" in p
    is_away = "away" in p
    _over_fb = {"0.5": 1.30, "1.5": 1.55, "2.5": 1.90, "3.5": 3.00, "4.5": 5.00}
    _team_over_fb = {"0.5": 1.35, "1.5": 2.10, "2.5": 4.00}
    if ("both team" in p or "btts" in p or "gg" in p or "goal goal" in p) and not m:
        return ("Beide Teams treffen", 1.80, "btts")
    if m and m.group(1) in _GOAL_LINES:
        ln = m.group(1)
        if is_home:
            return (f"Heim über {ln} Tore", _team_over_fb.get(ln, 2.10), "team_goals")
        if is_away:
            return (f"Auswärts über {ln} Tore", _team_over_fb.get(ln, 2.10), "team_goals")
        return (f"Über {ln} Tore", _over_fb.get(ln, 2.00), "o25" if ln == "2.5" else "over")
    if mu and mu.group(1) in _GOAL_LINES:
        ln = mu.group(1)
        return (f"Unter {ln} Tore", {"1.5": 3.20, "2.5": 1.90, "3.5": 1.35}.get(ln, 1.90), "under")
    if "home" in p and ("win" in p or p.strip() == "home"):
        return ("Heimsieg", 2.00, "win")
    if "away" in p and ("win" in p or p.strip() == "away"):
        return ("Auswärtssieg", 2.30, "win")
    return None


def _fi_parse(text: str):
    """Parse a footballinsight 'Free pick' post → dict or None."""
    if not text or "🆚" not in text or "➡️" not in text:
        return None
    tm = re.search(r"([^\n🆚]+?)\s*🆚\s*([^\n]+)", text)
    pm = re.search(r"➡️\s*([^\n]+)", text)
    if not tm or not pm:
        return None
    home = re.sub(r"[🌏🏆🇮🇸\U0001F1E6-\U0001F1FF]", "", tm.group(1)).strip()
    away = re.sub(r"[🌏🏆🇮🇸\U0001F1E6-\U0001F1FF]", "", tm.group(2)).strip()
    pick = re.sub(r"\bPick\b", "", pm.group(1), flags=re.I).strip()
    dm = re.search(r"(\d{2})/(\d{2})/(\d{4}).*?\((\d{1,2}):(\d{2})\)", text, re.DOTALL)
    league = ""
    lm = re.search(r"➡️[^\n]+\n\s*\n?\s*([^\n]+)", text)
    if lm:
        league = re.sub(r"[🌏🏆🇮🇸\U0001F1E6-\U0001F1FF]", "", lm.group(1)).strip()
    match_time = ""
    if dm:
        d, mo, y, h, mi = map(int, dm.groups())
        try:
            match_time = datetime(y, mo, d, h, mi,
                                  tzinfo=timezone(timedelta(hours=1))).isoformat()
        except Exception:
            match_time = ""
    if not home or not away:
        return None
    return {"home": home, "away": away, "pick": pick, "league": league, "match_time": match_time}


async def footballinsight_autopost() -> dict:
    """Scrape footballinsight01's free single picks → post into the TipJarHQ hq-auto pool
    (no expert bot, no expert badge). Owner-requested: source, not persona."""
    if AUTOPOST_PAUSED:
        return {"posted": 0, "reason": "autopost paused (curated mode)"}
    hq = await db.users.find_one({"email": "hq@tipjar.com"})
    if not hq:
        return {"posted": 0, "reason": "HQ account missing"}
    import emptips_watch
    posts = await asyncio.to_thread(emptips_watch.fetch_telegram, FOOTBALLINSIGHT_CHANNEL)
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    posted = 0
    for p in posts:
        if posted >= FOOTBALLINSIGHT_MAX_PER_RUN:
            break
        parsed = _fi_parse(p.get("text", ""))
        if not parsed:
            continue
        mk = _fi_market(parsed["pick"])
        if not mk:
            continue
        market, fb_odds, family = mk
        home, away, league = parsed["home"], parsed["away"], parsed["league"]
        if _is_women_or_youth(home) or _is_women_or_youth(away):
            continue
        if _team_or_league_blocked(home, away, league):
            continue
        ko = _parse_kickoff(parsed["match_time"])
        if ko is None or ko < now:
            continue  # only future kickoffs
        tip_id = f"hqtip-fi-{p['id']}"
        if await db.tips.find_one({"id": tip_id}, {"_id": 1}):
            continue
        # keep one pick per match+market in the pool (avoid dupes across sources)
        if await db.tips.find_one({"source": "hq-auto", "status": "pending",
                                   "home_team": home, "away_team": away, "market": market}, {"_id": 1}):
            continue
        odds, real = await apply_real_odds(market, fb_odds, home, away, parsed["match_time"])
        try:
            _od = float(odds)
        except Exception:
            _od = fb_odds
        rating = 7.0 if _od <= 1.60 else (6.5 if _od <= 2.5 else 6.0)
        # Banker stays rare: sub-1.40 non-banker-safe picks are dropped, not dumped in Value.
        if _od < 1.40:
            if _is_banker_safe(market):
                pcategory = "banker"
            else:
                continue
        elif _od <= 2.60:
            pcategory = "value"
        else:
            continue
        ptype = "value" if _od >= VALUE_MIN_ODDS else "banker"
        lg = league or "TipJarHQ Pick"
        if "friendl" in lg.lower():
            lg = "Freundschaftsspiel"
        _ctx = (f"Wettbewerb: {lg}. Spiel: {home} vs {away}. Markt/Tipp: {market}. "
                f"Quote: {odds}. Anstoß {parsed['match_time']}.")
        analysis = await llm_pick_analysis(_ctx) or (
            f"{market} — solider Einzeltipp für {home} vs {away}. "
            f"{'Echte Buchmacher-Quote. ' if real else ''}Automatisch von TipJarHQ.")
        tip = {
            "id": tip_id, "user_id": hq["id"], "username": "TipJarHQ",
            "raw_text": "", "image_path": None,
            "home_team": home, "away_team": away, "match_time": parsed["match_time"],
            "country": "", "league": lg, "market": market,
            "odds": odds, "ai_rating": rating, "ai_analysis": analysis,
            "pick_type": ptype, "category": pcategory,
            "is_gift": (_od >= 2.20 and rating >= 5.5),
            "legs": [], "is_parlay": False, "stake": "", "potential_return": "",
            "status": "pending", "sum_stars": 0, "ratings_count": 0, "avg_rating": 0,
            "source": "hq-auto", "created_at": now_iso,
        }
        await db.tips.insert_one(tip)
        posted += 1
        logger.info(f"HQ auto-posted (FI): {home} vs {away} — {market} ({odds})")
    await _dedupe_hq_tips()
    return {"posted": posted, "scanned": len(posts)}


async def footballinsight_loop():
    await asyncio.sleep(150)
    while True:
        if not _is_leader():
            await asyncio.sleep(60)
            continue
        try:
            res = await footballinsight_autopost()
            logger.info(f"HQ loop FI (footballinsight01): {res}")
        except Exception as e:
            logger.error(f"HQ loop FI error: {e}")
        await asyncio.sleep(30 * 60)  # every 30 minutes — post tips close to real-time
