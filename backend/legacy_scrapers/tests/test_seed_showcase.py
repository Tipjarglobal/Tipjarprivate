"""
Iteration-8: TipJarHQ showcase seed verification.

Verifies that backend startup idempotently seeds:
  - user hq@tipjar.com / TipJarHQ (password from HQ_PASSWORD env, default 'TipJarHQ2026!')
  - tip id 'seed-portugal-messi' (Portugal & Messi, odds 35.00, ai_rating 2, image)
  - tip id 'seed-hacken-parlay' (Häcken parlay, is_parlay=true, odds 2.47, ai_rating 7, no image)

Regression:
  - POST /api/tips still enforces non-empty match_time (400).
  - Register/login for a normal user still works.
"""

import os
import uuid
import pytest
import requests


def _load_backend_url() -> str:
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        with open("/app/frontend/.env") as f:
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

HQ_EMAIL = "hq@tipjar.com"
HQ_PASSWORD = os.environ.get("HQ_PASSWORD", "TipJarHQ2026!")


def _auth(token: str):
    return {"Authorization": f"Bearer {token}"}


# ================================================================ Seed presence
class TestSeedPresence:

    def test_portugal_messi_seed_present(self):
        r = requests.get(f"{API}/tips?limit=100&sort=new", timeout=TIMEOUT)
        assert r.status_code == 200
        tips = r.json()
        messi = [t for t in tips if t.get("id") == "seed-portugal-messi"]
        assert len(messi) == 1, f"Expected exactly one seed-portugal-messi, got {len(messi)}"
        t = messi[0]
        assert t["username"] == "TipJarHQ"
        assert t["home_team"] == "Portugal & Lionel Messi"
        assert t["market"] == "Winner & Top Scorer"
        assert t["odds"] == "35.00"
        assert float(t["ai_rating"]) == 2.0
        assert t.get("stake") == "25,00 €"
        assert t.get("potential_return") == "875,00 €"
        assert t.get("is_parlay") in (False, None)
        assert t.get("image_path"), "Portugal & Messi tip should have image_path set"
        assert t["match_time"].strip() != ""

    def test_hacken_parlay_seed_present(self):
        r = requests.get(f"{API}/tips?limit=100&sort=new", timeout=TIMEOUT)
        assert r.status_code == 200
        tips = r.json()
        parlay = [t for t in tips if t.get("id") == "seed-hacken-parlay"]
        assert len(parlay) == 1, f"Expected exactly one seed-hacken-parlay, got {len(parlay)}"
        t = parlay[0]
        assert t["username"] == "TipJarHQ"
        # German umlaut preserved
        assert "Häcken" in t["home_team"], f"expected umlaut in home_team, got {t['home_team']}"
        assert "Djurgården" in t["home_team"]
        assert t["odds"] == "2.47"
        assert float(t["ai_rating"]) == 7.0
        assert t.get("potential_return") == "131,75 €"
        assert t["is_parlay"] is True
        assert isinstance(t.get("legs"), list) and len(t["legs"]) == 2
        # Verify umlauts in legs
        combined = " ".join(str(l) for l in t["legs"])
        assert "Häcken" in combined
        assert "Djurgården" in combined
        assert "Über" in combined
        # No image on parlay
        assert not t.get("image_path")


# ================================================================ Idempotency
class TestSeedIdempotency:

    def test_only_one_of_each_seeded_id(self):
        # Pull ALL tips (capped 100) and count occurrences of the two fixed seed ids.
        r = requests.get(f"{API}/tips?limit=100&sort=new", timeout=TIMEOUT)
        assert r.status_code == 200
        tips = r.json()
        messi = [t for t in tips if t.get("id") == "seed-portugal-messi"]
        parlay = [t for t in tips if t.get("id") == "seed-hacken-parlay"]
        assert len(messi) == 1, f"Duplicates for seed-portugal-messi: {len(messi)}"
        assert len(parlay) == 1, f"Duplicates for seed-hacken-parlay: {len(parlay)}"


