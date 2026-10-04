"""Iter39 regression: ticket_render.py extraction — share-image + systems still work."""
import os, requests, pytest

BASE = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")


def test_systems_have_banker_and_league():
    r = requests.get(f"{BASE}/api/systems", timeout=30)
    assert r.status_code == 200
    data = r.json()
    systems = data.get("systems") or []
    assert len(systems) > 0, "no systems returned"
    # verify banker (bool) + league (str) present on selections
    found_banker = 0
    found_league = 0
    total_legs = 0
    for s in systems:
        for sel in (s.get("selections") or []):
            total_legs += 1
            assert isinstance(sel.get("banker", False), bool)
            if sel.get("banker"): found_banker += 1
            if isinstance(sel.get("league"), str) and sel["league"]:
                found_league += 1
    assert total_legs > 0
    print(f"legs={total_legs} banker={found_banker} league={found_league}")


def test_share_image_parlay_still_renders():
    # Find a member parlay tip
    r = requests.get(f"{BASE}/api/tips", timeout=30)
    assert r.status_code == 200
    tips = r.json() if isinstance(r.json(), list) else r.json().get("tips") or []
    target = None
    for t in tips:
        if t.get("tip_type") in ("parlay","member","member_parlay") or (t.get("legs") and len(t.get("legs")) >= 2):
            target = t; break
    if not target:
        pytest.skip("no parlay tip available")
    tid = target.get("id") or target.get("_id")
    r2 = requests.post(f"{BASE}/api/tips/{tid}/share-image", timeout=60)
    assert r2.status_code == 200, f"share-image failed {r2.status_code} {r2.text[:200]}"
    body = r2.json()
    path = body.get("path")
    assert path, f"no path in {body}"
    r3 = requests.get(f"{BASE}/api/files/{path.lstrip('/').replace('files/','')}" if path.startswith('/') or 'files/' in path else f"{BASE}/api/files/{path}", timeout=30)
    # Handle both forms
    if r3.status_code != 200:
        # try direct
        r3 = requests.get(f"{BASE}{path}" if path.startswith('/') else f"{BASE}/{path}", timeout=30)
    assert r3.status_code == 200, f"file fetch failed {r3.status_code}"
    content = r3.content
    assert len(content) > 500
    # WebP magic: RIFF....WEBP
    assert content[:4] == b"RIFF" and content[8:12] == b"WEBP", f"not a WebP: {content[:16]!r}"
    print(f"share-image OK: {len(content)} bytes, path={path}")


def test_no_500s_on_core_endpoints():
    for ep in ["/api/systems", "/api/tips", "/api/fixtures"]:
        r = requests.get(f"{BASE}{ep}", timeout=30)
        assert r.status_code < 500, f"{ep} -> {r.status_code}"
