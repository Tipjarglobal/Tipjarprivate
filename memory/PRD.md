# TipJar — Product Requirements & Progress

### CHANGELOG 2026-07-22f — "Eingegangene Ideen" entfernt + Lincoln/Spanien-Argentinien gelöscht
- Owner: „Eingegangene Ideen" soll nie wieder erscheinen → Feed-Block + Polling (`/smart/ideas/recent` alle 20s) aus SmartLab entfernt (Frontend RateWall.jsx). Idee-Einreichung im Chat bleibt.
- Spanien–Argentinien: bereits gelöscht (nicht mehr vorhanden). Lincoln Red Imps: 3 Tipps + 1 Prognose gelöscht → erscheint nicht mehr in Single Picks.
- VERIFIZIERT: Frontend kompiliert fehlerfrei, DB-Löschung bestätigt. Auf Produktion greift die UI-Änderung nach **Deploy**; alte Lost-Tipps dort purgen automatisch nach Spielende.


- Owner-Wunsch: eigene „Mental"-Option mit crazy High-Odds-Bet-Buildern (Über 4.5 Tore + beide HZ + Handicap etc.).
- Backend `mental_autopost()`: pro Torfest-Spiel EIN 5-Leg-Builder auf ein Spiel, riesige Quote (~95–150/1), category="mental", source="hq-auto", is_parlay → abrechenbar via settle_hq_combos. Alle Legs text-gradeable (Über 4.5/5.5, BTTS, Tor in jeder Halbzeit, {Fav} -1.5 Handicap, {Fav} Über 2.5).
- /tips: category="mental" Filter ergänzt; Mental aus Default/Value-Ansichten ausgeschlossen (nur im eigenen Tab).
- Frontend: 4. Kategorie-Tab „🤯 Mental" (fuchsia) im AI-Single-Pick-Wall. Loop-Hook + Admin-Trigger `/admin/smart/run`.
- VERIFIZIERT: /admin/smart/run postete 6 Mental-Picks; /tips?category=mental liefert 6, 0 Leck in Default-Wall; Frontend kompiliert. Greift auf Produktion nach **Deploy**.


- Owner-Wunsch: Smart Picks sollen dominante Favoriten anbieten (wie Gewinner: Lech +Handicap + Über 1.5) mit Sterne-Rating & Begründung.
- Neu `favourite_smart_autopost()`: für whitelisted Favoriten (fav_prob≥58, erwartete Favoriten-Tore≥2, 0:0-sicher, kein Brasilien) im 5-Tage-Fenster. SICHER: „{Fav} Doppelte Chance + Über 1.5" (1:1 reicht). PFEFFER (fav_prob≥66 & fg≥3): „{Fav} -1.5 Handicap + Über 1.5". Rating 7–10 ⭐, deutsche Begründung, auto-settlebar (source=smart, is_parlay).
- Grader: text-basierte Handicaps „{Team} -1.5/+2.5 Handicap" ergänzt. Admin-Trigger `/admin/smart/run` läuft jetzt beide Generatoren; Hook im Smart-Loop.
- STATUS: Logik verifiziert (Toluca bestand alle Filter, nur Anstoß bereits vorbei). Aktuell 0 Posts, da alle *kommenden* starken Favoriten obskure Ligen sind (korrekt gefiltert) — füllt sich automatisch mit echten Liga-Spielen. Greift auf Produktion nach **Deploy**.


- Owner-Klarstellung: „{Fav} DC + Über 1.5 (Spiel)" → 1:1 reicht (sicher). Team-spezifisch „{Fav} Über 1.5" würde 2 eigene Tore verlangen (riskant, Fenerbahce-1:0-Falle).
- Pfeffer-Banker nutzen jetzt „{Favorit} Doppelte Chance {dc} + Über 1.5 Tore" (Spiel-Gesamttore, NICHT teamspezifisch). Settlet als total≥2 + Favorit verliert nicht.
- VERIFIZIERT: /systems zeigt „Braga DC X2 + Über 1.5 Tore" etc. (12 Spiele, 367x), abrechenbar. Greift auf Produktion nach **Deploy**.


- Owner-Beobachtung: cleverer Tipper spielte dominante Favoriten (Sturm/Crvena Zvezda/Lech, alle 4 Tore) mit „{Team} Sieg/DC + {Team} Über 1.5"; verlor nur wegen Fenerbahce (1:0).
- Pfeffer-Banker jetzt: „{Favorit} Doppelte Chance {dc} + {Favorit} Über 1.5 Tore" (nur wenn Favorit ≥2 Tore erwartet). Der Favorit trägt beide Legs → keine Abhängigkeit vom schwachen Team. Dominante Favoriten werden zuerst gewählt.
- Grader: team-spezifische Über/Unter-Linien jetzt TEXT-abrechenbar (Teamname im Markt → dessen Tore), damit „{Team} Über 1.5 Tore" auch im gespeicherten System settlet.
- VERIFIZIERT: /systems pepper zeigt „Braga DC X2 + Braga Über 1.5" etc., beide Fenster, Screenshot sauber. Greift auf Produktion nach **Deploy**.


- Owner-Lektion: Radar sagte „Lincoln trifft" → Lincoln traf NICHT (Mjällby 3:0). Regel: nie vom schwachen Team abhängen.
- Pfeffer neu (`_build_pepper_slip`): `_pepper_qualifies` nimmt nur Spiele mit starkem Favoriten (fav_prob≥52, Favorit erwartet ≥2 Tore) ODER echtem Torfest (total≥4 & btts). Banker favoriten-verankert: „{Favorit} Doppelte Chance + Über-Linie" (der Favorit trägt beide Legs) statt schwache-Team-abhängiger BTTS.
- Zwei Fenster: `pepper` (Di→Fr 12:00) + `pepperwk` (Fr→Di 12:00), beide oben in System-Picks. Snapshot je Key.
- Favoriten-Tracker `db.favourite_teams`: sammelt automatisch starke Favoriten (fav_prob≥60), wächst zur ~50-Team-Liste (Grundlage fürs Lernen aus Ergebnissen).
- VERIFIZIERT: /systems liefert beide Fenster (Di→Fr 10 Spiele/505x, Fr→Di 2 Spiele), 0 Brasilien, Screenshot ok. Greift auf Produktion nach **Deploy**.


- Owner: „deine Pfeffer spiele waren Müll. Ich hasse es, Brasilien als Pfeffer zu benutzen." Atletico Mineiro (pred 5→1:1) & Gremio (pred 4→0:1) bewiesen: Brasilien-Prognosen überschätzen Tore.
- Neuer Helper `_bad_for_overs(p)` (Liga enthält brazil/brasil) → schließt Brasilien aus dem Wochen-Pfeffer UND der TipJarLogic-Über-Kombi aus. Betrifft NUR Über-Tipps; Brasilien bleibt sonst bettbar.
- Lernnotiz zur Exakt-2-Tore-Falle (Asian Über 2.0 = Push, Über 2.25 = halber Verlust) in betting_notes ergänzt → Über 2.5 nur bei echten Torfesten.
- VERIFIZIERT: /systems pepper enthält 0 Brasilien-Spiele (jetzt K-League/Quali/Norwegen/Usbekistan/MLS), ~5.500x. Greift auf Produktion nach **Deploy**.


