# TipJar — Owner's Betting Strategy Notes (INTERNAL ONLY — never show on website/UI)

These are the app owner's personal betting philosophy notes. Use them to tune the
auto-tip engines (ratings, source trust, markets). DO NOT display any of this text
publicly. Language: owner speaks German + Greek + Spanish.

## Star-rating discipline (MOST IMPORTANT)
- Be VERY careful with 9★ and 10★. A 9-10★ pick must almost never lose. Losing a
  9-10★ destroys trust. When in doubt, rate lower.
- Automated ceiling: do NOT auto-assign 10★. Keep auto-tips at 9.0★ max, and only
  the very safest markets (1+ goal in a high-scoring expected game) reach 9.0.

## Source trust
- DO NOT trust Predictz at all on its own. Its predicted scores are unreliable
  (e.g. it says 4-1 and the game ends 0-2).
- Predictz is only acceptable when it AGREES with Forebet on the same match
  (same over/goals signal or same favourite). Otherwise ignore Predictz.
- Forebet is the primary/more reliable engine.

## Theories to explore / encode over time
1. "Identical 1X2 odds type → similar results": matches that share the same 1X2
   odds shape/category tend to produce similar outcomes (cluster by odds profile).
2. "All results must make a circle / cycle": outcomes rotate over time; patterns
   repeat in cycles — don't assume the recent trend continues forever.
3. "Traditions are made to be broken" (Οι παραδόσεις είναι για να σπάνε):
   Historical head-to-head dominance is NOT reliable. Example: Lens–Arsenal was
   Lens's first-ever European home game and they had never beaten Arsenal, yet it
   looked like a both-teams-score first-half game. Owner tipped HT 1-1 and FT 2-1
   (odds ~40). So: do not over-weight historical H2H; read the current match shape.
4. "Good teams must score roughly every ~70 minutes": if a strong/attacking team
   has gone a whole match without scoring, treat 'they WILL score (next match /
   remaining time)' as a ~10★ conviction. i.e. regression-to-mean on goal drought
   for quality attacking sides → strong 'to score' / Over 0.5 team-goals angle.

## Practical mapping (current)
- Favor GOALS markets (Over 0.5 / Over 1.5 / BTTS / team-to-score) over match-result
  bets. Result bets (favorite to win) fail on upsets (see Olympiacos draws Sundays).
- Über 0.5 Tore (1+ goal in match) = the true banker (loses only on 0-0).
- Real bookmaker odds now come from API-Football /odds (per match), so 'not every
  1.70 is equal' is respected — odds are real where the fixture is priced.

_Last updated: 2026-07-07 by main agent, per owner voice notes._

## Winning example the owner shared — "Banker-Kombi" (favorites accumulator)
A 6-fold ACCUMULATOR of heavy favorites on the MATCH RESULT (1X2) market, each at
very short odds, multiplied together:
- Argentina 1.41 (3-2 vs Egypt), FC Sabah 1.22 (2-0), Una Strassen 1.29 (1-0),
  Hannover 96 1.14 (3-1), Spain (W) U19 1.15 (3-0), FC Lugano 1.14 (0-4).
- Total odds ~3.32, stake 250€ → 829,12€ won. All 6 legs won.
Insight: combining MANY very strong favorites (odds ~1.10–1.45) into one parlay is a
winning pattern — individual upset risk is small, the multiplier makes it pay. This
is DIFFERENT from betting a single favorite to win (which the owner distrusts). The
key is short-priced, high-confidence favorites across leagues, bundled.
→ TODO idea: add a "Banker-Kombi" system = 5–6 strongest Match-Winner favorites
  (real odds ~1.10–1.45, highest win% from Forebet probs) combined into one parlay.

## Over-market timing insight (owner voice note, 2026-07-08)
- Even the "banker" Über 0.5 can wobble until the 90th minute (real case: Víkingur
  0-0 bis zur letzten Minute, dann 1-0). So Über 0.5 is NEVER a true 10★ — keep the
  auto ceiling at 9.0.
- Prefer matches that score EARLY and score ENOUGH, so the bet turns green quickly
  and comfortably (3 goals by the 20th minute = Über 2.5 already won). We can't get
  goal minutes from Forebet, so use goal EXPECTANCY as the proxy: high Ø goals/game +
  high predicted total = attacking, early-scoring game.
- Engine mapping: goals-picks are now ranked by rating AND predicted Ø goals, so the
  most torreiche games surface first. Ambitious over-markets (Über 2.5, Über 2.5+BTTS)
  are only offered with a clear cushion (predicted total ≥ 4 AND Ø ≥ 3.2).
- Rule: ONE selection per match only — the "smartest" (best rating × odds). No more
  overlapping Über 0.5 + Über 2.5+BTTS on the same game.

## Underdog-scores-early rule (owner voice note, 2026-07-08) — HIGHEST PRIORITY
- In a game with a CLEAR favourite (e.g. Real – Atlético), prioritise the UNDERDOG /
  weaker side "<Team> Über 0.5 Tore" (team-to-score). The weaker team usually finds
  the net and often scores EARLY, so the bet turns green fast and wins even when they
  lose the match. This beats a plain match Über 0.5.
- Engine: when Forebet predicts pred=1/2 (clear favourite) AND the underdog's predicted
  score ≥ 1, we post "<Underdog> Über 0.5 Tore" with priority — it is chosen over all
  other markets for that match.

