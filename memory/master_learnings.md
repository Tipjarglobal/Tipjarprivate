# TipJar Master / Tipp-Logik — Owner Learnings (2026-07-30)

Der Owner ist frustriert über schwache Master-Picks. Diese Regeln MÜSSEN eingebaut werden.

## 1. TIMING bei "Team trifft" / Über 0.5
- Fehler: App sagte "The New Saints treffen" → stimmte, ABER erst 91'. Owner hatte "trifft bis 85'" getippt → verloren.
- Regel: Nicht blind "Team trifft" sagen. Berücksichtigen WANN ein Team typischerweise trifft.
- Markiere Teams, die LOCKER früh treffen (bis 40', 60', 75').
- Ausgabe entweder:
  - generell "Über 0.5 Tore bis zur 60. Minute", ODER
  - konkretes Team: "Team X trifft bis zur X. Minute"
  - X ist IMMER eine von: 40, 60, 75, 90.
- Teams, die nur spät treffen können, NICHT für frühe Zeitfenster empfehlen.

## 2. "Durstig auf Tore" (goal-thirst) — Ausschlüsse
- Grundregel bleibt: Team, das letztes Spiel NICHT getroffen hat, trifft wohl im nächsten. (Pafos-Beispiel war korrekt: Pafos 4-0.)
- ABER: Master gab fälschlich "Hajduk trifft" (Auswärts-Underdog) → Pafos-Hajduk 4-0, Hajduk 0. → Master soll die STARKE Seite backen, nicht blind den durstigen Auswärts-Underdog.
- Qarabag: hatte ZUHAUSE nicht getroffen → auswärts noch schwerer → evtl. schlecht geworden → NICHT in Durstig-Statistik aufnehmen.
- Ausschluss: Teams, die selbst zuhause nicht treffen / vom Modell auf 0 Tore gesetzt werden / klare Auswärts-Underdogs.

## 3. Statistik-UI (erste Halbzeit)
- Kürzer & übersichtlicher machen — Owner will nicht so viel scrollen.
- KEINE doppelten Einträge: z.B. "Paok - Dinamo Tor erste HZ" darf NICHT zweimal erscheinen
  (einmal weil man für Paok spricht, einmal für Dinamo). Pro Spiel nur EIN Eintrag.

## 4. Konkrete beobachtete Ergebnisse (zur Kalibrierung)
- Pafos - Hajduk 4-0 (Master lag mit "Hajduk trifft" falsch)
- Paok - Konstantelias: 2 Tore
- Panathinaikos: beide treffen bereits 1-1
- Qarabag: zuhause kein Tor

## 5. Master-Avatar (neue Idee)
- Im Master-Kanal einen Master-Avatar mit Sprechblase.
- Er sagt konkret, was sicher passieren wird, z.B.:
  "Pafos hatte nicht getroffen und wird diesmal treffen. Zuhause sind sie stark."

## Kosten (separat, vom Owner genehmigt)
- B) Text-LLM (Analyse/Moderation/Übersetzung) auf günstiges Modell (Gemini Flash), Vision-OCR bleibt Pro.
- C) Scraper: nur Picks mit guten Sternen posten.

## 6. K.o.-Duelle: NUR die starke / aggregat-führende Seite backen (2026-07-30)
- Fehler (Owner-Screenshots, Wazamba): "So viele gute Spiele und wir backen Torshavn."
  - HB Torshavn: Hinspiel 0:2 hinten, auswärts Underdog → Rückspiel 0:3 → Handicap +0.75 VERLOREN.
  - Hajduk Split: 0:2 hinten, auswärts → "Über 0.5 Tore" → Pafos 4:0, Hajduk 0 Tore → VERLOREN.
  - Gewinner-Seiten waren die STARKEN: Pafos (0:2 vorn → 4:0), Nordsjaelland (→ 6:0), Derry Under 3.
- REGEL: In Zwei-Bein-Duellen (und generell bei klarem Favoriten) NIE die schwache/zurückliegende
  Auswärts-Seite backen (kein Sieg/Handicap/"trifft"/Über 0.5 auf den Underdog). IMMER die
  aggregat-führende / starke Seite. Umgesetzt:
  - `_favourite_side_map` + `_leg_backs_clear_underdog` (server.py): Master-Bein-Pool
    (`_master_leg_candidates`) droppt team-spezifische Beine auf der klaren Underdog-Seite (fav_prob≥62).
  - `goal_thirst`: klare Underdogs (fav_prob≥62, Gegenseite Favorit) werden aus "trifft"-Liste
    ausgeschlossen, außer das Modell erwartet selbst 2+ Tore.
  - `knockout_tie_autopost` backt ohnehin bereits den Hinspiel-Sieger (korrekt).