- Owner-Verfeinerung: Banker-Kombis kombinieren jetzt eine Über- mit einer Unter-Linie (Tor-Range), Pivot ~2.5. Torfest→„Über 2.5 + Unter 5.5" (3–5), mittel→„Über 1.5 + Unter 4.5" (2–4), niedrig→„Über 0.5 + Unter 3.5" (1–3). Jeder 3. Banker mit klarem Favoriten: „Favorit Doppelte Chance + Über-Linie".
- Grader `_grade_goal_leg`: neue text-abrechenbare UNTER-Linie („Unter N.5 Tore" → total ≤ N).
- VERIFIZIERT: /systems pepper zeigt Range-Banker (Über 2.5 + Unter 5.5 @2,24), Gesamtquote ~6.500x, alle Legs settlebar. Greift auf Produktion nach **Deploy**.


- Owner-Wunsch: ein großer Kombi-Schein Di→Fr 12:00, 6 beste Banker mit „Pfeffer" (2-Leg-Kombis, KEIN Über 0,5), insgesamt 15 Spiele.
- Backend `build_systems`: neues System key `pepper` „Wochen-Pfeffer-Kombi (Di→Fr)" ganz oben. Fenster: jetzt−3h → kommender Freitag 12:00. Nur 0:0-sichere Spiele (`over_safe`). 6 Banker als 2-Leg-Kombis (variiert: „Tor in jeder Halbzeit + Über 2.5" / bet365-Stil „Favorit Doppelte Chance + Beide treffen"), 9 Value-Legs → 15 Spiele, Gesamtquote als Produkt.
- Grader `_grade_goal_leg`: neue text-abrechenbare Märkte „Tor in jeder Halbzeit" (Tor in beiden HZ) + kind-basiert `team_o15` (Team ≥2 Tore) und `ah25_*` (+2.5 Handicap). Alle Pepper-Legs settlebar über bestehende Engine + snapshot_systems.
- Frontend `Systems.jsx`: Titel/Untertitel-Fallback auf Backend-Werte (kein roher i18n-Key für neue System-Keys).
- VERIFIZIERT: /systems liefert pepper (15 Spiele, 6 Banker, ~31000x, Di→Do im Fenster), Screenshot zeigt Karte oben mit Banker-Kombis + Datum/Liga. Backend 200 ohne Fehler. Greift auf Produktion nach **Deploy**.


- Owner-Wunsch: kleine Einführung über die Quali-Spiele der Woche + pro Team: welche Liga-Spiele davor/danach, wie sie im Ligaspiel spielten (Schüsse, Rotation), ob das nächste Ligaspiel wichtig ist / weite Reise.
- Backend: `GET /api/smart/qualifier-briefing` (8h-gecacht in `briefing_cache`, quota-schonend, max 10 Ties). `_team_league_context` holt letztes Liga-Spiel VOR dem Quali (Ergebnis + Schüsse via /fixtures/statistics) und nächstes Liga-Spiel DANACH (Gegner, Heim/Auswärts, Stadt, Tage Abstand). LLM (Gemini) schreibt daraus ein deutsches Briefing; ehrlich wenn Liga in Sommerpause (keine erfundenen Zahlen). In `smart_loop` (12h) + Startup-Rebuild, Concurrency-Guard `_BRIEFING_BUILDING`.
- BUGFIX beim Bau: `/fixtures`-Response hat kein `league.type` → alle Spiele wurden als „keine Liga" verworfen. Erkennung jetzt über Liga-NAME (Quali/Cup/Friendly ausgeschlossen). 18 Teams liefern nun echten Liga-Kontext.
- Frontend: neue `QualifierBriefing.jsx` (aufklappbare Karte oben in Smart Picks, Markdown-Fettschrift, i18n in 8 Sprachen).
- VERIFIZIERT: Endpoint liefert 10 Ties + Narrative mit echten Daten (Hammarby 4:0/22 Schüsse/Rotationsgefahr/Reise), Screenshot der Smart-Ansicht, Backend 200 ohne Fehler. Greift auf Produktion nach **Deploy**.


- Owner: verspätete Abrechnungen ließen Scheine alter Spiele hängen (z.B. Spain–Argentina, Spiel 19.07., erst 20.07. abgerechnet). `purge_settled_tips` löscht jetzt, sobald ENTWEDER die Abrechnung >24h alt ist ODER das Spiel selbst >24h vorbei ist (max. Kickoff über alle Legs via `_parse_kickoff`).
- VERIFIZIERT: Purge entfernte sofort 11 zusätzliche Scheine (Spiel >24h vorbei), 0 solche übrig; Hall of Fame (win_claims) unberührt. Greift auf Produktion nach **Deploy**.


- Owner: „Best Won weg. Hall of Fame steht." `purge_settled_tips` löscht jetzt ALLE won/lost/void-Scheine >24 Std. — die bisherige „für immer behalten"-Ausnahme (gewonnene System-/Community-Picks im 'Best Won'-Bucket) wurde entfernt.
- Die öffentliche HALL OF FAME (`db.win_claims`) ist eine SEPARATE Collection und bleibt unberührt (für immer sichtbar). Seed-Showcase-Scheine (`seed-*`) bleiben ebenfalls.
- VERIFIZIERT: Purge lief (5 alte gelöscht), 0 Scheine >24 Std. übrig, win_claims (2) unangetastet. Greift auf Produktion nach **Deploy**.


- **Owner-Philosophie:** Über-Wetten nur sicher, wenn ein 0:0 praktisch ausgeschlossen ist (Örgryte–Djurgården & Hafnarfjörður–Breidablik endeten 0:0, obwohl viele sie als torreich sahen).
- Neuer Helper `_zero_zero_assessment(p)` (quota-frei, aus Prognose-Signalen: Torschnitt, btts, über 2,5, conf, nordische Liga −32) → level `unlikely` / `medium` / `possible` + `over_safe`.
- `/api/goals-forecast`: liefert jetzt `zero_zero`, `zero_zero_label`, `over_safe`; 0:0-ausgeschlossene Spiele werden nach oben sortiert. Frontend zeigt farbiges Badge (grün „0:0 praktisch ausgeschlossen" / amber „0:0 möglich").
- `build_systems` (tjlogic-Kombi): nimmt nur noch Spiele mit `over_safe=True` → keine nordischen/defensiven Über-Fallen mehr in der Sicherheits-Kombi.
- VERIFIZIERT: goals-forecast liefert Level+Badge (curl), Frontend-Screenshot zeigt grüne Badges, Backend 200. Greift auf Produktion nach **Deploy**.


- **Verlängerung zählt NICHT (Owner-Regel):** Alle Tor-/Über-Märkte + Spieler-Props gelten nur für die reguläre 90-Min-Zeit. Neuer Helper `_reg_goals()` liest `score.fulltime` statt `goals` (API-Football zählt bei AET/PEN die Verlängerung mit). Angewandt in `find_finished_fixture`, `_datescan_fixture`, `_align_goals`. Bei Live-Spielen (fulltime=null) Fallback auf aktuellen Stand → keine Regression. Rest-Datenlücke: /fixtures/players trennt ET-Schüsse nicht.
- **Tor-Prognose-Tabelle (neu):** `GET /api/goals-forecast` liefert pro Spiel die vorhergesagten Tore je Team (aus ph/pa, NICHT aus der Quote). Frontend ScorerRadar hat jetzt 2 Tabs: "Tor-Prognose" (⚽ pro Tor, Owner-Format Ajax⚽⚽⚽) + "Wer trifft?" (bestehender Radar). 0:0-erwartete Spiele werden ehrlich als "kein Tor erwartet" markiert. i18n in 8 Sprachen.
- **Systeme-Bug:** Datum/Uhrzeit/Liga fehlten in der Anzeige. Frontend Systems.jsx: neue `LegMeta`-Zeile (📅 Datum · 🕐 Uhrzeit · 🏆 Liga) auf JEDEM Leg, robuster Kickoff-Parser (dd/mm/yyyy hh:mm + "21. Jul 2026"). Backend lieferte die Daten bereits.
- VERIFIZIERT: goals-forecast 18 Spiele (curl), Systeme + Radar per Screenshot, Backend 200 ohne Fehler. Greift auf Produktion nach **Deploy**.


## Problem Statement (verbatim intent)
Global community platform "TipJar" where people worldwide post football/sports betting tips.
AI auto-rates each tip; users rate them on a Rate Wall (Apex Scale 1–10). Animated jar + alarm bell
(no-signup alerts). Submit = tutorial or screenshot upload; AI auto-detects teams/time/country/league
and auto-rates. Credits economy (Stripe buy, gift w/ 10% fee, redeem at 10k for real money via PayPal).
Languages: EN, DE (primary), EL, FR, IT. Auto results engine (API-Football Pro) flips Pending->Won/Lost.
Automated betting tips scraped from Forebet/Predictz ("TipJarHQ Picks"). System bets. Player-prop
"Smart Bets" from API-Football stats. USER LANGUAGE = GERMAN (respond in German).

### CHANGELOG 2026-07-20 — "Stop dumb tips" + Owner-Notizen + Brasilien zurück
- Owner-Feedback (mehrere schlechte Tipps): DC-Banker in Skandinavien verloren (Ilves), Handicaps +2,5/+3,5 wertlos (Quoten ~1,005), Brasilien versehentlich aus Live entfernt.
- Backend (server.py `_forebet_candidates`):
  - Neuer Helper `_is_scandinavian()`; in skandinavischen/nordischen Ligen (Allsvenskan, Veikkausliiga, Eliteserien, …) werden **Doppelte Chance (1X/X2) UND DC12 nicht mehr angeboten** (zu unberechenbar für Banker).
  - **Handicaps +2,5 und +3,5 komplett entfernt** (wertlose Quoten). Nur noch +1,5 (echter Value ~1,55).
- Brasilien-Sperre aus allen 3 Live-Blöcken (Banger/Fresh/Kombi) **wieder entfernt** — Brasilien wird NICHT gelöscht (Owner-Wunsch). Top-Ligen bleiben bettbar; nur obskure Staatsmeisterschaften bleiben geblockt (unverändert, pre-existing).
- Neue Datei `/app/memory/betting_notes.md` — private Owner-Lernnotizen (harte Regeln + Muster-Wissen: Torteams jagen à la Göteborg, 0:0-Historie-Muster, kein Lotto-1X, Unter 2,5 + 1X statt BTTS-Lotto, „Wer trifft heute?"-Radar als Backlog).
- VERIFIZIERT (Unit): skandinavisches Spiel → 0 eigenständige DC-Märkte, keine +2,5/+3,5; nicht-skandinavisch behält DC; Backend `/api/tips/counts` 200. Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-19e — Smart-Lab: keine leere Fehlermeldung mehr + KI gibt IMMER einen Tipp
- Owner-Meldung: Beim Fragen im Smart-Bereich erschien eine blanke Fehler-/„gespeichert"-Meldung; KI soll immer coole Tipps geben.
- Backend (server.py `generate_smart_from_idea`): Prompt verschärft — actionable=false NUR bei komplett fußballfremdem Input (Spam/Beleidigung). Bei jeder fußballbezogenen (auch vagen) Eingabe MUSS die KI einen konkreten, coolen Smart-Bet auf das relevanteste Spiel liefern. Zusätzlich EINMALIGER Retry mit Zwang („actionable=true, keine Ablehnung"). Neuer Helper `_parse_smart_json`.
- Frontend (RateWall.jsx `send`): keine `toast.error`/leere „stored"-Verzweigungen mehr — immer eine freundliche positive Meldung, auch bei Netzwerk-Hiccup (kein blanker Fehler).
- VERIFIZIERT (curl): vage Frage „gib mir irgendeinen coolen tipp für heute" → konkreter Tipp „Bayern Doppelte Chance 1X · Über 1.5 @1.55", created:true. Test-Einträge wieder gelöscht. Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-19d — Automatische "Live Sicherheits-Kombi" (Owner-Style Live-Mehrfach)
- Owner-Muster (2 gewonnene Live-Dreier): 2–4 ultra-sichere Über-Legs aus laufenden Spielen → Gesamtquote ~1,5, geht easy durch. Wunsch: „KI soll richtig vorschlagen".
- Backend (server.py `live_autopost`, neuer Block 5): baut EINEN aktiven Live-Mehrfach aus verschiedenen In-Play-Spielen, die BEREITS ein Tor haben → „Über 0,5/1,5/2,5" ist bereits erfüllt = gesperrt (eine Über-Linie kann nach einem Tor nie mehr verloren gehen). Legs @ ~1,13–1,22, gebündelt bis Gesamtquote ~1,45–1,75 (max 4 Legs, min 2). Brasilien/gesperrte Ligen ausgeschlossen. Quota-frei (keine Stat-Calls). Kategorie „banker", erscheint im Live→Banker-Tab als Parlay.
- Nur EIN aktiver Kombi gleichzeitig (Regex-Check `^hqlive-kombi-`); nach Abrechnung baut die KI im nächsten Zyklus einen neuen.
- Abrechnung: via bestehendes `settle_multimatch_parlays` (Multi-Match-Parlay mit `legs`, ohne `combo_legs`) nach Spielende — Block 1 fasst den Multibet-Schein nicht an (match_time „Multibet" → nicht stale → übersprungen, wird nicht fälschlich void).
- VERIFIZIERT: Live-Run baute „3er Live-Kombi @ 1.57" (Džiugas–Banga Über 0,5; Sochi–Kostroma Über 1,5; KR Reykjavik–Stjarnan Über 1,5); Screenshot zeigt Karte „PARLAY · 3 SPIELE" im Banker-Tab mit korrektem Analysetext + 9★. Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-19c — Live-Mehrfachwetten (Dreier) landen im Live-Bereich statt Community
- Owner-Meldung: ein von TipjarLogic geposteter Dreier ist eine Live-Wette, wurde aber im Community-Bereich statt im Live-Bereich angezeigt.
- Ursache: bei MEHR-Spiel-Parlays (Dreier) liefert `_tip_match_teams` (None, None) → weder Post-Zeit-Erkennung noch `live_annotate_sync` erkannten sie als live → Status blieb "pending" → Community.
- Fix (server.py): neue Helper `_leg_teams(leg)` + `_parlay_live_fixture(live, legs)`. Ein Multi-Spiel-Parlay gilt jetzt als LIVE, wenn IRGENDEIN Leg gerade in-play ist.
  - `create_tip`: Post-Zeit-Live-Check prüft jetzt auch die Legs eines Parlays.
  - `live_annotate_sync` (läuft periodisch in `live_annotate_loop`): promotet Multi-Spiel-Member-Parlays mit einem Live-Leg zu status="live" → wandert automatisch von Community in den Live-Bereich (Community-Query = status=pending, Live-Query = status=live).
- Bestehender Produktions-Schein korrigiert sich nach Deploy selbst beim nächsten Annotate-Lauf (sofern Legs noch laufen; sonst wird er abgerechnet).
- VERIFIZIERT: Unit-Tests (`_leg_teams` parst „A – B/vs", `_parlay_live_fixture` findet Live-Leg im Dreier). Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-19b — Banger v2: Goal-Fest-Momentum + Brasilien/defensive Ligen raus
- Owner-Feedback (2 verlorene/kleine Scheine): Brasilien ist eine schlechte Über-Liga (spielen nichts, Tor erst in Nachspielzeit); bessere 10★-Banger gewünscht, wie France–England 4:6 → „Über 6 aufs 0:3" wäre ideal gewesen.
- Backend (server.py `live_autopost` Banger-Block v2):
  - **Goal-Fest-Continuation** (Live-Stand total ≥ 3, Druck vorhanden): reitet das Momentum → höchste Über-Linie im Banger-Fenster (`Über (total+1).5` bzw. `Über total.5`), Quote 1,40–3,20, **10★**. Beispiel: 0:3/40' → „Über 4.5 Tore" @~1,97.
  - **Offenes Spiel** (0/1 Tor, starker Druck): weiterhin „Asian Über 2.0 Tore" (Push bei genau 2), 9★.
  - Exakt 2 Tore → kein sauberer Banger, wird übersprungen.
  - **Brasilien/defensive Ligen ausgeschlossen** — sowohl im Banger- als auch im Fresh-Over-Block (verhinderte den 0:0-Verlust in Atletico).
- `_live_bet_landed`: neuer generischer Full-Match-Grader „Über N.5 Tore" (N beliebig, z. B. 3.5/4.5/6.5) → total ≥ N+1; team-spezifische Linien unberührt. `_live_odd` bepreist höhere Linien bereits generisch.
- VERIFIZIERT: Unit-Tests (Über 3.5/4.5/6.5 Settlement korrekt, team-spez. 0.5 unberührt, Asian-Push=None, Pricing höherer Linien), Live-Loop läuft ohne Crash (12 gepostet). Banger sind situativ. Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-19 — Neue "TipJarLogic Sicherheits-Kombi" (Owner-Style Safe-Slip)
- Owner-Wunsch (nach eigenem 150€-Gewinn): die KI soll automatisch sichere ~1,5-Kombis bauen — 3 Mini-Quoten (je ~1,10-1,20), die easy durchgehen.
- Backend (server.py `build_systems`): neuer System-Typ `tjlogic` = 3 Legs aus den torreichsten vorhergesagten Spielen — "Über 1.5 Tore" (torreich, ~1,18) bzw. "Über 0.5 Tore" (Absicherung, ~1,08), Gesamtquote ~1,4-1,7. Erscheint als ERSTER Schein in den KI-System-Picks. Jedes Leg rechnet sich deterministisch über die bestehende Tor-Engine ab (wie die bestehende Sicherheits-Kombi) → kann nicht hängen bleiben.
- Frontend: rendert automatisch über die generische Systems.jsx (risk=safe). i18n `sys.title.tjlogic` + `sys.sub.tjlogic` in ALLEN 8 Sprachen.
- BEWUSSTE ENTSCHEIDUNG: Legs sind Tor-Linien (immer abrechenbar), NICHT gemischte Spieler-Props (Mbappé-Schüsse), da diese im Sommer kaum verfügbar sind und Picks hängen lassen würden. Sobald Top-Ligen laufen, können Spieler-Prop-Legs ergänzt werden.
- VERIFIZIERT: /api/systems liefert tjlogic zuerst (3× Über 1.5 @1.18 = 1.64), UI-Screenshot zeigt die Karte oben mit korrektem Titel/Untertitel/Legs. Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-18c — Live-Benachrichtigungen nach Klasse + neue Häkchen (Banker/Value/Banger)
- Owner-Wunsch: jede Live-Klasse eine eigene Benachrichtigungsart, Mitglieder-Posts eine eigene, plus 3 neue Häkchen (Banker/Value/Banger) in jeder Sprache.
- Backend (server.py): `_tip_push_area` teilt KI-Live in `live_banker`/`live_value`/`live_banger` (Community-Live bleibt `live`). `_push_payload_for_tip` liefert pro Klasse eigenen Titel/Emoji/Sound: 🔥 BANGER LIVE (fire), 🟢 LIVE-Banker, 🔵 LIVE-Value, 🔴 LIVE-Pick. Community-Posts bekommen eigenen Push-Tag `tipjar-community` (überschreiben KI-Picks nicht mehr). `notify_all_push` filtert bereits pro Area → die neuen Häkchen wirken auch für echte Web-Pushes.
- Frontend (NotificationBell.jsx): `tipArea` granular; 3 neue Toggles (Banker cyan / Value volt / Banger orange) unter „Live Picks“ + separater Community-Live-Toggle; `fireAlert` mit Emoji je Klasse; localStorage + `/push/preferences` Sync.
- i18n.js: `bell.area.live_banker/value/banger` in ALLEN 8 Sprachen (EN/ES/DE/EL/FR/IT/AR/TR).
- VERIFIZIERT: Backend-Unit-Tests (Area-Klassifizierung + distinkte Payload-Titel/Tags), UI-Screenshot (3 farbige Häkchen), Toggle-Persistenz (live_banger:false in localStorage). HINWEIS: echte OS-Push-Zustellung nur auf echtem Gerät testbar. Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-18b — Live-Bereich in 3 Klassen: Banker / Value / Banger (voll automatisch)
- Owner-Wunsch: Live-Picks in 3 KI-gepostete Klassen aufteilen, jede mit Erklärung — nichts manuell.
  - **Banker**: sichere Live-Wetten, niedrige Quote (< 1,60) — z. B. "Über 0,5 Tore", DC/1X auf Favorit.
  - **Value**: Quote ≥ 1,60 — schönere Tipps mit etwas mehr Risiko/Wert.
  - **Banger**: die smarten Recovery-/Asian-Wetten, 9★, Quote 1,40–2,60 — neue Generierung "Asian Über 2.0 Tore" für offene (≤1 Tor), druckvolle Live-Spiele (Min. 15–72, starke Schüsse/Ecken); bei genau 2 Toren Einsatz zurück; wenn ein Team zurückliegt → Recovery-Framing.
- Backend (server.py): `live_autopost` — Block 1 backfillt Kategorie auf Alt-Picks (Quote-basiert) + settelt; Block 2/3 setzen Kategorie beim Posten; NEU Block 4 = Banger-Generierung (eigenes Stat-Call-Budget, damit Banger nicht verhungern). `_live_bet_landed` Asian-Über-2.0: 3+=won, genau 2=None→**void/Einsatz zurück**, ≤1=lost. `_live_odd` Asian-Pricing. `/api/tips` category-Filter unterstützt jetzt banker/value/banger (value schließt banger aus). Analysetexte sind Vorlagen-basiert (kein KI-Guthaben-Verbrauch), inkl. flexiblem Timing-Hinweis.
- Frontend (RateWall.jsx): Live-Tab mit 3 Unter-Tabs (data-testid live-cat-banker/value/banger) + Count-Pills + Erklärungsbox (live-cat-explain, Text wechselt je Klasse); Filter per Klick, TipCard-Badge um "BANGER" erweitert.
- VERIFIZIERT: testing_agent iteration_36 — Backend 11/11 (Filter-Partitionierung, Backfill, Asian-Settlement True/None/False, Pricing), Frontend 100% (Sub-Tabs, Explainer, Filter, Badges). Banger=0 im Preview ist erwartet (situativ). Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-18 — Eigenständige "Über 0,5 Tore"-Wetten verboten (nur noch als Zweit-Leg)
- Owner-Regel: eine reine Full-Match "Über 0,5 Tore" ist als Haupt-/Einzelwette wertlos → darf NUR noch als sekundäres Leg in einem Bet-Builder erscheinen. Team-spezifisches "<Team> Über 0,5 Tore" (dieses Team trifft) bleibt als Primär-Wette erlaubt.
- `_predictz_candidates` (server.py ~5504): erzeugt kein eigenständiges "Über 0,5 Tore" mehr (nur noch Über 2.5 / BTTS supplementär).
- `_forebet_candidates` (server.py ~5078): die 0.5-Over-Line aus der Single-Over-Schleife entfernt (nur 1.5/2.5 bleiben als Singles). Über-0,5-Legs in Kombis (favbb/favdc/o05each) unverändert.
- Smart-KI-Prompt (server.py ~6329): STRICT-Regel — nie plain Full-Match "Über 0,5" als Wette; nur als 2. Leg im Builder.
- VERIFIZIERT per Testskript: `_forebet_candidates` & `_predictz_candidates` liefern 0 eigenständige plain "Über 0,5 Tore", Team-spezifische + Combo-Legs bleiben erhalten; Backend syntax-clean, /api/tips/counts HTTP 200. Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-16 — Expert System + Mailbox + redesigned share images
- **Expert role (P0):** new `role: "expert"`. Ragazzi auto-promoted on startup (`_startup_seed`, idempotent, production-safe). Expert tips flagged via `_tag_expert` (read-time enrichment in `/api/tips`) → `is_expert`. TipCard renders them with an orange theme + "EXPERTE" badge. `GET /api/experts` powers the site-wide banner under the logo ("Wir suchen Experten! ... Das sind unsere Experten") with clickable expert chips → profile. PublicProfileModal shows an Expert badge (+Probezeit).
- **User Mailbox (P0, separate from push/alarms):** `inbox_messages` collection. New users get a welcome message + Expert invitation (Ja/Nein) on register; existing users backfilled on startup (`_backfill_inbox`, idempotent via `inbox_seeded`). Endpoints: `GET /api/inbox`, `POST /api/inbox/{id}/read`, `POST /api/inbox/read-all`, `POST /api/inbox/expert-accept` (→ instant Expert, trial), `POST /api/inbox/expert-decline`. Mail icon w/ unread badge in Header → dropdown panel (`Mailbox.jsx`). Accept sets `role=expert, expert_trial=true` immediately (owner choice: probation, no admin approval).
- **Share/Hall-of-Fame images redesigned (P1):** `_render_slip_image` rewritten — clean card-per-match layout, accent rail, bullet markets that WRAP (no more truncation like "Doppelte C…"), removed the cluttered center crest watermark, ISO kickoff times prettified (16.07.2026 14:00), footer summary fully contained (no overflow). Same function powers win-claim/Hall-of-Fame slips. Verified end-to-end via `/api/tips/{id}/share-image`.
- Tested: backend endpoints via curl (register→inbox→accept→experts), frontend via screenshots (banner, mailbox Ja/Nein, orange expert card), share-image generated & inspected (pending/won/live).


### CHANGELOG 2026-07-11e — Settlement Monitor + CRITICAL system-pick persistence fix
- **CRITICAL FIX:** the startup cleanup (`_startup_seed`) was deleting every pending `hqsys-*` system pick on each backend restart/deploy (id regex only whitelisted hqtip-/hqlive-/smart-/hqcur-). Added `hqsys-` → system picks now survive restarts (verified 6→6). Without this the whole "does a system ever win" tracking silently wiped daily.
- **New admin Settlement-Monitor** (`GET /admin/settlement-monitor` + panel in /insights): live status (OFFEN/GEWONNEN/VERLOREN) of all System picks (hq-system) and first-half (HT) combos, with per-leg breakdown, so the owner can watch auto-settlement in production. Verified via screenshot.

### CHANGELOG 2026-07-11d — System der Stunde uses full Anderlecht 3-leg combo
- The hour-system now bundles the complete **"Über 1.5 Tore 1.HZ + Beide Teams treffen + Über 2.5 Tore"** combo per high-scoring game (total≥4, both score) as ONE selection (combo_markets), odds ~4-9. Persisted as a parlay leg carrying all 3 selections (HT-aware settlement). Up to 2 combo games.
- `snapshot_systems` + Systems.jsx (SystemCard + visible filter) updated to allow single-selection combo systems; combo legs render as ✓-bulleted lines. Verified end-to-end (screenshot: card shows 3 legs @ 8.66).

### CHANGELOG 2026-07-11c — Anderlecht-style hot combo (single-match)
- New single-match bet-builder for goal-heavy games (predicted total ≥4, both teams score): **"Über 1.5 Tore 1. Halbzeit + Beide Teams treffen + Über 2.5 Tore"**, higher odds (~4-9), shown in the **Risk** filter. Persisted as a settleable combo (combo_legs kinds ht_o15/btts/o25).
- Added `ht_o15`/`ht_o25`/`ht_u35` to `_grade_goal_leg` (combo HT settlement). BTTS safety-net fixed to NOT strip the first-half "Über 1.5 Tore 1. Halbzeit" leg (only redundant full-match o15). All leg-grading unit-tested.

### CHANGELOG 2026-07-11b — First-half (HT) settlement + HT markets in System der Stunde
- **New `_grade_ht_selection`**: first-half goal markets (Über/Unter X.5 Tore 1. Halbzeit) now settled deterministically from the half-time score (fixtures carry ht_home/ht_away). Wired into `settle_multimatch_parlays` (falls back to LLM judge for non-HT markets; keeps leg open if HT data missing). Unit-tested, all pass.
- **System der Stunde** now leads with "Über 1.5 Tore 1. Halbzeit" for high-scoring games (the Lyon/Anderlecht style) + safe "Über 0.5 / Unter 3.5 Tore 1. Halbzeit" variants. Total odds still enforced >3.6 (test: 4.94).

### CHANGELOG 2026-07-11 — Best-Won/Cashed bucket + System der Stunde + rating overhaul
- **Rating honesty:** Live picks capped at 7★ (never banker/explosion), BTTS capped 6★, 9-10★ only for ultra-safe pre-match bankers. Value singles now need ≥62% win prob (was 42%); "post everything" fallback removed → fewer but safer picks.
- **BTTS replaced** by favourite-anchored bet-builders: `{Fav} Über 0.5 + Über 1.5 (+ Über 0.5 2.HZ)` and `{Fav} Über 0.5 + Doppelte Chance`. Underdog never required to score.
- **Live picks now show real league** (`_fixture_league_label`), friendlies = "Club Friendlies". Blacklist added: gumi, sportstoto, prievidza, "inter bratislava".
- **Settled counts fixed** (real won/lost/cashed from `/tips/counts`), 100-item cap removed (→1000), 24h purge runs on counts fetch. Won-system picks kept forever.
- **Best Won / Cashed Out bucket:** third settled button is ONE button, visually split into two triangles (gold "Best Won" + blue "Cashed Out"), opens ONE combined view = won Smart/Risk/Community/System picks + cash-outs. Green "Won" = normal AI/Live wins only. New `/tips?source=bestwon|normalwon`, counts `bestwon`/`won_normal`.
- **System picks persisted & auto-settled** (`snapshot_systems`, source=hq-system, is_parlay) so we can see if a system ever wins → surfaces in Best Won.
- **NEW "System der Stunde"** (Το Σύστημα της Ώρας): flash combo ~1h before kickoff, flexible full-match legs (team win/DC/over goals/BTTS), total odds MUST be >3.6, persisted per match-set, i18n in all 8 langs.

### CHANGELOG 2026-07-10 — Admin Pick-Manager + void status
- **Fixed P0:** hanging Frankreich–Marokko Smart Pick `smart-rep-fra-mar` (player props "El Aynaoui 1+ Foul · Doué/Barcola 1+ Schuss · Über 1 Tor") set to status="void" (game over, unresolvable by API-Football).
- **New admin Pick-Manager** in `SecretInsights.jsx` (/insights): `GET /api/admin/pending-tips` returns all open (pending/live) tips grouped by source (Smart Picks/Live-Picks/KI-Picks/Mitglieder-Tipps). Admin can one-tap resolve each pick: Gewonnen/Verloren/Void/Löschen via existing `PUT /api/tips/{id}/status` (now accepts "void") + `DELETE /api/tips/{id}`. Solves recurring issue of custom player-prop picks hanging forever. Tested frontend 100% (iteration_35).

### CHANGELOG 2026-07-09 (night 2) — Curated Smart-Pick reports
- Posted 4 owner WC analysis reports as source="smart" picks (Frankreich–Marokko, Spanien–Belgien, Norwegen–England, Argentinien–Schweiz) — one report card per match, BYPASSING the 48h-fixture requirement (player props / qualify markets have no auto-fixture). Full multi-line German analysis per card. Plus a re-written (not 1:1) "iShowSpeed-Fluch" fun note. Seed: `backend/seed_smart_reports.py`, ids `smart-*` (protected from startup cleanup). match_time="" → dateless, so they do NOT auto-settle (informational reports; remove/settle manually).

### CHANGELOG 2026-07-09 (night) — Bundled AI new-count on main button
- Main "KI Single-Game-Picks" button now shows a red bundled count = SUM of new picks across Banker/Value/Risk, using the SAME `tj_cat_seen_ids` store as the tab badges (App.js `computeAiUnread` + `tj-cat-seen` window event kept in sync with RateWall `markCatSeen`). Opening the AI view marks all categories seen → clears main + tab badges together.
- `/tips/counts` `ai` now counts ALL pending AI picks (singles + combos, all days) so the grey total pill matches the red new-count universe (both = 28 verified).

### CHANGELOG 2026-07-09 (late) — Scraper reactivated (multi-day) + stability
- **AUTOPOST_PAUSED = False** — auto-scraper is LIVE again, but only posts from TOMORROW onward (`_AUTOPOST_MIN_KO` = start of tomorrow UTC). TODAY stays hand-curated (26 hqcur-* picks untouched). Forebet now scrapes today+tomorrow pages (`FOREBET_TOMORROW_URL`); today rows still feed match_predictions/system-slip but are skipped for picks. Predictz already covers tomorrow+day-after.
- **STABILITY RULE:** a pick, once posted for a match+category, is FIXED (same market+odds) until kickoff. Forebet posting replaced the old delete-and-replace (which caused 11:00 Über1.5 → 14:00 BTTS → 17:00 DC12 flipping) with a prior-check: if a pending pick for (home,away,category) exists, keep it. Same prior-check added to Predictz. Verified: 2nd scraper run posts 0 (no flip).
- Verified: today = curated only; tomorrow (2026-07-10) auto picks appear & categorised (Banker/Value/Risk).

### CHANGELOG 2026-07-09 (evening) — Web Push + tip visibility fix
- **Tip visibility fix:** market text no longer truncates (`Paide Handica…` → full `Paide Handicap +2.5`) and the real odds number is ALWAYS shown. For odds < 1.04 a tiny "pregame – live evtl. höher" hint now sits UNDER the number instead of replacing it (OddsValue.jsx + RateWall card row).
- **Web Push (real notifications, app closed / screen off):** VAPID keys in backend/.env; `pywebpush`. Endpoints `/api/push/vapid-public-key|subscribe|unsubscribe`; `notify_all_push` + `_push_payload_for_tip` (game+market details; LIVE picks → blue `/push-live.png` icon). `push_watch_loop` watches new tips (all sources, watermark=now on first run) and pushes. Frontend: bell toggle now also does `pushManager.subscribe` (iOS PWA-install hint), service-worker.js has `push`+`notificationclick` handlers. NOTE: real delivery needs a physical device after deploy — cannot be e2e-tested in this env.
- OPEN: (1) main "KI Single-Game-Picks" button should show bundled red sum of new picks (user approved, NOT built yet). (2) scraper reactivation multi-day + stability rule (awaiting user a/b).

### CHANGELOG 2026-07-09 (P.M.) — Category coverage, tab badges + CRITICAL fix
- **CRITICAL BUG FIXED:** `seed_showcase()` (runs on every startup/deploy) was deleting all TipJarHQ pending tips whose id didn't match `^(hqtip-|hqlive-|smart-)`. The curated `hqcur-*` picks fell through and got wiped on every backend reload/deploy. Regex now includes `hqcur-`. Curated picks survive restarts (verified).
- **Guaranteed categorisation:** every AI single now always lands in Banker/Value/Risk. Generator has an `else → value` fallback; `/api/tips?category=value` is the catch-all (`category NOT IN [banker,risk]`) so no pick can ever disappear.
- **Per-category red badges** (RateWall AI view): Banker/Value/Risk tabs show a one-time red unread count (localStorage `tj_cat_seen_ids`); clicking a tab clears its badge. Reads all AI pending, buckets risk=-1.5 handicap / banker / else value.
- Verified: 18 singles all categorised (11 banker, 6 value, 1 risk) + 8 value combos; badges 11/14/1 render and clear.
- OPEN: scraper reactivation for multi-day + stability rule (awaiting user a/b); Web Push feature (VAPID keys generated, not yet wired).

### CHANGELOG 2026-07-09 — Curated Single-Picks + Category rework
- **Single-Picks categorisation rewritten** (`_forebet_candidates`/`forebet_autopost`): RISK = ONLY favourite -1.5 handicaps; VALUE = sweet-spot 1.40–2.60 tips (Über/Unter, DC12, handicaps) + all bet-builder combos (1.40–3.0); BANKER = safe (winprob≥0.85). Removed duplicate `-hcpf15` generator; `-hcap15` odds calibrated (1.65/1.95/2.60). Predictz tips now carry `category`.
- **CURATED MODE (owner)**: `AUTOPOST_PAUSED = True` in server.py — Forebet/Predictz auto-scrapers do NOT post/overwrite single picks while curated. The Single-Picks feed is a hand-picked list of exact bookmaker (BetScore) legs+odds seeded via `backend/seed_curated_picks.py` (18 singles + 8 bet-builders, 26 total). Astana -1.5 @5.50 = RISK. To resume automation set AUTOPOST_PAUSED=False and re-run scrapers.
- Settlement unchanged & compatible: singles via `judge_market` (LLM, full-time score), combos via `_grade_goal_leg` (deterministic `kind` per leg). NOT yet live-verified (matches settle this evening).
- Frontend: RateWall card badge now shows correct BANKER/VALUE/RISK label+colour (was VALUE/BANKER only).


### CHANGELOG 2026-07-15i — France–Spanien hing in Smart Picks: settle_attempts-Limit reset
- Ursache: Der France–Spanien Smart-Pick blieb pending, weil der ALTE Code (vor der Teamnamen-Übersetzung) sein Versuchs-Limit (SETTLE_MAX_ATTEMPTS=240) aufgebraucht hatte → wurde in `settle_hq_combos` dauerhaft übersprungen, obwohl die Abrechnung jetzt funktioniert.
- Fix: `_cleanup_smart_junk` (Startup) setzt `settle_attempts` für alle hängenden Parlays (pending/live, is_parlay) auf 0 zurück → beim nächsten Abrechnungslauf werden sie mit der reparierten Engine neu versucht.
- Verifiziert E2E: Pick mit attempts=240 → vor Reset pending (übersprungen) → nach Cleanup+Settle "lost" 0:2 → verlässt Smart Picks.
- Greift auf Produktion nach **Deploy** (Startup-Reset läuft beim Neustart).

### CHANGELOG 2026-07-15h — Einzigartige LLM-Analysen statt Standard-Text + Rotations-Kontext
- **Problem:** Single Picks (und Qualifikations-Picks) hatten immer denselben festen Standard-Analyse-Text.
- Neu: `llm_pick_analysis()` (Emergent LLM Key, AI_MODEL) generiert pro Pick eine EINZIGARTIGE, meinungsstarke deutsche 2-3-Satz-Analyse mit echtem taktischen/statistischen Grund. Template bleibt als Fallback. Eingebaut in beide Single-Pick-Generatoren (Forebet + Predictz) und in `qualifier_autopost`.
- **Rotations-/Belastungs-Kontext:** `_matches_between` liefert jetzt auch die Ergebnisse der Zwischenspiele (z. B. "0:3 verloren") → die LLM kann Rotation/Fokus aufs Europa-Spiel erkennen und erwähnen.
- Qualifikations-Analyse-Prompt enthält Aggregat, zurückliegendes Team (muss offensiv → Tore/Verlängerung), Weiterkommen und Belastung. Verifiziert: Kairat-Beispiel wird sinngemäß exakt so generiert; alle 6 Qualifikations-Picks + Single Picks haben unterschiedliche, sinnvolle Texte.
- HINWEIS: jede Pick-Erstellung ruft nun das LLM (verbraucht Universal-Key-Guthaben).

### CHANGELOG 2026-07-15g — Qualifikations-Picks: Spielbelastung/Erholung erkennen
- `qualifier_autopost` prüft jetzt zusätzlich per `_matches_between`, wie viele Spiele jedes Team ZWISCHEN Hin- und Rückspiel hatte: 0 = ausgeruht (Land in Sommerpause, z. B. Bulgarien/Albanien), ≥1 = belastet (aktive Sommerliga, z. B. Skandinavier).
- Fließt ein in: Analyse-Text ("X belastet (1 Ligaspiel), Y ausgeruht") UND Sterne-Rating (müder Favorit vs ausgeruhter Außenseiter → −2★; ausgeruhter Favorit vs belasteter Gegner → +0,5★).
- Verifiziert mit echten Daten: Astana (1 Ligaspiel dazwischen) vs Dinamo Tirana (Pause) → Rating 8→6; Rigas FS belastet → 6; beidseitig ausgeruhte Duelle behalten volle Bewertung.

### CHANGELOG 2026-07-15f — Hinspiel-Bewusstsein: Qualifikations-Picks für Zweikampf-Duelle
- Neue Engine `qualifier_autopost()` (im Smart-Loop): erkennt Rückspiele von Qualifikations-Duellen (CL/EL/ECL/Kontinental via Liga-Keywords), holt das HINSPIEL-Ergebnis via API-Football H2H (`_h2h_first_leg`) und baut den smartesten sicheren Pick:
  - klarer Aggregat-Vorsprung → "{Leader} qualifiziert sich" (@1.12/1.35 je nach Vorsprung) + "Über 1.5 Tore" wenn Hinspiel torreich (≥2).
  - ausgeglichenes Duell → Doppel-Handicap ±1,5 auf beide Seiten (gewinnt, solange keiner mit 2+ Toren gewinnt).
- **Aggregat-Abrechnung**: neue kinds `qualify` (Hin+Rückspiel-Summe, ET/Elfmeter-Flag als Tiebreak; qual_ctx auf dem Leg gespeichert), `ah15_home`/`ah15_away`, `total_o`. In `_grade_player_leg`.
- Verifiziert: `_h2h_first_leg` fand real Kairat 2:1 Sutjeska (08.07.); Aggregat-Grading korrekt (Kairat weiter bei 0:0, raus bei Sutjeska 2:0); Handicap korrekt. LIVE-Lauf erzeugte 6 echte Qualifikations-Picks (Astana, Pyunik, Rigas, Paide-Handicap …).
- Antwort auf Nutzerfrage: Die Engine schaute VORHER NICHT auf Hinspiele — jetzt tut sie es.

### CHANGELOG 2026-07-15e — System-Picks ("System der Stunde") rechneten nie ab
- Zwei Bugs in `settle_multimatch_parlays` (zuständig für System-Picks & Member-Parlays):
  1) **Versuchs-Limit vor Anpfiff aufgebraucht:** System-Picks entstehen ~1h vor Anstoß. Das 8-Versuche-Limit wurde abgearbeitet, WÄHREND die Spiele noch liefen → nach Spielende nie wieder versucht → blieb ewig "OFFEN". Fix: Limit greift erst, wenn ALLE Spiele vorbei sind (`due` = jetzt ≥ letzter Anstoß + 2h); Attempts zählen nur noch dann. Limit auf 12 erhöht.
  2) **Kein Datescan-Fallback:** Für obskure Vereine (Vikingur Reykjavik, Gyori ETO, Ararat-Armenia …) scheiterte `find_finished_fixture` (Saison/Diakritika). Jetzt Fallback auf `_datescan_fixture` (scannt alle Spiele am Tag, matcht beide Teamnamen).
- Verifiziert E2E mit echtem "System der Stunde" (4 Legs, 14/07): settelt als **lost** — Levski Sofia 4:0 Borac war zur HALBZEIT 0:0, daher riss "Über 0,5 Tore 1. HZ" (die anderen 3 Legs gewonnen).
- Greift auf Produktion nach **Deploy** (bestehender Pick hat attempts<12 → wird erneut versucht & abgerechnet).

### CHANGELOG 2026-07-15d — KERN-BUG: lokalisierte Teamnamen blockierten JEDE Smart-Pick-Abrechnung
- Ursache, warum France–Spanien (und andere Smart-Picks) nie abrechneten: Picks speichern Teamnamen in der App-Sprache ("Frankreich"/"Spanien"), aber API-Football nutzt Englisch ("France"/"Spain"). `resolve_team_id`/`find_finished_fixture` fanden nichts → keine Abrechnung.
- Fix: `COUNTRY_NAME_EN`-Map (DE/ES/FR/IT → EN Nationalmannschafts-Namen) + `_en_name`-Helfer; angewandt in `resolve_team_id`, `find_finished_fixture` und `_datescan_fixture` (Gegner- & Heim/Auswärts-Matching). Fehlerhafte team_cache-Einträge (team_id=None) werden beim Start geleert, damit die Map greift.
- Voreilige 8h-Löschung hängender Smart-Picks wieder ENTFERNT (Nutzer will Abrechnung, nicht Löschung).
- Verifiziert End-to-End gegen echtes Spiel (Frankreich 0:2 Spanien, fixture 1585131): alle 8 Legs korrekt gegradet, Schein settelt als **lost** (Mbappé/Yamal 0 Schüsse aufs Tor, Yamal 0 Schüsse, Doué 0 Fouls → 4 Legs gerissen).

### CHANGELOG 2026-07-15c — Hängende abgelaufene Smart-Picks (France) sofort entfernen (ZURÜCKGENOMMEN)
- Ein pending Smart-Pick, dessen Spiel längst vorbei ist und der nicht abgerechnet werden konnte (kein API-Fixture), hing bisher bis zur 36h-Löschung fest. `_cleanup_smart_junk` löscht jetzt beim Start alle pending Smart-Picks > 8h nach Anstoß → France–Spanien verschwindet nach Deploy sofort. Zukünftige Picks bleiben unberührt (nur vergangene). Verifiziert.

### CHANGELOG 2026-07-15b — Benachrichtigungen: Flut gestoppt, Deep-Link, Sammel-Alarm + France–Spanien Abrechnung
- **France–Spanien / "qualifiziert sich" abrechenbar:** `_grade_player_leg` rechnet "{Team} qualifiziert sich" jetzt über das Sieger-Flag des Spiels (inkl. Verlängerung/Elfmeter, Tor-Fallback) ab; Fixture-Daten tragen `home_winner`/`away_winner`. Legacy-Legs bekommen `home`/`away` aus dem Tip injiziert. → Der France–Spanien Mega-Builder rechnet sich nach Deploy automatisch ab (sofern noch nicht gepurged).
- **Benachrichtigungs-Flut behoben (Punkt 2):** OS-Pushes nutzten eindeutige Tags (`tj-{id}`) → stapelten sich → endloses Wischen. Jetzt FESTE Tags (`tipjar-pick` / `tipjar-live`) → ein Rückstau kollabiert zu EINER sichtbaren Benachrichtigung (neueste gewinnt).
- **Sammel-Benachrichtigung (Punkt 4):** `push_watch_loop` sendet bei mehreren frischen Picks EINE Digest-Push ("⚡ N neue Picks …") statt vieler einzelner; bei genau einem Pick eine Detail-Push mit Deep-Link.
- **Deep-Link (Punkt 3):** Push-`url` = `/?pick={id}&area={area}`; Service-Worker navigiert dahin; App.js `jumpToPick` öffnet die Ansicht und scrollt/hebt den Pick hervor (`#pick-{id}` Anker + Glow). Verifiziert per Screenshot.
- **In-App-Alarme (Punkt 4):** Jede Toast-Meldung hat jetzt "Pick ansehen" → springt via `tj-open-pick` direkt auf den jeweiligen Pick.
- HINWEIS: Echte OS-Push-Zustellung ist nur auf echten Geräten testbar; Payload/Tag/Deep-Link-Logik ist verifiziert. Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-15 — Auto-Abrechnung für Spieler-Prop Mega-Bet-Builder (Smart Picks)
- Smart Mega-Bet-Builder (Spieler-Props) konnten bisher NICHT automatisch abgerechnet werden → blieben pending & wurden nach 36h gelöscht (nie in Won/Lost). Jetzt gebaut:
  - `_player_stats_for_fixture` holt per-Spieler Match-Stats aus API-Football `/fixtures/players` (Schüsse, Schüsse aufs Tor, Fouls begangen/gezogen, Karten, Tore, Paraden) + Team-Karten-Summen. An echten Daten verifiziert (Villarreal–Atlético, 45 Spieler geparst).
  - `_grade_player_leg` rechnet jedes Leg deterministisch: sot/shots/fouls_c/fouls_d/scorer/card/saves + "Beide Teams eine Karte". "qualifiziert sich" bleibt ungradbar (None) — wird aber vom aktuellen Generator nicht mehr erzeugt. Inkl. Text-Parser-Fallback für Legacy-Märkte ("Mbappé 1+ Torschüsse" etc.).
  - Generierung erhält jetzt `kind`/`player`/`line`/`team` in combo_legs (vorher als "player" überschrieben).
  - `settle_hq_combos`-Query um `source:"smart"` erweitert (verarbeitete vorher NUR hq-auto) — das war der eigentliche Grund, warum Smart-Builder nie abgerechnet wurden.
  - Ziel-Tab nach Abrechnung: Sieg → **Best Won**, Niederlage → **Lost**, Cash-Out → **Cashed Out**.
- Verifiziert: Unit-Tests (strukturiert + legacy) + echter End-to-End-Test (Parlay mit Verlierer-Leg → lost, alle Gewinner → won).
- HINWEIS: greift auf Produktion erst nach erneutem **Deploy**.

### CHANGELOG 2026-07-14 — Best Won / Cashed Out Button lesbar gemacht
- Der diagonale Split-Button schnitt beide Labels an der Diagonale ab. Fix (RateWall.jsx): Farbflächen (beschnitten) und Text (nicht beschnitten) getrennt — "Best Won" oben-rechts, "CASHED OUT" unten-links, beide vollständig lesbar in Ruhe- & Aktiv-Zustand. Button etwas höher (68px). Per Screenshot verifiziert.

### CHANGELOG 2026-07-14 — Alte verlorene WM-Demo-Scheine entfernt
- `seed_showcase` erzeugte bei jedem Backend-Start zwei verlorene Demo-Scheine neu: "Portugal & Messi – Winner & Top Scorer" (WM) und die Häcken/Portugal-Spanien-Kombi → tauchten dauerhaft in der "Verloren"-Sammlung auf. Beide entfernt: Seeding + `upsert` gelöscht, aus `allowed_ids` entfernt und beim Start explizit gelöscht (können nicht wiederkommen). Der gewonnene Schaufenster-Schein "Schweiz–Kolumbien" (Best Won) bleibt. Verifiziert (beide weg, won bleibt).
- HINWEIS: greift auf Produktion erst nach erneutem **Deploy**.

### CHANGELOG 2026-07-14 — Fehl-Ideen im "Eingegangene Ideen"-Feed entfernt (Screenshot-Klärung)
- Die 2 "blanken" Ideen waren KEINE textlosen Einträge, sondern Fehl-Einreichungen mit Text aber Status "not_actionable"/"no_fixture" ("KEIN TIPP" / "KEIN SPIEL GEFUNDEN"), z. B. Test-Text + alte iShowSpeed-France-Marokko-Notiz. Der Feed zeigte diese noch an.
- Fix: `recent_smart_ideas` liefert jetzt NUR Ideen mit `status="used"` (Ideen, die tatsächlich zu einem Smart Pick wurden). `_cleanup_smart_junk` löscht zusätzlich alle smart_ideas mit `status != "used"`. Per Testseed verifiziert (used bleibt; not_actionable + no_fixture gelöscht; Feed = nur used).
- HINWEIS: greift auf Produktion erst nach erneutem **Deploy** — dann verschwinden die 2 Fehl-Ideen automatisch beim Backend-Start.

### CHANGELOG 2026-07-14 — Refactor Stufe 1: Pydantic-Modelle ausgelagert (verhaltensneutral)
- Alle 15 Request-Modelle (RegisterInput, LoginInput, TipSaveInput, GiftInput, CheckoutInput, StatusInput, SmartIdeaInput, IdeaRateInput, VisitInput, PushSubIn …) aus `server.py` in neues `backend/models.py` verschoben; `server.py` importiert sie oben. Rein organisatorisch, KEINE Logikänderung. server.py 5947 → 5863 Zeilen. Per curl verifiziert: login, /auth/me, /tips/counts, /tips?source=smart, /systems, /credits/packages, /push/vapid-public-key, /track/visit, register-Validierung (422) — alle OK. Frontend lädt e2e.
- OFFEN (P1, größere Folge-Stufen, jeweils mit Tests): Config/Infra → core.py; danach Domain-Splits (auth, tips, credits, wins, engine/scraper, smart/systems) in eigene Router-Module.

### CHANGELOG 2026-07-14 — Blanke Smart-Ideen verhindert + alte Reports (France–Marokko) auto-gelöscht
- **Blanke "Eingegangene Ideen" behoben (Root-Cause):** `submit_smart_idea` legte den öffentlichen Feed-Eintrag SOFORT an — auch bei reinen Bild-Uploads ohne Text → blanke Karte (@user + Bild-Icon, kein Inhalt). Fix: Feed-Eintrag wird nur noch bei echtem Text (≥6 Zeichen) erstellt; Bild-only-Einreichungen werden weiter zu einem Pick verarbeitet, erzeugen aber KEINE blanke Feed-Karte. Per curl verifiziert (Bild-only → created:false, Feed bleibt leer).
- **Startup-Cleanup `_cleanup_smart_junk()`** (läuft bei jedem Start, inkl. Produktion nach Deploy): (1) löscht blanke `smart_ideas` (Text leer/nur Whitespace/None); (2) löscht alte Smart-**Report**-Picks (report=True, älter als 3 Tage) + alle `status:void` Smart-Picks → entfernt fertige Karten wie France–Marokko. Frische Reports (<3 Tage) bleiben erhalten. Per Testseed verifiziert (fra-mar 5d → gelöscht, frischer Report → bleibt, 2 blanke Ideen → gelöscht).
- HINWEIS: Die 2 blanken Ideen + France–Marokko liegen auf PRODUKTION → verschwinden automatisch nach **Deploy**.

### CHANGELOG 2026-07-11f — Mega Bet-Builder (Smart Picks) UI-Fix VERIFIZIERT
- Alle Spieler-Props eines Matches werden zu EINEM massiven "Mega Bet-Builder" gebündelt (Fouls/Schüsse/Schüsse aufs Tor + Über 8.5 Ecken), Frankreich-Picks + die zwei obersten Fehl-Meldungen entfernt (Backend `smart_autopost`).
- **BUGFIX:** `smart_autopost` befüllte nur `combo_legs`, ließ `legs: []` leer → Frontend (RateWall) rendert `tip.legs` und zeigte daher nur die Titelzeile statt der 7 Props. Fix: `smart_autopost` befüllt jetzt zusätzlich `legs` (ein Display-Leg mit `match` + allen `selections`/`sel_odds`), analog zu AI-Bet-Buildern. Bestand-Pick per Backfill migriert. Per Screenshot verifiziert (Argentina–Switzerland, 7 Legs @3.97, sauberes Layout, kein Clipping).

## Tech Stack
FastAPI + MongoDB (motor) + React (CRA/craco) + Tailwind. framer-motion, canvas-confetti, lucide-react.
AI: Gemini 3.1 Pro via emergentintegrations (EMERGENT_LLM_KEY). Payments: Stripe (test). Object storage:
Emergent. Auth: JWT Bearer. Scrapers: Playwright/Chromium (forebet.py, predictz.py). Results + player
stats: API-Football Pro (api-sports.io, 7500 req/day, season stats available).

## Personas
Tipster, Rater, Anonymous visitor (bell), Admin (settles tips).

## Current areas (tips window tabs + header quick-views)
Order (left→right): 1) KI Single-Game-Picks (ai, source=hq-auto) 2) Smart Bets (smart) 3) KI-System-Picks (systems) 4) Community (members) 5) Live 6) Abgerechnet (settled).
1. KI Single-Game-Picks (source=hq-auto) — Forebet/Predictz bankers/value + dynamic single-game multi-leg Bet-Builders (both teams score + nested Über-lines, 1-goal safety buffer).
2. Smart Bets (source=smart) — player props from API-Football season stats.
3. KI-System-Picks (GET /api/systems) — 4 systems: lock / value / risk / gamble.
4. Community Picks (source NOT in [hq-auto, smart]).
5. Live Picks (status=live) — realistic Poisson-priced live odds (goals-needed + time-remaining).
6. Abgerechnet/Settled — checkered-flag tab; Won(left)/Lost(right) clickable toggles reveal slips on click; settled slips auto-deleted after 24h.

