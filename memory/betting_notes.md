# TipJar — Owner Betting Notes (Private)

Persönliche Wett-Lernnotizen des Owners ("TipjarLogic"). Diese Regeln spiegeln die reale
Erfahrung des Owners wider und sollen die KI-Tippgenerierung steuern. IMMER hier nachschlagen,
bevor Tippgenerierungslogik geändert wird. Owner-Sprache: DEUTSCH.

## Harte Regeln (in Code umgesetzt)
1. **Keine Doppelte Chance (1X/X2) als Banker in Skandinavien/Nordics.** Diese Ligen
   (Allsvenskan, Superettan, Veikkausliiga, Eliteserien, Superligaen, Úrvalsdeild, …) sind
   zu unberechenbar. Beispiel-Verlust: "Ilves gewinnt nicht" → Ilves gewann 3:1.
   → `_is_scandinavian()` in `_forebet_candidates`: DC-Option wird dort übersprungen. (2026-07-20)
2. **Keine wertlosen Handicaps.** +2,5 / +3,5 Handicap = reale Quoten ~1,005–1,05 → null Value.
   NUR +1,5 anbieten (reale Quote ~1,55). +2,5/+3,5 entfernt. (2026-07-20)
3. **Keine eigenständige "Über 0,5 Tore"-Wette** (nur als Zweit-Leg im Builder). (2026-07-18)
4. **Kein Lotto-1X / kein "beide treffen" als Zufalls-Lotto.**
   - Bsp: Spanien–Argentinien → KI gab "beide treffen" (Lotto). Besser wäre: **Unter 2,5 Tore + 1X**.
5. **Brasilien NICHT löschen!** Brasilianische Top-Ligen (Série A/B) bleiben bettbar. Nur
   obskure Staatsmeisterschaften (paulista, carioca, …) bleiben geblockt. Bei Live-Overs in
   Brasilien vorsichtig sein (oft passiert nichts, dann Tor in der Nachspielzeit) — aber NICHT
   pauschal ausschließen. (Hard-Exclusion 2026-07-20 wieder entfernt.)

## Muster-Wissen (für zukünftige Features / KI-Prompts)
- **"Hungrige" Torteams jagen:** Wenn ein Team wie **Göteborg** in einem Spiel gar nicht trifft,
  trifft es sehr wahrscheinlich im nächsten. Solche Teams gezielt auf "Team trifft" backen.
- **0:0-Historie:**
  - Team mit LANGER Historie OHNE 0:0 → ein 0:0 ist bald fällig (Vorsicht bei Overs, evtl. Under/0:0).
  - Team mit FRISCHER 0:0-Historie → wird bald wieder Tore schießen (Overs / Team trifft backen).
- **Sichere Live-Kombi (Owner-Style, umgesetzt):** 2–4 bereits erfüllte Über-Legs (Spiel hat schon
  Tore → "Über 0,5/1,5" ist gesperrt) aus verschiedenen laufenden Spielen → Gesamtquote ~1,5.
- **Banger (umgesetzt):** Goal-Fest-Momentum — wenn schon ≥3 Tore + offen/schnell → höhere Über-Linie.
  Offenes 0/1-Tor-Spiel mit Druck → "Asian Über 2.0" (Push bei genau 2).
- **Smart-KI (umgesetzt):** gibt IMMER einen konkreten, coolen Tipp; nie leere Fehlermeldung.

## Offene Owner-Wünsche (Backlog)
- **"Wer trifft heute?"-Radar:** Über viele Spiele hinweg einfach sagen, WELCHE Teams heute treffen
  werden (Bsp genannt: **Malmö, Breidablik, Göteborg**). Fokus auf verlässliche Torteams +
  "hungrige" Teams (siehe Muster oben). → eigenes Feature, noch zu bauen.
