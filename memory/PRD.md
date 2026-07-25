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
- 2026-06 (25th): **Zeitzonen-Anzeige + sicherere Experten-Void-Logik**.
  • **Zeitzonen**: Anstoßzeiten werden jetzt in der vom Betrachter gewählten Zeitzone angezeigt.
    Basis = Europe/Berlin (Berlin bleibt unverändert), Umrechnung via Intl in i18n.js
    (`getViewerTz`/`setViewerTz`/`applyAccountTz`, `_toViewer` in `formatKickoff`). Header hat einen
    Zeitzonen-Umschalter (`timezone-switcher`, `tz-<IANA>`) neben der Sprache; Default = Account-
    Zeitzone (falls keine manuelle Wahl). Verifiziert: „08:00" → Berlin 08:00, Athen 09:00,
    London 07:00, NY 02:00; Mitternachtswechsel korrekt. (Mobil: Account-Default; Umschalter ab sm.)
  • **Void-Timing marktabhängig** (`_grade_window_min` + `void_stale_expert_slips`): Erste-Halbzeit-
    Märkte (Ergebnis steht zur HZ fest) werden ~1h nach Anstoß bereinigt; Ganzspiel-Märkte ~2,5h;
    Kombis mit Ganzspiel-Bein warten bis Full-Time. Void läuft NACH dem Settle-Pass: Ganzspiel-Scheine
    nur voiden, wenn die Engine sie bereits erfolglos versucht hat (attempts≥1) → gradebare werden
    ABGERECHNET statt annulliert; zeitlose sofort; 12h-Backstop. Loop alle 15 Min. Unit-getestet
    (H1-Einzel→60min, Ganzspiel→150min, H1-in-Kombi→150min).


- 2026-06 (25th): **Schnellere Bereinigung abgelaufener Experten-Scheine**.
  • Problem: Ein „Fortuna Düsseldorf – Dortmund"-Schein (Polaris, exotischer Markt „Next Team to
    Score First Half") blieb ~7h nach Anstoß offen. Ursachen: (1) Feeds posten LOKALE Anstoßzeiten,
    die wir als UTC lesen → Spiel wirkt jünger, 6h-Void griff zu spät; (2) der laufende Prozess
    hatte die Void-Logik noch nicht geladen.
  • Fix: `void_stale_expert_slips` Grenze von 6h → **3h** nach (geparstem) Anstoß gesenkt (deckt den
    Lokalzeit-Versatz + Spieldauer ab; Settle läuft davor, also werden gradebare Scheine zuerst
    abgerechnet). Backend neu gestartet → Loop führt Void alle 15 Min aus. Sofort-Bereinigung
    ausgeführt: 12 abgelaufene Experten-Scheine annulliert (inkl. der gemeldeten Polaris-Scheine).
    Kombi mit einem noch offenen Bein (morgen) bleibt korrekt bestehen.


- 2026-06 (25th): **Team-Total-Quoten aus dem API-Football-Feed**.
  • `_parse_odds` liest jetzt auch Team-Totals (Heim/Gast über/unter X.5) aus dem /odds-Feed —
    robust gegen Namensvarianten ("Total - Home", "Home Team Total", …) → Keys home_over05/15/25,
    away_over05/15/25 etc.
  • `_real_odd_for` mappt deutsche Team-Total-Märkte ("Heim über 1.5 Tore", "{Team} über 0.5 Tore")
    via neuem `_side_in_market` (Heim/Gast-Keywords ODER signifikantes Team-Namenswort) auf die
    echten Team-Total-Quoten — GEPRÜFT vor der Match-Total-Linie, damit team-spezifische Märkte nie
    fälschlich auf die Gesamt-Tor-Linie gemappt werden.
  • `_enrich_legs_real_odds`: Übersprung-Regel für Team-Über/Unter entfernt → auch diese Beine
    bekommen echte Quoten; Fallback = plausibilitätsgefilterte Pool-Quote, wenn der Feed keinen
    Preis hat. Unit-getestet mit simulierter API-Antwort (Heim/Gast/Team-Name-Mapping korrekt).


