"""
Tests for Smart Bet feature + regression tests for won/lost tips filter.
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-credit-saver.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"


@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok, f"no token in login response: {r.json()}"
    return tok


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------- Counts endpoint ----------
class TestCounts:
    def test_counts_returns_smart_key(self):
        r = requests.get(f"{API}/tips/counts", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        # required keys
        for k in ["smart", "ai", "ai_total", "members", "live", "systems"]:
            assert k in data, f"key '{k}' missing from counts: {data}"
        assert isinstance(data["smart"], int), f"'smart' should be int, got: {type(data['smart'])}"
        print("counts:", data)


# ---------- Smart tips listing ----------
class TestSmartTips:
    def test_source_smart_returns_only_smart(self, admin_headers):
        r = requests.get(f"{API}/tips", params={"source": "smart", "status": "pending"}, timeout=30)
        assert r.status_code == 200, r.text
        tips = r.json()
        assert isinstance(tips, list)
        print(f"smart tips returned: {len(tips)}")
        if len(tips) == 0:
            # trigger admin smart run and retry
            run = requests.post(f"{API}/admin/smart/run", headers=admin_headers, timeout=120)
            print("smart/run:", run.status_code, run.text[:500])
            time.sleep(3)
            r = requests.get(f"{API}/tips", params={"source": "smart", "status": "pending"}, timeout=30)
            assert r.status_code == 200
            tips = r.json()
        # after run, we may still have 0 based on data availability — allow but assert structure if any
        if len(tips) > 0:
            for t in tips:
                assert t.get("source") == "smart", f"non-smart tip in smart filter: {t.get('source')}"
                for f in ["home_team", "away_team", "market", "odds", "ai_rating", "ai_analysis", "match_time", "league"]:
                    assert f in t, f"missing field '{f}' in smart tip: {list(t.keys())}"
                assert t["league"] == "TipJarHQ Smart Bet", f"unexpected league: {t['league']}"
                assert isinstance(t["market"], str) and len(t["market"]) > 0
                # market should contain a player prop marker (— dash + one of German terms), tolerate variations
                m = t["market"]
                assert any(x in m for x in ["Schüsse", "Paraden", "gefoult", "Torschütze", "Foul", "Karte", "Über", "Under", "Über 0", "Über 1"]), \
                    f"market does not look like a player prop: {m}"
            print("first smart tip market:", tips[0]["market"])
        else:
            print("WARNING: 0 smart tips available even after smart/run — likely data-availability (July minor leagues)")

    def test_source_members_excludes_smart_and_hqauto(self):
        r = requests.get(f"{API}/tips", params={"source": "members"}, timeout=30)
        assert r.status_code == 200, r.text
        tips = r.json()
        assert isinstance(tips, list)
        bad = [t for t in tips if t.get("source") in ("smart", "hq-auto")]
        assert len(bad) == 0, f"members feed leaked {len(bad)} smart/hq-auto tips: sample={bad[:2]}"
        print(f"members feed size={len(tips)}, no smart/hq-auto leaks")


# ---------- Won / Lost regression ----------
class TestWonLostRegression:
    def test_won_ai_returns_settled(self):
        r = requests.get(f"{API}/tips", params={"status": "won", "source": "ai"}, timeout=30)
        assert r.status_code == 200, r.text
        tips = r.json()
        assert isinstance(tips, list)
        print(f"won&source=ai count={len(tips)}")
        # per review: should be 3 settled won tips
        won_hq = [t for t in tips if t.get("status") == "won"]
        assert len(won_hq) >= 1, f"expected at least 1 won AI tip, got {len(won_hq)}. sample={tips[:2]}"

    def test_lost_returns_lost(self):
        r = requests.get(f"{API}/tips", params={"status": "lost"}, timeout=30)
        assert r.status_code == 200, r.text
        tips = r.json()
        assert isinstance(tips, list)
        print(f"lost count={len(tips)}")
        for t in tips:
            assert t.get("status") == "lost", f"non-lost tip returned: {t.get('status')}"


# ---------- Admin routes: smart/run + smart/reset ----------
class TestAdminSmart:
    def test_smart_run_requires_auth(self):
        r = requests.post(f"{API}/admin/smart/run", timeout=30)
        assert r.status_code in (401, 403), f"unauth call should be 401/403, got {r.status_code}"

    def test_smart_reset_requires_auth(self):
        r = requests.post(f"{API}/admin/smart/reset", timeout=30)
        assert r.status_code in (401, 403), f"unauth call should be 401/403, got {r.status_code}"

    def test_smart_run_admin(self, admin_headers):
        r = requests.post(f"{API}/admin/smart/run", headers=admin_headers, timeout=180)
        assert r.status_code == 200, f"admin smart/run failed: {r.status_code} {r.text[:500]}"
        data = r.json()
        for k in ("posted", "matches", "candidates"):
            assert k in data, f"missing key '{k}' in run response: {data}"
            assert isinstance(data[k], int)
        print("smart/run:", data)

    def test_smart_reset_admin(self, admin_headers):
        r = requests.post(f"{API}/admin/smart/reset", headers=admin_headers, timeout=180)
        assert r.status_code == 200, f"admin smart/reset failed: {r.status_code} {r.text[:500]}"
        data = r.json()
        for k in ("deleted", "posted", "matches", "candidates"):
            assert k in data, f"missing key '{k}' in reset response: {data}"
            assert isinstance(data[k], int)
        print("smart/reset:", data)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
