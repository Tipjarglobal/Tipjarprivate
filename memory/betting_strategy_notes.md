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

## LIVE tips theory (owner voice note, 2026-07-08) — for the empty "Live Picks" channel
Real cases that shape the live logic:
- Víkingur: 0-0 the whole game, scored in the LAST minute → a live "match still to see
  a goal" can land very late; strong attacking pressure = keep faith in Über 0.5 live.
- Argentina: was 1-2 and turned it in the last ~10 minutes → late comebacks/goals are
  a real live edge when a quality side trails.
- Schweiz–Kolumbien: 0-0, NEVER a goal → warning: not every game gets a goal, so live
  "goal will come" is NOT automatic. Read the actual match, don't force it.
Owner's live angles to auto-generate (in-play, from API-Football live fixtures + stats):
1. First-goal timing: many games score in the first ~3 minutes, then stay flat. If a
   game is still 0-0 with heavy pressure (shots/corners), consider live Über 0.5 /
   next-goal; if it's flat and low-quality, DON'T.
2. Corners edge: if a team is TRAILING and winning lots of corners (piling pressure)
   but you feel they can't finish, give a live tip on THAT team to win MORE corners
   (team corners over X) instead of a goal.
3. Half-based goal markets: "Tor in der 1. Halbzeit", "Tor in der 2. Halbzeit",
   "Tor gegen Ende" — good live markets when the shape supports it.
Practical signals from live stats: shots on target, total shots, corners, ball
possession, dangerous attacks, current minute + score. Use these to pick ONE smart
live market per match, same one-pick-per-match discipline as the pre-match engine.

## LIVE "nachreichen" rule (owner voice note, 2026-07-08) — CORE of the live engine
- We already post ~37 pre-match AI picks at 8–9★ (Über 0.5 / BTTS / Über 2.5 etc.).
- When one of those matches is LIVE and the bet has NOT yet landed (e.g. an Über 0.5
  pick still 0-0), RE-OFFER it live at the (now higher) live odds. Second chance,
  better value.
- BUT be careful: only re-offer if there is still realistic pressure (shots on goal /
  corners). Do NOT re-offer a dead, flat game (à la Schweiz–Kolumbien 0-0 with no
  chances), especially late.
- Live tips auto-settle (won/lost) from the final score once the match ends.

## VALUE-ONLY rule (owner voice note, 2026-07-08) — OVERRIDES everything above
- STOP giving 50/50 (coin-flip) bets. Only give bets we win ~80% of the time (80/20),
  AND the odds must be > 1.60. I.e. give ~80% win chance at odd ≥ 1.60 = genuine value
  (bookmaker mispricing). If a market can't meet BOTH, don't post it.
- If a market family loses too often over time, STOP giving that family (self-learning).
- Engine mapping (Forebet + Predictz, source hq-auto): each candidate carries an
  estimated winprob; we apply the REAL bookmaker odd (API-Football) and keep only
  winprob ≥ 0.78 AND odd ≥ 1.60. `_banned_market_families()` disables any family whose
  settled win-rate < 0.55 over ≥ 8 samples. Coin-flip families (BTTS, Über 2.5,
  Über 2.5+BTTS, correct-score) are never posted; plain Über 0.5 (odds ~1.08) is filtered
  out by the 1.60 rule. Result: far FEWER but higher-quality picks. The prime value market
  is "Über 1.5 Tore" in clearly high-scoring games and DC/DNB on solid favourites when the
  book prices them ≥ 1.60.
- Trade-off the owner accepted: volume drops sharply (e.g. 1 pick out of 42 scanned).
  Threshold WIN_PROB_MIN can be relaxed toward 0.72 if more volume is wanted.


## Slip image + markets update (owner voice note, 2026-06)
- Generated "Fantasy Slip" (Pillow, `_render_slip_image`) now shows: TipJar title top-left
  + tagline, and per match a grey subline "Liga · Datum · Uhrzeit". These are read from
  the uploaded slip via Gemini Vision (`extract_win_slip` now returns league/date/time per
  leg). If any of the three is unreadable, that part is simply omitted. Word "Über"/"Unter"
  always spelled out; team-specific markets keep the team name.
- AI picks: added "Doppelte Chance 12" (home OR away, no draw) — offered when draw is
  unlikely; real dc_12 bookmaker odd from API-Football decides the value gate. Unter 2.5 /
  Unter 3.5 Tore now use REAL bookmaker odds too (under25/under35 parsed from /odds).

## Handicaps + Blacklist + Dedup (owner voice notes, 2026-07-08)
- HANDICAP theory (owner): Außenseiter-Handicap +3.5 ist SICHERER als "Unter 3.5 Tore".
  Beispiel Kairat–Sutjeska: Sutjeska +3.5 verliert NUR bei 4+ Toren Unterschied (0:4 verloren,
  1:4 GEWONNEN), während "Unter 3.5" bei 1:4 (5 Tore) verliert. → Handicap überlebt torreiche Spiele.
- Engine: bei jedem Favoriten (pred 1/2) werden jetzt Underdog-Handicaps angeboten:
  +3.5 (wp 0.92, Banker), +2.5 (0.87, Banker), +1.5 (0.73, Value wenn Quote≥1.60).
  Favorit -1.5 (wp 0.72) nur wenn erwartete Tordifferenz ≥2. Handicap schlägt "Unter X.5" im
  Banker-Tie-Break (0.92 > 0.90). Echte Asian-Handicap-Quoten noch nicht gemappt → Schätzquote.
- Korrekte Schreibweise beim Auslesen: "Sutjeska 3.5" → "Sutjeska Handicap +3.5" (Vision-Prompt).
- Doppelte Chance 12 + Unter 2.5/3.5 mit echten Quoten (früher ergänzt).
- BLACKLIST (Teams/Ligen, Keyword-Match auf home/away/league): "golden", "mogadishu", "kahibah".
  In forebet + predictz Autopostern und in _slip_eligible (Systeme) durchgesetzt. Erweiterbar in
  TEAM_LEAGUE_BLACKLIST.
- DEDUP: _dedupe_hq_tips() erzwingt EIN Pick pro Spiel über alle pending hq-auto (forebet+predictz).
  Bei Duplikaten (z.B. Über 0.5 + Über 1.5) bleibt der wertvollste (value>banker, dann höchste Quote),
  die risikoärmsten Duplikate werden gelöscht. Läuft am Ende beider Autoposter.
