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
