# TipJar Global — PRD (Kurzfassung)

> Vollständige Produktregeln & Historie: `/app/tipjar.md`, `/app/BRAIN.md`, `/app/MEMORY.md`.
> Sprache des Nutzers: **Deutsch** — alle Antworten auf Deutsch.

## Produkt
Sports-Betting-/Tip-Community-PWA. React (frontend) + FastAPI (backend) + MongoDB.
Features: AI-Combo-Generierung & OCR (Gemini via Emergent LLM Key), Live-Settlement-Loops,
30-Tier Coin-Jar-System, i18n (8 Sprachen), Sponsor-Feeder, Coin-Battery, JarDex/Open Case.

## Umgebungen
- PREVIEW (dev): Arbeitsumgebung des Agents.
- PRODUCTION: https://tipjarglobal.com — Änderungen erfordern Redeploy durch den Nutzer.
- Git: kein remote pull/push im Container; Nutzer lädt `.txt`-Dateien hoch bzw. nutzt „Save to GitHub".

## Wichtige Constraints
- Keine automatisierten Massentests (Credits sparen). Nur curl + einzelner Smoke-Screenshot.
- Keine neuen Dependencies ohne Grund. Direkt Dateien überschreiben, kein Refactoring.

## Changelog (diese Session, 16.08.2026)
- 28 Jar-PNGs via `install_all_jars.sh` nach `/app/frontend/public/jars/` installiert.
- Sponsor-Feeder: 2 Sponsoren ergänzt (BETSCORE, SGCASINO) → 7 gesamt.
- Sponsor-Klick-Tracking: `POST /api/sponsors/{id}/click` (Event-basiert, Bots/Crawler ausgeschlossen,
  Admin zählt jetzt mit) + `GET /api/admin/sponsor-stats?period=today|7d|all` (nur Admin).
  Ranking-UI in `SecretInsights.jsx` (`/insights`) mit Zeitraum-Filter.
- Jar-Tabs bereinigt:
  - `ProfileModal.jsx`: nur 2 Tabs (Profil | Sammlung), oberer Open-Case-Tab entfernt.
  - `JarDex.jsx`: neu gebaut aus `JAR_DEFS` — echte PNGs in Inventory/JarDex/Open-Case, keine `???`,
    keine Dev-Notizen. Inventory=closed front, Open-Case=`graphicOpen||graphic`.
  - `OpenCase.jsx`: Dev-Notiz raus, Spieler-Hinweis oben.
  - Backend `/jars/opencase`: `jar_ids` jetzt `List[str]`; Register-Default `["common_glass"]`.
- `AnimatedJar.jsx`: frühere Homepage-Version wiederhergestellt (schwebendes Wappen + Glas mit
  Füll-Animation + fallende Münzen beim Boost + Fortschrittstext). Exportiert weiter `JAR_DEFS`/`getJarForCredits`.

## Backlog / offene Ideen
- P1: Sponsor-Klick-Verlauf als 14-Tage-Balkenchart.
- P2: Sponsor-Buttons automatisch nach Klicks sortieren.
- P2: Fliegende Boost-Münze auch in die CoinBattery integrieren.

## Test-Credentials
Admin: `admin@tipjar.com` / `TipJarAdmin2026!`
