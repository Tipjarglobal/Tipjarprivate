"""Regression tests for TipJar auth (username + optional email) and Forebet autopost."""
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-credit-saver.preview.emergentagent.com").rstrip("/")


def _uniq(prefix="TEST"):
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


class TestAuthOptionalEmail:
    def test_register_without_email(self):
        username = _uniq("noemail")
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username, "password": "secret123",
            "timezone": "Europe/Berlin", "language": "de",
        }, timeout=15)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "token" in data and len(data["token"]) > 20
        u = data["user"]
        assert u["username"] == username
        assert u["email"] in (None, "")
        assert u["email_verified"] is True, f"email_verified should be True for email-less signup, got: {u}"

    def test_register_with_email(self):
        username = _uniq("withemail")
        email = f"{username}@example.com"
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": username, "email": email, "password": "secret123",
            "timezone": "Europe/Berlin", "language": "de",
        }, timeout=15)
        assert r.status_code == 200, r.text
        u = r.json()["user"]
        assert u["email"] == email
        assert u["username"] == username

    def test_multiple_email_less_accounts(self):
        # partial unique index on email allows many null emails
        u1 = _uniq("multi1"); u2 = _uniq("multi2")
        for uname in (u1, u2):
            r = requests.post(f"{BASE_URL}/api/auth/register", json={
                "username": uname, "password": "secret123",
            }, timeout=15)
            assert r.status_code == 200, r.text

    def test_duplicate_username_rejected(self):
        uname = _uniq("dup")
        r1 = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": uname, "password": "secret123",
        }, timeout=15)
        assert r1.status_code == 200
        r2 = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": uname, "password": "secret123",
        }, timeout=15)
        assert r2.status_code in (400, 409), f"expected 400/409, got {r2.status_code} {r2.text}"

    def test_login_by_username(self):
        uname = _uniq("loginu"); pwd = "secret123"
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": uname, "password": pwd,
        }, timeout=15)
        assert r.status_code == 200
        # login by username
        lr = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": uname, "password": pwd,
        }, timeout=15)
        assert lr.status_code == 200, lr.text
        assert lr.json()["user"]["username"] == uname

    def test_login_by_email(self):
        uname = _uniq("loginm"); email = f"{uname}@example.com"; pwd = "secret123"
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "username": uname, "email": email, "password": pwd,
        }, timeout=15)
        assert r.status_code == 200
        # login using email in the username field
        lr = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": email, "password": pwd,
        }, timeout=15)
        assert lr.status_code == 200, lr.text
        u = lr.json()["user"]
        assert u["email"] == email and u["username"] == uname

    def test_admin_login_by_email_still_works(self):
        lr = requests.post(f"{BASE_URL}/api/auth/login", json={
            "username": "admin@tipjar.com", "password": "TipJarAdmin2026!",
        }, timeout=15)
        assert lr.status_code == 200, lr.text
        assert lr.json()["user"]["role"] == "admin"


class TestForebetAutopost:
    def test_forebet_tip_on_wall(self):
        r = requests.get(f"{BASE_URL}/api/tips?limit=200", timeout=15)
        assert r.status_code == 200
        tips = r.json()
        forebet = [t for t in tips if str(t.get("id", "")).startswith("forebet-")]
        assert len(forebet) >= 1, "expected at least one forebet-* tip on the rate wall"
        fb = forebet[0]
        assert fb.get("source") == "forebet"
        assert fb.get("username") == "TipJarHQ"
        assert fb.get("league") == "Forebet Pick"
        assert fb.get("market"), "market should be set (e.g. 'X gewinnt' / 'Unentschieden')"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
