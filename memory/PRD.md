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

## Backlog / offene Ideen
- P1: Sponsor-Klick-Verlauf als 14-Tage-Balkenchart.
- P2: Sponsor-Buttons automatisch nach Klicks sortieren.
- P2: Fliegende Boost-Münze auch in die CoinBattery integrieren.
- P2: Glitch-Muster tiefer in die algorithmischen Master-Combo-Builder einbauen (größeres Projekt).

## Test-Credentials
Admin: `admin@tipjar.com` / `TipJarAdmin2026!`
