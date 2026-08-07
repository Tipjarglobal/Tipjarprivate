# TipJar Global — CHANGELOG

## 2026-08-03 — Geteiltes Ticket: Land, Teamnamen, Stürmername
Owner-Screenshot: geteiltes Ticket ohne Land, Teamnamen zu blass, Markt abgeschnitten (Robbie Ure fehlte).
- `ticket_render.py`: Render-Legs tragen jetzt `country`; Meta-Zeile zeigt „Land · Liga · Datum · Zeit".
  Markt-Schrift wird per `fit()` auf 36→22 verkleinert, um den vollen Text (inkl. Spielername) zu zeigen
  statt hart abzuschneiden. Teamtitel etwas größer (44→46/34).
- `server.py` `_enrich_legs_country`: füllt fehlendes Land/Liga der Legs quota-frei aus
  `match_predictions` (Token-Overlap-Match), aufgerufen vor jedem Ticket-Render. `_pretty_country`
  wandelt ISO-Codes um (dk→Denmark …).
- Verifiziert per gerendertem Ticket (Halmstad–Sirius … Djurgården): Teamnamen groß, „Sweden ·
  Allsvenskan · 03.08 · 17:00", und „Anytime Goalscorer o. Ersatzspieler — Robbie Ure" komplett sichtbar.


## 2026-08-03 — Durst-Kanal: ALLE durstigen Teams im 7-Tage-Fenster
Owner: „Ich will in der Statistik ALLE durstigen Teams im 7-Tage-Fenster gelistet."
- `server.py` `goal_thirst`: Ausgabe-Truncation entfernt (kein `[:80]`/`>=80`-Break mehr) → liefert
  ALLE gefundenen Durst-Teams; Kandidaten-Pool auf 600 erhöht; Sortierung jetzt chronologisch nach
  Kickoff (frühestes zuerst). 7-Tage-Fenster (`now-2h … now+7d`) unverändert.
- `warm_goal_thirst_cache`: Standard-Cap 20→40; bricht NICHT mehr bei einem einzelnen API-Leerergebnis
  ab (nur `_api_quota_exhausted` stoppt) → füllt den Form-Cache pro 15-Min-Zyklus deutlich schneller.
- Verifiziert: Warmer 40/Lauf, `team_form_cache` 54→102, Durst-Kanal 3→20 Teams (wächst weiter bis alle
  7-Tage-Durst-Teams gecacht sind). Frontend `GoalThirst.jsx` listet ohne Client-Cap.


## 2026-08-03 — Durst-Kanal: mehr Teams melden
Owner: „Melde bitte mehr Teams im Durst-Kanal." Engpass war nicht der Cap, sondern der Form-Cache:
~153 Kandidaten, aber nur ~54 im `team_form_cache` → 99 „unbekannt" → übersprungen (pro Seitenaufruf
nur 12 API-Checks).
- `server.py` `goal_thirst`: Ausgabe-Cap 40→80, Kandidaten 200→300, API-Budget pro Aufruf 12→28.
- NEU `warm_goal_thirst_cache(cap=20)` (im `settlement_loop`, alle 15 Min, rate-capped): füllt den
  Form-Cache für kommende Durst-Kandidaten vor → der Kanal zeigt ALLE echten Durst-Teams, nicht nur
  die pro Seitenaufruf API-prüfbaren. 12h-Cache begrenzt die API-Kosten.
- Verifiziert: nach Warmen stieg der Durst-Kanal von 3 → 9 Teams (wächst weiter, während der Cache
  über die Loop-Zyklen warm wird). Endpoint 200.
Hinweis: Vom Nutzer hochgeladener „TipJar Logic"-Schein liegt in der PROD-DB (tipjarglobal.com) —
aus der Preview nicht einsehbar.


## 2026-08-03 — Echte Anstoßzeit auch in der Statistik (API-Football)
Folgeauftrag: date-only Statistik-Spiele (Sentinel) sollen die echte Zeit bekommen, nicht nur das Datum.
- Neuer `resolve_prediction_kickoffs(cap=12)` in `server.py`: löst `match_predictions` mit unbekannter
  Zeit über API-Football auf (echte Kickoff-Zeit + Land + Liga), in-place → alle Statistik-Endpoints
  zeigen sofort die echte Zeit. Rate-capped, je Vorhersage max. alle 6h (`ko_resolve_at`).
