import os
import time
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or \
           "https://ai-credit-saver.preview.emergentagent.com"

ENDPOINT = f"{BASE_URL}/api/i18n/translate"


class TestI18nTranslate:
    def test_greek_translation(self):
        payload = {"lang": "el", "texts": ["Beide Teams treffen", "0:0 praktisch ausgeschlossen"]}
        r = requests.post(ENDPOINT, json=payload, timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "map" in data, data
        m = data["map"]
        assert "Beide Teams treffen" in m
        assert "0:0 praktisch ausgeschlossen" in m
        v1 = m["Beide Teams treffen"]
        v2 = m["0:0 praktisch ausgeschlossen"]
        # Should have some Greek characters
        assert any("\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff" for c in v1), f"not greek: {v1}"
        assert any("\u0370" <= c <= "\u03ff" or "\u1f00" <= c <= "\u1fff" for c in v2), f"not greek: {v2}"
        print("GREEK ok:", v1, "|", v2)

    def test_greek_cache_hit_is_fast(self):
        payload = {"lang": "el", "texts": ["Beide Teams treffen", "0:0 praktisch ausgeschlossen"]}
        t0 = time.time()
        r = requests.post(ENDPOINT, json=payload, timeout=60)
        dt = time.time() - t0
        assert r.status_code == 200
        assert dt < 3.0, f"cache hit too slow: {dt:.2f}s"
        print(f"cache hit dt={dt:.2f}s")

    def test_german_returns_empty_map(self):
        payload = {"lang": "de", "texts": ["Beide Teams treffen", "0:0 praktisch ausgeschlossen"]}
        r = requests.post(ENDPOINT, json=payload, timeout=30)
        assert r.status_code == 200
        data = r.json()
        assert data.get("map", {}) == {} or all(not v for v in data.get("map", {}).values()), data

    def test_french_translation(self):
        payload = {"lang": "fr", "texts": ["Beide Teams treffen"]}
        r = requests.post(ENDPOINT, json=payload, timeout=60)
        assert r.status_code == 200
        data = r.json()
        m = data.get("map", {})
        assert "Beide Teams treffen" in m
        v = m["Beide Teams treffen"]
        # Should NOT contain German words 'Beide' and should be French-ish
        assert v and v.lower() != "beide teams treffen", f"looks untranslated: {v}"
        print("FR:", v)
