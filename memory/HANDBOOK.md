# 📘 TipJar Global — AGENTEN-HANDBUCH (bitte VOR jeder Arbeit lesen)

> Zweck: Der Owner will KEINE Anfängerfragen mehr. Alles Nötige steht hier. Latest Owner-Regel gewinnt immer.

---

## 0) ⚠️ DIE 7 WICHTIGSTEN REGELN FÜR DEN AGENTEN
1. **Sprache: IMMER Deutsch** antworten. Der Owner spricht Deutsch.
2. **KEINE Rückfragen zu Umfang/Wortlaut/„ersetzen ja/nein".** Owner gibt eine Codemining-Regel → SOFORT umsetzen. Die neueste Regel gewinnt immer, auch wenn sie einer älteren widerspricht.
3. **Zwei Umgebungen:** Du arbeitest in der **PREVIEW**. Der Owner schaut fast immer auf **PRODUCTION = https://tipjarglobal.com** (Live). Änderungen erscheinen dort ERST nach **„Save to Github → Deploy"**. Wenn der Owner sagt „geht nicht/ist falsch" → zuerst prüfen: schaut er Preview oder Live? Meistens Live + nicht neu deployt.
4. **Keine Demo-/Beispiel-Einträge im Codemining.** Nie hochladen, nie seeden. Beendete Reads NIE anfassen.
5. **Codemining-Text-Mappings sind Gesetz.** Nicht „schlauer" machen, nicht eigene Logik drüberlegen.
6. **Keine „Lotto"-Picks** (generische glatte Siege ohne Edge, willkürliche „Unter 3.5"-Polster).
7. **Nur Fußball. Keine russischen Spiele** (Boykott — Russland/Moskau/etc. sind geblacklistet, auch in OCR-Übersetzungen).

---

