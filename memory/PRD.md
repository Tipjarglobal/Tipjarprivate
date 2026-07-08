# TipJar — Product Requirements & Progress

## Problem Statement (verbatim intent)
Global community platform "TipJar" where people worldwide post football/sports betting tips.
AI auto-rates each tip; users rate them on a Rate Wall (Apex Scale 1–10). Animated jar + alarm bell
(no-signup alerts). Submit = tutorial or screenshot upload; AI auto-detects teams/time/country/league
and auto-rates. Credits economy (Stripe buy, gift w/ 10% fee, redeem at 10k for real money via PayPal).
Languages: EN, DE (primary), EL, FR, IT. Auto results engine (API-Football Pro) flips Pending->Won/Lost.
Automated betting tips scraped from Forebet/Predictz ("TipJarHQ Picks"). System bets. Player-prop
"Smart Bets" from API-Football stats. USER LANGUAGE = GERMAN (respond in German).

## Tech Stack
FastAPI + MongoDB (motor) + React (CRA/craco) + Tailwind. framer-motion, canvas-confetti, lucide-react.
AI: Gemini 3.1 Pro via emergentintegrations (EMERGENT_LLM_KEY). Payments: Stripe (test). Object storage:
Emergent. Auth: JWT Bearer. Scrapers: Playwright/Chromium (forebet.py, predictz.py). Results + player
stats: API-Football Pro (api-sports.io, 7500 req/day, season stats available).

## Personas
Tipster, Rater, Anonymous visitor (bell), Admin (settles tips).

## Current areas (tips window tabs + header quick-views)
1. AI Picks (source=hq-auto) — Forebet/Predictz-derived DNB + safe goals bankers, kickoff-window filter.
2. AI System Picks (GET /api/systems) — 4 systems: lock / value / risk / gamble (whitelist leagues).
3. Smart Bets (source=smart) — NEW, player props from API-Football season stats.
4. Members Picks (source NOT in [hq-auto, smart]).
5. Live Picks (status=live).

## Key backend endpoints
- GET /api/tips?source=ai|smart|members&status=pending|won|lost|live&window=24|48|48plus&sort
- GET /api/tips/counts -> {ai, ai_total, members, live, systems, smart}
- GET /api/systems, GET /api/system-slip
- POST /api/admin/settle-now, /api/admin/forebet/run, /api/admin/predictz/run,
  /api/admin/autotips/reset, /api/admin/smart/run, /api/admin/smart/reset
- Auth login body key: "email" OR "username" + "password".

## Implemented history (condensed — see git log for full detail)
- Core: auth (JWT, optional email), landing + animated jar, notification bell, submit+AI analyze,
  Rate Wall (filters, 10-star, streak), leaderboard, credits (Stripe buy/gift/redeem), i18n EN/DE/EL/FR/IT,
  admin settle, referral rewards, email verify (Resend/dev-link), content moderation (Gemini vision+text).
- Auto-tips: Forebet (primary, DNB + goals bankers w/ kickoff time) + Predictz (supplementary BTTS/Over),
  source anonymised as "hq-auto"/"TipJarHQ", league whitelist, realistic odds, chromium self-heal.
- Systems: match_predictions store -> 4 systems (lock/value/risk/gamble), whitelist-only slip.
- Auto-settlement: API-Football Pro, every 15 min, only finished games, quota-safe; settled tips kept
  (won/lost visible under status filter). Verified won/lost render in UI.
- Navigation: 4 (now 5) green quick-view buttons w/ live counts; tab switcher inside tips window;
  per-area notification toggles.

## Session 2026-07-07 (this fork)
### Bug fix — scraper robustness (verified)
- Root cause of intermittent "0 tips": during Playwright scraper runs, an app reload/shutdown could
  hang waiting on the mid-flight scrape task (NOT event-loop blocking — proven: /api/tips stayed at
  0.01s latency during an active scrape). "won cards visible: 0" earlier was a transient reload window.
