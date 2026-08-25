import React, { createContext, useContext, useState, useCallback } from "react";
import { transliterate } from "transliteration";
import enGB from "./locales/en-GB";
import de from "./locales/de";
import es from "./locales/es";
import el from "./locales/el";
import fr from "./locales/fr";
import it from "./locales/it";
import ar from "./locales/ar";
import tr from "./locales/tr";

// Convert non-Latin scripts (Greek, Cyrillic, Arabic, Hebrew, CJK, …) to Latin
// characters for display only. Latin text (incl. German umlauts ä/ö/ü/ß and
// accents) is left untouched so we never mangle "München" into "Munchen".
const NON_LATIN_RE = /[\u0370-\u03FF\u0400-\u04FF\u0500-\u052F\u0590-\u05FF\u0600-\u06FF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]/;
export function toLatin(text) {
  if (!text || typeof text !== "string") return text;
  if (!NON_LATIN_RE.test(text)) return text;
  // Keep the original script when the reader's selected language uses that same
  // script (a Greek user who picked Ελληνικά wants to see Ολυμπιακός, not Latin).
  const lang = (typeof localStorage !== "undefined" && localStorage.getItem("tj_lang")) || "en";
  if (lang === "el" && /[\u0370-\u03FF]/.test(text)) return text;
  if (lang === "ar" && /[\u0600-\u06FF]/.test(text)) return text;
  return transliterate(text);
}

// Team-name display: native-script readers (el/ar) keep the original; everyone else
// prefers the canonical API-Football Latin name (e.g. "Blumenau SC") when available,
// else falls back to phonetic transliteration.
export function displayTeam(raw, latin) {
  const lang = (typeof localStorage !== "undefined" && localStorage.getItem("tj_lang")) || "en";
  if (lang === "el" || lang === "ar") return raw;
  if (latin) return latin;
  return toLatin(raw);
}

export const LANGUAGES = [
  { code: "en-GB", label: "English", flag: "🇬🇧" },
  { code: "de", label: "Deutsch", flag: "🇩🇪" },
  { code: "es", label: "Español", flag: "🇪🇸" },
  { code: "el", label: "Ελληνικά", flag: "🇬🇷" },
  { code: "fr", label: "Français", flag: "🇫🇷" },
  { code: "it", label: "Italiano", flag: "🇮🇹" },
  { code: "ar", label: "العربية", flag: "🇸🇦" },
  { code: "tr", label: "Türkçe", flag: "🇹🇷" },
];

export const RTL_LANGS = ["ar"];

// ── Viewer timezone ──────────────────────────────────────────────────────────
// Kickoff strings are stored/displayed as Europe/Berlin wall-clock, so a Berlin
// viewer sees them unchanged and every other city gets the correct offset
// (Athens = Berlin +1, London = Berlin −1, …). Selectable in the header.
export const KICKOFF_BASE_TZ = "Europe/Berlin";
export const TIMEZONES = [
  { tz: "Europe/London", label: "London" },
  { tz: "Europe/Berlin", label: "Berlin" },
  { tz: "Europe/Paris", label: "Paris" },
  { tz: "Europe/Madrid", label: "Madrid" },
  { tz: "Europe/Rome", label: "Rom / Roma" },
  { tz: "Europe/Athens", label: "Athen / Αθήνα" },
  { tz: "Europe/Istanbul", label: "Istanbul" },
  { tz: "Europe/Moscow", label: "Moskau" },
  { tz: "America/New_York", label: "New York" },
  { tz: "America/Sao_Paulo", label: "São Paulo" },
  { tz: "Africa/Lagos", label: "Lagos" },
  { tz: "Asia/Dubai", label: "Dubai" },
  { tz: "Asia/Kolkata", label: "Mumbai / Delhi" },
  { tz: "Asia/Bangkok", label: "Bangkok" },
  { tz: "Asia/Singapore", label: "Singapore" },
  { tz: "UTC", label: "UTC" },
];

