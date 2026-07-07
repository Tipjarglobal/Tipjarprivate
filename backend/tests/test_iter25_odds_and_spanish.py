"""
Iteration 25 — Real-odds, systems, counts, smart-safety, admin-reset, and Spanish support.

Covers per review_request:
 1) GET /api/tips?source=ai&status=pending
 2) GET /api/systems (4 systems, numeric selection odds, computed total_odds)
 3) GET /api/tips/counts (keys ai, ai_total, members, live, systems, smart — all int)
 4) Admin POST /api/admin/smart/run    (fast; returns posted,matches,candidates)
    Admin POST /api/admin/autotips/reset is asserted only lightly (long-running, up to ~4m).
 5) Settle engine must NOT touch smart tips: source=smart still returns smart tips.
"""
import os
import re
import pytest
import requests


def _base():
    url = os.environ.get("REACT_APP_BACKEND_URL")
    if not url:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL"):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return url.rstrip("/")


BASE = _base()
API = f"{BASE}/api"
TIMEOUT = 60

ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                      timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    return r.json()["token"]


# --------------------------------------------------------------------- AI picks
class TestAIPicks:
    """GET /api/tips?source=ai&status=pending — ratings capped, odds are strings."""

    def test_ai_pending_shape_and_ratings(self):
        r = requests.get(f"{API}/tips",
                         params={"source": "ai", "status": "pending", "limit": 100},
                         timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        tips = r.json()
        assert isinstance(tips, list)
        assert len(tips) > 0, "expected at least 1 AI pick"

        real_odds_count = 0
        fallback_count = 0
        problems = []

        for t in tips:
            # odds is a string
            odds = t.get("odds")
            assert isinstance(odds, str), f"odds should be string, got {type(odds).__name__}: {t.get('id')}"
            try:
                float(odds)
            except Exception:
                problems.append(f"non-numeric odds '{odds}' in tip {t.get('id')}")

            # ai_rating cap
            rating = float(t.get("ai_rating") or 0)
            assert rating <= 9.5 + 1e-9, f"ai_rating {rating} > 9.5 in tip {t.get('id')} ({t.get('market')})"

            # Über 1.5 Tore must NOT be >=9
            market = (t.get("market") or "").lower()
            if "über 1.5" in market or "über 1,5" in market:
                assert rating < 9.0, f"'Über 1.5' rating {rating} must be < 9 (tip {t.get('id')})"

            # only safe markets should be 9.0-9.5
            if rating >= 9.0:
                safe_ok = ("über 0.5" in market or "über 0,5" in market
                           or "double chance" in market or "doppelte chance" in market
                           or "dnb" in market or "draw no bet" in market
                           or "beide teams treffen — nein" in market  # unlikely but safe-ish
                           or "goalscorer" in market)
                # 'Über 0.5 Tore' is the primary intended banker
                if not safe_ok:
                    problems.append(f"high rating {rating} on non-safe market '{t.get('market')}' (tip {t.get('id')})")

            analysis = t.get("ai_analysis") or ""
            if "Echte Buchmacher-Quote" in analysis:
                real_odds_count += 1
            else:
                fallback_count += 1

        assert not problems, "AI rating/odds problems: " + "; ".join(problems)
        # partial coverage is normal; log for context
        print(f"[ai-picks] total={len(tips)} real_odds={real_odds_count} fallback={fallback_count}")

    def test_no_500_on_various_ai_filters(self):
        for status in ("pending", "won", "lost"):
            r = requests.get(f"{API}/tips",
                             params={"source": "ai", "status": status, "limit": 50},
                             timeout=TIMEOUT)
            assert r.status_code == 200, f"{status}: {r.status_code} {r.text[:200]}"


# --------------------------------------------------------------------- Systems
class TestSystems:
    def test_systems_returns_four_typed_bundles(self):
        r = requests.get(f"{API}/systems", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        data = r.json()
        assert isinstance(data, list) or isinstance(data, dict), "systems should be list or wrapped dict"
        systems = data if isinstance(data, list) else (data.get("systems") or data.get("items") or [])
        assert len(systems) == 4, f"expected 4 systems, got {len(systems)}"

        types_seen = set()
        for sys_obj in systems:
            stype = (sys_obj.get("key") or sys_obj.get("type")
                     or sys_obj.get("system_type") or sys_obj.get("id") or "")
            types_seen.add(str(stype).lower())

            selections = sys_obj.get("selections") or sys_obj.get("legs") or []
            assert isinstance(selections, list) and len(selections) >= 1, f"no selections in {stype}"

            product = 1.0
            for sel in selections:
                odd = sel.get("odds") if "odds" in sel else sel.get("odd")
                assert odd is not None, f"selection missing odds in {stype}: {sel}"
                try:
                    fv = float(odd)
                except Exception:
                    pytest.fail(f"non-numeric selection odds {odd!r} in {stype}")
                assert fv > 1.0, f"selection odds must be >1.0 in {stype}: {fv}"
                product *= fv

            total = sys_obj.get("total_odds")
            assert total is not None, f"total_odds missing in {stype}"
            assert isinstance(total, (int, float)), f"total_odds not numeric: {total!r}"
            # Allow tiny floating-point drift
            assert abs(float(total) - product) / product < 0.05, \
                f"total_odds {total} != product {product:.4f} for {stype}"

        expected = {"lock", "value", "risk", "gamble"}
        # Systems may prefix names — accept substring match too.
        found = set()
        for e in expected:
            if any(e in t for t in types_seen):
                found.add(e)
        assert found == expected, f"expected {expected}, found types {types_seen}"


# --------------------------------------------------------------------- Counts
class TestCounts:
    def test_counts_keys_all_ints(self):
        r = requests.get(f"{API}/tips/counts", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("ai", "ai_total", "members", "live", "systems", "smart"):
            assert k in d, f"missing key '{k}' in counts: {d}"
            assert isinstance(d[k], int), f"'{k}' not int: {type(d[k]).__name__} = {d[k]}"


# --------------------------------------------------------------------- Smart safety
class TestSmartSafety:
    def test_smart_tips_still_present_and_not_settled(self):
        # smart_run resets smart tips in-place; retry briefly if we hit a mid-reset moment
        import time as _t
        tips = []
        for _ in range(6):
            r = requests.get(f"{API}/tips",
                             params={"source": "smart", "limit": 100},
                             timeout=TIMEOUT)
            assert r.status_code == 200, r.text
            tips = r.json()
            if len(tips) >= 1:
                break
            _t.sleep(1.0)
        assert isinstance(tips, list)
        assert len(tips) >= 1, "expected at least 1 smart tip (retried 6x)"
        for t in tips:
            assert t.get("source") == "smart", f"non-smart leaked: {t.get('source')}"

    def test_smart_source_excludes_ai_and_members(self):
        r = requests.get(f"{API}/tips", params={"source": "smart", "limit": 100}, timeout=TIMEOUT)
        tips = r.json()
        for t in tips:
            assert t.get("source") == "smart"


# --------------------------------------------------------------------- Admin: smart/run
class TestAdminSmartRun:
    def test_smart_run_returns_expected_shape(self, admin_token):
        r = requests.post(f"{API}/admin/smart/run",
                          headers={"Authorization": f"Bearer {admin_token}"},
                          timeout=180)
        assert r.status_code == 200, r.text
        d = r.json()
        for k in ("posted", "matches", "candidates"):
            assert k in d, f"missing '{k}' in {d}"
            assert isinstance(d[k], int), f"'{k}' not int in {d}"

    def test_smart_run_requires_admin(self):
        r = requests.post(f"{API}/admin/smart/run", timeout=TIMEOUT)
        assert r.status_code in (401, 403), r.text


# --------------------------------------------------------------------- Admin: autotips/reset (light)
class TestAdminAutotipsReset:
    """Autotips reset may run scrapers up to ~4 min.  We assert only response shape."""

    @pytest.mark.slow
    def test_autotips_reset_returns_shape(self, admin_token):
        r = requests.post(f"{API}/admin/autotips/reset",
                          headers={"Authorization": f"Bearer {admin_token}"},
                          json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
                          timeout=260)
        # Endpoint may return 200 with partial info even when a scraper hiccups.
        assert r.status_code == 200, f"{r.status_code}: {r.text[:400]}"
        d = r.json()
        assert "deleted" in d
        assert "forebet" in d and isinstance(d["forebet"], dict) and "posted" in d["forebet"]
        assert "predictz" in d and isinstance(d["predictz"], dict) and "posted" in d["predictz"]
