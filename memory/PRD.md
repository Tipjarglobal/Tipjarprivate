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
- 2026-06 (25th): **Correct names in leg boxes + leagues/countries + live-score unlock**.
  Expert-bot tips (Deneb/Sirius/Nova/Atlas…) are stored fully in Greek incl. a `legs[]` box
  and league/country. Added `_canonical_league_name` (LLM, cached in `label_alias`) and
  `_canonicalize_display(tip)` which rewrites each `leg.match` ("Μάιντζ–Κρόιτσλ." → "Mainz –
  Kreuzlingen"), `leg.league`, and top-level `league`/`country`/`*_latin` to canonical English
  — independent of any API-Football fixture (friendlies work too). Runs at the top of
  `enrich_member_picks` every pass (idempotent, cached); picks query broadened to catch any
  Greek label. Because the live per-leg loop matches by `leg.match`, fixing the names ALSO
  unlocks the **live score + real minute** in the leg box for these mostly-live tips.
  Verified: 0 Greek-labelled pending/live tips remain; all leg matches canonical (Luzern–Thun,
  Girona–Alaves, Kaiserslautern–Sudtirol, …); countries translated (Norway/Spain/Switzerland/Finland).

- 2026-06 (25th): **Correct names EVERYWHERE (settlement + live + consensus)**. Extended the
  canonical-name fix beyond display: `_tip_match_teams` now prefers `*_latin` (so live-score
  matching, master consensus & live-alternatives use real names for Greek-tipped games);
  live_annotate & master_consensus projections include the latin fields. Settlement
  (`settle_pending_tips`, `settle_hq_combos`, `settle_multimatch_parlays`) resolves canonical
  names (from `*_latin` or `_canonical_team_name` fallback) before fixture lookup / datescan /
  judge_market, so Greek-tipped games auto-settle reliably. Verified: `_tip_match_teams`
  returns ('Luzern','Thun') for the ΛΟΥΚΕΡΝΗ tip; all settlement loops run clean.

- 2026-06 (25th): **Team-name fix (Greek → canonical)**. GR/foreign tipster bots stored teams
  in Greek ("ΛΟΥΚΕΡΝΗ"/"ΤΟΥΝ") which `toLatin` turned into phonetic "LOYKERNI"/"TOYN" for
  non-Greek readers. Added `_canonical_team_name()` (server.py): LLM (Gemini) resolves a
  non-Latin team name → the club's canonical English name (cached in `team_alias`).
  `resolve_team_id` now prepends the alias to its API-Football search and ignores stale
  `None` cache hits. `enrich_member_picks` computes canonical home/away for both the
  opponent match AND the live-fixture fallback, and — crucially — writes `home_team_latin`/
  `away_team_latin` (and rewrites parlay leg `match`) from the alias EVEN when no fixture is
  found, so the display name is always correct. Runs automatically in member_live_loop.
  Verified: Luzern/Thun, Girona/Alaves, AZ Alkmaar/Olympiacos, Eldense/Al-Ettifaq all resolved.
- 2026-06 (25th): Master texts — removed "Papa/Μπαμπάς" and "corrections/διορθώσεις" wording;
  now purely "live" / "TipJarMaster" / "διαλογέας".

- 2026-06 (25th): **Master special box + card-name visibility**. Added a distinct RED
  "TipJarMaster" tile (crown, `showcase-master`, spans full width) at the top of the
  ExpertsShowcase alongside the expert "friends"; clicking opens the Master area
  (`onMasterClick` → openTipsView("master")). i18n `master.showcase.sub`. Tip-card header
  now `flex-wrap` with no `truncate`/`min-w-0` on the author so the author name (e.g.
  "by TipJarMaster") is ALWAYS fully visible; badges wrap below when space is tight.
  Consistency: `hq-master` added to expire_stale_pending `ai_src` (settlement.py),
  `_is_member_tip`, enrich_member_picks & _purge_unclarified_slips exclusions so the bot
  is never treated as a member.

- 2026-06 (25th): **TipJarMaster ("der Papa"/Μπαμπάς)** — new red bot, the "father of HQ".
  Backend (server.py): `_get_master_bot` (email master@tipjar.com, is_master=True, role expert
  but EXCLUDED from /experts & _tag_expert). `source="hq-master"`, added to all members/bestwon
  $nin exclusions. `/tips?source=master`; `/tips/counts` now returns `master`.
  • **Phase 2 — live corrections**: `_live_pick_in_danger()` detects a goals/result pick failing
    live (Über X.5 short of goals late, BTTS one-sided late, backing a losing side late).
    `_derate_fields()` strips 'banker'→'risk' + drops stars to 3 + sets `live_danger` (auto-restore
    if the game turns), applied in `live_annotate_sync` for singles AND per-leg (banker_was). Effective
    category derived on read in list_tips (`live_danger ⇒ risk`) to avoid write-path races.
  • `master_live_alternatives()`: for each in-danger HQ single, Papa posts a SAFER in-play pick on the
    same match (`_safer_live_alternative`: Über line down to current total+0.5, or DC 1X/X2 for a losing backed side).
  • **Phase 3+4 — consensus/learning**: `master_consensus()` publishes when ≥5 experts (`MASTER_CONSENSUS_MIN`)
    back the same fixture+market family (`_market_family`), weighted by `_expert_hitrates()` (won/total from settled).
  • `master_loop()` every 120s (registered in startup).
  Frontend: RED 'Master' quick-view button FIRST in Header (variant "master", Crown icon); 'Master' tab
  FIRST in tips window; RateWall view=="master" with 2 sub-tabs (Slips `master-tab-slips` / Live `master-tab-live`);
  RED master card + crown `master-badge` (no Experte badge); red `tip-live-danger`/`leg-live-danger` "Σε κίνδυνο"
  warning badges. i18n: `wall.liveDanger`, `nav.viewmaster`, `master.slips` (all langs / en+el).
  Verified: unit + live-fixture e2e (backend), testing_agent iteration_41 (100% frontend, 5/5 backend).
- 2026-06 (25th): **Flames 🔥 removed from all expert-name displays** (ExpertsShowcase, Header ExpertBanner,
  RateWall member search) and **date-gated** via `flamesActive()` (i18n.js) — hidden now, auto-return **1 Sep 2026**.
  Expert showcase names enlarged (text-lg/xl, bold, no truncate) for readability.

- 2026-06: Added expert **Capella** (The Doc). Then added **Atlas** = Totis Sports WEBSITE
  scraper (totissports.gr, all 5 tipsters → one bot). `totissports_autopost()` +
  `totissports_loop()` (every 6h): fetches each analysis page, `_totissports_extract()`
  pulls matchup+kickoff+Greek estimation, LLM-parses via `_ingest_emptips(bot_cfg=Atlas)`.
  Quality-gated (requires teams+odds), dedup per pick (emptips_seen `tot-*`). 13 experts total.
- 2026-06: Added expert **Antares** (betting with tyga, t.me/bettingwithtyga). 10 experts now:
  Orion, Vega, Nova, Sirius, Rigel, Polaris, Altair, Lyra, Vela, Antares.
- 2026-06: **Hall of Fame overhaul** — deleted all old seeded/showcase win_claims, disabled
  the showcase seeds (`_seed_showcase_wins`, `_seed_hof_showcase_slip`). New `daily_hof_autofill()`
  + `daily_hof_loop()` (once/day): turns the best recent WON tips into branded trophy slips
  (auto-approved win_claims, dedup by `source_tip_id`, odds≥1.5, max 6/day).
- 2026-06: Added experts **Lyra** (Betting Friends @bettingfriendss, X) and **Vela**
  (DGD Football Tips @DGDFreeTips, X). 9 experts total now.
- 2026-06: Added **BET KING.gr** (t.me/betmastersfreee) → new bot **Altair**. 7 experts now:
  Orion(EMPTips), Vega(LEVY-X), Nova(thesuperbets), Sirius(Chrisbetsbets),
  Rigel(grizzlybetslive-X), Polaris(bet_of_the_day_tips_free), Altair(betmastersfreee).
- 2026-06: Added **BET OF THE DAY TIPS FREE** (public Telegram) → new bot **Polaris**
  (image betslips via Vision-AI). Bot map: EMPTips→Orion, LEVY→Vega, thesuperbets→Nova,
  Chrisbetsbets→Sirius, grizzlybetslive(X)→Rigel, bet_of_the_day_tips_free→Polaris.
- 2026-06: Added **Grizzly Bets (@grizzlybetslive, X)** → new unique bot **Rigel** (scraped
  via free Nitter mirrors; their TG is a private invite). Added to `_CODE_X_HANDLES`.
  Bot map now: EMPTips→Orion, LEVY→Vega, thesuperbets→Nova, Chrisbetsbets→Sirius,
  grizzlybetslive→Rigel. (kingRoyalAlex skipped — no public preview / group, not scrapable.)
- 2026-06: **Pre-seed all expert bots on startup** so every expert (Orion/Vega/Nova/Sirius
  + Ragazzi) always shows in the "Our Experts" showcase — not only after first post.
  `_startup_seed` iterates `_CHANNEL_BOTS` → `_get_expert_bot`. Ragazzi + bots marked
  permanent/`is_bot` → exempt from the 7-day expert auto-expiry (no flip-flop).
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
