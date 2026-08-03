"""TipJar betting-logic intelligence (owner rules, 2026-07-24).

Two jobs:
  1) dedupe_implied_legs(): remove any selection whose outcome is already
     logically ENTAILED by the combination of the other selections (adds no
     odds / value). Understands handicaps, totals, BTTS, 1X2, double chance.
  2) scoreline_to_combo(): express a predicted scoreline via a NON-redundant
     combination of markets instead of an exact "correct score" pick.

Constraints are evaluated over a bounded scoreline grid (home 0..7, away 0..7).
Markets we don't model as a scoreline constraint (half-time timing, corners,
cards, player props, "goal in each half") return None → treated as independent
and NEVER dropped and never used to imply another leg.
"""
import re

GRID = [(h, a) for h in range(8) for a in range(8)]


def _norm(s: str) -> str:
    return (s or "").lower().strip()


def _team_in(market: str, team: str) -> bool:
    t = _norm(team)
    return bool(t) and t in _norm(market)


def market_constraint(market: str, home: str, away: str):
    """Return a predicate f(h,a)->bool over integer scorelines, or None if the
    market is not a scoreline constraint (timing/props/corners/cards)."""
    m = _norm(market)
    if not m:
        return None

    # Timing / non-scoreline markets → independent (never redundant)
    if any(k in m for k in ("halbzeit", "1. hz", "2. hz", " hz", "each half",
                            "ecken", "corner", "karten", "card", "booking",
                            "schütze", "torschütze", "scorer", "anytime",
                            "spieler", "player", "assist", "foul", "einwurf",
                            "abseits", "elfmeter", "penalty", "eckball")):
        return None

    # "<team> schießt die ersten N Tore" / "first N goals" → that team scores at least N
    # (necessary condition; lets us drop a weaker implied leg like "<team> Über 0.5" so the
    # Bet-Builder stays PRECISE with no redundant legs).
    fg = re.search(r'(?:ersten?|first)\s*(\d+)\s*(?:tore?|goals?)', m)
    if fg:
        n = int(fg.group(1))
        if _team_in(market, home) and not _team_in(market, away):
            return lambda h, a, n=n: h >= n
        if _team_in(market, away) and not _team_in(market, home):
            return lambda h, a, n=n: a >= n
        return lambda h, a, n=n: (h + a) >= n

    # Correct score
    cs = re.search(r'(\d+)\s*[:\-]\s*(\d+)', m)
    if "genaues ergebnis" in m or "correct score" in m or (cs and "handicap" not in m and "über" not in m and "unter" not in m):
        if cs:
            x, y = int(cs.group(1)), int(cs.group(2))
            return lambda h, a, x=x, y=y: h == x and a == y

    # Handicap: "<team> -1.5 handicap" / "+1.5"
    hc = re.search(r'([+-]?\d+)\.5\s*handicap', m) or (re.search(r'([+-]\d+)\.5', m) if "handicap" in m else None)
    if hc and "handicap" in m:
        line = float(hc.group(1) + ".5") if hc.group(1).startswith(("+", "-")) else float(hc.group(1) + ".5")
        if _team_in(market, home):
            return lambda h, a, L=line: (h - a) + L > 0
        if _team_in(market, away):
            return lambda h, a, L=line: (a - h) + L > 0
        return None

    # BTTS
    if "beide teams treffen" in m or "btts" in m or m in ("gg", "gg/gg") or "both teams to score" in m:
        if "nein" in m or "no" in m or " ng" in m:
            return lambda h, a: not (h >= 1 and a >= 1)
        return lambda h, a: h >= 1 and a >= 1

    # Team total goals: "<team> über/unter X.5"
    tot = re.search(r'(über|ueber|over|unter|under)\s*(\d+)\.5', m)
    if tot:
        n = int(tot.group(2))
        is_over = tot.group(1) in ("über", "ueber", "over")
        # team-specific?
        if _team_in(market, home) and not _team_in(market, away):
            return (lambda h, a, n=n: h >= n + 1) if is_over else (lambda h, a, n=n: h <= n)
        if _team_in(market, away) and not _team_in(market, home):
            return (lambda h, a, n=n: a >= n + 1) if is_over else (lambda h, a, n=n: a <= n)
        # total goals
        return (lambda h, a, n=n: h + a >= n + 1) if is_over else (lambda h, a, n=n: h + a <= n)

    # Double chance
    if "doppelte chance" in m or "double chance" in m or re.search(r'\b(1x|x2|12)\b', m):
        if "1x" in m or ("heim" in m and "unent" in m):
            return lambda h, a: h >= a
        if "x2" in m or ("aus" in m and "unent" in m):
            return lambda h, a: a >= h
        if "12" in m:
            return lambda h, a: h != a

    # Draw no bet
    if "draw no bet" in m or "dnb" in m or "sieg oder unentschieden" in m:
        if _team_in(market, home):
            return lambda h, a: h >= a
        if _team_in(market, away):
            return lambda h, a: a >= h

    # Straight draw
    if "unentschieden" in m or re.search(r'\(x\)', m) or m == "x" or "draw" in m:
        return lambda h, a: h == a

    # Team win
    if "sieg" in m or " win" in m or m in ("1", "2"):
        if _team_in(market, home) or m == "1":
            return lambda h, a: h > a
        if _team_in(market, away) or m == "2":
            return lambda h, a: a > h

    return None


