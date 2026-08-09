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
