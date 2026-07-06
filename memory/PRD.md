# TipJar — Product Requirements & Progress

## Problem Statement (verbatim intent)
Global community platform "TipJar" where people worldwide post football/sports betting tips.
AI auto-rates each tip; other users rate them on a Rate Wall (Apex Scale, 1–10 stars, gamified).
Fancy-but-clean landing with a signature ANIMATED JAR (floating coins) + a top ALARM BELL that
enables tip notifications with NO signup. Submit flow = built-in tutorial (Argentina vs Cape Verde,
a bad tip, a banker pregame, a live lock) OR direct screenshot upload; AI auto-detects teams, time,
country, league and auto-rates. Credits economy: signup (choose timezone+language), buy credits
(Stripe), gift credits (platform keeps 10%), redeem at 10,000 received credits for real money (PayPal).
Users change username freely. 3 languages: English, German (umlauts ö ä ü), Greek.
Auto results engine (sofascore.com + optaplayerstats.statsperform.com) to flip Pending->Won/Lost.

## Tech Stack
FastAPI + MongoDB (motor) + React (CRA/craco) + Tailwind. framer-motion, canvas-confetti, lucide-react.
AI: Gemini 3.1 Pro via emergentintegrations (EMERGENT_LLM_KEY). Payments: Stripe (test key).
Object storage: Emergent object store for slip screenshots. Auth: JWT Bearer (localStorage).

## Personas
- Tipster: posts tips, builds a track record, earns credits/gifts, redeems for cash.
- Rater: browses Rate Wall, scores pending tips, builds daily streak.
- Anonymous visitor: enables the bell for tip alerts without signing up.
- Admin: settles tips Won/Lost.

## Implemented (2026-07-06)
- Auth: register/login/me/profile (JWT). 100 welcome credits. Username changeable anytime + uniqueness.
- Landing: animated glass jar w/ floating coins, hero, long story section, footer.
- Notification bell: no-signup subscribe/unsubscribe, subscriber count, browser Notification + polling.
- Submit modal: Tutorial (4 examples) + Upload (drag/drop) + AI scan (Gemini) + publish to Rate Wall.
- AI auto-detect + auto-rating (teams/time/country/league/market/odds + 1–10 rating + analysis). WORKING.
- Rate Wall: filters (fresh/hype/top + pending/won/lost), 10-star Apex Scale, confetti, streak widget.
- Leaderboard: aggregated top tipsters (tips, won, win%).
- Credits: buy (Stripe checkout + polling + webhook idempotency), gift (10% fee), redeem (10k threshold).
- i18n EN/DE/EL full UI translation incl. German umlauts.
- Admin settle Won/Lost.
- Verified by testing agent: backend 28/28, frontend 7/7 critical flows.

## Implemented (2026-07-06, iteration 2)
- Auto-results engine: API-Football + AI market judging + 15-min background job + admin "Sync now".
  Idle until API_FOOTBALL_KEY set. Settled tips store final_home/final_away/settled_by/settled_at.
- Referral rewards: each user has a stable referral_code; invite link `?ref=CODE`. Referrer earns
  100 credits ONLY after the invitee signs up AND verifies email. referral_rewarded guards double-pay.
- Email verification via Resend (send_verification_email). DEV mode (no key) returns verify_link in
  register/resend responses. /verify page + verify-email banner + resend button.
- EUR economics: buy 1000/€10, 5000/€50, 10000/€100 (€0.01/credit); withdraw 10,000 earned => €50
  (€5/1000, half price); must EARN 10,000 received credits to withdraw. Stripe currency=eur.
- "Road to 1,000 members" centered Invite section with copy-link + WhatsApp/Telegram/X share. GET /api/stats.
- Verified: backend 38/38 pytest, all frontend flows; fixed 6 missing i18n keys (en/el).

## Deployment readiness fixes (2026-07-06, iteration 3)
- Fixed compilation blocker: missing `toast` import in App.js (VerifyBanner resend).
- DB query optimization: /tips sorts+limits at DB level (cap 100), /tips/mine limit 100,
  /credits/transactions limit 50. Added compound indexes (tips: user_id/created_at,
  status/created_at, avg_rating/ratings_count, ai_rating; credit_transactions: from_user/to_user + created_at).
- Verified: backend 47/47 pytest, frontend toast-fix regression (zero ReferenceError).
- deployment_agent status: PASS. App is deployment-ready.
- NOTE: App now live in production at https://tipjarglobal.com. Redeploy needed to push these fixes to prod.

## Tip moderation (2026-07-06, iteration 4)
- Demo/test tips prohibited: purge_demo_tips() deletes all tips (+ratings) from test-bot accounts
  (email domain @t.com) on every backend startup. Only legit tips remain (e.g. TipJarHQ).