- Guard: NUR heute/zukünftige Spiele werden aufgelöst (`_ko.date() < now.date()` → skip), damit ein
  vergangenes date-only Spiel NICHT auf ein zukünftiges Rückspiel gemappt wird.
- `store_match_prediction`: aufgelöste Zeit/Land (`ko_fixed`) wird beim nächsten Scrape NICHT mehr mit
  dem date-only-Wert überschrieben.
- Aufruf im `settlement_loop` neben `resolve_unparseable_kickoffs`.
- Verifiziert: echte Preds bekamen echte Zeit+Land+Liga (z.B. Scotland Championship); Guard-Test:
  vergangenes „1. Aug"-Spiel übersprungen, Backend/Frontend gesund.


## 2026-08-03 — P0: 01:59-Sentinel auch in den Statistik-Karten behoben
Owner: „In der Statistik fangen viele Spiele um 01:59 nachts an — heißt das, du kennst die Kickoff-Zeit
nicht und schreibst immer die Standard-Uhrzeit?" → Genau: 23:59 UTC ist der „Zeit unbekannt"-Sentinel,
lokal = 01:59. Der frühere `kickoffInfo`-Fix deckte nur die Tip-Karten ab; die Statistik-Karten haben
eigene lokale Formatter.
Fix: neuer Helper `isKickoffTimeUnknown(iso)` in `i18n.js` (erkennt 23:59-UTC). Angewandt in
`GoalThirst.jsx`, `HtGoals.jsx`, `ScorerRadar.jsx`, `SecretInsights.jsx` → bei unbekannter Zeit wird
nur das Datum (bzw. gar keine Zeit) gezeigt, nie mehr die falsche ~01:59-Nachtzeit. Echte Zeiten
(z.B. 19:30) unverändert. Per Node verifiziert, Frontend kompiliert.


