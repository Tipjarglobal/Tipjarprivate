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
- **Markt-Mechanik DC + Über (Owner 2026-07-22, wichtig!):**
  - „{Fav} Doppelte Chance + Über 1.5 (SPIEL)" → ein **1:1 reicht** (Favorit verliert nicht + 2 Tore im Spiel). SICHER. ← Pfeffer-Banker nutzen genau das.
  - „{Fav} Sieg + Über 1.5" oder team-spezifisch „{Fav} Über 1.5" → Favorit braucht **2+ eigene Tore** (1:0-Sieg verliert). RISKANTER (Fenerbahce 1:0 hat so einen Schein gekillt).
- **GEWINNER-MUSTER (2026-07-22, vom Owner beobachtet):** Ein cleverer Tipper spielte dominante
  Favoriten, die 4:0 gewinnen: Sturm (1X + Über 0.5), Crvena Zvezda (Sieg + Über 1.5), Lech
  (Gegner +2.5 + Über 1.5) — alle trafen 4 Tore. Verlor nur wegen Fenerbahce (Über 1.5, aber nur 1:0).
  → LEHRE: Auf den STARKEN FAVORITEN setzen, der SELBST 2+ trifft: „{Favorit} Doppelte Chance +
  {Favorit} Über 1.5 Tore". Der Favorit trägt den Schein — nie vom schwachen Team abhängen.
  → Pfeffer-Banker sind jetzt genau so gebaut. VORSICHT: auch Top-Teams gewinnen mal 1:0
  (Fenerbahce) → nur Favoriten mit vorhergesagten 2+ Toren nehmen (fav_goals≥2).
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

## Referenz-Quoten (User-Vorgabe 2026-07-23, Wettz-Screenshots)
Für Ligen OHNE echte Buchmacher-Quoten (Armenien, Baltikum, Kirgistan, Kosovo, MLS Next Pro II etc.) muss die Fallback-Heuristik (base_odd) ungefähr so aussehen:
- Team "Über 0.5 Tore" (Team trifft): ~1.10 (sehr niedrig, war 1.22)
- Match "Über 1.5 Tore": ~1.35-1.44 → base_odd 1.38 (war 1.28/1.30)
- Match "Über 2.5 Tore": ~1.65-1.70 → base_odd 1.70 (war 1.85)
- "Beide Teams treffen (Ja)": ~1.60-1.65 → base_odd 1.65 (war 1.80)
- "Über 8.5 Ecken": ~1.55 (ok)
- HT "Über 1.5 Tore": ~2.4-2.6 (ok)
- Match "Unter 3.5": ~1.40 | "Unter 3": ~1.36
Beispiel-Referenz-Combos: CFR Cluj Team Ü0.5 + Ü1.5 = 1.58 | Herediano Ü0.5+Ü1.5 = 1.37 | NE Rev II Ü2.5+BTTS = 1.81 | Liepaja Ü2.5+HT Ü1.5+BTTS = 3.80.

## Neue Muster vom Owner (2026-07-23) — "lern von mir, sei offener, mehr Ideen"
Der Owner will MEHR Vielfalt, nicht immer dieselben 3 Bausteine. Zwei konkrete neue Muster:

1) SAFE-FAVOURITE "Braga"-Dreiereck (10★, sehr sicher): ein starker Favorit, der knapp & tor-arm gewinnt.
   - Doppelte Chance 1X/X2  +  {Fav} Über 0,5 Tore  +  {Fav} Unter 3,5 Tore
   - Logik: Favorit verliert nicht UND trifft 1–3 Tore. Ein 1:0/2:1 reicht; ein Kantersieg schadet nicht (unter 3,5 pro Team).
   - Umgesetzt als opt "-favsafe" (rating 8.5). Neuer Grader-Kind team_u35 (team-spezifisches Unter).

2) VALUE-BANKER "Austria-Wien": frühes Tor in offenen Spielen.
   - Über 0,5 Tore 1. Halbzeit (asiatisches HT-Tor)  +  {Fav} Über 0,5 Tore
   - Als "Value-Banker" gedacht (hohe Trefferquote, faire Quote). Umgesetzt als opt "-htvalue" (rating 8.0).

GENERELLE ANWEISUNG: Bei der Tipp-Generierung offener/kreativer sein — verschiedene Markt-Kombis je nach Spielcharakter (tor-arm vs. offen), nicht stur dieselben Templates. Favoriten-Tipps immer absichern (DC statt reiner Sieg), Kantersieg-Risiko mit "Unter X,5 (Team)" abfedern.
