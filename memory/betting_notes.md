# TipJar — Owner Betting Notes (Private)

Persönliche Wett-Lernnotizen des Owners ("TipjarLogic"). Diese Regeln spiegeln die reale
Erfahrung des Owners wider und sollen die KI-Tippgenerierung steuern. IMMER hier nachschlagen,
bevor Tippgenerierungslogik geändert wird. Owner-Sprache: DEUTSCH.

## Harte Regeln (in Code umgesetzt)
1. **Verlängerung zählt NICHT.** Alle Tor-Märkte (Über/Unter) und Spieler-Props
   (z.B. "Messi Über 0,5 Torschüsse", "Über 1,5 Tore") gelten NUR für die reguläre
   Spielzeit (90 Min). → Helper `_reg_goals()` nutzt `score.fulltime` statt `goals`
   (API-Football zählt bei AET/PEN die Verlängerung mit). Angewandt in
   `find_finished_fixture`, `_datescan_fixture`, `_align_goals`. (2026-07-20)
   HINWEIS: Spieler-Schuss-Statistiken (/fixtures/players) trennen ET nicht separat —
   dort bleibt eine kleine Datenlücke bei K.-o.-Spielen mit Verlängerung.
2. **Keine Doppelte Chance (1X/X2) als Banker in Skandinavien/Nordics.** Diese Ligen
   (Allsvenskan, Superettan, Veikkausliiga, Eliteserien, Superligaen, Úrvalsdeild, …) sind
   zu unberechenbar. Beispiel-Verlust: "Ilves gewinnt nicht" → Ilves gewann 3:1.
   → `_is_scandinavian()` in `_forebet_candidates`: DC-Option wird dort übersprungen. (2026-07-20)
2. **Keine wertlosen Handicaps.** +2,5 / +3,5 Handicap = reale Quoten ~1,005–1,05 → null Value.
   NUR +1,5 anbieten (reale Quote ~1,55). +2,5/+3,5 entfernt. (2026-07-20)
3. **Keine eigenständige "Über 0,5 Tore"-Wette** (nur als Zweit-Leg im Builder). (2026-07-18)
4. **Kein Lotto-1X / kein "beide treffen" als Zufalls-Lotto.**
   - Bsp: Spanien–Argentinien → KI gab "beide treffen" (Lotto). Besser wäre: **Unter 2,5 Tore + 1X**.
5. **Brasilien NICHT löschen, aber NIE als Pfeffer/Über-Tipp!** Brasilianische Top-Ligen
   (Série A/B) bleiben bettbar; obskure Staatsmeisterschaften (paulista, carioca, …) geblockt.
   ABER: Brasilien NIE für Über-Tore/Pfeffer verwenden (Owner 2026-07-21: "Ich hasse es,
   Brasilien als Pfeffer zu benutzen"). Prognosen dort überschätzen Tore massiv:
   Atletico Mineiro (pred total 5 → real 1:1), Gremio Novorizontino (pred 4 → real 0:1).
   → Helper `_bad_for_overs()` schließt Brasilien aus Pfeffer- & TipJarLogic-Über-Kombis aus.
6. **Exakt-2-Tore-Falle (Asian Handicap):** Bei Über 2.0 mit genau 2 Toren = Push (Einsatz
   zurück, kein Gewinn). Bei Über 2.25 mit 2 Toren = halber Verlust. → Über 2.5 nur bei
   echten Torfesten (torreiche Ligen), niemals in torarmen Ligen wo 1:1/2:x typisch ist.

## Muster-Wissen (für zukünftige Features / KI-Prompts)
- **Nie von schwachen Teams abhängen (2026-07-21):** Radar sagte „Lincoln trifft" → Mjällby 3:0 Lincoln (Lincoln traf NICHT). Larne 0:4 Crvena zvezda, AGF 1:4 Lech. Lehre: NICHT auf das schwache Team setzen (BTTS/each-half, das das schwache Team braucht). Stattdessen den STARKEN FAVORITEN spielen (Favorit verliert nicht + Über-Linie, die der Favorit selbst liefert).
  → Pfeffer ist jetzt favoriten-verankert (`_pepper_qualifies`: nur Spiele mit starkem Favoriten, der 2+ Tore erwartet, ODER echtem Torfest total≥4 & btts). Banker = „{Favorit} Doppelte Chance + Über-Linie" oder Über/Unter-Range.
- **Zwei Pfeffer-Fenster (2026-07-21):** Di→Fr 12:00 (`pepper`) und Fr→Di 12:00 (`pepperwk`). Beide oben in den System-Picks.
- **Favoriten-Tracker (`db.favourite_teams`):** sammelt automatisch starke Favoriten (fav_prob≥60) → wächst zur ~50-Team-Liste. TODO: aus Ergebnissen lernen (Trefferquote je Team, chronische Versager wie Lincoln soft-blocken).
- **0:0 in Skandinavien real (2026-07-20 bestätigt):** Örgryte–Djurgården endete 0:0,
  Hafnarfjörður–Breidablik endete 0:0. Beweis, dass 0:0 dort möglich ist → bei Über-Wetten
  in nordischen Ligen vorsichtig, torlose Spiele ehrlich als solche kennzeichnen.
  → Tor-Prognose-Tabelle zeigt 0:0-erwartete Spiele als "kein Tor erwartet".
- **Tor-Prognose-Tabelle (umgesetzt 2026-07-20):** `/api/goals-forecast` zeigt pro Spiel,
  wie viele Tore jedes Team laut Vorhersagescore (ph/pa) schießt (⚽ = 1 Tor). WICHTIG:
  Bälle kommen aus der PROGNOSE, nicht aus der Quote — kein Ball nur weil ein Favorit @1.20
  steht. Ein Team mit 0 vorhergesagten Toren bekommt 0 Bälle.
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
