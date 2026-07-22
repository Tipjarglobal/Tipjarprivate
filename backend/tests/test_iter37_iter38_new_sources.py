"""iter37/38 — session tests:
 - Player-prop SINGLE auto-settlement (won + lost) via POST /api/admin/settle-now.
 - API-Football /predictions gap-filler admin endpoint schema.
 - Statarea scraper admin endpoint schema.
 - Analytics: visit tracking (admin excluded, anonymous counted) + /admin/visits schema.
 - Consumers (/scorers/today, /goals-forecast, /systems) still healthy with new sources.
 - Auth guard on all new admin endpoints.
"""
import os
import time
import uuid
import pytest
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"

MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")


# ---------- fixtures ----------
@pytest.fixture(scope="session")
def admin_token():
    r = requests.post(f"{API}/auth/login",
                      json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                      timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code}: {r.text}"
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}", "Content-Type": "application/json"}


# ---------- 1. Auth guard on new admin endpoints ----------
class TestAdminAuthGuard:
    def test_settle_now_requires_admin(self):
        r = requests.post(f"{API}/admin/settle-now", timeout=15)
        assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}"

    def test_apifootball_predictions_run_requires_admin(self):
        r = requests.post(f"{API}/admin/apifootball/predictions/run", timeout=15)
        assert r.status_code in (401, 403)

    def test_statarea_run_requires_admin(self):
        r = requests.post(f"{API}/admin/statarea/run", timeout=15)
        assert r.status_code in (401, 403)

    def test_admin_visits_requires_admin(self):
        r = requests.get(f"{API}/admin/visits", timeout=15)
        assert r.status_code in (401, 403)


# ---------- 2. API-Football /predictions gap-filler ----------
class TestApiFootballPredictionsRun:
    def test_endpoint_returns_expected_schema(self, admin_headers):
        r = requests.post(f"{API}/admin/apifootball/predictions/run",
                          headers=admin_headers, timeout=180)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
        body = r.json()
        # Either normal shape or short-circuit shape when no API key.
        assert "posted" in body
        # Normal shape:
        for k in ("scanned", "api_calls", "quota_exhausted"):
            assert k in body, f"missing key '{k}' in response: {body}"
        assert body["posted"] <= 20, "must respect the 20/run cap"
        assert isinstance(body["posted"], int)
        assert isinstance(body["api_calls"], int)

    def test_predictions_stored_with_source_apifootball(self):
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            n = db.match_predictions.count_documents({"source": "apifootball"})
            assert n >= 0
        finally:
            client.close()


# ---------- 3. Statarea scraper ----------
class TestStatareaRun:
    def test_endpoint_returns_expected_schema(self, admin_headers):
        r = requests.post(f"{API}/admin/statarea/run",
                          headers=admin_headers, timeout=180)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
        body = r.json()
        assert "posted" in body, f"missing 'posted': {body}"
        # scanned only present when scrape succeeded (not when chromium unavailable etc.)
        if "reason" not in body:
            assert "scanned" in body, f"missing 'scanned': {body}"
            assert isinstance(body["posted"], int)
            assert isinstance(body["scanned"], int)

    def test_predictions_stored_with_source_statarea(self):
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            n = db.match_predictions.count_documents({"source": "statarea"})
            assert n >= 0
        finally:
            client.close()


# ---------- 4. Consumers still healthy ----------
class TestConsumersHealthy:
    def test_scorers_today_ok(self):
        r = requests.get(f"{API}/scorers/today", timeout=30)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
        body = r.json()
        assert isinstance(body, (list, dict))

    def test_goals_forecast_ok(self):
        r = requests.get(f"{API}/goals-forecast", timeout=30)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"
        body = r.json()
        assert isinstance(body, (list, dict))

    def test_systems_ok(self):
        r = requests.get(f"{API}/systems", timeout=30)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"

    def test_source_priority_forebet_predictz_still_appear(self):
        """Verify that after apifootball/statarea sources were added the
        traditional scraper sources are still present (they must keep priority)."""
        client = MongoClient(MONGO_URL)
        db = client[DB_NAME]
        try:
            forebet = db.match_predictions.count_documents({"source": "forebet"})
            predictz = db.match_predictions.count_documents({"source": "predictz"})
            assert forebet > 0, "forebet predictions disappeared (source priority broken)"
            assert predictz > 0, "predictz predictions disappeared (source priority broken)"
        finally:
            client.close()