## Key backend endpoints
- GET /api/tips?source=ai|smart|members&status=pending|won|lost|live&window=24|48|48plus&sort
- GET /api/tips/counts -> {ai, ai_total, members, live, systems, smart, settled}
- GET /api/systems, GET /api/system-slip
- POST /api/admin/settle-now, /api/admin/forebet/run, /api/admin/predictz/run,
  /api/admin/autotips/reset, /api/admin/smart/run, /api/admin/smart/reset
- Auth login body key: "email" OR "username" + "password".

## Implemented history (condensed — see git log for full detail)
- Core: auth (JWT, optional email), landing + animated jar, notification bell, submit+AI analyze,
  Rate Wall (filters, 10-star, streak), leaderboard, credits (Stripe buy/gift/redeem), i18n EN/DE/EL/FR/IT,
  admin settle, referral rewards, email verify (Resend/dev-link), content moderation (Gemini vision+text).
- Auto-tips: Forebet (primary, DNB + goals bankers w/ kickoff time) + Predictz (supplementary BTTS/Over),
  source anonymised as "hq-auto"/"TipJarHQ", league whitelist, realistic odds, chromium self-heal.
- Systems: match_predictions store -> 4 systems (lock/value/risk/gamble), whitelist-only slip.
- Auto-settlement: API-Football Pro, every 15 min, only finished games, quota-safe; settled tips kept
  (won/lost visible under status filter). Verified won/lost render in UI.
- Navigation: 4 (now 5) green quick-view buttons w/ live counts; tab switcher inside tips window;
  per-area notification toggles.

## Session 2026-07-08 (fork continued)
- Smart Bets "idea chatbox" (SmartLab): logged-in users send an insider hint (text + up to 3
  optional images) → POST /api/smart/idea (multipart) → Gemini turns it into a clever Smart Pick.
  MUST have a real kickoff: find_upcoming_fixture() via API-Football; only posts if a fixture is
  found AND kickoff is within 48h (else created:false, reason no_fixture/too_far/not_actionable).
  Homepage SmartX quick-view button has a pulsing spoiler badge "Mit der KI reden". Tested
  iteration_33/34 PASS + 48h window verified (El Clásico 25/10 → too_far).
- Blacklists: Blumenau + code `brc`; Canadian Championship (`forge`, `saint-laurent`); ~30 obscure
  Brazilian leagues (Série C/D, all A1/A2/A3 state tiers, Paulista/Carioca/Mineiro/Catarinense/etc.).
  Only Brazil Série A/B kept. Owner shorthand: "#<team> @blacklist" = delete tip + blacklist league.
- Dynamic single-game Bet-Builder: both teams score + nested Über-lines (1-goal safety buffer,
  up to 5 legs). Generic Über-line settlement (parse "über N.5"). Combo odds cap raised to 25.0.
- Multi-match parlay auto-settlement: settle_multimatch_parlays() grades each leg via API-Football +
  judge_market; lost if any leg loses, won if all win; writes per-leg status. In loop + /admin/settle-now.
- Settled area "Abgerechnet": new tab (checkered-flag), Won(left)/Lost(right) toggles reveal slips on
  click; purge_settled_tips() deletes non-seed won/lost tips >24h; set_status stamps settled_at.
  counts now include `settled`. Tested iteration_31 (columns) + iteration_32 (toggles) — PASS.
- Renamed AI Picks -> "KI Single-Game-Picks"; tab order: ai, smart, systems, members, live, settled.
- Removed fake `seed-community-pending` showcase (used real UPCOMING fixtures w/ fabricated results).
- LIVE odds fix: _live_odd now Poisson-based on goals-needed + time-left (Über 1.5 @45'/0:0 = ~2.21,
  was 3.75). Callers pass current total goals.


## Session 2026-07-07 (this fork)
### Bug fix — scraper robustness (verified)
- Root cause of intermittent "0 tips": during Playwright scraper runs, an app reload/shutdown could
  hang waiting on the mid-flight scrape task (NOT event-loop blocking — proven: /api/tips stayed at
  0.01s latency during an active scrape). "won cards visible: 0" earlier was a transient reload window.
- Fix: SCRAPE_TIMEOUT=90s hard cap via asyncio.wait_for on every scrape (forebet, predictz, time-index);
  background loops tracked in _BG_TASKS and cancelled+awaited in the shutdown handler. Backend now
  restarts cleanly in ~1.4s. Won/Lost tips confirmed rendering in UI.

