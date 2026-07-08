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
### Win-claim: branded slip image + 404 fix + market wording + UNDER markets
- FIXED 404 "Bild nicht sichtbar": claim_win uploaded via put_object but never created the
  db.files record the /files/{path} route requires → now inserts it.
- Win claims no longer store the raw bookmaker screenshot. `_render_slip_image()` (PIL,
  FreeSans) renders a standardised TipJar-branded won slip from the extracted data: logo
  (Tip white/Jar green), WON badge, legs GROUPED by match (fixture titled once), German
  market names with "Über/Unter", total odds, @user, winnings. Shown in Hall of Fame.
- Match-key made accent- & language-insensitive (unicodedata fold + de↔en national-team
  aliases) so "Schweiz"=="Switzerland", "Víkingur"→"vikingur". `_system_match_keys` now
  PERSISTENT (all tips + parlay legs), since claims arrive after matches finish.
  WIN_MIN_PLAYED_LEGS 5→3 (TipJar systems can be 3-leg).
- Live claim accepts up to 4 images (multipart `files`); combined into one branded slip.
- extract_win_slip prompt updated: German markets, "Über/Unter", team totals ("Víkingur
  Über 0.5 Tore"), player shots ("Mbappé Über 0.5 Torschüsse"), 1X/X2.
- AI engine (_forebet_candidates): added UNDER markets (Unter 2.5/3.5 Tore) for low-scoring
  predicted games; _market_family knows u25/u35/under. Smart Picks restored (top leagues).
- Frontend: WinClaimModal multi-file live upload + "TipJar Best Wins" button + storage note;
  HallOfFame shows full branded slip (object-contain) with rank badge, no redundant footer.
- NOTE: preview only — user must redeploy to production (tipjarglobal.com).

### Smart Picks RESTORED with top-league-only player markets (owner reversal)
- Owner: keep the Smart Picks feature (tab + notification toggle); only generate player-prop
  markets for TOP leagues that actually offer them (EPL, La Liga, Serie A, Bundesliga, Ligue 1
  +2nd tiers, NED/POR/BEL/TUR/SCO, MLS, Saudi, WC/EC/Euro). EXCLUDE UEFA club qualifiers,
  Brazil, minor South-American/Asian leagues.
- Impl: `smart_autopost` re-enabled + `smart_loop` restarted; new `SMART_LEAGUE_CODES` gate in the
  upcoming filter. Frontend Smart quick-view button (Header.jsx) + tab (App.js) restored (5 nav
  items). NotificationBell smart toggle was never removed. Currently 0 (summer break) — populates
  when top leagues open.

### Value 72% + separate Banker + league whitelist on AI picks (verified: unit + real scrape + screenshot)
- Owner refined: min win-prob 72% for VALUE (odds ≥1.60), PLUS a separate safe BANKER
  category (winprob ≥0.85, low odds, for combos). Forebet picks one per match: prefer a
  VALUE pick, else the safest BANKER. Tips carry `pick_type` (value|banker) + `win_prob`.
- AI picks (Forebet + Predictz) now restricted to the recognised-league WHITELIST
  (FOREBET_SLIP_CODES / SLIP_LEAGUE_KEYWORDS) + women/youth blocked → removed Somalia (so1),
  Kyrgyzstan, Bolivia, Canada, Australia NPL, China L2 (cn3 blacklisted). Kept UCL/UEL/ECL
  qualifiers etc.
- Frontend: VALUE (volt) / BANKER (cyan) badge + "≈NN%" on each AI-pick card (RateWall.jsx),
  data-testid pick-type-{type}. Verified via screenshot.
- NOTE: July off-season → only European qualifiers whitelisted are live, so volume is low
  (4 bankers, 0 value right now). Value picks appear when book prices ≥1.60 at ≥72%.


### VALUE-ONLY rule (owner) — verified (unit + real Forebet scrape)
- Owner: stop 50/50 bets; only give ~80% win chance AT odds ≥ 1.60 (genuine value);
  auto-disable market families that lose too often (self-learning).
- Impl: `_forebet_candidates` now returns ALL options each with `winprob`; forebet_autopost
  applies REAL bookmaker odds (ensure_match_odds/_real_odd_for) and keeps only
  winprob≥0.78 AND odd≥1.60, one per match, ordered by winprob. `_banned_market_families()`
  disables any family with settled win-rate<0.55 over ≥8 samples. Constants VALUE_MIN_ODDS,
  WIN_PROB_MIN, MARKET_MIN_SAMPLE/WINRATE. Same odds/coin-flip gate added to Predictz.
- Coin-flip families (BTTS/Über2.5/O2.5+BTTS/correct-score) never posted; plain Über 0.5
  (1.08) filtered by 1.60 rule; prime value = Über 1.5 in high-scoring games + DC/DNB on
  solid favourites when book prices ≥1.60. Women/youth now blocked from AI picks too.
- TRADE-OFF (owner accepted): volume drops hard (~1 pick / 42 scanned). Relax WIN_PROB_MIN→0.72
  for more volume. Cleared 37 legacy non-value pending picks.


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

## Changelog — 2026-06 (Best-Wins & Community-Gifting)
- Hall-of-Fame-Button umbenannt: "Credits verdienen" → "Zeig, was du mit TipJar gewonnen hast" (i18n key `win.showWin`, alle 8 Sprachen). Der Hero-Button oben bleibt "Credits verdienen".
- Klickbare Usernames: In den Tip-Cards (Rate Wall) und in der Hall of Fame sind Benutzernamen jetzt anklickbar. Klick öffnet das Wallet-Modal auf dem "Gift"-Tab mit vorausgefülltem Empfänger (nutzt bestehendes POST /api/credits/gift). Ohne Login öffnet sich das Login-Modal. Self-Gift wird geblockt.
- Best-Wins Vollansicht: Klick auf ein gewonnenes Slip-Bild öffnet einen Vollbild-Viewer (Lightbox) mit dem Username des Besitzers unten links (ebenfalls klickbar zum Verschenken). Kein Zoom, nur Vollansicht.
- Frühere Slip-Bild-Verbesserungen (Titel/Liga/Datum/Uhrzeit) + KI-Märkte (Doppelte Chance 12, Unter 2.5/3.5 mit echten Quoten) bereits in diesem Zyklus umgesetzt.
- Getestet: testing_agent iteration_27.json — 3/3 Flows bestanden, keine Fehler.

## Changelog — 2026-07-08 (Handicaps, Dedup, Blacklist, Button-Farben)
- KI-Tipps nutzen jetzt HANDICAPS: Außenseiter +3.5/+2.5/+1.5 (sicher, schlägt "Unter X.5"), Favorit -1.5 (Value). Korrekte Schreibweise "<Team> Handicap +X.5" auch beim Auslesen hochgeladener Scheine (Vision). Verifiziert: Kairat–Sutjeska → "Sutjeska Niksic Handicap +3.5".
- DEDUP: _dedupe_hq_tips() erzwingt EIN Pick pro Spiel (forebet+predictz), löscht risikoärmste Duplikate. Verifiziert: 8 einzigartige Spiele.
- BLACKLIST: TEAM_LEAGUE_BLACKLIST = golden, mogadishu, kahibah (in beiden Autopostern + Systemen).
- Doppelte Chance 12 + Unter 2.5/3.5 mit echten Quoten.
- UI: Header/Tab-Button "Member Picks" = GOLD, "Live" = blinkend BLAU.

## Changelog — 2026-07-08 (Profil, größere Slip-Schrift, Einzelquoten, Telegram-Teilen)
- (1) Klick auf @Username (Tip-Cards + HOF-Viewer) öffnet öffentliches PROFIL-Modal (Avatar, "Mitglied seit", Stats Tips/Gewinne/Erhalten, Button "Credits verschenken" → Gift-Flow). Neuer Endpoint GET /api/users/public/{username}.
- (2) Slip-Bild (Hall of Fame) mit deutlich größerer Schrift; Renderer unterstützt "pending"-Modus (OFFEN, Community-Tipp).
- (3) Einzelquoten je Leg: Vision extrahiert sel_odds; Anzeige als @-Chip. Auto-Backfill (background task) füllt Einzelquoten bei bestehenden Member-Parlays per gespeichertem Bild nach.
- (4/5) "Teilen"-Button nur bei PENDING Member-Picks → generiert TipJar-Slip-Bild (POST /api/tips/{id}/share-image) und teilt via Web Share/Telegram; Teil-Text enthält https://tipjarglobal.com.
- Getestet: testing_agent iteration_28 — 5/5 Flows bestanden, keine Fehler.

## Changelog — 2026-07-08 (Auto-Live-Erkennung + Live teilbar)
- Eingereichte Member-Tipps landen jetzt AUTOMATISCH im Live-Kanal (status="live"), wenn das Spiel gerade läuft: Anstoß liegt max. ~150 Min zurück (bzw. ein Parlay-Leg). Neu: _kickoff_dt (inkl. ISO-Format) + _looks_live_now in server.py, angewandt in POST /api/tips. Verifiziert per E2E-curl (live/pending/abgelaufen korrekt).
- Teilen-Button (RateWall) jetzt auch für LIVE Member-Tipps (vorher nur pending): isShareable = status in [pending,live] & source nicht hq-auto/smart. share-image funktioniert für Live-Tipps (verifiziert).

## Changelog — 2026-07-08 (SEO-Fixes nach Audit)
- robots.txt (echte Textdatei, Allow + Sitemap-Verweis), sitemap.xml, llms.txt (korrektes Format) in /app/frontend/public/ angelegt.
- index.html: Open-Graph-/Twitter-Meta-Tags, Canonical-URL, sichtbarer #seo-fallback-Textblock (H1/H2/Listen) für Crawler → verbessert Text/HTML-Verhältnis. React ersetzt den Fallback beim Mount (verifiziert).
- Nicht behebbar: emergent-main.js unminified + blockierte externe Fonts (Plattform-Ressourcen). Muss neu deployt werden.

## Changelog — 2026-07-08 (Splash Snake-Border verifiziert)
- Splash Screen: statischer mint/grüner Rand aus allen 8 Lokal-PNGs entfernt (bestätigt: splash-de.png sauber). SVG-„Snake"-Rahmen (Volt #E1FF00, 2,5s, im Uhrzeigersinn, non-scaling-stroke, glow) läuft über den Viewport. Visuell per Screenshot verifiziert.

## Changelog — 2026-07-08 (Apex-Flamme + Slip-Korrektur)
- NEU "Apex-Flamme" 🔥: Bewertungsserie-Kachel ist anklickbar → Sprechblase mit Fortschritt zur 30-Tage-Serie. Bei 30 Tagen wird der kosmetische Orden vergeben (erscheint auf eigenem + öffentlichem Profil), und die Serie-Kachel verschwindet von der Startseite. Backend: _maybe_award_apex_flame (Schwelle APEX_FLAME_STREAK=30), rate-Response liefert apex_flame/apex_flame_new; public profile + user-Objekt tragen apex_flame. Rein optisch.
- Seed 'seed-community-pending' auf den ECHTEN BetScore-Schein korrigiert: 7 Legs (Sutjeska Hcp +3.5, mehrere Über 1.5, Connah's Quay Hcp +2.5, Unter 3.5), Gesamtquote 4.15, Einsatz 12 €, möglicher Gewinn 49,81 €.
- Getestet: testing_agent iteration_29 — alle Flows bestanden, 0 Konsolenfehler.
