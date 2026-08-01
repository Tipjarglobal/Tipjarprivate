# TipJar Global — CHANGELOG

## 2026-08-01 — Codemining: "Ρίζωσε" (Root note) + Anstoßzeit auf Karten
- **Root-Note-Knopf (Wand2):** Pro Karte (nur wenn eine Notiz existiert) + globaler Toolbar-Knopf "Notizen einwurzeln (n)". Backend: `POST /admin/code-reading/{id}/root-note` und `POST /admin/code-reading/root-notes` (bulk, alle aktiven Reads mit Notiz).
  - Wurzelt die Owner-Notiz FEST in den Read ein: our_market/read werden final, `pattern="rooted"`, `rooted=True`, `verified=True`.
  - **Beschreibung wird via LLM sauber neu geschrieben** (`_polish_code_reason`, Gemini, base German) — aus grober Handnotiz wird professionelle 1-2-Satz-Begründung. Fallback ohne LLM: bereinigte Notiz.
  - Notiz-Record wird gelöscht → StickyNote-Badge verschwindet, sieht native aus.
  - `_purge_and_refresh_code_reads` überspringt jetzt `rooted=True` Reads (Lock — nie mehr re-interpretiert).
- **Anstoßzeit + Liga** werden jetzt auf jeder Codemining-Karte angezeigt (Clock-Icon + kickoff · league).
- Getestet (curl e2e): manueller Read → grobe Notiz "…over 1.5 easy" → Root → sauberer DE-Text, note weg, rooted/verified True, our_market erhalten ✅. Frontend kompiliert & rendert ✅.


## 2026-08-01 — FIX: Black Screen im Code-Mining-Tab (P0)
- **Ursache:** `CodeReading.jsx` nutzte die Icons `FlaskConical` (Demo) & `StickyNote` (Notiz), importierte sie aber nie → `ReferenceError: FlaskConical is not defined` beim Rendern der Karten → kompletter React-Crash, ausschließlich auf dem Code-Mining-Tab. (Regression aus dem Notiz/Demo-Feature, nicht Service-Worker.)
- **Fix:** Beide Icons dem lucide-react-Import (Zeile 2) hinzugefügt.
- Verifiziert per Screenshot: Login als Admin → Code Mining → Aktiv- + Beendet-Tab rendern ohne Black Screen, keine Konsolenfehler.


## 2026-08-01 — Codemining: Notiz-System, Duplikat-Schutz, Demo-Schutz, Meta-Anzeige
- **Notiz-System (`code_notes`):** Notiz ist an den CODE-TEXT gebunden (normalisiert via `_code_note_key`). Wann immer genau dieser Code auftaucht (Scan ODER Sweep), überschreibt die Notiz automatisch den Pick — `our_market` ODER `No Bet` — + Begründung. Bleibt dauerhaft bis geändert/gelöscht. Endpoints: `POST /admin/code-reading/note` (upsert; leer = löschen), `GET /admin/code-reading/notes`, `DELETE /admin/code-reading/note/{key}`. Helper: `_lookup_code_note`, `_note_to_interp` (pattern `note_override`). Notiz wird bei `POST note` sofort auf offene Reads angewendet (via Sweep) und in `GET /code-reading` je Read als `note` mitgeliefert.
- **Duplikat-Schutz beim Upload:** Scan überspringt ein Leg, wenn bereits ein AKTIVER Read mit gleichen Teams (`_norm`) + gleichem Match-Datum existiert (statt vorher zu löschen+neu). Kein Duplikat.
- **Demo-Schutz:** Neuer `demo`-Flag + `POST /admin/code-reading/{id}/demo`. Wie der Haken schützt `demo=True` vor „Ungeprüfte löschen". clear-active überspringt jetzt `verified is True OR demo is True` (Projektion enthält beide Felder — Bug gefixt).
- **Meta-Anzeige:** Jede Karte zeigt jetzt 📅 Anstoß (Datum+Uhrzeit) · Liga.
- **Frontend:** pro Karte Admin-Buttons Notiz (StickyNote), Demo (FlaskConical), Haken (BadgeCheck); Notiz-Modal (Pick / No-Bet-Toggle / Begründung / Speichern / Löschen); DEMO- & Notiz-Badges. Labels DE/EN/EL.
- Getestet (curl): Notiz-Override no_bet→counter inkl. sofortiger Anwendung + `note` in Response ✅; Demo geschützt, Plain gelöscht ✅; Frontend kompiliert & rendert sauber. Duplikat-Skip-Logik implementiert (voll e2e erst bei echtem Bild-Upload prüfbar).


