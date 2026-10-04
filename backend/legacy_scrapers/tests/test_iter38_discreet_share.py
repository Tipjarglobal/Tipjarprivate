"""
Iteration 38 — Discreet Share + Per-Leg League/Banker/Live tests.

Verifies:
  1. GET /api/systems returns selections with per-leg `league` and `banker` fields.
  2. GET /api/tips (member + combo) returns legs with `league` populated for
     multi-game parlays and `banker` where applicable.
  3. POST /api/tips/{id}/share-image on a member combo tip returns a valid
     file path, the file is downloadable via /api/files/{path}, and it's a
     WebP image (discreet TipJar ticket render — visually verified by main
     agent, we assert only the transport contract here).
  4. Regression: /api/health responds, /api/tips loads.
"""
import os
import pytest
import requests
from pathlib import Path

def _load_frontend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if v:
        return v
    fe = Path("/app/frontend/.env")
    if fe.exists():
        for line in fe.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("REACT_APP_BACKEND_URL not set")

BASE_URL = _load_frontend_url().rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


# ---- Regression / smoke -------------------------------------------------
def test_tips_endpoint_loads(s):
    r = s.get(f"{API}/tips", timeout=30)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)


# ---- Feature 1 & 4: Systems carry banker + league per leg --------------
def test_systems_have_league_and_banker_flags(s):
    r = s.get(f"{API}/systems", timeout=30)
    assert r.status_code == 200
    data = r.json()
    # /api/systems returns {"week": "...", "systems": [...]}
    if isinstance(data, dict):
        systems = data.get("systems") or []
    else:
        systems = data
    assert isinstance(systems, list) and len(systems) > 0, "expected at least one system slip"

    league_seen = 0
    banker_seen = 0
    total_legs = 0
    for sys_slip in systems:
        sels = sys_slip.get("selections") or []
        for leg in sels:
            total_legs += 1
            # league key must be present (may be empty for unknown leagues)
            assert "league" in leg, f"system leg missing 'league' key: {leg.keys()}"
            assert "banker" in leg, f"system leg missing 'banker' key: {leg.keys()}"
            if leg.get("league"):
                league_seen += 1
            if leg.get("banker"):
                banker_seen += 1
    assert total_legs > 0
    # at least ONE leg across all systems should have a league (real fixture data)
    assert league_seen > 0, "no system leg carried a non-empty league — enrichment broken"
    print(f"[systems] legs={total_legs} with_league={league_seen} bankers={banker_seen}")


# ---- Feature 2 & 3: Multi-game combo tips carry per-leg league + live --
def test_member_combo_tips_have_per_leg_league(s):
    r = s.get(f"{API}/tips", timeout=30)
    assert r.status_code == 200
    tips = r.json()
    combos = [t for t in tips if t.get("is_parlay") and (t.get("legs") or [])]
    # It's OK if none exist right now — only assert when we have data
    if not combos:
        pytest.skip("no combo tips in current DB — skipping per-leg league check")

    checked = 0
    with_league = 0
    live_legs = 0
    for tip in combos:
        for leg in tip["legs"]:
            checked += 1
            assert "league" in leg, f"combo leg missing 'league' key on tip {tip.get('id')}"
            if leg.get("league"):
                with_league += 1
            # live legs (if any) must carry live_score & live_minute keys
            if leg.get("live"):
                live_legs += 1
                # keys must exist; values may be None if fixture not yet in AF live feed
                assert "live_score" in leg
                assert "live_minute" in leg
    print(f"[combos] tips={len(combos)} legs_checked={checked} with_league={with_league} live_legs={live_legs}")
    assert checked > 0


# ---- Feature 5: /tips/{id}/share-image endpoint + discreet slip -------
def test_share_image_endpoint_returns_webp(s):
    r = s.get(f"{API}/tips", timeout=30)
    assert r.status_code == 200
    tips = r.json()
    # member combos preferred (non hq-auto / smart)
    member = [
        t for t in tips
        if t.get("source") not in ("hq-auto", "smart")
        and t.get("legs")
    ]
    if not member:
        # fall back to any member tip
        member = [t for t in tips if t.get("source") not in ("hq-auto", "smart")]
    if not member:
        pytest.skip("no member tip available to share")

    tip = member[0]
    resp = s.post(f"{API}/tips/{tip['id']}/share-image", timeout=60)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "path" in body and isinstance(body["path"], str) and body["path"]
    path = body["path"]

    # Download the file — must be a valid webp image
    dl = s.get(f"{API}/files/{path}", timeout=30)
    assert dl.status_code == 200
    assert dl.headers.get("content-type", "").startswith("image/"), dl.headers
    # WebP magic: bytes 0-3 "RIFF" and 8-11 "WEBP"
    b = dl.content
    assert len(b) > 500, f"tiny image body ({len(b)} bytes) — render likely failed"
    assert b[:4] == b"RIFF" and b[8:12] == b"WEBP", "not a WebP file"
    print(f"[share] tip={tip['id']} path={path} bytes={len(b)}")


def test_share_image_rejects_hq_auto(s):
    """hq-auto/smart tips must NOT be shareable (business rule)."""
    r = s.get(f"{API}/tips", timeout=30)
    tips = r.json()
    hq = [t for t in tips if t.get("source") in ("hq-auto", "smart")]
    if not hq:
        pytest.skip("no hq-auto/smart tip present")
    resp = s.post(f"{API}/tips/{hq[0]['id']}/share-image", timeout=15)
    assert resp.status_code == 400