- 2026-06 (25th): **Echte Master-Quoten + Übersetzung der Statistik-Tabs**.
  • **Real bookmaker odds für Master-Packs**: `_enrich_legs_real_odds` ersetzt Pool-Quoten der
    GEWÄHLTEN Beine durch echte API-Football-Quoten (bestehendes `ensure_match_odds` /
    `_real_odd_for`, 6h-Cache in `odds_cache`) — nur die gewählten Beine, um das Kontingent zu
    schonen. Team-spezifische Über/Unter-Märkte werden übersprungen (nicht einzeln gepreist →
    keine Fehlzuordnung zur Match-Total-Linie); Fallback = plausibilitätsgefilterte Pool-Quote,
    wenn keine echte Quote/kein Kontingent. Eingebunden in `master_build_packs` & `master_challenge`.
  • **Übersetzungs-Cache auf Statistik-Tabs erweitert**: `useProseTranslations` jetzt auch in
    ScorerRadar (`s.reason`, `m.note`, `m.zero_zero_label`) und HtGoals (`r.market`). Verifiziert in
    Greek (z.B. „Να σκοράρουν και οι δύο ομάδες", „ΤΟ 0:0 ΠΡΑΚΤΙΚΑ ΑΠΟΚΛΕΙΕΤΑΙ") und EN. GoalThirst
    war bereits vollständig über i18n-Keys abgedeckt. Getestet: testing_agent iteration_43 (alle
    Übersetzungen el/de/en/fr + Stats/Master-Integration bestehen, keine Regression).