def _sat(pred):
    return {(h, a) for (h, a) in GRID if pred(h, a)}


def dedupe_implied_legs(legs, home, away, market_key="market"):
    """Drop legs whose outcome is entailed by the combination of the OTHERS
    (adds no odds / value). Fixpoint: repeatedly remove the weakest redundant
    leg (largest satisfying set) and recompute, until stable. Non-scoreline
    (timing/props) legs are always kept and never imply another leg.
    Returns (kept_legs, dropped_legs)."""
    scored, passthrough = [], []
    for lg in legs:
        mk = lg.get(market_key) if isinstance(lg, dict) else str(lg)
        pred = market_constraint(mk, home, away)
        if pred is None:
            passthrough.append(lg)
        else:
            s = _sat(pred)
            if not s:  # impossible/unparseable → keep, don't let it nuke others
                passthrough.append(lg)
            else:
                scored.append([lg, s])

    dropped = []
    changed = True
    while changed and len(scored) > 1:
        changed = False
        worst = None  # (index, satisfying-set size) of weakest redundant leg
        for i in range(len(scored)):
            others = set(GRID)
            for j in range(len(scored)):
                if j != i:
                    others &= scored[j][1]
            if others and others <= scored[i][1]:  # leg i implied by the others
                if worst is None or len(scored[i][1]) > worst[1]:
                    worst = (i, len(scored[i][1]))
        if worst is not None:
            dropped.append(scored.pop(worst[0])[0])
            changed = True

    keep_ids = {id(s[0]) for s in scored} | {id(p) for p in passthrough}
    kept = [lg for lg in legs if id(lg) in keep_ids]
    return kept, dropped


def scoreline_to_combo(ph, pa, home, away):
    """Express a predicted scoreline as a NON-redundant list of market strings
    (never an exact score). Returns list of market strings."""
    try:
        ph, pa = int(ph), int(pa)
    except Exception:
        return []
    legs = []
    margin = abs(ph - pa)
    fav = home if ph > pa else (away if pa > ph else None)
    both = ph >= 1 and pa >= 1
    total = ph + pa

    if fav is None:  # predicted draw
        legs.append("Doppelte Chance 1X" if ph >= pa else "Doppelte Chance X2")
        if both:
            legs.append("Beide Teams treffen (BTTS)")
    else:
        if margin >= 3:
            legs.append(f"{fav} -2.5 Handicap")
        elif margin >= 2:
            legs.append(f"{fav} -1.5 Handicap")
        else:
            legs.append(f"{fav} Sieg")
        if both:
            legs.append("Beide Teams treffen (BTTS)")

    # Add an over line ONLY if it raises the bar above what the legs already imply.
    tmp = [{"market": x} for x in legs]
    base_kept, _ = dedupe_implied_legs(tmp + [{"market": f"Über {total - 0.5:g} Tore"}], home, away)
    # find the smallest over line that is NOT redundant and matches predicted total
    for line in (total - 0.5,):
        cand = f"Über {line:g} Tore"
        _, dropped = dedupe_implied_legs(tmp + [{"market": cand}], home, away)
        if not any(d.get("market") == cand for d in dropped) and line >= 1.5:
            legs.append(cand)
            break

    kept, _ = dedupe_implied_legs([{"market": x} for x in legs], home, away)
    return [k["market"] for k in kept]
