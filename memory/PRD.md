# TipJar Global — PRD

## Problem statement
Sports-betting tips community platform (React + FastAPI + MongoDB PWA on Kubernetes).
Features: AI slip parsing, automated tips scraped from Forebet/Predictz/Statarea/
footballpredictions, multi-leg Bet-Builders, live odds, Hall of Fame, strict
auto-settlement into unified "Abgerechnet" (Settled) tab, anonymous cloned-tipster bots.

## Language
User is GREEK. Communicate ONLY in Greek.

## Behavioral rules (hard constraints)
- DO NOT propose unsolicited features/improvements ("Μην προτείνεις νέες προσθηκες").
- Betting logic: NO exact scores. REMOVE logically redundant legs (e.g. -1.5 HC + BTTS ⇒ omit Over 2.5/3.5).
- Risk-averse philosophy: avoid 0:0 leagues, "Value Bankers" combos, custom Asian-line logic.
- One UNIQUE in-house bot per scraped tipster channel — never mix personas.
- API-Football quotas are tight → always use caching (match_stats.py), never live-hit loops.

## Architecture
```
/app/backend/
  core.py, server.py (main endpoints), scrapers_autopost.py, settlement.py,
  background_tasks.py, match_stats.py, betting_logic.py, emptips_watch.py, ticket_render.py
/app/frontend/src/  App.js, components/
```

## Integrations
Emergent Auth & Storage, API-Football (user key, rate-limited), Gemini 3.1 Pro / Claude 4.6
(Emergent LLM key, Vision OCR), pywebpush.

## DB schema (key)
- tips: {id, status, combo_legs, legs, source, username, user_id, is_expert, ...}
- team_cache, emptips_seen, users (role=expert, is_bot for personas)

## Implemented (latest)
- 2026-06: **footballinsight01 ("Magic Betting Tips") scraper** — feeds the TipJarHQ
  `hq-auto` pool (NOT an expert bot, per owner). `footballinsight_autopost()` +
  `footballinsight_loop()` (every 2h). Parses structured Telegram text picks
  (teams · market · league · kickoff), maps goal/win markets to German labels, REJECTS
  corners/cards/odd goal-lines, dedups per match+market, future-kickoff only. Posts as
  TipJarHQ (source hq-auto, no expert badge). Tested (8 posted, corners rejected).
- 2026-06: **Expert auto-expiry** — real experts (NOT in-house bots) lose the title after
  `EXPERT_INACTIVITY_DAYS`=7 days without a new tip. `expire_inactive_experts()` +
  `expert_expiry_loop()` (every 6h). Demote → role=user, `expert_expired_at`, and a mailbox
  letter (`type=expert_expired`, `cta=expert_invite`) → 2-click reactivation via existing
  `/inbox/expert-accept`. Bots (is_bot) exempt. Tested (inactive demoted+mailed, recent kept,
  bot exempt).
- 2026-06: Added **Chris bets (t.me/Chrisbetsbets)** → new unique bot **Sirius**. Added new
  **"Our Experts" showcase** section prominently at top of home page (`ExpertsShowcase.jsx`,
  fetches `/experts`, clickable → profile). Moved **Statistics quick-nav to LAST** in BOTH
  header pills (Header.jsx) and overlay nav (App.js). Bot map now:
  EMPTips→Orion, LEVY→Vega, thesuperbets→Nova, Chrisbetsbets→Sirius.
- 2026-06: Added **Super bets (t.me/thesuperbets)** → new unique bot **Nova**. Made
  watch lists CODE-driven (`_CODE_TG_CHANNELS`/`_CODE_X_HANDLES`, env additive & deduped)
  so cloning works in production without env changes. Baselined existing posts.
  Bot map: EMPTips→Orion, LEVY(@LevyKingTips)→Vega, thesuperbets→Nova.
- 2026-06: **"Δώρα" (Gifts)** cross-cutting tab in AI Single-Game Picks — `is_gift` flag on
  hq-auto picks (forebet gift bucket rescues generous singles; predictz + combos flagged;
  odds≥2.00/2.20 + winprob≥0.55). Endpoint `/api/tips?category=gifts` → `is_gift:True`.
  Gold 🎁 chip on single & parlay cards. **VOID/Annulliert** settle button (push/refund).
  **Removed big top red LIVE bar**; discreet per-game LIVE badge on the right instead.
  Tested (backend 100%, frontend 95%; parlay chip gap fixed).
- 2026-06: **Statistics "Γκολ ημιχρόνου" tab** — `/api/ht-goal-forecast` (quota-free from
  stored predictions; total≥3 or over2.5&≥2.5 → confidence). New `HtGoals.jsx`.
  Moved **Statistics (scorers) quick-nav to LAST (after Settled)**.

- 2026-06: Generic **"Experten" notification area** for cloned tipster bots (Orion/Vega).
  Expert-bot posts route to area `experts` (backend `_tip_push_area` + frontend `tipArea`
  check `is_expert`). New generic "Expert Picks" checkbox (orange dot) in NotificationBell
  — NO per-bot boxes. Foreground alerts bypass the star threshold; background Web Push
  fires with title "🔮 Experten-Tipp · <bot>" and its own `tipjar-expert` tag. i18n added
  in all 8 languages. Verified: backend routing (python) + frontend smoke screenshot.
- 2026-06: Added LEVY (@LevyKingTips) as new tipster → own unique bot **Vega**
  (`vega@tipjar.com`). Its private Telegram invite link is unscrapeable, so we read its
  public X profile via Nitter. Generalized to multi X-handle watching via `WATCH_X_HANDLES`
  env (each handle routed to its channel bot). Verified routing + /api/tips 200.
- 2026-06: Multi-bot per-channel architecture. `_CHANNEL_BOTS` map (channel→{email,name,bio}),
  `_bot_for_channel()`, generic `_get_expert_bot(bot_cfg)` and `_ingest_emptips(..., bot_cfg)`.
  Each source channel posts under its own unique expert bot (tip id/source use bot slug).
  EMPTips (Telegram `EMPTipsTele` + X `EmpTips`) → Orion. New channels add a new unique bot.
  Verified via backend routing test + /api/tips 200.
- Prior: server.py modularization, footballpredictions scraper, betting_logic dedupe engine,
  match_stats caching engine, emptips_watch Telegram/Nitter scraper, anonymous Orion bot.

## Backlog
- P1: Add more tipster channels → new unique bot per channel (edit `_CHANNEL_BOTS`).
- P2: Telegram outbound notifications.
- P2: Stripe payments & PayPal payouts.

## Credentials
Admin: admin@tipjar.com | TipJarAdmin2026!
