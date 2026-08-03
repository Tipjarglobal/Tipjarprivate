# TipJar Global — CHANGELOG

## 2026-08-02 — Single-KI: keine Klone, Handicap-Gate, richtiger Zähler, 24–72h auffüllen
Owner (Live-Screenshots): „3× Cruz Azul / 2× Seattle geklont, Zähler sagt 26 statt 5, Felder 24–48
& 48+ leer, -1.5 Handicap überall." Fixes:
- **Ein Pick pro Spiel (`_dedupe_hq_tips`)**: ALLE Kategorien (auch Gift/Mental/Banger/Avatar) eines
  Spiels werden zu EINEM Pick zusammengefasst — behalten wird die **höchste Quote** (Owner: „immer
  das höchste Risiko, die höchste Quote"). Läuft jetzt bei jedem Refresh (purge). Bug behoben:
  Projektion enthielt `market`/`league` nicht → Handicap-Regel lief nie.
- **-1.5 Handicap nur für bekannte Top-Teams** (`_is_marquee_handicap_league`): erlaubt in Top-5-
  Europa-Ligen + UEFA (Leverkusen ✓), entfernt in kleineren Ligen (Seattle/MLS ✗).
- **Zähler korrigiert**: `/tips/counts` zählt nur noch KOMMENDE, platzierbare Picks (kickoff ≥ −3h),
  nicht mehr angepfiffene/erledigte → passt zur Liste (26 → real).
- **24–48h / 48+ auffüllen** (`topmatch_lookahead_autopost`, 24–72h Horizont): ein sicherer Früh-
  Pick pro Spiel — NUR Qualität: UEFA Champions/Europa/Conference-League (inkl. Qualifikation) +
  Top-Ligen, geprüft per Land+Liga-Paar → KEINE unterirdischen Teams (Bhutan/Kambodscha/2. Ligen
  raus). Im Scheduler (HQ-Loop C) + Reset-Regen registriert.
- Verifiziert: Cruz-Azul-Klone → 1 Pick (höchste Quote), Seattle-Handicap entfernt/Leverkusen behalten,
  Lookahead lässt nur UEFA-Quali + Top-Ligen durch.


## 2026-08-02 — Safety-Picks aus Systemen entfernt → Master „Einfach" = 8er Sicher-Mix + Codemining
Owner: „Lösche die Safety-Picks aus den System-Picks (nie wieder anzeigen). Der Master soll solche
Scheine im Easy-Bereich posten — aber 8 Spiele, nicht 4. Gemischt, kein Lotto, immer Codemining."
- **Beide Safety-Systeme entfernt**: „Sicherheits-Kombi des Tages" (lock) UND „TipJarLogic
  Sicherheits-Kombi" (tjlogic) werden in `build_systems` nicht mehr erzeugt; bestehende
  `hqsys-lock-*`/`hqsys-tjlogic-*`-Tipps aus der DB gelöscht. `/systems` verifiziert ohne Safety.
- **Master „Einfach" neu (`master_easy_build`)**: ersetzt den alten 2–4-Spiele-~3.0-Einfach durch
  einen **8-Spiele-Sicher-Mix** mit gemischten sicheren Märkten: Tor 1./2. Halbzeit, Team trifft
  (Über 0.5), **Doppelte Chance NUR wenn ein Ergebnis praktisch unmöglich** (kein Lotto — Basel-1X-
  Lehre), Bet-Builder „Unter 2.5 1.HZ + Über 0.5", Value/Geschenk (BTTS/Über 2.5). **Zieht IMMER
  zuerst die Codemining-Beratung** (aktive Codemines mit ★ zuerst). Teilt NIE ein Spiel mit einem
  anderen offenen Master-Schein. Alte Einfach-Scheine werden beim Bau ersetzt. Im Scheduler +
  Reset-Regen registriert.
- Settlement: Mehrfach-Selektion-Beine (Bet-Builder) + HZ-Märkte werden von `settle_multimatch_parlays`
  korrekt Bein-für-Bein abgerechnet. Verifiziert: 8-Bein-Mix inkl. 1× Codemine, Gesamtquote ~9.


## 2026-08-02 — Rescue-KOMBI: alle Rescues + Banger + Zehner in EINEM Schein
Owner: „Besser zusammenfassen als jeden einzeln posten — gib mir alle Rescues + 1 Banger + 1 Zehner,
dessen Spiel gleich anfängt." Umgesetzt in `code_live_autopost` / `_build_rescue_kombi`:
- Rescues werden NICHT mehr einzeln gepostet, sondern als LEGS gesammelt und in EINEN Live-Parlay
  gebündelt: **alle aktuellen Rescues (10★ Lead + 2★ Buzzer) + der beste Live-Banger + ein imminenter
  10★ Vor-Spiel-Pick (Anpfiff ≤ 60 Min)**.
- Nur EINE aktive Rescue-Kombi gleichzeitig (läuft bis zur Abrechnung, wie die Vierer-Live-Kombi);
  Settlement leg-für-leg über `settle_multimatch_parlays`. Alte Einzel-`crlive-*`-Tipps werden entfernt.
- Codemine-Karte behält die „🎯 RESCUE 10★ / 🚨 BUZZER 2★ / 🟥 {Team}"-Badges, damit sichtbar bleibt,
  welche Spiele in der Kombi stecken.
- Verifiziert (gemockt): 2 Rescues + 1 Banger + 1 Zehner (Anpfiff in 29 Min) → 4-Bein-Parlay,
  Gesamtquote 22.53, 10★, keine Einzel-Tipps.

## 2026-08-02 — Live-Codemine-Rescue-Engine (Basis)
- `code_live_autopost()` + Loop `code_live_loop`: 10★ Lead-Rescue (Team führt, keine rote Karte,
  Codemine sagt Tor voraus), 2★ Buzzer-Beater ab 75. Min (Counter braucht genau 1 Tor), Rote-Karte-
  Warnung aus Live-Statistik, Favorit/Underdog aus 1X2-Quoten. (Jetzt gebündelt, s.o.)



## 2026-08-02 — KI-Vorschlag: IMMER ein spielbarer Pick, nie „No Bet"
Owner: „Die Codemining-KI soll lernen wie WIR temporäre Optionen auswählen — wir tun das NICHT um
No Bets auszuwählen." (No Bet ist in der normalen Lesart legitim, z.B. das nötige blaue Rangers-1-1.)
- `_CR_SUGGEST_SYSTEM` neu geschrieben: eine temporäre Option ist IMMER genau EIN konkreter, spielbarer
  Gegen-Pick — niemals „No Bet"/„kein Muster". Die KI wählt die stabilste wiederkehrende ÜBER-/Gegen-
  Linie mit Sicherheitspuffer (Linie unter den kleinsten beobachteten Wert), bevorzugt Über-Torschüsse/
  Ecken/Tore/BTTS/Team-trifft. Wenn nur Endergebnisse (keine Detail-Statistik) vorliegen, wird die
  Option aus Toren/Torminuten abgeleitet; im Zweifel die plausibelste sichere Linie mit niedrigerer
  confidence. `no_bet` aus Endpoint-Antwort + Frontend entfernt (Pick wird immer angezeigt/übernommen).
  Verifiziert: Historie ohne Detail-Statistik (3-1/2-1/2-2) → Pick „Beide Teams treffen" statt No Bet.


## 2026-08-02 — Codemining: zwei Fallen-Muster korrigiert (Halbzeit-Nein + Gewinnspanne-Nein)
Owner (Live-Screenshots, Spinbetter-Scheine): die KI las zwei Fallen-Codes falsch herum.
- **„Tor in beiden Halbzeiten – Team X: Nein"**: Fallen-Logik → Team X trifft sehr wohl in BEIDEN
  Halbzeiten (≥2 Tore). Neuer Regel-Pick (`_code_read_interpret` pattern `both_halves_counter`):
  Haupt **„{Team} Über 1.5 Tore" ★9** + Alt **„{Team} trifft in beiden Halbzeiten"**. Vorher gab die
  Vision-KI fälschlich „{Team} Under 2.5" (widerspricht der Prämisse).
- **„Ein Team Gewinnspanne mit 2 (oder mehr) Toren – Nein"**: Fallen-Logik → eine Mannschaft gewinnt
  klar (2+ Abstand) → Unentschieden ausgeschlossen. Neuer Pick (pattern `margin_no_draw`):
  **„Doppelte Chance 12 (kein Unentschieden)" ★8**. Vorher fälschlich NO BET.
- Beide Muster sind (a) in `_REINTERP_RULES` → bestehende offene Reads werden bei jedem
  `/code-reading`-Refresh automatisch korrigiert (fixt die Live-Karten nach dem Deploy von selbst),
  und (b) in `_CODE_FORCE_RULES` → bei NEUEN Scans überschreibt die deterministische Regel die
  Vision-KI. E2E verifiziert: geseedete Philadelphia- & Chicago-Karten wurden über den echten
  Endpoint korrekt umgeschrieben. Settlement geprüft: „{Team} Über 1.5 Tore" (deterministisch),
  „Doppelte Chance 12" (dc_12 / judge_market) sind gradebar.

## 2026-08-01 — Codemines nach Startzeit + KI-Vorschlag + Live-Badge + Tablet-3-Reihen
- **Codemine-Sortierung repariert**: neuer robuster Parser `_cr_sort_dt` versteht die Scanner-Formate
  (`DD/MM HH:MM` ohne Jahr, `DD.MM. HH:MM`, nur `HH:MM`, ISO) → aktive Codemines jetzt wirklich
  chronologisch nach Anstoß. (Vorher scheiterte `_parse_kickoff` an diesen Formaten → keine Sortierung.)
- **Rote Live-Anzeige**: aktive Codemines mit laufendem Spiel bekommen ein kleines rot-pulsierendes
  Badge (Ergebnis + Minute), 1 gecachter `/fixtures?live=all`-Aufruf (60s), keine DB-Schreibvorgänge.
- **KI-Vorschlag im Code-Defaults-Panel** (Endpoint `/admin/code-reading/defaults/{key}/ai-suggest`):
  Historie gleicher Codes + echte Match-Statistiken (Heim/Gast getrennt, gecacht) → LLM findet Muster.
- **Tablet-Layout**: 9 Homepage-Knöpfe `md:grid-cols-3 xl:grid-cols-9` → 3 Reihen à 3 auf Tablets.
HINWEIS: greift auf tipjarglobal.com erst nach „Save to GitHub → Deploy".



## 2026-08-01 — Codemining: „Fertige abrechnen"-Knopf + Einzel-Settle
- Owner will fertige Codemining-Spiele manuell verschieben/abrechnen + fragte nach dem Kontroll-Panel.
- `_settle_one_code_read(r, now, cache, force=False)` aus `settle_code_reads` extrahiert (DRY). `force=True` umgeht das kickoff+2h-Gate.
- Neue Admin-Endpoints: `POST /admin/code-reading/{id}/settle-now` (ein Read) und `POST /admin/code-reading/settle-finished` (alle Reads mit bereits erfolgtem Anstoß → Beendet).
- Frontend: Toolbar-Knopf „Fertige abrechnen" (rot, `code-settle-finished-btn`) im Codemining (Admin).
- Getestet: settle-finished antwortet sauber `{ok, settled}`. Backend/Frontend kompilieren.
- Panel-Standort: Codemining-Tab → Toolbar → fuchsia Knopf „Code-Defaults" (nur Admin). Erscheint auf Prod erst nach Deploy.
- ⚠️ Wirkt erst nach Deploy auf tipjarglobal.com.


## 2026-08-01 — Gifts: ein Gift pro Spiel + bessere Halbzeit-Märkte (Owner-Wünsche)
- Owner sah 2 widersprüchliche Gifts auf DEMSELBEN Spiel („gewinnt mind. eine Halbzeit" @1.25 vs „gewinnt NICHT beide Halbzeiten" @1.55) — Lotto. Wollte: 1 Pick/Spiel + sinnvollere Märkte.
- **Neue, auto-abrechenbare Gift-Märkte** (`settlement.py` `_special_gift_kind` + `_grade_special_gift`):
  - `ht_win` „{Fav} gewinnt die 1. Halbzeit" (HT-Sieger)
  - `ht_ft` „{Fav} gewinnt 1. Halbzeit und Spiel" (HT-Sieger UND FT-Sieger)
  - `ht_combo` „1. Halbzeit unter 2.5 Tore & über 1.5 Tore im Spiel" (HT-Total<2.5 UND FT-Total>Linie)
  - benotet aus HT-/FT-Score, funktioniert auch für Auswärts-Favoriten (orient).
- **Generator** (`gift_specials_autopost`): postet jetzt genau EIN Gift pro Spiel (elif-Kette: ht_ft → ht_win → first_two → ht_combo). Die widersprüchliche half_any/not_both_halves-Ausgabe entfernt (Erkennung/Benotung bleibt für Altbestand). Kategorie bleibt `value`+`is_gift` → wird zusätzlich vom `_dedupe_hq_tips` (core) auf 1/Spiel reduziert.
- Verifiziert (Unit): Erkennung + Benotung aller neuen Märkte (won/lost/Auswärts-Fav) korrekt. Backend startet sauber.
- ⚠️ Wirkt erst nach Deploy; die 2 Duplikate auf Prod stammen aus altem Code ohne Dedup-Aufruf.


## 2026-08-01 — FIX: Single-Picks — nur EIN Pick pro Spiel (Risk > Value > Banker)
- Owner: dasselbe Spiel wurde 3-4× gepostet (Risk + Value + Banker) → Single-Tab überflutet. „Wenn du den Risk gegeben hast, ist fertig."
- **Ursache:** `_dedupe_hq_tips()` (a) deduplizierte absichtlich PRO Kategorie (`|{_cat}`), so blieb pro Spiel je ein Risk/Value/Banker; UND (b) wurde **nie aufgerufen** (toter Code).
- **Fix:**
  1. Dedup-Schlüssel auf „core" umgestellt: risk/value/banker eines Spiels kollabieren zu EINEM Pick; behalten wird das Größte (Rang Risk 3 > Value 2 > Banker 1, dann höchste Quote). Gifts/mental/banger bleiben separate Tabs.
  2. `await _dedupe_hq_tips()` in `master_loop` eingehängt (läuft alle 120s, DB-only, unabhängig vom API-Key) + Logging.
- Verifiziert (DB e2e): Spiel mit risk/value/banker → nur Risk überlebt; Gift bleibt; zusätzlich 7 echte Alt-Duplikate der Preview-DB entfernt.
- ⚠️ Wirkt erst nach Deploy; danach räumt der Loop den Bestand binnen ~2 Min auf.


## 2026-08-01 — Vierer-Live-Kombi jetzt VORMATCH (~25 Min vor Anstoß)
- Owner: die 4-Bein-Live-Kombi soll spielbar sein → nicht mehr aus laufenden Spielen (Linie schon erfüllt = nicht mehr wettbar), sondern **vor Anstoß**.
- Neu in `live_autopost()` (server.py): Kombi wird aus gespeicherten Forebet/Predictz-Vorhersagen (`match_predictions`, quota-frei) gebaut und gepostet, sobald das **früheste** gewählte Spiel ~25 Min vor Anstoß ist. Alle 4 Spiele liegen in einer **3h-Spanne** (Fenster ab dem Anchor).
- **Gemischte Märkte** (nicht nur Über 0.5): goal-heavy → „Über 0.5 Tore 1. Halbzeit" (1.44, frühe Entscheidung, bevorzugt); over2.5/total≥2.6 → „Über 1.5 Tore" (1.40); total≥2.0 → „Über 0.5 Tore" (1.10). Reihenfolge bevorzugt 1.-Halbzeit-Tor-Spiele (kein Zittern bis zur letzten Minute).
- Nur eine aktive Kombi gleichzeitig (`hqlive-kombi-*`); Abrechnung via `settle_multimatch_parlays` (HT-Over-Legs werden von `_grade_goal_leg`/`_grade_ht_selection` benotet).
- Verifiziert (Logik-Unit-Test): Anchor-Trigger 0–25 Min, 3h-Fenster-Filter, gestartete/zu weit entfernte Spiele raus, 4-fold mit gemischten Märkten @ ~3.28. Backend startet sauber.
- ⚠️ Wirkt erst nach Deploy auf tipjarglobal.com.


## 2026-08-01 — FIX (kritisch): Falsches Fixture beim Abrechnen (deutsche Torschützen auf SA-Spielen)
- Symptom (Prod): Gimnasia y Esgrima–Union de Santa Fe zeigte „2-1, Dynamo Dresden 22',52' · Union Berlin 19'"; Everton VdM–Colo-Colo „1-2, Hamburger SV 49' · Everton 40',90'+4" — Endstände FREMDER (deutscher) Spiele, obwohl die Spiele noch liefen.
- **Ursache:** `find_finished_fixture` (settlement.py) hatte einen Blind-Fallback „Team hat genau EIN beendetes Spiel am Tag → nimm es". Wenn `resolve_team_id` kollidiert (SA-Klub → deutscher Klub gleichen Namensteils), wurde dessen fremdes Spiel ohne Gegner-Check akzeptiert.
- **Fix:** Neuer Parameter `self_name` + `_self_ok()`: die Fixture-Seite mit `team_id` MUSS namentlich zum gesuchten Klub passen — sowohl im Match-Loop als auch im len==1-Fallback. An alle 5 Aufrufer übergeben (code-reading ×2, live-force ×1, settle_pending ×1, parlays ×2).
- Verifiziert: `_teams_match('Dynamo Dresden','Gimnasia…')=False`, `('Hamburger SV','Everton VdM')=False` → falsche Fixtures verworfen; `('Everton','Everton de Viña…')=True`, `('Colo Colo','Colo-Colo')=True` → legitime bleiben.
- Zusammen mit dem Timing-Gate (nie vor Anpfiff+2h abrechnen) ist der Wrong-Fixture-Bug beidseitig abgesichert. Bereits falsch abgerechnete Alt-Einträge müssen gelöscht werden / laufen aus (~30h).
- ⚠️ Wirkt erst nach Deploy auf tipjarglobal.com.


## 2026-08-01 — FIX: AI erfand „Hinspiel"/Qualifikation bei Liga-Spielen + „Spiel zuende" für alle Picks
- **Erfundenes Hinspiel (Ayr–Arbroath, Inverness–Dunfermline):** `_looks_two_legged()` prüfte u.a. das Keyword `"champions"` — das matcht `"Scotland Championship"`! Dadurch wurden reine LIGA-Spiele als zweibeinige Champions-League-Qualis behandelt und ein „Hinspiel-Aggregat" (letztes H2H als erstes Leg) erfunden → „X führt nach Hinspiel 2:0 / 0:0 im Hinspiel". 
  - Fix: `QUAL_KEYWORDS` präzisiert (`champions league`, `europa league`, `conference league`, `afc/caf/concacaf champions` …) + expliziter Ausschluss für `championship` / `league one` / `league two` / `1. lig`. Verifiziert: Scotland/England Championship → nicht zweibeinig; echte UEFA-Qualis/Play-offs → weiterhin zweibeinig.
- **„Spiel zuende" (Force-Settle) für ALLE Admin-Picks:** Der Knopf war in `RateWall.jsx` hinter `isCommunityLive` versteckt → bei Master/HQ-Picks nicht sichtbar. Jetzt für jeden Admin-Pick sichtbar (`admin-settle-now-{id}`). Backend-Endpoints existierten bereits: `PATCH /admin/tips/{id}` (Anstoßzeit via „Bearbeiten") + `POST /admin/tips/{id}/settle-now`.
  - Workflow: Pick → **Bearbeiten** (Anstoßzeit korrigieren) → Speichern → **Spiel zuende** (erzwingt Abrechnung).
