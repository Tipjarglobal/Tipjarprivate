"""
Iteration 30 tests — TipJar features batch:
1. Mandatory self star-rating on POST /api/tips
2. Multi-image analyze endpoint (files field, up to 4)
3. AI area (source=ai) sorted ascending by kickoff (match_time)
4. Share-image endpoint for member tip (pending/live) — rejects hq-auto/smart
5. Combo AI picks (hq-auto is_parlay=true) with 2 legs on AI feed (soft check)
"""

import io
import os
import struct
import zlib

import pytest
import requests

def _load_frontend_env_url():
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env_url() or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL missing"

ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"


# ---- helpers -----------------------------------------------------------------
def _make_png_bytes(w: int = 4, h: int = 4) -> bytes:
    """Return a minimal valid PNG image as bytes (single-color)."""
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    raw = b""
    for _ in range(h):
        raw += b"\x00" + (b"\x00\x80\xff") * w  # filter byte + RGB pixels
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


@pytest.fixture(scope="module")
def admin_token():
    s = requests.Session()
    # /api/auth/login accepts email or username via `username` field
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
               timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    data = r.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        pytest.skip(f"No token in login response: {list(data.keys())}")
    return token


@pytest.fixture
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---- 1. Mandatory self star-rating ------------------------------------------
class TestMandatorySelfRating:
    def _base_payload(self):
        return {
            "raw_text": "TEST iter30 mandatory stars",
            "home_team": "TEST_HomeA_iter30",
            "away_team": "TEST_AwayA_iter30",
            "match_time": "2030-01-01 18:00",
            "country": "TEST",
            "league": "TEST",
            "market": "Over 2.5",
            "odds": "1.85",
            "ai_rating": 6.0,
            "ai_analysis": "test",
            "stake": "10",
            "potential_return": "18.50",
        }

    def test_post_tip_without_self_rating_returns_400(self, auth_headers):
        p = self._base_payload()
        # no self_rating field
        r = requests.post(f"{BASE_URL}/api/tips", json=p, headers=auth_headers, timeout=30)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:200]}"

    def test_post_tip_self_rating_zero_returns_400(self, auth_headers):
        p = self._base_payload()
        p["self_rating"] = 0
        p["home_team"] = "TEST_HomeB_iter30"
        r = requests.post(f"{BASE_URL}/api/tips", json=p, headers=auth_headers, timeout=30)
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text[:200]}"

    def test_post_tip_with_self_rating_ok(self, auth_headers):
        p = self._base_payload()
        p["self_rating"] = 7
        p["home_team"] = "TEST_HomeC_iter30"
        p["away_team"] = "TEST_AwayC_iter30"
        r = requests.post(f"{BASE_URL}/api/tips", json=p, headers=auth_headers, timeout=30)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:200]}"
        tip = r.json()
        assert tip.get("avg_rating") == 7.0, f"avg_rating={tip.get('avg_rating')}"
        assert tip.get("ratings_count") == 1, f"ratings_count={tip.get('ratings_count')}"
        assert tip.get("sum_stars") == 7
        # persistence check via GET /api/tips/mine (should include this tip)
        tip_id = tip.get("id")
        assert tip_id
        # cleanup
        requests.delete(f"{BASE_URL}/api/tips/{tip_id}", headers=auth_headers, timeout=15)


# ---- 2. Multi-image analyze --------------------------------------------------
class TestAnalyzeMulti:
    def test_analyze_text_only_no_files(self, auth_headers):
        r = requests.post(
            f"{BASE_URL}/api/tips/analyze",
            data={"text": "Bayern vs Dortmund — Over 2.5 @ 1.85"},
            headers=auth_headers,
            timeout=90,
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text[:300]}"
        data = r.json()
        assert data.get("image_paths") == [], f"image_paths={data.get('image_paths')}"
        assert data.get("safe") is True, f"safe={data.get('safe')}"

    def test_analyze_accepts_multiple_files_field(self, auth_headers):
        png = _make_png_bytes()
        files = [
            ("files", ("slip1.png", io.BytesIO(png), "image/png")),
            ("files", ("slip2.png", io.BytesIO(png), "image/png")),
        ]
        r = requests.post(
            f"{BASE_URL}/api/tips/analyze",
            data={"text": ""},
            files=files,
            headers=auth_headers,
            timeout=120,
        )
        # We only assert the endpoint accepts multi-file uploads (200 OK path).
        # AI may still return a low-confidence result but 200 is required.
        assert r.status_code == 200, (
            f"Multi-file analyze failed: {r.status_code} {r.text[:400]}"
        )
        data = r.json()
        assert "image_paths" in data
        assert isinstance(data["image_paths"], list)