- Fix: SCRAPE_TIMEOUT=90s hard cap via asyncio.wait_for on every scrape (forebet, predictz, time-index);
  background loops tracked in _BG_TASKS and cancelled+awaited in the shutdown handler. Backend now
  restarts cleanly in ~1.4s. Won/Lost tips confirmed rendering in UI.

### NEW Feature — Smart Bets (player props) (verified, 9/9 backend + frontend)
- Computes player props from API-Football /players season stats (shots, shots on target, fouls
  committed/drawn, yellow cards, goals=anytime scorer, GK saves). Poisson-based probability -> Apex
  rating + estimated odds. Markets in German (e.g. "X — Über 0,5 Schüsse aufs Tor (1+)", "Über 1,5
  Paraden", "Torschütze (Anytime)", "Über 0,5 mal gefoult", "sieht eine Karte").
- Only regular starters (lineups>=8) of teams in upcoming WHITELIST match_predictions (next 5 days).
  Team players cached 24h (db.player_stats_cache). smart_autopost caps 14 matches, 4 props/team.
- Stored as source="smart", league "TipJarHQ Smart Bet". smart_loop every 12h. Excluded from
  settle engine (score-based settle can't judge props) and from members/settle queries.
- Frontend: 5th quick-view button (Header, data-testid=view-smart-btn, Brain icon, grid-cols-5),
  tab tabview-smart in tips window, RateWall view="smart" -> source=smart. i18n nav.viewsmart (5 langs).
- DATA LIMITATION (told to user): API-Football does NOT provide offsides, corners, throw-ins,
  free-kicks, headed/long-range goals, corner-by-10th-minute, team-scores-first -> those props omitted.
  Also July = mostly minor leagues -> low candidate volume until top leagues resume.

## Session 2026-07-08 (fork)
### AI Pick dedup + smartest-selection (verified: python unit + curl)
- ROOT CAUSE of "multiple overlapping tips per match": `_forebet_candidates` returned
  several markets per game and `forebet_autopost` posted each. FIX: it now returns exactly
  ONE "smartest" pick per match. Autopost also `delete_many`s any other pending hq-auto tip
  for the same (home,away,match_time) → strict one-pick-per-match. Cleaned 6 legacy dups.
- Selection priority (owner "den smartesten" + "Underdog trifft früh"): 1) UNDERDOG team-to-score
  "<Underdog> Über 0.5 Tore" when there's a clear favourite (pred 1/2) and the underdog is
  predicted to score (e.g. Real–Atlético → Atlético Über 0.5); else 2) best rating×odds
  (torreiches game → "Über 2.5 + Beide treffen"). Goals-picks ranked by rating AND predicted
  Ø goals so torreiche games surface first.
- Settlement verified for new markets via judge_market (8/8 cases: team-to-score, O2.5+BTTS,
  BTTS, DNB all correct won/lost).
- Systems UI: team names in system legs now wrap instead of truncating (Systems.jsx break-words).

### NEW Feature — LIVE engine (built; unit-tested; NOT yet seen E2E — no live games at build time)
- `live_autopost()` + `live_loop()` (every 3 min). Re-offers our pending pre-match hq-auto
  goal-picks (Über 0.5/1.5/2.5, BTTS, O2.5+BTTS, team-to-score) while the match is IN-PLAY and
  the bet has NOT yet landed, at now-higher live odds (source="hq-live", status="live",
  fixture_id, live_minute, live_score). Owner "nachreichen" rule.
- "Be careful" guard `_live_pressure_ok`: only re-offer if real pressure (shots on goal/corners)
  by minute band; dead/flat games (Schweiz–Kolumbien style) skipped, esp. late.
- Deterministic helpers unit-tested: `_live_bet_landed`, `_market_team_side` (unique-token, handles
  Real vs Atlético 'Madrid'), `_live_odd` (scales with minute), `_align_goals` (fixture orientation),
  `_find_live_fixture`. Live tips auto-settle won/lost from final score when match ends.
