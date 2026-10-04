"""
Tests for the UPDATED Smart Bets IDEA feature (multipart + real fixture).

Contract additions (Jan 2026):
- POST /api/smart/idea is now MULTIPART (text form field + optional 'files' UploadFiles).
- The endpoint MUST NOT create a tip without a real kickoff date/time.
  * If no fixture is found, returns {ok:true, created:false, reason:'no_fixture'}.
  * If created, tip.match_time is a NON-EMPTY string like '25/10/2026 16:00'.
- Auth-gating still holds (401/403 without token).
"""
import os
import re
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-credit-saver.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"

MATCH_TIME_RE = re.compile(r"^\d{2}/\d{2}/\d{4} \d{2}:\d{2}")


# ---------- Fixtures ----------
@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    payload = r.json()
    tok = payload.get("token") or payload.get("access_token")
    assert tok, f"no token in login response: {payload}"
    return tok


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ---------- Auth-gating ----------
class TestSmartIdeaAuthMultipart:
    def test_unauth_multipart(self):
        # multipart POST without Authorization must be 401/403
        r = requests.post(
            f"{API}/smart/idea",
            data={"text": "Real Madrid gegen Barcelona: beide Teams treffen und über 2.5 Tore"},
            timeout=30,
        )
        assert r.status_code in (401, 403), f"unauth call must be 401/403, got {r.status_code}: {r.text[:200]}"


# ---------- Validation (multipart) ----------
class TestSmartIdeaValidationMultipart:
    def test_too_short_text_no_files_returns_400(self, admin_headers):
        r = requests.post(
            f"{API}/smart/idea",
            headers=admin_headers,
            data={"text": "hi"},
            timeout=30,
        )
        assert r.status_code == 400, f"expected 400 on <6 chars, got {r.status_code}: {r.text[:200]}"

    def test_empty_text_no_files_returns_400(self, admin_headers):
        r = requests.post(
            f"{API}/smart/idea",
            headers=admin_headers,
            data={"text": ""},
            timeout=30,
        )
        assert r.status_code == 400, f"expected 400 on empty, got {r.status_code}"


# ---------- End-to-end multipart flow with fixture lookup ----------
class TestSmartIdeaFixtureFlow:
    def test_created_tip_has_non_empty_match_time(self, admin_headers):
        """Send the exact spec hint. Expect either:
        - created:true with a tip whose match_time is a real DD/MM/YYYY HH:MM string, OR
        - created:false with reason=='no_fixture' (never a created tip without match_time)."""
        idea = "Real Madrid gegen Barcelona: beide Teams treffen und über 2.5 Tore"
        r = requests.post(
            f"{API}/smart/idea",
            headers=admin_headers,
            data={"text": idea},
            timeout=240,
        )
        assert r.status_code == 200, f"POST /smart/idea failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert data.get("ok") is True, f"missing ok:true: {data}"
        assert "created" in data and isinstance(data["created"], bool)

        if data["created"]:
            tip = data.get("tip")
            assert tip, f"created=true but no tip returned: {data}"
            for k in ("id", "home_team", "away_team", "market", "odds", "ai_rating", "ai_analysis", "source", "match_time"):
                assert k in tip, f"tip missing field '{k}': {list(tip.keys())}"
            # Key spec: match_time must be NON-EMPTY (real date & time)
            mt = (tip.get("match_time") or "").strip()
            assert mt, "match_time must be non-empty when tip is created (no post without date/time)"
            assert MATCH_TIME_RE.match(mt), f"match_time should look like DD/MM/YYYY HH:MM, got '{mt}'"
            assert tip["source"] == "smart"
            assert tip.get("smart_idea") is True
            assert tip["id"].startswith("smart-idea-")
            assert "_id" not in tip

            # Verify persistence via GET /api/tips?source=smart&status=pending
            time.sleep(1)
            r2 = requests.get(f"{API}/tips", params={"source": "smart", "status": "pending"}, timeout=30)
            assert r2.status_code == 200
            found = next((t for t in r2.json() if t.get("id") == tip["id"]), None)
            assert found, f"created tip {tip['id']} not in smart feed"
            assert (found.get("match_time") or "").strip() == mt, "persisted match_time must match returned"
            print(f"SMART CREATE OK — id={tip['id']} match_time='{mt}' market='{tip['market']}' odds={tip['odds']}")
        else:
            # Legit outcome: no fixture -> no tip created
            reason = data.get("reason")
            assert reason in ("no_fixture", "not_actionable"), f"unexpected reason: {reason}"
            print(f"SMART NOT CREATED (spec-compliant) — reason={reason}")

    def test_no_fixture_returns_created_false(self, admin_headers):
        """Use a nonsense fixture unlikely to be found by API-Football. Expect created:false with reason.
        (Either 'no_fixture' — teams parsed but no upcoming match — or 'not_actionable'.)
        Either way, NO tip should be created."""
        idea = "Zorkforfnia FC gegen Blurbville United treffen beide über 2.5 Tore heute Abend"
        # tips count BEFORE
        r0 = requests.get(f"{API}/tips", params={"source": "smart", "status": "pending"}, timeout=30)
        before_ids = {t.get("id") for t in (r0.json() if r0.status_code == 200 else [])}

        r = requests.post(
            f"{API}/smart/idea",
            headers=admin_headers,
            data={"text": idea},
            timeout=240,
        )
        assert r.status_code == 200, f"POST /smart/idea failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert data.get("ok") is True
        if data.get("created"):
            # If KI hallucinated real teams then API-Football found a fixture — still require match_time
            tip = data.get("tip") or {}
            mt = (tip.get("match_time") or "").strip()
            assert mt, "created tip must always carry a real match_time"
            print(f"KI mapped nonsense to real teams with fixture: {tip.get('id')} @ {mt}")
        else:
            assert data.get("reason") in ("no_fixture", "not_actionable"), f"reason must be no_fixture or not_actionable, got {data.get('reason')}"
            # Nothing new should appear in smart feed
            r1 = requests.get(f"{API}/tips", params={"source": "smart", "status": "pending"}, timeout=30)
            after_ids = {t.get("id") for t in (r1.json() if r1.status_code == 200 else [])}
            new = after_ids - before_ids
            assert not new, f"no tip should be created for reason={data.get('reason')}, but new ids appeared: {new}"
            print(f"SMART SKIP OK — reason={data.get('reason')} (no tip created)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
