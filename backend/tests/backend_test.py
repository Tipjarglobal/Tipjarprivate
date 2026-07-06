"""
TipJar backend integration tests.

Covers:
- Auth (register/login/me/profile update + username uniqueness)
- Tips analyze (multipart image, fallback rating OK)
- Tips create + list (status, sort=new/hype/top)
- Rating flow (avg/count updates, no double-count, streak)
- Admin settle Won/Lost and 403 for non-admin
- Leaderboard
- Credits: packages, checkout (Stripe session created), gift (fee+debit+credit), redeem threshold
- Notifications: subscribe/stats/unsubscribe (no auth)
"""

import io
import os
import time
import uuid
import struct
import zlib

import pytest
import requests


def _load_backend_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        env_path = "/app/frontend/.env"
        if os.path.exists(env_path):
            with open(env_path) as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL"):
                        url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
    if not url:
        raise RuntimeError("REACT_APP_BACKEND_URL not set")
    return url.rstrip("/")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"
TIMEOUT = 60

ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"


# --------------------------------------------------------------------- helpers
def _rand_suffix() -> str:
    return uuid.uuid4().hex[:8]


def _register(email: str = None, username: str = None, password: str = "secret1"):
    email = email or f"TEST_{_rand_suffix()}@t.com"
    username = username or f"TEST_{_rand_suffix()}"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": password, "username": username,
        "timezone": "UTC", "language": "en",
    }, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    data["password"] = password
    return data


def _tiny_png_bytes() -> bytes:
    # minimal 1x1 red PNG built without external libs
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\x00\x00"  # filter byte + RGB
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


# --------------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def user_a():
    return _register()


@pytest.fixture(scope="session")
def user_b():
    return _register()


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


