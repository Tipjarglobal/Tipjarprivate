# RASTER MAP — TipJar GLOBAL · THEMELIA FUNDAMENT (Erste Etage)

13 Raster (0–12), 100% inline-gestylt, Tailwind-frei, framer-motion-frei. App.jsx = Single Source (genau 13 Imports 0→12, keine App.js). Bulletproof für Vite/Hetzner.

## Zuordnung (VON → BIS)
| # | Datei | data-testid | Inhalt |
|---|-------|-------------|--------|
| 0 | Raster0_Splash.jsx | raster-0 | Splash/Lade-Screen, gelber Rand via CSS @keyframes |
| 1 | Raster1_PartnerPillenBisOrange.jsx | raster-1 | "Deine Partner…" + RENT 2 (300€) + RENT 1 (150€) dashed pink + WAZAMBA lila + Casino-Grid bis SGCASINO orange |
| 2 | Raster2_CommunityPricing.jsx | raster-2 | "Supporte TipJar…" Pricing 119,99€ PARTNER → 9,99€ SUPPORTER (groß→klein) |
| 3 | Raster3_ToolbarHeader.jsx | raster-3 | Toolbar h-80: Logo + Download + Glocke + Sprache + Registrieren gelb + Plus |
| 4 | Raster4_KiInfoAndSixActions.jsx | raster-4 | KI-Info + blauer Korrektur-Knopf + 6 Pillen (grün/grün/rot/weiß/blau/pink) |
| 5 | Raster5_WettenGeldVerdienen.jsx | raster-5 | Krone-CTA + Tipp/Münzen/Sammlung/Community LIVE/confidential + Glühbirne |
| 6 | Raster6_Batterie.jsx | raster-6 | Batterie 0/2500 + feeden/Spendieren + Leaderboard |
| 7 | Raster7_GlobaleCommunity.jsx | raster-7 | Posten. Bewerten. Kassieren. + Wasserzeichen + tipjarglobal.com |
| 8 | Raster8_Video.jsx | raster-8 | Video SPORTS BETTING + Play + "Try it free" |
| 9 | Raster9_WasIstTipJar.jsx | raster-9 | Was ist TipJar? + Vorteil-Box + CTA |
| 10 | Raster10_FreundeEinladen.jsx | raster-10 | Ziel 1.000 + Einladungslink + WhatsApp/Telegram/X |
| 11 | Raster11_HallOfFame.jsx | raster-11 | HALL OF FAME + Best of + CTA + Empty-State |
| 12 | Raster12_LegalFooter.jsx | raster-12 | Footer + Impressum/Datenschutz/AGB + WICHTIGER HINWEIS + 18+ + BZgA + kontakt@ |

## Fixe Farben (Hex, inline)
RENT pink `#ec4899` · WAZAMBA lila `#a855f7` · BANKONBET `#22c55e` · ROBOCAT `#ef4444` · PISTOLO `#eab308` · 5GRINGOS `#a16207` · 20BET `#16a34a` · BETSCORE `#facc15` · SGCASINO `#f97316`

## THEMELIA-REGELN für Meta AI / Termius
1. **Farben IMMER inline** (`style={{ backgroundColor: "#.." }}`), NIE Tailwind-Klassen (`bg-volt` etc.). Grund: Vite purged sie weg → ungestylte Kästen (Screenshot 19:16).
2. **Animationen IMMER CSS @keyframes inline**, NIE framer-motion `motion.path`. Grund: Vite Tree-Shaking killt framer-motion (gelber Schlangen-Rand Bug).
3. **App.jsx = Single Source**, genau 13 Imports. Kein backend/, kein Dockerfile, kein Caddy, kein mongo ändern.
4. **Nur innerhalb VON-BIS arbeiten**, nie über die BIS-Grenze hinaus.
5. **i18n**: Texte aktuell Deutsch als Basis; `data-i18n="rasterN…"`-Attribute sind gesetzt → Meta AI hängt die 8 Sprachen (EN/DE/ES/EL/FR/IT/AR/TR) daran auf.
6. `navigator.vibrate()` nur in `useEffect` mit `if (typeof window !== "undefined")`.

Alte 58 Emergent-Komponenten sind verwaist (nicht importiert) → in Termius gefahrlos löschbar.