- Admin trigger: POST /api/admin/live-run. Frontend Live channel already fetches status=live.
- TODO (future): general corner-edge tips ("Team X mehr Ecken" when trailing + many corners) and
  half-based goal markets for ALL live whitelist games (currently only re-offers our own picks to
  stay quota-safe). Verify E2E once live matches are available.

## Deferred by user
- SESSION 2026-07-07 (part 3): Removed Leaderboard entirely. Redesigned Systems into 5
  winning-focused bundles (lock=Sicherheits-Kombi ~1.3x high win-rate, value=Banker-Kombi
  DC favorites, smartvalue=Value-Kombi BTTS/Over, risk=Risk-Kombi DC+BTTS, gamble=Jackpot
  3 likely correct-scores ~35-300x). Ratings capped at 9.0 auto; Predictz posts ONLY when
  Forebet agrees. Double-Chance real odds added. NEW "Earn Credits / Zeig deinen Gewinn":
  upload WON slip → Gemini Vision reads it → auto-award credits IF it matches a real TipJar
  SYSTEM (anti-fraud). Types: played (5+ legs, credits=legs count), posted (20), live (4+
  legs each >1.60, 20). Public Hall of Fame ("Best of", sorted by total odds). Endpoints:
  POST /api/wins/claim, GET /api/wins/hall-of-fame. Win rewards credited to received_credits
  (redeemable). Owner strategy notes in /app/memory/betting_strategy_notes.md (INTERNAL).
- KNOWN: system TITLES/subtitles/labels + win.* + Hall of Fame now localized in ALL 8
  languages via i18n keys (sys.* / win.*). Remaining: the individual bet MARKET strings
  inside system legs (e.g. "Über 0.5 Tore", "Doppelte Chance 1X + Beide treffen") are still
  server-side German — a future backend market-localization pass.


- SESSION 2026-07-07 (part 2): Rating discipline tightened — auto-tip ceiling now 9.0★
  (no 9.5/10 automated); Forebet DNB max 8.5, "Über 1.5" max 8.0, "Über 0.5" the top
  banker (9.0 only when high-scoring predicted). Predictz now ONLY posts when Forebet
  AGREES on the same match (owner distrusts Predictz alone). Real bookmaker odds via
  API-Football /odds now include Double Chance. SYSTEMS REDESIGNED for winning: 5 systems
  = Sicherheits-Kombi (4× Über0.5, ~1.3x, high win rate), Banker-Kombi (5× Doppelte Chance
  favorites, real odds), Value-Kombi (BTTS/Over2.5), Risk-Kombi (DC+BTTS bet-builders),
  Jackpot (3 most-likely correct scores, ~35-300x). Owner strategy notes saved to
  /app/memory/betting_strategy_notes.md (INTERNAL, never shown on site).
- KNOWN: systems bundle titles/subtitles are server-side German only (not localized) —
  future i18n pass.


- PayPal payouts + paid credits monetization: ON HOLD until 1,000 members (features exist, dormant).
- Full legal pages (Impressum/AGB/Datenschutz): BLOCKED on user providing business address data.
- Telegram integration; Stripe payments go-live.

## Backlog / Next (P1)
- Refactor server.py (~2650 lines) into modules: routes/, models/, scrapers/, engines/ (settle, smart).
- Smart Bets: expand markets when top leagues resume; consider team-corner props via /fixtures/statistics
  aggregation; add a probable-lineup source (~40min pre-kickoff) to refine which players start.
- Disable star rating on already-settled tips.
- Web-push (VAPID) for true off-site alerts; My Tips / track-record page.

## Credentials
- Admin: admin@tipjar.com / TipJarAdmin2026!  (login field "email" or "username")
- HQ: hq@tipjar.com / TipJarHQ2026!
- See /app/memory/test_credentials.md
