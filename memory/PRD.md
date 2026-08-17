# TipJar Global — PRD (Kurzfassung)

> Vollständige Produktregeln & Historie: `/app/tipjar.md`, `/app/BRAIN.md`, `/app/MEMORY.md`.
> Sprache des Nutzers: **Deutsch** — alle Antworten auf Deutsch.

## Produkt
Sports-Betting-/Tip-Community-PWA. React (frontend) + FastAPI (backend) + MongoDB.
Features: AI-Combo-Generierung & OCR (Gemini via Emergent LLM Key), Live-Settlement-Loops,
30-Tier Coin-Jar-System, i18n (8 Sprachen), Sponsor-Feeder, Coin-Battery, JarDex/Open Case,
privater Admin-Bereich `/insights` (Analytics, Pick-Manager, Sponsor-Ranking, Glitch-Tracker).

## Umgebungen
- PREVIEW (dev): Arbeitsumgebung des Agents.
- PRODUCTION: https://tipjarglobal.com — Änderungen erfordern Redeploy durch den Nutzer.
- Git: kein remote pull/push im Container; Nutzer lädt `.txt`-Dateien hoch bzw. nutzt „Save to GitHub".

## Wichtige Constraints
- Keine automatisierten Massentests (Credits sparen). Nur curl + einzelner Smoke-Screenshot.
- Keine neuen Dependencies ohne Grund. Direkt Dateien überschreiben, kein Refactoring.

## Changelog (Session 16.08.2026)
- 28 Jar-PNGs via `install_all_jars.sh` nach `/app/frontend/public/jars/`.
- Sponsor-Feeder: BETSCORE + SGCASINO ergänzt (7 gesamt).
- Sponsor-Klick-Tracking: `POST /api/sponsors/{id}/click` (Event-basiert; Bots/Crawler aus, Admin zählt) +
  `GET /api/admin/sponsor-stats?period=today|7d|all`. Ranking-UI mit Zeitraum-Filter in `SecretInsights.jsx`.
- Jar-Tabs bereinigt: ProfileModal nur 2 Tabs; JarDex neu aus `JAR_DEFS` (echte PNGs, keine `???`);
  OpenCase Hinweis-Text; Backend `/jars/opencase` → `List[str]`, Register-Default `["common_glass"]`.
- `AnimatedJar.jsx`: frühere Homepage-Version wiederhergestellt (Wappen + Glas + Füll-Animation + Boost-Münzen).
- **Money-Glitch-Lexikon (Typ1–Typ9)**:
  - `/app/backend/glitch_lexikon.py` (FLAGS, GLITCH_LEXIKON, `detect_glitch`, `LEXIKON_PROMPT_BLOCK`, `brain_lessons`).
  - KI-Integration: Lexikon-Block an `AI_SYSTEM` angehängt (Slip-Analyse erkennt/bewertet Muster) +
    9 Lessons idempotent in `db.master_brain` geseedet (Startup).
  - Privater Bet-Tracker (Admin `/insights`): `GET /admin/glitch-lexikon`, `GET/POST /admin/glitch-bets`,
    `PUT/DELETE /admin/glitch-bets/{id}` — Auto-Tagging via `detect_glitch`, Profit-Summary. UI: `GlitchTracker`.
- **TipJarMaster GENERELLER Safety-Glitch-Melder (Patch 16.08.)**:
  - `MasterAvatar.jsx` ersetzt: rotierende Safety-Speech-Blase (alle 4s), generisch für JEDES Team.
  - `glitch_lexikon.py` ersetzt: + `SAFETY_SPEECH_TEMPLATES`, `get_safety_speech`, `build_avatar_speech_for_tip`, `master_pille_must_have_safe`.
  - `/api/master/avatar` reichert jeden Call mit generischem Safety-Speech + `safety_speeches` an (Playable-Filter beibehalten).
- **Real Odds (mehrsprachige echte Quoten) — immer MongoDB**:
  - `/app/backend/real_odds.py` (Markt-Normalisierung über Sprachen: Über/Over/Más de/Üst/Più di… + `REAL_QUOTES_DB` + Persistenz-Helfer `snapshot_providers`/`hydrate`).
  - `/app/backend/ticket_collector.py` (Parser + Collectors: `ingest_instagram`, `ingest_experten`, `ingest_capella_scraper`, `universal_ticket_parser`). Quoten-Parser gefixt (nahm fälschlich Markt-Linie 0.5 statt @1.46).
  - Persistenz: MongoDB `real_quotes` (`{match, market, providers, updated_at}`); Startup-Hydration in `REAL_QUOTES_DB`.
  - API (Admin): `POST /api/odds/ingest` (source: raw|instagram|experten|capella), `GET /api/odds/quote`, `GET /api/odds/all`, `DELETE /api/odds/{match}/{market}`.
  - 2c: Win-Claim-Reader (`extract_win_slip`) füttert via `_auto_ingest_slip_odds` jeden echten Schein automatisch in die Odds-DB (anbieter=username, defensiv).
  - Hinweis: Top-Level-Module (nicht `core/`, da `core.py` schon existiert).