let _viewerTz = null;
export function getViewerTz() {
  if (_viewerTz) return _viewerTz;
  try {
    const saved = localStorage.getItem("tj_tz");
    if (saved) { _viewerTz = saved; return saved; }
  } catch { /* ignore */ }
  try {
    _viewerTz = Intl.DateTimeFormat().resolvedOptions().timeZone || KICKOFF_BASE_TZ;
  } catch { _viewerTz = KICKOFF_BASE_TZ; }
  return _viewerTz;
}
export function setViewerTz(tz) {
  _viewerTz = tz;
  try { localStorage.setItem("tj_tz", tz); } catch { /* ignore */ }
}
// Apply the account timezone once, only if the viewer hasn't chosen one yet.
export function applyAccountTz(tz) {
  if (!tz) return;
  try { if (localStorage.getItem("tj_tz")) return; } catch { /* ignore */ }
  setViewerTz(tz);
}

function _tzParts(tz, ms) {
  const dtf = new Intl.DateTimeFormat("en-GB", {
    timeZone: tz, hour12: false, year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit",
  });
  const p = {};
  dtf.formatToParts(new Date(ms)).forEach((x) => { p[x.type] = x.value; });
  return { y: +p.year, mo: +p.month, da: +p.day, hh: p.hour, mm: p.minute };
}
function _tzOffsetMin(tz, ms) {
  const q = _tzParts(tz, ms);
  return Math.round((Date.UTC(q.y, q.mo - 1, q.da, +q.hh, +q.mm) - ms) / 60000);
}

// ── Kickoff date/time parsing + prominent formatting (shared by RateWall / Systems) ──
const _KO_MONTHS = { jan: 0, feb: 1, "mär": 2, mar: 2, apr: 3, mai: 4, may: 4, jun: 5, jul: 6, aug: 7, sep: 8, okt: 9, oct: 9, nov: 10, dez: 11, dec: 11 };
const _KO_MON3 = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Parse any stored kickoff string → { ts (ms, for sorting), y, mo, da, time }.
// Handles ISO (2026-07-23T17:00:00+00:00), dd/mm/yyyy HH:MM, "23. Jul 2026", bare HH:MM.
export function isKickoffTimeUnknown(iso) {
  // 23:59 UTC is the backend's "date known, TIME unknown" sentinel — never a real kickoff.
  // Local conversion turns it into a bogus ~01:59 night time, so callers must hide the time.
  if (!iso) return false;
  const ms = Date.parse(iso);
  if (isNaN(ms)) return false;
  const d = new Date(ms);
  return d.getUTCHours() === 23 && d.getUTCMinutes() === 59;
}

export function kickoffInfo(mt) {
  const empty = { ts: null, y: null, mo: null, da: null, time: "" };
  if (!mt) return empty;
  const s = String(mt).trim();
  if (!s || /multibet/i.test(s)) return empty;
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/);
  if (m) {
    // ISO. If it carries an explicit offset/Z it's an ABSOLUTE instant (API-Football stores
    // UTC) → normalise to the Europe/Berlin wall-clock convention the rest of the pipeline
    // (and _toViewer) expects. Without this, a UTC 15:00 kickoff was wrongly treated as
    // 15:00 Berlin and shown 1–2h too early — the source of "enorm viele" kickoff errors.
    const hasTz = /(?:Z|[+-]\d{2}:?\d{2})$/.test(s);
    const realMs = Date.parse(s);
    if (hasTz && !isNaN(realMs)) {
      // 23:59 UTC is the backend's "date known, TIME UNKNOWN" sentinel (date-only kickoff).
      // It is NEVER a real kickoff — do not shift it into the next day as a bogus ~02:00 time.
      // Show the intended match DATE (UTC) with no time (owner: "Europa spielt nie um 2 Uhr nachts").
      const du = new Date(realMs);
      if (du.getUTCHours() === 23 && du.getUTCMinutes() === 59) {
        return { ts: realMs, y: du.getUTCFullYear(), mo: du.getUTCMonth() + 1, da: du.getUTCDate(), time: "", dateOnly: true };
      }
      const b = _tzParts(KICKOFF_BASE_TZ, realMs);
      return { ts: Date.UTC(b.y, b.mo - 1, b.da, +b.hh, +b.mm), y: b.y, mo: b.mo, da: b.da, time: `${b.hh}:${b.mm}` };
    }
    const [, y, mo, da, hh, mm] = m;
    return { ts: Date.UTC(+y, +mo - 1, +da, +hh, +mm), y: +y, mo: +mo, da: +da, time: `${hh}:${mm}` };
  }
  m = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?/);
  if (m) {
    const time = m[4] ? `${m[4].padStart(2, "0")}:${m[5]}` : "";
    return { ts: Date.UTC(+m[3], +m[2] - 1, +m[1], m[4] ? +m[4] : 12, m[5] ? +m[5] : 0), y: +m[3], mo: +m[2], da: +m[1], time };
  }
  m = s.match(/^(\d{1,2})\.\s*([A-Za-zäöü]+)\s+(\d{4})(?:\s+(\d{1,2}):(\d{2}))?/);
  if (m) {
    const mo = _KO_MONTHS[m[2].toLowerCase().slice(0, 3)];
    const time = m[4] ? `${m[4].padStart(2, "0")}:${m[5]}` : "";
    if (mo != null) return { ts: Date.UTC(+m[3], mo, +m[1], m[4] ? +m[4] : 12, m[5] ? +m[5] : 0), y: +m[3], mo: mo + 1, da: +m[1], time };
  }
  m = s.match(/^(\d{1,2}):(\d{2})$/);
  if (m) return { ts: null, y: null, mo: null, da: null, time: `${m[1].padStart(2, "0")}:${m[2]}` };
  return empty;
}

