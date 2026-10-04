"""Iter 47: Master Avatar + anti-underdog + honest live banger + stats dedup"""
import os, requests, pytest

BASE = os.environ.get('REACT_APP_BACKEND_URL', 'https://ai-credit-saver.preview.emergentagent.com').rstrip('/')

def test_master_avatar_endpoint():
    r = requests.get(f"{BASE}/api/master/avatar", timeout=30)
    assert r.status_code == 200
    j = r.json()
    assert set(["count", "calls", "generated_at"]).issubset(j.keys())
    assert j["count"] == len(j["calls"])
    assert j["count"] >= 3
    required = {"id", "home_team", "away_team", "market", "odds",
                "avatar_minute", "avatar_text", "avatar_confidence", "drought", "status"}
    for c in j["calls"]:
        assert required.issubset(c.keys()), f"Missing keys in call: {required - set(c.keys())}"
        assert c["avatar_minute"] in (40, 60, 75, 90)

def test_master_avatar_seeded_teams():
    r = requests.get(f"{BASE}/api/master/avatar", timeout=30).json()
    teams = {c["home_team"] for c in r["calls"]}
    for expected in ["Bayern Munich", "Real Madrid", "Barcelona"]:
        assert expected in teams, f"Missing seeded team {expected}"

def test_goal_thirst_anti_underdog():
    r = requests.get(f"{BASE}/api/goal-thirst", timeout=30)
    assert r.status_code == 200
    j = r.json()
    # 'will score' list must not have clear away underdogs of strong favourites
    ws = j.get("will_score") or j.get("willScore") or j.get("teams") or []
    assert isinstance(ws, list)
    # We only assert 200; deeper anti-underdog rule requires knowing opponent fav_prob.

def test_tips_master_slips():
    r = requests.get(f"{BASE}/api/tips?source=master&mcat=slips", timeout=30)
    assert r.status_code == 200

def test_tips_master_avatar():
    r = requests.get(f"{BASE}/api/tips?source=master&mcat=avatar", timeout=30)
    assert r.status_code == 200

def test_live_honest_banger_rating():
    r = requests.get(f"{BASE}/api/tips?source=live", timeout=30)
    assert r.status_code == 200
    tips = r.json()
    if isinstance(tips, dict):
        tips = tips.get("tips", tips.get("items", []))
    high_over = ("Über 3.5 Tore", "Über 4.5 Tore", "Über 5.5 Tore")
    offenders = []
    for t in tips or []:
        market = str(t.get("selection") or t.get("market") or t.get("bet_type") or "")
        rating = t.get("ai_rating") or t.get("rating") or 0
        try:
            rating = float(rating)
        except Exception:
            rating = 0
        status = str(t.get("status", "")).lower()
        if any(h in market for h in high_over) and rating > 7.0 and status in ("live", "pending", "", "open"):
            offenders.append({"market": market, "rating": rating, "id": t.get("id")})
    assert not offenders, f"High over-line tips rated >7: {offenders}"

def test_ht_goal_forecast_dedup():
    r = requests.get(f"{BASE}/api/ht-goal-forecast", timeout=30)
    assert r.status_code == 200
    j = r.json()
    fixtures = j if isinstance(j, list) else (j.get("fixtures") or j.get("items") or j.get("matches") or [])
    seen = set()
    dups = []
    for f in fixtures:
        h = (f.get("home_team") or f.get("home") or "").strip().lower()
        a = (f.get("away_team") or f.get("away") or "").strip().lower()
        if not h or not a:
            continue
        key = tuple(sorted([h, a]))
        if key in seen:
            dups.append(key)
        seen.add(key)
    assert not dups, f"Duplicate fixtures found: {dups}"