- **LLM-freie Schein-Annahme (Option A, Tesseract-Fallback)**:
  - `extract_win_slip` (server.py): zuerst Gemini Vision; wenn LLM-Budget leer / LLM aus / leeres Ergebnis → lokaler **Tesseract-OCR-Fallback** (`_ocr_tesseract`) → `parse_slip_text_to_legs` (Regex + `real_odds.normalize_market`). Kostet 0 Credits, kein LLM.
  - `parse_slip_text_to_legs`: stateful mehrzeiliger Parser (Team-Zeile + Markt-Zeile getrennt, überspringt Summenzeilen, strippt angehängte Quoten). Auch für Pipe-Format „Heim vs Gast | Markt | Quote".
  - `claim_win`: optionaler `slip_text`-Form-Param (Text-Einreichung möglich, aber KEIN Frontend-Button — vom Nutzer nicht gewünscht).
  - Deps: `tesseract-ocr` (System-Binary, in Preview via apt) + `pytesseract` (requirements.txt).
  - ⚠️ PRODUCTION-WARNUNG: Tesseract-System-Binary muss im Deploy-Image vorhanden sein. Kein Aptfile/Dockerfile im Repo → Emergent Support kontaktieren, ob `tesseract-ocr` in Production installiert ist, sonst greift der Fallback dort nicht.

## Changelog (Session 17.08.2026 — Homepage 6-Raster Migration)
- Homepage nach `/app/memory/pille.md` in modulare Raster überführt (alle 8-sprachig: de/en/es/el/fr/it/ar/tr).
- Neu gebaut & in `App.js` eingebunden:
  - `Raster2_Supporter.jsx` — 5 Supporter-Templates (XXL 119,99€ → S 9,99€), Bestseller-Badge, Instagram-Buchung. Platziert direkt unter Raster 1.
  - `Raster3_AiPicks.jsx` — hellblaues KI-Info-Raster + KI-Pillen kompakt 2-Spaltig (Single/grün, Smart/grün+„Mit der KI reden", Master/rot+Crown, Abgerechnet/weiß, Statistiken/rosa). Verdrahtet an `openTipsView(...)`.
  - `Raster4_Money.jsx` — „Willst du mit Wetten Geld verdienen?"-Text + Globale-Tipp-Community-Section (Badge/Headline/Body/Info-Box) + eingebettete `CoinBattery` + 2 Buttons (Tipp einwerfen / Münzen verdienen).
  - `Raster4b_CommunityLive.jsx` — Community Picks (gelb, links, mit blauem LIVE-Button) + Live KI Picks (blau, rechts, Wifi-Icon).
- Reihenfolge oben→unten: Raster1 → Raster2(Supporter) → Header(Nav) → CoinBattery → Raster3 → Raster4 → Raster4b → (Legacy Hero/Story/Invite/HallOfFame beibehalten) → Raster5 → Raster6 → Footer.
- Bestehende Header-Nav (`Raster2_Header`/QuickView-Pills), Hero, Story, InviteSection, HallOfFame NICHT entfernt (additive Migration, Homepage nicht gebrochen).
- Verifikation: sauberer Webpack-Compile (nur bestehende ESLint-Warnings), keine React-Runtime-Fehler in Konsole, `raster3-ai-picks` im DOM auffindbar. ⚠️ Kein sauberer Live-Screenshot möglich (Screenshot-Tool liefert bei dieser App nur den frühen Splash-PNG-Frame).

## Offene Tasks (nächste Session)
- P1: Feed-Limit auf 300 erhöhen + Community-Picks-Fallback in `backend/server.py` (`GET /api/feed`), damit Sektionen bei leerem KI-Feed nicht leer wirken.
- P1: Homepage-Raster visuell final abnehmen (User oder testing_agent).

## Backlog / offene Ideen
- P1: Sponsor-Klick-Verlauf als 14-Tage-Balkenchart.
- P2: Sponsor-Buttons automatisch nach Klicks sortieren.
- P2: Fliegende Boost-Münze auch in die CoinBattery integrieren.
- P2: Glitch-Muster tiefer in die algorithmischen Master-Combo-Builder einbauen (größeres Projekt).

## Test-Credentials
Admin: `admin@tipjar.com` / `TipJarAdmin2026!`