// Convert a parsed kickoffInfo (Europe/Berlin wall-clock) to the viewer's timezone.
function _toViewer(info) {
  if (!info || info.ts == null) return info; // bare time / unknown date → leave as-is
  if (info.dateOnly) return info;            // date-only sentinel → never shift into a bogus time/day
  const berlinOff = _tzOffsetMin(KICKOFF_BASE_TZ, info.ts);
  const realMs = info.ts - berlinOff * 60000; // true instant behind the Berlin wall-clock
  const v = _tzParts(getViewerTz(), realMs);
  return { ts: realMs, y: v.y, mo: v.mo, da: v.da, time: `${v.hh}:${v.mm}` };
}

// A clear, human label: "Heute 17:00" / "Morgen 15:00" / "24.07. 15:00".
export function formatKickoff(mt, t) {
  const info = _toViewer(kickoffInfo(mt));
  if (!info.y && !info.time) return "";
  const tr = typeof t === "function" ? t : (k) => (k === "date.today" ? "Heute" : "Morgen");
  let dayLabel = "";
  if (info.y) {
    const now = new Date();
    const td = { y: now.getFullYear(), mo: now.getMonth() + 1, da: now.getDate() };
    const tmr = new Date(now); tmr.setDate(now.getDate() + 1);
    const td2 = { y: tmr.getFullYear(), mo: tmr.getMonth() + 1, da: tmr.getDate() };
    if (info.y === td.y && info.mo === td.mo && info.da === td.da) dayLabel = tr("date.today");
    else if (info.y === td2.y && info.mo === td2.mo && info.da === td2.da) dayLabel = tr("date.tomorrow");
    else dayLabel = `${_KO_MON3[(info.mo || 1) - 1]} ${info.da}`;
  }
  return [dayLabel, info.time].filter(Boolean).join(" ");
}

// Format a FREE-TEXT kickoff (scraper strings like "02.08. 14:00", "02/08/2026 GMT (13:00)")
// into the compact owner style "Aug 2 · 14:00" — never the year (owner 2026-08).
export function formatKickoffText(mt) {
  if (!mt) return "";
  const s = String(mt).trim();
  const info = kickoffInfo(s);
  if (info.mo && info.da) {
    return [`${_KO_MON3[info.mo - 1]} ${info.da}`, info.time].filter(Boolean).join(" · ");
  }
  const dm = s.match(/(\d{1,2})[.\/](\d{1,2})(?:[.\/]\d{2,4})?/);
  const tm = s.match(/(\d{1,2}):(\d{2})/);
  let out = "";
  if (dm) {
    const da = +dm[1], mo = +dm[2];
    if (mo >= 1 && mo <= 12 && da >= 1 && da <= 31) out = `${_KO_MON3[mo - 1]} ${da}`;
  }
  const time = tm ? `${tm[1].padStart(2, "0")}:${tm[2]}` : "";
  return [out, time].filter(Boolean).join(" · ") || s;
}