- Backend startet sauber, Frontend kompiliert. ⚠️ Wirkt erst nach Deploy auf tipjarglobal.com.


## 2026-08-01 — Codemining: Zwei-Stufen-Defaults + Karten-Notiz nur pro Spiel
- **Karten-Notiz = nur dieses Spiel** (Wunsch A): Notiz auf einer Karte schreibt jetzt einen READ-LOKALEN Override (`ov_local`/`ov`) → KEIN Übertrag auf andere Spiele mit demselben Code. Endpoint `POST /admin/code-reading/{id}/override` (leer = Override löschen). Note-Badge/Editor lesen jetzt `r.ov_local`/`r.ov`.
- **Neues Panel „Code-Defaults"** (`CodeDefaultsPanel.jsx`, Button in Codemining-Toolbar): pro Code
  - **Temporär (experimentell):** mehrere gespeicherte Optionen (Pick/No-Bet/Notiz), eine ist aktiv → wird auf alle aktuellen & neuen Spiele mit dem Code angewendet (pattern `default_temp`, nicht gelockt), frei umschaltbar.
  - **Permanent (final):** „Einwurzeln" → wird finaler Default, auf alle Spiele gewurzelt + gelockt (pattern `default_perm`, `rooted=True`), überschreibt temporär.
  - Lokaler Karten-Override gewinnt über Defaults (bleibt pro Spiel).
