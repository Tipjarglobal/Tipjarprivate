"""Real match-stats helper (2026-07-24) — free, uses the existing API-Football key.

Computes genuine hit-rates (BTTS, Over 2.5, form, clean sheets) from each team's
last-N finished fixtures + head-to-head, so the analyst can cite REAL numbers
(e.g. "BTTS 6/8") instead of inventing them. Results are cached in db.stats_cache
(12h TTL) to protect the daily API quota; when the quota is exhausted we return
None and the caller simply omits stats (never fabricates)."""
from datetime import datetime, timezone, timedelta

from core import db, logger, _apifootball_async, _api_quota_exhausted

FINISHED = {"FT", "AET", "PEN"}
CACHE_TTL_H = 12


def compute_form(fixtures, team_id):
    """Pure: summarise a team's finished fixtures. Returns a stats dict."""
    played = w = d = l = btts = over25 = scored = conceded_cnt = cs = fts = 0
    results = []
    for fx in fixtures or []:
        if (fx.get("fixture", {}).get("status", {}).get("short")) not in FINISHED:
            continue
        teams = fx.get("teams", {})
        goals = fx.get("goals", {})
        gh, ga = goals.get("home"), goals.get("away")
        if gh is None or ga is None:
            continue
        is_home = teams.get("home", {}).get("id") == team_id
        gf, gaf = (gh, ga) if is_home else (ga, gh)
        played += 1
        if gf > gaf:
            w += 1; results.append("W")
        elif gf == gaf:
            d += 1; results.append("D")
        else:
            l += 1; results.append("L")
        if gh >= 1 and ga >= 1:
            btts += 1
        if gh + ga >= 3:
            over25 += 1
        if gf >= 1:
            scored += 1
        else:
            fts += 1
        if gaf == 0:
            cs += 1
        conceded_cnt += gaf
    return {
        "played": played, "w": w, "d": d, "l": l,
        "btts": btts, "over25": over25, "scored": scored,
        "failed_to_score": fts, "clean_sheets": cs,
        "form": "".join(results[:5]),
    }


def compute_h2h(fixtures):
    played = btts = over25 = 0
    for fx in fixtures or []:
        goals = fx.get("goals", {})
        gh, ga = goals.get("home"), goals.get("away")
        if gh is None or ga is None:
            continue
        played += 1
        if gh >= 1 and ga >= 1:
            btts += 1
        if gh + ga >= 3:
            over25 += 1
    return {"played": played, "btts": btts, "over25": over25}


async def _cached(key, fetch_coro):
    doc = await db.stats_cache.find_one({"key": key})
    if doc:
        try:
            at = datetime.fromisoformat(doc["at"])
            if datetime.now(timezone.utc) - at < timedelta(hours=CACHE_TTL_H):
                return doc["data"]
        except Exception:
            pass
    if _api_quota_exhausted():
        return doc["data"] if doc else None  # stale-but-better-than-nothing
    data = await fetch_coro()
    if data is not None:
        await db.stats_cache.update_one(
            {"key": key},
            {"$set": {"key": key, "data": data, "at": datetime.now(timezone.utc).isoformat()}},
            upsert=True)
    return data


async def team_form(team_id, n=8):
    if not team_id:
        return None

    async def _f():
        fx = await _apifootball_async("/fixtures", {"team": team_id, "last": n})
        if fx is None:
            return None
        return compute_form(fx, team_id)

    return await _cached(f"form-{team_id}-{n}", _f)


async def h2h_stats(id1, id2, n=6):
    if not id1 or not id2:
        return None
    a, b = sorted([id1, id2])

    async def _f():
        fx = await _apifootball_async("/fixtures/headtohead", {"h2h": f"{id1}-{id2}", "last": n})
        if fx is None:
            return None
        return compute_h2h(fx)

    return await _cached(f"h2h-{a}-{b}-{n}", _f)


