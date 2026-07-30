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

