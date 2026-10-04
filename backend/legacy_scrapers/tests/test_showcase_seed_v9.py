"""
Iteration 9 backend regression tests:
- GET /api/tips returns ONLY the Portugal & Messi showcase tip
- The old Häcken parlay (seed-hacken-parlay) is fully removed
- Portugal & Messi tip has stake=25,00 € and potential_return=875,00 €
- Ratings endpoint still works for the remaining tip (regression)
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-credit-saver.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    return sess


@pytest.fixture(scope="module")
def all_tips(s):
    r = s.get(f"{API}/tips", timeout=30)
    assert r.status_code == 200, f"GET /api/tips failed: {r.status_code} {r.text}"
    data = r.json()
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    return data


class TestSeedShowcase:
    """Seed state on the preview deployment"""

    def test_only_portugal_messi_seed_exists(self, all_tips):
        seed_ids = [t["id"] for t in all_tips if t.get("id", "").startswith("seed-")]
        assert seed_ids == ["seed-portugal-messi"], f"Unexpected seed ids: {seed_ids}"

    def test_hacken_parlay_completely_removed(self, all_tips):
        for t in all_tips:
            assert t.get("id") != "seed-hacken-parlay", "seed-hacken-parlay still present"
            # Extra safety: no is_parlay Häcken tip anywhere
            teams = f"{t.get('home_team','')} {t.get('away_team','')}".lower()
            legs_txt = " ".join([str(l.get('match','')) for l in (t.get('legs') or [])]).lower()
            assert "häcken" not in teams and "häcken" not in legs_txt, \
                f"A Häcken tip still exists: {t.get('id')}"

    def test_portugal_messi_stake_and_winnings(self, all_tips):
        pm = next((t for t in all_tips if t["id"] == "seed-portugal-messi"), None)
        assert pm is not None
        assert pm.get("stake") == "25,00 €"
        assert pm.get("potential_return") == "875,00 €"
        assert pm.get("is_parlay") is False
        assert pm.get("odds") == "35.00"
        assert pm.get("ai_rating") == 2.0
        # image should still be present (photo of Messi/Portugal)
        assert pm.get("image_path"), "image_path missing on Portugal & Messi"

    def test_portugal_messi_country_league_used_for_flags(self, all_tips):
        """The frontend derives flags from country/league/team strings.
        We just verify the raw text contains recognisable tokens."""
        pm = next(t for t in all_tips if t["id"] == "seed-portugal-messi")
        hay = " ".join([
            pm.get("country") or "",
            pm.get("league") or "",
            pm.get("home_team") or "",
            pm.get("away_team") or "",
        ]).lower()
        assert "portugal" in hay, "team text should mention Portugal so 🇵🇹 flag renders"

    def test_seed_image_served(self, s, all_tips):
        pm = next(t for t in all_tips if t["id"] == "seed-portugal-messi")
        r = s.get(f"{API}/files/{pm['image_path']}", timeout=20)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("image/")
        assert len(r.content) > 1000


class TestRegression:
    """Basic regression: auth + ratings still work."""

    def test_hq_login(self, s):
        r = s.post(f"{API}/auth/login", json={"email": "hq@tipjar.com", "password": "TipJarHQ2026!"})
        assert r.status_code == 200
        assert r.json().get("token")

    def test_admin_login_and_rate(self, s):
        r = s.post(f"{API}/auth/login", json={"email": "admin@tipjar.com", "password": "TipJarAdmin2026!"})
        assert r.status_code == 200, r.text
        token = r.json()["token"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        # Rate the showcase tip 5 stars — endpoint should accept it (or 400 if already rated).
        r2 = requests.post(f"{API}/tips/seed-portugal-messi/rate", json={"stars": 5}, headers=headers, timeout=15)
        assert r2.status_code in (200, 400), f"Unexpected {r2.status_code}: {r2.text}"

    def test_tips_endpoint_count(self, all_tips):
        # There may be user-created @t.com tips lingering until next restart, but
        # showcase count must be exactly 1.
        seed_count = sum(1 for t in all_tips if t.get("id", "").startswith("seed-"))
        assert seed_count == 1
