# RASTER MAP — TipJar GLOBAL (Erste Etage / Skelett)

Stand: 2026-06 (Emergent Fork). 13 Raster (0–12), 100% inline-gestylt, Tailwind-frei, bulletproof für Vite/Hetzner.
App.jsx = Single Source of Truth, importiert genau diese 13 in Reihenfolge 0→12.

| # | Datei | Inhalt (VON → BIS) |
|---|-------|--------------------|
| 0 | Raster0_Splash.jsx | Splash/Lade-Screen, gelber SMIL-Rand → Übergang zu Raster 1 |
| 1 | Raster1_PartnerPillenBisOrange.jsx | "Deine Partner…" + RENT 2 PILLS 300€ + RENT A PILL 150€ (dashed pink) + WAZAMBA lila + Casino-Grid bis SGCASINO orange |
| 2 | Raster2_CommunityPricing.jsx | "Supporte TipJar…" + Pricing 119,99€ PARTNER → 9,99€ SUPPORTER (klein→groß) |
| 3 | Raster3_ToolbarHeader.jsx | Toolbar h-80px: Logo + Download + Glocke + Sprache + Registrieren gelb + Plus |
| 4 | Raster4_KiInfoAndSixActions.jsx | KI-Info-Box + blauer Korrektur-Knopf + 6 Pillen (grün/grün/rot/weiß/blau/pink) |
| 5 | Raster5_WettenGeldVerdienen.jsx | Krone-CTA + Tipp einwerfen/Münzen/Sammlung/Community LIVE/confidential + Glühbirne |
| 6 | Raster6_Batterie.jsx | "Sich gegenseitig beschenken" + Batterie 0/2500 + feeden/Spendieren + Leaderboard |
| 7 | Raster7_GlobaleCommunity.jsx | Badge + "Posten. Bewerten. Kassieren." + grüne Haken-Box + Wasserzeichen + tipjarglobal.com |
| 8 | Raster8_Video.jsx | Video SPORTS BETTING + Play + "Try it free at tipjarglobal.com" |
| 9 | Raster9_WasIstTipJar.jsx | Was ist TipJar? + System-Modus USP + Vorteil-Box + CTA |
| 10 | Raster10_FreundeEinladen.jsx | Ziel 1.000 + Einladungslink + Progress + WhatsApp/Telegram/X |
| 11 | Raster11_HallOfFame.jsx | HALL OF FAME + Best of + CTA + Empty-State + Signatur |
| 12 | Raster12_LegalFooter.jsx | Footer + Impressum/Datenschutz/AGB + WICHTIGER HINWEIS + 18+ + BZgA + kontakt@ |

## REGELN für Meta AI (damit nie Missverständnisse passieren)
- Farben IMMER inline (`style={{...}}`), NIE Tailwind-Farbklassen — sonst purged Vite sie weg.
- Jede Datei = genau EIN Raster. Kein Code über die VON-BIS-Grenze hinaus.
- App.jsx bleibt die einzige Quelle mit exakt 13 Imports 0→12. Keine App.js.
- Alte 58 Emergent-Komponenten sind verwaist (nicht mehr importiert) → in Termius gefahrlos löschbar.
