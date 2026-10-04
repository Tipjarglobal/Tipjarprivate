"""Iteration 26 - Hall of Fame, /wins/claim validation, 5 systems, counts, no leaderboard."""
import os
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-credit-saver.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PW = "TipJarAdmin2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PW}, timeout=30)
    assert r.status_code == 200, r.text
    tok = r.json().get("token")
    assert tok
    return tok


# --- Hall of Fame -----------------------------------------------------------
class TestHallOfFame:
    def test_hall_of_fame_ok(self):
        r = requests.get(f"{BASE_URL}/api/wins/hall-of-fame", timeout=20)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)


# --- Wins claim validation --------------------------------------------------
class TestWinsClaim:
    def test_unauth_returns_401(self):
        r = requests.post(f"{BASE_URL}/api/wins/claim", data={"type": "played"},
                          files={"file": ("x.png", b"fake", "image/png")}, timeout=30)
        assert r.status_code in (401, 403)

    def test_bad_type_returns_400(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = requests.post(f"{BASE_URL}/api/wins/claim", headers=headers,
                          data={"type": "xxx"},
                          files={"file": ("x.png", b"fake", "image/png")}, timeout=30)
        assert r.status_code == 400
        assert "Invalid claim type" in r.text

    def test_non_slip_rejected(self, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        # Use a real (non-slip) png from the repo
        path = "/app/test_reports/iter9_tipcard.png"
        if not os.path.exists(path):
            pytest.skip("no sample image available")
        with open(path, "rb") as fh:
            r = requests.post(f"{BASE_URL}/api/wins/claim", headers=headers,
                              data={"type": "played"},
                              files={"file": ("slip.png", fh, "image/png")}, timeout=90)
        # Gemini rejects: 422 "Nur GEWONNENE Scheine zählen"
        assert r.status_code == 422, f"status={r.status_code} body={r.text}"
        assert "GEWONNEN" in r.text or "Won" in r.text or "gewonnen" in r.text.lower()


# --- Systems (5 winning-focused systems) ------------------------------------
class TestSystems:
    def test_five_systems_keys(self):
        r = requests.get(f"{BASE_URL}/api/systems", timeout=20)
        assert r.status_code == 200
        data = r.json()
        systems = data.get("systems", [])
        assert len(systems) == 5, f"expected 5 systems, got {len(systems)}"
        keys = {s["key"] for s in systems}
        assert keys == {"lock", "value", "smartvalue", "risk", "gamble"}, keys

    def test_lock_low_total_odds(self):
        data = requests.get(f"{BASE_URL}/api/systems", timeout=20).json()
        lock = next(s for s in data["systems"] if s["key"] == "lock")
        # each selection must have numeric odds
        for sel in lock["selections"]:
            assert isinstance(sel.get("odds"), (int, float)) and sel["odds"] > 1.0
        assert 1.05 <= lock["total_odds"] <= 1.9, lock["total_odds"]

    def test_all_selections_have_numeric_odds_and_total(self):
        data = requests.get(f"{BASE_URL}/api/systems", timeout=20).json()
        for s in data["systems"]:
            assert isinstance(s.get("total_odds"), (int, float))
            for sel in s.get("selections", []):
                assert isinstance(sel.get("odds"), (int, float))
                assert sel["odds"] > 1.0


# --- Counts endpoint --------------------------------------------------------
class TestCounts:
    def test_counts_shape_and_systems_five(self):
        r = requests.get(f"{BASE_URL}/api/tips/counts", timeout=20)
        assert r.status_code == 200
        d = r.json()
        for key in ("ai", "ai_total", "members", "live", "systems", "smart"):
            assert key in d, f"missing {key}"
            assert isinstance(d[key], int)
        assert d["systems"] == 5, d


# --- No leaderboard route (was removed) -------------------------------------
class TestNoLeaderboard:
    def test_leaderboard_endpoint_still_exists_or_not(self):
        # This endpoint may still exist server-side even if UI removed the section.
        # We only assert that IF present, it doesn't error, and IF absent, 404 is fine.
        r = requests.get(f"{BASE_URL}/api/leaderboard", timeout=20)
        assert r.status_code in (200, 404)
