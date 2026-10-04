"""Iter44 critical-flow backend tests: Russia block, HoF rules, push threshold,
AI translation (en/el/fr), Master easy/medium disjoint matches."""
import os
import re
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL must be set"

RUSSIA_KEYWORDS = [
    "russia", "russian", "zenit", "cska moscow", "spartak moscow",
    "lokomotiv moscow", "dynamo moscow", "krasnodar", "fc rostov",
    "baltika", "akhmat", "rubin kazan", "orenburg", "fakel", "pari nn",
    "nizhny novgorod", "khimki", "fc ural", "fc sochi", "akron togliatti",
    "makhachkala",
]


def _contains_russia(text: str) -> str | None:
    if not text:
        return None
    t = text.lower()
    for kw in RUSSIA_KEYWORDS:
        if kw in t:
            return kw
    return None


def _scan_tip(tip: dict) -> list[str]:
    hits = []
    for f in ("home_team", "away_team", "league"):
        hit = _contains_russia(str(tip.get(f, "")))
        if hit:
            hits.append(f"{f}='{tip.get(f)}' matched '{hit}'")
    for leg in tip.get("legs", []) or []:
        for f in ("match", "league", "home_team", "away_team"):
            hit = _contains_russia(str(leg.get(f, "")))
            if hit:
                hits.append(f"leg.{f}='{leg.get(f)}' matched '{hit}'")
    return hits


# ---------- 1) Russia block ----------
class TestRussiaBlock:
    def _fetch(self, params):
        r = requests.get(f"{BASE_URL}/api/tips", params=params, timeout=30)
        assert r.status_code == 200, f"{params} -> {r.status_code}: {r.text[:200]}"
        data = r.json()
        if isinstance(data, dict):
            return data.get("tips") or data.get("items") or []
        return data or []

    def test_no_russia_in_ai(self):
        tips = self._fetch({"source": "ai"})
        problems = []
        for t in tips:
            hits = _scan_tip(t)
            if hits:
                problems.append({"id": t.get("id"), "hits": hits})
        assert not problems, f"Russia leaks in AI tips: {problems[:3]}"
        print(f"AI tips scanned: {len(tips)}, clean")

    def test_no_russia_in_members(self):
        tips = self._fetch({"source": "members"})
        problems = [(t.get("id"), _scan_tip(t)) for t in tips if _scan_tip(t)]
        assert not problems, f"Russia leaks in members: {problems[:3]}"
        print(f"members tips scanned: {len(tips)}")

    def test_no_russia_in_live(self):
        tips = self._fetch({"source": "live"})
        problems = [(t.get("id"), _scan_tip(t)) for t in tips if _scan_tip(t)]
        assert not problems, f"Russia leaks in live: {problems[:3]}"
        print(f"live tips scanned: {len(tips)}")

    def test_no_russia_in_systems(self):
        tips = self._fetch({"source": "systems"})
        problems = [(t.get("id"), _scan_tip(t)) for t in tips if _scan_tip(t)]
        assert not problems, f"Russia leaks in systems: {problems[:3]}"
        print(f"systems tips scanned: {len(tips)}")

    def test_no_russia_status_live(self):
        tips = self._fetch({"status": "live"})
        problems = [(t.get("id"), _scan_tip(t)) for t in tips if _scan_tip(t)]
        assert not problems, f"Russia leaks in status=live: {problems[:3]}"
        print(f"status=live scanned: {len(tips)}")