# ---- 3. AI list sorted ascending by kickoff ---------------------------------
class TestAiSortedByKickoff:
    def test_ai_pending_sorted_by_kickoff_asc(self):
        r = requests.get(f"{BASE_URL}/api/tips", params={"source": "ai", "status": "pending"}, timeout=30)
        assert r.status_code == 200, f"list_tips failed: {r.status_code} {r.text[:200]}"
        tips = r.json()
        assert isinstance(tips, list)
        # parse match_time and confirm ascending
        from datetime import datetime, timezone as tz
        parsed = []
        for t in tips:
            mt = (t.get("match_time") or "").strip()
            dt = None
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
                try:
                    d = datetime.strptime(mt, fmt)
                    if d.tzinfo is None:
                        d = d.replace(tzinfo=tz.utc)
                    dt = d
                    break
                except Exception:
                    pass
            parsed.append(dt)
        # only enforce ordering across tips with parseable kickoff
        pairs = [(a, b) for a, b in zip(parsed, parsed[1:]) if a and b]
        for a, b in pairs:
            assert a <= b, f"AI feed not ascending by kickoff: {a} > {b}"


# ---- 4. Share-image endpoint -------------------------------------------------
class TestShareImage:
    def test_share_image_for_member_pending_tip(self, auth_headers):
        # create a member tip
        p = {
            "raw_text": "TEST iter30 share",
            "home_team": "TEST_ShareHome_iter30",
            "away_team": "TEST_ShareAway_iter30",
            "match_time": "2030-06-01 21:00",
            "country": "TEST", "league": "TEST",
            "market": "Over 2.5", "odds": "1.90",
            "ai_rating": 6.5, "ai_analysis": "share test",
            "stake": "10", "potential_return": "19",
            "self_rating": 6,
        }
        c = requests.post(f"{BASE_URL}/api/tips", json=p, headers=auth_headers, timeout=30)
        assert c.status_code == 200, f"create failed: {c.status_code} {c.text[:200]}"
        tip = c.json()
        tip_id = tip["id"]
        try:
            r = requests.post(f"{BASE_URL}/api/tips/{tip_id}/share-image", timeout=90)
            assert r.status_code == 200, f"share-image failed: {r.status_code} {r.text[:300]}"
            data = r.json()
            assert "path" in data and data["path"], f"missing path: {data}"
        finally:
            requests.delete(f"{BASE_URL}/api/tips/{tip_id}", headers=auth_headers, timeout=15)

    def test_share_image_rejects_hq_auto(self):
        # find an hq-auto tip
        r = requests.get(f"{BASE_URL}/api/tips", params={"source": "ai", "status": "pending"}, timeout=30)
        assert r.status_code == 200
        tips = r.json()
        if not tips:
            pytest.skip("No hq-auto tips available to test rejection")
        tid = tips[0].get("id")
        assert tid
        rr = requests.post(f"{BASE_URL}/api/tips/{tid}/share-image", timeout=30)
        assert rr.status_code == 400, f"Expected 400 for hq-auto share-image, got {rr.status_code}: {rr.text[:200]}"


# ---- 5. Combo AI picks (soft) -----------------------------------------------
class TestComboAI:
    def test_combo_ai_shape_soft(self):
        r = requests.get(f"{BASE_URL}/api/tips", params={"source": "ai", "status": "pending"}, timeout=30)
        assert r.status_code == 200
        tips = r.json()
        combos = [t for t in tips if t.get("is_parlay")]
        if not combos:
            pytest.skip("No hq-auto parlay tips present in DB (generated by scrapers over time) — soft skip.")
        for c in combos[:5]:
            legs = c.get("legs") or []
            assert isinstance(legs, list), f"legs not list: {legs}"
            # spec says 2-leg
            assert len(legs) == 2, f"parlay legs len={len(legs)} for tip {c.get('id')}"
