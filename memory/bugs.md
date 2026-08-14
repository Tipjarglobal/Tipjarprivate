# TipJar — Bug-Liste (verifiziert gegen echten Code)

Protokoll (Owner 2026-08-13): Bugs werden IMMER hier notiert. Beim Stichwort **"Valhalla"** liefert der Agent
je Bug einen credit-minimalen Prompt + fertigen Code-Block (zum Selbsteinsetzen in der Produktion),
damit der Owner möglichst wenig Credits verbraucht.

Status-Legende: 🔴 offen · 🟡 teilweise/needs-verify · 🟢 gefixt · 🟣 Valhalla-Code geliefert (2026-08-13), noch nicht deployed

VALHALLA 2026-08-13: Root-Causes final verifiziert. BUG-001+002 = Multi-Match-Routing + eingefrorener leg.live_score.
Fix-Blöcke geliefert für settlement.py (settle_hq_combos + settle_multimatch_parlays), betting_logic.py (precise_label), RateWall.jsx (leg-score-Anzeige).

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

## BUG-003 🟢-ready — Spieler-Schuss-Bein wird als „Gesamt-Tore Über 0.5" gelabelt
**WICHTIG (Owner 2026-08-13) — zwei UNTERSCHIEDLICHE Märkte, nicht verwechseln:**
- **Schuss / Schüsse** = normaler Schuss (shots, gr. σουτ) → niedrigere Quote, weniger Risiko. (Zafeiris-Fall = DIESER.)
- **Torschuss / Torschüsse** = Schuss AUFS TOR (shot on target / SOT, gr. σουτ στην εστία) → höhere Quote, mehr Risiko.
- Grading/OCR MÜSSEN beide getrennt behandeln (unterschiedliche Fixture-Stats: total shots vs. shots on target).
  Beim Labeln zählen aber BEIDE als Spieler-Prop → beide dürfen NIE zu „Gesamt-Tore" werden.
**Verifiziert:** `precise_label` (betting_logic.py:209). Zeile 225-228 Exklusions-Liste enthält KEIN
„schuss/schüsse/torschuss/torschüsse/shots/sot". Ein Bein „Zafeiris über 0.5 Schüsse" (Spielername, kein Teamname
im String) matcht `über 0.5` (Z.221), fällt durch die Exklusion und endet in Zeile 237 → „Gesamt-Tore Über 0.5".
**Fix (1 Zeile, sicher):** in das Tuple Z.225-228 aufnehmen:
`"schuss", "schüsse", "schusse", "torschuss", "torschüsse", "torschusse", "shots", " sot", "shot on"`
Nur Anzeige (precise_label ist display-only, ändert NICHT den Grading-String) → risikolos.

## BUG-004 🟢 GEFIXT — Bild-Upload crasht mit Cloudflare 520 (Owner 2026-08-14)
Ursache: AI_VISION_MODEL = "gemini-3.1-pro-preview" hing/retried endlos bei JEDEM Bild (LiteLLM-Retries
20:07:11→20:07:58→20:08:18) → >25s → Ingress-Proxy antwortet mit unparsebarem 520. OCR funktionierte nie.
Fix:
1. core.py: AI_VISION_MODEL → "gemini-2.5-flash" (multimodal, ~5s, günstiger). Bild-Upload liest jetzt in 5s.
2. server.py analyze_tip: LLM-Call in asyncio.wait_for(timeout=20) → fällt bei Hänger/Down schnell in den
   bestehenden Fallback (ai_error=True, safe=True) → Tipp ist IMMER postbar, auch ohne LLM.
Getestet: Text-Pfad (Flash) 5.6s ok; Bild-Pfad vorher 25s Timeout→jetzt 5.1s HTTP200 mit echten Teams/Quote.