## 7. Avatar-Calls NUR auf verifizierte, reale Spiele (2026-07-30)
- Fehler (Owner): "Spiel existiert nicht" — ein Avatar-Call (Arges Pitesti – Miercurea Ciuc) war
  ein Phantom-Spiel aus match_predictions, das API-Football nicht bestätigte.
- Fix: `master_avatar_calls` verifiziert JEDES Spiel vor dem Posten via `resolve_team_id` +
  `find_upcoming_fixture` (auch reversed). Ohne bestätigtes Fixture (echter Anstoß im Fenster) →
  Call wird übersprungen. Nutzt reale Namen/Anstoß/Liga aus dem Fixture. Kein Phantom-Spiel mehr.
- Avatar-Sprechblase + Karten sind vollständig lokalisiert (Sprechblasen-Text via prose-Cache,
  Idle-Zeile + Tab-Label via i18n-Keys master.avatar.idle / master.cat.avatar in allen 8 Sprachen).

## 8. 10★ NUR für echte Banks — Live-"noch ein Tor" ist NIE 10★ (2026-07-30)
- Fehler (Owner): "10 Sterne Austria Über 4.5 Tore verloren — rote Karte, Spiel vorbei, sie wollten
  nicht mehr." Live-Banger in `live_autopost` vergaben pauschal `rating=10.0` für die nächste
  Over-Linie (oft "Über (total+1).5" = ZWEI Tore mehr nötig!).
- REGEL: Ein Live-Bet, der noch ein/zwei Tore BRAUCHT, ist keine Bank. Owner-Regel "live nie
  unschlagbar, Cap 7★" galt bisher nur für die Push-Anzeige, nicht für die gespeicherte Bewertung.
- Fix (`live_autopost`, server.py): Bewertung jetzt EHRLICH aus der Live-Quote abgeleitet
  (rating ≈ min(7, 1/odd·10)), gedeckelt bei 7★. "Über 4.5" (2 Tore nötig) → ~3★ statt 10★.
  Bestehende Live-Banger-Tips >7★ einmalig auf 7★ geklemmt. Analyse-Text warnt jetzt ehrlich
  (rote Karte / Zeitspiel kann kippen).
- NUANCE (Owner): "Manche Über 4.5 sind sicherer — aber ein Aggregat 5:1 mit roter Karte kann das
  Spiel früher enden." → Nicht pauschal alle Über-Linien abwerten. Kontext-Strafen NUR bei
  Gefahrensignalen (`_live_overline_penalty`): klarer Vorsprung/Blowout (|Tor-Differenz|≥3 → −2★),
  rote Karte im Spiel (aus denselben Live-Stats, kein Extra-Call → −1★), K.o.-Duell/Pokal
  (führende Seite verwaltet → −1.5★). Offene, ausgeglichene Nicht-K.o.-Spiele behalten bis 7★.
  Bei zu vielen Signalen (Rating <3★) wird die Über-Linie gar nicht mehr angeboten.

## 9. Stürmer in Galaform als Signal (2026-07-30)
- Owner: "Pavlidis hat für Benfica 4 Tore gemacht." → Ein Stürmer, der gerade einen 4-Packer
  (oder Doppelpack) gemacht hat, ist ein starkes Signal: sein Team trifft/gewinnt, und er selbst
  ist ein Top-"Anytime-Scorer"-Kandidat im nächsten Spiel.
- IDEE (noch NICHT umgesetzt — braucht Spieler-Daten aus API-Football /players): "In-Form-Scorer"-
  Boost für Avatar/Master: wenn ein Schlüsselstürmer zuletzt 2+ Tore machte, dessen Team-Über-0.5 /
  Team-Sieg höher bewerten und ggf. einen "Spieler trifft"-Call ausgeben. Owner fragen, bevor gebaut.

## 11. Hot-Scorer-Kombi = Hall-of-Fame-Schein (2026-07-30)
- Owner: "Hätten wir Konstantelias UND Pavlidis über 1.5 Tore gespielt, dann wäre der Schein in der
  Hall of Fame." → mehrere In-Form-Stürmer in EINEN aggressiven Doppelpack-Schein kombinieren.
