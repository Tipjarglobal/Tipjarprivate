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