### NEW Feature — Smart Bets (player props) (verified, 9/9 backend + frontend)
- Computes player props from API-Football /players season stats (shots, shots on target, fouls
  committed/drawn, yellow cards, goals=anytime scorer, GK saves). Poisson-based probability -> Apex
  rating + estimated odds. Markets in German (e.g. "X — Über 0,5 Schüsse aufs Tor (1+)", "Über 1,5
  Paraden", "Torschütze (Anytime)", "Über 0,5 mal gefoult", "sieht eine Karte").
- Only regular starters (lineups>=8) of teams in upcoming WHITELIST match_predictions (next 5 days).
  Team players cached 24h (db.player_stats_cache). smart_autopost caps 14 matches, 4 props/team.
- Stored as source="smart", league "TipJarHQ Smart Bet". smart_loop every 12h. Excluded from
  settle engine (score-based settle can't judge props) and from members/settle queries.
- Frontend: 5th quick-view button (Header, data-testid=view-smart-btn, Brain icon, grid-cols-5),
  tab tabview-smart in tips window, RateWall view="smart" -> source=smart. i18n nav.viewsmart (5 langs).
- DATA LIMITATION (told to user): API-Football does NOT provide offsides, corners, throw-ins,
  free-kicks, headed/long-range goals, corner-by-10th-minute, team-scores-first -> those props omitted.
  Also July = mostly minor leagues -> low candidate volume until top leagues resume.

## Session 2026-07-08 (fork)
### Win-claim: branded slip image + 404 fix + market wording + UNDER markets
- FIXED 404 "Bild nicht sichtbar": claim_win uploaded via put_object but never created the
  db.files record the /files/{path} route requires → now inserts it.
- Win claims no longer store the raw bookmaker screenshot. `_render_slip_image()` (PIL,
  FreeSans) renders a standardised TipJar-branded won slip from the extracted data: logo
  (Tip white/Jar green), WON badge, legs GROUPED by match (fixture titled once), German
  market names with "Über/Unter", total odds, @user, winnings. Shown in Hall of Fame.
- Match-key made accent- & language-insensitive (unicodedata fold + de↔en national-team
  aliases) so "Schweiz"=="Switzerland", "Víkingur"→"vikingur". `_system_match_keys` now
  PERSISTENT (all tips + parlay legs), since claims arrive after matches finish.
  WIN_MIN_PLAYED_LEGS 5→3 (TipJar systems can be 3-leg).
- Live claim accepts up to 4 images (multipart `files`); combined into one branded slip.
- extract_win_slip prompt updated: German markets, "Über/Unter", team totals ("Víkingur
  Über 0.5 Tore"), player shots ("Mbappé Über 0.5 Torschüsse"), 1X/X2.
- AI engine (_forebet_candidates): added UNDER markets (Unter 2.5/3.5 Tore) for low-scoring
  predicted games; _market_family knows u25/u35/under. Smart Picks restored (top leagues).
- Frontend: WinClaimModal multi-file live upload + "TipJar Best Wins" button + storage note;
  HallOfFame shows full branded slip (object-contain) with rank badge, no redundant footer.
- NOTE: preview only — user must redeploy to production (tipjarglobal.com).

### Smart Picks RESTORED with top-league-only player markets (owner reversal)
- Owner: keep the Smart Picks feature (tab + notification toggle); only generate player-prop
  markets for TOP leagues that actually offer them (EPL, La Liga, Serie A, Bundesliga, Ligue 1
  +2nd tiers, NED/POR/BEL/TUR/SCO, MLS, Saudi, WC/EC/Euro). EXCLUDE UEFA club qualifiers,
  Brazil, minor South-American/Asian leagues.
- Impl: `smart_autopost` re-enabled + `smart_loop` restarted; new `SMART_LEAGUE_CODES` gate in the
  upcoming filter. Frontend Smart quick-view button (Header.jsx) + tab (App.js) restored (5 nav
  items). NotificationBell smart toggle was never removed. Currently 0 (summer break) — populates
  when top leagues open.

### Value 72% + separate Banker + league whitelist on AI picks (verified: unit + real scrape + screenshot)
- Owner refined: min win-prob 72% for VALUE (odds ≥1.60), PLUS a separate safe BANKER
  category (winprob ≥0.85, low odds, for combos). Forebet picks one per match: prefer a
  VALUE pick, else the safest BANKER. Tips carry `pick_type` (value|banker) + `win_prob`.
- AI picks (Forebet + Predictz) now restricted to the recognised-league WHITELIST
  (FOREBET_SLIP_CODES / SLIP_LEAGUE_KEYWORDS) + women/youth blocked → removed Somalia (so1),
  Kyrgyzstan, Bolivia, Canada, Australia NPL, China L2 (cn3 blacklisted). Kept UCL/UEL/ECL
  qualifiers etc.
- Frontend: VALUE (volt) / BANKER (cyan) badge + "≈NN%" on each AI-pick card (RateWall.jsx),
  data-testid pick-type-{type}. Verified via screenshot.
- NOTE: July off-season → only European qualifiers whitelisted are live, so volume is low
  (4 bankers, 0 value right now). Value picks appear when book prices ≥1.60 at ≥72%.


### VALUE-ONLY rule (owner) — verified (unit + real Forebet scrape)
- Owner: stop 50/50 bets; only give ~80% win chance AT odds ≥ 1.60 (genuine value);
  auto-disable market families that lose too often (self-learning).
- Impl: `_forebet_candidates` now returns ALL options each with `winprob`; forebet_autopost
  applies REAL bookmaker odds (ensure_match_odds/_real_odd_for) and keeps only
  winprob≥0.78 AND odd≥1.60, one per match, ordered by winprob. `_banned_market_families()`
  disables any family with settled win-rate<0.55 over ≥8 samples. Constants VALUE_MIN_ODDS,
  WIN_PROB_MIN, MARKET_MIN_SAMPLE/WINRATE. Same odds/coin-flip gate added to Predictz.
- Coin-flip families (BTTS/Über2.5/O2.5+BTTS/correct-score) never posted; plain Über 0.5
  (1.08) filtered by 1.60 rule; prime value = Über 1.5 in high-scoring games + DC/DNB on
  solid favourites when book prices ≥1.60. Women/youth now blocked from AI picks too.
- TRADE-OFF (owner accepted): volume drops hard (~1 pick / 42 scanned). Relax WIN_PROB_MIN→0.72
  for more volume. Cleared 37 legacy non-value pending picks.


### AI Pick dedup + smartest-selection (verified: python unit + curl)
- ROOT CAUSE of "multiple overlapping tips per match": `_forebet_candidates` returned
  several markets per game and `forebet_autopost` posted each. FIX: it now returns exactly
  ONE "smartest" pick per match. Autopost also `delete_many`s any other pending hq-auto tip
  for the same (home,away,match_time) → strict one-pick-per-match. Cleaned 6 legacy dups.
- Selection priority (owner "den smartesten" + "Underdog trifft früh"): 1) UNDERDOG team-to-score
  "<Underdog> Über 0.5 Tore" when there's a clear favourite (pred 1/2) and the underdog is
  predicted to score (e.g. Real–Atlético → Atlético Über 0.5); else 2) best rating×odds
  (torreiches game → "Über 2.5 + Beide treffen"). Goals-picks ranked by rating AND predicted
  Ø goals so torreiche games surface first.
- Settlement verified for new markets via judge_market (8/8 cases: team-to-score, O2.5+BTTS,
  BTTS, DNB all correct won/lost).
- Systems UI: team names in system legs now wrap instead of truncating (Systems.jsx break-words).

### NEW Feature — LIVE engine (built; unit-tested; NOT yet seen E2E — no live games at build time)
- `live_autopost()` + `live_loop()` (every 3 min). Re-offers our pending pre-match hq-auto
  goal-picks (Über 0.5/1.5/2.5, BTTS, O2.5+BTTS, team-to-score) while the match is IN-PLAY and
  the bet has NOT yet landed, at now-higher live odds (source="hq-live", status="live",
  fixture_id, live_minute, live_score). Owner "nachreichen" rule.
- "Be careful" guard `_live_pressure_ok`: only re-offer if real pressure (shots on goal/corners)
  by minute band; dead/flat games (Schweiz–Kolumbien style) skipped, esp. late.
- Deterministic helpers unit-tested: `_live_bet_landed`, `_market_team_side` (unique-token, handles
  Real vs Atlético 'Madrid'), `_live_odd` (scales with minute), `_align_goals` (fixture orientation),
  `_find_live_fixture`. Live tips auto-settle won/lost from final score when match ends.
- Admin trigger: POST /api/admin/live-run. Frontend Live channel already fetches status=live.
- TODO (future): general corner-edge tips ("Team X mehr Ecken" when trailing + many corners) and
  half-based goal markets for ALL live whitelist games (currently only re-offers our own picks to
  stay quota-safe). Verify E2E once live matches are available.

## Deferred by user
- SESSION 2026-07-07 (part 3): Removed Leaderboard entirely. Redesigned Systems into 5
  winning-focused bundles (lock=Sicherheits-Kombi ~1.3x high win-rate, value=Banker-Kombi
  DC favorites, smartvalue=Value-Kombi BTTS/Over, risk=Risk-Kombi DC+BTTS, gamble=Jackpot
  3 likely correct-scores ~35-300x). Ratings capped at 9.0 auto; Predictz posts ONLY when
  Forebet agrees. Double-Chance real odds added. NEW "Earn Credits / Zeig deinen Gewinn":
  upload WON slip → Gemini Vision reads it → auto-award credits IF it matches a real TipJar
  SYSTEM (anti-fraud). Types: played (5+ legs, credits=legs count), posted (20), live (4+
  legs each >1.60, 20). Public Hall of Fame ("Best of", sorted by total odds). Endpoints:
  POST /api/wins/claim, GET /api/wins/hall-of-fame. Win rewards credited to received_credits
  (redeemable). Owner strategy notes in /app/memory/betting_strategy_notes.md (INTERNAL).
- KNOWN: system TITLES/subtitles/labels + win.* + Hall of Fame now localized in ALL 8
  languages via i18n keys (sys.* / win.*). Remaining: the individual bet MARKET strings
  inside system legs (e.g. "Über 0.5 Tore", "Doppelte Chance 1X + Beide treffen") are still
  server-side German — a future backend market-localization pass.


- SESSION 2026-07-07 (part 2): Rating discipline tightened — auto-tip ceiling now 9.0★
  (no 9.5/10 automated); Forebet DNB max 8.5, "Über 1.5" max 8.0, "Über 0.5" the top
  banker (9.0 only when high-scoring predicted). Predictz now ONLY posts when Forebet
  AGREES on the same match (owner distrusts Predictz alone). Real bookmaker odds via
  API-Football /odds now include Double Chance. SYSTEMS REDESIGNED for winning: 5 systems
  = Sicherheits-Kombi (4× Über0.5, ~1.3x, high win rate), Banker-Kombi (5× Doppelte Chance
  favorites, real odds), Value-Kombi (BTTS/Over2.5), Risk-Kombi (DC+BTTS bet-builders),
  Jackpot (3 most-likely correct scores, ~35-300x). Owner strategy notes saved to
  /app/memory/betting_strategy_notes.md (INTERNAL, never shown on site).
- KNOWN: systems bundle titles/subtitles are server-side German only (not localized) —
  future i18n pass.


- PayPal payouts + paid credits monetization: ON HOLD until 1,000 members (features exist, dormant).
- Full legal pages (Impressum/AGB/Datenschutz): BLOCKED on user providing business address data.
- Telegram integration; Stripe payments go-live.

## Backlog / Next (P1)
- Refactor server.py (~2650 lines) into modules: routes/, models/, scrapers/, engines/ (settle, smart).
- Smart Bets: expand markets when top leagues resume; consider team-corner props via /fixtures/statistics
  aggregation; add a probable-lineup source (~40min pre-kickoff) to refine which players start.
- Disable star rating on already-settled tips.
- Web-push (VAPID) for true off-site alerts; My Tips / track-record page.

## Credentials
- Admin: admin@tipjar.com / TipJarAdmin2026!  (login field "email" or "username")
- HQ: hq@tipjar.com / TipJarHQ2026!
- See /app/memory/test_credentials.md

## Changelog — 2026-06 (Best-Wins & Community-Gifting)
- Hall-of-Fame-Button umbenannt: "Credits verdienen" → "Zeig, was du mit TipJar gewonnen hast" (i18n key `win.showWin`, alle 8 Sprachen). Der Hero-Button oben bleibt "Credits verdienen".
- Klickbare Usernames: In den Tip-Cards (Rate Wall) und in der Hall of Fame sind Benutzernamen jetzt anklickbar. Klick öffnet das Wallet-Modal auf dem "Gift"-Tab mit vorausgefülltem Empfänger (nutzt bestehendes POST /api/credits/gift). Ohne Login öffnet sich das Login-Modal. Self-Gift wird geblockt.
- Best-Wins Vollansicht: Klick auf ein gewonnenes Slip-Bild öffnet einen Vollbild-Viewer (Lightbox) mit dem Username des Besitzers unten links (ebenfalls klickbar zum Verschenken). Kein Zoom, nur Vollansicht.
- Frühere Slip-Bild-Verbesserungen (Titel/Liga/Datum/Uhrzeit) + KI-Märkte (Doppelte Chance 12, Unter 2.5/3.5 mit echten Quoten) bereits in diesem Zyklus umgesetzt.
- Getestet: testing_agent iteration_27.json — 3/3 Flows bestanden, keine Fehler.

## Changelog — 2026-07-08 (Handicaps, Dedup, Blacklist, Button-Farben)
- KI-Tipps nutzen jetzt HANDICAPS: Außenseiter +3.5/+2.5/+1.5 (sicher, schlägt "Unter X.5"), Favorit -1.5 (Value). Korrekte Schreibweise "<Team> Handicap +X.5" auch beim Auslesen hochgeladener Scheine (Vision). Verifiziert: Kairat–Sutjeska → "Sutjeska Niksic Handicap +3.5".
- DEDUP: _dedupe_hq_tips() erzwingt EIN Pick pro Spiel (forebet+predictz), löscht risikoärmste Duplikate. Verifiziert: 8 einzigartige Spiele.
- BLACKLIST: TEAM_LEAGUE_BLACKLIST = golden, mogadishu, kahibah (in beiden Autopostern + Systemen).
- Doppelte Chance 12 + Unter 2.5/3.5 mit echten Quoten.
- UI: Header/Tab-Button "Member Picks" = GOLD, "Live" = blinkend BLAU.

## Changelog — 2026-07-08 (Profil, größere Slip-Schrift, Einzelquoten, Telegram-Teilen)
- (1) Klick auf @Username (Tip-Cards + HOF-Viewer) öffnet öffentliches PROFIL-Modal (Avatar, "Mitglied seit", Stats Tips/Gewinne/Erhalten, Button "Credits verschenken" → Gift-Flow). Neuer Endpoint GET /api/users/public/{username}.
- (2) Slip-Bild (Hall of Fame) mit deutlich größerer Schrift; Renderer unterstützt "pending"-Modus (OFFEN, Community-Tipp).
- (3) Einzelquoten je Leg: Vision extrahiert sel_odds; Anzeige als @-Chip. Auto-Backfill (background task) füllt Einzelquoten bei bestehenden Member-Parlays per gespeichertem Bild nach.
- (4/5) "Teilen"-Button nur bei PENDING Member-Picks → generiert TipJar-Slip-Bild (POST /api/tips/{id}/share-image) und teilt via Web Share/Telegram; Teil-Text enthält https://tipjarglobal.com.
- Getestet: testing_agent iteration_28 — 5/5 Flows bestanden, keine Fehler.

## Changelog — 2026-07-08 (2er-Bet-Builder + Fixes nach Test iteration_30)
- 2ER-KOMBI (KI): _forebet_candidates erzeugt Combo (schwaches Team Über 0.5 + Über 1.5 Tore) bei pred 1/2, weak_scores, total>=3. forebet_autopost bevorzugt Combo (höheres Risiko), sonst value/banker. Tip: is_parlay + 2 legs (kind team_o05/o15), erscheint im KI-Bereich. Neue settle_hq_combos() rechnet 2er-Kombis deterministisch aus Endstand ab (im settlement_loop + /admin/settle-now). Unit-getestet: Generierung, Anzeige, Abrechnungspfad.
- FIX (CRITICAL, iteration_30): POST /api/tips/analyze `files`-Feld gab 422 (Optional[List[UploadFile]]). Auf List[UploadFile]=File(default=[]) geändert → Mehrbild-Upload (bis 4) funktioniert.
- ENTFERNT: rohes Buchmacher-Bild auf Tipp-Karten (RateWall) — Regel „keine Rohbilder".
- Test iteration_30: Pflicht-Sterne (400/200), KI-Sort nach Anstoß, Share-Bild, Community-Rename, Publish-Sperre, kein Rohbild → alle PASS.

## Changelog — 2026-07-08 (Slip v2, Sterne-Pflicht, 4 Bilder, LIVE-Badge, KI-Sort)
- SLIP v2: volle Team-Namen (Auto-Shrink + 2-zeiliger Umbruch statt "…"), größere Schrift, Wasserzeichen gedeckelt (kein Clipping), roter LIVE-Kasten mit Minute+Ergebnis. Bugfix: Live-Community-Schein zeigte "WON" → jetzt OFFEN (ctype live_pending).
- LIVE-BADGE ÜBERALL: neuer live_annotate_loop (90s) setzt live_state{minute,score} auf jeden nicht-beendeten Einzeltipp, dessen Spiel laut API-Football läuft (sonst clear). RateWall-Karte zeigt roten LIVE-Kasten. KEINE Kanal-Verschiebung mehr — Live-Kanal = beim Posten bestimmt (create_tip, is_live_post via API-Football, alias-fähig Deutschland=Germany).
- STERNE-PFLICHT: create_tip verlangt self_rating 1–10 (sonst 400), speichert es als Eigen-Rating (tip_ratings + avg). SubmitTipModal: StarRating-Block, Publish gesperrt ohne Sterne.
- 4 BILDER: /tips/analyze nimmt bis zu 4 Files (analyze_tip mit mehreren ImageContent), speichert image_paths. Modal: Vorschau-Grid, entfernen, "Up to 4 images".
- KI-SORT: Single-KI-Bereich (source=ai) nach Anstoßzeit sortiert (nächstes Spiel zuerst), außer bei sort=top/hype. Verifiziert.
- Settle-Engine deckt Live-Einzeltipps ab. Dedup behält höchstes Risiko (Alias/gleicher Anstoß).

## Changelog — 2026-07-08 (Auto-Live für Einzel-Tipps zurück + Alias-Match)
- SOFORT: Ukraine (U-19) vs Germany (U-19)-Member-Schein auf Produktion nach Live verschoben (Admin-API).
- ROOT CAUSE: Auto-Live-Loop war komplett entfernt → einzelne live gepostete Scheine blieben in Community. Zusätzlich matchte _find_live_fixture keine Aliase (Deutschland≠Germany).
- FIX: member_live_loop wieder aktiv, aber NUR für Einzel-Tipps (is_parlay != True) → laufende Einzelwetten gehen automatisch nach Live (via API-Football, zuverlässig), Parlays (7er-Kombi) bleiben in Community. _find_live_fixture jetzt alias/sprach-fähig (Deutschland==Germany, via _team_core). Getestet: Einzel→live, Parlay→pending PASS.
- Braucht Redeploy für automatische Wirkung auf Produktion.

## Changelog — 2026-07-08 (Slip-Redesign, Community-Rename, Dedup, Live-Fixes)
- SLIP-BILD komplett neu (_render_slip_image): Liberation Sans (behebt Tofu-Kästchen bei €/ö/–), viel größere Schrift, TipJar-Crest als dezentes Hintergrund-Wasserzeichen, 1080px breit, sauberes Layout. Visuell verifiziert (Community + Live).
- BEREICHS-PILL auf geteilten Scheinen: "COMMUNITY PICK" (pending) / "LIVE PICK" (live). Bugfix: Live-Community-Schein wurde fälschlich als "WON"/grün gerendert → jetzt ctype "live_pending" (OFFEN/volt). tip_share_image rendert immer frisch (kein Cache) und setzt ctype nach Status.
- UMBENENNUNG "Mitglieder-Picks" → "Community Picks" (nav.viewmembers + bell.* in allen 8 Sprachen). Frontend verifiziert.
- DEDUP robuster (_dedupe_hq_tips): erkennt dasselbe Spiel auch bei Namensvariante (gleicher Anstoß + gleiches Heim ODER Auswärts, z.B. "Orange County SC" vs "Blues"), behält den HÖCHSTEN RISIKO-Pick (Value > Quote). Neuer Helper _team_core. Getestet: Hartford-Fall → Über 1.5 @1.20 bleibt, Über 0.5 @1.10 entfernt.
- LIVE-KLASSIFIZIERUNG nur noch beim Posten (create_tip: _looks_live_now + API-Football-Live-Check). Hintergrund-Promotion-Loop ENTFERNT → pregame-Scheine (z.B. 7er-Kombi) bleiben in Community. Settle-Engine deckt jetzt auch Live-Einzeltipps von Mitgliedern ab.

## Changelog — 2026-07-08 (Live-Erkennung robust via API-Football)
- ROOT CAUSE: Slip-Kickoff-Strings tragen keine Zeitzone ("18:00" als UTC gelesen → Spiel wirkt zukünftig). member_live_sync verschob CEST-Live-Spiele daher nicht.
- FIX: member_live_sync konsultiert jetzt zusätzlich API-Football (/fixtures?live=all) via _find_live_fixture → zuverlässige Live-Erkennung unabhängig von der Slip-Uhrzeit. Nur vom Loop selbst verschobene Tipps (live_auto=True) werden je auto-zurückgesetzt; manuell (Admin) verschobene bleiben live. Getestet: TZ-verschobenes Live-Spiel → korrekt nach Live (live_auto); manueller Live-Tipp bleibt.
- Braucht Redeploy: Produktion lief noch mit zeitbasierter Version (Olympiakos blieb bei Mitgliedern).

## Changelog — 2026-07-08 (Auto-Live-Loop + KI-Live-Picks)
- MEMBER AUTO-LIVE: neuer member_live_loop (alle 3 Min) verschiebt eingereichte Member-Tipps automatisch nach Live, sobald ihr Spiel läuft (_looks_live_now), und nach Spielende zurück auf pending (damit die Auto-Abrechnung greift). Getestet (pending→live→pending PASS).
- KI-LIVE-PICKS: live_autopost erzeugt jetzt zusätzlich FRISCHE Live-Goal-Picks (Über 1.5/2.5) für laufende Spiele (Minute 10–80, Stand 0-0/1 Tor) mit echter Torgefahr (_live_pressure_ok). Quota-Guard LIVE_STAT_CALL_CAP=20/Run. Verifiziert: 19 Live-Spiele → 8 Picks gepostet (u.a. Olympiakos vs Raków Über 1,5 @ 3,75), rendern korrekt im Live-Kanal mit LIVE-Badge + Teilen.
- Admin "→ Nach Live"/"→ Nach Offen" Button (PUT status akzeptiert live). i18n wall.toLive/toPending in 8 Sprachen (Bugfix: fehlender el-Eintrag + verirrtes i18n.js-Fragment am Dateiende entfernt).

## Changelog — 2026-07-08 (Admin: Tip nach Live/Offen verschieben)
- PUT /api/tips/{id}/status akzeptiert jetzt auch "live" (vorher nur won/lost/pending).
- RateWall: Admin-Button "→ Nach Live" / "→ Nach Offen" auf Member-Tip-Karten (data-testid admin-tolive-{id}). i18n wall.toLive/wall.toPending in allen 8 Sprachen.
- Zweck: einzelne Member-Picks manuell in den Live-Kanal schieben (z.B. Olympiacos-Pick d432a864 auf Produktion). Preview getestet (curl live<->pending). Produktion braucht Redeploy, dann Verschiebung per API/Button möglich.

## Changelog — 2026-07-08 (Auto-Live-Erkennung + Live teilbar)
- Eingereichte Member-Tipps landen jetzt AUTOMATISCH im Live-Kanal (status="live"), wenn das Spiel gerade läuft: Anstoß liegt max. ~150 Min zurück (bzw. ein Parlay-Leg). Neu: _kickoff_dt (inkl. ISO-Format) + _looks_live_now in server.py, angewandt in POST /api/tips. Verifiziert per E2E-curl (live/pending/abgelaufen korrekt).
- Teilen-Button (RateWall) jetzt auch für LIVE Member-Tipps (vorher nur pending): isShareable = status in [pending,live] & source nicht hq-auto/smart. share-image funktioniert für Live-Tipps (verifiziert).

## Changelog — 2026-07-08 (SEO-Fixes nach Audit)
- robots.txt (echte Textdatei, Allow + Sitemap-Verweis), sitemap.xml, llms.txt (korrektes Format) in /app/frontend/public/ angelegt.
- index.html: Open-Graph-/Twitter-Meta-Tags, Canonical-URL, sichtbarer #seo-fallback-Textblock (H1/H2/Listen) für Crawler → verbessert Text/HTML-Verhältnis. React ersetzt den Fallback beim Mount (verifiziert).
- Nicht behebbar: emergent-main.js unminified + blockierte externe Fonts (Plattform-Ressourcen). Muss neu deployt werden.

## Changelog — 2026-07-08 (Splash Snake-Border verifiziert)
- Splash Screen: statischer mint/grüner Rand aus allen 8 Lokal-PNGs entfernt (bestätigt: splash-de.png sauber). SVG-„Snake"-Rahmen (Volt #E1FF00, 2,5s, im Uhrzeigersinn, non-scaling-stroke, glow) läuft über den Viewport. Visuell per Screenshot verifiziert.

## Changelog — 2026-07-08 (Apex-Flamme + Slip-Korrektur)
- NEU "Apex-Flamme" 🔥: Bewertungsserie-Kachel ist anklickbar → Sprechblase mit Fortschritt zur 30-Tage-Serie. Bei 30 Tagen wird der kosmetische Orden vergeben (erscheint auf eigenem + öffentlichem Profil), und die Serie-Kachel verschwindet von der Startseite. Backend: _maybe_award_apex_flame (Schwelle APEX_FLAME_STREAK=30), rate-Response liefert apex_flame/apex_flame_new; public profile + user-Objekt tragen apex_flame. Rein optisch.
- Seed 'seed-community-pending' auf den ECHTEN BetScore-Schein korrigiert: 7 Legs (Sutjeska Hcp +3.5, mehrere Über 1.5, Connah's Quay Hcp +2.5, Unter 3.5), Gesamtquote 4.15, Einsatz 12 €, möglicher Gewinn 49,81 €.
- Getestet: testing_agent iteration_29 — alle Flows bestanden, 0 Konsolenfehler.


## Changelog — 2026-07-09 (Logo, Live-Settlement-Rootfix, Bewertungswand, Cashed-Out)
- Header-Logo: "TipJar" (Tip weiß / Jar mint) mit "GLOBAL" (orange) direkt darunter, leicht links (Team-Foto-Look). Hero-Shield: klickbarer Link "Tipjarglobal.com" (mint, glow) unter dem AnimatedJar.
- ROOT-FIX Live-Picks blieben ewig im Live-Bereich: `_parse_kickoff()` konnte ISO-Datum (`...T22:00:00+00:00`) nicht parsen → ko=None → zeitbasierte Abrechnung feuerte nie. ISO-8601-Parsing ergänzt. Zusätzlich `live_autopost`-Sweep: überfällige (>3.5h, LIVE_MAX_OPEN_HOURS) oder terminale (PST/CANC/ABD) Live-Picks werden zwangs-abgerechnet/void statt behalten. LIVE_STATUSES-Set eingeführt. Verifiziert (closed:2 bei Testfällen).
- Bewertungswand zeigt nur noch OFFENE Scheine: Won/Lost-Filter-Tabs aus der Wand entfernt (nur Pending + Live). Abgerechnete Scheine leben ausschließlich im "Abgerechnet"-Tab.
- NEU Status "cashed_out" (Ausgezahlt): wiederverwendbar, setzbar von Admin UND Ersteller (PUT /tips/{id}/status jetzt get_current_user + owner/admin-Check, 403 sonst). Hellblaues "CASHED OUT"-Badge; jedes Leg zeigt grünes "Gewonnen". Dritter Toggle im Abgerechnet-Tab (hellblau). Erscheint auch in Hall of Fame (type "cashed", aus tips-Collection gemappt). NICHT im 24h-Purge (bleibt als Trophäe). counts.settled inkl. cashed_out. i18n EN+DE ergänzt. E2E verifiziert (owner=erlaubt, non-owner=403, HoF zeigt 'cashed').
- FIX (2026-07-09b) Cashed-Out-Claim war im Upload-Formular NICHT wählbar (WinClaimModal TYPES hatte nur played/posted/live) → Nutzer landete zwangsweise im "nur GEWONNEN"-Zweig, Ablehnung. Behoben: 4. Button "Ausgezahlt" (Banknote) ergänzt, grid-cols-2. Zusätzlich Backend-Härtung: played/posted-Branch akzeptiert jetzt auch slip status "cashed" (ohne System-Match-Zwang, WIN_CASHED_CREDITS=20), egal welcher Typ gewählt wurde. E2E: Button rendert, Beschreibung + Upload sichtbar (Admin-Token injiziert).
- FEATURE (2026-07-09c) ECKEN-MÄRKTE (Corners) im Bet-Builder + Single-Picks. Generierung (`_forebet_candidates`): Poisson-Modell auf geschätztem Ecken-Erwartungswert `corner_lam = clamp(6.5+1.4*lam, 7..14)`; Single-Lines Über 7.5/8.5 & Unter 10.5/11.5 Ecken, plus Corner-Bet-Builder "Über 1.5 Tore + Über 8.5 Ecken" (kind `corner_o`). Settlement: NEU deterministisch aus API-Football `/fixtures/statistics` — `find_finished_fixture` liefert jetzt `fixture_id`; `_corner_total_for_fixture()` summiert Ecken via `_live_stat_totals`; `_grade_goal_leg` versteht `corner_o/corner_u` (Über/Unter X.5, None wenn keine Statistik). `settle_pending_tips` routet Ecken-Singles deterministisch (statt LLM judge_market), `settle_hq_combos` holt Ecken-Total wenn ein Leg Ecken enthält. Frontend i18n `localizeMarket`: dynamische Ecken-Lines → EN "Over/Under X.5 Corners", DE "Über/Unter X.5 Ecken" (keys mkt.ovr/und/corners in EN+DE, Fallback EN). Kuratierte Corner-Builder in seed_curated_picks.py (CORNER_COMBOS, id-Präfix hqcur-cc-, 3 Stück: Dynamo Kyiv, Qarabag, Sheriff). VERIFIZIERT: Generierung (unit), Grading (unit: 11 Ecken → Über 8.5=won/Unter 11.5=won/keine Stats=None), echte API-Football Ecken-Abfrage (corners=5), Rendering im Value-Tab (auto Shandong-Karte + kuratierte), EN-Localisierung "Over 8.5 Corners". LIMIT: obskure Ligen ohne Ecken-Statistik → Leg settelt nicht (settle_attempts cap 4).
- FIX (2026-07-09d) SMART-LAB nahm Bild-Einreichungen (Bet-Builder / Kombi-Scheine / Analyse-Sheets) NICHT an und hinterließ leere Posts. Ursachen: (1) submit_smart_idea verlangte ZWINGEND eine reale API-Football-Fixture ≤48h → WC-/fiktive Spiele wurden abgelehnt (no_fixture/too_far), (2) die Idee wurde VOR der Prüfung gespeichert → blanke Waisen-Einträge im "Eingegangene Ideen"-Feed. Behoben: submit_smart_idea postet jetzt IMMER einen Smart-Pick, wenn die KI Team+Markt erkennt — Fixture nur noch optional für die Anstoßzeit; ohne nahe Fixture wird als REPORT (report=True, KEINE Auto-Abrechnung) gepostet, wie die kuratierten WC-Analysen. Bild-only-Einreichungen ohne Ergebnis werden gelöscht (kein blanker Waise). recent_smart_ideas filtert leere Texte raus → nie wieder blanke Karten. settle_pending_tips schließt report-Tips aus (`report:{$ne:True}`). generate_smart_from_idea liest jetzt Datum vom Screenshot, fasst Bet-Builder-Legs zu EINEM Markt zusammen (' · '), akzeptiert leniente. VERIFIZIERT: echtes France-v-Morocco-Bet-Builder-Bild via API → created:true, Markt "El Aynaoui 1+ Foul · Doué 1+ Schuss · Barcola 1+ Schuss · Über 1 Tor" + volle DE-Analyse, report:true. HINWEIS: die 3 blanken Posts des Nutzers liegen auf PRODUKTION (Preview hatte keine) — nach DEPLOY werden sie durch den Feed-Filter ausgeblendet.
- FIX (2026-07-09e) GEWINN-SCHEIN-BILD (`_render_slip_image`) war zu hoch/luftig → Schrift wirkte auf dem Handy winzig, Schein zu breit, Abstände zu groß. Kompaktiert: head_h 258→212, foot_h 440→344, mrow_h 106→76, gap 40→22, sub_h 62→46, Titelzeilen-Abstand +34→+16; Fonts leicht reduziert (logo 110→92, big 124→96, footer-Labels). Footer-Layout enger neu gesetzt (passt jetzt sauber in die Card). WON-Badge-Padding korrigiert (war rechts abgeschnitten). VERIFIZIERT: 6-Leg- und 3-Leg-Schein gerendert & visuell geprüft — dicht, lesbar, Unterzeile (Liga·Datum·Zeit) vollständig, Badge komplett sichtbar.
- FIX (2026-07-09f) (1) BTTS-BET-BUILDER schrieb "beide Teams treffen" als zwei Einzel-Legs "{Team} Über 0.5 Tore" + teils redundantes "Über 1.5 Tore". Owner-Regel: nur "Beide Teams treffen" und mehr nicht. Block (c) in _forebet_candidates umgebaut: EIN sauberes btts-Leg; reines BTTS (total=3) → als SINGLE "Beide Teams treffen" (kein 1er-Kombi); höhere Totals → "Beide Teams treffen + Über X.5 Tore (Ner-Bet-Builder)" (nur NICHT-implizierte Over-Lines ab 2.5). Verifiziert per Generierung. (2) RISK-Single "Dinamo Tirana vs Astana — Astana Handicap -1.5 @5.50" war unsichtbar: durch mein seed_curated-Rerun war match_time=None → fiel aus dem Default-Fenster "Next 24h". Fixture aufgelöst (09/07/2026 19:00 UTC, ECL, NS), Live-Record repariert + seed_curated_picks.py mit META_OVERRIDE gehärtet (kein None mehr). Verifiziert per Screenshot im Risk-Tab. HINWEIS: kuratierte Picks liegen NUR in der DB (nicht im Code) → Produktion braucht die Picks in ihrer eigenen DB; Code-Änderungen (BTTS, seed) greifen erst nach Deploy.
- FIX+FEATURE (2026-07-09g) ABRECHNUNG-ROBUSTHEIT + STERNE-SYSTEM. (a) Spiele die seit ~2h zu Ende waren blieben "offen": Root-Cause = Produktion läuft mit 2 Replicas → beide fahren dieselben Background-Loops → 2× API-Football-Calls (Quota-Exhaustion über 7500/Tag) und 2× settle_attempts → der aggressive Cap 4 (=~1h bei 15-Min-Loop, ~30 Min bei 2 Replicas) wurde erreicht bevor API-Football FT publizierte. Fix1: SETTLE_MAX_ATTEMPTS 4→24 (~6h Retries). Fix2: Mongo-basierte Single-Leader-Lease (`system_locks.bg_leader`, TTL 90s, `_leadership_loop` renewt alle 30s, FAIL-OPEN) — nur EINE Replica fährt settlement/forebet/predictz/smart/live/member_live/push_watch-Loops (`if not _is_leader(): continue`). Halbiert API-Verbrauch, verhindert Doppel-settle_attempts & Doppel-Push. Verifiziert: Lock gehalten von Server-Prozess, Loops laufen. (b) STERNE statt Prozente: ai_rating kommt jetzt aus win_prob (stars=clamp(1,10,round(win_prob*10))) → 8.5-Cap weg, ≥96%→10★, 90%→9★. (c) Owner-Regel: JEDER Single-Pick mit win_prob≥0.90 → Banker (vor Value-Check in _forebet_candidates-Kategorisierung). (d) Prozente entfernt: ≈X%-Badge aus RateWall raus + bestehende ai_analysis-Prosa bereinigt (7 Picks, "ca. NN% Trefferchance"→"N/10 Sterne"), neue Analysen ohne %. (e) NEU AiRatingStars.jsx: ai_rating als 1-10 Sterne; 10★ = explodierende Partikel-Animation (ExplosionBurst, framer-motion), 9★ = flammende Aura (FlameAura, orange). Ersetzt die AI-Zahl im Card-Footer. Bestehende Picks re-kategorisiert (≥90%→banker) + re-rated aus win_prob (31 Picks). VERIFIZIERT per Screenshot: 10★ (volt) + 9★ (orange+Flammen), kein %-Badge mehr.
- REFINE (2026-07-09h) Banker-Regel an Sterne gekoppelt + Produktions-Daten-Migration. (1) Kategorisierung nutzt jetzt `round(winprob*10) >= 9` (statt win_prob≥0.90) → JEDER 9- oder 10-Sterne-Single → Banker. (2) `-1.5`/`-1,5` Handicap-Singles → immer Risk. (3) NEU `_migrate_stars_and_categories()` läuft in `_startup_seed` (idempotent, auch auf Produktion): re-ratet ai_rating aus win_prob (≤10), verschiebt 9/10★-Singles → Banker, -1.5-Handicaps → Risk, und strippt "ca. NN% Trefferchance"/"(Value ≥1,60)" aus bestehenden Analyse-Texten. WICHTIG: Grund für "nach Deploy nix geändert" war, dass bestehende Produktions-Picks alte Daten (Kategorie/Rating/%-Text) hatten — nur der Frontend-Code (Sterne, kein %-Badge) war live. Migration zieht die Bestandsdaten beim Start nach. VERIFIZIERT: 0 Picks mit %-Text, Sternverteilung 2–10, 0 von 9/10★ in Value, alle 3 -1.5-Handicaps (Astana/Sheriff/Qarabag) in Risk.
- REFINE (2026-07-09j) Owner-Regel: wenn "Beide Teams treffen" Teil eines Bet-Builders ist, muss "Über 1.5 Tore" RAUS (redundant, BTTS garantiert bereits ≥2 Tore). Migration `_migrate_stars_and_categories` erweitert: beim Zusammenführen der team_o05-Legs zu einem btts-Leg wird jede o15/"Über 1.5 Tore"-Leg entfernt, Gesamtquote + market + combo_legs + Display neu berechnet. Über 2.5+ bleibt erhalten (nicht impliziert). VERIFIZIERT: BTTS+Über1.5 → "Beide Teams treffen" @1.69 (1 Leg btts); BTTS+Über2.5 → "Beide Teams treffen + Über 2.5 Tore" @3.38 (btts+o25). Neu-Generierung war bereits korrekt (fügt nie Über 1.5 zu BTTS hinzu).
- FEATURE (2026-07-09k) GEHEIMER BESUCHERZÄHLER (nur Admin). Backend: `POST /api/track/visit` (anonym, cookiefrei — visitor_id = zufällige localStorage-ID; deduped pro Besucher/Tag via upsert in `visits`-Collection → hits + unique). `GET /api/admin/visits` (require_admin, 401 für alle anderen): total/today/week unique+hits, 14-Tage-Verlauf, members, subscribers. Frontend: App.js pingt beim Laden einmal pro Session (sessionStorage-Guard). NEU SecretInsights.jsx unter Route `/insights` — KEIN Link irgendwo in der UI, zeigt für Nicht-Admins "Nichts zu sehen hier", für Admin ein Dashboard (Heute/7T/Gesamt-Besucher, Registrierungen, Push-Abos, 14-Tage-Balkenchart). VERIFIZIERT: Tracking zählt unique+hits, /admin/visits 401 ohne Admin, /insights rendert für Admin (Screenshot). Kein Visitor-Tracking existierte vorher.
- FEATURE (2026-07-09l) PUSH-OPT-IN-PROMPT (Conversion). Dezentes Banner (NotificationPrompt.jsx) gleitet 2,5s nach dem ersten Öffnen einer Picks-Ansicht hoch (Trigger: `tj-viewed-pick` Event aus openTipsView). Einmalig, dismissbar ("Später"/X → localStorage tj_push_prompt_dismissed). Gated: nur wenn Web-Push unterstützt, Notification.permission != 'denied', tj_bell != '1' (nicht schon an), nicht iOS-ohne-PWA. "Aktivieren" → pushClient.js `enablePushFull()` (permission + /notifications/subscribe + /push/subscribe VAPID) → dispatcht `tj-push-enabled`, NotificationBell hört darauf und setzt on=true. i18n EN+DE (push.prompt.*). Wired in App.js Home. VERIFIZIERT: kompiliert fehlerfrei, Gating korrekt (Headless-Browser=permission denied → korrekt nicht angezeigt); echte Sichtprüfung auf Gerät mit permission=default steht aus (Headless erzwingt denied).
- FEATURE (2026-07-09m) NOTIFICATION-SOUNDS + gezielte High-Impact-Pushes + Abo-Boost.
  (1) COIN-SOUND: neue Assets in public/ (coin.wav, coin_explosion.wav=Münze+kleine Explosion, coin_fire.wav=Münze+Feuerknistern; per numpy synthetisiert). Neues Modul src/coinSound.js `playCoin(kind)`. NotificationPrompt.jsx spielt Coin-Ding beim Hochgleiten des Opt-in-Prompts. Bei eingehendem Push (Vordergrund) postet der Service-Worker `{type:'tj-push-coin', sound}` an alle Clients; index.js hört darauf und spielt den passenden Sound. Autoplay-Blockade wird still geschluckt (NotAllowedError catch).
  (2) SOUND-MAPPING nach Sternen (round(win_prob*10)): 10★→'explosion' (Münze+Explosion), 9★→'fire' (Münze+Feuer), sonst→'coin'. Live-Picks bekommen 'explosion' ab 9★.
  (3) GEZIELTE PUSH-TITEL in `_push_payload_for_tip`: hq-auto Banker 10★ → "💥 10-Sterne-Banker!", Banker 9★ → "🔥 9-Sterne-Banker!". Payload trägt jetzt `sound`-Feld. Live bleibt "🔵 LIVE-Pick".
  (4) ABO-BOOST auf ALLE öffentlichen Endpoints ausgeweitet: `_sub_boost()` (+140 bis 2026-09-09, danach 0) jetzt auch in /api/stats (subscribers), /api/notifications/stats (subscriber_count) und /notifications/unsubscribe — vorher nur /notifications/subscribe. Insights-Dashboard bleibt roh (echte Zahl). VERIFIZIERT via curl: /api/stats subscribers=141 (real 1 +140), /notifications/stats=141.
  VERIFIZIERT: Backend-Syntax OK + läuft; Payload-Logik-Test (0.97 banker→10★/explosion/💥-Titel, 0.90→9★/fire/🔥, 0.75→coin); Frontend kompiliert; alle 3 Audio-Assets liefern HTTP 200; Homepage lädt. HINWEIS: tatsächliche Audio-Wiedergabe ist autoplay-policy-/interaktionsabhängig → finale Ohrenprobe am echten Gerät durch Nutzer. Produktion braucht Re-Deploy.
- FEATURE/FIX (2026-07-09n) LIVE-FRÜH-ABRECHNUNG + Mitglieder-Boost + Produktions-Diagnose.
  (1) LIVE EARLY-SETTLE: in `live_autopost()` (Abschnitt 1) werden Over-/BTTS-Live-Picks jetzt SOFORT mitten im Spiel als "won" nach Abgerechnet verschoben, sobald `_live_bet_landed(...) is True` (unumkehrbar, da Tore nur steigen) — kein Warten mehr auf FT. Fügt vor dem "in-play weiterlaufen"-Zweig eine Prüfung ein (settled_by="auto-live-early", schreibt final_home/away + live_score/minute). VERIFIZIERT: admin/live-run schloss 4 laufende Picks korrekt (Vllaznia 2:1 Über2.5 @65', CSKA 3:1 @64', Glentoran 1:1 Über1.5 @45', Petrovac 1:1 @37').
  (2) MITGLIEDER-BOOST: neue Konstante MEMBER_DISPLAY_BOOST=400 (+`_member_boost()`, läuft bis 2026-09-09 aus) auf /api/stats `members` addiert (Homepage-Fortschrittsbalken InviteSection). VERIFIZIERT: /api/stats members Preview 76→476 (Prod real ~22→422). Insights-Dashboard bleibt roh.
  (3) DIAGNOSE-ENDPOINT: neuer GET /api/admin/live-health (require_admin) meldet in EINEM Call: api_football_key_set, is_leader, hq_account_exists, current_live_tips, pending_prematch_tips, API-Football /status (http/errors/requests/plan) und live=all results. Zweck: Produktions-Ursache für "keine Lives" bestimmen ohne Log-Zugriff. JETZT AUCH als mobiles Panel oben in SecretInsights.jsx (/insights) mit Klartext-Verdikt (grün/rot) — Nutzer ist am Handy, kann keine Konsole nutzen. VERIFIZIERT: Panel rendert auf Preview /insights, Verdikt "✅ Alles ok", zeigt Key gesetzt/Pro/1412 Requests, 14 live, Leader=true, 6 Live-Picks, 31 Vor-Spiel-Picks.
  LEADER-LOCK ANALYSE: Preview zeigte kurz is_leader=false — Ursache war ein abgelaufener Lock eines toten Reload-Workers; heilt sich in ≤30s selbst (nach 35s is_leader=true). Kein Produktions-Blocker. Leader-Logik funktioniert.
  OFFEN (Produktion, nur mit Env-Zugriff lösbar): "keine Live-Picks den ganzen Tag" auf tipjarglobal.com. Hauptverdacht: API_FOOTBALL_KEY fehlt/ungültig in der Deployment-Umgebung (Live braucht API-Football; Vor-Spiel-Picks per Scraper laufen ohne). Nächster Schritt: nach Re-Deploy /api/admin/live-health auf Produktion auswerten.

## Offene Punkte / Hinweise
- Produktion (tipjarglobal.com) läuft mit ALTEM Code bis Nutzer erneut deployt → verschwundener 7-Leg-Community-Schein war auf Produktion (eigene DB, kein Zugriff, nicht wiederherstellbar). Nutzer muss DEPLOY klicken, damit Live-Settlement + Bewertungswand-Fix + Cashed-Out live gehen.
- Live-Bereich zeigt viele obskure US-Amateurligen — evtl. striktere Liga-Whitelist für Live-Loop gewünscht (offen).


## Changelog — 2026-07-09 (Realistische Tor-Quoten via Poisson)
- Owner spielte Single-Picks real bei BetScore nach → Schätzquoten waren „extrem falsch". Fix: neue `_pois_line_odds(lam, line, over, margin=0.95)` berechnet Über/Unter X.5-Quoten match-spezifisch aus erwarteten Toren (lam = avg bzw. Prognose-Total, Poisson). Feste Fantasiewerte (o15/o05/u25/u35 + clean-sheet o25) ersetzt.
- Gegen echte Samples kalibriert: Über 2.5 Caernarfon–Levadia real 1.58 → berechnet 1.59; Über 0.5 ~1.01–1.10 (real 1.03); Unter 3.5 ~1.17 (real 1.17); Unter 2.5 ~1.40–1.67 (real 1.60-1.70). Markt-Labels bleiben Dot-Format ("Über 2.5 Tore") für Odds-Lookup/Settlement-Konsistenz.
- OFFEN (2. Batch erwartet): Handicap-Quoten (Qarabag -1.5=1.19, Sheriff -1.5=1.95) + Team-Totals ebenfalls match-spezifisch machen; Marge feinjustieren.


## Changelog — 2026-07-09 (Friendlies-Label, Liga auf Single-Tipps, Bet-Builder-Vielfalt)
- Bet-Builder Redundanz-Fix: „Über 1.5 Tore" wird nie mehr zu „beide treffen" gepackt (implizit). Tor-Linien ab Über 2.5 mit 1-Tor-Puffer. Klassisches beide treffen bleibt 2 Legs (Combo-Gate 1.80→1.60). Clean Sheet (3:0/0:3) → Über 2.5 statt BTTS.
- Freundschaftsspiele NICHT geblockt (Blacklist-Ergänzung mkk dnepr/friendl wieder entfernt), sondern als „Freundschaftsspiel" gelabelt (forebet + predictz Tip-Erstellung).
- Single-Tipps zeigen jetzt echte Liga statt „TipJarHQ Pick" (forebet: league_disp aus r.league/lcode/cc; predictz bereits real). Frontend zeigt tip.league (RateWall Zeile ~568).
- NEUE settlebare Bet-Builder (deterministisch via neuem `_grade_goal_leg`): Beide treffen + Doppelte Chance (1X/X2), Über 2.5 + DC 12, Über 0.5 je Halbzeit. `find_finished_fixture` liefert jetzt HT-Tore (score.halftime). `_grade_goal_leg` behandelt o{k}5/team_o05/btts/res_*/dc_*/ht_o05/sh_o05/o05_each/ht_u25/ht1_win, gibt None bei unbekanntem Kind (nie Fake-Ergebnis). In settle_hq_combos verdrahtet. Regression + neue Kinds getestet.
- OFFEN: Ecken-Märkte (brauchen Statistics-API-Abruf) bewusst zurückgestellt.


## Changelog — 2026-07-09 (Cash-out-Claim, Homepage-Texte, Profil-E-Mail)
- Homepage: unter „Was ist TipJar?" neue Blöcke — SYSTEM-MODUS-Label, H3 „Warum Anwender TipJar wählen — statt Telegram, Discord & Co.", Nutzen-Text, „Dein Vorteil"-Box (volt), „Was wir NICHT sind"-Abgrenzung, CTA-Text (kein Button). i18n EN+DE (Rest via EN-Fallback). Kein Zähler, kein FAQ (bewusst).
- „Zeig deinen Gewinn"/Hall-of-Fame-Claim akzeptiert jetzt CASH-OUT-Scheine: neuer Claim-Typ "cashed" (Button „Ausgezahlt", Banknote-Icon, grid-cols-2). Backend: extract_win_slip erkennt "Cashed Out/Ausgezahlt" → status "cashed"; claim_win-Branch für "cashed" OHNE System-Match-Zwang (eigene Trophäe), 2+ Legs, WIN_CASHED_CREDITS=20; _render_slip_image Label „Ausgezahlt" + „Ausgezahlt:"-Betrag. i18n win.type.cashed(.desc) EN+DE.
- Profil: E-Mail jetzt änderbar (vorher nur Username). ProfileUpdate.email + Endpoint mit Unique-/Format-Check; ProfileModal neues Feld profile-email. E2E getestet (Username+E-Mail ändern, Login mit neuer E-Mail ok). → Nutzer ändert sein Konto selbst auf Produktion (duexxatuxx→TipJarLogic, danoglidis...→kontakt@tipjarglobal.com).

## Changelog — 2026-07-09 (Voll-Automatik Abrechnung + korrigierbare Scheine)
- Abgerechnete Scheine sind jetzt KORRIGIERBAR: TipCard zeigt für Admin/Ersteller (canDelete) auf JEDEM Status die Zeile "Ergebnis setzen / korrigieren" mit 4 Buttons (OFFEN/GEWONNEN/VERLOREN/CASHED OUT), aktueller Status hervorgehoben. `settle()` lädt im Abgerechnet-Tab die Listen neu (loadSettled als useCallback). Behebt "Olympiakos versehentlich auf Verloren, kein Undo möglich".
- OFFEN-Reopen setzt hq-live → "live" (Auto-Loop übernimmt wieder), sonst "pending".
- Voll-Automatik Gewonnen/Verloren: bereits vorhanden (settle_pending_tips / settle_hq_combos / settle_multimatch_parlays / live_autopost graden jede Wette + jedes Leg aus API-Football-Endstand). Keine manuelle Aktion nötig; Buttons sind nur Override.
- Cashed-Out-Grenze (ehrlich dokumentiert): Cash-out ist eine Buchmacher-Aktion, für die es KEINE Datenquelle gibt → kann NICHT auto-erkannt werden. Nutzer setzt "Ausgezahlt" per 1 Klick (D1: ganzer Schein=Ausgezahlt, gewonnene Legs=Gewonnen).
- NEU: settle_multimatch_parlays gradet jetzt AUCH cashed_out-Scheine leg-für-leg weiter (Status-Filter um "cashed_out" erweitert, Attempt-Cap 24), überschreibt aber NIE den Schein-Status "cashed_out" (is_cashed-Guard). So füllen sich die Legs automatisch mit echtem Gewonnen/Verloren, während der Schein "Ausgezahlt" bleibt. Frontend zeigt Legs wieder per echtem Status (kein Force-Grün mehr). E2E verifiziert (cashed bleibt cashed, normales Parlay flippt zu won).


- FIX (2026-07-10) ABRECHNUNG hängt bei Akzent-Ligen + UI z-index.
  ROOT CAUSE (Produktion: Spiele bleiben stundenlang „OFFEN"): `_teams_match`/`_norm` entfernten keine diakritischen Zeichen → "Rīgas FS"≠"Rigas FS", "MSK Žilina"≠"MSK Zilina" → find_finished_fixture/resolve_team_id scheiterten für viele Sommer-Quali-Ligen (baltisch, slawisch, Conference/Europa League) → settle_attempts liefen bis zum alten Cap 24 → Tipps dauerhaft ausgeschlossen (settle-now checked:0).
  FIXES: (1) `_norm` nutzt jetzt unicodedata NFKD + strippt combining marks (Rīgas→rigas, Žilina→zilina, ö→o). Repariert die komplette Fixture-/Team-Auflösung. (2) Neuer robuster Fallback `_datescan_fixture(home,away,dates,cache)`: scannt `/fixtures?date=` und matcht BEIDE Teamnamen (beide Richtungen), unabhängig von team-id/season; per-Datum-Cache. Eingebaut in settle_pending_tips UND settle_hq_combos (nach find_finished_fixture). (3) SETTLE_MAX_ATTEMPTS 24→240 (spät veröffentlichte FT-Status + Fallback-Retries bis 36h-Purge; Alt-Tipps mit ~34 Versuchen sind dadurch wieder < Cap → werden erneut geprüft). VERIFIZIERT im Backend: _teams_match('Rīgas FS','Rigas FS')=True, _datescan Glentoran→1:2, Hajduk→2:0. Braucht Re-Deploy; danach räumt der Loop den Rückstau automatisch ab.
  UI-FIX: Sprach- & Profil-Dropdown im Header (Header.jsx) lagen HINTER den grünen CTA-Buttons (absolute ohne z-index vs. relative Badge-Buttons später im DOM) → beiden Dropdowns `z-[60]` gegeben. Auf Preview verifiziert (Dropdown vollständig oben). Braucht Re-Deploy.

## Changelog — 2026-07-15 (Transliteration nicht-lateinischer Schriften → Anzeige)
- FEATURE (P0): Tipps mit nicht-lateinischen Team-/Liga-/Markt-Namen (Griechisch, Kyrillisch, Arabisch, Hebräisch, CJK, Hangul) werden für ALLE Nutzer in lateinische Buchstaben umgewandelt — nur auf Anzeige-Ebene, Rohdaten in der DB bleiben unverändert.
- Lib `transliteration@2.6.1` (yarn add). Neue Helper `toLatin(text)` in i18n.js: transliteriert NUR wenn `NON_LATIN_RE` (Greek/Cyrillic/Arabic/Hebrew/CJK/Kana/Hangul-Ranges) matcht → deutsche Umlaute (München), ß und türkische Zeichen (Süper Lig) bleiben UNANGETASTET.
- `formatSelection` wrappt jetzt sein Ergebnis mit toLatin (interne Logik nach `_formatSelection` umbenannt).
- RateWall.jsx: `tip.home_team`, `tip.away_team`, `tip.league`, `tip.country`, `leg.match`, `leg.league` mit `toLatin(...)` umschlossen.
- Bewusste Grenze: reine Zeichen-Transliteration (Ολυμπιακός→Olympiakos ✓, Спартак Москва→Spartak Moskva ✓). Phonetische Rekonstruktion (Μπλουμενάου→Blumenau) NICHT gemacht, da griech. μπ mehrdeutig ist (würde Olympiakos→Olybiakos kaputtmachen). "Μπλουμενάου"→"Mploymenaoy" (lesbar, nicht perfekt). VERIFIZIERT: node-Unit-Test + Frontend kompiliert fehlerfrei + Homepage-Screenshot ok. Braucht Re-Deploy für Produktion.

## Changelog — 2026-07-15 (Griechische/nicht-lat. Teamnamen: Auflösung + kanonische Anzeige)
- PROBLEM: Mitglied postete "Μπλούμεναου Over 4.5" (Blumenau SC vs Metropolitano, real 4:1). Griech. Teamnamen konnten von der Abrechnung NICHT aufgelöst werden (_norm transliteriert kein Griechisch) -> Tipp blieb OFFEN; deutsche Leser konnten ihn nicht lesen.
- BACKEND (server.py): Neue Umschrift-Helfer _translit_greek(hard) mit modern-griech. Digraphen (μπ->b/mp, ντ->d/nt, ου->u/ou, γκ->g, τσ->ts ...). _latin_variants() liefert Kandidaten (Griechisch: soft+hard; Kyrillisch/andere: unidecode). "Μπλούμεναου"->hard "blumenau" (loest auf), "Ολυμπιακός"->soft "olympiakos" (loest auf).
- _teams_match() prueft jetzt alle Latin-Varianten beider Namen (refaktoriert: _match_norm Kernlogik). resolve_team_id() probiert jede Variante bei /teams?search bis eine Team-ID findet.
- settle_pending_tips() speichert kanonische API-Football-Namen als home_team_latin/away_team_latin (Orientierung via _teams_match). GET /api/tips gibt Rohdicts zurueck -> Felder fliessen automatisch durch.
- FRONTEND (i18n.js/RateWall.jsx): neuer displayTeam(raw, latin) -> el/ar sehen Original, alle anderen bevorzugen latin (z.B. "Blumenau"), sonst toLatin-Fallback. Single-Pick home/away nutzt displayTeam.
- VERIFIZIERT E2E gegen echte API-Football: resolve Μπλούμεναου->19635, Ολυμπιακός->553; fixture Blumenau 4:1 Metropolitano FT; synth. Tipp -> status=won, home_team_latin=Blumenau. Frontend kompiliert fehlerfrei. Deps: unidecode==1.4.0. BRAUCHT RE-DEPLOY; Auto-Loop raeumt stecken gebliebene griech. Tipps danach automatisch ab (sofern settle_attempts < Cap).

## Changelog — 2026-07-15 (Push-Praeferenzen serverseitig, Mitglieder-Suche, lila Mitglieder-Karten)
- PUSH-PRAEFERENZEN: Die Bereichs-Kaestchen der Glocke (KI/Systeme/Smart/Mitglieder/Live) steuerten bisher NUR In-App-Popups; der echte Server-Web-Push ging an alle. Jetzt: /push/subscribe speichert areas, neuer POST /push/preferences {endpoint,areas} aktualisiert sie; notify_all_push filtert pro Geraet nach payload.area (Subs ohne Prefs bekommen weiter alles). _push_payload_for_tip + digest tragen jetzt "area"; push_watch_loop gruppiert frische Tipps nach area (ein Push je Bereich -> filterbar). Frontend NotificationBell: enableWebPush(areas) sendet Prefs beim Aktivieren; areas-useEffect postet /push/preferences per Subscription-Endpoint bei jeder Aenderung. VERIFIZIERT: sub mit ai:false -> AI-Push uebersprungen, members-Push zugestellt.
- MITGLIEDER-SUCHE: GET /api/users/search?q= (Regex auf username, case-insensitive, + Latin-Transliterations-Fallback via _latin_variants fuer griech./kyrill. Namen). Frontend: neue MemberSearch-Komponente (debounced 300ms) in der Community-Ansicht (view===members), Ergebnisse klickbar -> onUserClick -> PublicProfileModal. i18n wall.searchMembers/searching/noMembers/tipsLabel (EN+DE). VERIFIZIERT: Suche "smok" -> smokey1.
- LILA MITGLIEDER-KARTEN: TipCard bekommt isMemberPick (source nicht in hq-auto/hq-system/hq-live/smart) -> Hintergrund bg-[#1b1030] + lila Border; HQ/KI bleibt bg-surface (dunkel/grunlicher volt-Akzent).

## Changelog — 2026-07-16 (Admin-Besuche aus Analytics ausschliessen)
- WUNSCH (Owner): Eigene stuendliche Seitenaufrufe blaehen die Besucherzahlen auf (24 "Besucher" = nur er). 
- FIX: /track/visit liest jetzt optional den User (Token wird vom Frontend-Interceptor automatisch mitgeschickt). Ist der Besucher Admin -> Visit-Doc wird is_admin=True markiert UND per update_many werden ALLE frueheren Visits derselben visitor_id (stabile localStorage-ID des Geraets) rueckwirkend geflaggt. /admin/visits filtert ueberall is_admin != True (daily unique/hits, total_unique distinct, total_hits). VERIFIZIERT: Admin-Ping -> is_admin True, anon -> False. Braucht Re-Deploy; historische Admin-Besuche verschwinden aus den Zahlen, sobald der Owner die Live-Seite eingeloggt einmal oeffnet.

## Changelog — 2026-07-16 (KI raus aus Community + System Picks nach Zeit gruppiert)
- COMMUNITY = nur echte Mitglieder: list_tips(source=members) und tips_counts.members schliessen jetzt hq-auto, smart, hq-live, hq-system UND usernames TipJarHQ/"TipJarHQ System" aus. KI/HQ postet nicht mehr in Community.
- SYSTEM PICKS nach ZEIT statt Risiko gruppiert: build_systems() setzt pro Schein time_bucket (now/today/week) via fruehester Anstosszeit der Selektionen; hour-System immer now; ohne parsbare Zeit -> week (jeder Schein landet in GENAU einem Bucket). Systems.jsx rendert 3 Abschnitte: Faengt jetzt an / Heute / Diese Woche (nur nicht-leere), Icons Timer/CalendarDays/CalendarRange. i18n sys.bucket.now/today/week (EN+DE). Single Picks behalten Banker/Value/Risk unveraendert.
- VERIFIZIERT: /systems liefert time_buckets (lock=week, uebrige=today); Community-API leer in Preview (nur KI-Picks vorhanden); Screenshot zeigt HEUTE-Abschnitt. Braucht Re-Deploy.

## Changelog — 2026-07-16 (Markt-Begriffe alle Sprachen + Live-Tipps raus aus Community)
- MARKT-BEGRIFFE mehrsprachig: normalizeBetTerms(s,t) in i18n.js wandelt transliterierte Fremdbegriffe in die Lesersprache: Korner->mkt.corners, Gkol/Gol->mkt.goals, "1o Imihrono"->"1. "+mkt.half, Over->mkt.ovr, Under->mkt.und; entfernt redundantes Trailing "- Over/Under". Neue Keys mkt.goals/mkt.half (EN+DE, Rest EN-Fallback). formatSelection wrappt jetzt normalizeBetTerms(toLatin(_formatSelection(sel,t)),t). Griech. Nutzer (lang=el) sehen Original. VERIFIZIERT via node-Regex-Test.
- LIVE-MITGLIEDER-TIPPS -> LIVE-BEREICH: live_annotate_sync flippt jetzt echte Mitglieder-Tipps (nicht KI/HQ), deren Spiel gerade laeuft, auf status=live (auch 1-Spiel-Parlays; Teams aus Feldern ODER aus einzelner Leg "A – B" via _tip_match_teams). Helper _is_member_tip. Community laedt nur status=pending -> Live-Picks verschwinden dort und erscheinen im Live-Tab. Settlement bleibt intakt (settle_pending_tips inkl. live/non-hq; parlays via settle_multimatch_parlays). VERIFIZIERT: synth. Mitglieder-Einzel + 1-Spiel-Parlay mit gemocktem Live-Fixture -> beide status=live, live_state gesetzt (to_live:2). Braucht Re-Deploy.

## Changelog — 2026-07-16 (Alarm-Bereiche: Single-Picks Rename + Live Doppelbox KI/Community)
- RENAME: Alarm-Option "KI-Picks" -> "Single-Picks" (DE) / "Single Picks" (EN); entspricht dem ersten Bereich (AI Single-Game). bell.new.ai analog angepasst.
- LIVE DOPPELBOX: Live ist der einzige Bereich wo KI + Community gleichzeitig posten. Neuer Area-Key live_ai (orange "KI TIPPS") NEBEN der roten live-Box (Community-Live) in der Alarm-Einstellungen-Zeile. Getrennt abhakbar.
- Backend _tip_push_area: live -> live_ai wenn AI-Quelle (hq-live/hq-auto/hq-system/smart) sonst live. _push_payload_for_tip nutzt _tip_push_area (url bleibt area=live fuer Navigation). notify_all_push filtert live_ai/live getrennt.
- Frontend NotificationBell: tipArea splittet live_ai/live; DEFAULT_AREAS+VIEW_KEY um live_ai erweitert (view=live); fireAlert isLive/navArea (live_ai -> Live-View); poll gated pro Sub-Area. i18n bell.area.live_ai (EN AI Picks / DE KI Tipps).
- VERIFIZIERT: _tip_push_area (hq-live->live_ai, member-live->live); Screenshot zeigt Single-Picks + orange KI-TIPPS-Box neben roter Live-Box. Braucht Re-Deploy.

## Changelog — 2026-07-16 (Suche findet auch Spiele/Teams)
- Problem: Suchleiste fand nur Mitglieder (Nutzernamen). Nutzer suchte Team "Makara" -> nichts.
- /users/search gibt jetzt zusaetzlich games zurueck: aktive Tipps (pending/live) gematcht auf home_team/away_team/league + Leg-Match, mit Transliteration (_latin_variants). Teams via _tip_match_teams (auch 1-Spiel-Parlays).
- MemberSearch (RateWall): zeigt Abschnitt SPIELE (klickbar -> tj-open-pick area+id -> jumpToPick) + Abschnitt MITGLIEDER. Live-Spiele mit pulsierendem Punkt. i18n wall.gamesLabel/membersLabel, Placeholder "Mitglieder oder Spiele suchen". VERIFIZIERT: Backend q=makara/masoyk findet Spiel; Screenshot zeigt SPIELE-Treffer. Braucht Re-Deploy.

## Changelog — 2026-07-16 (Mitglieder-Scheine anreichern: Namen/Liga/Anstoss)
- Problem: AI-transliterierte Mitglieder-Scheine haben falsch geschriebene Teamnamen (z.B. "Makara – Masoyk Royna"), fehlende Liga und fehlendes Datum/Uhrzeit.
- FIX: neue enrich_member_picks() (laeuft in member_live_loop). Sucht Mitglieder-Picks (pending/live, single+1-Spiel-Parlay) denen home_team_latin/league/match_time fehlt; resolve_team_id + find_upcoming_fixture (sonst _find_live_fixture fuer laufende Spiele). Fuellt home_team_latin/away_team_latin (kanonisch, orientiert nach Fixture-Reihenfolge), league und match_time (dd/mm/YYYY HH:MM). Fuer 1-Spiel-Parlays: legs[0].match -> kanonisch, legs[0].league + legs[0].kickoff gefuellt. enrich_tries-Cap (6). 
- Frontend zeigt bereits league (Karte), match_time (Single), leg.league/leg.kickoff (Parlay) + displayTeam(home_team_latin) -> kein FE-Change.
- VERIFIZIERT: mock upcoming fixture -> leg.match "Blumenau SC – Metropolitano", league+kickoff gesetzt, korrekte Orientierung. resolve "Makara"->6282 real. Limitierung: nur wenn Fixture (upcoming/live) via API aufloesbar. Braucht Re-Deploy.

## Changelog — 2026-07-16 (Freundliche Rueckfrage statt Ablehnung bei schwer erkennbaren Scheinen)
- Problem: Scheine ohne erkennbaren Anstoss wurden hart abgelehnt ("needs a match date & time") -> Spieler geben auf.
- create_tip: harte Ablehnung bei fehlendem match_time entfernt (Single) -> match_time="" akzeptiert. Nach Insert _slip_needs_clarification(tip) prueft teams (via resolve_team_id+find_upcoming/live), league, datetime -> setzt needs_clarification + clarification_fields, gibt sie in der Response zurueck.
- Neuer Endpoint POST /tips/{id}/clarify (ClarifyInput: league/match_time/home_team/away_team, owner/admin-only): fuellt Felder, aktualisiert 1-Spiel-Parlay-Leg (match/league/kickoff), setzt needs_clarification=False + enrich_tries=0 (Auto-Enrichment retry).
- Frontend SubmitTipModal: nach Publish wenn data.needs_clarification -> ClarifyPanel (statt schliessen) fragt freundlich nur die fehlenden Felder ab (Teams/Liga/Datum-Uhrzeit) mit Speichern/Spaeter. i18n clarify.* (EN+DE). Tipp ist bereits gepostet (onPublished refresh), Klaerung optional.
- VERIFIZIERT E2E via curl: POST /tips (Makara/Masoyk, kein Datum) -> needs_clarification True, fields [teams,league,datetime]; /clarify -> Felder gefuellt, Flag zurueckgesetzt. Frontend kompiliert. Braucht Re-Deploy.

## Changelog — 2026-07-16 (Stuck Makara-Schein loeschen)
- Owner-Request: james76 Live-Schein "Makara – Masoyk Royna" (nicht aufloesbar) loeschen. Prod-DB kein Zugriff -> Startup-Cleanup _delete_stuck_makara_pick() in _startup_seed. Matcht eng: username ^james + (home/away/legs.match regex makar|masoyk|royna). Loescht tips + tip_ratings. VERIFIZIERT: loescht nur die 2 Makara-Scheine, andere james76-Scheine + Fremd-Nutzer bleiben. Laeuft beim naechsten Deploy automatisch. Idempotent.

## Changelog — 2026-07-16 (Auto-Loeschung unklarer Scheine nach 12h)
- Owner-Request: Scheine, deren Teams die KI nicht versteht und die nicht geklaert werden, nach 12h automatisch loeschen.
- _purge_unclarified_slips() (laeuft in member_live_loop): loescht Mitglieder-Tipps mit needs_clarification=True UND "teams" in clarification_fields UND created_at > 12h (+ tip_ratings). Nur-Liga/Datum-fehlt oder HQ/KI-Quellen werden NICHT geloescht.
- enrich_member_picks setzt bei erfolgreicher Aufloesung needs_clarification=False + clarification_fields=[] -> ein Schein, dessen Teams doch noch erkannt werden, wird NICHT geloescht.
- VERIFIZIERT: alt+teams-unbekannt geloescht; frisch/nur-liga/HQ bleiben. Braucht Re-Deploy.

## Changelog — 2026-07-16 (Zeit-Auswahl beim Hochladen: Live/Heute/Spaeter)
- TipSaveInput.timing (live|today|later). create_tip: timing==live -> is_live_post -> status=live (Live-Bereich). member_timing gespeichert. Wenn timing gesetzt -> datetime aus clarification_fields entfernt (kein Anstoss-Nachfragen noetig).
- Frontend SubmitTipModal: 3-Button-Selektor (Live rot / Heute volt / Spaeter grau, toggle) unter Self-Rating; timing in /tips-Payload. i18n submit.timing(.live/today/later) EN+DE. reset() setzt timing=null.
- VERIFIZIERT: timing=live -> status live + keine datetime-Rueckfrage; timing=today -> pending + member_timing + datetime entfaellt. Frontend kompiliert. Braucht Re-Deploy.

## Changelog — 2026-07-16 (Bugfix: Abrechnung / Sync bei API-Football Quota)
- ROOT CAUSE: Sync rechnet fertige Spiele nicht ab, weil das API-Football Tageslimit erreicht war ("You have reached the request limit for the day"). _apifootball gab bei erschoepfter Quota eine leere Liste zurueck (HTTP 200 + errors-Payload) — nicht unterscheidbar von "Spiel nicht gefunden". Dadurch wurden settle_attempts faelschlich hochgezaehlt und dem Admin kein Grund angezeigt.
- FIX server.py: _apifootball erkennt jetzt errors.requests/rateLimit -> globales _API_QUOTA-Flag (_api_quota_exhausted / _reset_api_quota_flag). settle_pending_tips / settle_hq_combos / settle_multimatch_parlays brechen bei erschoepfter Quota ab OHNE settle_attempts zu verbrennen. settle_now setzt ok=False + deutsche reason -> Sync-Button zeigt Toast "API-Football Tageslimit erreicht ...".
- VERIFIZIERT (Quota war live erschoepft): settle_now -> ok=False, checked=0, settled=0, quota_exhausted=True, 0 Tips mit veraenderten settle_attempts. Kein Abrechnungs-Gap: alle 66 pending Parlays korrekt zugeordnet (40 combo_legs->settle_hq_combos hq-auto/smart, 26 legs->settle_multimatch). Braucht Re-Deploy.
- OFFEN/EMPFEHLUNG: Quota resettet taeglich -> Abrechnung laeuft dann automatisch weiter. Bei taeglicher Erschoepfung: API-Football Plan upgraden ODER Quota-Verbrauch reduzieren (viele obskure Quali-Tips + 15-Min-Loop + Scraper).

## Changelog — 2026-07-16 (KI-Risk-Bet BTTS in jeder HZ + Schärfung 1.HZ-Bet)
- NEU (_forebet_candidates): Risk-Bet-Builder "Beide Teams treffen 1. Halbzeit + 2. Halbzeit" (sfx -btts2h, hot=True -> RISK-Filter). Nur bei torreichen Ligen: ph>=1, pa>=1 UND xg/avg >= 3.5. Legs: btts_ht (base 2.60) + btts_sh (base 2.50). Landet via prod 6.5 im RISK (3.0-15.0).
- SCHAERFUNG HOT-Builder (Über 1.5 Tore 1.HZ + BTTS + Über 2.5): zusaetzliches Gate xg/avg >= 3.4, damit schwache/torarme Teams (Dila Gori 0:0) den aggressiven 1.-Halbzeit-Bet NICHT mehr ankern (vorher nur total>=4 aus lopsided 3:1).
- BUGFIX _grade_goal_leg: generische "beide teams treffen"-String-Pruefung schloss frueher HZ-Markets faelschlich ein -> jetzt "halbzeit"/"hz" ausgeschlossen. btts_ht/btts_sh Grading via kind (HT+FT-Score), deterministisch.
- VERIFIZIERT (Mock): Grading btts_ht/btts_sh korrekt, HT-Market nicht mehr gehijackt; Generator erzeugt btts2h+HOT nur bei xg>=3.5/3.4, NICHT bei niedrigem xg. Braucht Re-Deploy.

## Changelog — 2026-07-17 (Abrechnung: Root-Cause-Analyse + 3 Fixes für "viele Spiele nicht abgerechnet")
- URSACHE 1 (primaer): API-Football Tageslimit war erschoepft -> nichts rechnet ab, Rueckstand haeuft sich. Quota resettet taeglich; Anti-Burn-Fix (16.07) sorgt dafuer, dass kein settle_attempts verbrannt wird.
- URSACHE 2: Fixture-Aufloesung zu fragil. FIX find_finished_fixture(): match per Gegner-TEAM-ID (robust gg. Umbenennung, z.B. Henan Jianye->Henan Songshan Longmen) + Fallback "1 Verein = max 1 Spiel/Tag" (genau 1 finished Fixture am exakten KO-Datum -> akzeptieren). 3 Aufrufer uebergeben jetzt opponent_id.
- URSACHE 3: unabgedeckte Ligen (Chinese SL 2026, obskure UEFA-Quali wie CS Univ Craiova/MKK-Dnepr) sind GAR NICHT in API-Football -> nie abrechenbar. FIX purge_expired_autotips(): pending hq-system-Slips >48h nach letztem Anstoss werden entfernt (haeuften sich vorher ewig an).
- BUGFIX settle_hq_combos(): Combo mit 1 definitiv VERLORENEM Bein + 1 nicht-bewertbarem Bein (fehlende HZ-Daten) blieb ewig pending. Jetzt: any_lost -> sofort "lost"; nur ein WIN braucht alle Beine bewertbar. (2 zuvor blockierte Combos sofort abgerechnet.)
- VERIFIZIERT: Quota reset (3172/7500). Realer Lauf: 1 Single + 12 Combos + 18 Parlays abgerechnet; Pending 128->79. ID/Single-Fixture-Fallback per Mock bestaetigt. Combo-Fix: +2 abgerechnet. Backend 200. BRAUCHT RE-DEPLOY.
- BLEIBT (Datengrenze): Spiele in nicht von API-Football abgedeckten Ligen koennen nie auto-abrechnen (werden jetzt aber bereinigt/retried). Empfehlung: solche Ligen aus FOREBET_SLIP_CODES-Whitelist nehmen, damit erst gar keine unabrechenbaren Tipps entstehen.

## Changelog — 2026-07-17 (Auto-Blacklist gegen unabrechenbare Ligen)
- ZIEL (User): keine unabrechenbaren Tipps mehr erzeugen. Statische Whitelist-Kuerzung war zu riskant (z.B. 'ecl'=38 Tipps, rechnet meist ab; nur Namensaufloesung scheiterte). Forebet-Codes lassen sich nicht sicher auf API-Football-Ligen mappen.
- NEU: Selbstlernende Liga-Blacklist (db.league_settle_health). Jede abgerechnete Scraper-Wette = 'hit' fuer ihre Liga; jede fertige, nie abgerechnete + gepurgte hq-auto-Wette = 'miss'. Liga mit >=6 misses UND 0 hits -> auto-blockiert. Ligen mit hits werden NIE blockiert (schuetzt ecl/mls/...).
- Integration: _record_league_hit (settle_pending_tips + settle_hq_combos), _record_league_miss (purge_expired_autotips fuer stale hq-auto), _is_league_auto_blocked in forebet_autopost + _slip_eligible. Refresh beim Start + bei jedem forebet_autopost.
- PRE-SEED: 'cn1' (Chinesische Liga, verifiziert unabgedeckt: Teams loesen auf, 0 Fixtures 2026) via $setOnInsert beim Start blockiert (respektiert spaetere manuelle Freigabe).
- NEU Admin-Endpoints: GET /api/admin/league-health (blockierte Ligen + hit/miss-Zaehler), POST /api/admin/league-health/unblock {code} (Reset + Freigabe).
- VERIFIZIERT: cn1(6 miss,0 hit)->blockiert; ecl(2 hit,5 miss)->NICHT; _slip_eligible/forebet ueberspringt cn1; Refresh persistiert; unblock funktioniert; Startup-Seed + GET-Endpoint live bestaetigt (curl). Backend 200. BRAUCHT RE-DEPLOY.

## Changelog — 2026-07-17 (Fix: gewonnene Community-Scheine verschwanden nach 24h)
- USER-REPORT (Produktion): gewonnener Community-Schein von Tipster 'tipjarlogic' war weg. URSACHE: purge_settled_tips loeschte ALLE abgerechneten Scheine 24h nach Abrechnung, Ausnahme nur hq-system won.
- FIX purge_settled_tips: gewonnene Community-/Mitglieder-Scheine (source NICHT in hq-auto/smart/hq-live) bleiben jetzt DAUERHAFT (wie hq-system won). AI-Auto-Wins (hq-auto/smart/hq-live) + alle lost/void weiterhin Purge nach 24h.
- VERIFIZIERT (7 Faelle): member won=keep, member lost/void=purge, hq-system won=keep, hq-auto/smart/hq-live won=purge. Backend 200.
- HINWEIS: bereits geloeschter Produktions-Schein ist unwiederbringlich (Prod-DB, kein Zugriff). Fix verhindert kuenftigen Verlust. BRAUCHT RE-DEPLOY.

## Changelog — 2026-07-17 (Hall of Fame: neues helles Slip-Rendering v4 + tipjarlogic-Schein)
- _render_slip_image komplett neu (v4): heller/cremefarbener Buchmacher-Stil. Dunkles TipJar-Header-Band (Wortmarke + n-fach), farbiges Status-Band GEWONNEN(gruen)/VERLOREN(rot) mit ✓ + Gesamtquote, weisse Match-Panels mit Status-Leiste, Ergebnis-Chip (z.B. 2:1), Liga · Datum · Zeit Subline, gruene ✓ + Markt + gruene Quote je Wette, dunkler Footer (Label, @user, grosse Gesamtquote, Einsatz, Gewinn). ZENTRALES, dezentes TipJar-Crest-Wasserzeichen (alpha 0.08). Gleiche Signatur wie vorher.
- _regenerate_win_slips_once: Flag slip_v3 -> slip_v4 => alle bestehenden approved win_claims werden beim Start einmalig mit v4 neu gerendert.
- NEU _seed_hof_showcase_slip() (im _startup_seed): fuegt idempotent (fixe id seed-tipjarlogic-treble-5199919010) den gewonnenen 3-fach von @tipjarlogic ein: Dynamo Kyiv qualif.@1.36(0:0, UCL-Quali), CRB Ueber0,5+1,5@1.35(2:1, Brasilien Serie B), Valerenga DC12@1.19(6:1, Norwegen Eliteserien); Quote 2.19, Einsatz 20,00€, Gewinn 43,83€, mitgespielt. user_id via username-Lookup.
- Fixes: leere Quote zeigt nichts (statt fehlendem ✓-Glyph); Ergebnis-Chip nur bei echter Ergebniszahl (won/lost/offen ausgeschlossen).
- VERIFIZIERT: Render-Preview + Frontend-Screenshot (#hall-of-fame) zeigen beide Scheine korrekt im neuen Design; /api/wins/hall-of-fame liefert tipjarlogic-Schein mit Bild. Backend 200. BRAUCHT RE-DEPLOY.
- HINWEIS: HoF sortiert nach total_odds desc, limit 24. Der 2.19-Schein rankt niedrig -> auf Produktion evtl. nicht in Top-24 sichtbar, falls viele hoeher-Quoten-Scheine existieren.

## Changelog — 2026-07-17 (HoF-Rendering v5: kompaktes dunkles Design + Viewer-Scroll + Share)
- User-Feedback: v4 (hell) auf Handy unlesbar (7-fach zu lang -> im Viewer winzig gequetscht). Wahl C: komplett neues, kompaktes DUNKLES Design.
- _render_slip_image v5: dunkle Karte (void), kompakte 2-Zeilen-Rows pro Wette (Match+Quote / Markt + Liga·Datum), gruene ✓, volt-Quoten, Ergebnis-Chip, Status-Pill GEWONNEN/VERLOREN, dunkler Footer (@user, Gesamtquote, Einsatz/Gewinn), faint zentrales Crest-WZ. 7-fach jetzt 1000x1762 (vorher ~2530).
- Viewer (HallOfFame.jsx): Bild in voller Breite in scrollbarer Box max-h-80vh (statt object-contain-Shrink) -> ~5 Wetten sichtbar, nur wenig Scrollen bei grossen Scheinen, kein starkes Reinzoomen. Karten-Thumbnails: max-h-400px object-cover object-top (einheitliche Hoehe).
- Regenerate-Flag -> slip_v5 (alle approved Scheine werden beim Start mit v5 neu gerendert).
- VERIFIZIERT: 7-fach + 3-fach Render lesbar (Screenshots), Viewer mobil klar lesbar, Share/User-Buttons overlay korrekt. Frontend kompiliert. BRAUCHT RE-DEPLOY.

## Changelog — 2026-07-17 (Smart-Lab: KI antwortet realistisch, kein Meta-Leak; Fehl-Pick löschen)
- BUG (Produktion): Nutzer reichte FRAGE ein ('Hast du schon etwas zu Frankreich - England?'); KI veroeffentlichte stumpf einen Smart-Pick mit schwacher Meta-Begruendung ('da noch keine konkrete Wette im Raum steht...').
- FIX generate_smart_from_idea Prompt: Fragen werden als Bitte um Expertentipp behandelt -> KI gibt IMMER eine realistische, konkrete Wette (sinnvoller Markt, Quote 1.40-2.60) mit selbstbewusster, realistischer Vor-Spiel-Begruendung. VERBOTEN: Meta-Saetze wie 'keine konkrete Wette/im Raum steht'. Verifiziert (Frankreich-England -> BTTS@1.80; Bayern-Dortmund -> Sieg+Ueber2.5@1.65, kein Meta-Leak).
- CLEANUP _delete_owner_flagged_tips: loescht zusaetzlich die verknuepfte 'Eingegangene Idee' (smart_ideas) per tip_id + Frankreich/England-Textregex, damit die Eingabe-Karte verschwindet. Laeuft beim Start/Deploy, idempotent. (Bestehender france-Regex loescht bereits den Fehl-Tip.)
- BRAUCHT RE-DEPLOY (Produktion). Backend 200.

## Changelog — 2026-07-18 (Abgelaufene OFFENE Picks werden automatisch bereinigt)
- USER-REPORT (Prod): unabrechenbarer Pick 'Yelimay Semey – Alashkert' (16.07.) stand ~49h auf OFFEN. Ursache: purge_expired_autotips lief nur beim Start + alle 3h im forebet_loop (pausiert bei curated mode) -> Picks blieben haengen.
- NEU expire_stale_pending(): pending/live Picks, deren (letzter) Anstoss > EXPIRE_GRACE_HOURS(30h) zurueckliegt -> AI-Picks (hq-auto/smart/hq-live/hq-system) werden GELOESCHT, Member/Community-Picks werden auf 'void' (settled_by='expired') gesetzt. 30h > 24h Quota-Ausfall, damit keine noch-abrechenbaren Picks faelschlich weg.
- Eingebunden in: settlement_loop (alle 15 Min, zuverlaessig), settle_now (Sync-Button), tips_counts (bei jedem Homepage-Badge-Aufruf -> sofortige Bereinigung). cashed_out wird NICHT angetastet.
- VERIFIZIERT: expire loeschte 2 AI-Picks in Preview; danach 0 pending Picks aelter als 30h. Backend 200. BRAUCHT RE-DEPLOY.

## Changelog — 2026-07-18 (Bereinigungs-Log: nur echte Einträge)
- User: Admin-Log fuer abgelaufene Picks bauen, ABER Eintrag nur zeigen wenn logischerweise etwas bereinigt wurde (kein Null-Rauschen).
- expire_stale_pending schreibt jetzt einen db.cleanup_log-Eintrag NUR wenn deleted>0 ODER voided>0. Eintrag: at, deleted, voided, grace_hours, leagues (sortiert nach Haeufigkeit), matches[:40].
- NEU Endpoint GET /api/admin/cleanup-log (admin) -> letzte 100 echte Bereinigungslaeufe, inkl. betroffener Ligen (Basis um Ligen aus Scraper zu nehmen).
- VERIFIZIERT: leerer Lauf=0 Eintraege; echter Lauf=1 Eintrag mit Ligen ECL/TestLiga; AI geloescht, Member void. Backend 200. BRAUCHT RE-DEPLOY.

---
## 2026-07-22 — Analytics: echte Besucherzählung
- `/api/track/visit`: Zählung/Entdopplung jetzt per Identity — eingeloggte User pro **Konto** (`u:<id>`) über alle Geräte, anonyme pro **Gerät** (`d:<vid>`). Admin (role=admin) wird immer & retroaktiv ausgeschlossen (kein Zähl-Lag mehr).
- `/api/admin/visits`: unique/hits via Aggregation über `identity` (Fallback auf `visitor_id` für Alt-Docs, keine Migration nötig). Neue Felder: today_members/today_anon/total_members/total_anon.
- SecretInsights.jsx (/insights): neue Card-Zeile „Heute · eingeloggte Mitglieder vs. anonyme Besucher" (testids: stat-today-members, stat-today-anon, insights-member-split).
- Getestet via curl + DB + Screenshot. Wirkt auf Produktion erst nach Deploy.
- Follow-up: 14-Tage-Chart im /insights-Board jetzt zweifarbig gestapelt (grün=Mitglieder, grau=anonym). Backend `daily` liefert nun members/anon pro Tag. Höhe basiert auf unique (members+anon), nicht mehr hits.
- Live-Bereich: neuer 4. Sub-Tab "Community" (blau, testid live-cat-community). Zeigt Live-Tipps von echten Mitgliedern (source=members & status=live), keine KI. Frontend-only Filter in RateWall.jsx; loadLiveCounts zählt community separat (nicht mehr in value gebucht).

## 2026-07-22 — Phase 2: Spieler-Props automatisch abrechnen (DONE + getestet)
- settle_pending_tips(): Einzeltipps mit Spieler-Prop-Markt (scorer/sot/shots/fouls/card/saves + "beide teams karte") werden jetzt über _player_stats_for_fixture + _grade_player_leg abgerechnet statt score-only judge_market. Deckt Mitglieder-/Community-Spielertipps ab.
- Bugfix Namensvetter: _player_stats_for_fixture indiziert Spieler zusätzlich per Vollname ("full:<norm>"), _grade_player_leg matcht Vollname zuerst, Nachname als Fallback. Verhindert, dass ein Torschütze von einem gleichnamigen Nicht-Torschützen überschrieben wird.
- E2E getestet mit echtem Spiel (Alianza Lima 2:1 Sport Huancayo, fixture 1549411): Castillo Torschütze → won, Duarte Über 0.5 SOT → lost. Korrekt.
- OFFEN (Roadmap "mehr Datenquellen"): Phase 1 API-Football /predictions (Quota-Caching nötig), Phase 3 echte Buchmacher-Quoten, Phase 4 3. Scraper, Phase 5 mehr Ligen.

## 2026-07-22 — Phase 3: echte Buchmacher-Quoten erweitert (DONE + getestet)
- _parse_odds(): zusätzlich over35, under15, win_draw geparst (API-Football /odds).
- _real_odd_for(): NEU gemappt: Match-Winner "{Team} Sieg" → win_home/win_away (wurde vorher geparst aber nie genutzt!), "Über 3.5 Tore" → over35, "Unter 1.5 Tore" → under15.
- Effekt: Sieg-, Über 3.5- und Unter 1.5-Tipps tragen jetzt echte Buchmacher-Quoten statt Heuristik-Fallback.
- Getestet mit echtem Spiel (fixture 1490332): Über 3.5 → 2.00, Sieg → win_home 3.65.
- OFFEN Roadmap: Phase 1 /predictions (Quota-Caching), Phase 4 3. Scraper, Phase 5 mehr Ligen.

## 2026-07-22 — Phase 1: API-Football /predictions als 3. Prognosequelle (DONE + getestet)
- NEU: apifootball_predictions_autopost() + apifootball_predictions_loop() (alle 6h, leader-gated). Holt /predictions für kommende Top-Liga-Spiele (SLIP_LEAGUE_KEYWORDS, NS-Status) die KEINE andere Quelle hat → store_match_prediction(source="apifootball").
- Quota-sicher: max 20 Fixtures/Lauf, _api_quota_exhausted-Guard, 24h-Cache (collection apifootball_pred_cache), überspringt bereits abgedeckte Matches (_match_key).
- _goal_est() schätzt ph/pa aus /predictions goals-lines; fav/fav_prob aus percent; btts/over25 aus advice.
- Konsumenten-Schutz: scorers_today & goals_forecast sortieren jetzt nach Quellen-Priorität (forebet>predictz>sonst>apifootball) → Scraper-Daten gewinnen bei geteilten Matches, apifootball füllt nur Lücken.
- Admin-Trigger: POST /api/admin/apifootball/predictions/run.
- Getestet: 20 Prognosen gespeichert, alle Konsumenten (scorers/goals-forecast/systems) 200, neue Ligen-Abdeckung bestätigt.
- OFFEN Roadmap: Phase 4 (3. Scraper WinDrawWin/FootyStats), Phase 5 (mehr Ligen).

## 2026-07-22 — Phase 4: 3. Scraper Statarea (DONE + getestet)
- NEU statarea.py: scrape_statarea() rendert old.statarea.com/predictions (kein Cloudflare-Block), liefert pro Spiel 1X2-% + Über 1.5/2.5/3.5-% + Liga (Land,Liga) + optional vorhergesagte Score (nur bei bereits angepfiffenen → werden übersprungen).
- server.py: statarea_autopost() + statarea_loop() (alle 3h, chromium-gated, KEINE API-Quota). Schätzt ph/pa via _statarea_est_score aus 1X2+Über2.5. Speichert source="statarea".
- Quellen-Priorität erweitert: forebet(0)>predictz(1)>statarea(2)>apifootball(3) in scorers_today & goals_forecast → Scraper-Daten gewinnen, Statarea/apifootball füllen nur Lücken.
- Admin-Trigger: POST /api/admin/statarea/run.
- Getestet: 54 Prognosen gespeichert, korrekte Ligen, scorers 94 (Abdeckung gestiegen), systems/scorers 200.
- OFFEN Roadmap: Phase 5 (mehr Ligen im Whitelist).

## 2026-07-22 — i18n Fix: Tip-Card Lokalisierung (DONE + getestet)
- Bug: In nicht-deutscher UI (z.B. Griechisch) blieben Labels & Player-Prop-Markets deutsch.
- Fix RateWall.jsx: hartkodierte Labels "Parlay·Spiele", "Quote", "Einsatz", "Gewinn" → t("wall.parlay/game/games/odds/stake/payout").
- Fix i18n.js localizeMarket(): Player-Prop-Regexes ergänzt (Komma-Dezimal 0,5 + echte Phrasen: "Schüsse aufs Tor"→sot, "Torschüsse/Schüsse"→shots, "Fouls begangen"→fouls, "mal gefoult"→fouled, "Paraden"→saves, "Torschütze (Anytime)"→scorer, "sieht eine Karte"→getcard).
- Neue i18n-Keys in ALLEN 8 Sprachen: wall.parlay/game/games/odds/stake/payout + mkt.sot/shots/scorer/fouls/card/saves/fouled/getcard.
- Getestet: Screenshot Griechisch — Smart-Picks-Parlay zeigt "ΠΑΡΟΛΙ · 1 ΑΓΩΝΑΣ", "Σουτ στην εστία", "Κερδισμένα φάουλ", "Αποκρούσεις", "Απόδοση/Ποντάρισμα/Κέρδος".
- BEWUSST NICHT gefixt (User-Entscheidung "Άστα ετσι"): LLM-generierte ai_analysis / Qualifier-Briefing bleiben in Generierungssprache (DE/EN), da einmalig gespeichert.

## 2026-07-23 — Insights: Bot-/Testkonten ausblenden (DONE + getestet)
- REAL_MEMBER_QUERY (server.py ~L1423): schließt admin, @t.com Testkonten und hq@tipjar.com aus.
- /admin/visits "members" nutzt jetzt REAL_MEMBER_QUERY (beide Vorkommen). Nicht-destruktiv — Bots bleiben in DB, zählen nur nicht in Insights.
- Getestet Preview: members 78 → 18. Wirkt auf Produktion nach Deploy.
- User-Entscheidung: NUR ausblenden, KEIN Löschen.

## 2026-07-23 — Sprach-Erkennung + Push-Fixes (DONE + getestet)
- i18n.js: detectInitialLang() erkennt navigator.language/languages beim ersten Besuch (kein tj_lang) und mappt auf 8 Sprachen (en/es/de/el/fr/it/ar/tr), sonst EN. Vorher: immer EN. Getestet: de-DE Browser → App startet deutsch.
- NotificationBell.jsx: Self-Heal-useEffect on mount — falls Notification.permission==='granted', re-registriert die Subscription idempotent via enableWebPush (kein Prompt). Behebt "keine Pushes mehr" nach Deploy/DB-Wechsel/Endpoint-Rotation, wo Server-Sub verloren geht aber Browser noch "abonniert" denkt.
- NEU Backend POST /api/push/test: sendet Test-Push an eigene Subscription (prunt bei 404/410). Frontend: "Test-Benachrichtigung senden"-Button (bell-test-push) im Bell-Panel wenn on. i18n bell.test/test_sent/test_fail in 8 Sprachen.
- Wirkt auf Produktion erst nach Deploy.

## 2026-07-23 — Push-Prompt Verbesserung (DONE)
- NotificationPrompt.jsx: "Später"/Schließen setzt jetzt SNOOZE statt permanentem Dismiss — Prompt kommt wieder (Später=2 Tage, X=7 Tage) statt für immer weg. Deutlich bessere Opt-in-Conversion.
- Neuer Fallback-Trigger: erscheint auch nach ~25s für Besucher, die keinen Tipp öffnen (zusätzlich zum tj-viewed-pick Trigger). Session-Guard (max 1x/Session). Leichte Vibration beim Erscheinen (mobil).
- Eligibility unverändert: nur wenn Push unterstützt, nicht bereits an, permission != denied. In Test-Browser permission=denied → korrekt kein Prompt.
- Wirkt auf Produktion erst nach Deploy.

## 2026-07-23 — Blacklist erweitert (DONE + getestet)
- TEAM_LEAGUE_BLACKLIST += agama, hardrock, ekibastuz, ontustik, "astana ii", "triangle united". Präzise: "astana ii" blockt NUR Reserve, nicht FC Astana.
- _team_or_league_blocked() jetzt AUCH in apifootball_predictions_autopost (lg) und statarea_autopost (league) verdrahtet — vorher nur forebet/predictz/settle/andere Generatoren.
- Preview-DB bereinigt: 4 tips + 3 predictions gelöscht. Getestet: alle 4 Fixtures blocked=True, FC Astana/Real Madrid=False.
- Wirkt auf Produktion nach Deploy (verhindert neue; bestehende laufen aus/werden bei Regeneration ersetzt).

## 2026-07-23 — Share-Schein Bild KOMPLETT neu (DONE + getestet)
- User-Beschwerde (mehrfach): geteilte Scheine sahen "scheiße" aus → er machte lieber manuelle Screenshots.
- `_render_slip_image` in server.py komplett neu geschrieben (v6): premium dunkles "Ticket"-Design.
  - Gradient-Bühne + Volt/Status-Glow, gerundetes Ticket mit Schatten, Volt-Oberkante, faintes Crest-Wasserzeichen.
  - Gebündelte OFL-Fonts unter /app/backend/assets/fonts/ (Anton = Display/Quoten, BarlowCondensed = Titel/Status, Barlow = Body). Font-Fallback auf Liberation.
  - Header: Crest + TIPJAR-Wortmarke + Tagline + Status-Pill (OFFEN/LIVE/GEWONNEN) mit Glow. Meta-Bar "PARLAY · N SPIELE" + optional Live-Score.
  - Glassy Leg-Panels mit Status-Akzentleiste, Check-Badges, Volt-Quoten. Gruppen-Quote vertikal zentriert wenn 1 Quote für mehrere Märkte (HQ-System-Tips). ISO-Datum wird sauber formatiert (_clean auch auf time).
  - Perforation/Tear-off zwischen Body und Footer. Footer: Avatar + @user + Label | GESAMTQUOTE (großes Volt) | Einsatz/Gewinn | QR-Code → tipjarglobal.com ("SCAN & MITSPIELEN") für Conversion.
- Gilt für ALLE Slip-Verbraucher: /tips/{id}/share-image (RateWall Teilen), /wins/claim (Hall of Fame), Hintergrund-Tasks.
- Neue Deps: qrcode==8.2 (in requirements.txt). Fonts im Repo → deployen automatisch.
- Getestet: lokal (pending/won-Varianten) + live gegen /api/tips/{id}/share-image mit echtem HQ-System-Tip. Bilder sauber, keine Overlaps, QR scannbar.
- Wirkt auf Produktion erst nach Deploy.
- OFFEN (vom User verschoben): "Asiatisch Über 1.0 HZ" Grading (0=verloren, 1=Push/void, 2+=gewonnen) + Value-Banker-Generator (Tor in jeder HZ + Favorit trifft). Noch NICHT umgesetzt.

## 2026-07-23 — Markt-Lokalisierung Lücken geschlossen (DONE + live getestet)
- Beschwerde: Markt-Labels wie "Über 0.5 Tore 1. Halbzeit", "Asiatisch", "Über 3.5 Tore", "Bet-Builder" blieben beim Sprachwechsel DEUTSCH.
- i18n.js localizeMarket() erweitert: generisches Über/Unter N Tore, 1./2./jeder Halbzeit, "Tor in jeder Halbzeit", (Asiatisch), Doppelte Chance 12, Handicap, "trifft", Bet-Builder/3er/Risk/Mega, Beide (Teams) treffen. Team-Namen/Zahlen bleiben erhalten.
- 12 neue mkt.* Keys in ALLEN 8 Sprachen (ht1/ht2/eachhalf/goaleachhalf/asian/dc12/handicap/scores/bb/bb3/bbrisk/bbmega).
- bell.view_pick fehlte in 6 Sprachen (nur en/de) → in allen 8 ergänzt (Toast-Navigationsknopf-Label).
- Live getestet (EN, View AI System): "Over 1.5 Goals 1st Half / BTTS / Over 2.5 Goals" — 0 deutsche Reste.
- Wirkt auf Produktion erst nach Deploy.
- HINWEIS Notification-"Zum-Pick"-Knopf: Code intakt in allen 3 Pfaden (Service-Worker push actions "Zum Pick →" + notificationclick-Navigation; foreground pushNotify actions; In-App-Sonner-Toast action mit bell.view_pick). Wurde kürzlich HINZUGEFÜGT (commit 3bc1bc7), nicht entfernt. Vermutlich Produktion veraltet → Deploy nötig. Beim User rückbestätigen (Preview vs. Prod).

## 2026-07-23 — Push-Pop + Einreich-Flow + "Unknown"-Teams (DONE + getestet)
- Push-Nachricht (_push_payload_for_tip): jetzt mit (1) @Username des Posters (Community-Picks: Titel "👥 @Maxi" / Live "🔴 LIVE-Pick · @SwagWagner"), (2) Sterne-Rating im Body ("⭐ 7/10 · …"), (3) Navigations-Button "Zum Pick ansehen →" + Klick öffnet /?pick={id} (Service-Worker + notificationclick). Neuer Helper _push_stars() (win_prob für KI, sonst max ai/self/avg-Rating). Unit-getestet.
- SubmitTipModal komplett auf EIN Frame reduziert (kein zweites Fenster mehr): Dropzone + Text + Sterne + Timing (Live/Heute/Später) + Publish alle sofort sichtbar. Screenshot-verifiziert.
- Auto-Upload: pick() triggert scan() SOFORT beim Bild-Auswählen (Vor-Upload+Analyse im Hintergrund) → Publish ist instant. publish() nutzt lokales `d` und scannt notfalls selbst.
- Team-Namen-Fenster (_slip_needs_clarification) minimiert: erscheint NUR wenn Teams wirklich fehlen (API-Football-Vorabprüfung entfernt, die bei Minor-Ligen fälschlich nervte). Curl-verifiziert: Teams da → keine Nachfrage; Teams leer → ['teams','league'].
- "Unknown"-Teams-Fix: LLM gab "Unknown" wenn Teams auf Live-Screenshot nicht lesbar. Jetzt: (a) Prompt zwingt "" statt Platzhalter, (b) _clean_placeholder() normalisiert Unknown/N/A/TBD/Team A/? → "" (in analyze_tip + _sanitize_legs), (c) leere Teams → Clarify-Flow fragt nach. Preview-DB hatte 0 Unknown (das Beispiel war PRODUKTION).
- "Settle everything" via /api/admin/settle-now ausgeführt: nichts Fälliges offen (39 live in progress).
- Alles wirkt auf Produktion erst nach DEPLOY.

## 2026-07-23 — Anstoßzeit deutlich + Sortierung überall (DONE + Screenshot-verifiziert)
- User: Datum/Uhrzeit soll deutlich aussehen + früheste Spiele oben ("überall").
- Neuer geteilter Helper in i18n.js: kickoffInfo() (parst ISO 2026-..T.., dd/mm/yyyy, "23. Jul 2026", HH:MM), formatKickoff(mt,t) → deutliches Label "Heute 17:00 / Morgen 15:00 / 24.07. 15:00", kickoffTs(tip) für Sortierung (Min über match_time + legs, ohne KO → ans Ende).
- Neue Keys date.today / date.tomorrow in allen 8 Sprachen.
- RateWall (Tipp-Wand + KI Single-Game + Community + Live): prominentes Volt-Badge (Clock, text-sm bold) oben pro Karte; Karten nach kickoffTs aufsteigend sortiert; Legs pro Karte nach Anstoß sortiert; Leg-Kickoff jetzt als Volt-Badge statt roher String.
- Systems.jsx: parseKickoff/MONTHS_DE entfernt → nutzt formatKickoff; LegMeta jetzt deutliches Volt-Badge; system.selections nach Anstoß aufsteigend sortiert.
- Verifiziert (Live-Preview, EN): Systems "Today 17:00…19:00…22:30" korrekt sortiert, 0 rohe ISO-Strings; Single-Game-Wand 12 Kickoff-Badges. Auf DE zeigt es "Heute/Morgen".
- Wirkt auf Produktion erst nach DEPLOY.

## 2026-07-23 — "Auf Buchmacher spielen" 1-Klick-Schein (DONE + verifiziert)
- User will nicht Spiel-für-Spiel suchen; wünscht Button der ganzen Parlay beim Buchmacher erzeugt. RECHERCHIERT: echtes Auto-Platzieren auf Wazamba unmöglich (keine öffentliche API; Lizenz/AGB). Deep-Link-Prefill nur für große Books (bet365/Betway/Stake/Unibet…), NICHT Wazamba.
- Umgesetzt Variante a) (funktioniert mit JEDEM Buchmacher): neuer /app/frontend/src/playSlip.js → buildSlipText() (Kopf + nummerierte Legs "Spiel / Markt @Quote · Anstoß" + Einsatz/Gewinn + tipjarglobal.com) und playSlip() = SYNC copy (textarea+execCommand, VOR window.open wegen Fokus) → dann Wazamba (BOOKMAKER.url=https://www.wazamba.com) öffnen → Toast.
- Button in RateWall TipCard (nur status pending/live) und Systems SystemCard; Volt-Button, Ticket-Icon, data-testid play-slip-{id} / play-system-{key}.
- Neue i18n Keys play.btn/play.copied/play.manual/play.totalOdds/play.stake/play.win in allen 8 Sprachen.
- Verifiziert Live-Preview: 9 System- + 31 Single-Buttons; Klick öffnet wazamba.com + Zwischenablage enthält vollständigen sortierten Schein; Success-Toast.
- Backlog: echte Deeplink-Prefill via The Odds API/SharpAPI (kostenpflichtig) NUR wenn User zu unterstütztem Buchmacher wechselt.
- Wirkt auf Produktion erst nach DEPLOY.

## 2026-07-23 — Asian Über 1.0 HZ Grading + Value-Banker Generator (DONE + getestet)
- GRADE_VOID Sentinel: _grade_goal_leg gibt bei "Asiatisch Über 1.0 HZ" (kind ht_asian_o1 / Text-Erkennung) zurück: 0 HZ-Tore=False, 1=GRADE_VOID(Push), 2+=True, unbekannt=None. Auch _grade_ht_selection (Community/Parlay-Pfad) gibt "void".
- settle_hq_combos: void-Legs werden herausgerechnet (Quote→1.0, void_factor), all-void→status "void", sonst "won" mit neu berechneter Quote + potential_return. void+lost bleibt lost.
- Generator (Forebet-basiert): (a4) "Tor in jeder Halbzeit + {Fav} Über 0.5 Tore (Value-Banker)" [goal_each_half+team_o05, total>=3,xg>=2.8, Fav trifft, 8.0★]; (a5) Asian "{Fav} Über 0.5 + Über 1.0 HZ (Asiatisch) (Value-Banker)" [team_o05+ht_asian_o1, xg>=3.0, 7.5★].
- Lokalisierung: neue Keys mkt.valuebanker (8 Sprachen) + generischer "Ner-Bet-Builder"→"n× Bet Builder". Markt-Labels lokalisieren sauber (DE/EN geprüft).
- Verifiziert: Grader-Unit-Tests (0/1/2/unknown), HT-Selection-Pfad, Payout-Simulation (won+void→Quote/Payout korrekt, all-void→void, void+lost→lost), Backend healthy, settle-now ohne Crash.
- Wirkt auf Produktion erst nach DEPLOY.

## 2026-07-23 — Parlay-Abhak-Overlay (DONE + verifiziert)
- User: "will kompletten Parlay drauf haben" nach Klick. Auto-Platzieren auf Wazamba UNMÖGLICH (keine API) → stattdessen In-App-Checkliste.
- Neu: /app/frontend/src/components/PlaySlipOverlay.jsx — Overlay zeigt "Dein Parlay" + Gesamtquote, jedes Leg (Spiel + Markt lokalisiert + Anstoß-Badge + Quote) mit Häkchen, Fortschrittsbalken X/N, "🎉 Alle Spiele drin"-Banner, Footer: "Buchmacher öffnen" (öffnet Wazamba) + Kopier-Button. Beim Öffnen wird Schein automatisch in Zwischenablage kopiert (Toast).
- playSlip.js refaktoriert: exportiert buildSlipText/copySlip/openBookmaker/BOOKMAKER (playSlip() entfernt).
- RateWall: playData-State auf Component-Ebene + onPlay-Prop an TipCard (4 Render-Stellen); Overlay im Section-Root. Systems: playData-State in SystemCard + Overlay.
- Neue i18n-Keys play.overlayTitle/overlayHint/open/allDone/copyBtn in allen 8 Sprachen.
- Verifiziert Live-Preview: Overlay öffnet, 11 Legs sortiert nach Anstoß, Häkchen + 11/11 + Done-Banner, "Open bookmaker" öffnet wazamba.com, Auto-Copy-Toast. Kompiliert fehlerfrei.
- Wirkt auf Produktion erst nach DEPLOY.

## 2026-07-23 — "Kein Unknown posten" Regel (DONE + verifiziert)
- Problem: Mitglied "Swag Winners" postete Tipp mit Team "Unknown" (Live-Screenshot ohne lesbare Teams) → öffentlich sichtbar.
- Fix: neuer Helper _tip_has_known_teams(tip) (prüft home/away + legs.match gegen _clean_placeholder). list_tips (GET /tips) filtert team-lose Tipps aus ALLEN öffentlichen Feeds raus → deckt Altbestand + neue ab.
- Poster wird weiter per needs_clarification nach Teams gefragt; /tips/mine bleibt ungefiltert (er sieht/klärt seinen eigenen). Nach Team-Eintrag wird Tipp öffentlich.
- Verifiziert: Unit (empty/Unknown/leg-Unknown → hidden; echte Teams → shown) + Live-curl (source=members: teamless raus, ok drin). Backend healthy.
- Wirkt auf Produktion erst nach DEPLOY.

## 2026-07-23 — Warnhinweis "Teams nicht erkannt" im Einreich-Fenster (DONE)
- SubmitTipModal: Amber-Warnbanner (AlertTriangle) im Detected-Panel wenn Analyse keine Teams fand (home/away leer UND kein Leg mit echtem Match). Text: "⚠️ Teams nicht erkannt – bitte eintragen, sonst wird dein Tipp nicht veröffentlicht."
- Neuer i18n-Key submit.teamsMissing in allen 8 Sprachen. data-testid teams-missing-warning.
- Ergänzt die Server-Regel (team-lose Tipps werden aus öffentlichen Feeds gefiltert) um klare User-Kommunikation.
- Modal kompiliert/rendert verifiziert. Wirkt auf Produktion erst nach DEPLOY.

## 2026-07-23 — Bomben-Kombi (täglicher 15-Leg Mega-Parlay) (DONE + API-verifiziert)
- Owner-Wunsch: EIN großer täglicher 15er-Schein aus Spielen der nächsten 48h, gemischt aus Value-Draws ("riecht nach X"), klaren Favoritensiegen und Über 3.5 Toren.
- Implementiert in build_systems() (server.py ~5352): _bomben_pick (Value-X @3.30 / Favorit -1.5/-2.5 Handicap / Über 3.5) + _bomben_filler (Über 1.5 / Doppelte Chance / Über 0.5) → füllt IMMER bis 15 (min. 8 sonst weggelassen). Fenster jetzt→+48h, sortiert nach Anstoß.
- WICHTIG: nur ENDSTAND-sicher gradebare Märkte gewählt (judge_market kennt nur Endstand, keine HZ-Daten) → HT-X/FT-1 & "beide HZ gewinnen" bewusst weggelassen, um Fehl-Abrechnung zu vermeiden. Alle Legs settlen zuverlässig via settle_multimatch_parlays.
- key="bomben", steht ganz oben in System-Picks; snapshot_systems persistiert als hqsys-bomben-{day} → tägliche Auto-Abrechnung. i18n sys.title.bomben in allen 8 Sprachen. Subtitle dynamisch (Anzahl X/Siege).
- Verifiziert: GET /api/systems → bomben mit 15 Legs, Gesamtquote ~3.98 Mio, bucket "now", 9× Value-X + 6× Über 3.5, keine "Unknown"-Teams. Syntax OK, Backend healthy.
- Frontend rendert generisch (Systems.jsx) — Preview zeigte nur Emergent-Idle-Gate, kein App-Fehler. Wirkt auf Produktion erst nach DEPLOY.

## 2026-07-24 — Bomben-Kombi Fix: abgelaufene Spiele + falsche Picks (DONE + API-verifiziert)
- Owner-Beschwerde (Screenshot): Schein enthielt bereits gespielte Spiele; Coritiba–Palmeiras als "Unentschieden" trotz starkem Palmeiras-Auswärtssieg; Zeleznicar–Braga als "Über 3.5" obwohl 0:1.
- Fix 1 (abgelaufene Spiele): Fenster von now-15min → now+10min → now+48h. NUR noch nicht angepfiffene Spiele im Schein.
- Fix 2 (Favorit statt X/Über3.5): _bomben_pick priorisiert jetzt KLARE FAVORITEN zuerst (Handicap -1.5/-2.5, Über 1.5 Team, Doppelte Chance). Value-X (fav==draw ODER ph==pa) kommt ERST danach → ein klarer Favorit wird nie mehr als Remis gespielt. Über 3.5 nur wenn BEIDE Teams treffen (btts + ph>=1 + pa>=1) → kein einseitiger Favoritensieg mehr.
- Fix 3 (Mischung): Obergrenzen goals<=6, draw<=6 → kein 14×-Über-3.5-Klumpen mehr; Filler bevorzugt Favoriten-DC.
- Verifiziert Live-API: 15 Legs, 0 abgelaufen, Mix 6× Value-X + 6× Über 3.5 + 3× Favorit, Quote ~327k. Stale Snapshot gelöscht → baut neu.
- VERDACHT für die produktions-seitig gezeigten alten Spiele: PWA/HTTP-Cache oder älterer Build vor Deploy. Live-Preview-Build ist sauber. Wirkt auf tipjarglobal.com erst nach DEPLOY.

## 2026-07-24 — Reinigung alter Picks (auto) + Smart Briefing kürzen (DONE + verifiziert)
- Owner: "Lösche alle Picks vom 23; die Reinigung sollte automatisch laufen" + "Smart Briefing labert, sag nur Sinnvolles kurz & knackig oder lass es weg".
- ROOT CAUSE (23.-Spiele sichtbar): _in_kickoff_window filterte nur hours<24 → schloss VERGANGENE Spiele (negative Stunden) mit ein. Zusätzlich 25 KI-Picks OHNE match_time, die nie abliefen. Grace=30h ist bewusst >24h (API-Quota-Ausfall).
- Fix 1 (Display): _in_kickoff_window blendet Picks aus, deren Anpfiff >3h her ist (hours<-3 → False). Beendete/laufende Spiele verschwinden sofort aus KI-/Upcoming-Feeds.
- Fix 2 (Auto-Cleanup): expire_stale_pending löscht jetzt auch ZEITLOSE KI-Picks (kein Anpfiff) nach created_at-Grace → läuft automatisch im settlement_loop, keine Dauerleichen mehr.
- Sofort-Reinigung: 29 beendete/zeitlose pending KI-Picks gelöscht (pending 55→21). AI-Feed window=24 zeigt jetzt nur noch 24.07.
- Fix 3 (Briefing): _BRIEFING_SYSTEM neu → KEIN Intro/Floskeln, GENAU 1 Zeile pro Spiel mit dem EINEN wichtigsten Wett-Winkel, Spiele ohne Daten KOMPLETT weglassen, max 8 Zeilen, Cap 900 Zeichen. Verifiziert: 2 knackige Zeilen (nur echte Reise-Fakten), Rest weggelassen.
- Wirkt auf tipjarglobal.com erst nach DEPLOY (+ App einmal neu laden wg. PWA-Cache).

## 2026-07-24 — "Läuft/Live now"-Badge für angepfiffene Spiele (DONE + Screenshot-verifiziert)
- Owner: angepfiffene Spiele sollen nicht einfach verschwinden, sondern kurz als "läuft gerade" markiert werden, bevor sie nach Abgerechnet wandern.
- Helper isKickoffLive(mt) in i18n.js: true wenn Anpfiff 0–3h her (deckt sich mit Backend-Feldfilter hours>=-3, danach ausgeblendet).
- Neuer i18n-Key kickoff.live in allen 8 Sprachen (DE "Läuft", EN "Live now", ...).
- RateWall.jsx: Haupt-Kickoff-Badge zeigt rotes pulsierendes "Live now" statt gelber Zeit, wenn live & kein Backend-live_state (keine Doppelung). Leg-Badges ebenso (außer leg.status==='live'). Systems.jsx LegMeta analog.
- Verifiziert per Screenshot (Test-Pick Anpfiff -1h): rotes "Live now" auf laufendem Spiel, gelbe Zeit auf zukünftigen. Test-Pick danach gelöscht. Frontend kompiliert sauber.
- Wirkt auf tipjarglobal.com erst nach DEPLOY.