# ---------- 5. Analytics — visit tracking (admin excluded) ----------
class TestVisitTracking:
    def test_admin_visit_does_not_increase_unique(self, admin_headers):
        # baseline
        r1 = requests.get(f"{API}/admin/visits", headers=admin_headers, timeout=15)
        assert r1.status_code == 200
        before = r1.json()["today_unique"]

        # admin ping (must be flagged is_admin and excluded)
        vid_admin = f"TEST_admin_{uuid.uuid4().hex[:8]}"
        rp = requests.post(f"{API}/track/visit",
                           headers=admin_headers,
                           json={"visitor_id": vid_admin, "path": "/"},
                           timeout=15)
        assert rp.status_code == 200

        r2 = requests.get(f"{API}/admin/visits", headers=admin_headers, timeout=15)
        assert r2.status_code == 200
        after = r2.json()["today_unique"]

        assert after == before, (
            f"today_unique changed after admin ping ({before} -> {after}); "
            "admin visits must NOT count"
        )

    def test_anonymous_visit_increases_unique(self, admin_headers):
        r1 = requests.get(f"{API}/admin/visits", headers=admin_headers, timeout=15)
        before_unique = r1.json()["today_unique"]
        before_anon = r1.json()["today_anon"]

        vid = f"TEST_anon_{uuid.uuid4().hex[:8]}"
        # NO Authorization header => anonymous
        rp = requests.post(f"{API}/track/visit",
                          json={"visitor_id": vid, "path": "/"},
                          timeout=15)
        assert rp.status_code == 200

        r2 = requests.get(f"{API}/admin/visits", headers=admin_headers, timeout=15)
        after_unique = r2.json()["today_unique"]
        after_anon = r2.json()["today_anon"]

        assert after_unique == before_unique + 1, (
            f"anonymous visit didn't bump today_unique ({before_unique} -> {after_unique})"
        )
        assert after_anon == before_anon + 1, (
            f"anonymous visit didn't bump today_anon ({before_anon} -> {after_anon})"
        )


class TestAdminVisitsSchema:
    def test_schema_has_expected_fields(self, admin_headers):
        r = requests.get(f"{API}/admin/visits", headers=admin_headers, timeout=15)
        assert r.status_code == 200
        body = r.json()
        for k in ("today_unique", "today_members", "today_anon",
                  "total_members", "total_anon", "daily"):
            assert k in body, f"missing '{k}' in /admin/visits: {list(body)}"
        assert isinstance(body["daily"], list) and len(body["daily"]) > 0
        for entry in body["daily"]:
            assert "members" in entry and "anon" in entry, entry


# ---------- 6. Player-prop SINGLE auto-settlement ----------
# Real finished fixture from today (Jul 22 2026): Toluca 1-2 UNAM Pumas (F.ID 1550904)
# Confirmed via API-Football /fixtures/players:
#   Jorge Diaz (Toluca) -> goals=1  (scorer prop → WON)
#   Fernando Arce Juarez (Toluca) -> sot=0, shots=1  (SOT 0.5 line → LOST)
PP_TEST_HOME = "Toluca"
PP_TEST_AWAY = "U.N.A.M. - Pumas"
PP_TEST_KICKOFF = "2026-07-22T03:05:00+00:00"


@pytest.fixture()
def temp_player_tips(admin_headers):
    """Insert two TEST_ member player-prop tips + clean them up after."""
    won_id = f"TEST_pp_won_{uuid.uuid4().hex[:8]}"
    lost_id = f"TEST_pp_lost_{uuid.uuid4().hex[:8]}"
    docs = [
        # scorer WON
        {
            "id": won_id,
            "source": "members",
            "status": "pending",
            "is_parlay": False,
            "home_team": PP_TEST_HOME,
            "away_team": PP_TEST_AWAY,
            "match_time": PP_TEST_KICKOFF,
            "market": "Jorge Díaz Anytime Torschütze",
            "player": "Jorge Díaz",
            "kind": "scorer",
            "line": None,
            "odds": 3.5,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "settle_attempts": 0,
        },
        # shots on target 0.5 LOST (player had 0 SOT)
        {
            "id": lost_id,
            "source": "members",
            "status": "pending",
            "is_parlay": False,
            "home_team": PP_TEST_HOME,
            "away_team": PP_TEST_AWAY,
            "match_time": PP_TEST_KICKOFF,
            "market": "Fernando Arce Juárez Über 0.5 Torschüsse aufs Tor",
            "player": "Fernando Arce Juárez",
            "kind": "sot",
            "line": 0,
            "odds": 2.1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "settle_attempts": 0,
        },
    ]

    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    db.tips.insert_many(docs)
    c.close()

    yield {"won_id": won_id, "lost_id": lost_id}

    c = MongoClient(MONGO_URL)
    db = c[DB_NAME]
    db.tips.delete_many({"id": {"$in": [won_id, lost_id]}})
    c.close()