## 2026-08-03 — Legs zeigen Land, Liga, Live-Ergebnis & echte Teamnamen
Owner (Live-Screenshot Melbourne/Atlet): fehlendes Live-Ergebnis + kryptische Namen „Atlet – Rebel".
Anforderung: jede Karte/jedes Leg muss Land, Liga, Datum, Kickoff, Live-Ergebnis, echte Teamnamen
zeigen — keine Duplikate.
- Backend (`server.py`): neue `_live_annotate_tips` (in `list_tips`) — ein gecachter
  `/fixtures?live=all`-Call (geteilter 60s-Cache mit den Codemines). Reichert JEDES Feed-Pick + jedes
  Parlay-Leg, dessen Spiel gerade live ist, an: `live_score`/`live_minute` (Orientierung via
  `_align_goals`), Backfill von `country` + `league`, kanonische Teamnamen (behebt „Atlet – Rebel"),
  Orientierung beibehalten. Response-only (volatiler Live-Score wird nicht persistiert).
- Frontend (`RateWall.jsx`): Leg zeigt jetzt „Land · Liga" statt nur Liga. Kickoff/Datum-Badge und
  Live-Badge waren bereits vorhanden und greifen nun mit den angereicherten Daten.
- Verifiziert: synthetisches Parlay mit echtem Live-Fixture → Leg bekam live 0:0 15', Australia,
  „Victoria NPL 2", voller Name. Nicht-Live-Legs unberührt.
- Duplikate: für hq-auto via Kickoff-Resolver + `_dedupe_hq_tips` bereits abgedeckt.


## 2026-08-03 — P0: „Annulliert 164" obwohl Liste leer (Zähler ≠ Liste)
Owner-Screenshot: Badge „Annulliert" zeigte 164, die Karte war aber leer. Ursache: `/tips/counts`
zählte void-Tips ohne die Filter, die die Liste anwendet (`hidden`, Silent-Sources, team-lose Slips).
Fix (`server.py` counts-Endpoint): `void_n` nutzt jetzt exakt die Listen-Filter — `hidden!=True`,
`_exclude_silent_sources`, kein `seed-`, plus `_tip_has_known_teams` in Python → Badge == Liste.
Ebenso `lost_n`, `cashed_n`, `bestwon_n`, `won_normal_n` um Silent-Sources bereinigt.
Verifiziert (API): void-Badge 11 = void-Liste 11; lost-Badge 3 = lost-Liste 3.


## 2026-08-03 — Admin-Knopf „Smart Picks löschen"
- Backend: neuer Endpoint `POST /api/admin/smart/clear` (require_admin) → löscht ALLE offenen
  Smart Picks (pending+live) OHNE Regenerierung; abgerechnete Historie bleibt. Getestet: `{"deleted":1}`.
- Frontend (`RateWall.jsx`): roter Button „Smart Picks löschen" (`data-testid=clear-smart-btn`) im
  Smart-Picks-View, nur für `role==admin`. Confirm-Dialog, danach Feed-Reload.
- i18n: `wall.smartClear/Confirm/Cleared` in EN (Fallback) + DE ergänzt.

## 2026-08-03 — Echte Anstoßzeit nachladen + Duplikate zusammenführen
Folgeauftrag zum Zeit-Fix. `server.py` `resolve_unparseable_kickoffs` erweitert:
- Neuer Helper `_kickoff_time_unknown`: erkennt unparsebare UND 23:59-UTC-Sentinel-Kickoffs
  (date-only). Resolver bezieht jetzt auch `hq-auto` ein (vorher ausgeschlossen), holt die echte
  Anstoßzeit + kanonische Teamnamen via API-Football (`find_upcoming_fixture`), speichert absolute UTC.
- Multi-Spiel-Kombis werden übersprungen (kein Einzel-Kickoff auflösbar).
- Nach Auflösen von hq-auto-Tips läuft `_dedupe_hq_tips` → Duplikate, die vorher wegen abweichender
  Schreibweise/Zeit (z.B. „Sparta Praha 18:00" vs „Sparta Prague"+Sentinel) durchrutschten, werden
  jetzt zu EINEM Pick zusammengeführt.
- Läuft im `settlement_loop` (rate-capped 12/Lauf, stündlicher Retry) → Produktion heilt sich nach Deploy.
- Verifiziert (Preview): Sparta–Lyon → nur noch 1 Pick, 04.08. 18:00, Sentinel-Duplikat entfernt.


## 2026-08-03 — P0: Falsche Anstoßzeiten (Sentinel 23:59 → "02:00 nachts") behoben
Owner (Screenshot): Sparta Prague – Lyon (UCL) stand auf „Aug 5 01:59". „Europa spielt nie um 2 Uhr
nachts." Ursache: date-only Kickoffs bekommen intern 23:59 UTC als Sentinel (`_parse_kickoff` Z.5144,
für Ablauf-Logik nötig). Als ISO gespeichert + nach Europe/Berlin (+2) konvertiert → 01:59 nächster Tag.
Fix (`frontend/src/i18n.js`): `kickoffInfo` erkennt den 23:59-UTC-Sentinel und behandelt ihn als
„Datum bekannt, Uhrzeit unbekannt" → zeigt das Spieldatum (UTC) OHNE Uhrzeit, `_toViewer` verschiebt
ihn nicht mehr in den Folgetag. Echte Zeiten (z.B. 18:00 UTC) unverändert. Per Node verifiziert.
Gilt für alle Picks; wirkt auf Produktion nach „Save to Github → Deploy".


## 2026-08-03 — Smart: alle Zyklus-Picks gelöscht + Owner-Referenzpick eingefügt
Owner: „Lösche alle Zyklus-Picks aus dem Smart, füge diesen ein, und lerne: Smart Picks sind kein Lotto."
- Alle 3 vorhandenen Smart-Tips waren Zyklus-Picks → per Script gelöscht (jeder Status).
- Eingefügt (Owner-Referenz, `source=smart`, `id=smart-6b3de011-ure`): **„Anytime Goalscorer o.
  Ersatzspieler — Robbie Ure" @ 1.41**, Halmstad vs. Sirius, Anstoß 03.08.2026 19:00. `kind=player`
  (settelt nicht automatisch, bleibt pending bis Admin). Per API verifiziert (erscheint in Smart Picks).
- Prinzip dokumentiert in `/app/memory/smart_picks_principle.md`: Smart Picks = sichere, logische
  Value-Singles; „Zyklus/fällig"-Lotto ist verboten und deaktiviert.


