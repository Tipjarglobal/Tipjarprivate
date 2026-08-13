# TipJar — Bug-Liste (verifiziert gegen echten Code)

Protokoll (Owner 2026-08-13): Bugs werden IMMER hier notiert. Beim Stichwort **"Valhalla"** liefert der Agent
je Bug einen credit-minimalen Prompt + fertigen Code-Block (zum Selbsteinsetzen in der Produktion),
damit der Owner möglichst wenig Credits verbraucht.

Status-Legende: 🔴 offen · 🟡 teilweise/needs-verify · 🟢 gefixt

---

## BUG-001 🟡 — Master-Scheine landen nicht (immer) im Settled / gewonnener Schein „verschwindet"
**Owner-Wunsch:** ALLE Master-Scheine müssen runter ins Settled — entweder „Lost" oder „Best-Of/Won".
**Verifiziert im Code:**
- `settle_pending_tips` (settlement.py:782) schließt Parlays aus (`is_parlay: {$ne: True}`) → nur Singles. KORREKT so.
- `settle_hq_combos` (settlement.py:931-934) fordert `status:"pending"` UND `combo_legs:{$exists:True}` und löst
  EIN Fixture (home/away des Tipps) für ALLE Beine → nur für SAME-MATCH-Builder gedacht. Ein Master-Parlay
  über MEHRERE Spiele, das fälschlich `combo_legs` trägt, würde hier alle Beine gegen EIN Spiel bewerten (falsch).
  Und sobald ein Bein „live" ist, fällt der Schein aus `status:"pending"` → wird hier nie erfasst.
- ABER `settle_multimatch_parlays` (settlement.py:1119-1130) EXISTIERT und verarbeitet Multi-Match-Parlays
  (`status in [pending,live,cashed_out]`, `is_parlay:True`, `combo_legs:{$exists:False}`, `legs.0 exists`)
  Bein-für-Bein gegen JEWEILS EIGENES Fixture. → Die frühere Analyse „keine Funktion erfasst Multi-Match" ist FALSCH.
**Wahrscheinliche echte Ursache (bei Valhalla final verifizieren):**
- Master-Multi-Match-Builder speichert evtl. `combo_legs` (→ landet in hq_combos → All-gegen-ein-Fixture-Fehlgrading)
  ODER der Schein bleibt „live" und wird nur von hq_combos gesucht (das aber `pending` fordert).
- TODO Valhalla: prüfen, ob Master-Multi-Match-Builds `combo_legs` ODER nur `legs` setzen; hq_combos-Query um
  `status:{$in:[pending,live]}` erweitern und combo_legs-Zwang nur für echte Same-Match-Builder.

## BUG-002 🔴 — Settled zeigt Zwischenstand statt Endergebnis (z.B. „Boca trifft" bei 1:1 gewonnen → final 1:1 statt 3:1)
**Owner:** Scheine, die VOR dem Abpfiff (sobald Bein gewonnen) ins Settled wandern, müssen den Finalstand nachkorrigieren.
**Ursache (Hypothese, bei Valhalla verifizieren):** Der pro Bein/Schein angezeigte Score-Snapshot wird im Moment
der ersten „won"-Erkennung gespeichert und beim echten Full-Time nicht aktualisiert. Fix: beim finalen Settlement
(FT-Fixture) den echten Endstand jedes Beins (gh:ga aus find_finished_fixture) überschreiben, auch wenn das Bein
schon als „won" markiert war.

## BUG-003 🟢-ready — Spieler-Schüsse-Bein wird als „Gesamt-Tore Über 0.5" gelabelt
**Verifiziert:** `precise_label` (betting_logic.py:209). Zeile 225-228 Exklusions-Liste enthält KEIN
„schüsse/torschüsse/shots/sot". Ein Bein „Zafeiris über 0.5 Torschüsse" (Spielername, kein Teamname im String)
matcht `über 0.5` (Z.221), fällt durch die Exklusion und endet in Zeile 237 → „Gesamt-Tore Über 0.5".
**Fix (1 Zeile, sicher):** in das Tuple Z.225-228 aufnehmen:
`"schüsse", "schusse", "torschüsse", "torschusse", "schuss", "shots", " sot", "sog"`
Nur Anzeige (precise_label ist display-only, ändert NICHT den Grading-String) → risikolos.