// True while a match is (likely) IN PLAY: it kicked off 0..3h ago. Used to show a
// "Läuft/Live" badge so a just-started game doesn't just vanish from the feed but is
// clearly marked as live before it moves to "Abgerechnet" (owner 2026-07-24).
export function isKickoffLive(mt) {
  const info = kickoffInfo(mt);
  if (info.ts == null) return false;
  const elapsedH = (Date.now() - info.ts) / 3600000;
  return elapsedH >= 0 && elapsedH <= 3;
}

// Apex-Flame season gate (owner): flames are OFF during the summer break and come
// back automatically when the new season starts on 1 September 2026.
export const FLAMES_START = new Date("2026-09-01T00:00:00Z");
export function flamesActive() {
  return Date.now() >= FLAMES_START.getTime();
}


// Earliest kickoff (ms) across a tip's match_time + legs — for ascending sort.
// Tips without a resolvable kickoff sort last.
export function kickoffTs(tip) {
  const cand = [];
  const add = (v) => { const i = kickoffInfo(v); if (i.ts != null) cand.push(i.ts); };
  add(tip && tip.match_time);
  (tip && tip.legs ? tip.legs : []).forEach((l) => add(l && l.kickoff));
  return cand.length ? Math.min(...cand) : Infinity;
}

// Localize the German bet-market strings produced by the backend (systems + tips).
// Keeps dynamic parts (team names, scores). Order matters: combos before singles.
export function localizeMarket(market, t) {
  if (!market || typeof market !== "string") return market;
  let m = market;
  const combos = [
    ["Doppelte Chance 1X + Beide treffen", `${t("mkt.dc1x")} + ${t("mkt.btts")}`],
    ["Doppelte Chance X2 + Beide treffen", `${t("mkt.dcx2")} + ${t("mkt.btts")}`],
    ["Doppelte Chance 1X + Über 1.5 Tore", `${t("mkt.dc1x")} + ${t("mkt.over15")}`],
    ["Doppelte Chance X2 + Über 1.5 Tore", `${t("mkt.dcx2")} + ${t("mkt.over15")}`],
    ["Doppelte Chance 1X", t("mkt.dc1x")],
    ["Doppelte Chance X2", t("mkt.dcx2")],
    ["(Draw No Bet)", `(${t("mkt.dnb")})`],
    ["Beide Teams treffen (BTTS)", t("mkt.btts")],
    ["Über 0.5 Tore", t("mkt.over05")],
    ["Über 1.5 Tore", t("mkt.over15")],
    ["Über 2.5 Tore", t("mkt.over25")],
    ["Genaues Ergebnis", t("mkt.cs")],
    ["Unentschieden (X)", t("mkt.draw")],
  ];
  for (const [de, loc] of combos) m = m.split(de).join(loc);
  // Corner (Ecken) Over/Under lines — dynamic (7.5 / 8.5 / 9.5 …).
  m = m.replace(/Über\s+(\d+(?:\.\d+)?)\s+Ecken/g, (_, n) => `${t("mkt.ovr")} ${n} ${t("mkt.corners")}`);
  m = m.replace(/Unter\s+(\d+(?:\.\d+)?)\s+Ecken/g, (_, n) => `${t("mkt.und")} ${n} ${t("mkt.corners")}`);
  // Player props — comma decimals (0,5), format "{Player} — {market}". Localize the
  // market wording; keep player name and any "(1+)" hint intact. Order matters:
  // "Schüsse aufs Tor" before bare "Schüsse".
  const N = "(\\d+(?:[.,]\\d+)?)";
  m = m.replace(new RegExp(`Über\\s+${N}\\s+Paraden`, "gi"), (_, n) => `${t("mkt.ovr")} ${n} ${t("mkt.saves")}`);
  m = m.replace(new RegExp(`Über\\s+${N}\\s+Schüsse aufs Tor`, "gi"), (_, n) => `${t("mkt.ovr")} ${n} ${t("mkt.sot")}`);
  m = m.replace(new RegExp(`Über\\s+${N}\\s+Torschüsse`, "gi"), (_, n) => `${t("mkt.ovr")} ${n} ${t("mkt.shots")}`);
  m = m.replace(new RegExp(`Über\\s+${N}\\s+Schüsse`, "gi"), (_, n) => `${t("mkt.ovr")} ${n} ${t("mkt.shots")}`);
  m = m.replace(new RegExp(`Über\\s+${N}\\s+Fouls begangen`, "gi"), (_, n) => `${t("mkt.ovr")} ${n} ${t("mkt.fouls")}`);
  m = m.replace(new RegExp(`Über\\s+${N}\\s+mal gefoult`, "gi"), (_, n) => `${t("mkt.ovr")} ${n} ${t("mkt.fouled")}`);
  m = m.replace(new RegExp(`Über\\s+${N}\\s+Karten?`, "gi"), (_, n) => `${t("mkt.ovr")} ${n} ${t("mkt.card")}`);
  m = m.replace(/Torschütze\s*\(Anytime\)/gi, t("mkt.scorer"));
  m = m.replace(/Anytime\s+Torschütze/gi, t("mkt.scorer"));
  m = m.replace(/\bTorschütze\b/gi, t("mkt.scorer"));
  m = m.replace(/sieht eine Karte/gi, t("mkt.getcard"));
  // ── extended German market wording (halves, asian lines, builders, DC/handicap,
  //    generic over/under goals) so NOTHING stays German after a language switch ──
  m = m.replace(/3er-?Bet-?Builder/gi, t("mkt.bb3"));
  m = m.replace(/(\d+)er-?Bet-?Builder/gi, (_, n) => `${n}× ${t("mkt.bb")}`);
  m = m.replace(/Value-?Banker/gi, t("mkt.valuebanker"));
  m = m.replace(/Risk-?Bet-?Builder/gi, t("mkt.bbrisk"));
  m = m.replace(/Mega-?Bet-?Builder/gi, t("mkt.bbmega"));
  m = m.replace(/Bet-?Builder/gi, t("mkt.bb"));
  m = m.replace(/Tor\s+in\s+jeder\s+Halbzeit/gi, t("mkt.goaleachhalf"));
  m = m.replace(/in\s+jeder\s+Halbzeit/gi, t("mkt.eachhalf"));
  m = m.replace(/beide\s+Halbzeiten/gi, t("mkt.eachhalf"));
  m = m.replace(/1\.\s*Halbzeit/gi, t("mkt.ht1"));
  m = m.replace(/erste\s+Halbzeit/gi, t("mkt.ht1"));
  m = m.replace(/2\.\s*Halbzeit/gi, t("mkt.ht2"));
  m = m.replace(/zweite\s+Halbzeit/gi, t("mkt.ht2"));
  m = m.replace(/\bHalbzeit\b/gi, t("mkt.half"));
  m = m.replace(/Beide\s+Teams\s+treffen/gi, t("mkt.btts"));
  m = m.replace(/Beide\s+treffen/gi, t("mkt.btts"));
  m = m.replace(/Team-?Tore\s+Über\s+(\d+(?:[.,]\d+)?)/gi, (_, n) => `${t("mkt.teamgoals")} ${t("mkt.ovr")} ${n.replace(",", ".")}`);
  m = m.replace(/Team-?Tore\s+Unter\s+(\d+(?:[.,]\d+)?)/gi, (_, n) => `${t("mkt.teamgoals")} ${t("mkt.und")} ${n.replace(",", ".")}`);
  m = m.replace(/Über\s+(\d+(?:[.,]\d+)?)\s+Tore/gi, (_, n) => `${t("mkt.ovr")} ${n.replace(",", ".")} ${t("mkt.goals")}`);
  m = m.replace(/Unter\s+(\d+(?:[.,]\d+)?)\s+Tore/gi, (_, n) => `${t("mkt.und")} ${n.replace(",", ".")} ${t("mkt.goals")}`);
  // English "Over/Under X Goals" (raw member/bookmaker slips) → locale, so it doesn't stay
  // half-English on non-Latin locales (owner 2026-07-26).
  m = m.replace(/\bOver\s+(\d+(?:[.,]\d+)?)\s+Goals?\b/gi, (_, n) => `${t("mkt.ovr")} ${n.replace(",", ".")} ${t("mkt.goals")}`);
  m = m.replace(/\bUnder\s+(\d+(?:[.,]\d+)?)\s+Goals?\b/gi, (_, n) => `${t("mkt.und")} ${n.replace(",", ".")} ${t("mkt.goals")}`);
  m = m.replace(/Doppelte\s+Chance\s+12/gi, t("mkt.dc12"));
  m = m.replace(/Doppelte\s+Chance\s+1X/gi, t("mkt.dc1x"));
  m = m.replace(/Doppelte\s+Chance\s+X2/gi, t("mkt.dcx2"));
  m = m.replace(/Draw\s+No\s+Bet/gi, t("mkt.dnb"));
  m = m.replace(/Genaues\s+Ergebnis/gi, t("mkt.cs"));
  m = m.replace(/Unentschieden(?:\s*\(X\))?/gi, t("mkt.draw"));
  // English-worded raw selections (member/bookmaker slips) → locale, so a slip that was
  // parsed in English also reads correctly in Greek/any language (owner 2026-07-26).
  m = m.replace(/\bGG\s*\/\s*NG\s+GG\b/gi, t("mkt.ggng_yes"));
  m = m.replace(/\bGG\s*\/\s*NG\s+NG\b/gi, t("mkt.ggng_no"));
  m = m.replace(/\bGG\s*\/\s*NG\b/gi, t("mkt.ggng_yes"));
  m = m.replace(/\bBoth\s+Teams\s+to\s+Score\b/gi, t("mkt.btts"));
  m = m.replace(/\bDouble\s+chance\s+1X\b/gi, t("mkt.dc1x"));
  m = m.replace(/\bDouble\s+chance\s+X2\b/gi, t("mkt.dcx2"));
  m = m.replace(/\bDouble\s+chance\s+12\b/gi, t("mkt.dc12"));
  m = m.replace(/\bDouble\s+chance\b/gi, t("mkt.doublechance"));
  m = m.replace(/\bDraw\b/gi, t("mkt.draw"));
  m = m.replace(/\bor\b/gi, t("mkt.or"));
  m = m.replace(/\(?\s*Asiatisch\s*\)?/gi, ` ${t("mkt.asian")}`);
  m = m.replace(/\bHandicap\b/gi, t("mkt.handicap"));
  m = m.replace(/\btrifft\b/gi, t("mkt.scores"));
  m = m.replace(/\s{2,}/g, " ").trim();
  return m;
}

