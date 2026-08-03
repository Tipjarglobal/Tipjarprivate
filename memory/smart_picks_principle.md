# Smart Picks — Owner-Prinzip (2026-08-03)

**Smart Picks sind KEIN Lotto.** Owner-Regel, verbindlich für alle Generatoren und alle künftigen Agents.

## Was ein Smart Pick IST
- Sicher & logisch, gut begründbar aus echten Daten/Form.
- Einzelne, ruhige Value-Singles (~1.3–1.6) sind ideal.
- Beispiel (Owner-Referenz, 03.08.2026): **„Anytime Goalscorer o. Ersatzspieler — Robbie Ure" @ 1.41**
  (Halmstad vs. Sirius). Die Absicherung „oder sein Ersatzspieler trifft" macht den Pick ruhig —
  ein einzelnes Tor aus der Position reicht.

## Was ein Smart Pick NIE ist (= Lotto, verboten)
- „Zyklus"-Logik: „Team hat lange nicht getroffen/gewonnen → jetzt fällig". → DEAKTIVIERT
  (`smart_h2h_autopost` gibt sofort `return` zurück, Code erhalten aber unerreichbar).
- „Team, das nie 3 Tore macht, macht plötzlich 3 Tore" / Torfestival-Wetten auf schwache Angriffe.
- Alles, was auf „Trendumkehr/fällig" statt auf echter Stärke basiert.

## Enforcement
- `smart_h2h_autopost` bleibt deaktiviert + self-heal (löscht offene Zyklus-Picks bei jedem Lauf).
- Neue Smart-Generatoren nur mit sicheren, logischen Linien. Keine „due/fällig"-Heuristik.
