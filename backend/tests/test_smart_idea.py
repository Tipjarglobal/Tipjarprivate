"""
Tests for the NEW Smart Bets IDEA feature (SmartLab chatbox).
- POST /api/smart/idea (auth required)
- Rejects too-short text
- Real KI-generation flow produces a tip in the /api/tips?source=smart feed
- GET /api/admin/smart/ideas lists ideas (admin only)
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-credit-saver.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"


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
class TestSmartIdeaAuth:
    def test_smart_idea_unauth_rejected(self):
        r = requests.post(f"{API}/smart/idea", json={"text": "Real Madrid gegen Barcelona viele Tore, beide treffen."}, timeout=30)
        assert r.status_code in (401, 403), f"unauth call must be 401/403, got {r.status_code}: {r.text[:200]}"


# ---------- Validation ----------
class TestSmartIdeaValidation:
    def test_smart_idea_too_short(self, admin_headers):
        r = requests.post(f"{API}/smart/idea", headers=admin_headers, json={"text": "hi"}, timeout=30)
        assert r.status_code == 400, f"expected 400 on <6 chars, got {r.status_code}: {r.text[:200]}"
        assert "kurz" in r.text.lower() or "short" in r.text.lower() or "detail" in r.text.lower()

    def test_smart_idea_empty(self, admin_headers):
        r = requests.post(f"{API}/smart/idea", headers=admin_headers, json={"text": ""}, timeout=30)
        assert r.status_code == 400, f"expected 400 on empty text, got {r.status_code}"


# ---------- End-to-end KI flow ----------
class TestSmartIdeaFlow:
    def test_submit_idea_creates_smart_tip(self, admin_headers):
        idea = "Ich denke Real Madrid gegen Barcelona gibt viele Tore, beide Teams treffen und Vinicius trifft auch."
        r = requests.post(f"{API}/smart/idea", headers=admin_headers, json={"text": idea}, timeout=180)
        assert r.status_code == 200, f"idea POST failed: {r.status_code} {r.text[:400]}"
        data = r.json()
        assert data.get("ok") is True, f"missing ok:true: {data}"
        assert "created" in data, f"missing 'created' key: {data}"
        assert isinstance(data["created"], bool)

        if data["created"]:
            # Response contract: includes tip object
            tip = data.get("tip")
            assert tip, f"created=true but no tip returned: {data}"
            # Verify required fields on returned tip
            for k in ("id", "home_team", "away_team", "market", "odds", "ai_rating", "ai_analysis", "source"):
                assert k in tip, f"tip missing field '{k}': {list(tip.keys())}"
            assert tip["source"] == "smart", f"created tip source must be 'smart', got {tip['source']}"
            assert tip.get("smart_idea") is True, f"tip must have smart_idea=True, got {tip.get('smart_idea')}"
            assert tip["id"].startswith("smart-idea-"), f"tip id must start with 'smart-idea-', got {tip['id']}"
            assert "_id" not in tip, "_id (Mongo ObjectId) must be stripped from response"
            print(f"created smart tip: {tip['id']} — {tip['home_team']} vs {tip['away_team']} | {tip['market']} @ {tip['odds']}")

            # Verify persistence: it must appear in GET /api/tips?source=smart
            time.sleep(1)
            r2 = requests.get(f"{API}/tips", params={"source": "smart", "status": "pending"}, timeout=30)
            assert r2.status_code == 200
            all_smart = r2.json()
            ids = [t.get("id") for t in all_smart]
            assert tip["id"] in ids, f"created tip {tip['id']} not found in smart feed (got {len(ids)} tips)"
        else:
            # Not actionable — that's a valid outcome; KI decided the hint was too vague
            print(f"idea marked not_actionable (created=False): {data}")


# ---------- Admin listing ----------
class TestAdminSmartIdeas:
    def test_admin_list_smart_ideas(self, admin_headers):
        r = requests.get(f"{API}/admin/smart/ideas", headers=admin_headers, timeout=30)
        assert r.status_code == 200, f"admin list failed: {r.status_code} {r.text[:200]}"
        docs = r.json()
        assert isinstance(docs, list), f"expected list, got {type(docs)}"
        if docs:
            d = docs[0]
            for k in ("id", "user_id", "text", "status", "created_at"):
                assert k in d, f"missing field '{k}' in idea doc: {list(d.keys())}"
            assert "_id" not in d, "_id must be stripped from admin list"
        print(f"admin smart/ideas returned {len(docs)} entries")

    def test_admin_list_smart_ideas_unauth(self):
        r = requests.get(f"{API}/admin/smart/ideas", timeout=30)
        assert r.status_code in (401, 403), f"unauth admin list must be 401/403, got {r.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