- Umgesetzt: `master_hotscorer_combo()` (server.py, in master_loop, 1×/Berlin-Tag): findet 2–3
  brace-fähige Galaform-Stürmer (gl≥0.6) in VERIFIZIERTEN Fixtures, baut ein Multi-Match-Parlay
  "{Spieler} trifft 2+ (Doppelpack)" mit Gesamtquote → Hall-of-Fame-Kandidat. Eigener Tab
  "🔥 Torjäger-Kombi" (master_category=hotscorer). Gift-Guard aktiv.
- Zusätzlich: Avatar-Einzel-Call wird bei richtig heißen Stürmern (gl≥0.8) zu "{Spieler} — 2+ Tore
  (Doppelpack)" statt nur Anytime.
- SETTLEMENT: `_grade_player_leg` scorer respektiert jetzt `need` (line+1) → Doppelpack (2 Tore)
  korrekt abgerechnet; `settle_multimatch_parlays` wertet Spieler-Torschützen-Legs pro Fixture
  (holt player-stats). Anytime (need=1) unverändert. Unit-getestet: 2 Tore=WON, 1 Tor=LOST.

## 10. GESCHENKE haben Vorrang — keine andere KI darf widersprechen (2026-07-30)
- Owner: "Wenn das Geschenk sagt Qarabag unter 2.5, dann darf in der Statistik NICHT 'Qarabag
  trifft' stehen, der Master darf NICHT 'Qarabag über 2.5' wählen und der Mental darf es NICHT
  'über 4.5' geben. Was die Geschenke sagen, hat Vorrang — keine weitere KI kann dagegen tippen.
  Der Master soll meistens aus Geschenken, Smart-Picks und Statistiken auswählen."
- Umgesetzt (server.py): `_gift_stance_map()` liest alle offenen Geschenk-Tips (is_gift) und leitet
  je Spiel eine Haltung ab (team_over/team_under, match_over/match_under). `_conflicts_with_gift()`
  + `_gift_under_lean()` erkennen Widersprüche. Eingebaut in:
  - `goal_thirst` (Statistik "trifft") — widersprechende Teams raus.
  - `mental_autopost` — Geschenk-"unter"-Spiele bekommen keinen Über-4.5-Mental.
  - `_master_leg_candidates` — kein widersprechendes Master-Bein.
  - `master_doublepack`, `master_special_build` — Geschenk-"unter"-Spiele übersprungen.
  - `master_avatar_calls` — kein Avatar-"Fav trifft" gegen ein Geschenk.
- Regel-Nuance: Geschenk auf EIN Team ("Qarabag unter") sperrt nur dieses Team (Gegner darf
  weiter "trifft"); ein Match-"unter" sperrt jedes "über"/"trifft" im ganzen Spiel.


## 12. KEINE Feature-Vorschläge / Next Action Items (Owner 2026-07-31)
- Owner: "Frag diese 4 Sachen nicht wieder." → beim finish-Tool KEINE ausgedachten
  Feature-Ideen / Enhancement-Vorschläge auflisten. Nur bauen, was der Owner explizit sagt.
  Kurze Abschluss-Zusammenfassung ohne "Next Action Items"-Ideen.

## 8. FREUNDSCHAFTSSPIELE / TESTSPIELE — kein Torschützen-Vertrauen (Owner 2026-08-08)
- Beobachtung (Owner): Es gibt im Sommer SEHR viele Freundschaftsspiele. Aufstellungen sind NICHT scrapebar → man weiß vorher nicht, wer wirklich spielt.
- Barcelona spielte am 08.08.26 ZWEI Spiele am SELBEN Tag (Barcelona 1-0 Forest UND Udinese 1-0 Barcelona) → geteilter Kader, beide Aufstellungen schwach → "Scheiße gespielt", kaum Tore.
- REGEL: Der Master soll in Freundschaftsspielen KEINE Torschützen-/Über-Tore-Picks blind setzen. Ein starker Klubname (Barça, Bournemouth, Real …) heißt NICHT, dass die A-Elf aufläuft oder trifft.
- UMSETZUNG (Code, master_hotscorer_combo): Freundschaftsspiele werden aus der Torjäger-Kombi komplett AUSGESCHLOSSEN (Liga-Name enthält friendl/freundschaft/testspiel/φιλικ/amistoso/amichev). Zusätzlich existiert _is_domestic_league_fx (schließt friendl/cup aus) für die Ligaklassifizierung.
- MASTER-VERSTÄNDNIS (Ziel): Falls Freundschaftsspiele doch mal genutzt werden, muss der Master erkennen, welche Teams "verstärkt genug antreten" (A-Kader) um zu treffen — sonst NICHT backen. Bis Aufstellungsdaten sicher vorliegen: Testspiele meiden.