# ---------- 2) Hall of Fame rules ----------
class TestHallOfFame:
    def test_hof_empty_before_aug1(self):
        r = requests.get(f"{BASE_URL}/api/wins/hall-of-fame", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        entries = data if isinstance(data, list) else (data.get("entries") or data.get("items") or [])
        # Should be empty because server date is 2026-07-29 and HOF opens 2026-08-01
        assert entries == [] or len(entries) == 0, f"HoF should be empty before 2026-08-01, got {len(entries)} entries: {entries[:2]}"
        print(f"HoF entries: {len(entries)} (empty as expected)")

    def test_hof_structural_rules(self):
        """Even if non-empty, must satisfy: legs>=2, created_at>=2026-08-01,
        house systems total_odds>=20, non-house total_odds>=3."""
        r = requests.get(f"{BASE_URL}/api/wins/hall-of-fame", timeout=30)
        data = r.json()
        entries = data if isinstance(data, list) else (data.get("entries") or data.get("items") or [])
        violations = []
        for e in entries:
            legs_count = e.get("legs_count") or len(e.get("legs") or [])
            if legs_count < 2:
                violations.append(f"single pick: {e.get('id')} legs={legs_count}")
            ca = str(e.get("created_at", ""))
            if ca and ca < "2026-08-01":
                violations.append(f"pre-Aug: {e.get('id')} created_at={ca}")
            odds = float(e.get("total_odds") or 0)
            src = str(e.get("source") or "")
            author = str(e.get("author") or "").lower()
            is_house = any(x in author for x in ("tipjarhq", "tipjarmaster", "tipjar hq", "tipjar master"))
            if is_house and odds < 20.0:
                violations.append(f"house < 20: {e.get('id')} odds={odds}")
            if (src == "system" or src == "systems") and not is_house and odds < 3.0:
                violations.append(f"non-house sys < 3: {e.get('id')} odds={odds}")
        assert not violations, f"HoF structural violations: {violations[:5]}"


# ---------- 3) Push threshold ----------
class TestPushMinStars:
    ENDPOINT_URL = "https://example.com/push/endpoint/iter44-test"

    def test_push_subscribe_accepts_min_stars(self):
        payload = {
            "endpoint": self.ENDPOINT_URL,
            "keys": {"p256dh": "BFAKE_p256dh_key", "auth": "FAKE_auth"},
            "areas": {"ai": True},
            "min_stars": 9,
        }
        r = requests.post(f"{BASE_URL}/api/push/subscribe", json=payload, timeout=15)
        assert r.status_code == 200, f"{r.status_code}: {r.text}"
        data = r.json()
        assert data.get("ok") is True, data

    def test_push_preferences_accepts_min_stars(self):
        payload = {
            "endpoint": self.ENDPOINT_URL,
            "areas": {"ai": True},
            "min_stars": 9,
        }
        r = requests.post(f"{BASE_URL}/api/push/preferences", json=payload, timeout=15)
        assert r.status_code == 200, f"{r.status_code}: {r.text}"
        data = r.json()
        assert data.get("ok") is True, data


# ---------- 4) AI analysis translation ----------
class TestTranslateAnalysis:
    URL = None

    def setup_method(self):
        self.URL = f"{BASE_URL}/api/i18n/translate"

    def test_en_translation(self):
        german_text = "Beide Teams treffen wahrscheinlich, da beide Offensiven stark sind."
        r = requests.post(f"{BASE_URL}/api/i18n/translate", json={"lang": "en", "texts": [german_text]}, timeout=60)
        assert r.status_code == 200, r.text
        m = r.json().get("map", {})
        assert german_text in m, m
        v = m[german_text]
        assert v and v != german_text, f"not translated: {v}"
        # Ensure it doesn't contain the German unique word 'Beide' as first word
        assert "beide" not in v.lower().split()[:2], f"looks like german: {v}"
        print("EN:", v)

    def test_el_translation(self):
        text = "Beide Teams treffen"
        r = requests.post(f"{BASE_URL}/api/i18n/translate", json={"lang": "el", "texts": [text]}, timeout=60)
        assert r.status_code == 200
        v = r.json().get("map", {}).get(text, "")
        assert any("\u0370" <= c <= "\u03ff" for c in v), f"not greek: {v}"

    def test_fr_translation(self):
        text = "Beide Teams treffen"
        r = requests.post(f"{BASE_URL}/api/i18n/translate", json={"lang": "fr", "texts": [text]}, timeout=60)
        assert r.status_code == 200
        v = r.json().get("map", {}).get(text, "")
        assert v and v.lower() != text.lower()


# ---------- 5) Master easy/medium disjoint ----------
def _norm_match(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


class TestMasterDisjoint:
    def test_easy_medium_disjoint(self):
        r = requests.get(f"{BASE_URL}/api/tips", params={"source": "master", "status": "pending"}, timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        tips = data if isinstance(data, list) else (data.get("tips") or data.get("items") or [])
        by_cat = {"einfach": [], "mittel": []}
        for t in tips:
            cat = str(t.get("master_category") or "").lower()
            if cat in by_cat:
                by_cat[cat].append(t)
        print(f"master pending: einfach={len(by_cat['einfach'])} mittel={len(by_cat['mittel'])}")
        if not by_cat["einfach"] or not by_cat["mittel"]:
            print("only one/none present — acceptable, skipping disjoint check")
            return
        einfach_matches = set()
        for t in by_cat["einfach"]:
            for leg in t.get("legs") or []:
                einfach_matches.add(_norm_match(leg.get("match")))
        mittel_matches = set()
        for t in by_cat["mittel"]:
            for leg in t.get("legs") or []:
                mittel_matches.add(_norm_match(leg.get("match")))
        overlap = (einfach_matches & mittel_matches) - {""}
        assert not overlap, f"einfach vs mittel share matches: {overlap}"
        print(f"disjoint OK. einfach={len(einfach_matches)} mittel={len(mittel_matches)}")
