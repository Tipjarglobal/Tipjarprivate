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

## Backlog / Next
- P0: Real auto-results engine (sofascore / optaplayerstats) to auto-settle Pending->Won/Lost
      (currently admin settles manually; live scraping/sports-data API deferred).
- P1: PayPal payout execution for redemptions (currently records a redemption request).
- P1: Disable star rating on already-settled tips; optionally block rating own tip.
- P1: Push notifications (web-push/VAPID) for true off-site tip alerts.
- P2: My Tips / profile track record page; audit log for admin settlements; DB-side pagination.