## 2026-08-01 — Codemining: Team-Total & Salzburg (nächstes Tor) → Asiatisch Über 2.0
- **Team-Total-Über-Code** (Team soll 2+ machen: „Gesamtzahl 1 Über 1.5", „Team 1 Über 1.5") → jetzt `Asiatisch Über 2.0 Tore` (Muster `match_over_asian2`) statt team-spezifischer „Unter 2.5"-Cap. Owner: keine Team-Tor-Wetten, v.a. nicht in Großbritannien. Ersetzt die alte Falkirk-Regel.
- **Salzburg-Regel (4× korrigiert):** „nächstes Tor / exaktes N-tes Tor / kein 4. Tor / next goal"-Code → `Asiatisch Über 2.0 Tore` (neue Branch (e0) in `_code_read_interpret`). Vorher „exaktes Tor → NO BET".
- Beide Muster (`match_over_asian2`) in `_REINTERP_RULES` → offene Reads self-healen beim Feed-Öffnen (Deploy nötig für Live).
- Verifiziert: alle Regeln getestet OK; DC/Handicap/über 2.5 → NO BET; Frontend kompiliert, Syntax OK.
- HINWEIS: `STRONG_FAVORITE_TEAMS` / „Favoriten-Whitelist + Odds-Check" eines anderen Agenten sind NICHT in dieser Umgebung (separater Fork).


## 2026-08-01 — Codemining: „Alle aktiven löschen"-Button + Herkunftsklärung
- **New:** `POST /api/admin/code-reading/clear-active` — löscht in EINEM Tap alle noch aktiven (unabgerechneten) Codemining-Reads. **Beendete/abgerechnete Reads bleiben unangetastet** (gleiche is_over-Logik wie `/code-reading`).
- **Frontend (`CodeReading.jsx`):** roter „Alle aktiven löschen"-Button rechts neben den Tabs (nur Admin, nur im Aktiv-Tab wenn Reads vorhanden), mit Bestätigungsdialog; Labels DE/EN/EL.
- **Herkunft der Codemining-Einträge geklärt:** Ganzer Backend-Code durchsucht — es gibt KEINEN Scraper/Seed für Codemining. Reads entstehen NUR durch (1) hochgeladenen Bookie-Screenshot (Vision-OCR) oder (2) manuelle Admin-Eingabe. Die vom Owner gesehenen Einträge (IK Start–Viking Stavanger, Cobresal–Union La Calera) waren NICHT in der Preview → sie liegen auf Production (tipjarglobal.com), vermutlich aus einem früheren Test-Upload eines Agents. Alter „+1.5/verzichten"-Text im Screenshot = alte, noch nicht neu deployte Logik.
- Getestet: clear-active gibt `{ok:true, deleted:0}` in Preview (7 beendete korrekt geschützt); Frontend kompiliert.

## 2026-08-01 — Codemining: glatter Sieg-Code → Draw No Bet (DNB)
- **New owner rule (Cobresal/Liberec):** A plain 1X2 WIN code no longer becomes "Underdog +1.5 / verzichten".
  - **Fall A** — code backs a team to WIN (S1/S2/Heimsieg/Auswärtssieg/"gewinnt") → OUR pick = `<that team> Draw No Bet (DNB)` (they won't lose; a draw returns the stake). Pattern `straightwin_dnb`.
  - **Fall B** — pure Double Chance (1X / X2 / Doppelte Chance / "gewinnt nicht") → **NO BET** (gegen X2 zu gehen ist Risiko). Unchanged, via `_code_read_interpret` (e)-branch.
- **Grading (`_grade_code_our_market`):** DNB → team wins = `won`, draw = `push` (Einsatz zurück), team loses = `lost`. `settle_code_reads` now treats `push` as a terminal outcome.
- **Frontend (`CodeReading.jsx`):** new `push` verdict chip "EINSATZ ZURÜCK" (sky/blue); Check icon for CORRECT/push, X only for UNCORRECT; DE/EN/EL example texts updated to DNB; fixed duplicate closing lines that broke the ESLint build.
- The **7 finished (Beendet)** code_reads from yesterday were **NOT touched** (they have `outcome` set → skipped by settler & sweep). No demo data is seeded into the active feed.
- Files: `/app/backend/server.py` (`_code_straightwin_decision`, `_grade_code_our_market`, `settle_code_reads`), `/app/frontend/src/components/CodeReading.jsx`.
- Tested: Python unit tests (interpret + grading won/push/lost) all pass; DC→NoBet confirmed; frontend compiles & Codemining page renders.
