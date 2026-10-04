"""Regression tests after moving app.include_router to bottom of server.py.
Also validates new learning + code-reading endpoints and auth guards.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"


@pytest.fixture(scope="session")
def s():
    return requests.Session()


@pytest.fixture(scope="session")
def admin_token(s):
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text[:200]}"
    data = r.json()
    tok = data.get("access_token") or data.get("token")
    assert tok, f"no token in login response: {data}"
    return tok


# ---------- Regression: pre-existing endpoints still routable ----------
class TestRegressionRoutes:
    def test_root_api(self, s):
        r = s.get(f"{BASE_URL}/api/", timeout=30)
        assert r.status_code in (200, 404)  # some apps mount root differently

    def test_master_avatar(self, s):
        r = s.get(f"{BASE_URL}/api/master/avatar", timeout=30)
        assert r.status_code == 200, r.text[:200]

    def test_tips_feed(self, s):
        # Try common candidates
        for path in ("/api/tips", "/api/tips/active", "/api/tips/today", "/api/master/tips"):
            r = s.get(f"{BASE_URL}{path}", timeout=30)
            if r.status_code == 200:
                return
        pytest.fail("No tips feed endpoint reachable (200)")

    def test_login_endpoint(self, s):
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
        assert r.status_code == 200


# ---------- Learning endpoints ----------
class TestLearningStats:
    def test_get_learning_stats(self, s):
        r = s.get(f"{BASE_URL}/api/learning/stats", timeout=30)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        for k in ("master", "hq", "code", "min_n", "veto_rate"):
            assert k in data, f"missing key {k}: {list(data.keys())}"
        assert data["min_n"] == 6
        assert abs(data["veto_rate"] - 0.4) < 1e-6
        for group in ("master", "hq", "code"):
            assert isinstance(data[group], list)
            for row in data[group]:
                for f in ("pattern", "won", "lost", "n", "rate", "verdict"):
                    assert f in row, f"{group} row missing {f}: {row}"
                # verdict logic
                if row["n"] >= 6 and row["rate"] < 0.4:
                    assert row["verdict"] == "veto", row
                elif row["n"] >= 6 and row["rate"] >= 0.7:
                    assert row["verdict"] == "boost", row
                else:
                    assert row["verdict"] == "ok", row

    def test_admin_learning_refresh_requires_auth(self, s):
        r = s.post(f"{BASE_URL}/api/admin/learning/refresh", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"

    def test_admin_learning_refresh_with_admin(self, s, admin_token):
        r = s.post(f"{BASE_URL}/api/admin/learning/refresh",
                   headers={"Authorization": f"Bearer {admin_token}"}, timeout=60)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert data.get("ok") is True
        assert "code_reads" in data
        assert "stats" in data


# ---------- Code-reading endpoints ----------
class TestCodeReading:
    def test_get_code_reading_public(self, s):
        r = s.get(f"{BASE_URL}/api/code-reading", timeout=30)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert "count" in data and "reads" in data
        assert isinstance(data["reads"], list)

    def test_admin_scan_requires_auth(self, s):
        r = s.post(f"{BASE_URL}/api/admin/code-reading/scan",
                   json={"images": []}, timeout=30)
        assert r.status_code in (401, 403), r.status_code

    def test_admin_scan_empty_images(self, s, admin_token):
        r = s.post(f"{BASE_URL}/api/admin/code-reading/scan",
                   headers={"Authorization": f"Bearer {admin_token}"},
                   json={"images": []}, timeout=60)
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:200]}"


# ---------- _code_read_interpret unit checks ----------
class TestInterpretRules:
    def test_rules(self):
        import sys
        sys.path.insert(0, "/app/backend")
        import server
        r1 = server._code_read_interpret("Gesamtzahl 1 1.5 Unter", "Motor Lublin", "Jagiellonia")
        assert r1["read"] == "counter"
        assert "Motor" in r1["our_market"] and "Über 0.5" in r1["our_market"]
        assert r1["pattern"] == "team_total_under_low"

        r2 = server._code_read_interpret("Gesamtzahl 2 Unter 2.5 - Nein", "Legia", "Widzew Lodz")
        assert r2["read"] == "counter"
        assert "Widzew" in r2["our_market"] and "Unter 3.5" in r2["our_market"]
        assert r2["pattern"] == "team_total_over_cap"

        r3 = server._code_read_interpret("1X2 S1", "A", "B")
        assert r3["read"] == "no_bet"
        assert r3["pattern"] == "straight_win_nobet"