## HINWEIS ZUM BRAIN
- Alles, was der Owner mir gibt (Screenshots, Ergebnisse, Regeln), wird HIER im Brain notiert. HQ und Master lernen daraus. Dieses File ist die Quelle für Kalibrierung & Regeln.

## 9. CONTRARIAN-DENKE: "Was fickt die Scheine der größten Masse?" (Owner 2026-08-09)
- Grundprinzip: Wenn die Scraper 3-1 andeuten, kann es genauso 2-2 enden. Der Master soll IMMER denken "was fickt die Masse".
- Beobachtete Fehlschläge der Masse (Favoriten, die NICHT gewannen): Bochum-Hertha 0-1; PSV nicht gewonnen; Sporting nicht gewonnen; Wolfsburg 0-0; Darmstadt. Hunderte weitere.
- REGEL 1 — Sprechblase (Avatar) nur UNFICKBARE Aussagen: statt "Über 0.5 1.HZ" / "Torschütze" (fällt bei 0-0 durch) jetzt Rotation aus (a) "{Favorit} gewinnt mindestens eine Halbzeit", (b) "Doppelte Chance {Favorit}", (c) "Über 1,5 Tore" (nur goal-friendly). Diese gewinnen SELBST bei einem 2-2. Umgesetzt in master_avatar_calls.
- REGEL 2 — Neuer "Hard"-Bereich (master_hard_2_2): EINE tägliche Kombi aus EXAKTEN 2:2 für Fallen-Spiele. Faktoren wie gestern PSV/Sporting/Darmstadt: klarer-aber-nicht-überragender Favorit (fav_prob 50-72), BEIDE Seiten laut Prognose ~2 Tore (ph>=2 & pa>=2), Gesamt <=5, |ph-pa|<=1, keine Friendlies. Cap 6 Beine (sonst astronomische Quote). Settlement: "Genaues Ergebnis 2:2" deterministisch (judge_market Shortcut).
- Beispiel: 3 Spiele × 2:2 ≈ Quote 2197 (Owner-Idee "8000er"). Mini-Einsatz, Mega-Traum.

## 10. FLAGGEN + OCR-Feedback (Owner 2026-08-09)
- Flaggen: EINE Landesflagge oben links VOR jedem einzelnen Spiel (Single & Kombi-Beine). Die alte Flaggen-Reihe oben rechts wurde ENTFERNT. flagFor(): Country-Name → ISO2-Code (z.B. "co"→🇨🇴) → Liga-Keyword → 🌍-Fallback (jedes Spiel MUSS eine Flagge haben). NATION/LEAGUE-Maps stark erweitert (EN+DE). Master-Kombi-Beine speichern jetzt "country".
- Konnte KEINE von "Agent E3" vorbereitete Flaggen-Version im Code finden → frisch implementiert.
- OFFEN (braucht LLM-Vision-Credits zum Testen): TipJarLogic/Codemining-OCR liest Slips falsch: "FC Sion" statt "FC Sion Draw No Bet"; "Molde Über 0.5 Team-Tore" falsch übernommen. Außerdem sollen die RICHTIGEN Uhrzeiten aus dem Slip übernommen werden. → mit Owner abstimmen, bevor Credits verbraucht werden.

## 11. OCR-Prompt-Fixes (Owner 2026-08-09, Option B: nur Prompt, kein Test)
- AI_SYSTEM (TipJarLogic-Slip-Reader) + read_betslip (Win-Claim) ergänzt:
  • DRAW NO BET: 'Draw No Bet'/'DNB'/'Sieg ohne Unentschieden'/'Unentschieden keine Wette' => '<Team> Draw No Bet' (Team MUSS drin bleiben, NIE zum reinen Sieger verkürzen). Beispiel-Fehler war 'FC Sion' statt 'FC Sion Draw No Bet'.
  • TEAM-Tore Over/Under: 'Molde over 0.5' => 'Molde Über 0.5 Tore' (Team + Linie behalten, NICHT zu Gesamt-Tore machen).
  • Per-Bein 'kickoff' = exakt die neben DEM Match gedruckte Uhrzeit (nie leeren/verschieben/erfinden).
- Nicht getestet (Owner wollte Credits sparen). Bei nächstem echten Upload prüfen.
- KNOWN FOLLOW-UP (Settlement): betting_logic _leg_predicate wertet DNB-Remis aktuell als WIN (h>=a) statt VOID/Rückzahlung. Falls DNB-Beine künftig falsch abgerechnet werden → dort Remis=void nachrüsten.

