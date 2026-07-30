"""Iteration 48: Anti-contradiction guard for GIFT tips (owner rule).
Tests server._conflicts_with_gift + _gift_under_lean using stances built the
same way as server._gift_stance_map, plus endpoint health with a live gift.
"""
import os
import sys
import pytest
import requests

sys.path.insert(0, "/app/backend")
from server import (  # noqa: E402
    _conflicts_with_gift,
    _gift_under_lean,
    _parse_over_under,
    _market_team_side,
    _team_core,
)

def _load_backend_url() -> str:
    v = os.environ.get("REACT_APP_BACKEND_URL", "").strip()
    if v:
        return v.rstrip("/")
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().rstrip("/")
    except OSError:
        pass
    return ""


BASE_URL = _load_backend_url()


def _mkstance(home: str, away: str, gift_market: str) -> dict:
    """Build a stance dict for one gift, mirroring _gift_stance_map()."""
    st = {"team_over": set(), "team_under": set(), "match_over": [], "match_under": []}
    pu = _parse_over_under(gift_market)
    assert pu, f"gift market must be over/under: {gift_market}"
    direction, line = pu
    side = _market_team_side(gift_market, home, away)
    team = home if side == "home" else away if side == "away" else None
    if team:
        (st["team_over"] if direction == "over" else st["team_under"]).add(_team_core(team))
    else:
        (st["match_over"] if direction == "over" else st["match_under"]).append(line)
    return st


# ---- Anti-contradiction predicate ----
class TestConflictsWithGift:
    def test_team_under_blocks_team_scores(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Qarabag Unter 2.5 Tore")
        assert _conflicts_with_gift("Qarabag trifft", home, away, st) is True

    def test_team_under_blocks_team_over(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Qarabag Unter 2.5 Tore")
        assert _conflicts_with_gift("Qarabag Über 2.5 Tore", home, away, st) is True

    def test_team_under_blocks_big_match_over(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Qarabag Unter 2.5 Tore")
        assert _conflicts_with_gift("Über 4.5 Tore", home, away, st) is True

    def test_team_under_allows_other_team_scores(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Qarabag Unter 2.5 Tore")
        assert _conflicts_with_gift("Ludogorets trifft", home, away, st) is False

    def test_team_under_allows_small_match_over(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Qarabag Unter 2.5 Tore")
        assert _conflicts_with_gift("Über 2.5 Tore", home, away, st) is False

    def test_match_under_blocks_match_over(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Unter 2.5 Tore")
        assert _conflicts_with_gift("Über 2.5 Tore", home, away, st) is True

    def test_match_under_blocks_big_match_over(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Unter 2.5 Tore")
        assert _conflicts_with_gift("Über 4.5 Tore", home, away, st) is True

    def test_match_under_blocks_team_trifft(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Unter 2.5 Tore")
        assert _conflicts_with_gift("Qarabag trifft", home, away, st) is True

    def test_match_under_allows_higher_under(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Unter 2.5 Tore")
        assert _conflicts_with_gift("Unter 3.5 Tore", home, away, st) is False

    def test_team_over_asian_blocks_trifft_nicht(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Qarabag Asian Über 1.0 Tore")
        assert _conflicts_with_gift("Qarabag trifft nicht", home, away, st) is True

    def test_team_over_allows_team_over_2_5(self):
        home, away = "Qarabag", "Ludogorets"
        st = _mkstance(home, away, "Qarabag Asian Über 1.0 Tore")
        assert _conflicts_with_gift("Qarabag Über 2.5 Tore", home, away, st) is False


# ---- Under-lean helper ----
class TestGiftUnderLean:
    def test_team_under_is_under_lean(self):
        st = _mkstance("Qarabag", "Ludogorets", "Qarabag Unter 2.5 Tore")
        assert _gift_under_lean(st) is True

    def test_match_under_is_under_lean(self):
        st = _mkstance("Qarabag", "Ludogorets", "Unter 2.5 Tore")
        assert _gift_under_lean(st) is True

    def test_team_over_is_not_under_lean(self):
        st = _mkstance("Qarabag", "Ludogorets", "Qarabag Asian Über 1.0 Tore")
        assert _gift_under_lean(st) is False

    def test_empty_is_not_under_lean(self):
        assert _gift_under_lean({}) is False


# ---- Endpoint health with an active gift ----
ENDPOINTS = [
    "/api/goal-thirst",
    "/api/ht-goal-forecast",
    "/api/tips?category=mental",
    "/api/tips?source=master&mcat=slips",
    "/api/tips?source=master&mcat=avatar",
    "/api/master/avatar",
    "/api/tips?source=ai",
]


@pytest.mark.parametrize("path", ENDPOINTS)
def test_endpoint_health(path):
    assert BASE_URL, "REACT_APP_BACKEND_URL missing"
    r = requests.get(BASE_URL + path, timeout=60)
    assert r.status_code == 200, f"{path} → {r.status_code}: {r.text[:200]}"