## 2026-08-03 — P0: Smart-Picks "Zyklus" deaktiviert (Lotto raus)
Owner: „Teams, die nie 3 Tore treffen, machen nicht plötzlich 3 Tore. Das ist Lotto — mach den
Code inaktiv und ungültig (nicht löschen), poste keine solchen Smart Picks mehr."
- `server.py` `smart_h2h_autopost` (der „H2H-Zyklus", Aufruf background_tasks.py:474 + `/admin/smart/run`):
  früher `return` direkt nach dem Docstring → postet NIE mehr Zyklus-Picks. Code bleibt vollständig
  erhalten (nur unerreichbar), wie vom Owner gewünscht.
- Self-heal: bei jedem Lauf werden vorhandene OFFENE Zyklus-Picks entfernt
  (`source=smart & h2h_cycle=True` bzw. `id ^smarth2h-`, nur pending/live) → auch Produktion
  bereinigt sich nach dem Deploy selbst. Abgerechnete/History bleiben unberührt.
- Verifiziert: Funktion gibt `{posted:0, purged:N, reason:'cycle disabled ...'}` zurück; Backend importiert & läuft (200).


## 2026-08-03 — P0: Codemining Straight-Win = No Bet + Beispiele richtig gestellt
Owner (Live-Screenshot Halmstad–Sirius): durchgestrichener „1X2 S2" wurde fälschlich zu
„IK Sirius Draw No Bet (DNB)" — eine Wette FÜR Sirius, obwohl der durchgestrichene S2 heißt
„Sirius gewinnt NICHT". Fixes:
- **Backend (`server.py` `_run_code_scan`, ~Z. 9830)**: glatter Sieg/1X2-Code (`_is_straightwin_code`)
  → IMMER `read=no_bet` mit Glaskugel-Warnung „{Team} gewinnt NICHT" (via `_code_win_side`).
  Kein DNB / keine Doppelte Chance mehr. Alte `_code_straightwin_decision`-DNB-Regel ersetzt.
  Verifiziert: `1X2 S2` (Halmstad–Sirius) → win_side=away=IK Sirius → „IK Sirius gewinnt NICHT" + No Bet.
- **Frontend (`CodeReading.jsx`)**: Upload-Beispiele in de/el/en auf die 3 echten Schritte umgebaut —
  **Code → Glaskugel (was NICHT passiert) → Mining (was gespielt wird)**. Milan–Inter jetzt korrekt
  NO BET statt DNB. Render zeigt 3 beschriftete Zeilen.


## 2026-08-03 — P0: Halbzeit-Totals werden korrekt gewertet (kein VOID mehr)
Owner (Live-Screenshots): „Über 0.5 Tore 1. Halbzeit" wurde fälschlich VOID gesetzt statt Gewonnen/
Verloren. Fix in `settlement.py` `_grade_goal_leg` (Z. 437-449): 1./2.-Halbzeit-Totallinien
(`Über/Unter X.5 ... Halbzeit/HZ/Hälfte/first-half/second-half`) werden jetzt aus dem HZ-Score
(`ht_home`/`ht_away`, 2. HZ = FT-Total − HZ-Total) gewertet → Gewonnen/Verloren. Bei fehlenden
HZ-Daten sauber `None` (nie geraten/VOID). Per Simulation bestätigt (Über/Unter 1./2. HZ ✓).
Owner-Entscheid: nur Fix behalten, KEINE Rück-Abrechnung bestehender VOID-Tickets.


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

### Glaskugel: 1-Klick Permanent verankern
- CodeDefaultsPanel.jsx: neuer Button "Permanent verankern" (Lock) in der Glaskugel-Box neben "Als Option uebernehmen". Ruft /permanent mit dem Glaskugel-Vorschlag (our_market oder no_bet + trend-note) auf -> wird sofort in alle Spiele mit diesem Code eingewurzelt & gelockt.
- rootPermFromAi() + Labels aiRoot (DE/EN/EL). Getestet: /permanent akzeptiert no_bet=true + leeren Markt (curl ok); Frontend compiled.

### 2026-08-03 — Dedup: ein Pick pro Spiel (inkl. Ein-Spiel-Bet-Builder) [P0]
- Bug: KI Single-Game-Picks zeigte dasselbe Spiel doppelt (Einzel-Wette + Ein-Spiel-Bet-Builder favdc). Ursache: _dedupe_hq_tips filterte is_parlay:{ne:True} -> Bet-Builder (is_parlay=true, 1 Leg) entkam dem Dedup.
- Fix (server.py _dedupe_hq_tips): Query holt jetzt alle hq-auto pending; MULTI-Spiel-Parlays (>1 distinct match in legs) bleiben ausgenommen; Ein-Spiel-Bet-Builder nehmen am Dedup teil. Ranking: Geschenk geschuetzt > hoechste Quote > Kategorie (Risk>Value>Banker). Guard: Tips ohne Home+Away werden NIE kollabiert (match_key(None,None)= "|" haette sonst alle in einen Bucket gelegt).
- Getestet: 4 kollidierende Spiele -> je 1 Pick behalten; Feed 7 Spiele / 0 Duplikate; erneuter Dedup-Lauf entfernt 0.
- Hinweis: bei Kollision Einzel vs Bet-Builder ueberlebt der hoehere-Quoten-Pick (Owner-Regel). Bei Geschenk vs anderer Pick ueberlebt das Geschenk.

### 2026-08-03 — Telegram-Pick Fehl-Jahr (3026) [P0]
- Bug: footballinsight-Telegram-Post mit Tippfehler "02/08/3026" -> Pick mit Jahr 3026 (ferne Zukunft) haengt ewig im Feed, wird nie abgerechnet.
- Fix (scrapers_autopost.py _fi_parse): unplausibles Jahr (>cur+1 oder <cur-1) wird auf aktuelles Jahr geklemmt. Getestet: 3026->2026, gueltige 2026-Daten bleiben.
- Altlast: den einen haengenden Pick (hqtip-fi-tg-footballinsight01-39768, vergangenes Datum, nicht abrechenbar) direkt geloescht. Feed sauber.

### 2026-08-03 — Kollisionen mergen statt loeschen + Teamnamen-Parser [P0/P1]
- Owner-Wunsch: pro Spiel EIN Pick = alle Selektionen in einem Bet-Builder kombiniert (Bsp Bukovyna: X2 + Ueber 0.5 + Unter 3.5), hoehere Gesamtquote.
- server.py _dedupe_hq_tips komplett umgebaut: Union-Find gruppiert alle Picks eines Spiels (3 Identitaets-Strategien); pro Gruppe werden Selektionen via dedupe_implied_legs zusammengefuehrt, Gesamtquote via _correlated_combo_odds (Tor-Cluster-Daempfung), Geschenk-Flag bleibt erhalten. Import erweitert: market_constraint,_sat,GRID.
- Widerspruchs-Schutz: unmoegliche Kombi (z.B. Ueber3.5 + Unter1.5) wird NICHT gemergt -> hoechste Quote bleibt. Getestet: Merge (2->1 Bet-Builder, 3 Selektionen, Quote 1.61) + Contra-Fallback (behaelt 3.10).
- scrapers_autopost.py _fi_clean_team: extrahiert bei einzeiligen Telegram-Posts nur den echten Teamnamen (schneidet Pick/Datum/Liga/Disclaimer ab, strippt Free-pick-Label). Getestet: Midtjylland/Horsens, Real Madrid/Barcelona, Bodo/Glimt korrekt.

### 2026-08-03 — Praezise Bet-Builder-Legs + Geschenk-Vorzug [P0]
- Owner: kein Leg-Limit; Geschenke bevorzugen; praezise Legs (keine redundanten Selektionen), Vorbild = gewonnener WZ-Slip.
- betting_logic.py market_constraint: neue Regel "<team> schiesst die ersten N Tore / first N goals" -> Team>=N (Scoreline-Constraint). Damit erkennt dedupe_implied_legs, dass z.B. "Shakhtar Ueber 0.5" von "Shakhtar ersten 2 Tore" impliziert wird -> die schwaechere Leg wird gedroppt.
- server.py _dedupe_hq_tips: (a) Widerspruchs-Fallback bevorzugt jetzt das Geschenk (gift or max-odd). (b) neuer Praezisions-Durchlauf ueber JEDEN Ein-Spiel-Bet-Builder (auch ohne Kollision): redundante Legs raus, Quote/Label neu.
- Getestet: Kudrivka-Builder [X2, ersten 2 Tore] (Ueber 0.5 entfernt), Quote 2.56, is_gift bleibt True. Feed 1 Pick/Spiel, 0 Duplikate.

### 2026-08-03 — Praezise Markt-Labels (WZ-Stil) [P1]
- betting_logic.precise_label(): Anzeige-Normalisierung. Team-Total -> "<Team> Team-Tore Ueber/Unter X.5"; Match-Total -> "Gesamt-Tore Ueber/Unter X.5". DC/BTTS/Sieg/1.HZ/Asian/Handicap/Ecken/Composite-Bet-Builder-Header bleiben unveraendert. Idempotent, Mindest-Teamlaenge>=3 (kein Fehlmatch in "ueber").
- server.py list_tips: wendet precise_label auf market + legs[].selections an (Anzeige-only, gespeicherte Strings unberuehrt -> Settlement-Grading unveraendert). Gilt fuer alle Feeds (ai+master).
- Verifiziert im UI: "LNZ Cherkasy Team-Tore Ueber 0.5", "Gesamt-Tore Ueber 1.5"; Composite-Header nicht zerstoert; Geschenk-Badge + Merge korrekt.

### 2026-08-03 — Datum-Format + Badge-Overflow + Community/Codemining-Datum [P0]
- Task1 Datum: nie Jahr, Format "Aug 2" (3-Buchstaben-Monat + Tag). i18n.formatKickoff (Hauptfeed) + neue i18n.formatKickoffText fuer Freitext-Scrape-Daten ("02.08. 14:00","02/08/2026" -> "Aug 2 · 14:00"). Verifiziert: keine 2026 mehr im Feed.
- Task4 Badge: RateWall Header rechte Badge-Gruppe shrink-0 entfernt + min-w-0 -> GEWONNEN-Badge quillt nicht mehr rechts raus, bricht sauber um.
- Task2 Community-Picks Datum/Zeit: Kickoff-Badge zeigte nichts wenn formatKickoff Freitext nicht parsen konnte (return null). Fallback auf formatKickoffText ergaenzt -> Community-Picks zeigen jetzt Datum+Uhrzeit. Live/End-Score werden gerendert wenn Daten da (fixture-abhaengig).
- Task3 beendetes Codemining End-Ergebnis: Frontend rendert r.score bereits, Backend settle_code_reads setzt es. Aktuell 0 beendete Reads zum Live-Test; Rendering+Backend vorhanden.
- Codemining-Datum nutzt jetzt formatKickoffText (CodeReading.jsx).

### 2026-08-03 — Poster-Zeitzone lernen + Kickoff-Korrektur [P0]
- Neu poster_tz.py: lernt pro Poster den Offset (Poster-Lokalzeit minus Berlin) durch Vergleich der GETIPPTEN Wanduhrzeit vs echter API-Football-UTC-Kickoff. Rolling window (8 samples), Modus-basiert -> vacation-aware (temporaere Korrektur bei neuem, wiederholtem Offset). Speicher: db.poster_tz {username, offset_min, samples}.
- settlement.py: fixture-Resolver liefert jetzt kickoff_utc; settle_pending_tips lernt daraus record_offset() — NUR fuer Member/Experten (nicht hq-auto/hq-live).
- server.py list_tips: _shift_typed_kickoff verschiebt GETIPPTE naive Kickoffs (DD/MM/YYYY HH:MM) um -offset auf Berlin-Basis; absolute ISO-Zeiten (mit +HH:MM/Z) bleiben unberuehrt. Danach greift die bestehende Viewer-Zeitzonen-Umrechnung. Ergebnis: Owner(Berlin) sieht Polaris(Athen) -1h; Athen-Betrachter sieht Polaris original + Owner +1h.
- Getestet: Polaris lernt +60; 20:00 -> 19:00 Berlin; absolute ISO unberuehrt. Backend gesund.
- OFFEN (naechster Schritt): API-Fallback fuer UNPARSEBARE Kickoffs kommender Member-Picks (echten Anstoss live von API holen) — Lernen laeuft bereits, wenn Spiele abgerechnet werden.

### 2026-08-03 — API-Fallback fuer unlesbare Kickoffs [P0 erledigt]
- server.py resolve_unparseable_kickoffs(): fuer pending MEMBER/expert-Picks mit nicht-parsebarem Kickoff wird der echte Anstoss von API-Football geholt (find_upcoming_fixture -> date_iso) und als absolute UTC-Zeit gespeichert -> korrekt fuer jede Betrachter-Zeitzone. Rate-cap 12/Lauf, pro Pick max. stuendlich (ko_resolve_at). Aktualisiert auch home/away aus API. HQ-Scraper ausgenommen.
- settlement.py settlement_loop ruft es periodisch auf; Import ergaenzt; fixture-Resolver liefert kickoff_utc.
- Getestet live: 3/3 unlesbare aufgeloest (z.B. Dortmund-Bayern -> 2026-08-22T18:30:00+00:00). Backend clean, /api/tips 200.

### 2026-08-03 — Ticket-Renderer Teamnamen groesser + neue Schrift [P0 erledigt]
- ticket_render.py: Teamname-Titel von schmaler BarlowCondensed-Bold auf breite Barlow-Bold (BODY_B) umgestellt, Groesse fit 60->44, TITLE_H 74. Teamnamen jetzt gross/fett/lesbar, Trenner "–" ohne Tofu. Verifiziert per echtem /share-image Endpoint (polaris/master Tickets).
- server.py: SHARE_RENDER_VER 5->8, damit gecachte alte Share-Bilder neu generiert werden.

### 2026-08-03 — "Both halves over 0.5" falsch als "Gesamt-Tore Über 0.5" gelabelt [P0 erledigt]
- Root cause: betting_logic.precise_label() erkannte englisches "halves" nicht -> "both halves over 0.5" (Tor in JEDER Halbzeit) wurde zum Match-Total "Gesamt-Tore Über 0.5" (nur 1 Tor gesamt) verfaelscht. Nur Anzeige, gespeicherter String war korrekt.
- Fix precise_label: "both halves"/"halves"/"each half" zur Ausschlussliste hinzugefuegt -> Markt bleibt unveraendert.
- Fix i18n.js _formatSelection: neue Regel "both halves over X" -> "Über X Tore in jeder Halbzeit" (localisiert).
- Fix settlement.py: englische Begriffe "both halves"/"each half" zur each-half Grading-Regel ergaenzt (vorher Grading-Luecke -> ungrade/void). Bewertet jetzt korrekt: Tor in JEDER Halbzeit.
- Verifiziert: precise_label Unit-Test, Frontend kompiliert clean, JS-Regex-Test ok.

### 2026-08-05 — Master 'Einfach': zusaetzlicher 3-Tage-Sammelschein [Feature]
- Neue Funktion server.py master_easy3day_build(): baut ZUSAETZLICH zum 8er 'easy_mix' einen grossen 3-Tage-Sammelschein im Einfach-Bereich (master_category 'einfach', Flag easy3d=True).
- 12-14 Legs, Zielquote ~20-30 (Band-Kontrolle: stop bei >=12 Legs & prod>=24, max 14). Fenster = heute + 2 Berlin-Tage.
- Markt-Logik: Pass 1 klare Favoriten-Siege ('<Team> Sieg', fav_prob>=64 -> gestaffelte Quoten 1.15-1.42, <=~1.40 bei starken Favs); Pass 2 sichere Tor-Maerkte (Ueber 1.5 / Team Ueber 0.5 / Ueber 0.5) als Mix-Auffueller.
- Dedup: per-Fixture + (Team, Tag) -> collabiert Bookie-Namensvarianten (z.B. 'CSKA 1948' vs '... Sofia'), keine Team-Doppelung. Darf Favoriten mit anderen Master-Packs teilen (eigenstaendiges Showcase-Produkt).
- Eingehaengt in beide Loops (_regen_pregames_bg + Master-Hauptloop) mit Log 'easy3d {...}'. Settlement bewertet '{Team} Sieg' (settlement.py Z.339-341) und each-half/Tor-Maerkte korrekt.
- Getestet: Build liefert 13 Legs @27.60, 4x Sieg + Mix, keine Duplikate; API /tips?source=master&mcat=einfach zeigt beide Scheine (13er 3-Tage + 8er Sicher-Mix). Backend clean.

### 2026-08-06 — Admin: einzelnen Gewinn-Schein in Hall of Fame pinnen (Ausnahme) [Feature]
- Grund: Win-Claim vergibt 20 Credits ohne Quoten-Check, aber HoF verlangt Gesamtquote >=3.00 -> sub-3.00 Scheine (z.B. 2.17) bekamen Credits, erschienen aber nie. User wollte AUSNAHMSWEISE einen Schein posten (HoF war leer, Marketing), OHNE die Hauptregel zu aendern.
- server.py: hall_of_fame() honoriert jetzt Flag hof_force=True als Ausnahme (bypass Quote+Legs, behaelt HOF_START-Datum). 3.00/20.00-Hauptregel unveraendert fuer alle anderen.
- Neue Admin-Endpunkte: GET /admin/wins/recent (Liste + in_hof-Status), POST /admin/wins/{id}/pin, /unpin.
- Frontend: neue Komponente HofPinPanel.jsx + Button 'Hall of Fame pinnen' in AdminResetBar.jsx (Modal listet letzte Claims, Pin/Unpin-Toggle).
- WICHTIG: Preview- und Live-DB sind GETRENNT. Der eingereichte Schein des Users liegt in der LIVE-DB. Nach Deploy muss der User den Button auf tipjarglobal.com nutzen, um seinen Schein zu pinnen.
- Getestet: Login als Admin, Test-Claim @2.17 -> vor Pin NICHT in HoF (size 0), nach Pin drin (size 1), nach Unpin wieder weg. Frontend-Screenshot: Panel + Claim-Liste + Pinnen-Button rendern korrekt.

### 2026-08-07 — Settlement/Zaehler/Best-of Sammelfix (User: "repariere alles") [P0/Feature]
- P3 Kategorie-Zaehler: GET /tips/counts akzeptiert jetzt ?category=banker|value|risk|gifts und zaehlt NUR diese Kategorie (Fenster + Alle). Frontend RateWall.jsx uebergibt aktive Kategorie -> jeder Bereich zeigt seine EIGENE korrekte Zahl (vorher immer Gesamtzahl 31). Verifiziert: total 5 = value 4 + gift 1.
- P2 Best of: bestwon-Abfrage (count @ ~1100 + list @ ~2747) schloss hq-master aus -> gewonnene Master-Parlays (Doppelpack Ajax+Benfica etc.) erschienen nie in Best of. Fix: {source:hq-master, is_parlay:true} in beide $or aufgenommen. Verifiziert: Master-Parlays erscheinen jetzt in /tips?source=bestwon.
- P1 Settlement: Neuer Admin-Button "Jetzt abrechnen" (AdminResetBar) -> POST /admin/settle-now (Tipps+Parlays+Combos, umgeht Leader-Check) + POST /admin/code-reading/settle-finished (Codemining beendet -> Farbe+Ergebnis). Toast zeigt Anzahl. Settlement-Engine-Code ist korrekt (settle-now im Preview getestet: ok, checked 3). Leadership funktioniert (Lock TTL 90s, fail-open).
- HINWEIS: Automatische Abrechnung auf LIVE haengt an Loop-Ausfuehrung + API-Football-Coverage der (oft obskuren) Ligen. Der manuelle Button gibt dem Owner sofortige Kontrolle. Preview- und Live-DB sind getrennt -> User muss nach Deploy auf tipjarglobal.com "Jetzt abrechnen" druecken, um gestrige Spiele sofort abzurechnen.
- P4 Codemining Auto-Auswahl: bereits automatisch (keine Aenderung noetig).
- Getestet: server syntax OK, frontend compiled (1 harmloser eslint-warning), alle 4 Endpunkte per curl, Admin-Buttons rendern (Screenshot).

### 2026-08-07 — Silent Instagram-Scout 'Spica' (@thatsfootball90x) fuettert Master [Feature]
- Neuer stiller Hidden-Expert-Bot 'Spica' in _CHANNEL_BOTS (handle thatsfootball90x, silent=True, feeds_master=True). Nie oeffentlich sichtbar.
- _ingest_emptips setzt jetzt learn_as_master=bool(bot_cfg.feeds_master) auf den Tipp.
- learning.py refresh_learning: bezieht {learn_as_master:true}-Tipps ein und mappt sie aufs 'master'-System -> Master lernt aus Spicas settled Picks (Markt-Veto + per-Leg).
- Neuer Admin-Endpunkt POST /admin/scout/ingest (Upload 1-6 Screenshots oder Text) -> Vision-OCR (analyze_tip) -> versteckter Tipp source=spica, is_expert, hidden, learn_as_master.
- Frontend: ScoutFeedPanel.jsx + Button 'Scout fuettern' (fuchsia) in AdminResetBar.
- Instagram NICHT direkt scrapebar (Login-Wall, crawl 403) -> OCR-Upload-Weg gewaehlt (Option A). Voll-Auto-Scraper waere Drittanbieter-API (kostenpflichtig) - nicht gebaut.
- Getestet: 404 bei falschem Handle; Text-Ingest -> Spica-Tipp (hidden=True, learn_as_master=True, source=spica, aus public feed ausgeschlossen); refresh_learning trainiert 'master' darauf; Admin-Modal rendert (Screenshot). Bot-User role=expert/silent.