## 12. DNB-Abrechnung korrigiert (Owner 2026-08-09)
- judge_market (settlement.py) hat jetzt einen deterministischen DRAW-NO-BET-Shortcut (kein LLM/Credits):
  Remis (hg==ag) => VOID (Rückzahlung); gebacktes Team gewinnt => won; verliert => lost.
  Team wird aus dem Markt gelesen ("{Team} Draw No Bet"/"{Team} DNB") und via _teams_match Home/Away zugeordnet (Default Home).
- Getestet mit 6 Fällen (Sion/Servette, Home & Away, Sieg/Remis/Niederlage) → ALLE OK.
- Gilt für Einzel- UND Kombi-Beine (beide laufen über judge_market). Void-Bein wird im Parlay als Push behandelt und die Quote neu gerechnet.
- Der frühere Follow-up (Remis-als-Win) ist damit erledigt.

## 13. Sprechblasen-Vielfalt: neue unfickbare Aussage (Owner 2026-08-09)
- Neu in der Avatar-Rotation: "{Favorit} verliert nicht zur Halbzeit" (settlement kind=ht_no_loss: f1>=o1, Favorit liegt zur HZ NICHT hinten). Überlebt selbst 0-0/2-2 zur Pause; verliert nur, wenn der Favorit zur HZ zurückliegt.
- Rotation jetzt: half_any → ht_no_loss → dc (→ over15 nur goal-friendly).
- Settlement: _special_gift_kind erkennt "verliert nicht zur halbzeit/hz"; _grade_special_gift kind ht_no_loss; _fav_side_in_fixture splittet jetzt auch auf " verliert" (Team-Zuordnung Heim/Auswärts).
- Deterministisch getestet (6 Fälle Heim+Auswärts, Sieg/Remis/Rückstand HZ) → ALLE OK. Keine Credits.

## 14. KOSTEN-SENKUNG: teures LLM-Modell nur noch für Vision (Owner 2026-08-09)
- Problem: gemini-3.1-pro-preview (AI_MODEL) lief auf JEDEM Tipp-Rating (analyze_tip) → Hauptkostentreiber. Übersetzung war NIE das Problem (bereits Flash + DB-Cache).
- Fix (core.py): AI_MODEL = "gemini-2.5-flash" (günstig, für häufige TEXT-Analyse), NEU AI_VISION_MODEL = "gemini-3.1-pro-preview" (stark, nur für Bild/OCR).
- server.py: analyze_tip (1342) + SmartLab-Fan-Hint (9240) wählen jetzt pro Aufruf: Bild vorhanden → AI_VISION_MODEL (OCR-Genauigkeit bleibt, schützt Draw-No-Bet/Team-Tore/Uhrzeiten-Fixes); nur Text → AI_MODEL (Flash). Reine Vision-OCR (Win-Slip 3310, Code-Reader 9808, Lineup 12365) bleiben auf AI_VISION_MODEL.
- Getestet: Text-Rating läuft auf gemini-2.5-flash (Log bestätigt), Rating 9.0, kein Fehler. Backend startet sauber.
- Info: App nutzt EINEN EMERGENT_LLM_KEY (nicht 3). Kosten = Modell-Wahl + Token-Volumen, nicht Übersetzung.

## 15. Englisch als Basissprache + Asian Handicap -1 + Hard-Umbenennung (Owner 2026-08-09)
- HAUPTSPRACHE = ENGLISCH. Master-Markt-Labels jetzt Englisch: "Double Chance {fav}" (nicht "Doppelte Chance"), "{fav} wins at least one half", "{fav} not losing at half-time", "Over 1.5 Goals". Combo-Titel: "🔥 Top Scorer Combo", "🎯 HARD". Hard-Beine: "Correct Score 2:2". Badge-Labels + Tabs Englisch.
- NEU in Sprechblasen-Rotation: "{fav} -1 Asian Handicap" (Sieg mit 2+ = won, mit genau 1 = VOID/Rückzahlung, sonst lost). Owner-Hauptwunsch "Lugano -1". Rotation: ah_minus1 → half_any → ht_no_loss → dc (→ over15 goal-friendly).
- Settlement: _special_gift_kind erkennt jetzt EN+DE (half_any, ht_no_loss) + neu ah_fav_1; _grade_special_gift ah_fav_1 gibt True/"void"/False; _fav_side_in_fixture bilingual (Team am Marktanfang, startswith). Einzel-Settler finalisiert deterministischen Push (void) statt Endlos-Retry (definitive_push-Flag).
- "Hard 2:2"-Bereich heißt jetzt nur noch "Hard" (Tab + Badge).
- Getestet: AH -1 Grading (5-0=won, 2-1=void, 1-1=lost, Auswärts analog) + EN-Kind-Erkennung → OK. Screenshot: Bubble zeigt "FK Crvena Zvezda -1 Asian Handicap @1.70" (EN), Hard-Tab, Flaggen pro Spiel.
- NOCH OFFEN (Owner-Wunschliste, nicht gebaut): Team-Total-Value-Picks im Master ("Sion over 1.5 team", "Vaduz over 1.5 team", "St. Gallen total over 3.5"), lockere ~10er Tore-Kombi, "over 23.5 shots"-Markt aus Experten-Reads.

