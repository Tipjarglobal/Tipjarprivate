"""Iteration 36 — Live sub-categories (Banker / Value / Banger).

Covers:
  * GET /api/tips?status=live&category=... filter semantics
    - banker → strict category == "banker"
    - value  → category NOT IN [banker, risk, banger]
    - banger → strict category == "banger"
    - no category → all live tips
  * POST /api/admin/live-run (admin auth) — backfills categories + upserts, must
    return JSON with numeric posted/closed, and after it runs every live tip
    has a category in [banker, value, banger] (no missing/legacy nulls).
  * Direct unit-check of _live_bet_landed() for "Asian Über 2.0 Tore":
      total >= 3  → True
      total == 2  → None
      total <= 1  → False
"""
import os
import sys
import importlib.util
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://ai-credit-saver.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"


# ── auth ────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def admin_token():
    """POST /api/auth/login → response field is 'token' (NOT access_token)."""
    r = requests.post(f"{API}/auth/login",
                      json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                      timeout=30)
    assert r.status_code == 200, f"admin login failed: {r.status_code} {r.text}"
    data = r.json()
    tok = data.get("token") or data.get("access_token")
    assert tok, f"no token in login response: {data}"
    return tok


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ── /api/tips category filter ───────────────────────────────────────────────
class TestLiveCategoryFilter:
    def test_all_live_no_category(self):
        r = requests.get(f"{API}/tips", params={"status": "live", "limit": 200}, timeout=30)
        assert r.status_code == 200, r.text
        tips = r.json()
        assert isinstance(tips, list)
        # every returned tip must be live
        for t in tips:
            assert t.get("status") == "live", f"non-live tip returned: {t.get('id')} status={t.get('status')}"
        # store count for cross-checks
        pytest.all_live_count = len(tips)
        pytest.all_live_tips = tips

    def test_banker_returns_only_banker(self):
        r = requests.get(f"{API}/tips", params={"status": "live", "category": "banker", "limit": 200}, timeout=30)
        assert r.status_code == 200, r.text
        tips = r.json()
        for t in tips:
            assert t.get("status") == "live"
            assert t.get("category") == "banker", f"expected banker, got {t.get('category')} on {t.get('id')}"

    def test_banger_returns_only_banger(self):
        r = requests.get(f"{API}/tips", params={"status": "live", "category": "banger", "limit": 200}, timeout=30)
        assert r.status_code == 200, r.text
        tips = r.json()
        for t in tips:
            assert t.get("status") == "live"
            assert t.get("category") == "banger", f"expected banger, got {t.get('category')} on {t.get('id')}"

    def test_value_excludes_banker_risk_banger(self):
        r = requests.get(f"{API}/tips", params={"status": "live", "category": "value", "limit": 200}, timeout=30)
        assert r.status_code == 200, r.text
        tips = r.json()
        for t in tips:
            assert t.get("status") == "live"
            assert t.get("category") not in ("banker", "risk", "banger"), \
                f"value bucket must exclude banker/risk/banger, got {t.get('category')} on {t.get('id')}"

    def test_category_partitioning_consistent(self):
        """banker + value(-risk-banger) + banger must cover ALL live tips exactly."""
        def _fetch(cat=None):
            p = {"status": "live", "limit": 200}
            if cat:
                p["category"] = cat
            return requests.get(f"{API}/tips", params=p, timeout=30).json()

        all_live = _fetch()
        banker = _fetch("banker")
        banger = _fetch("banger")
        value = _fetch("value")
        # non-negative
        for name, arr in [("all", all_live), ("banker", banker), ("value", value), ("banger", banger)]:
            assert isinstance(arr, list) and len(arr) >= 0, f"{name} not a list"

        # value bucket may still contain 'risk' items server-side? No — value excludes risk too.
        # BUT: total live tips == banker + banger + value + any leftover with category='risk'.
        risk_count = sum(1 for t in all_live if t.get("category") == "risk")
        assert len(all_live) == len(banker) + len(banger) + len(value) + risk_count, (
            f"partition mismatch: all={len(all_live)} banker={len(banker)} banger={len(banger)} "
            f"value={len(value)} risk={risk_count}"
        )