## 1) WAS IST DIE APP?
**TipJar Global** — eine KI-gestützte Sportwetten-Tipp-Plattform (PWA). Kernbausteine:
- **TipJarMaster / TipJarHQ**: automatische KI-Tipp-Generierung (Bet-Builder, Kombis, Value-Picks).
- **Codemining** (Herzstück): Der Owner lädt Screenshots von **Trap-Buchmacher-Scheinen** hoch (z.B. „Akku des Tages", Boost-Angebote von Anbietern, die den Spieler in die Falle locken — NICHT Bet365). Die Vision-KI liest den Schein per OCR und spielt bewusst **DAGEGEN** (Counter-Pick) oder gibt **NO BET**.
- **Master Avatar**: zeigt Top-Picks (2 pro Ansicht, manuelles Wischen, nie vergangene Spiele; Teams/Liga/Datum/Uhrzeit).
- **Settlement-Engine**: rechnet Tipps automatisch gegen echte Ergebnisse via **API-Football** ab.
- **Mehrsprachig**: Basissprache Codemining = Englisch, Auto-Übersetzung nach Deutsch/Griechisch je nach User-Sprache.

---

## 2) TECH-STACK & ARCHITEKTUR
- **Frontend**: React PWA (`/app/frontend`), craco, TailwindCSS, shadcn/ui, lucide-react, sonner (Toasts).
- **Backend**: FastAPI (`/app/backend`), alle Routen mit **`/api`**-Prefix (Kubernetes-Ingress).
- **DB**: MongoDB (via `MONGO_URL`, `DB_NAME` aus `backend/.env`).
- **Hosting**: Kubernetes, Supervisor-managed. Backend intern `0.0.0.0:8001`, Frontend `3000`. Hot-Reload aktiv.
- **URLs/Secrets**: NUR aus `.env`. Frontend nutzt `process.env.REACT_APP_BACKEND_URL`. NIE hardcoden.

### Wichtige Dateien
- `/app/backend/server.py` — **Riesig (>12,5k Zeilen)**. Enthält: KI-Generierung, Master-Loops, **Codemining-OCR + Interpret-Logik**, Auto-Übersetzung, alle Endpoints. Bei Regex-Änderungen in `_code_read_interpret` VORSICHTIG sein (Nachbarregeln nicht brechen).
- `/app/backend/settlement.py` — Grading/Abrechnung, API-Football-Events, `judge_market`.
- `/app/backend/learning.py` — KI-Gedächtnis/Veto-Logik (Trefferquote je Muster).
- `/app/backend/match_stats.py` — H2H, Europapokal-Müdigkeit, Formanalyse.
- `/app/frontend/src/components/CodeReading.jsx` — Codemining-UI (Karten, Verdicts, Haken, Löschen).
- `/app/frontend/src/components/MasterAvatar.jsx` — Avatar-Sprechblasen.
- `/app/frontend/src/components/AdminResetBar.jsx` — Homepage-Reset für Pregame-Slips.
- `/app/frontend/src/App.js`, `/app/frontend/src/i18n.js` (Übersetzungen).

### Wichtige Endpoints
- `GET /api/code-reading` — liefert `{count, reads (aktiv), finished (beendet)}`. Ruft beim Öffnen automatisch das **Self-Healing** auf.
- `POST /api/admin/code-reading/scan` — startet Vision-OCR-Scan aus hochgeladenen Bildern (async Job). Neue Reads bekommen automatisch `verified: True`.
- `GET /api/admin/code-reading/scan-status/{job_id}`
- `POST /api/admin/code-reading/manual` — manueller Einzel-Read (bleibt `verified` = false).
- `DELETE /api/admin/code-reading/{id}` — Einzel-Read löschen.
- `POST /api/admin/code-reading/{id}/verify` — „Geprüft"-Haken toggeln (Body `{verified: bool}`).
- `POST /api/admin/code-reading/clear-active` — ALLE aktiven Reads löschen (beendete bleiben).
- `GET /api/master/avatar` — Avatar-Picks.
- `POST /api/admin/pregame/regenerate` — Pregame-Slips neu generieren.
- `GET /api/learning/stats` — ehrliche Trefferquote je Muster/System.
- `POST /api/admin/learning/refresh` — Settlement + Learning refresh.

### DB-Schema (grob)
- `tips`: {id, status, kickoff, category, is_parlay, legs[], master_category, combo_odds, admin_edited, source, from_codemining, ...}
- `code_reads`: {id, home, away, league, kickoff, **code_market** (Original-Code), **our_market** (unser Pick), **read** ("counter"|"no_bet"), reason, **pattern**, stars, **outcome** ("won"|"lost"|"push"|"info"), score, goal_minutes, code_outcome, **verified** (bool), created_at, expires_at}

---

## 3) CODEMINING-PHILOSOPHIE (Owner-Denke)
Trap-Scheine sind gebaut, damit DU verlierst. Wir lesen jeden Leg und nehmen die **sichere Gegen-Lesart** — oder NO BET. Wichtig: **nur Trap-Anbieter hochladen, NIE Bet365** (deren Quoten sind fair). Es geht NICHT um Quoten, sondern zu verstehen, wie die anderen Buchmacher denken.

### 🎯 DIE CODE→PICK-REGELN (aktueller, gültiger Stand — genau so umsetzen)
| Code des Trap-Buchmachers | UNSER Pick |
|---|---|
| **Glatter Sieg / 1X2 / „Team gewinnt" / S1 / S2 / Heimsieg / Auswärtssieg** | **`<dieses Team> Draw No Bet (DNB)`** (verliert nicht; Remis = Einsatz zurück) |
| **Doppelte Chance (1X / X2) / „Team gewinnt nicht"** | **NO BET** (dagegen = X2 spielen = Risiko) |
| **Handicap (glatt, z.B. -1.5)** | **NO BET** |
| **Team-Total Über (Team soll 2+/3+ machen, „Gesamtzahl 1 Über 1.5", „Team 1 Über 1.5")** | **`Asiatisch Über 2.0 Tore`** (keine Team-Tor-Wetten, v.a. nicht in Großbritannien) |
| **Match „über 3.5 Tore" / „genaue Zahl N oder weniger – Nein" (N≥3.5)** | **`Asiatisch Über 2.0 Tore`** |
| **Match „über 1.5 Tore"** (bzw. „genaue Zahl 1 oder weniger – Nein") | **`Über 1.5 Tore` BEHALTEN** (sauberste sichere Linie) |
| **Match „über 2.5 Tore"** | **NO BET** (zu locker) |
| **Nächstes Tor / exaktes N-tes Tor / „kein 4. Tor" (Salzburg-Typ)** | **`Asiatisch Über 2.0 Tore`** |
| **Team trifft NICHT („Über 0.5 – Nein", Clean Sheet)** | **`<Team> trifft (Über 0.5 Tore)`** / BTTS |
| **Tor in engem Zeitfenster (z.B. 46–60 Min)** | **`<Team> Über 0.5 Tore`** (breiter, sicher) |
| **Frühes Remis / Ergebnis in 15./20./30. Min** | **`Über 0.5 Tore 1. Halbzeit`** |
| **Team trifft SPÄT (letztes Tor 55–90 / 2. HZ)** | **`<Team> trifft bis zur 60. Minute`** |
| **Verschachtelte DC-Kombi (1X/X2 + Total), z.B. Everton–Colo Colo** | **`<Team> +2.5 (Handicap)`** |
| **Underdog +1/+1.5 Handicap** | **`<Favorit> -1 (Handicap)`** (2+ = gewonnen, genau 1 = Push) |
| **„Team nicht zweimal treffen"** | **`<Team> Unter 2.5 Tore`** |

**Asiatisch Über 2.0 Tore Grading:** 3+ Tore = **gewonnen**, genau 2 Tore = **Push (Einsatz zurück)**, ≤1 = verloren. Sehr sicher (~1.20).
**DNB Grading:** Team gewinnt = gewonnen, Remis = **Push**, Team verliert = verloren.

> Der Owner sieht Asiatisch Über 2.0 gern als „safe Default" statt NO BET (siehe seine Nachricht). Wenn ein Code Tore erwartet und kein sauberer team-spezifischer Counter passt → Asiatisch Über 2.0.

### Self-Healing (WICHTIG gegen „ich hab's korrigiert, es bleibt trotzdem")
- `_purge_and_refresh_code_reads()` läuft bei jedem Öffnen von `/api/code-reading`.
- Es re-interpretiert **offene** (unabgerechnete) Reads neu, WENN das frische Muster in **`_REINTERP_RULES`** steht (u.a. `match_over_asian2`, `match_over_clean`, `team_total_over_counter`, `team_not_twice`, `goal_window_broaden`, `underdog_plus15_fav_minus1`, `team_total_under_low`).
- Es überspringt: abgerechnete Reads (haben `outcome`), und `_is_straightwin_code`-Codes (die laufen über `_code_straightwin_decision` = DNB).
- ⚠️ Wenn eine neue Regel greifen soll, MUSS ihr Muster in `_REINTERP_RULES` sein, sonst aktualisieren sich alte Einträge nicht.
- Neue Regeln greifen auf Live erst **nach Deploy**.

### Verdict-Farben (CodeReading.jsx, Beendet-Tab)
- Counter **gewonnen** → grün „CORRECT"
- Counter **verloren** → rot „UNCORRECT"
- Counter **Push** (DNB-Remis / Asian genau 2) → himmelblau **„EINSATZ ZURÜCK"**
- NO BET, Trap-Code kam NICHT → blau „CORRECT" (uns gerettet)
- NO BET, Trap-Code KAM doch → orange „UNCORRECT"

### „Geprüft"-Haken (verified)
- Admin kann pro Karte (aktiv + beendet) einen grünen Haken toggeln (`BadgeCheck`).
- **Screenshot-Uploads** bekommen den Haken **automatisch** (`verified: True`).
- **Manuelle** Einträge bleiben ungeprüft, bis der Admin sie abhakt.

---

## 4) INTEGRATIONEN
- **API-Football** — braucht `API_FOOTBALL_KEY` (Owner-Key). Für H2H, Form, Europapokal-Müdigkeit, Fixture-Lookup, Settlement. Quota-geschützt (Batch-Caps, Retry-Budget).
- **Emergent LLM Key** — Gemini (Vision-OCR für Codemining + Textgenerierung). NIE eigene SDKs installieren; über die Emergent-Integration.
- Weitere Scraper (Telegram-Kanäle, Totis Sports, Forebet, Predictz, Statarea) füttern NUR den normalen Tipp-Feed / Bot-Tipster / Master — **NICHT** das Codemining.

---

## 5) UMGEBUNGEN & DEPLOYMENT (der häufigste Reibungspunkt!)
- **PREVIEW** = Entwicklungsumgebung des Agents. Hier testen/ändern.
- **PRODUCTION** = **https://tipjarglobal.com** (Live). Der Agent hat KEINEN direkten Zugriff auf die Live-DB.
- Ablauf, damit Änderungen live gehen: **„Save to Github → Deploy"** (dauert ~10–15 Min).
- Live-DB-Daten (z.B. ein alter Salzburg-Eintrag) heilen sich nach Deploy beim Öffnen des Feeds selbst — sofern die Regel + Muster in `_REINTERP_RULES` deployt sind.
- Bei reinen Production-Themen (Env-Var, Domain) → Emergent Support (support@emergent.sh).

---

## 6) ADMIN-ZUGANG (Test)
- E-Mail: `admin@tipjar.com`
- Passwort: `TipJarAdmin2026!`
(Auch in `/app/memory/test_credentials.md`.)

---

## 7) OFFENE / GEWÜNSCHTE FEATURES (Backlog)
- **Telegram-Auto-Post**: jeder neue Master-Slip, Avatar-Pick, Gift automatisch in einen Telegram-Kanal.
- **Lotto-Filter verschärfen**: „Team Über 0.5" nach echter Tor-Wahrscheinlichkeit filtern; „Unter 3.5/4.5"-Polster aus Same-Game-Buildern raus.
- **Stripe-Zahlungen & PayPal-Auszahlungen**.
- **Live-Picks** („nächstes Team das trifft", „3+ Ecken nach 70. Min") — blockiert bis Settlement zuverlässig.
- **Haken-Filter**: Aktiv-Tab optional nur geprüfte Codes zeigen.

---

## 8) ARBEITSWEISE, DIE DER OWNER ERWARTET
- Regel bekommen → **direkt im Code umsetzen** (meist in `_code_read_interpret` / `_code_straightwin_decision` in `server.py`), testen (`python3 -c` gegen die Interpret-Funktion), fertig.
- Muster ggf. in `_REINTERP_RULES` aufnehmen, damit bestehende Einträge self-healen.
- Danach den Owner erinnern: **auf tipjarglobal.com erst nach Deploy sichtbar.**
- Keine langen Rückfrage-Ketten. Bei echter Mehrdeutigkeit: EINE präzise Frage, sonst sinnvolle Annahme + später nachjustieren.
- Nichts an beendeten Codemining-Reads oder an der Preview/Prod-Konfiguration kaputt machen.