## 16. Value Goals Combo + Shots-OCR + Team-Total-Englisch-Fix (Owner 2026-08-09)
- NEU master_value_goals_combo() → master_category "valuecombo", Tab "💎 Value Goals". 1x/Berlin-Tag, ~6er-Kombi (~6-15x): "{Team} Over 1.5 Goals" für starke Scorer (ph/pa>=1.8, prob>=0.45) + "Over 3.5 Goals" für torreiche Spiele (total>=3.6). Odds via _prob_over/_odds_from_prob. Keine Friendlies. Deckt Owner-Wunsch "Sion/Vaduz over 1.5 team + St.Gallen total over 3.5 + lockere 10er Kombi" ab. Getestet: 6 Beine @14.72.
- Verdrahtet: master_loop, reset-refresh, mcat-Filter, Frontend Tab+Counts+Badge.
- SHOTS-OCR: AI_SYSTEM erkennt jetzt Shots-Märkte ("Over 23.5 Shots"/"Schüsse"/"shots on target") und lässt sie als SHOTS (nicht Goals) stehen — nie in Tore umwandeln.
- BUGFIX (app-weit): localizeMarket hatte KEINE Regel für die deutsche Team-Total-Kanonform "{Team} Team-Tore Über X" → blieb bei EN-Locale deutsch. Neu: Regel + Key mkt.teamgoals (en "Team Goals", de "Team-Tore"). Jetzt zeigt EN "Team Goals Over 1.5" (Screenshot bestätigt). Betraf ALLE Team-Total-Picks, nicht nur den neuen Combo.