- Trusted 1-star purge: a stars==1 rating instantly DELETES a tip, but ONLY from a trusted rater
  = admin OR "highly-rated" tipster (own tips avg_rating >= 7.0 across >= 3 rated tips).
  Non-trusted users' 1-star is recorded normally (no delete). Constants TRUSTED_MIN_TIPS=3,
  TRUSTED_REPUTATION=7.0 in server.py. Frontend removes card + toast wall.removed (EN/DE/EL).
- Verified: backend 51/51 pytest; frontend admin 1-star delete + non-trusted preserve confirmed.

## Submit rules & moderation (2026-07-06, iteration 5-6)
- Large screenshots: client-side auto-compression in SubmitTipModal (max 1600px, JPEG 0.85)
  before upload → no more proxy 413 errors. Input accepts image/*.
- Winnings rule: potential_return = stake x odds, taxes/fees IGNORED (AI_SYSTEM prompt + verified).
- Reject tips without a match date+time: create_tip returns 400 if match_time empty.
- Bugfix: analyze_tip() now returns stake/potential_return/legs/is_parlay (were dropped) — parlays
  keep their legs, winnings flow through.
- Demo-tip policy extended: TipJarAdmin-authored demo tips removed; @t.com test accounts' tips
  auto-purged on startup; trusted 1-star purge (admin + highly-rated) still active.
- Verified: iteration-5 (upload) 3/3, iteration-6 (rules) 9/9 backend + 2/2 frontend. AI is LIVE.

## Showcase seed & header polish (2026-07-06, iteration 7-8)
- Header: removed the small crest icon (top-left); only "TipJar" wordmark remains, row sits further left.
- Data-vs-code: clarified deploy ships CODE not DB data (preview & prod have separate DBs).
- seed_showcase() (startup, idempotent): creates TipJarHQ account (hq@tipjar.com) + 2 showcase tips
  with FIXED ids (seed-portugal-messi w/ image, seed-hacken-parlay). Now appear in ANY env after deploy.
  Seed image bundled at backend/seed_assets/portugal_messi.jpg.
- Verified: iteration-7 header 100%, iteration-8 seed 9/9 backend (no duplicates, login works, image 200).

## Rate Wall polish (2026-07-06, iteration 9)
- Country FLAGS now render on every tip card (data-testid='tip-flags'), derived from
  country/team/league via NATION_FLAGS/LEAGUE_FLAGS maps in RateWall.jsx.
- Single (non-parlay) tips now show the Einsatz/Gewinn row (previously only parlays did) —
  so winnings (stake x odds) are always visible.
- Removed the Häcken 4-leg parlay showcase (seed block deleted + startup delete_many by id,
  so it's gone in every env after deploy). Only seed-portugal-messi remains.
- Verified: iteration-9 backend 8/8, frontend 5/5.

## Showcase restored (2026-07-06, iteration 10)
- Tax row pixel-erased from Messi slip image (only that row); analysis & Gewinn 875 € kept.
- Häcken 4-leg parlay showcase RE-ADDED to seed (user changed mind); startup delete_many removed.
- Both showcase tips now seed idempotently: seed-portugal-messi (image, no tax) + seed-hacken-parlay.

## Winnings recalculation rule (2026-07-06, iteration 10b)
- Added compute_return(stake, odds): winnings = stake x odds, taxes NEVER applied. Robust
  locale-aware number parsing (_parse_num) + German € formatting (_fmt_eur). Added `import re`.
- Applied server-side in create_tip (overrides any tax-adjusted value on publish) and in
  analyze_tip preview. Häcken seed recalced to 131,48 € (53,23 x 2.47).
- Rule "accept bet only with date+time" already enforced (create_tip 400 if match_time empty).
- Verified via curl: input "66,20 € (after tax)" with stake 20 x odds 3.5 -> stored "70,00 €".

## Tax removal made bulletproof (2026-07-06, iteration 10c)
- seed_showcase() is now AUTHORITATIVE: it re-uploads the tax-free image and force-updates
  (upsert $set) both showcase tips' content/image_path on every startup — so redeploy fixes
  production even though the tip already exists. Image uses a NEW versioned path
  (seed-portugal-messi-notax.jpg) to bust any CDN/browser cache.
- Confirmed served image no longer contains the 'Tax 5,3%' row (byte-verified + visual).

## Deferred by user
- PayPal payouts + paid credits monetization: ON HOLD until 1,000 members (features exist, dormant).

## Backlog / Next
- Set RESEND_API_KEY (+ verified sender domain) to send real verification emails (currently DEV link).
- Set API_FOOTBALL_KEY to activate live auto-settlement.
- Redeem two-phase (requested->paid/rejected) restoring balance on rejection.
- Debounce/rate-limit resend-verification; whitelist origin_url on checkout/verify.
- P1: PayPal payout execution; disable star-rating on already-settled tips.
- P1: Disable star rating on already-settled tips; optionally block rating own tip.
- P1: Push notifications (web-push/VAPID) for true off-site tip alerts.
- P2: My Tips / profile track record page; audit log for admin settlements; DB-side pagination.
