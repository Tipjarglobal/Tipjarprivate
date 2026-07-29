import { useState, useEffect } from "react";
import api from "./api";

// Dynamic prose translation cache. Free-form generated text (KI analyses, Smart
// reports, Master texts) is stored in one language; we translate it on demand into
// the reader's language via the backend (/api/i18n/translate) and cache the result
// in memory + localStorage so a given string is only ever translated once per lang.
const _mem = {};
// Only real translations are persisted. Failed / missing translations are NOT cached as
// the source text (that used to permanently "stick" German when a batch failed) — instead
// they stay absent so a later render / reload retries them. Bumping this key wipes any
// poisoned caches from older builds.
const _CACHE_V = "tj_tr2_";

function _cache(lang) {
  if (_mem[lang]) return _mem[lang];
  try {
    _mem[lang] = JSON.parse(localStorage.getItem(_CACHE_V + lang) || "{}");
  } catch {
    _mem[lang] = {};
  }
  return _mem[lang];
}

function _save(lang) {
  try {
    localStorage.setItem(_CACHE_V + lang, JSON.stringify(_mem[lang]));
  } catch { /* quota — ignore */ }
}

export function useProseTranslations(texts, lang) {
  const [, force] = useState(0);
  const list = (Array.isArray(texts) ? texts : [texts]).filter(
    (x) => x && typeof x === "string"
  );
  useEffect(() => {
    if (!lang || lang === "de") return;
    const cache = _cache(lang);
    const need = [...new Set(list.filter((x) => !(x in cache)))];
    if (need.length === 0) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.post("/i18n/translate", { lang, texts: need });
        if (cancelled) return;
        const map = (data && data.map) || {};
        // Persist ONLY entries the server actually returned. Anything missing stays absent
        // so it retries next time (never poison the cache with untranslated German).
        Object.assign(cache, map);
        _save(lang);
        force((v) => v + 1);
      } catch { /* keep source text on failure — will retry */ }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lang, list.join("\u0000")]);
  return (text) =>
    !lang || lang === "de" ? text : (_cache(lang)[text] || text);
}