## 17. VALUE = schwaches Team trifft doppelt (Owner 2026-08-10)
- Gewinner-Schein (Owner): Sirius vs IF Brommapojkarna — "Brommapojkarna (schwaches/Auswärts-Team) Over 1.5 Tore" + "Total Over 3.5" als Same-Game Bet-Builder @4.75, gewonnen bei 2:2. Zweites Beispiel: AZ Alkmaar Res vs FC Eindhoven — "Eindhoven Over 1.5 + Total Over 3.5" @2.90.
- KERN-LEARNING: Der VALUE steckt darin, das SCHWÄCHERE Team zu backen, dass es ZWEIMAL trifft (Over 1.5 Team-Tore) — die Quote ist hoch, weil der Markt es unterschätzt. Kombiniert mit "Total Over 3.5" im SELBEN Spiel = großer Value.
- LEAN halten: Owner "könnte noch Tor 1.HZ / Sirius Over 1.5 dazunehmen, aber die Quote steigt kaum und mehr Beine = mehr Risiko". Also nicht überladen.
- WICHTIGE NUANCE (nicht Learning #6 widersprechen): NUR in torreichen, AUSGEGLICHENEN Spielen backen, wo BEIDE Teams treffen (min. projizierte Tore ≥1.4 pro Team, Gesamt ≥3.6). NIEMALS ein einseitiges Blowout-Underdog-"trifft".
- UMSETZUNG (server.py master_value_goals_combo): jedes Bein ist jetzt ein Same-Game-Builder "{schwächeres Team} Over 1.5 Goals" + "Over 3.5 Goals" (Gate: total≥3.6 & min(ph,pa)≥1.4 & pw≥0.40 & pt≥0.42). Fallback = einzelnes starkes Over-1.5 / Over-3.5. Schlank: 2–4 Beine, Cap Quote 60. Getestet (Mock): Brommapojkarna O1.5 @2.1 + O3.5 @1.9 korrekt gebaut. Abrechnung über bestehende settle_multimatch_parlays (2-Selektions-Beine wie Special).

## 18. WARUM „schwaches Team trifft doppelt" Value ist — die Faktoren (Owner 2026-08-10)
Owner erklärt den Sirius–Brommapojkarna-Schein (2:2, Quote 4.75) im Detail. Diese Denke soll der Master lernen:
- **Kurze Anreise / lokales Derby**: Brommapojkarna reist nur ~53 km → keine Reisemüdigkeit, das Auswärtsteam kann voll auftreten. Große Distanzen schwächen Auswärtsteams, kurze nicht.
- **H2H-Muster (STÄRKSTES Signal, umgesetzt)**: „Sirius kassiert zuhause IMMER 2 Tore von denen." Direktvergleich bestätigt: Brommapojkarna traf 2+ in fast jedem Duell (0-3, 3-2, 3-2 bei Sirius zuhause; 2-4 auswärts). → Value-Bein „schwaches Team Over 1.5" wird jetzt nur gebaut, wenn der H2H (match_stats.h2h_detailed, gecacht) real 2+ in ≥50% der letzten Duelle zeigt (`_h2h_team_scores_2plus`). Ohne H2H-Daten → Modell-Gate.
- **Tabellenkonstellation / Motivation**: Sirius steht 1. mit 10 Punkten Vorsprung → auch ein Remis tut nicht weh → verwaltet, verteidigt lockerer → offenes Spiel. Brommapojkarna (13.) hat „Punkte-Not" → maximale Aggression → trifft. (NOCH NICHT im Code — bräuchte /standings-Daten, quota. Als Mental-Modell notiert.)
- **„Fickerei-Faktor" / Contrarian**: Die MASSE kauft das Offensichtliche — „Sirius Sieg" + „Sirius Over 1.5" @1.40. Der Value liegt im 2:2 (beide treffen, hohes Total) @4.75. Immer fragen: „Was fickt die Scheine der Masse?" → Genau der Kern der Value Goals Combo (siehe auch Learning #9).
- UMSETZUNG heute: H2H-Bestätigung im Value-Builder (server.py master_value_goals_combo + `_h2h_team_scores_2plus`). Standings/Motivation + Reisedistanz bleiben als Mental-Modell (quota/Datenlage) — bei Bedarf mit Owner abstimmen, bevor gebaut.

## 19. SMART PICKS: KOMPLETTE Community-Kombi übernehmen (Owner 2026-08-10)
- Fehler (Owner-Screenshot): @TipJarLogic postete eine Kombi "Dembélé Torschuss + PSG trifft + PSG verliert nicht @1.81" (PSG–Aston Villa Finale). Die KI kollabierte das auf EIN eigenes Bein "PSG Team-Tore Über 0.5 @1.81" und erfand eigenen Text. FALSCH.
- REGEL: "Du musst IMMER die gesamte Kombi annehmen, nicht jedes Mal etwas Eigenes aussuchen und eigenen Text erfinden. Übernimm, was der Spieler nimmt, und passe den Text darauf an. Nur ändern, wenn eine Selektion zu unlogisch klingt." Nur wenn KEINE konkrete Wette vorliegt (reine Frage) darf die KI selbst einen Tipp vorschlagen.
- UMSETZUNG (server.py):
  • `generate_smart_from_idea` Prompt umgebaut: bei konkreter Wette/Slip ALLE Selektionen als `legs[]` faithfully übernehmen (nichts droppen/tauschen/erfinden), Spieler-Quoten behalten, Selektion nur bei Unlogik ändern, Analyse an die EXAKTEN Selektionen anpassen. JSON neu: is_combo, same_match, legs[], total_odds.
  • `submit_smart_idea`: bei ≥2 Beinen → Parlay-Tip. Same-Match-Builder → `combo_legs` (Abrechnung via settle_hq_combos) + display `legs`; Multi-Match → nur `legs` (settle_multimatch_parlays). market = Selektionen mit " · " verbunden, odds = total_odds. Single-Fall unverändert.
- Getestet (Mock): 3-Bein-PSG-Kombi korrekt gebaut (legs 3 + combo_legs 3, is_parlay, odds 1.81, Analyse passt). Frontend rendert legs[] automatisch als Parlay (RateWall 1308+) — keine FE-Änderung.
- NICHT mit echten LLM-Credits getestet (Owner-Kostenwunsch) — beim nächsten echten Upload prüfen.

## 20. DOPPEL-K.O.: Psychologie > Quoten (Owner 2026-08-11)
- Bei Zwei-Bein-K.o.-Duellen WENIGER auf Quoten schauen, MEHR auf Psychologie:
  • Το γκολ της τιμής: das "Ehrentor", das die schlechte/unterlegene Mannschaft am Ende doch macht.
  • Η ομάδα που πιέζει και δεν σκοράρει, στο τέλος το δέχεται: das Team, das verzweifelt drückt und einfach nicht trifft, kassiert am Ende selbst.
- AGGREGAT-REGEL (Owner-Kalibrierung, echte Ergebnisse 11.08.26):
  • Wenn das FINALE AGGREGAT für die gute Mannschaft ÜBER 4 Tore geht, trifft am Ende meist auch die schlechte Mannschaft mindestens 1 Tor. Beispiel: Dinamo Zagreb Hinspiel 5:0 → Rückspiel Žalgiris 1:2 (Debeljuh 56'), finales Aggregat 1:7 → Žalgiris hat doch getroffen.
  • Vorschlag: in solchen einseitigen Rückspielen "{schwache Mannschaft} trifft / Über 0.5 Tore" anbieten (z.B. "Žalgiris trifft über 0.5").
  • NUR SEHR WENIGE Teams treffen über ZWEI Spiele GAR NICHT: an dem Tag nur Kairat (Aggregat 0:2) und Sparta Praha (Aggregat 0:3). Also die "schlechte trifft am Ende doch"-Regel ist stark.
- ERGEBNISSE zur Kalibrierung: NEC–Olympiacos 2:1 n.V. (agg 2:1); CSKA Sofia–Panathinaikos 1:2 (agg 2:3, Ehrentor Dvali 87'); Bodø/Glimt–USG 3:2 n.V. (agg 6:5, torreich beide); Sturm–Fenerbahçe 0:1 (agg 0:3).
- HALTUNG: Hab KEINE ANGST, im Master (Hard-Bereich) ernste, schlaue Wetten zu geben. Die Master-Bereiche dürfen NICHT leer sein.

## 21. Master-Bereiche NIE leer + Beispiel-Wetten (Owner 2026-08-11)
- Genaue Ergebnisse (Hard): Olympiakos 1:1, Panathinaikos 1:1, Bodø/Glimt 2:2.
- Oder weniger Risiko: Union SG trifft 2× (Über 1.5) + Über 3.5 Tore; schwächere Mannschaft (Nijmegen) trifft und verliert nicht; die bulgarische Mannschaft trifft und verliert nicht.
- Sabah gewann mit 29:14 Torschüssen (Geschenk @1.44) UND 4:0 mit VIER späten Toren → Schuss-Dominanz + späte Tore sind ein starkes Über-/Team-trifft-Signal.

## 22. LIVE-CUTS + HZ-Tor in die Sprechblase (Owner 2026-08-11)
- HZ-Tor-Tipps LIVE komplett GECUTTET: gewinnen nur ~1 von 5 (an dem Tag Bodø, Roter Stern, Sabah alle 0:0 zur HZ). Live "Über 0.5 Tore 1. Halbzeit" wird nicht mehr gepostet.
- ALLE Live-Vierer ("Vierer-Live-Kombi") GECUTTET — schaut kein Mensch, zu kleine Community. (server.py live_autopost Abschnitt 5 → `if False`.)
- Ein SERIÖSES Pregame-HZ-Tor (kein Joker/Geschenk) gibt jetzt der MASTER in der Sprechblase (master_avatar_calls: neue Option "ht_goal", nur bei über25 + total≥3.2 + 0:0 praktisch ausgeschlossen → "Over 0.5 Goals 1st Half" @1.44, bilingual gradebar).

## 23. SYSTEM PICKS AUS + Buttons Admin-only (Owner 2026-08-11, Credit-Notfall)
- ALLE System-Picks abgeschaltet: `snapshot_systems()` → return 0 (keine hq-system-Scheine mehr, spart Settlement-Quote). Bestehende offene hq-system-Scheine gelöscht.
- Buttons "System Picks" und "Codemining" nur noch für Admin sichtbar (Header.jsx + App.js Overlay-Nav via isAdmin = user.role==admin). Verifiziert per Screenshot: für Nicht-Admin beide weg.

## 24. MASTER-TRAINING per Button = fast 0 Credits (Owner-Frage 2026-08-11)
- Owner fragt, ob ein Button zum "Trainieren" des Masters (Ergebnisse zeigen, gewonnene Freunde-Scheine, Kommentare/Analysen) weniger Credits kostet.
- ANTWORT: JA, drastisch. Das SPEICHERN von Ergebnissen/Kommentaren kostet 0 LLM-Credits (nur DB-Text). Die Lernregeln wirken über CODE-Regeln + dieses Brain-File, nicht über teure LLM-Dauerläufe. Ein Trainings-Button (Owner tippt/fotografiert Ergebnisse → landet in master_learnings/DB) ist der günstigste Weg, das Gehirn zu schärfen. Kann als nächstes gebaut werden.