- 2026-06 (25th): **Mehrsprachige dynamische Texte + Quoten-Plausibilität**.
  • **Dynamic i18n (lazy LLM translation cache)**: frei generierte Prosa (KI-Analysen `ai_analysis`,
    Smart-Berichte report=True, Master-Texte, Qualifier-Briefing `narrative`) wird jetzt in ALLE 8
    Sprachen übersetzt. Backend: `POST /api/i18n/translate` ({lang, texts}) → `_translate_batch`
    übersetzt fehlende Strings per Emergent-LLM (batch, JSON-Rückgabe) und cacht jede (text,lang)
    permanent in `db.translation_cache` (sha1-key). Deutsch = Quellsprache → unverändert. Frontend:
    `src/proseI18n.js` `useProseTranslations(texts, lang)` Hook (mem + localStorage `tj_tr_<lang>`
    Cache), verdrahtet in TipCard (`ai_analysis`, Fallback localizeProse während Laden) und
    QualifierBriefing (`narrative`). Erster Aufruf eines Strings/Sprache = 1 LLM-Call, danach sofort.
    Verifiziert e2e: el/fr/ar Übersetzungen im Browser + curl; Cache-Hit ~0.2s; de → {}.
  • **Master-Quoten-Plausibilität**: `_plausible_odds(market, odds)` verwirft unrealistisch niedrige
    Quellquoten (z.B. „Heim über 1.5 Tore @1.12" — Team-2+-Tore ist realistisch ~1.5+), angewandt
    in `_master_leg_candidates`. Challenge-Quotenband auf 1.20–1.60 erweitert. Aktuellen
    Challenge-Schein auf reale Buchmacher-Quoten korrigiert (1.55 & 1.30 → 2.02). Master-Labels
    lokalisiert (i18n `master.cat.*`: Easy/Medium/Challenge · el Εύκολα/Μέτρια/Πρόκληση).
    HINWEIS: noch keine echte Live-Odds-Quelle angebunden (API-Football-Odds wäre nächster Schritt);
    aktuell Plausibilitätsfilter statt echter Quoten.


- 2026-06 (25th): **Master sub-categories + expert cleanup**.
  • **Expert cleanup (owner "cleanup the expert mess")**: `_expert_playable_time()` (server.py)
    gates `_ingest_emptips` — an expert slip is now REJECTED at ingest unless it carries a
    recognized, still-playable match/kickoff time (present AND, if fully datable, not >3h past).
    New `void_stale_expert_slips()` (settlement.py, called each settlement cycle AFTER the settle
    pass) auto-voids expert slips that are unsettled >6h after their (last) kickoff OR have NO
    recognizable time at all. Migration voided 58 stale/timeless expert slips (64→6).
  • **TipJarMaster packs**: three sub-categories published by the Master (`master_loop`):
    - **Einfach** (Εύκολα): 2–4 games, target odds ~3.0, ≤2/day.
    - **Mittel** (Μέτρια): 3–5 games, target odds ~6–8, ≤2/day.
    - **Challenge** (Πρόκληση): ONE active pick at a time, start 10 €, rolls the FULL win over
      4 steps; 2 safe low-odds picks per step (~1.2–1.6 each). Loss → reset to step 1.
      State in `db.master_challenge` (id="state": step/stake/status/current_tip_id).
    Backend: `_master_leg_candidates` (pregame pool from experts weighted by hit-rate + hq-auto,
    one leg per fixture), `_assemble_parlay` (greedy to ~target*0.85), `_pack_legs`,
    `master_build_packs`, `master_challenge`. Packs stored as source=hq-master, is_parlay=True,
    `master_category` in {einfach,mittel,challenge}, `master_day`, `challenge_step` — auto-settled
    by `settle_multimatch_parlays` (leg-by-leg). Stale/unsettleable master packs are DELETED by
    `expire_stale_pending` (hq-master ∈ ai_src); challenge auto-reopens if its tip is gone.
    `/api/tips?source=master&mcat=<einfach|mittel|challenge|slips>` filters (slips = no category).
    Frontend RateWall.jsx: 5 master sub-tabs (`master-tab-slips/einfach/mittel/challenge/live`),
    localized labels (i18n `master.cat.einfach/mittel/challenge` → Easy/Medium/Challenge · el:
    Εύκολα/Μέτρια/Πρόκληση), card badge `master-cat-*` with challenge step. Odds on a posted
    challenge slip are correctable (owner supplies real bookmaker odds when they differ from pool).
    Verified: backend unit runs (pack/challenge open→win→advance→loss→reset), testing_agent
    iteration_42 (sub-tabs + mcat filtering pass), Greek UI screenshot.


- 2026-06 (25th): **Capella → silent scraper**. Capella flooded the feed. Now marked a
  "silent scraper": bot cfg `silent:True` (docbettingg), user `silent:True`, and every Capella
  pick gets `hidden:True` at ingest. All public surfaces exclude `hidden` (list_tips base query,
  /tips/counts members/live/settled/won/lost/bestwon/won_normal, /experts excludes `silent`
  users, daily_hof_autofill). Because Capella tips keep `is_expert:True`, `master_consensus` &
  `_expert_hitrates` STILL use them in the background — so the Master keeps learning from Capella
  while she never posts publicly or notifies. Migration set 32 existing Capella tips hidden.
  Verified: Capella absent from /experts & all feeds (0 visible), Master pool still sees 32 picks.

- 2026-06 (25th): **Notification-toast flood fix**. In-app sonner toasts fired one-per-pick in
  waves and were hard to clear. NotificationBell now (a) **coalesces** a whole wave of new picks
  per area into ONE summary toast ("4 × Expert Picks — …"), (b) shows a floating red
  **"Dismiss all (n)"** button (`clear-toasts-btn`, calls `toast.dismiss()`), tracking a live
  `toastCount`, (c) toasts have a close button + `visibleToasts={3}`, shorter durations.
  Verified e2e: 4 seeded picks → 1 bundled toast; clear-all wiped all toasts (0 left).
  i18n `bell.clearToasts`. Also: Master quick-view moved to 4th position (after greens, before
  gold); gold button deepened (#E3A81B).

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