# ================================================================ HQ Login
class TestHQLogin:

    def test_hq_login_returns_token(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": HQ_EMAIL, "password": HQ_PASSWORD}, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "token" in d and isinstance(d["token"], str) and len(d["token"]) > 20
        assert d["user"]["email"] == HQ_EMAIL
        assert d["user"]["username"] == "TipJarHQ"

    def test_hq_me_and_owns_seed_tips(self):
        r = requests.post(f"{API}/auth/login",
                          json={"email": HQ_EMAIL, "password": HQ_PASSWORD}, timeout=TIMEOUT)
        assert r.status_code == 200
        token = r.json()["token"]
        me = requests.get(f"{API}/auth/me", headers=_auth(token), timeout=TIMEOUT).json()["user"]
        hq_id = me["id"]
        # /tips/mine returns HQ's own tips
        mine = requests.get(f"{API}/tips/mine", headers=_auth(token), timeout=TIMEOUT)
        assert mine.status_code == 200
        mine_ids = [t["id"] for t in mine.json()]
        assert "seed-portugal-messi" in mine_ids
        assert "seed-hacken-parlay" in mine_ids
        # All belong to HQ user
        for t in mine.json():
            assert t["user_id"] == hq_id


# ================================================================ Seed image served
class TestSeedImageServed:

    def test_portugal_messi_image_resolves_via_files_endpoint(self):
        r = requests.get(f"{API}/tips?limit=100&sort=new", timeout=TIMEOUT)
        tips = r.json()
        messi = next(t for t in tips if t.get("id") == "seed-portugal-messi")
        image_path = messi.get("image_path")
        assert image_path, "seed-portugal-messi missing image_path"
        # GET /api/files/{path}
        r_img = requests.get(f"{API}/files/{image_path}", timeout=TIMEOUT)
        assert r_img.status_code == 200, f"expected 200 for image, got {r_img.status_code}: {r_img.text[:200]}"
        ctype = r_img.headers.get("content-type", "")
        assert "image/jpeg" in ctype, f"expected image/jpeg, got {ctype}"
        assert len(r_img.content) > 0


# ================================================================ Regression: create_tip guard + register/login
class TestRegressionGuards:

    def _register(self):
        suffix = uuid.uuid4().hex[:8]
        body = {
            "email": f"TEST_seed_{suffix}@t.com",
            "password": "secret1",
            "username": f"TEST_seed_{suffix}",
            "timezone": "UTC",
            "language": "en",
        }
        r = requests.post(f"{API}/auth/register", json=body, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        d["password"] = body["password"]
        return d

    def test_register_and_login_unaffected(self):
        u = self._register()
        assert "token" in u
        r = requests.post(f"{API}/auth/login",
                          json={"email": u["user"]["email"], "password": u["password"]}, timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.json()["user"]["email"] == u["user"]["email"]

    def test_create_tip_requires_match_time(self):
        u = self._register()
        payload = {
            "raw_text": "no match time provided",
            "home_team": "A", "away_team": "B",
            "match_time": "",  # empty on purpose
            "country": "International", "league": "Friendly",
            "market": "1X2 - Home", "odds": "1.50",
            "ai_rating": 5.0, "ai_analysis": "n/a",
        }
        r = requests.post(f"{API}/tips", json=payload, headers=_auth(u["token"]), timeout=TIMEOUT)
        assert r.status_code == 400, f"expected 400 for empty match_time, got {r.status_code}: {r.text}"
        detail = (r.json().get("detail") or "").lower()
        assert "match" in detail and ("date" in detail or "time" in detail or "kickoff" in detail)

    def test_create_tip_with_match_time_succeeds(self):
        u = self._register()
        payload = {
            "raw_text": "with match time",
            "home_team": "Alpha", "away_team": "Beta",
            "match_time": "Sat 21:00",
            "country": "International", "league": "Friendly",
            "market": "1X2 - Home", "odds": "1.80",
            "ai_rating": 5.0, "ai_analysis": "ok",
        }
        r = requests.post(f"{API}/tips", json=payload, headers=_auth(u["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        assert r.json()["home_team"] == "Alpha"