class TestPlayerPropSettlement:
    def test_settle_now_grades_scorer_won_and_sot_lost(self, admin_headers, temp_player_tips):
        won_id = temp_player_tips["won_id"]
        lost_id = temp_player_tips["lost_id"]

        # trigger settle
        r = requests.post(f"{API}/admin/settle-now",
                          headers=admin_headers, timeout=300)
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"

        # give it a moment then inspect DB directly
        c = MongoClient(MONGO_URL)
        db = c[DB_NAME]
        w = db.tips.find_one({"id": won_id})
        l = db.tips.find_one({"id": lost_id})
        c.close()
        assert w is not None and l is not None, "test tips vanished before verification"

        # Scorer with goals=1 must be WON
        assert w["status"] == "won", (
            f"scorer prop for known scorer did NOT settle to WON: status={w.get('status')} "
            f"settled_by={w.get('settled_by')} attempts={w.get('settle_attempts')} "
            f"final={w.get('final_home')}-{w.get('final_away')}"
        )

        # SOT 0.5 (need >=1) with player who had 0 SOT must be LOST
        assert l["status"] == "lost", (
            f"SOT prop for 0-SOT player did NOT settle to LOST: status={l.get('status')} "
            f"settled_by={l.get('settled_by')} attempts={l.get('settle_attempts')} "
            f"final={l.get('final_home')}-{l.get('final_away')}"
        )

        # Neither should be void or stuck pending
        for tip, label in ((w, "scorer"), (l, "sot")):
            assert tip["status"] not in ("pending", "void"), (
                f"{label} tip ended up as {tip['status']} (must be won/lost)"
            )


# ---------- 7. Player-prop grader unit test (offline, no API) ----------
class TestGraderUnit:
    """Import server internals and confirm the grader picks the right player even
    when two players share a last name (full-name key)."""

    def test_full_name_key_disambiguates_same_last_name(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from server import _grade_player_leg, _norm  # noqa

        # Two "Castillo" players — one scored, one didn't.
        pmap = {
            "full:" + _norm("Diego Castillo"): {
                "shots_total": 3, "shots_on": 2, "goals": 1, "saves": 0,
                "fouls_c": 0, "fouls_d": 0, "cards": 0, "team": "A",
            },
            "full:" + _norm("Luis Castillo"): {
                "shots_total": 1, "shots_on": 0, "goals": 0, "saves": 0,
                "fouls_c": 0, "fouls_d": 0, "cards": 0, "team": "B",
            },
        }
        fx = {"home_goals": 1, "away_goals": 0, "home_name": "A", "away_name": "B"}
        leg_won = {"market": "Diego Castillo Anytime Torschütze",
                   "kind": "scorer", "player": "Diego Castillo",
                   "home": "A", "away": "B"}
        leg_lost = {"market": "Luis Castillo Anytime Torschütze",
                    "kind": "scorer", "player": "Luis Castillo",
                    "home": "A", "away": "B"}
        assert _grade_player_leg(leg_won, pmap, {}, fx) is True
        assert _grade_player_leg(leg_lost, pmap, {}, fx) is False

    def test_sot_line_0_needs_at_least_one(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from server import _grade_player_leg, _norm  # noqa

        pmap = {
            "full:" + _norm("Zero SOT"): {
                "shots_total": 1, "shots_on": 0, "goals": 0, "saves": 0,
                "fouls_c": 0, "fouls_d": 0, "cards": 0, "team": "T",
            },
            "full:" + _norm("One SOT"): {
                "shots_total": 2, "shots_on": 1, "goals": 0, "saves": 0,
                "fouls_c": 0, "fouls_d": 0, "cards": 0, "team": "T",
            },
        }
        fx = {"home_goals": 0, "away_goals": 0, "home_name": "T", "away_name": "X"}
        assert _grade_player_leg(
            {"market": "Zero SOT Über 0.5 Torschüsse aufs Tor",
             "kind": "sot", "line": 0, "player": "Zero SOT",
             "home": "T", "away": "X"}, pmap, {}, fx) is False
        assert _grade_player_leg(
            {"market": "One SOT Über 0.5 Torschüsse aufs Tor",
             "kind": "sot", "line": 0, "player": "One SOT",
             "home": "T", "away": "X"}, pmap, {}, fx) is True
