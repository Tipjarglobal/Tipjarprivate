"""
Iteration-16: DELETE /api/tips/{tip_id}
- Admin can delete ANY tip
- Owner can delete their own
- Non-owner (regular user) gets 403 on someone else's
- 404 for non-existent tip
- Deleted tip disappears from GET /api/tips
"""
import os
import uuid
import requests
import pytest


def _load_backend_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL"):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return url.rstrip("/")


BASE_URL = _load_backend_url()
API = f"{BASE_URL}/api"
TIMEOUT = 60
ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"


def _rand():
    return uuid.uuid4().hex[:8]


def _auth(t):
    return {"Authorization": f"Bearer {t}"}


def _register(password="secret1"):
    body = {
        "email": f"TEST_{_rand()}@t.com",
        "password": password,
        "username": f"TEST_{_rand()}",
        "timezone": "UTC", "language": "en",
    }
    r = requests.post(f"{API}/auth/register", json=body, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _admin_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _create_tip(token, suffix):
    payload = {
        "raw_text": f"delete test {suffix}",
        "home_team": f"H_{suffix}", "away_team": f"A_{suffix}",
        "match_time": "Sat 21:00", "country": "International",
        "league": "Friendly", "market": "1X2 - Home",
        "odds": "1.50", "ai_rating": 5.0, "ai_analysis": "test",
    }
    r = requests.post(f"{API}/tips", json=payload, headers=_auth(token), timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()


class TestDeleteTip:

    def test_admin_can_delete_any_tip(self):
        user = _register()
        tip = _create_tip(user["token"], _rand())
        tip_id = tip["id"]

        admin_tok = _admin_token()
        r = requests.delete(f"{API}/tips/{tip_id}", headers=_auth(admin_tok), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("deleted") is True
        assert body.get("tip_id") == tip_id

        # verify gone from wall
        r_list = requests.get(f"{API}/tips?sort=new&limit=100", timeout=TIMEOUT)
        assert r_list.status_code == 200
        assert not any(t["id"] == tip_id for t in r_list.json())

    def test_owner_can_delete_own_tip(self):
        user = _register()
        tip = _create_tip(user["token"], _rand())
        tip_id = tip["id"]

        r = requests.delete(f"{API}/tips/{tip_id}", headers=_auth(user["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json().get("deleted") is True

        r_list = requests.get(f"{API}/tips?sort=new&limit=100", timeout=TIMEOUT)
        assert not any(t["id"] == tip_id for t in r_list.json())

    def test_non_owner_gets_403(self):
        owner = _register()
        other = _register()
        tip = _create_tip(owner["token"], _rand())
        tip_id = tip["id"]

        r = requests.delete(f"{API}/tips/{tip_id}", headers=_auth(other["token"]), timeout=TIMEOUT)
        assert r.status_code == 403, r.text
        # tip must still exist
        r_list = requests.get(f"{API}/tips?sort=new&limit=100", timeout=TIMEOUT)
        assert any(t["id"] == tip_id for t in r_list.json()), "tip should NOT be deleted by non-owner"

    def test_delete_nonexistent_returns_404(self):
        admin_tok = _admin_token()
        fake_id = f"nonexistent-{_rand()}"
        r = requests.delete(f"{API}/tips/{fake_id}", headers=_auth(admin_tok), timeout=TIMEOUT)
        assert r.status_code == 404

    def test_delete_requires_auth(self):
        # even without a body, unauthenticated must be rejected
        r = requests.delete(f"{API}/tips/any-id", timeout=TIMEOUT)
        assert r.status_code == 401