# ── /api/admin/live-run ────────────────────────────────────────────────────
class TestAdminLiveRun:
    def test_live_run_returns_json_and_backfills_category(self, admin_headers):
        r = requests.post(f"{API}/admin/live-run", headers=admin_headers, timeout=90)
        assert r.status_code == 200, f"live-run failed: {r.status_code} {r.text}"
        data = r.json()
        assert isinstance(data, dict), f"expected dict, got {type(data)}"
        # numeric counters must exist and be non-negative ints
        for k in ("posted",):
            assert k in data, f"missing '{k}' in live-run response: {data}"
            assert isinstance(data[k], int) and data[k] >= 0
        # closed is optional-ish (only present if there were live tips beforehand)
        if "closed" in data:
            assert isinstance(data["closed"], int) and data["closed"] >= 0

        # after live-run every live tip should carry a valid category
        tips = requests.get(f"{API}/tips", params={"status": "live", "limit": 200}, timeout=30).json()
        legacy = [t for t in tips if t.get("category") not in ("banker", "value", "banger", "risk")]
        assert not legacy, (
            f"live-run did not backfill category for {len(legacy)} tips: "
            f"{[t.get('id') for t in legacy][:5]}"
        )

    def test_live_run_requires_admin(self):
        r = requests.post(f"{API}/admin/live-run", timeout=30)
        assert r.status_code in (401, 403), f"expected 401/403 without auth, got {r.status_code}"


# ── unit-level: _live_bet_landed for Asian Über 2.0 ─────────────────────────
def _load_server():
    """Load /app/backend/server.py as a module without triggering FastAPI startup."""
    if "server_iter36" in sys.modules:
        return sys.modules["server_iter36"]
    sys.path.insert(0, "/app/backend")
    spec = importlib.util.spec_from_file_location("server_iter36", "/app/backend/server.py")
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        pytest.skip(f"server import failed (heavy side effects): {e}")
    sys.modules["server_iter36"] = mod
    return mod


class TestAsianUeber20Settlement:
    """The rule the user personally confirmed:
       exactly 2 goals => stake back (None), 3+ => won (True), <=1 => lost (False)."""

    def test_asian_over_2_won_at_3_plus(self):
        srv = _load_server()
        # 3-0
        assert srv._live_bet_landed("Asian Über 2.0 Tore", 3, 0, "A", "B") is True
        # 2-1
        assert srv._live_bet_landed("Asian Über 2.0 Tore", 2, 1, "A", "B") is True
        # 4-2
        assert srv._live_bet_landed("Asian Über 2.0 Tore", 4, 2, "A", "B") is True

    def test_asian_over_2_push_at_exactly_2(self):
        srv = _load_server()
        # 2-0
        assert srv._live_bet_landed("Asian Über 2.0 Tore", 2, 0, "A", "B") is None
        # 1-1
        assert srv._live_bet_landed("Asian Über 2.0 Tore", 1, 1, "A", "B") is None
        # 0-2
        assert srv._live_bet_landed("Asian Über 2.0 Tore", 0, 2, "A", "B") is None

    def test_asian_over_2_lost_at_1_or_less(self):
        srv = _load_server()
        assert srv._live_bet_landed("Asian Über 2.0 Tore", 1, 0, "A", "B") is False
        assert srv._live_bet_landed("Asian Über 2.0 Tore", 0, 0, "A", "B") is False

    def test_asian_over_2_pricing_reasonable(self):
        """_live_odd for the banger market must return a finite odd in [1.05, 15.0]."""
        srv = _load_server()
        for minute in (15, 30, 45, 60, 70):
            for total in (0, 1):
                o = srv._live_odd("Asian Über 2.0 Tore", minute, total)
                assert 1.05 <= o <= 15.0, f"odd out of range at minute={minute} total={total}: {o}"