- Backend: Collection `code_defaults` (`options[]`, `active_id`, `permanent`), Helfer `_code_default_lookup`/`_default_to_interp`; angewandt in Scan-Insert + `_purge_and_refresh_code_reads`. Endpoints: GET defaults, POST option (activate), POST activate, DELETE option, POST/DELETE permanent, DELETE default.
- Alte code_notes-Propagation (Root-Notiz/Bulk-Root) im UI durch das Panel ersetzt; Legacy-Endpoints bleiben unangetastet.
- Getestet (curl e2e): 2 Reads gleicher Code → temp aktivieren propagiert auf beide (nicht gelockt); 1 Read lokal auf No-Bet überschrieben bleibt lokal; permanent einwurzeln lockt die übrigen (rooted), Override bleibt bestehen ✅. UI: Panel öffnet als Admin ✅. Kompiliert sauber.
- ⚠️ Wirkt erst nach Deploy auf tipjarglobal.com.


## 2026-08-01 — FIX (Codemining): Noch-nicht-gestartete Spiele fälschlich "Beendet" mit falschem Endstand
- Symptom: Gimnasia–Union (20:30) & Everton VdM–Colo-Colo (21:00) standen um 19:52 unter "Beendet" mit Endständen FREMDER Spiele (deutsche Torschützen: Dynamo Dresden, Union Berlin, HSV).
- **Ursache:** In `settle_code_reads` diente `ref = ko or created_at` als "Spiel vorbei?"-Referenz. Bei UNPARSEBARER Anstoffzeit fiel es auf `created_at` zurück → ein vor Stunden erstellter Read wurde VOR Anpfiff bewertet und gegen ein falsches (bereits beendetes) Fixture gematcht.
- **Fixes (intern, kein Knopf):**
  1. `settle_code_reads`: parsebarer Kickoff muss >2h alt sein; unparsebarer Kickoff wird NICHT mehr über created_at gegradet — erst nach 18h. Kein Pre-Kickoff-Settlement mehr.
  2. `_purge_and_refresh_code_reads` (läuft bei jedem Feed-Öffnen): **Selbstheilung** — ein Read mit ZUKÜNFTIGEM Anstoß, der (fälschlich) score/outcome/settled_at trägt, wird bereinigt (`$unset`) + `cr_settle_attempts=0` → springt zurück nach Aktiv. Heilt die zwei kaputten Live-Einträge nach Deploy automatisch.
  3. `code_reading()`-Split: ein Spiel mit Anstoß in der Zukunft ist IMMER "Aktiv" (Sicherheitsnetz), nie "Beendet".
