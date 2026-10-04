"""Iteration 45 — AI-tip correction endpoint, expert push, API reserve, regression.

Covers review request #1 (endpoint auth+behaviour), #6 (regression).
Code-only checks (#4 expert push, #5 API reserve) are asserted via file grep
in test_iter45_code_review.
"""
import io
import os
import pytest
import requests

BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
ADMIN_EMAIL = "admin@tipjar.com"
ADMIN_PASSWORD = "TipJarAdmin2026!"


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"admin login failed: {r.status_code} {r.text[:150]}")
    return r.json().get("token") or r.json().get("access_token")


@pytest.fixture(scope="module")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


# ── 1. correction endpoint requires auth ─────────────────────────────
def test_correct_requires_auth():
    r = requests.post(f"{BASE_URL}/api/tips/does-not-exist/correct",
                      files={"file": ("x.png", b"1234", "image/png")}, timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403 got {r.status_code}"


# ── 1c. non-AI tip cannot be corrected ───────────────────────────────
def _find_non_ai_tip(headers):
    r = requests.get(f"{BASE_URL}/api/tips", headers=headers, timeout=30)
    assert r.status_code == 200
    tips = r.json() if isinstance(r.json(), list) else r.json().get("tips", [])
    ai_sources = {"hq-auto", "hq-live", "hq-system", "smart", "hq-master"}
    for t in tips:
        if t.get("source") not in ai_sources and t.get("status") in ("pending", "live"):
            return t
    return None


def _find_ai_single_tip(headers):
    r = requests.get(f"{BASE_URL}/api/tips?source=ai", headers=headers, timeout=30)
    if r.status_code != 200:
        r = requests.get(f"{BASE_URL}/api/tips", headers=headers, timeout=30)
    tips = r.json() if isinstance(r.json(), list) else r.json().get("tips", [])
    for t in tips:
        if (t.get("source") == "hq-auto"
                and not t.get("is_parlay")
                and t.get("status") in ("pending", "live")):
            return t
    # fall back: any AI-sourced non-parlay
    for t in tips:
        if (t.get("source") in {"hq-auto", "hq-live", "hq-system", "smart", "hq-master"}
                and not t.get("is_parlay")
                and t.get("status") in ("pending", "live")):
            return t
    return None


def _make_png(text="Double Chance 1X Odds 2.10"):
    # Minimal PNG file, not readable by vision but exercises the multipart pipeline.
    # 1×1 transparent PNG:
    return (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
            b"\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xc0\xc0\x00"
            b"\x00\x00\x03\x00\x01)&\x8e\x91\x00\x00\x00\x00IEND\xaeB`\x82")


def test_correct_non_ai_tip_rejected(admin_headers):
    tip = _find_non_ai_tip(admin_headers)
    if not tip:
        pytest.skip("no non-AI open tip available")
    files = {"file": ("slip.png", _make_png(), "image/png")}
    r = requests.post(f"{BASE_URL}/api/tips/{tip['id']}/correct",
                      headers=admin_headers, files=files, timeout=60)
    assert r.status_code == 422, f"expected 422 got {r.status_code}: {r.text[:200]}"
    assert "Only AI tips" in r.text or "ai tips" in r.text.lower()


# ── 1b. correct an AI tip — stake never changes ──────────────────────
def test_correct_ai_tip_stake_unchanged(admin_headers):
    tip = _find_ai_single_tip(admin_headers)
    if not tip:
        pytest.skip("no AI single tip available")
    orig_stake = tip.get("stake")
    tip_id = tip["id"]

    files = {"file": ("slip.png", _make_png(), "image/png")}
    data = {"text": "Double Chance 1X  Odds 2.10"}
    r = requests.post(f"{BASE_URL}/api/tips/{tip_id}/correct",
                      headers=admin_headers, files=files, data=data, timeout=90)

    # Vision may fail on a 1x1 PNG → 422 is acceptable per spec.
    if r.status_code == 422:
        # verify stake still unchanged
        g = requests.get(f"{BASE_URL}/api/tips", headers=admin_headers, timeout=30).json()
        tips = g if isinstance(g, list) else g.get("tips", [])
        after = next((t for t in tips if t.get("id") == tip_id), None)
        assert after is not None
        assert after.get("stake") == orig_stake, "stake must not change on 422"
        pytest.skip("vision couldn't read 1x1 PNG (expected) — 422 with stake preserved")

    assert r.status_code == 200, f"unexpected {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body.get("ok") is True
    doc = body.get("tip") or {}
    assert doc.get("stake") == orig_stake, "STAKE MUST NEVER CHANGE"
    assert doc.get("corrected") is True
    assert doc.get("corrected_by")


# ── 6. regression ───────────────────────────────────────────────────
def test_regression_tips_list():
    r = requests.get(f"{BASE_URL}/api/tips", timeout=30)
    assert r.status_code == 200
    body = r.json()
    tips = body if isinstance(body, list) else body.get("tips", [])
    assert isinstance(tips, list)


def test_regression_hof_empty():
    r = requests.get(f"{BASE_URL}/api/wins/hall-of-fame", timeout=30)
    assert r.status_code == 200
    body = r.json()
    items = body if isinstance(body, list) else body.get("items") or body.get("wins") or []
    assert items == [] or len(items) == 0, f"HoF should be empty pre-Aug-1, got {items}"


def test_regression_no_russian_matches():
    r = requests.get(f"{BASE_URL}/api/tips", timeout=30)
    body = r.json()
    tips = body if isinstance(body, list) else body.get("tips", [])
    blob = str(tips).lower()
    for kw in ("russia", "russian", "rpl ", "premier league russia"):
        assert kw not in blob, f"unexpected russian keyword '{kw}' in tips feed"


# ── #4 + #5 code-review invariants ──────────────────────────────────
def test_code_expert_push_and_reserve():
    with open("/app/backend/background_tasks.py") as f:
        bg = f.read()
    with open("/app/backend/core.py") as f:
        core = f.read()

    # Expert branch
    assert '"icon": "/push-expert.png", "badge": "/push-expert.png", "tag": "tipjar-expert"' in bg
    assert '"sound": "expert"' in bg
    assert "🔮" in bg
    # Digest expert badge
    assert '"badge": "/push-expert.png" if is_expert' in bg
    # push-expert asset present
    assert os.path.isfile("/app/frontend/public/push-expert.png")

    # API reserve
    assert "_api_note_headers" in core
    assert "_api_reserve_locked" in core
    assert "API_EVENING_UTC_HOUR = 15" in core
    assert "API_DAY_RESERVE_FRAC = 0.5" in core
    # live_loop + member_live_loop back off
    assert bg.count("if _api_reserve_locked():") >= 2