// Localize backend-generated German PROSE (AI commentary `ai_analysis` + system subtitles).
// These are free-text German strings shared across all users, so translate them client-side
// into the reader's language. German readers keep the original; unknown phrases stay as-is.
// (owner 2026-07-26: "μετέφρασε τα ολα" — translate everything.)
export function localizeProse(text, t, lang) {
  if (!text || typeof text !== "string") return text;
  if (lang === "de") return text;
  let m = text;
  const P = [
    [/liegt zurück und drückt auf den Ausgleich/gi, "prose.trailingpush"],
    [/Beide drücken bei 0:0/gi, "prose.bothpush"],
    [/bei GENAU 2 Toren gibt'?s den Einsatz zurück/gi, "prose.exact2refund"],
    [/\(Asian-Absicherung\)/gi, "prose.asianhedge"],
    [/am besten sofort spielen, solange die Quote hoch ist/gi, "prose.playnow"],
    [/\bTiming:/gi, "prose.timing"],
    [/\bDruck:/gi, "prose.pressure"],
    [/\bLive zu\b/gi, "prose.liveat"],
    [/\bStand\b/gi, "prose.score"],
    [/der große Zocker-Wumms/gi, "prose.gamblebang"],
    [/nur kommende Spiele/gi, "prose.upcomingonly"],
    [/nächste 48h/gi, "prose.next48"],
    [/\bläuft bis\b/gi, "prose.runsuntil"],
    [/Favoriten-Spiele/gi, "prose.favgames"],
    [/×\s*Favorit/gi, "prose.xfav"],
    [/×\s*Value-?X/gi, "prose.xvaluex"],
    [/\bLegs\b/gi, "prose.legs"],
    [/Schüsse aufs Tor/gi, "mkt.sot"],
    [/\bEcken\b/gi, "mkt.corners"],
    [/\bAsian\b/gi, "mkt.asian"],
  ];
  for (const [re, key] of P) {
    const val = t(key);
    m = m.replace(re, () => (/^×/.test(re.source) ? `× ${val}` : val));
  }
  // generic German market terms embedded in the prose
  m = m.replace(/Über\s+(\d+(?:[.,]\d+)?)\s+Tore?/gi, (_, n) => `${t("mkt.ovr")} ${n.replace(",", ".")} ${t("mkt.goals")}`);
  m = m.replace(/Unter\s+(\d+(?:[.,]\d+)?)\s+Tore?/gi, (_, n) => `${t("mkt.und")} ${n.replace(",", ".")} ${t("mkt.goals")}`);
  m = m.replace(/Über\s+(\d+(?:[.,]\d+)?)/gi, (_, n) => `${t("mkt.ovr")} ${n.replace(",", ".")}`);
  m = m.replace(/Unter\s+(\d+(?:[.,]\d+)?)/gi, (_, n) => `${t("mkt.und")} ${n.replace(",", ".")}`);
  m = m.replace(/Doppelte\s+Chance/gi, t("mkt.doublechance"));
  const WD = { Mo: "wd.mo", Di: "wd.di", Mi: "wd.mi", Do: "wd.do", Fr: "wd.fr", Sa: "wd.sa", So: "wd.so" };
  m = m.replace(/\b(Mo|Di|Mi|Do|Fr|Sa|So)\b(?=\s+\d)/g, (_, d) => t(WD[d]));
  m = m.replace(/\s{2,}/g, " ").trim();
  return m;
}
// market) into a clean, correctly-worded label. Handles legacy posted slips too.
//  - "Total OVER 1.5" / "Total Over 1,5"  -> "Über 1.5 Tore"
//  - "Total UNDER 3.5"                    -> "Unter 3.5 Tore"
//  - "Sutjeska 3.5" / "Connah's Quay 2.5" -> "<Team> Handicap +3.5"
//  - already-correct German markets pass through localizeMarket unchanged.
export function formatSelection(sel, t) {
  // toLatin FIRST on the raw input (latinises Cyrillic/foreign TEAM names), then localise —
  // otherwise toLatin would strip the Greek/Arabic market words we just translated, leaving
  // English on non-Latin locales (owner 2026-07-26: Greek slip still showed "GG/NG", "Double chance").
  const raw = String(sel || "");
  const lat = toLatin(raw);
  // Greek 1X2 full-time DRAW: sources post "Ισοπαλία" or "Χ (τελικό)". toLatin mangles the
  // Greek draw "Χ τελικό" into e.g. "H teliko" — always show the proper localised
  // "Draw (X)" / "Unentschieden (X)" / "Ισοπαλία (X)" label instead (owner 2026-07-29).
  if (/ισοπαλ/i.test(raw)) return t("mkt.draw");
  if (/^[xχ]$/i.test(lat.trim()) || /^[Χχ]$/.test(raw.trim())) return t("mkt.draw");
  const isFullTime = /ισοπαλ|τελικ/i.test(raw) || /\btelik[oó]\b/i.test(lat);
  if (isFullTime && /(?:^|[\s(/])(?:x|h|ch|χ)(?:[\s)/.]|$)/i.test(`${raw} ¦ ${lat}`)) {
    return t("mkt.draw");
  }
  return normalizeBetTerms(_formatSelection(lat, t), t);
}

// Clean up phonetically-transliterated foreign betting terms into the reader's language
// so a member's Greek slip ("Over 3.5 Korner (1o Imihrono)") reads correctly in ANY
// language (DE "Über 3.5 Ecken (1. Halbzeit)", EN "Over 3.5 Corners (1. Half)", …).
function normalizeBetTerms(s, t) {
  if (!s || typeof s !== "string") return s;
  const tr = (typeof t === "function") ? t : ((k) => k);
  let m = s;
  m = m.replace(/(\d+)\s*o\s+imi?[hx]?rono/gi, (_, n) => `${n}. ${tr("mkt.half")}`);
  m = m.replace(/\bimi?[hx]?rono\b/gi, tr("mkt.half"));
  m = m.replace(/\bkorners?\b/gi, tr("mkt.corners"));
  m = m.replace(/\b(gkol|gol)s?\b/gi, tr("mkt.goals"));
  // drop the redundant trailing "- Over/Under" market-type label
  m = m.replace(/\s*[-·]?\s*(over|über|ueber)\s*\/\s*(under|unter)\s*$/i, "");
  m = m.replace(/\bover\b/gi, tr("mkt.ovr"));
  m = m.replace(/\bunder\b/gi, tr("mkt.und"));
  m = m.replace(/\bueber\b/gi, tr("mkt.ovr"));
  m = m.replace(/\s{2,}/g, " ").trim();
  return m;
}
function _formatSelection(sel, t) {
  if (!sel || typeof sel !== "string") return sel;
  const s = sel.trim();
  const dec = (x) => x.replace(",", ".");
  let m = s.match(/^total\s+(?:over|über|ueber)\s+(\d+(?:[.,]\d+)?)/i);
  if (m) return localizeMarket(`Über ${dec(m[1])} Tore`, t);
  // "Both halves over X" / "Over X goals in each half" → a goal in EACH half (NOT a match
  // total). Must be caught before the generic over/under handler so it never collapses to
  // a plain "Über X Tore" match total (owner 2026-08: bookie 'Both halves over 0.5').
  m = s.match(/^both\s+halves\s+(?:over|über|ueber)\s+(\d+(?:[.,]\d+)?)/i);
  if (m) return localizeMarket(`Über ${dec(m[1])} Tore in jeder Halbzeit`, t);
  m = s.match(/^total\s+(?:under|unter)\s+(\d+(?:[.,]\d+)?)/i);
  if (m) return localizeMarket(`Unter ${dec(m[1])} Tore`, t);
  // leave already-worded markets to localizeMarket
  if (/handicap|über|unter|\btore\b|torsch|chance|treffen|draw no bet|ergebnis|btts|\bover\b|\bunder\b/i.test(s)) {
    return localizeMarket(s, t);
  }
  // bare "<Team> ±X.5" => handicap (positive if no sign)
  m = s.match(/^(.+?)\s([+-]?\d+(?:[.,]\d+)?)$/);
  if (m) {
    let n = dec(m[2]);
    if (!/^[+-]/.test(n)) n = "+" + n;
    return `${m[1].trim()} Handicap ${n}`;
  }
  return localizeMarket(s, t);
}


const T = {
  "en-GB": enGB,
  de,
  es,
  el,
  fr,
  it,
  ar,
  tr,
};

const I18nContext = createContext(null);

// Auto-detect the reader's language from the browser on first visit (no saved
// choice yet). Maps navigator languages to our 8 supported codes; falls back to EN.
const SUPPORTED_LANGS = ["en-GB", "es", "de", "el", "fr", "it", "ar", "tr"];
function detectInitialLang() {
  try {
    let saved = localStorage.getItem("tj_lang");
    if (saved === "en") saved = "en-GB";
    if (saved && SUPPORTED_LANGS.includes(saved)) return saved;
    const cands = [navigator.language, ...(navigator.languages || [])].filter(Boolean);
    for (const c of cands) {
      let code = c.slice(0, 2).toLowerCase();
      if (code === "en") code = "en-GB";
      if (SUPPORTED_LANGS.includes(code)) return code;
    }
  } catch { /* ignore */ }
  return "en-GB";
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(detectInitialLang);
  const [tz, setTzState] = useState(getViewerTz);
  const applyDir = useCallback((l) => {
    const rtl = RTL_LANGS.includes(l);
    document.documentElement.dir = rtl ? "rtl" : "ltr";
    document.documentElement.lang = l;
  }, []);
  React.useEffect(() => { applyDir(lang); }, [lang, applyDir]);
  const setLang = useCallback((l) => {
    setLangState(l);
    localStorage.setItem("tj_lang", l);
    applyDir(l);
  }, [applyDir]);
  const setTz = useCallback((z) => { setViewerTz(z); setTzState(z); }, []);
  const t = useCallback((key) => (T[lang] && T[lang][key]) || T["en-GB"][key] || key, [lang]);
  return <I18nContext.Provider value={{ t, lang, setLang, tz, setTz }}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  return useContext(I18nContext);
}