# ================================================================ Auth
class TestAuth:

    def test_root(self):
        r = requests.get(f"{API}/", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "TipJar" in r.json().get("message", "")

    def test_register_returns_token_and_welcome_credits(self, user_a):
        assert "token" in user_a and isinstance(user_a["token"], str)
        user = user_a["user"]
        assert user["credits"] == 100
        assert user["received_credits"] == 0
        assert user["role"] == "user"
        assert user["language"] == "en"
        assert user["timezone"] == "UTC"

    def test_login_success(self, user_a):
        r = requests.post(f"{API}/auth/login",
                          json={"email": user_a["user"]["email"], "password": user_a["password"]}, timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert "token" in data and data["user"]["email"] == user_a["user"]["email"]

    def test_login_invalid(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": "nobody@nowhere.com", "password": "xxxxxx"}, timeout=TIMEOUT)
        assert r.status_code == 401

    def test_me_requires_bearer(self, user_a):
        r = requests.get(f"{API}/auth/me", timeout=TIMEOUT)
        assert r.status_code == 401
        r = requests.get(f"{API}/auth/me", headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["user"]["email"] == user_a["user"]["email"]

    def test_profile_update_username_and_lang(self, user_a):
        new_username = f"TEST_{_rand_suffix()}"
        r = requests.put(f"{API}/auth/profile",
                         json={"username": new_username, "language": "de", "timezone": "Europe/Berlin"},
                         headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u["username"] == new_username
        assert u["language"] == "de"
        assert u["timezone"] == "Europe/Berlin"
        # persistence via GET /me
        r2 = requests.get(f"{API}/auth/me", headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r2.json()["user"]["username"] == new_username
        user_a["user"]["username"] = new_username

    def test_username_uniqueness_enforced(self, user_a, user_b):
        # try renaming user_b to user_a's username
        r = requests.put(f"{API}/auth/profile",
                         json={"username": user_a["user"]["username"]},
                         headers=_auth(user_b["token"]), timeout=TIMEOUT)
        assert r.status_code == 400
        assert "taken" in r.json().get("detail", "").lower()


# ================================================================ Tips analyze/create/list
class TestTips:

    def test_analyze_returns_shape(self, user_a):
        png = _tiny_png_bytes()
        files = {"file": ("bet.png", png, "image/png")}
        data = {"text": "Home team to win, Argentina vs Cape Verde"}
        r = requests.post(f"{API}/tips/analyze", files=files, data=data,
                          headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        # required fields
        for k in ("home_team", "away_team", "match_time", "country", "league",
                  "market", "odds", "rating", "analysis", "image_path"):
            assert k in d, f"missing {k} in {d}"
        assert 1.0 <= float(d["rating"]) <= 10.0
        # image_path either None (upload failed) or a string path — endpoint should still be 200.
        pytest.tipjar_last_analyze = d  # stash for next test

    def test_create_tip_persisted(self, user_a):
        payload = {
            "raw_text": "Argentina to win",
            "image_path": getattr(pytest, "tipjar_last_analyze", {}).get("image_path"),
            "home_team": "Argentina", "away_team": "Cape Verde",
            "match_time": "Sat 21:00", "country": "International",
            "league": "Friendly", "market": "1X2 - Home",
            "odds": "1.40", "ai_rating": 5.0, "ai_analysis": "Neutral fallback",
        }
        r = requests.post(f"{API}/tips", json=payload, headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        tip = r.json()
        assert tip["status"] == "pending"
        assert tip["home_team"] == "Argentina"
        assert tip["ratings_count"] == 0
        assert "id" in tip
        pytest.tipjar_tip_id = tip["id"]

    def test_list_pending_new(self):
        r = requests.get(f"{API}/tips?status=pending&sort=new", timeout=TIMEOUT)
        assert r.status_code == 200
        tips = r.json()
        assert any(t["id"] == pytest.tipjar_tip_id for t in tips)

    def test_list_sort_hype(self):
        r = requests.get(f"{API}/tips?sort=hype", timeout=TIMEOUT)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_sort_top(self):
        r = requests.get(f"{API}/tips?sort=top", timeout=TIMEOUT)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ================================================================ Rating & Streak
class TestRating:

    def test_rate_new(self, user_b):
        r = requests.post(f"{API}/tips/{pytest.tipjar_tip_id}/rate",
                          json={"stars": 8}, headers=_auth(user_b["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["tip"]["ratings_count"] == 1
        assert d["tip"]["avg_rating"] == 8.0
        assert d["your_stars"] == 8
        assert d["streak"] >= 1

    def test_rate_again_no_double_count(self, user_b):
        r = requests.post(f"{API}/tips/{pytest.tipjar_tip_id}/rate",
                          json={"stars": 6}, headers=_auth(user_b["token"]), timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        # still 1 rating from user_b, but stars changed to 6
        assert d["tip"]["ratings_count"] == 1
        assert d["tip"]["avg_rating"] == 6.0

    def test_rate_bounds(self, user_b):
        r = requests.post(f"{API}/tips/{pytest.tipjar_tip_id}/rate",
                          json={"stars": 11}, headers=_auth(user_b["token"]), timeout=TIMEOUT)
        assert r.status_code == 422

    def test_rate_unknown_tip(self, user_b):
        r = requests.post(f"{API}/tips/nonexistent-id/rate",
                          json={"stars": 5}, headers=_auth(user_b["token"]), timeout=TIMEOUT)
        assert r.status_code == 404


# ================================================================ Admin
class TestAdmin:

    def test_settle_won_as_admin(self, admin_token):
        r = requests.put(f"{API}/tips/{pytest.tipjar_tip_id}/status",
                         json={"status": "won"}, headers=_auth(admin_token), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "won"

    def test_settle_non_admin_forbidden(self, user_a):
        r = requests.put(f"{API}/tips/{pytest.tipjar_tip_id}/status",
                         json={"status": "lost"}, headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 403


# ================================================================ Leaderboard
class TestLeaderboard:
    def test_leaderboard_shape(self):
        r = requests.get(f"{API}/leaderboard", timeout=TIMEOUT)
        assert r.status_code == 200
        rows = r.json()
        assert isinstance(rows, list)
        if rows:
            for k in ("user_id", "username", "total_tips", "won", "win_rate", "avg_ai_rating"):
                assert k in rows[0]


# ================================================================ Credits
class TestCredits:

    def test_packages(self):
        r = requests.get(f"{API}/credits/packages", timeout=TIMEOUT)
        assert r.status_code == 200
        pkgs = r.json()
        assert set(pkgs.keys()) == {"starter", "pro", "whale"}
        assert pkgs["pro"]["credits"] == 1200

    def test_checkout_creates_stripe_session(self, user_a):
        r = requests.post(f"{API}/credits/checkout",
                          json={"package_id": "pro", "origin_url": BASE_URL},
                          headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["url"].startswith("https://")
        assert "session_id" in d and d["session_id"]

    def test_gift_flow(self, user_a, user_b):
        # ensure user_a has fresh balance snapshot
        me_a = requests.get(f"{API}/auth/me", headers=_auth(user_a["token"]), timeout=TIMEOUT).json()["user"]
        me_b = requests.get(f"{API}/auth/me", headers=_auth(user_b["token"]), timeout=TIMEOUT).json()["user"]
        amount = 50
        r = requests.post(f"{API}/credits/gift",
                          json={"to_username": me_b["username"], "amount": amount},
                          headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["fee"] == 5  # 10% of 50
        assert d["received"] == 45
        # sender debited full amount
        assert d["user"]["credits"] == me_a["credits"] - amount
        # receiver credited and received_credits increased
        me_b2 = requests.get(f"{API}/auth/me", headers=_auth(user_b["token"]), timeout=TIMEOUT).json()["user"]
        assert me_b2["credits"] == me_b["credits"] + 45
        assert me_b2["received_credits"] == me_b["received_credits"] + 45

    def test_gift_yourself_errors(self, user_a):
        me = requests.get(f"{API}/auth/me", headers=_auth(user_a["token"]), timeout=TIMEOUT).json()["user"]
        r = requests.post(f"{API}/credits/gift",
                          json={"to_username": me["username"], "amount": 10},
                          headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 400
        assert "yourself" in r.json()["detail"].lower()

    def test_gift_insufficient_balance(self, user_a, user_b):
        me_b = requests.get(f"{API}/auth/me", headers=_auth(user_b["token"]), timeout=TIMEOUT).json()["user"]
        r = requests.post(f"{API}/credits/gift",
                          json={"to_username": me_b["username"], "amount": 10_000_000},
                          headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 400
        assert "enough" in r.json()["detail"].lower()

    def test_redeem_below_threshold(self, user_a):
        r = requests.post(f"{API}/credits/redeem", headers=_auth(user_a["token"]), timeout=TIMEOUT)
        assert r.status_code == 400
        assert "10000" in r.json()["detail"]


# ================================================================ Notifications
class TestNotifications:

    def test_subscribe_no_auth(self):
        anon = f"anon_{_rand_suffix()}"
        r = requests.post(f"{API}/notifications/subscribe", json={"anon_id": anon}, timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert d["subscribed"] is True
        assert d["subscriber_count"] >= 1
        pytest.tipjar_anon = anon

    def test_stats(self):
        r = requests.get(f"{API}/notifications/stats", timeout=TIMEOUT)
        assert r.status_code == 200
        d = r.json()
        assert "subscriber_count" in d and "total_tips" in d

    def test_unsubscribe(self):
        anon = getattr(pytest, "tipjar_anon", None)
        assert anon is not None
        r = requests.post(f"{API}/notifications/unsubscribe", json={"anon_id": anon}, timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["subscribed"] is False
