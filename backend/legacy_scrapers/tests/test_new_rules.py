"""
Iteration-6 targeted tests for the two new rules and the analyze() shape fix:

1. POST /api/tips MUST reject empty match_time with HTTP 400 (new guard).
2. POST /api/tips with a non-empty match_time still succeeds.
3. POST /api/tips/analyze response MUST now include stake, potential_return, legs, is_parlay
   (these were previously dropped by analyze_tip()).
4. Regression: normal single-tip create+list still works.
"""

import io
import os
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
TIMEOUT = 90


def _rand_suffix() -> str:
    return uuid.uuid4().hex[:8]


def _register():
    email = f"TEST_{_rand_suffix()}@t.com"
    username = f"TEST_{_rand_suffix()}"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "secret1", "username": username,
        "timezone": "UTC", "language": "en",
    }, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _tiny_png_bytes() -> bytes:
    def _chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    raw = b"\x00\xff\x00\x00"
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


@pytest.fixture(scope="module")
def user():
    return _register()


# --------------------------------------------------------------------- RULE #1
class TestMatchTimeGuard:
    """POST /api/tips must reject empty/whitespace-only match_time with 400."""

    def test_create_tip_without_match_time_rejected(self, user):
        payload = {
            "raw_text": "Arsenal to win, no date given",
            "home_team": "Arsenal", "away_team": "",
            "match_time": "",  # empty → must be rejected
            "country": "", "league": "",
            "market": "Arsenal to win", "odds": "1.60",
            "ai_rating": 6.0, "ai_analysis": "text-only tip",
        }
        r = requests.post(f"{API}/tips", json=payload, headers=_auth(user["token"]), timeout=TIMEOUT)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        detail = r.json().get("detail", "")
        # exact message per server.py line 528
        assert "match date & time" in detail or "kickoff" in detail.lower(), \
            f"error detail missing kickoff wording: {detail!r}"

    def test_create_tip_with_whitespace_match_time_rejected(self, user):
        payload = {
            "raw_text": "no date",
            "home_team": "X", "away_team": "Y",
            "match_time": "   ",
            "market": "Home ML", "odds": "1.50",
            "ai_rating": 5.0, "ai_analysis": "n/a",
        }
        r = requests.post(f"{API}/tips", json=payload, headers=_auth(user["token"]), timeout=TIMEOUT)
        assert r.status_code == 400, f"whitespace should also be rejected, got {r.status_code}"

    def test_create_tip_with_match_time_succeeds(self, user):
        payload = {
            "raw_text": "Bayern vs Dortmund, 20/07/2026 20:30, Over 2.5 @ 1.90",
            "home_team": "Bayern", "away_team": "Dortmund",
            "match_time": "20/07/2026 20:30",
            "country": "Germany", "league": "Bundesliga",
            "market": "Over 2.5", "odds": "1.90",
            "ai_rating": 7.0, "ai_analysis": "solid line",
            "stake": "10", "potential_return": "19",
        }
        r = requests.post(f"{API}/tips", json=payload, headers=_auth(user["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        tip = r.json()
        assert tip["match_time"] == "20/07/2026 20:30"
        assert tip["home_team"] == "Bayern"
        assert tip["stake"] == "10"
        assert tip["potential_return"] == "19"
        # verify persisted
        r2 = requests.get(f"{API}/tips?status=pending&sort=new&limit=100", timeout=TIMEOUT)
        assert r2.status_code == 200
        assert any(t["id"] == tip["id"] for t in r2.json())


# --------------------------------------------------------------------- RULE #2
class TestAnalyzeReturnsFullShape:
    """analyze_tip() must now include stake, potential_return, legs, is_parlay."""

    def test_analyze_response_includes_all_keys(self, user):
        png = _tiny_png_bytes()
        files = {"file": ("bet.png", png, "image/png")}
        data = {"text": "Bayern vs Dortmund 20/07/2026 20:30, Over 2.5 @ 1.90, stake 25"}
        r = requests.post(f"{API}/tips/analyze", files=files, data=data,
                          headers=_auth(user["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        # THE key regression assertion — these keys were being dropped before the fix
        for k in ("stake", "potential_return", "legs", "is_parlay"):
            assert k in d, f"analyze response missing key: {k}. Response: {d}"
        # types
        assert isinstance(d["stake"], str)
        assert isinstance(d["potential_return"], str)
        assert isinstance(d["legs"], list)
        assert isinstance(d["is_parlay"], bool)
        # plus original keys still present
        for k in ("home_team", "away_team", "match_time", "country", "league",
                  "market", "odds", "rating", "analysis", "image_path"):
            assert k in d, f"analyze response missing existing key: {k}"

    def test_analyze_text_only_still_returns_shape(self, user):
        """No image, only text → still returns the full shape (fallback path OK too)."""
        data = {"text": "Arsenal to win no date"}
        r = requests.post(f"{API}/tips/analyze", data=data,
                          headers=_auth(user["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("stake", "potential_return", "legs", "is_parlay",
                  "home_team", "away_team", "match_time", "country",
                  "league", "market", "odds", "rating", "analysis"):
            assert k in d, f"missing key {k}"


# --------------------------------------------------------------------- RULE #3 (system prompt)
class TestSystemPromptContainsRules:
    """Sanity-check that the AI system prompt actually contains the new rules text.

    We can't easily assert the LLM output deterministically (Gemini live), but we
    CAN assert the server-side prompt string carries the two rules so future edits
    that regress the prompt are caught here.
    """

    def test_prompt_contains_stake_times_odds_rule(self):
        # Read the file that packages the prompt
        with open("/app/backend/server.py") as f:
            src = f.read()
        assert "stake MULTIPLIED BY odds" in src or "stake x odds" in src.lower() or "stake multiplied by odds" in src.lower(), \
            "AI_SYSTEM prompt must instruct 'stake x odds' rule"
        assert "IGNORE any tax" in src or "ignore any tax" in src.lower(), \
            "AI_SYSTEM prompt must instruct to ignore tax/fees"

    def test_prompt_requires_date_and_time_in_match_time(self):
        with open("/app/backend/server.py") as f:
            src = f.read()
        assert "match DATE and kickoff TIME" in src or "date and kickoff time" in src.lower(), \
            "AI_SYSTEM prompt must require DATE + TIME in match_time"

    def test_create_tip_guard_message_matches(self):
        with open("/app/backend/server.py") as f:
            src = f.read()
        # ensures the exact error message the frontend surfaces
        assert "Tip needs a match date & time" in src, \
            "create_tip must raise the exact 'Tip needs a match date & time' 400 message"


# --------------------------------------------------------------------- Regression
class TestRegressionSingleTip:
    """Regression: normal single-tip upload → analyze → publish still works E2E."""

    def test_full_single_tip_flow(self, user):
        png = _tiny_png_bytes()
        r = requests.post(f"{API}/tips/analyze",
                          files={"file": ("bet.png", png, "image/png")},
                          data={"text": "PSG vs Marseille 21/07/2026 21:00, Over 1.5 @ 1.50, stake 20"},
                          headers=_auth(user["token"]), timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        detected = r.json()

        # publish with a manually-forced match_time in case AI returned ''
        match_time = detected.get("match_time") or "21/07/2026 21:00"
        payload = {
            "raw_text": "PSG vs Marseille Over 1.5",
            "image_path": detected.get("image_path"),
            "home_team": detected.get("home_team") or "PSG",
            "away_team": detected.get("away_team") or "Marseille",
            "match_time": match_time,
            "country": detected.get("country", ""),
            "league": detected.get("league", ""),
            "market": detected.get("market") or "Over 1.5",
            "odds": detected.get("odds") or "1.50",
            "ai_rating": detected.get("rating", 5.0),
            "ai_analysis": detected.get("analysis", ""),
            "legs": detected.get("legs", []),
            "is_parlay": detected.get("is_parlay", False),
            "stake": detected.get("stake", ""),
            "potential_return": detected.get("potential_return", ""),
        }
        r2 = requests.post(f"{API}/tips", json=payload, headers=_auth(user["token"]), timeout=TIMEOUT)
        assert r2.status_code == 200, r2.text
        assert r2.json()["match_time"] == match_time