# ── "Zyklus"-Analyse (owner 2026-06): H2H-Historie + Heim/Auswärtsform, um zu WITTERN,
#    welches Team endlich TREFFEN oder GEWINNEN "muss" (Muster kehren im Zyklus zurück). ──
def _finished_meetings(fixtures):
    """Finished meetings, NEWEST-first: [{year, home_id, away_id, gh, ga}]."""
    out = []
    for fx in fixtures or []:
        if (fx.get("fixture", {}).get("status", {}).get("short")) not in FINISHED:
            continue
        g = fx.get("goals", {})
        gh, ga = g.get("home"), g.get("away")
        if gh is None or ga is None:
            continue
        t = fx.get("teams", {})
        date = (fx.get("fixture", {}) or {}).get("date", "") or ""
        out.append({
            "year": date[:4], "date": date,
            "home_id": t.get("home", {}).get("id"),
            "away_id": t.get("away", {}).get("id"),
            "gh": gh, "ga": ga,
        })
    out.sort(key=lambda m: m["date"], reverse=True)
    return out


async def h2h_detailed(id1, id2, n=10):
    """Per-meeting H2H history (newest-first), cached — for drought/cycle detection."""
    if not id1 or not id2:
        return None
    a, b = sorted([id1, id2])

    async def _f():
        fx = await _apifootball_async("/fixtures/headtohead", {"h2h": f"{id1}-{id2}", "last": n})
        if fx is None:
            return None
        return _finished_meetings(fx)

    return await _cached(f"h2hdet-{a}-{b}-{n}", _f)


async def team_recent(team_id, n=20):
    """Raw finished fixtures (newest-first) for a team — for home/away venue splits."""
    if not team_id:
        return None

    async def _f():
        fx = await _apifootball_async("/fixtures", {"team": team_id, "last": n})
        if fx is None:
            return None
        rows = []
        for f in fx:
            if (f.get("fixture", {}).get("status", {}).get("short")) not in FINISHED:
                continue
            g = f.get("goals", {})
            gh, ga = g.get("home"), g.get("away")
            if gh is None or ga is None:
                continue
            t = f.get("teams", {})
            rows.append({
                "date": (f.get("fixture", {}) or {}).get("date", "") or "",
                "home_id": t.get("home", {}).get("id"),
                "away_id": t.get("away", {}).get("id"),
                "gh": gh, "ga": ga,
            })
        rows.sort(key=lambda r: r["date"], reverse=True)
        return rows

    return await _cached(f"recent-{team_id}-{n}", _f)


def venue_split(rows, team_id, want_home, k=6):
    """Team's most recent matches at ONE venue (home or away), newest-first:
    [{gf, ga, res}]. Used to spot 'hasn't scored away in 3 games' style droughts."""
    seq = []
    for r in rows or []:
        is_home = r.get("home_id") == team_id
        is_away = r.get("away_id") == team_id
        if want_home and not is_home:
            continue
        if (not want_home) and not is_away:
            continue
        gf, ga = (r["gh"], r["ga"]) if is_home else (r["ga"], r["gh"])
        res = "W" if gf > ga else "D" if gf == ga else "L"
        seq.append({"gf": gf, "ga": ga, "res": res, "year": (r.get("date") or "")[:4]})
    return seq[:k]


def _scoreless_streak(seq):
    """How many of the most-recent matches (from the front) the team failed to score in."""
    n = 0
    for m in seq:
        if m["gf"] == 0:
            n += 1
        else:
            break
    return n


def _winless_streak(seq):
    n = 0
    for m in seq:
        if m["res"] in ("L", "D"):
            n += 1
        else:
            break
    return n


def stats_summary_text(home, away, hf, af, h2h):
    """German one-liner of the real numbers (or '' if nothing usable)."""
    parts = []
    if hf and hf.get("played"):
        parts.append(f"{home}: Form {hf['form'] or '–'} · BTTS {hf['btts']}/{hf['played']} · "
                     f"Über 2.5 {hf['over25']}/{hf['played']} · {hf['scored']}/{hf['played']} getroffen")
    if af and af.get("played"):
        parts.append(f"{away}: Form {af['form'] or '–'} · BTTS {af['btts']}/{af['played']} · "
                     f"Über 2.5 {af['over25']}/{af['played']} · {af['scored']}/{af['played']} getroffen")
    if h2h and h2h.get("played"):
        parts.append(f"H2H (letzte {h2h['played']}): BTTS {h2h['btts']}/{h2h['played']} · "
                     f"Über 2.5 {h2h['over25']}/{h2h['played']}")
    return " | ".join(parts)