- Getestet (pymongo+curl e2e): Read mit Zukunfts-Kickoff + Bogus-Score → nach GET /code-reading Score/Outcome entfernt, in ACTIVE statt FINISHED ✅. Backend startet sauber.
- ⚠️ Wirkt erst nach Deploy auf tipjarglobal.com.


## 2026-08-01 — FIX (Backend/Web-Push): Bodø gestern + Aberdeen 3× Alarme
- Betraf den ECHTEN OS-Web-Push (`background_tasks.push_watch_loop`), NICHT das In-App-Board vom vorigen Fix.
- **Stale-Spiele (Bodø war gestern):** Bisher umgingen Picks OHNE saubere Anstoßzeit (Datum-only / unparsebar) den "noch spielbar"-Filter (`ko is None` → nicht geskippt). Neu: `_pick_still_playable(tp, now)` — Clock-Kickoff muss >= now-15min sein; reine Datum-only-Slips nur wenn der Spieltag heute/später ist; KEINE Zeit-Info → nicht pushen. Live-Picks brauchen jetzt einen echten Clock-Kickoff < 3h alt.
- **Aberdeen 3×:** Neu `_push_match_sig(tp, area)` (Teams/Parlay-Legs normalisiert) + Mongo-Collection `push_sent` (24h). Dasselbe Fixture+Bereich wird nicht mehr doppelt gepusht, auch wenn das Backend den Pick unter neuer id neu erzeugt.
- Unit-getestet (ISO/DD-MM-YYYY-HH-MM/„1. Aug 2026"): gestern/vergangen/keine-Zeit → False; heute/zukünftig → True; Parlay mit bereits gestartetem Bein → False; Sig-Gleichheit bei gleichem Match ✅. Backend startet sauber.
- ⚠️ Wirkt erst nach Deploy auf tipjarglobal.com.


## 2026-08-01 — FIX: Benachrichtigungen (Duplikate + Phantom-Alerts)
- **6× dasselbe Spiel (Aberdeen):** Dedup lief nur über `tip.id` → bei jeder Neu-Generierung desselben Spiels (neue id) feuerte eine neue Benachrichtigung. Neu: **match-level Dedup** (`notifSig` = area + normalisierte Teams / Parlay-Legs), persistiert in localStorage `tj_notified_sigs`, 24h-Fenster. Dasselbe Spiel+Bereich meldet sich nicht mehr doppelt. Greift in `fireAlert` + `fireAlertBatch`.
- **Live-Pick doppelt (Cobresal):** Live-Picks stecken in beiden Feeds (`?sort=new` UND `?status=live`). Section-1 überspringt jetzt `status==="live"` → nur der Live-Watcher meldet Live-Picks. Kein Doppel-Ring mehr.
- **Nur mit echtem Pick:** `fireAlert` bricht ab, wenn kein `tp.id` vorhanden (außer Systems-View). Klick auf Board-Eintrag springt via `tj-open-pick` zum Pick (App.js `jumpToPick`, mit "Pick nicht mehr verfügbar"-Toast als Fallback).
- Datei: `frontend/src/components/NotificationBell.jsx`. Kompiliert (nur vorbestehende exhaustive-deps-Warnungen). Bell-Panel + Board rendern ✅.
- Hinweis: bereits gespammte Alt-Einträge auf dem Gerät bleiben, bis "Alle löschen" getippt wird — der Fix verhindert NEUE Duplikate.


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

## 2026-08-03 — Glaskugel-Richtungsfix (P0)
- **Problem (seit ~1 Woche):** Die Codemining-"Glaskugel" (`ai-suggest`) drehte bei Sieg-, Zeitfenster- und Spätor-Märkten die Richtung falsch und sagte das Durchgestrichene als Vorhersage voraus. User-Beispiele Sirius / Cracovia / Celtic gingen alle verkehrt.
- **Owner-Logik (bestätigt):** Auf dem Buchmacher-Screenshot durchgestrichene Auswahl = passiert NIE. Der Code nennt das Ergebnis, das das Durchgestrichene verlieren lässt = was wirklich passiert. Glaskugel sagt IMMER das Gegenteil des Durchgestrichenen; darunter unser Tipp.
- **Fix:** `_CR_SUGGEST_SYSTEM`-Prompt + User-Message in `server.py` neu mit expliziter "durchgestrichen = passiert NIE"-Framing und 3 Pflicht-Beispielen (Sieg→X2, frühes Tor→Über 0.5 bis Min15, Spätor→Unter 0.5 letzte 10 Min). JSON-Ausgabeformat unverändert (Frontend rendert bereits prediction über our_market).
- **Getestet:** Direkter LLM-Lauf gegen alle 3 Fälle → alle jetzt richtige Richtung (Sirius "gewinnt nicht"→X2; Cracovia "Tor bis Min15"→Über 0.5; Celtic "nach Min80 nichts"→kein Tor letzte 10 Min). Backend /api/code-reading = 200.
- Datei: `/app/backend/server.py` (`_CR_SUGGEST_SYSTEM`, `admin_cr_default_ai_suggest`).

### Korrektur (Sieg-Doppelchance-Richtung)
- Owner-Hinweis: Sirius steht auf Position 2 (Gast). Durchgestrichener Sieger darf NIE in unserer Doppelten Chance vorkommen.
- Regel im Glaskugel-Prompt fixiert: S1 durchgestrichen -> X2; S2 durchgestrichen -> 1X. Getestet: Sirius(2)->1X, Heim(1)->X2. Beide korrekt.

### Korrektur 2 (Sieg-Codes = No Bet + Vorwarnung)
- Owner: 1X/X2 zu riskant. Bei glatten SIEG/1X2-Codes -> TipJar-Option = No Bet, aber Glaskugel gibt weiter Vorwarnung aus, WELCHES Team nicht gewinnt (Position 1/2 erkannt).
- Backend: _CR_SUGGEST_SYSTEM Sonderregel + ai-suggest liefert no_bet-Flag (our_market leer bei no_bet). Frontend CodeDefaultsPanel: No-Bet-Chip + applyAi setzt no_bet-Schalter.
- Getestet: Sirius(Pos2)->no_bet+Warnung, Heim(Pos1)->no_bet+Warnung, Cracovia->echter Tipp. Frontend compiled OK.
