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
- 2026-06 (25th): **Experten-UI aufgeräumt + Bot-Voting/🔥-Mechanik**.
  • **Experten-Panel entfernt**: Das große „Οι ειδικοί μας"-Showcase (`ExpertsShowcase`, inkl.
    Master-Karte) UND der dünne Experten-Streifen (`ExpertBanner` im Header) sind vollständig
    entfernt. Master bleibt über den Header-Button erreichbar. Ungenutzte Imports/Props bereinigt.
  • **Apex-Box im Profil entfernt**: Die rote/Bell-Box `profile-apex-flame` in `PublicProfileModal`
    ist weg (das 🔥 neben dem Namen bleibt, gated durch flamesActive ab 1.9.).
  • **Experten-Bots voten & verdienen 🔥**: Neuer `expert_vote_loop` → `expert_bot_voting`: jeder
    Experten-Bot bewertet täglich 1–4 zufällige Tipps ANDERER Experten + des Masters (Sterne 3–5,
    in `tip_ratings`, aktualisiert avg/count des Tipps). Ein Vote-Tag = +1 Serie via
    `_bump_rating_streak`; 30-Tage-Serie → `apex_flame`=True (bestehende Logik). Bots werden nun mit
    `apex_flame:False` erstellt (bei Erstellung vergebene Flammen werden im Loop zurückgesetzt →
    echt verdient). Flammen erst ab 1.9.2026 sichtbar; bis dahin sind die 30-Tage-Serien aufgebaut.
  • **Deployment-Check bestanden** (deployment_agent: pass, keine Blocker).


- 2026-06 (25th): **Zeitzonen-Anzeige + sicherere Experten-Void-Logik**.
  • **Zeitzonen**: Anstoßzeiten werden jetzt in der vom Betrachter gewählten Zeitzone angezeigt.
    Basis = Europe/Berlin (Berlin bleibt unverändert), Umrechnung via Intl in i18n.js
    (`getViewerTz`/`setViewerTz`/`applyAccountTz`, `_toViewer` in `formatKickoff`). Header hat einen
    Zeitzonen-Umschalter (`timezone-switcher`, `tz-<IANA>`) neben der Sprache; Default = Account-
    Zeitzone (falls keine manuelle Wahl). Verifiziert: „08:00" → Berlin 08:00, Athen 09:00,
    London 07:00, NY 02:00; Mitternachtswechsel korrekt. (Mobil: Account-Default; Umschalter ab sm.)
  • **Live-Frühabrechnung erweitert** (`live_autopost` Abschnitt 1b): JEDER offene Einzel-Schein
    (Experten, HQ-Auto, Mitglieder) mit Über-Tore- oder BTTS-Markt wird SOFORT als GEWONNEN
    abgerechnet, sobald das Live-Spiel die nötigen Tore erreicht (owner 2026-07: „über 2.5 / beide
    treffen → sofort abrechnen, sobald 3 Tore fallen / beide treffen"). Nutzt `_live_bet_landed` +
    `_align_goals` + `_find_live_fixture` (fixture_id ODER Teamnamen). Nur WIN früh (Verlust wartet
    auf Full-Time). Team-spezifische Über-≥1.5-Linien ausgeschlossen (nicht sicher aus Gesamttoren
    gradebar). Läuft im live_loop (LIVE_POLL_SECONDS). E2E mit gemocktem 2:1/61.: Über 2.5 & BTTS →
    won, Über 3.5 → bleibt offen.
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

## Changelog 2026-07-25 (i) — Playable-only philosophy
- CONFIRMED: no win/result push notifications exist — pushes fire ONLY for new pending/live tips.
  Hardened push_watch_loop: skips pushing pre-match picks whose kickoff already passed (live picks
  always pass). Users only get pinged about tips they can still play.
- Homepage hero: added prominent `hero.playable` badge in all 8 languages — "Only PLAYABLE tips
  here — never win alerts. Just check in and copy the play, always with a controlled stake."
- Owner intent recorded: TipJar = check in & replay playable tips, NOT outcome notifications.
- Re-ran unplayable cleanup across all channels (0 stale remain; hide_unplayable_loop maintains it).

## Changelog 2026-07-25 (h) — Auto-hide unplayable + banker rarity + feed cleanup
- NEW `hide_unplayable_loop` (background_tasks.py, every 10 min): hides any PENDING pick once its
  earliest clock-timed kickoff has passed (>15 min grace). Settlement never filters `hidden`, so
  win/loss grading is unaffected — keeps the OPEN feed clean even while API quota delays settlement.
  Manually cleaned 34 stale past-kickoff pending picks. Registered in server startup.
- Banker rarity: non-banker sub-1.40 picks are DROPPED (not forced into Value) in predictz &
  footballinsight. Hid 30 mislabeled short-odds picks from Value. Value tab now all ≥1.41.
- `_is_banker_safe(market, winprob)` now context-aware: first-half goal / Über 1.5-2.5 qualify as
  banker only when winprob ≥ 0.88 (krass offensive / consensus). Full Über 0.5 / DC / DNB / safe
  unders always banker; Über 3.5+ / BTTS / win / handicap never.

## Changelog 2026-07-25 (g) — Strict bankers + Master push logo
- Owner rule: BANKERS must be near-certain. New `_is_banker_safe(market)` (server.py) — only
  Über 0.5 (incl. "<team> Über 0.5" = team scores 1+, e.g. Sporting), Doppelte Chance, Draw No Bet,
  Unter 3.5/4.5 qualify. NEVER: Über 1.5/2.5/3.5 (die on 0-1/1-0), BTTS, straight win, handicap,
  half-time markets. Applied in scrapers (forebet/predictz/footballinsight) + live category logic.
  Migrated 42 existing pending/live unsafe "banker" singles → value. Remaining bankers = team-scores.
- Master push notifications: dedicated branch in `_push_payload_for_tip` → "👑 Master Doppelpack" /
  "👑 Master-Pick" with a RED crown logo `/frontend/public/push-master.png` (192×192). Master no longer
  mislabeled as Community.

## Changelog 2026-07-25 (f) — Master Doppelpack, notifications & manual
- NEW `master_doublepack()` (server.py): Master actively backs 2 favourites to WIN (real 1X2 odds),
  1 slip, product closest to ~6.0 (band 4–9, per-leg 1.5–3.6). `master_doublepack:True`, no
  master_category → shows in the (renamed) Doppelpack tab. Added to `master_loop`. One open at a time.
- Renamed "slips" tab → Doppelpack per language (en Doppelpack, es Doblete, el Ντιπλό, fr Le Doublé,
  it La Doppietta, ar الثنائية, tr Çifte). Fixed master.showcase.sub "father"→"Master"; master-explain
  now uses translated key (was hardcoded Greek).
- Notifications: added dedicated "master" push area (`_tip_push_area`) + a 👑 Master checkbox at top of
  the bell settings (bell.area.master). Verified in UI.
- Manual banner above AI Single-Game Picks (master.manual.title/body) in all 8 languages — verified.

## Changelog 2026-07-25 (e) — Realistic SGM odds + $ everywhere
- Fixed wildly inflated single-match builder odds. `_correlated_combo_odds(legs)` shrinks ONLY the
  correlated GOAL cluster: shrink 2→0.55, 3→0.40, 4→0.30. Handicap, 1X2/Sieg, Doppelte Chance, Ecken
  & Spieler-Props keep FULL odds (Handicap-1X2 legitimately pays more; multi-match parlays untouched).
  Applied in `_combo_odd`, Favoriten-Smart, Mega. Mental jackpot untouched. Verified: handicap double
  5.0×4.25 stays 21.25.
- Recomputed same-match GOAL builder HoF trophy 8.66→4.06 (bundled-odds legs → shrink on stored total,
  `orig_total_odds` preserved for idempotency); mixed/handicap trophies left at full odds.
- $ enforced in `/wins/mine`, win-claim submit (image + stored) and cash-out receipts.

## Changelog 2026-07-25 (d) — Hall of Fame in $
- HoF now enforces $ everywhere: `hall_of_fame` endpoint reformats stake/winnings via `_money_to_usd`;
  `daily_hof_autofill` runs `_disguise_stakes` on the tip (matches feed); showcase seed uses $.
- Migrated all 12 existing approved win_claims: text €→$ AND re-rendered slip images in $ (verified image).

## Changelog 2026-07-25 (c) — Stake disguise & currency
- New `_disguise_stakes(tip)` (server.py, deterministic per tip id) applied in `_tag_expert`
  (feed), `/tips/mine`, and the share-image render (SHARE_RENDER_VER 3→4 to regen cached imgs).
- Rules: Expert bots → 12x LESS than source stake; unit stakes ('1u','2u') → VARIED $ amount
  (random 12–24 $/unit, stable per tip). TipJarLogic → DOUBLE the posted stake. Everyone else →
  keep amount. ALWAYS "$" (no €/£). Winnings recomputed = stake × odds. Verified: feed shows 0 €.

## Changelog 2026-07-25 (b) — Expert tip timing
- Expert bots (Altair etc.) were posting tips AFTER kickoff (games already over → useless).
  Root cause: `_expert_playable_time` tolerated up to 3h PAST kickoff, and `emptips_loop` ran
  every 20min with only 4 vision-AI picks/run (backlog).
- Fix: `_expert_playable_time` now REJECTS any expert slip whose earliest timed kickoff is already
  past (10-min grace); date-only/unparseable times still allowed. emptips_loop 20min→7min,
  MAX_PER_RUN 4→8. Vision-AI (Emergent key) — no API-Football quota impact. Unit-tested.

## Changelog 2026-07-25
- HoF filter: TipJarHQ & TipJarMaster qualify ONLY with systems/parlays (helper `_is_house_single`
  in server.py; applied in `hall_of_fame` + `daily_hof_autofill`). Removed 48 stale house-single win_claims.
- Scrapers now post near-real-time: forebet/predictz/statarea/footballpredictions/footballinsight/
  totissports loops reduced 2–6h → 30min (Chromium/static scrapers, quota-safe). apifootball_predictions
  kept at 6h (quota-heavy). emptips stays 20min.
- Master naming: never "Papa/Vater" — always "Master". Cleaned existing tip prose + stale el translation cache.
- Root cause of late settlement = API-Football DAILY quota exhausted (confirmed via /status). Added quota
  backoff to live_loop & member_live_loop so the settlement engine keeps budget. Manually settled the
  finished Gimcheon 3-2 Daejeon (Über 3.5 → won).
- RESOLVED TRADEOFF: LIVE_POLL_SECONDS 3min → 6min (user choice) to halve live quota use and
  keep budget for the settlement engine. member_live stays 90s.

## Backlog
- P1: Add more tipster channels → new unique bot per channel (edit `_CHANNEL_BOTS`).
- P2: Telegram outbound notifications.
- P2: Stripe payments & PayPal payouts.

## Changelog — 2026-07-29 (9-point batch, all tested: BE 13/13, FE 4/4)
NOTE: recent user communication is in GERMAN (respond in German).
1. Russia boycott: all Russian football blocked (COUNTRY_BLACKLIST/CODE_BLACKLIST + RUSSIA_KEYWORDS
   in TEAM_LEAGUE_BLACKLIST; removed `ru1` from FOREBET_SLIP_CODES). Startup cleanup hides any open
   Russian fixture (runs on prod after deploy). server.py ~4081.
2. Share caption localized to selected UI language (shareSlip.js `text` param; i18n share.* keys; RateWall
   doShare + HallOfFame use t()).
3. "Δώρα" gift label i18n → cat.gifts / wall.gift per language (Greek Δώρα, DE Geschenk, EN Gift, …).
4. Hall of Fame rules: opens 2026-08-01 (HOF_START), SYSTEMS ONLY (≥2 legs), quote ≥3.00, EXCEPT
   TipJarHQ systems need ≥20.00 (_hof_min_odds). Endpoint + daily_hof_autofill + startup cleanup enforce;
   all pre-Aug/single/low-odds win_claims purged. Currently empty until Aug 1 (by design).
5. AI analysis now translates per selected language — fixed proseI18n cache poisoning (bumped key to
   `tj_tr2_`, no longer persists untranslated German). Uses existing /api/i18n/translate cache.
6. Master Easy/Medium packs now use DISJOINT matches (master_build_packs tracks used_fixkeys across the
   run + existing open packs) so one result can't sink both. Verified disjoint via API.
7. Removed "Auf Buchmacher spielen" (Play on bookmaker): deleted PlaySlipOverlay.jsx + playSlip.js,
   removed buttons/state/imports from RateWall.jsx & Systems.jsx.
8. Sort + quick filter in ALL pick areas: "Neueste"/"Meiste Sterne" toggle + "Top 9–10★" chip
   (RateWall.jsx client-side, data-testid sort-newest/sort-stars/filter-top/tip-controls).
9. Push threshold enforced server-side: PushSubIn/PushPrefsIn carry min_stars; notify_all_push skips
   devices whose min_stars > tip stars (non-live areas; live always passes). Payloads carry `stars`.
- Also: member-guide banner moved from inside Single Picks area to the MAIN page above the area-button
  row (Header.jsx, data-testid member-guide).

## Credentials
Admin: admin@tipjar.com | TipJarAdmin2026!

## Changelog — 2026-07-29 (batch 2, tested: BE 7/7, FE all green — iteration_45)
1. Expert push = GOLDEN crystal-ball logo (public/push-expert.png), dedicated 🔮 branch in
   _push_payload_for_tip + expert digest badge. (background_tasks.py ~186)
2. API-Football daily budget RESERVE: core.py _api_note_headers captures rate-limit headers;
   _api_reserve_locked() protects 50% of daily budget before 15:00 UTC (evening = free).
   live_loop + member_live_loop back off when locked → keeps evening energy for settlement/experts.
3. AI-tip CORRECTION (#4): POST /api/tips/{id}/correct (multipart image). ANY logged-in user.
   Vision reads ONLY selection+odds → updates market/legs + recomputes total odds & potential_return;
   STAKE never changes. Parlays: matches legs by team names, replaces only recognised legs.
   Sets corrected/corrected_by/corrected_at, re-grades cleanly. Frontend: blue "Korrigieren" button
   + hidden file input on every open AI card (data-testid correct-tip-*/correct-input-*), "KORRIGIERT"
   badge. Only house AI sources (hq-auto/hq-live/hq-system/smart/hq-master) are correctable.
4. KICKOFF fix (#5): i18n.js kickoffInfo now normalises ISO-with-timezone (API-Football UTC) to the
   Europe/Berlin wall-clock convention → fixes tips shown 1-2h too early. Naive scraped times unchanged.
5. i18n keys tip.correct/correcting/corrected/correct.hint/correct.ok/correct.err in all 8 languages.
NOTE: "credits" (Emergent LLM) ≠ API-Football quota. Experts come via web-scrapers (no API-Football needed).

## Changelog — 2026-07-29 (batch 3) — 23:00 API-Burner + 00:30 Master Safe Bets
1. **23:00 API-Burner** (`background_tasks.py` `api_burner_loop`, registered in startup): once per
   Berlin day at hour 23, if the API-Football daily budget still has a real surplus
   (remaining > max(500, 25% of limit)), aggressively fetch predictions for the next 48h
   (`apifootball_predictions_autopost(day_offsets=(0,1,2), max_per_run=300)`) to prepopulate the DB
   before the midnight quota reset. State in `db.api_burner_state` (id="burner", day guard).
   `apifootball_predictions_autopost` now takes optional `day_offsets`/`max_per_run`. `_API_DAY`
   exported from core via server.
2. **00:30 Master "Safe Bets"** (`server.py` `master_safe_bets_build`, called from `master_loop`
   when Berlin time is 00:30–00:59, one slip/day guard via master_category="safe"+master_day):
   builds an 8-leg (min 6) parlay from near-certain legs — Win favourites (real 1X2, fav ≤1.65),
   Team über 0.5 Tore (real team-total odds), and Player props >0.5 Fouls/Schüsse/Paraden
   (estimated quasi-safe odds ~1.05–1.30 via existing `_team_best_props`/`_odds_from_prob`; feed has
   no micro-prop prices — owner-approved estimate, choice A). Helper `_fav_side`.
   `/api/tips?source=master&mcat=safe` filter added. Verified e2e: built a real 6-leg slip
   (odds 3.34) from the current thin pool; reaches 8 legs when the pool is fuller.
3. Frontend `RateWall.jsx`: new **"Safe Bets"** master sub-tab (data-testid master-tab-safe) +
   counts + card badge; i18n `master.cat.safe` (en/el "Safe Bets"). Screenshot-verified.
4. **Bug fix**: `push_watch_loop` crashed every run — `_earliest_kickoff` was undefined (missing
   helper from a prior fork). Added `_earliest_kickoff` in background_tasks.py → pushes work again.

## Changelog — 2026-07-29 (batch 4) — Teilen-Fix + KI-Korrektur-Hinweis
1. **Teilen-Bug (Samsung/Android "es passiert nichts")**: root cause = the share-image POST ran
   INSIDE the tap handler, so the long upload expired the user-activation → `navigator.share()`
   silently never opened. Fix (`RateWall.jsx` + `shareSlip.js`): the slip image is now pre-warmed
   into an in-memory `File` on viewport-enter (`warmedFile` ref), and `doShare` calls
   `navigator.share({files:[file]})` with ZERO network await inside the gesture. If the file isn't
   warmed yet, it shares the link immediately (sheet always opens) and warms for next time.
   `shareSlip` accepts an optional pre-fetched `file`. Backend share pipeline verified working
   (share-image 200, file fetchable w/ CORS).
2. **Homepage KI-Korrektur-Hinweis**: new light-blue box directly BELOW the red member-guide box
   (`Header.jsx`, data-testid ai-correction-guide, Info icon, sky styling). Explains the AI can be
   wrong (times/odds/unavailable lines, e.g. no "Über 0.5") → use the blue Correct button on each
   tip + post a bookmaker slip photo. i18n `ai.correct.guide.title/body` in all 8 languages.
   Screenshot-verified on the homepage.

## Changelog — 2026-07-29 (batch 5) — KI-Bewertung: Sicherheit statt Value
1. **AI slip rating philosophy flipped to SAFETY-first** (`server.py` `AI_SYSTEM` prompt): the vision
   model used to rate "quality/value", so ultra-safe low-odds accumulators (legs @1.04/1.03) scored
   only ~4/10 with "little value" wording — contradicting TipJar's safe-playable-tips philosophy.
   New rule: rating = how SAFE / likely-to-win the slip is (NOT payout value). Slips of near-certain
   legs (Over 0.5, low Unders, clear favourites, DC/DNB) MUST score 9-10 even at tiny total odds;
   mid 5-7 for mixed; low 1-4 ONLY for genuinely risky/illogical slips. Analysis must not call low
   odds "poor value". Verified via live LLM call: the reported 3-leg 1.435 slip now rates 9.0
   ("extremely safe … strong play"). NOTE: the specific reported slip lives on PRODUCTION (not in the
   preview DB) so it keeps its old 4★ until re-rated; the fix applies to newly uploaded/rated slips
   after deploy.

## Changelog — 2026-07-29 (batch 6) — Asiatisch Über 1.0 verstehen + Geschenke-Tab
Owner: "Individuel/Ομαδικό Asian over 1" (Team-Total asiatisch Über 1.0) ist ein wertvolles Geschenk (@1.34).
1. **Settlement** (`settlement.py _grade_goal_leg`): new branch for Asian FULL-TIME "Über 1.0"
   (team OR match total) — 2+ goals WIN, exactly 1 goal PUSH/refund (GRADE_VOID), 0 LOSE. Team side
   resolved via named team, Heim/Gast · Team 1/2 indicator, else whole-match total. Never matches
   Über 1.5. Unit-tested (2-0 win, 1-3 push, 0-4 lose, match 2/1/0, 1.5 not caught).
2. **Live early-settle** (`server.py _live_bet_landed`): Asian Über 1.0 wins early once the relevant
   side reaches 2 goals (push/loss resolved at FT).
3. **Vision prompt** (`AI_SYSTEM`): individual/team totals (e.g. "Individuel/Ομαδικό Asian over 1")
   are now PREFIXED with the exact team name (Total 1=home, 2=away) and always keep the word "Asian"
   → reliable settlement side-detection.
4. **Geschenke (Gifts) tab**: Asian-Über-1 picks are flagged `is_gift=True` on member submit
   (`_tip_has_asian_over1`/`_asian_over1_in_text`), and the Gifts tab (`category=gifts`) is now
   CROSS-SOURCE (no longer restricted to hq-auto) so owner-posted near-lock gifts (TipJarLogic) show
   there too. E2E verified via curl (TipJarLogic Asian-Over-1 pick appears under source=ai&category=gifts).
5. Also (batch 5 follow-up): AI slip rating tightened — an all-near-locks slip (every leg ≤~1.40)
   now scores the FULL 10 (verified live: the reported 1.435 slip → 10.0).

## Changelog — 2026-07-29 (batch 7) — Auto "Geschenk des Tages" (Asian Über 1.0)
Owner: post such gifts ONLY when the team has a real chance of 2+ goals; to land ~1.34 the team's
WIN odds must be ~1.50-1.65 (a heavier favourite prices it too low). Market on bookies = "Home/Away
Team Total Goals 3-Way · Over 1.0".
- New `gift_of_the_day()` (`server.py`, wired into `smart_loop`): picks a clear favourite
  (fav_prob ≥ 60) that is PREDICTED to score 2+ (ph/pa ≥ 2), 0:0 excluded, kickoff 2-120h out, and
  whose REAL win odds sit in 1.50-1.85. Posts a single hq-auto pick "{Team} Asian Über 1.0 Tore"
  (is_gift=True, gift_kind=asian_o1, category value, rating 9). Odds estimated from the win price
  (~1.30 at 1.50 win → ~1.42 at 1.85 win; 1.60 win → ~1.33). Max 3/day, dedup per match (id gift-*).
  Auto-settled via the new Asian-Über-1.0 judge (2+ win, exactly 1 push, 0 lose) and shows in the
  cross-source 🎁 Geschenke tab. Pipeline verified (20 core-eligible candidates found; selective by
  design — only fires within the time+win-odds band). Runs clean, no errors.

## Changelog — 2026-07-30 (batch 8) — iPhone "App herunterladen" fix
- Problem: on iPhone the "Download App" button did "nothing" — iOS Safari can't trigger PWA install
  programmatically (no beforeinstallprompt); the old code only showed an easy-to-miss toast.
- Fix (`Header.jsx InstallAppButton`): when no install prompt is available, open a clear
  step-by-step DIALOG (data-testid install-guide-overlay) instead of a toast. iOS path shows 3
  steps with Share + Add-to-Home icons; other browsers show the menu hint. iPadOS (desktop UA +
  touch) is now also detected as iOS. i18n keys `install.guide.title` + `install.ios.step1/2/3` in
  all 8 languages. Screenshot-verified with a spoofed iPhone UA (dialog renders with steps + Close).

## Changelog — 2026-07-30 (batch 9) — K.o.-Duell-Intelligenz (European two-leg ties)
Owner: "be smarter" about European two-legged ties (Kairat–Omonia 1:0/1:0, Lech–Aarhus 4:1) — post
AGGRESSIVE tips into the RISK section.
- New `knockout_tie_autopost()` (`server.py`, wired into `smart_loop`; helper `_first_leg_result`):
  scans European KO competitions (Champions/Europa/Conference League incl. qualifiers), detects the
  RETURN leg via H2H (a reversed meeting 3-30 days earlier), reads the first-leg score, and posts a
  bold same-game multi into category "risk" (source hq-auto, ko_tie=True): first-leg WINNER to win
  the return leg + Über 3.5 (big lead ≥2) or Über 2.5 (tight) + BTTS if both scored first leg.
  Real win odds when available, estimated over/BTTS. Max 4/day, dedup per tie (id ko-*).
- Settlement: `settle_hq_combos` couldn't grade a plain 1X2 "Sieg" leg → added a match-result branch
  to `_grade_goal_leg` ("{team} Sieg"/"gewinnt" via home_winner/away_winner flag + goal fallback).
  Tips carry settlement-ready `combo_legs` (market/odds/kind/team) + display `legs`, plus home_team/
  away_team so the fixture resolves. Win + over + BTTS grading unit-tested.
- Verified end-to-end on the live pool: 4 real return legs detected (Maccabi 5:0→Sieg+Ü3.5 @3.28,
  Beşiktaş, Hradec, Varazdin 3:2→+BTTS @14.71) and rendered in the Risk tab (screenshot).

## Changelog — 2026-07-30 (batch 10) — Master "Special" (4-game bet-builder) + Settled i18n
Owner: learned from 15 winning bet-builder slips. The Master must ALWAYS post a "Special" = a
4-game bet-builder combo. "Special" label stays UNIVERSAL (untranslated); "Settled" must translate.
- New `master_special_build()` + `_special_legs_for()` (`server.py`, wired into `master_loop`,
  one per Berlin day): picks the 4 most goal-friendly upcoming favourites and builds a 4-game combo
  where each game is a 2-selection same-game bet-builder from goal markets (1. HZ Über 0.5, Über
  1.5/2.5, Beide treffen), rotated for variety. source hq-master, master_category="special", no
  combo_legs → auto-settled leg-by-leg by `settle_multimatch_parlays` (HT via _grade_ht_selection,
  rest via judge_market — all unit-verified: GG/Über/HT grade correctly). `/api/tips?mcat=special`
  filter added. Built live: 4-game combo @26.2 with varied markets.
- `settle_hq_combos` now also accepts source "hq-master" (for any future same-game master builder
  with combo_legs); harmless for current master tips (they have no combo_legs).
- Frontend `RateWall.jsx`: new "Special" master sub-tab (UNIVERSAL hardcoded label, count + badge).
  Screenshot-verified (SPECIAL tab shows count 1).
- i18n: `nav.viewsettled` ("Settled") now translated in all 8 languages (was English-only fallback):
  de Abgerechnet, es Resueltas, el Διευθετημένα, fr Réglés, it Conclusi, ar المسوّاة, tr Sonuçlanan.

## Changelog — 2026-07-30 (batch 11) — Slip render/parse fixes + Special no-redundancy
Owner shared a Greek user slip (Altair) with tofu boxes, phonetic team names, Greek market text,
wrong dates. Fixes:
- **Share-image tofu FIXED** (`ticket_render.py`): added a universal FreeSans fallback font
  (covers Greek/Cyrillic/Arabic) via `famfor()` for team titles, market lines, league meta and
  username. Verified rendering Greek/Cyrillic ticket cleanly (no more □/?).
- **Vision parsing** (`AI_SYSTEM`): team/player names now OFFICIAL Latin (Cruz Azul not "Kroys
  Azoyl"; Crvena Zvezda; Olympiacos), home LEFT/away RIGHT as printed; markets NORMALIZED to
  standard English (Final Result, Both Teams to Score, Over/Under X, Double Chance, 1st Half) — no
  more foreign-script/phonetic markets; kickoff DATE+TIME copied exactly, never invented. Verified
  live on a Greek test slip.
- **Master count bug FIXED** (`/tips/counts`): the nav "Master (N)" badge was counting HIDDEN
  (past-kickoff) slips → inflated vs what's visible. Added `hidden != True` filter → badge now
  matches the visible sub-tabs (shows 3).
- **Special no-redundancy** (`_special_legs_for`): never combine logically-implied legs — BTTS
  already forces Über 1.5, Über 2.5 forces Über 1.5. A total/BTTS primary leg is now only paired
  with the independent "1. HZ Über 0.5", and some games stay SINGLE-leg for variety. Cleaned the
  current live Special in-place (removed the redundant Über 1.5 legs → odds 26.20→16.77).
NOTE: the reported slip lives on PRODUCTION; can't be retro-edited — fixes apply to newly
parsed/generated slips after redeploy. Per-language market display still relies on the UI's static
formatSelection map (English markets are readable everywhere; full per-language mapping is a TODO).

## Changelog — 2026-06 (Doppelpack umgebaut auf 2-Spiele-Bet-Builder)
Owner: "Zielquote egal (auch 100), Hauptsache du liest ZWEI Spiele gut" (Beispiel Lens–Arsenal
1-1 HZ → 2-1 FT @40). Vorher war `master_doublepack()` inkonsistent: Docstring sagte ~3.0-3.6,
Code zielte aber weiterhin auf ~6.0 (Band 4.0-9.0) mit 2 reinen Sieg-Wetten, ohne korrelierte Märkte.
- **Umbau** (`server.py master_doublepack`): jetzt liest der Master die 2 Spiele mit dem STÄRKSTEN
  Favoriten (fav_prob ≥ 58, torfreundlich via `_zero_zero_assessment.over_safe`) aus
  `match_predictions` und baut PRO Spiel einen smarten korrelierten Same-Game-Builder via des
  bestehenden `_special_legs_for` (Favorit-Sieg + beide treffen · Doppelte Chance + Über · HZ-Tor +
  Über usw., nicht-redundant). Kein starres Quoten-Band mehr (Quote ist Ergebnis, nicht Ziel).
  Muster-Index pro Spiel versetzt (0 / 2), damit die 2 Spiele nicht identische Builder bekommen.
  Struktur: `legs[].selections/sel_odds`, is_parlay, KEIN combo_legs → wird Bein-für-Bein von
  `settle_multimatch_parlays` abgerechnet (HZ via `_grade_ht_selection`, Rest via `judge_market`).
  market="Doppelpack — 2 Spiele Bet-Builder". Eine offene Doppelpack gleichzeitig.
- **Getestet** (manuelles Skript): 2 geseedete + reale Pool-Spiele → sauber generierter 2-Spiele-
  Builder; ALLE Selektionen graden korrekt (won im 3:1/HZ 1:0-Szenario, lost im 0:0-Szenario).
  Frontend unverändert nötig (Doppelpack-Tab rendert selections identisch zum Special-Tab).
- HINWEIS an Owner: Änderung ist in der PREVIEW-Umgebung → "Save to GitHub → Deploy" nötig, damit
  sie live auf der Domain erscheint.

## Changelog — 2026-06 (Special/Doppelpack: redundante Beine automatisch entfernen)
Owner (nach Deploy): "Ich sehe im Special immer noch beide treffen UND über 1.5" (redundant:
beide-treffen erzwingt bereits Über 1.5). Ursache: der aktuelle Code erzeugt das NICHT mehr
(`_special_legs_for` ist nicht-redundant, Preview-DB sauber) — der gemeldete Schein war ein
ALTER Special auf PRODUCTION (vor dem Deploy erstellt), der wegen der "1 Special/Tag"-Regel offen
liegen bleibt und nicht durch einen neuen ersetzt wird.
- **Permanenter Schutz** (`server.py`): neue `_dedupe_multigame_legs(legs)` + `master_dedupe_open_slips()`.
  Nutzt das bestehende `dedupe_implied_legs` (betting_logic.py) PRO SPIEL auf die `selections`/
  `sel_odds` der Multi-Match-Master-Scheine (Special/Doppelpack/Safe): entfernt jede Selektion, die
  von den anderen Selektionen DESSELBEN Spiels logisch impliziert wird (Beide treffen ⇒ Über 1.5,
  Über 2.5 ⇒ Über 1.5) und rechnet die Gesamtquote neu. Selektionen ÜBER verschiedene Spiele hinweg
  bleiben unangetastet (nicht redundant).
- Verdrahtet: bei Generierung in `master_special_build` UND `master_doublepack` (defensiv), sowie als
  Bereinigungslauf `master_dedupe_open_slips()` in jedem `master_loop`-Zyklus → säubert Legacy-Scheine
  automatisch, auch auf PRODUCTION nach dem nächsten Deploy.
- Getestet: Unit (BTTS impliziert Über 1.5 bei realen Teamnamen) + E2E (Legacy-Special mit
  "Beide Teams treffen"+"Über 1.5" → Über 1.5 entfernt, Quote 3.94→3.15). Backend gesund (special 200).
- HINWEIS: Auf tipjarglobal.com verschwindet die Redundanz erst nach "Save to GitHub → Deploy".

## Changelog — 2026-06 (Experten/Mitglieder-Scheine: Selektionen super sauber übersetzen)
Owner (Screenshot, Live): ein Altair-Experten-Schein zeigte griechisch-phonetische Bein-Texte
("Kroys Asoyl - Teliko Apotelesma", "Nai (GG) - Na skoraroyn kai oi 2 omades", "Mpaia - Teliko
Apotelesma") — die Karten-Überschriften waren korrekt, aber die BEIN-BOXEN nicht. Owner-Wahl B:
"alle Scheine annehmen, aber super sauber korrigieren".
- **Ursache**: Die Selektionen sind auf GRIECHISCH gespeichert; das Frontend `toLatin` TRANSLITERIERT
  sie nur phonetisch (Griechisch→Greeklish) statt zu übersetzen. `_canonicalize_display` fasste bisher
  nur `lg["match"]`/`league`/`country` an, NICHT `lg["selections"]` und nicht das Top-Level-`market`.
- **Fix** (`server.py`):
  1. Neuer LLM-Helper `_canonical_selection(sel)` (Cache `db.sel_alias`): übersetzt eine griechische
     Wett-Selektion in ein STANDARD-DEUTSCHES, abrechnungs-kompatibles Markt-Label mit kanonischen
     Teamnamen (z.B. 'Κρουζ Αζουλ - Τελικό Αποτέλεσμα' → 'Cruz Azul Sieg'; 'Ναι (GG) - Να σκοράρουν…'
     → 'Beide Teams treffen'; 'Άνω 1.5 - 1ο Ημίχρονο' → '1. Halbzeit Über 1.5 Tore').
  2. `_canonicalize_display` kanonisiert jetzt zusätzlich jede `lg["selections"]` (Greek→DE) UND das
     Top-Level-`market` ('Πολλαπλό στοίχημα' → 'Kombiwette').
  3. `enrich_member_picks`-Query um `{"legs.selections": /[Α-Ωα-ω]/}` und `{"market": /[Α-Ωα-ω]/}`
     erweitert → Scheine mit bereits kanonischer Überschrift, aber griechischen Selektionen, werden
     erneut verarbeitet. Läuft in `member_live_loop` (idempotent, gecacht).
- Getestet (E2E): kompletter Greek-Experten-Schein → alle Bein-Selektionen + Markt + Header sauber
  ins Deutsche/kanonische Englisch übersetzt; die deutschen Labels sind settlement-kompatibel.
- HINWEIS: Bestehende Scheine auf tipjarglobal.com werden nach "Save to GitHub → Deploy" von der
  enrich-Schleife automatisch bereinigt (die Übersetzungen werden gecacht → einmalig 1 LLM-Call/Text).

## Changelog — 2026-06 (Tasmania-Blacklist, Halbzeit-Märkte raus, "Zum Pick gehen"-Deep-Link)
Owner (Live, Screenshot des Master-Special + eigener Wettschein): (1) Halbzeit-Märkte gibt es bei
diesen Spielen nicht → nur realistisch spielbare Märkte übernehmen; (2) das tasmanische Spiel
(Somerset–Burnie Utd, Tasmania Northern Championship) ist nicht verfügbar → ganze Liga blacklisten +
Spiel aus dem Schein entfernen; (3) Benachrichtigungen sollen einen funktionierenden
"Zum Pick gehen"-Knopf bekommen.
- **Tasmania-Blacklist** (`server.py TEAM_LEAGUE_BLACKLIST`): 'tasmania','tasmanian','burnie' ergänzt
  (die "championship"-Whitelist matchte fälschlich "Tasmania Northern Championship"; Blacklist hat
  Vorrang in `_pred_whitelisted`).
- **Halbzeit-Märkte entfernt** (`_special_legs_for`): Builder nutzt jetzt AUSSCHLIESSLICH Vollzeit-
  Märkte (Sieg, Doppelte Chance, Beide treffen, Über 1.5/2.5), die jeder Buchmacher anbietet —
  KEINE "1. Halbzeit"-Wetten mehr (betrifft Special UND Doppelpack). Muster bleiben korreliert +
  nicht-redundant.
- **Auto-Bereinigung offener Master-Scheine** (`master_dedupe_open_slips`, läuft in jedem master_loop):
  entfernt (a) Beine auf blacklisteten Ligen/Teams, (b) alle "Halbzeit"-Selektionen (Bein wird
  gedroppt, wenn nur HZ), (c) logisch implizierte Beine; rechnet Quote neu und hält Markt-Label
  ("N Spiele") + ai_analysis synchron. → säubert die Live-Scheine automatisch nach dem Deploy.
- **"Zum Pick gehen"-Deep-Link funktioniert jetzt auch für Master-Sub-Tabs**:
  - `background_tasks.py _push_payload_for_tip`: Master-Push-URL trägt jetzt den Sub-Tab
    '/?pick={id}&area=master&sub={master_category|slips}'.
  - `App.js`: `jumpToPick(area, pick, sub)` + Deep-Link-Effekt lesen `sub`; `initialSub` an RateWall.
  - `RateWall.jsx`: neuer Effekt setzt bei `initialSub` den korrekten `masterTab`/`cat`/`liveCat` →
    die Pick-Liste lädt, Karte `pick-{id}` wird gefunden, gescrollt und hervorgehoben.
  - `NotificationBell.jsx`: In-App-Toast + Push-URL tragen ebenfalls den Sub-Tab.
  Root-Cause war: Master-Deep-Link öffnete nur `view=master` mit Default-Tab "slips" → Special-Pick
  war nie geladen → Scroll fand die Karte nie.
- **Getestet (Testing-Agent, iteration_46.json, 100% BE+FE)**: Deep-Link-URL + `tj-open-pick`-Event
  öffnen korrekt Master→Special, laden & highlighten die Karte; Special-Slip ist sauber (kein
  Tasmania, kein Halbzeit, Quote 5.67, 3 Beine); Backend-Check bestätigt keine blacklisteten
  Ligen/HZ-Selektionen. Kosmetischer Punkt (veraltete ai_analysis/Markt-Zählung) ebenfalls behoben.
- HINWEIS: Auf tipjarglobal.com greift alles erst nach "Save to GitHub → Deploy"; danach bereinigt
  der master_loop die bestehenden Live-Scheine automatisch.

## Changelog — 2026-06 (Neue Quelle: betarades.gr → nur für Master-Auswahl)
Owner: "New expert (betarades.gr), aber nur damit der Master auswählt." (Der zuvor geschickte
Telegram-Link war eine PRIVATE Gruppe "Kingbet chat" → technisch nicht scrapebar; nur öffentliche
Kanäle gehen.) betarades.gr ist öffentlich → als 6. Predictor-Quelle in den Master-Auswahlpool
`match_predictions` eingebunden, KEIN sichtbarer Experte/Badge.
- **Neuer Scraper** (`scrapers_autopost.py betarades_autopost` + `betarades_loop`, alle 30 Min,
  leader-gated, max 25 Spiele/Lauf, requests+bs4):
  1. Liest die Tagesliste (`/prognostika/`) → Spiele + Anstoß + Liga-Sektionen (europäische
     Comp-Slugs → englische Ligennamen für die Slip-Whitelist).
  2. Pro Spiel: liest die JSON-LD `startDate` (exakter Anstoß), die 3 Schnell-1X2-Quoten und die
     Tipster-Empfehlung ("Επιλογή …").
  3. Leitet Favorit + margenbereinigte Favoriten-Wahrscheinlichkeit aus den 1X2-Quoten ab; Over/Under
     2.5 + G/G aus dem Empfehlungstext; grobe ph/pa passend dazu.
  4. **Griechische Teamnamen → kanonisches Latein** via `_canonical_team_name` (LLM, gecacht) →
     matchen API-Football für echte Quoten + Auto-Abrechnung.
  5. `store_match_prediction("betarades", …)` → der Master (Special/Doppelpack/Safe/…) wählt daraus.
- Verdrahtet: Import + `betarades_loop`-Task in `server.py` (nach `footballinsight_loop`).
- **Getestet (Live-Lauf)**: 62 Spiele gefunden, Namen perfekt kanonisiert (ΠΑΟΚ→PAOK,
  ΝΤΙΝΑΜΟ ΚΙΕΒΟΥ→Dynamo Kyiv, ΚΑΡΑΜΠΑΚ→Qarabag, ΧΑΙΝΤΟΥΚ→Hajduk Split), Favorit/Quoten korrekt
  abgeleitet, als `source='betarades'` gespeichert. Backend startet fehlerfrei.
- Sichtbarkeit: erscheint NUR im Master-Auswahlpool, nicht als öffentlicher Schein.
- HINWEIS: greift live erst nach "Save to GitHub → Deploy".


## Changelog — 2026-07-30 (5 neue versteckte Predictor-Quellen für Master-Pool)
Owner: "New hidden non really existing expert for every site" → 5 Seiten geliefert. Alle NUR als
versteckte Quellen für `db.match_predictions` (Master-Auswahlpool), KEINE öffentlichen Tipster-Profile.
Umgesetzt wie `betarades` (requests+bs4, leader-gated, alle 30–45 Min, Griechisch→Latein via
`_canonical_team_name`, Anstoßzeiten Athen-Lokal → UTC (−3h)).

**3 von 5 gebaut & live getestet** (`scrapers_autopost.py`, verdrahtet in `server.py`):
- **matchmoney.com.gr** (`matchmoney_autopost`/`_loop`): Homepage-Slider → 6 Top-Spiele mit
  1X2-Quoten + exaktem Anstoß (`slider_countdown` data-attrs) + Liga. Favorit aus Quoten. BESTE Quelle.
  Getestet: 6 Preds gespeichert (PAOK, Panathinaikos, Hajduk Split, Midtjylland, Besiktas, AEK Larnaca).
- **foxbet.gr** (`foxbet_autopost`/`_loop`): Featured-Fixture aus eingebettetem JSON
  (`__frontpageSliderInitialState`) mit 1X2-Quoten. Nur 1 Headline-Spiel/Lauf (nur dieses hat
  Quoten im statischen HTML). Getestet: 1 Pred (PAOK - Dynamo Kyiv).
- **socialgamblers.gr** (`socialgamblers_autopost`/`_loop`): Mike Moytafidis' Tages-Artikel; parst die
  Tipp-Tabelle [Spiel · Tipp · Quote] der neuesten Fußball-Artikel (`/feed`). Nur settle-bare
  Goal/1X2-Signale (GG, Over 2.5 Tore, άσσος/διπλό); Spieler-Props (σουτ/κόρνερ/κάρτες) werden
  ignoriert. Anstoßzeit unbekannt → Artikeldatum 21:00 Athen (18:00 UTC). Getestet: GG-Signal
  aus Mikes Tabelle gespeichert.

**2 von 5 NICHT gebaut (technische Grenze — statisches HTML enthält keine Picks/Quoten):**
- **kingbet.net**: 1X2-Quoten per JS nachgeladen (Spans im statischen HTML leer) → kein Favorit ableitbar.
- **bethome.gr**: komplett JS-gerendert; requests liefert nur Offer-/Cookie-Banner, keine Spiele.
  → Beide bräuchten einen Headless-Browser (Chromium/Playwright); dem Owner gemeldet, offen für Entscheidung.

HINWEIS: greift auf tipjarglobal.com erst nach "Save to GitHub → Deploy".

## Changelog — 2026-07-30 (Nachtrag: bethome via Chromium; kingbet nicht umsetzbar)
- **bethome.gr** GEBAUT (`bethome_autopost`/`bethome_loop` in `scrapers_autopost.py`, alle 45 Min,
  `ensure_chromium`-gated wie statarea). Headless Chromium rendert 3 Kategorie-Seiten
  (Δυνατό Σημείο / Goal-Goal / Over-Under); parst `.betting-tips-listing__row`
  ("TEAM - TEAM DD/MM HH:MM PICK ODDS STAKE [SCORE ±res]"). Nur PENDING-Zeilen (ohne Endergebnis),
  Signale: Goal/Goal→btts, Over 2.5/3→over25, 1/1X→Heim-Fav, 2/X2→Auswärts-Fav. Griechisch→Latein,
  Athen-Zeit→UTC. Live getestet: 64 Zeilen gescraped, 2 offene Picks gespeichert (Midtjylland-Besiktas,
  Ilves-Stjarnan) — Rest sind historische/ausgewertete Ergebnisse (korrekt übersprungen).
- **kingbet.net** NICHT umsetzbar: Featured-Match-Quoten UND Pick laden aus einem separaten JS-Widget
  ohne stabilen Pro-Match-Key; die slide-eigenen `o1-<mongo>`-Spans bleiben auch nach networkidle+Scroll
  leer, und die Detailseiten (`/prognostika/...`) rendern den Pick ebenfalls per JS. Damit keine
  zuverlässige Quote↔Spiel-Zuordnung möglich → bewusst weggelassen (garbage-in würde Master schaden).
  Fixtures überschneiden sich ohnehin mit matchmoney (saubere Quoten).

Stand: 4 von 5 neuen versteckten Quellen live (matchmoney, foxbet, socialgamblers, bethome). kingbet offen.

## Changelog — 2026-07-30 (kingbet via JSON-API + Konsens-Booster)
### kingbet.net — jetzt LIVE (reine requests, kein Browser)
Odds-JSON-Endpoint entdeckt: `https://apiv2.kingbet.net/matches/latest-odds?matches=<ids>&group_key=gr`
liefert je Match-ID (aus statischem Homepage-HTML, `.analysis-slide[data-mongo]`) echte Buchmacher-
Quoten (opap/novibet): match_result 1X2, total_goals 2.5, both_teams_to_score. `kingbet_autopost`/
`kingbet_loop` (alle 30 Min) in `scrapers_autopost.py`, registriert in `server.py`. Fav aus 1X2,
Over/BTTS aus echten Märkten. Live getestet: 6 Prognosen gespeichert. → ALLE 5 neuen Quellen live
(matchmoney, foxbet, socialgamblers, bethome, kingbet).

### Konsens-Booster — der Master bevorzugt Spiele mit Quellen-Übereinstimmung
Neue Helfer `_consensus_map(preds)` / `_consensus_for(cmap, home, away, fav)` in `server.py`:
zählen pro Fixture (via `_match_key`), wie viele DISTINKTE Prognose-Quellen denselben Favoriten /
Over 2.5 / BTTS nennen. Verdrahtet in:
- `favourite_smart_autopost`: Sortierung jetzt (Konsens, fav_prob, fg); Rating-Bonus (+0.5 ab 3, +0.5
  ab 5 Quellen); Analyse-Hinweis "🔗 Konsens: N Quellen sehen denselben Favoriten".
- `master_doublepack`: wählt die 2 Spiele mit dem breitesten Favoriten-Konsens (dann fav_prob/total);
  Analyse nennt den Konsens beider Spiele.
- `master_special_build`: Tor-Konsens (over_n+btts_n) zuerst → wählt die 4 tor-einigsten Spiele;
  Analyse nennt Ø Quellen-Übereinstimmung.
Dry-Run gegen Live-Daten bestätigt: Doppelpack top = Panathinaikos-Paksi (3 einig); Special top =
Midtjylland-Besiktas (7 Quellen, Tor-Konsens 10).

HINWEIS: greift auf tipjarglobal.com erst nach "Save to GitHub → Deploy".

## Changelog — 2026-07-30 (Community-Pick sofort übernehmen + Leg-Status grün/rot/durchgestrichen)
1. **Schonfrist / sofort übernehmen** (`background_tasks.py::_is_unplayable`): ein Pick wird in den
   ersten 20 Min nach dem Posten NIE automatisch versteckt – auch wenn die KI Datum/Zeit falsch las.
   Danach greift der normale strenge „not_playable"-Filter. Unit-getestet (fresh past-KO → nicht
   versteckt; 40 Min alt → versteckt; Zukunft → nicht versteckt). Abrechnung unberührt (per id).
2. **Auto-Korrektur** (bestehend, `enrich_member_picks` + `_canonicalize_display`, läuft im
   member_live_loop): Teamnamen, Liga, Datum/Uhrzeit, Auswahlen (Griechisch→Englisch) werden nach dem
   Upload automatisch korrigiert. Mitglieder-Quoten werden NICHT überschrieben (bleiben wie gepostet).
3. **Leg-Status sichtbar** (`settlement.py` + `RateWall.jsx`):
   - `settle_multimatch_parlays`: schreibt pro Leg won/lost (grün/rot). NEU: ein Leg, dessen Spiel
     >14h vorbei ist aber nicht auflösbar (obskure Liga/fehlende Daten), wird als `void` markiert
     (Push, neutral) → Rest des Scheins wird trotzdem abgerechnet, statt ewig „pending" zu bleiben.
     Slip gewinnt wenn alle Nicht-Void-Legs gewonnen, verliert bei jedem verlorenen Leg, ist nur ganz
     void wenn kein Leg gewann.
   - `expire_stale_pending`: annullierte Mitglieder-Scheine → offene Legs werden auf `void` gesetzt.
   - Frontend: Leg gewonnen=grün, verloren=rot, void=durchgestrichen/grau (Spielname + Auswahl-Chips).
Hinweis: Voll-Live-Test der Auto-Abrechnung derzeit nicht möglich (API-Football 429/Rate-Limit);
Schonfrist-Logik unit-getestet, Frontend-Rendering per Screenshot verifiziert.
HINWEIS: greift auf tipjarglobal.com erst nach "Save to GitHub → Deploy".

## Changelog — 2026-07-30 (Void-Tooltip + KI-Korrektur-Badge)
1. **Void-Tooltip**: durchgestrichene (void) Legs zeigen beim Hovern „Nicht abrechenbar – als Push
   gewertet (neutral)" (title-Attribut auf Leg-Container + VOIDED-Badge). i18n-Key `wall.voidPush` (en/de).
2. **KI-Korrektur-Badge**: neues Flag `ai_corrected` wird in `enrich_member_picks` an allen 4 Update-
   Stellen gesetzt, wenn Teamnamen/Zeit/Liga/Auswahlen nach dem Upload automatisch berichtigt wurden.
   Frontend (`RateWall.jsx`): grünes Badge „KI-korrigiert" (CheckCircle2) neben EXPERTE. i18n-Key
   `wall.aiCorrected` (en/de). Feed liefert Flag über `{_id:0}`-Projektion.
Ende-zu-Ende per Screenshot verifiziert (Testdaten injiziert → Badge + grün/rot/durchgestrichen +
VOIDED-Tooltip korrekt gerendert → Testdaten zurückgesetzt).
HINWEIS: greift auf tipjarglobal.com erst nach "Save to GitHub → Deploy".

## User-Präferenz (2026-07-30) — WICHTIG
Vorschläge/„Next Action Items" sind OK. ABER diese 4 NIE wieder vorschlagen:
1. Korrektur-Detail (was die KI geändert hat), 2. Push-Konsens (Void-Kombi Quote neu färben),
3. Konsens-Badge („N Quellen einig" auf Master-Schein), 4. Telegram-Ausgabe/Bot.
Rückfragen nur bei echten Blockern (fehlende Keys o.ä.).

## Changelog — 2026-07-30 (Code-Review Fixes)
- MEDIUM behoben (`settlement.py::settle_multimatch_parlays`): bei gewonnener Kombi mit Void-Leg wird
  die Gesamtquote/Auszahlung um die Void-Legs bereinigt (void_factor, analog settle_hq_combos).
  Helfer `_leg_combined_odd`. Unit-getestet (6.00/2.00→3.00).
- LOW behoben (`scrapers_autopost.py::_greek_local_to_utc_iso`): echte DST-Zeitzone Europe/Athens via
  zoneinfo statt fixem -3h (Winter jetzt UTC+2 korrekt). Verifiziert (Winter 18:45 / Sommer 17:45 UTC).
- Review-Verdict war READY WITH FIXES; keine HIGH/CRITICAL.
- BETRIEBS-HINWEIS: Emergent LLM-Key-Budget ist ÜBERSCHRITTEN (79.80/79.77) → Team-Namen-Übersetzung
  & KI-Analyse fallen zurück/schlagen fehl, bis der Owner Guthaben auflädt (Profile → Manage plan →
  Universal Key → Add Balance).

## Changelog — 2026-07-30 (Master: mehr Scheine an vollen Spieltagen)
- `master_build_packs` (server.py): Einfach/Mittel-Limit erhöht von „2/Tag, 1 offen" auf
  PACK_DAILY_CAP=4 pro Tag und PACK_MAX_OPEN=3 gleichzeitig offen; baut pro Lauf mehrere Packs
  (while-Schleife), solange der Pool sauber Kombis hergibt. used_fixkeys verhindert weiterhin
  gemeinsame Spiele. Verifiziert in Preview: 2 Einfach + 1 Mittel offen.
- HINWEIS: Produktion (tipjarglobal.com) läuft auf ALTEM Deploy-Stand → dort weniger Master-Scheine,
  bis der Owner „Save to GitHub → Deploy" macht (bringt neue Quellen + höheres Pack-Limit live).

## Changelog — 2026-07-30 (Fix: stale Live-Push + Deep-Link ins Leere)
- `background_tasks.py::push_watch_loop`: Live-Picks werden NICHT mehr gepusht, wenn ihr Anstoß
  >3h in der Vergangenheit liegt (Spiel längst vorbei). Vorher: Live-Picks umgingen jede
  Anstoß-Prüfung → Push für z.B. "Mallorca – Al-Ittihad" 3h nach Spielende.
- `App.js::jumpToPick`: wenn der angetippte Pick nicht (mehr) existiert (auto-hidden/beendet),
  erscheint jetzt ein Toast `push.pickGone` statt stillem Nichts. i18n en+de ergänzt.
- Master baut mit erhöhtem Pack-Limit mehrere Picks (Preview: 4 offen). Auf Live erst nach Deploy
  + nachdem der master_loop einmal durchgelaufen ist.
- ALLE Fixes sind in PREVIEW → tipjarglobal.com braucht erneuten "Save to GitHub → Deploy".

## 2026-07-30 — Slip-Upload "Teams nicht erkannt" (Bug-Fix)
- ROOT CAUSE (reproduziert): analyze_tip (Gemini 3.1 Pro Vision via Emergent Universal Key) schlug fehl mit `OpenAIException - Daily spend limit reached`. Bei KI-Fehler gab analyze_tip den leeren Fallback zurück → Frontend zeigte fälschlich "Teams nicht erkannt".
- FIX: analyze_tip liefert jetzt `ai_error: true` bei KI-Ausfall/kein Key/kein JSON. Frontend (SubmitTipModal) zeigt dann `submit.aiUnavailable` ("KI gerade nicht verfügbar…") statt der irreführenden "Teams nicht erkannt"-Meldung. i18n-Keys en+de ergänzt (Rest fällt auf en zurück).
- USER-AKTION nötig: Universal Key Tageslimit/Guthaben erhöhen (Profil → Manage plan → Universal Key → Add Balance / Auto-Top-up).
- Nur PREVIEW — Deploy via Save to GitHub → Deploy nötig für Live.


## 2026-07-30 — LLM-Kosten-Fix + Torshavn-Learning + Master-Avatar (batch)
1. **Kosten-Optimierung (P0)**: `core.py` neuer `AI_TEXT_MODEL = "gemini-2.5-flash"`. Alle 7
   Text-LLM-Aufrufe in server.py (llm_pick_analysis, moderate_text, _translate_batch,
   _canonical_league_name, _canonical_team_name, _canonical_selection, qualifier-briefing)
   laufen jetzt auf Flash statt `gemini-3.1-pro-preview`. Nur die 3 VISION-Aufrufe (analyze_tip,
   extract_win_slip, generate_smart_from_idea = Slip-OCR) bleiben auf Pro. Verifiziert:
   /api/i18n/translate DE→Griechisch funktioniert mit Flash. → drastisch weniger Budget-Verbrauch.
2. **Torshavn-Learning (starke Seite backen)**: neue Helfer `_favourite_side_map` +
   `_leg_backs_clear_underdog` (server.py). `_master_leg_candidates` droppt team-spezifische Beine
   auf der klaren Underdog-Seite (fav_prob≥62); `goal_thirst` schließt klare Underdogs aus der
   "trifft"-Liste aus (außer Modell erwartet selbst 2+ Tore). Unit-getestet mit den echten
   Torshavn/Hajduk/Pafos-Fällen. KO-Autopost backt weiterhin korrekt den Hinspiel-Sieger.
3. **Master-Avatar + konkrete Minuten-Calls (Owner-Wahl B/B)**: `master_avatar_calls()` (server.py,
   in master_loop, 1×/Berlin-Tag, max 3 Calls) — backt NUR die starke Seite (fav_prob≥62), erkennt
   Tor-"Durst" (Fav ohne Tor im letzten Spiel → früher), leitet ein Minuten-Fenster (40/60/75/90) ab
   (`_avatar_goal_minute`). Reales, abrechenbares Bein: ≤45' → "Über 0.5 Tore 1. Halbzeit" (HZ-graden),
   sonst "{Fav} Über 0.5 Tore" (Team trifft). Endpoint `GET /api/master/avatar`. Frontend:
   `MasterAvatar.jsx` (Krone + Sprechblase, zyklisch) oben im Master-Kanal + neuer Default-Tab
   "🔮 Sichere Calls" (mcat=avatar) + Karten-Badge "🔮 bis X.'". Screenshot-verifiziert.
   HINWEIS: exakte Minuten-Märkte bieten die meisten Buchmacher nicht/nicht abrechenbar an → das
   PLAYBARE Bein ist der nächstsichere Markt (HZ-Tor / Team trifft), die Minute steht in der
   Avatar-Aussage. Owner darüber informiert.
   FIX (Owner "Spiel existiert nicht"): `master_avatar_calls` verifiziert jedes Spiel via
   resolve_team_id + find_upcoming_fixture (kein Phantom-Spiel mehr); Avatar-Bubble/Tab/Idle-Zeile
   vollständig lokalisiert (i18n master.avatar.idle / master.cat.avatar in allen 8 Sprachen +
   dynamischer prose-Cache für den Call-Text).
4. **Statistik-Entdopplung (P1)**: `/ht-goal-forecast` dedupt jetzt per `_match_key` (reihenfolge-/
   akzent-unabhängig) → "PAOK–Dinamo" erscheint nur EINMAL (kein reversed-Fixture-Duplikat).
- ALLE Änderungen sind in PREVIEW → tipjarglobal.com braucht "Save to GitHub → Deploy".


## 2026-07-30 (Teil 2) — Push, In-Form-Stürmer, Live-Über-Bewertung, Test bestanden
5. **Push für Avatar-Calls** (background_tasks.py `_push_payload_for_tip`): eigener Push
   „🔮 Sicherer Master-Call · bis X.'" für neue avatar_call-Tips (fire-Sound, sub=avatar).
6. **Live-Über-Bewertung ehrlich (Owner „10★ Über 4.5 verloren")**: `live_autopost` vergibt keine
   pauschalen 10★ mehr; Rating = min(7, 1/odd·10). PLUS Kontext-Strafen `_live_overline_penalty`
   (aus denselben Live-Stats, kein Extra-Call): Blowout |Diff|≥3 −2★, rote Karte −1★, K.o./Pokal
   −1.5★. Offene ausgeglichene Spiele bleiben bis 7★; <3★ → gar nicht angeboten. `_live_red_cards`
   + `_is_knockout_label` neu. Bestehende Banger >7★ einmalig geklemmt.
7. **In-Form-Stürmer (Owner „Pavlidis 4 Tore")**: `_hot_scorer_for_team` (nutzt 24h-gecachte
   get_team_players → keine Extra-Quota) findet den Top-Torjäger (reg. Starter, ≥4 Saisontore).
   `master_avatar_calls` gibt bei prob≥0.52 einen „{Spieler} — Torschütze (Anytime)"-Call aus
   (settlebar via scorer-grading), sonst HZ-Tor/Team-trifft. Endpoint liefert avatar_player/avatar_scorer.
8. **Master-Avatar Voll-Test bestanden**: iteration_47.json — 100% Backend (7/7) + Frontend, keine
   Bugs. Avatar-UI, Zyklus, Minuten-Chip, Lokalisierung (el/en), Anti-Underdog, kein Live->7★
   Über-Linie, ht-goal-Dedup alle bestätigt. Seed-Testdaten wieder entfernt.
- ALLE Änderungen in PREVIEW → „Save to GitHub → Deploy" für tipjarglobal.com nötig.

## 2026-07-31 — Lern-Framework (Code-Reader + Master + HQ) + Route-Bugfix
1. **Neues Modul `learning.py`**: aggregiert ALLE abgerechneten Picks (won/lost) aus der DB
   pro System (master/hq/code) und Markt-Muster (`learn_bucket`) zu ECHTER Trefferquote.
   `learn_verdict()` → veto (<40% bei ≥6), boost (≥70%), sonst ok. `refresh_learning()`
   mutiert den geteilten `_LEARN`-Cache in-place + persistiert Snapshot in `db.learn_stats`.
2. **Rückkopplung verdrahtet**: `_master_leg_candidates` droppt vetoed Bein-Muster;
   `build_systems` (Value-Loop) fällt bei vetoed Markt auf sichere Linie zurück;
   `_code_read_interpret` → NO BET bei vetoed Muster (`_code_apply_learn`).
3. **Code-Reader lernt**: dauerhaftes Speichern (nur unsettled today wird bei Re-Scan ersetzt),
   `settle_code_reads()` + `_grade_code_our_market()` werten Gegen-Pick gegen echtes Ergebnis
   (API-Football find_finished_fixture/_datescan), Ergebnis-Badge (✓/✗ + Score) pro Karte.
   Neue Regeln: `team_total_under_low` (Team Unter 1.5 → Team Über 0.5),
   `team_total_over_cap` (Team Unter 2.5–Nein → Team Unter 3.5). Frühes-Remis-Regex fixt EN "15th".
4. **`learning_loop`** (startup, alle 20 min): settle_code_reads → refresh_learning. Init-Refresh ~60s.
5. **Endpoints**: GET /api/learning/stats (public, formatiert), POST /api/admin/learning/refresh (admin).
6. **UI**: `CodeReading.jsx` neu — Guide, Beispiele, Upload, Outcome-Badges, "Lern-Statistik"-Panel
   (Master/HQ/Code je Muster mit %, n, Verdict-Badge herabgestuft/bewährt/aktiv).
7. **BUGFIX (kritisch, latent aus Vorsession)**: `app.include_router(api_router)` lief bei Zeile
   4216, während `/code-reading` & `/learning`-Routes DANACH definiert waren → NIE registriert
   (Code-Reader war live gar nicht erreichbar). include_router ans Dateiende verschoben → alle
   spät definierten Routes registriert. Regressionstest bestätigt: kein bestehender Endpoint kaputt.
8. **Test**: iteration_49.json — 100% Backend (11/11 pytest) + Frontend, keine Bugs.
- ALLE Änderungen in PREVIEW → tipjarglobal.com braucht "Save to GitHub → Deploy".


## Update 2026-07-31 — Live-Feed-Aufteilung (Community Live)
- "Live Picks" nav umbenannt → "Live KI Picks" (de) / "Live AI Picks" (en); Ansicht zeigt jetzt NUR KI-Live-Picks (neuer Backend-Filter `source=kilive` = hq-auto/hq-live/hq-system/smart). Community-Sub-Chip aus der Live-Ansicht entfernt.
- Neuer kleiner blauer Nav-Button "Community Live" (view=`livecommunity`) direkt rechts neben "Community Picks"; zeigt Live-Scheine echter Mitglieder/Community (source=members + status=live). Eigener Auto-aktualisierender Zähler via neuem count-Feld `community_live` in `/api/tips/counts`.
- Nav neu angeordnet: ai, smart, members, livecommunity, systems, master, live, settled, scorers, codereading (Community Picks weiter links, kleiner Live-Button rechts daneben, mobil sichtbar).
- Dateien: server.py (tips_counts + list_tips kilive-Zweig), i18n.js (nav.viewlive umbenannt, nav.viewlivecommunity neu), RateWall.jsx, App.js.
- Getestet: curl (counts liefert community_live; kilive/members-live filtern korrekt) + mobile Screenshots.

## OFFEN / PENDING (User-Entscheidung ausstehend)
- (keine offenen Punkte aus dem Feed-Split)

## Update 2026-07-31 (2) — Swagger-Fix, Community-Live-Badge, Admin-Slip-Editor
- **Swagger-Fix (editierbare Auswahl):** Im Post-Fenster (SubmitTipModal.jsx) ist das Feld "Markt/Auswahl" jetzt ein Eingabefeld (`market-edit-input`). Erkennt die KI keine Auswahl (Live-Odds-Screenshot → leere Legs + leerer Markt), erscheint ein hervorgehobenes Pflichtfeld mit Hinweis (`selection-hint`) und die Veröffentlichung wird blockiert (Toast `submit.selectionRequired`). publish() nutzt `hadPanel ? marketEdit : (d.market||'')` damit ein bewusst geleertes Feld respektiert wird. Parlays mit Leg-Auswahlen bleiben gültig.
- **Community-Live-Badge:** Jeder Community-Live-Schein zeigt ein prominentes rotes pulsierendes "Live"-Badge (`community-live-badge-<id>`) statt des generischen Status-Badges. Bedingung: `status==='live' && isMemberPick`.
- **Admin-Slip-Editor:** Neue Komponente `AdminSlipEditor.jsx` + Button "Bearbeiten" (`admin-edit-<id>`, nur Admin) auf jeder Karte. Bearbeitbar: Anstoß/Zeit, Teams (inkl. Tausch), Liga/Land, Markt/Quote/Einsatz, sowie pro Bein: Match, Kickoff, Status (Offen/Live/Gewonnen/Verloren/Annulliert), Banker-Toggle, Auswahlen + Quoten hinzufügen/entfernen, Bein entfernen. Backend: `PATCH /api/admin/tips/{id}` (require_admin, `_admin_sanitize_legs`, recompute is_parlay/potential_return).
- **"Spiel zuende" (manuelle KI-Abrechnung):** Roter Button (`admin-settle-now-<id>`) auf Community-Live-Scheinen → `POST /api/admin/tips/{id}/settle-now` (setzt settle_attempts=0, ruft settle_pending_tips/settle_multimatch_parlays, gibt `{settled, tip, reason}` zurück). Bei noch laufendem Spiel: Info-Toast statt Fehler.
- Getestet: iteration_50 (Tasks 2&3 PASS, Task1 Bug gefunden) → Fix → iteration_51 (Fix + Regression PASS). Backend per curl verifiziert (Edit persistiert, Leg-Edit/Remove, settle-now).
- Dateien: server.py (PATCH + settle-now Endpoints, `_admin_sanitize_legs`), SubmitTipModal.jsx, RateWall.jsx (Badge + Admin-Tools + doSettleNow), AdminSlipEditor.jsx (neu), i18n.js (submit.selectionRequired/Ph).

## Update 2026-07-31 (3) — Admin-korrigiert-Badge & Auto-Abrechnung Community-Live
- **Admin-korrigiert-Badge:** Auf jedem Schein mit `admin_edited=True` zeigt die Karte ein Indigo-Badge "vom Admin korrigiert" (`admin-edited-badge-<id>`, Stift-Icon) für Transparenz. i18n `tip.adminEdited` (de/en). Verifiziert per Screenshot.
- **Auto-Abrechnung Community-Live:** Die bestehende `settlement_loop` deckt Community-/Experten-Live-Scheine bereits ab (Singles via `settle_pending_tips` jede Runde; Parlays via `settle_multimatch_parlays`). NEU: Für Live-Status-Scheine wurde die Parlay-Bein-Fälligkeit von 2h-nach-Anstoß auf ~105 min gesenkt (`elig_gap` in settlement.py), damit sie direkt nach Abpfiff automatisch abgerechnet werden — sicher, da `find_finished_fixture` nur FT-Spiele zurückgibt. "Spiel zuende"-Button bleibt als manueller Sofort-Trigger. Backend-Pfad fehlerfrei per curl getestet.

## Update 2026-07-31 (4) — Codemining i18n, Community-Live-Knopf, Zähler & Live-Score
- **Codemining pro Sprache übersetzt:** CodeReading.jsx übersetzt jetzt `reason` (Analyse) via `useProseTranslations` + `localizeProse`/`toLatin`-Fallback und lokalisiert Märkte (`localizeMarket`/`formatSelection`) — vorher nur Deutsch. Selber Mechanismus wie RateWall ai_analysis.
- **Blauer "Community Live"-Knopf in der Community-Ansicht:** Zusätzlich zum Nav-Pill gibt es jetzt in der "Community Picks"-Ansicht einen prominenten kleinen blauen Button (`community-live-jump`, pulsierender Punkt + Zähler), der per `tj-open-view`-Event zur Community-Live-Ansicht springt. (Nav-Pill "Community Live" existierte bereits im Preview — Produktion braucht Deploy.)
- **Codemining-Zähler:** `/api/tips/counts` liefert neu `codereading` = Anzahl aktiver, noch nicht abgerechneter (pre-game) geminter Codes. Zahl auf dem "Codemining"-Nav-Button (z.B. 7).
- **Live-Score im Community-Live-Badge:** Rotes Live-Badge zeigt nun Spielstand + Minute (z.B. "LIVE · 0:0 37'"), aus `tip.live_state` (Einzel) bzw. einzigem live Leg (Parlay). Annotation via bestehendem `live_annotate_sync`.
- Getestet: curl (codereading=7, community_live=4) + Screenshots (blauer Knopf, Zähler 7, Live-Score-Badge "0:0 37'"). Frontend kompiliert fehlerfrei.
- Dateien: server.py (tips_counts codereading), CodeReading.jsx (i18n), RateWall.jsx (community-live-jump + clCount + liveScoreText im Badge).

## Update 2026-07-31 (5) — Homepage Community-Knopf mit eingebautem Live-Button
- Der "Community Picks"-QuickView-Knopf auf der Homepage (Header.jsx) ist jetzt ein geteilter Button: "Community Picks" links (→ members), separater kleiner blauer "LIVE"-Button rechts (→ livecommunity), einzeln klickbar. Testids: `view-members-btn-wrap`, `view-members-btn`, `view-members-btn-live`. Live-Zähler aus `counts.community_live`. Klick-Test bestätigt: blauer Teil öffnet Community-Live.
- Dateien: App.js (onViewLiveCommunity Prop), Header.jsx (QuickView split-render via liveAction/liveCount).


## Update 2026-07-31 (6) — Systemwetten, Bet-Builder-Kombiquote, Share-Bild-Fixes, Community-Pregame-Regel
Owner-Wahlen: KI erkennt System automatisch · GESAMTQUOTE bei System = Maximalquote · manuelles
Kombi-Quoten-Feld pro Bet-Builder-Spiel · Share-Bild-Text in gewählter App-Sprache. Getestet:
testing_agent iteration_52 (alle 4 Aufgaben bestanden) + Render-Bilder de/en/el + curl-E2E.
1. **Systemwetten (KI-erkannt):** `AI_SYSTEM`-Prompt liest jetzt `bet_type` ("system"), `system_from`,
   `system_total` (z.B. "12 aus 14") vom Schein/Text. `analyze_tip` + `_sanitize_legs` + `TipSaveInput`
   + `create_tip` tragen die Felder. Frontend zeigt "System X/Y" statt "Parlay":
   `parlay-system-badge` (RateWall) + `detected-system-badge` (SubmitTipModal). i18n `wall.system`
   (alle 8 Sprachen). Verifiziert: KI erkannte "System 12 aus 14" aus Text korrekt.
2. **Bet-Builder-Kombiquote (manuell):** pro Spiel mit 2+ Auswahlen kann der Poster EINE Kombiquote
   eingeben (`leg.combo_odds`). KI liest sie auch selbst (`combo_odds` je Leg). SubmitTipModal:
   `leg-combo-odds-input-<li>`. Karte: `leg-combo-odds-<li>`-Pill (nur wenn keine Einzel-Quoten da).
   Ticket bevorzugt `combo_odds` vor dem Produkt der Einzelquoten. i18n `submit.comboOdds/Ph`.
3. **Share-Bild (`ticket_render.py`):** (a) **GESAMTQUOTE nie mehr leer** — fällt auf das Produkt der
   Pro-Spiel-Quoten zurück; bei System heißt das Label "MAX. QUOTE" (Maximalquote). (b) **Voll
   lokalisiert** via neuem `_TICKET_LABELS`-Dict (8 Sprachen) + `lfont()` FreeSans-Fallback → keine
   Tofu-Boxen bei Griechisch/Arabisch/Kyrillisch (Status/SYSTEM/BANKER/GESAMTQUOTE/EINSATZ/…).
   (c) SYSTEM-Chip "SYSTEM X/Y · N SPIELE". `_render_slip_image(..., lang, bet_type, system_from,
   system_total)`. `SHARE_RENDER_VER 4→5`; share-image cached PRO SPRACHE (`share_images` map),
   Endpoint akzeptiert `?lang=`; Frontend übergibt `tj_lang`.
4. **Community-Pregame-Regel (Owner):** lange Pregame-Community-Scheine bleiben IMMER im pregame
   Community-Bereich. In `create_tip` ist `is_live_post = (timing == "live")` — KEINE automatische
   Live-Promotion mehr über `_looks_live_now`/API-Football-Leg-Check (die verschob lange Kombis
   fälschlich in Community-Live, sobald ein Bein lief). Nur explizit als "Live" gepostete Tipps → Live.
   Verifiziert: 3-Bein-System bleibt `status=pending`.
HINWEIS: greift auf tipjarglobal.com erst nach "Save to GitHub → Deploy".


## Update 2026-07-31 (7) — TipJarMaster postet sichere Systemwetten + X-aus-Y-Abrechnung
Owner: „Lass den Master gelegentlich eine sichere Systemwette posten … im special, easy und
medium Bereich kann er frei posten." Umgesetzt & getestet (Logik-Assertions + lokaler Render).
1. **Master-Systemwette:** `master_build_packs` (server.py) macht 1×/Tag den ersten Mittel-Pack mit
   ≥3 Spielen zu einem SICHEREN System `(N-1)/N` ("1 Tipp darf danebengehen") — `bet_type="system"`,
   `system_from=N-1`, `system_total=N`, `market="System X/Y"`, passende `ai_analysis`. Karte zeigt den
   `parlay-system-badge` "System X/Y · N Spiele" neben dem Mittel-Badge; Share-Bild zeigt "SYSTEM X/Y"
   + MAX. QUOTE. Lokal gerendert verifiziert (@TipJarMaster, System 3/4, MAX 6.20).
2. **System-Abrechnung X aus Y** (`settlement.py::settle_multimatch_parlays`): neuer System-Zweig —
   gewinnt SOFORT sobald `won_cnt >= min(system_from, eff_total)` (einige Beine dürfen verlieren),
   verliert erst wenn `eff_total - lost_cnt < need` (unerreichbar), sonst pending. Void-Beine fallen
   aus dem Total (eff_total = legs - void). `lost_cnt` neu getrackt. 7 Branch-Assertions bestanden
   (3/4 mit 1 Niete → gewonnen; 2 Nieten → verloren; offen & erreichbar → pending; Void reduziert Y).

## Update 2026-07-31 (8) — Master: bankers στα συστήματα + μάθηση από λάθη (ανά σκέλος/banker)
Owner (ελληνικά, teaching): κανένας σταθερός κανόνας — «μαρκάρεις bankers στο δελτίο, αναφέρεις ποιο
σύστημα, χωρίς πολλή επεξήγηση· ο Master μαθαίνει από τα λάθη του». Γνώση στο
`/app/memory/master_system_strategy.md`.
1. **Bankers στον Master (server.py `master_build_packs`):** το σύστημα μαρκάρει τα ασφαλέστερα σκέλη
   ως bankers (nb=1 για 3-4, 2 για 5+), αποφεύγοντας market-types με κακό banker-record (learning).
   `_pack_legs(chosen, banker_matches)` βάζει `banker:true`. Σύντομη ανάλυση «System X/Y · N Banker».
   Ticket + κάρτα δείχνουν ήδη το banker badge (επιβεβαιώθηκε render ΣΤΑΝΤΑΡ σε EL).
2. **Settlement (settlement.py):** χαμένος banker → όλο το σύστημα LOST· αλλιώς X-aus-Y. Unit-tests
   πέρασαν (banker χάνει με 3 άλλα won → lost· banker κερδίζει, 3/4 → won· ζητούμενο ανοιχτό → pending).
3. **Μάθηση ανά σκέλος (learning.py `refresh_learning`):** για master parlays μαθαίνει και ΑΝΑ ΣΚΕΛΟΣ
   (learn_bucket ανά selection) + buckets `banker_<bucket>` για λάθος bankers. Ο master builder ήδη
   κάνει `learn_verdict("master", market)` veto/boost. Επιβεβαιώθηκε: refresh τρέχει, master έχει τώρα
   πλούσια per-leg buckets (team_over_0.5 12/7, over_goals 5/5, under_goals 4/0, …). `banker_*` γεμίζουν
   καθώς κατεβαίνουν & αρχίζουν να αποδίδουν συστήματα με bankers.
HINWEIS: preview → tipjarglobal.com μόνο μετά από "Save to GitHub → Deploy".

## Update 2026-07-31 (9) — Master banker TIMING (νωρίτερα = banker, ποτέ το νυχτερινό)
Owner (ελληνικά, με live παράδειγμα): banker τα ΠΡΩΤΑ σίγουρα ματς (κλειδώνει η πρόοδος), ΠΟΤΕ banker
στο τελευταίο/νυχτερινό ματς (πιάνεις τα πάντα & χάνεις στο τέλος = χειρότερο). Στο
`master_build_packs` (server.py) η επιλογή banker γίνεται τώρα με σειρά (learning-safe → νωρίτερο
kickoff → χαμηλή απόδοση) και ΑΠΟΚΛΕΙΕΙ το ματς με το αργότερο kickoff. nb=min(2 αν n>=5 αλλιώς 1, n-2)
για να μένουν πάντα ≥2 ζητούμενα. Επιβεβαιώθηκε με assertion (banker→νωρίτερο ασφαλές, όχι το νυχτερινό).

## Update 2026-07-31 (10) — Κανόνες ποιότητας banker + «ρίσκο-banker → παρέλαση»
Owner (ελληνικά): ποτέ banker/ρίσκο-ζητούμενο για γέμισμα· χαλαρά πράγματα· και ενεργοποίηση του
«ρίσκο-banker → παρέλαση» σε special/medium.
1. **Banker safety (server.py master_build_packs):** BANKER_MAX=1.55 + όχι veto· αν δεν υπάρχει
   σωστή βάση banker → γυρίζει σε απλό Kombi (χωρίς banker-γέμισμα). Το ασφαλές σύστημα φέρει
   `system_style="safe"`.
2. **`master_riskparade_build` (νέα, στο master_loop):** 1×/ημέρα στο mittel, `system_style="risk"`.
   1 ρίσκο high-odds banker (3.0-12.0, όχι veto) + 3-4 χαλαρά ασφαλή ζητούμενα (1.10-1.55), system
   (N-1)/N. Χαμένος banker → όλο χαμένο (settlement). Δοκιμάστηκε live: System 4/5 @12.99, banker
   Über 3.5 @5.00 + 4 ασφαλή, καθαρίστηκε. Δεν συγκρούεται με το ημερήσιο ασφαλές σύστημα (χωριστό style).

## Update 2026-07-31 (11) — Code-Reading („smart picks") Müll-Bereinigung
Owner: beendete Spiele (Do Conference League) hängen im smart-picks-Bereich, Analysen nicht löschbar,
gevoidete Tipps kommen zurück; KI hat Datum verwechselt.
Root-cause & Fix (server.py):
1. `/code-reading` blendet jetzt Reads aus, deren Spiel VORBEI ist (kickoff + 150 min < now). Beendete
   Spiele verschwinden automatisch — auch wenn ein alter/falsch datierter Scan sie neu anlegt.
2. Der Code-Scan (`_run_code_scan`) legt KEINE Reads mehr für bereits beendete Spiele an (fängt die
   KI-Datumsverwechslung ab).
3. Einmalige Bereinigung ausgeführt: beendete code_reads gelöscht (0 in Preview — DB war sauber, nur
   heutige Spiele), 4 eindeutig beendete KI-Tipps (kickoff+4h<now) gelöscht.
BEFUND: Preview-DB enthielt KEINEN Donnerstag-Müll (nur aktuelle Freitag-Spiele) → der sichtbare Müll
ist auf PRODUCTION. Nach Deploy blendet der Endpoint-Filter beendete Spiele automatisch aus (auch bei
bestehenden Prod-Rows). Admin-Löschbutton (Trash2) pro Analyse existiert bereits (role==admin).

## Update 2026-07-31 (12) — Neue Spezial-Geschenke (Halbzeit & erste 2 Tore), auto-abrechenbar
Owner wünschte 5 neue Pick-Typen (2 Live, 3 Gifts). Umgesetzt: die 3 GESCHENKE (sauber abrechenbar).
Generator `gift_specials_autopost()` (server.py, im master_loop, 1× je Typ/Tag), Prognose+Quote:
1. „<Fav> gewinnt mindestens eine Halbzeit" — Fav-WIN-Quote > 1.30 (Est. 1.25).
2. „<Fav> gewinnt NICHT beide Halbzeiten" — starker Fav, WIN-Quote ≤ 1.40 (Est. 1.55).
3. „<Fav> schießt die ersten 2 Tore" — WIN-Quote > 1.40, Fav ≥2 Prognose-Tore & Gegner ≤1 (Est. 2.00).
Abrechnung (settlement.py `_grade_special_gift`): Halbzeit-Gifts deterministisch aus HT/FT-Score
(1./2. Halbzeit-Sieger); erste-2-Tore aus Tor-Events-Reihenfolge (Eigentor→Gegner, retry bis Events da).
Getestet: Halbzeit-Logik (Assertions), Generator (Fav 1.55 → half_any + first_two; ≤1.40 → not_both).
NICHT umgesetzt (bewusst): die 2 LIVE-Ideen — „Ecken nach 70'" ist mit API-Football NICHT sauber
abrechenbar (keine zeit-gesplitteten Ecken), und „nächstes Tor" bräuchte Live-Event-Polling (Void-Risiko).
Bewusst weggelassen, um NICHT den unabrechenbaren Müll zu erzeugen, den der Owner gerade beklagt hat.


## Update 2026-06 (13) — "Wir spielen kein Lotto": 1X/X2 nur wenn Gegnersieg unmöglich
Owner (frustriert, Beispiel Valérenga 1X in den Single-/Smart-Picks): die KI baute "1X + Über 1.5"
NUR um die Quote künstlich aufzublasen ("Lotto-Füller"). Owner-Regel: eine Doppelte Chance darf NUR
gespielt werden, wenn ein Gegner-Sieg praktisch UNMÖGLICH ist; sonst gar keine DC. Zusätzlich
Owner-Philosophie: "Zyklus"-Denken — Teams bringen alle Ergebnisse im Zyklus, Historie/H2H beachten
(z. B. nach 3 torlosen Duellen fällt endlich ein Tor), jedes Team einzeln bewerten. "Nie Lotto-Füller."
UMGESETZT (server.py):
1. Neuer Helper `_opp_win_practically_impossible(p)` (nach `_fav_team`): DC (1X/X2) nur zulässig, wenn
   der Favorit wirklich dominant ist (fav_prob ≥ 68, in skandinavischen/nordischen "Zyklus"-Ligen ≥ 74)
   UND laut Prognose mit ≥1 Tor Vorsprung GEWINNT (kein Remis-Muster).
2. `favourite_smart_autopost` neu verdrahtet — KEIN "DC 1X + Über 1.5"-Füller mehr:
   • sehr dominant (≥66 %, ≥3 Tore) → "-1.5 Handicap" (+Über 1.5 wird als impliziert entdeduped) — sauber;
   • Gegnersieg unmöglich + Torspiel (btts) → "{Fav} Sieg + Beide Teams treffen" (korreliert);
   • Gegnersieg unmöglich, Tore unsicher → sauberer EINZEL-"{Fav} Doppelte Chance";
   • sonst (Valérenga-Fall: nicht dominanter "Favorit", jedes Ergebnis im Zyklus möglich) → GAR KEIN Pick
     (der Smart-Bereich erkennt jetzt un-spielbare Spots und postet nichts statt eines 1X-Füllers).
GETESTET: `_opp_win_practically_impossible` Unit (6 Fälle, alle korrekt: Valérenga-Nordic-Mid-Fav →
abgelehnt, Bayern/PSG-dominant → zugelassen) + Zweig-Entscheidung simuliert (Valérenga/Mid → SKIP,
Bayern → Handicap, PSG → Sieg+BTTS). Backend lädt sauber, `favourite_smart_autopost` läuft fehlerfrei.
Preview-DB hatte 0 offene Smart-DC-Picks → das gemeldete Valérenga 1X lag auf PRODUCTION.
HINWEIS: greift auf tipjarglobal.com erst nach "Save to GitHub → Deploy"; danach postet der Smart-Loop
keine unbegründeten 1X-Kombis mehr. OFFEN/Backlog: volle "Zyklus"-H2H-Auswertung (team_form/h2h_stats
in match_stats.py existieren, kosten aber API-Quota) — aktuell nur regelbasiert, ohne fresh H2H-Fetch.

## Update 2026-06 (14) — H2H-"Zyklus"-Smart-Picks (welches Team endlich trifft/gewinnt)
Owner: "Lass die H2H zeigen, welches Team endlich treffen oder gewinnen soll." Beispiele:
Lazio hat bei Roma seit 3 Jahren (2023/24/25) nicht getroffen + Roma wackelt → Lazio trifft;
"PAOK hat seit 3 Auswärtsspielen nicht getroffen → jetzt holen sie den Sieg". Fokus HEIM- vs.
AUSWÄRTSFORM + H2H-Torflauten. Story wird IM Smart-Pick erzählt, konkreter Pick direkt darunter.
UMGESETZT:
- `match_stats.py`: `h2h_detailed` (per-Duell Historie, gecacht), `team_recent` (letzte 20 Spiele),
  `venue_split` (Heim-/Auswärtsserie), `_scoreless_streak`/`_winless_streak`. Alles 12h-gecacht +
  quota-gated (schont API-Football).
- `server.py`: `_venue_h2h_drought`, `_h2h_team_drought`, `_scores_regularly`, `_cycle_signal`
  (erkennt 4 Muster, Priorität S1>S2>S3>S4) und `smart_h2h_autopost()` (im smart_loop + admin/smart/run):
  • S1: Gast trifft bei diesem Gegner seit ≥2 Duellen nicht, trifft sonst regelmäßig, Gastgeber
    kassiert zuhause fast immer → "{Gast} Über 0.5 Tore" (Lazio@Roma-Muster).
  • S2: Gast seit ≥3 Auswärtsspielen ohne Tor → "{Gast} Über 0.5 Tore"; ist der Gastgeber zuhause
    sieglos (≥3) → Upgrade "{Gast} Sieg" (PAOK-Muster).
  • S3: Gastgeber zuhause ≥3 ohne Tor → "{Heim} Über 0.5 Tore"/"{Heim} Sieg".
  • S4: Heim-Team H2H ≥3 torlos gegen diesen Gegner, trifft sonst → "{Heim} Über 0.5 Tore".
  • kein Muster → GAR KEIN Pick (selektiv, kein Müll). Max 5 neue Fixtures/Lauf. source="smart",
    h2h_cycle=True, Story in ai_analysis, Märkte über judge_market sauber abrechenbar.
GETESTET: Unit (Lazio@Roma→Lazio trifft, PAOK-Auswärtsflaute+schwacher Gastgeber→PAOK Sieg,
No-Signal→None, venue_drought 3 Jahre) + Live-Lauf (5 echte Picks: Karpaty@Kryvbas Venue-Flaute,
Widzew/Indy Auswärtsflaute, Puebla H2H-Flaute, Laos Heimflaute) + Screenshot (Story+Pick rendern,
i18n übersetzt automatisch). HINWEIS: live erst nach "Save to GitHub → Deploy".

## Update 2026-06 (15) — Zyklus-Upgrade: Tor-Rhythmus + 0:0-Schutz + echte Quoten
Drei Erweiterungen der H2H-Zyklus-Smart-Picks (server.py):
1. **Tor-Rhythmus** (`_goal_rhythm`, `_rhythm_note`): liest je Team die zuletzt erzielten Tore
   (Heim-/Auswärts-Sequenz) und leitet ab, was im Zyklus fällig ist — 0 fehlt zuletzt → Nullnummer
   überfällig (blank_due); kein 3+ zuletzt → Torausbruch überfällig (big_due). Neue Zeile
   "📈 Tor-Rhythmus {Team}: 1-2-1-2 (Ø …) → …" in JEDER Zyklus-Story. Neues Signal S1b: big_due +
   Ø≥1.2 + Gegner kassiert reihenweise → "{Team} Über 1.5 Tore" (Torausbruch fällig).
2. **0:0-Traditionsschutz** (`_zero_tradition`): erkennt chronisch torarme Duelle (≥3 der letzten 6
   H2H mit ≤1 Tor ODER ≥2× 0:0, wie Chelsea–Liverpool) → alle tor-versprechenden Signale (S1/S1b/S3/
   S4 + die "trifft"-Variante von S2) werden UNTERDRÜCKT; ein evtl. Sieg-Pick bekommt einen ⚠️-Hinweis.
3. **Echte Buchmacherquoten** (`apply_real_odds` in `smart_h2h_autopost`): schärft die Quote jedes
   Zyklus-Picks (Sieg UND Über-Märkte) mit echten API-Football-Odds, wenn Kontingent frei — sonst
   Schätzung. Feld `real_odds` + Hinweis "Echte Buchmacherquote"/"Quoten sind Schätzungen".
GETESTET: Unit (Rhythmus blank_due/big_due, 0:0-Tradition True/False, Suppression unter Tradition,
S1b-Ausbruch, Rhythmus-Note angehängt) + Live-Lauf (5 Picks: 4× echte Quoten z. B. Widzew @1.33 statt
1.55, Indy @1.28; neue Über-1.5-Ausbruch-Picks Portland/Deportivo Tachira) + Screenshot (Rhythmus-Zeile
+ "Echte Buchmacherquote" rendern, i18n übersetzt). HINWEIS: live erst nach "Save to GitHub → Deploy".

## Update 2026-06 (16) — Admin-Blacklist-Knopf + Zyklus-Endergebnis
1. **Admin-Blacklist-Knopf** (jede Pick-Karte, nur Admin): roter "Blacklist"-Button → Dialog mit
   Auswahl "Dieses Spiel blacklisten" ODER "Die ganze Liga blacklisten (+ Liganame)".
   - Backend (`server.py`): dynamische DB-Blacklist `db.dyn_blacklist` → gespiegelt in In-Memory-Sets
     `_DYN_BL_LEAGUES`/`_DYN_BL_MATCHES`, die die zentrale `_team_or_league_blocked()` mitprüft
     (→ blockt automatisch künftige Preds/Slips via `_pred_whitelisted`/`store_match_prediction`).
     `refresh_dyn_blacklist()` (Startup + nach jedem Schreiben). Endpoints: `POST /admin/tips/{id}/blacklist`
     {scope:match|league}, `GET /admin/blacklist`, `DELETE /admin/blacklist/{id}`. `_purge_blacklisted()`
     löscht passende match_predictions + versteckt offene Tips sofort (Settlement unberührt).
   - Frontend (`RateWall.jsx` TipCard): Button `admin-blacklist-{id}` + Dialog `blacklist-dialog-{id}`
     mit `blacklist-match-{id}`/`blacklist-league-{id}`/`blacklist-cancel-{id}`. i18n `wall.bl.*` (en/de).
   - Getestet: curl (match-Blacklist → 10 Preds entfernt, 1 Tip versteckt, `_team_or_league_blocked`
     True für das Spiel, False für andere) + Screenshot (Dialog mit beiden Optionen).
2. **Zyklus-Endergebnis** (`_due_goals`, `_cycle_scoreline` in server.py): leitet aus BEIDEN Tor-
   Rhythmen je Team die "fällige" Tor-Zahl ab (0 fehlt→Nullnummer, kein 3+→Ausbruch; bei beidem offen
   entscheidet Gegner-Abwehr) und hängt eine Prognose-Zeile an jede Zyklus-Story an:
   "🎯 Zyklus-Endergebnis (gewittert): Heim X-Y Gast" (in 0:0-Tradition → 0-0). Nur NARRATIV, kein
   exakter Score als Wette (Owner-Regel). Getestet: Unit (3-0 bei leckem Gast/solidem Heim, 0-0 unter
   Tradition) + Screenshot (Puebla 1-3 Chivas, Minnesota 0-3 Portland etc., i18n übersetzt).
Auch notiert (owner-Muster): Bodø/Glimt trifft VOR der 30. Min (im Codemining bestätigt) →
master_system_strategy.md. HINWEIS: live erst nach "Save to GitHub → Deploy".

## User-Präferenz (2026-06) — WICHTIG (nicht mehr vorschlagen)
Owner: "Stelle diese 3 Fragen nicht." → NIE wieder als Next Action Items vorschlagen:
1. Bodø-Frühtor-Pick (automatischer "Tor vor 30. Min"-Pick), 2. Blacklist-Verwaltungsliste mit
Ein-Klick-Entsperren, 3. Rhythmus-Konfidenz/Zyklus-Score pro Pick.
Allgemein: am Ende KEINE aufgedrängten Feature-Vorschläge/Rückfragen mehr, wenn nicht angefragt.

## Update 2026-06 (17) — Sure-Calls-Tab weg, 3 Master-Sprechblasen, Admin-Delete bleibt entfernt
1. **"Sure Calls"-Tab entfernt** (RateWall.jsx): der redundante `avatar`-Tab (🔮 Sure Calls) ist raus
   ("macht gar nix"); Standard-Tab jetzt `hotscorer`. Die Avatar-CALLS erscheinen weiterhin oben in
   den Sprechblasen.
2. **Master-Avatar: bis zu 3 Sprechblasen gleichzeitig** (MasterAvatar.jsx neu): statt einer
   rotierenden Blase werden bis zu 3 Calls gestapelt (Minute + Text + Pick + Quote je Blase); bei >3
   rotiert das 3er-Fenster alle 8s. Getestet mit 3 Test-Calls (Puebla, Union SG, Bodø-Frühtor) —
   rendern sauber.
3. **Admin-Delete bleibt entfernt (Anti-Repost)** (server.py `delete_tip`): löscht ein Admin einen
   GENERIERTEN Pick (source hq-master/hq-auto/smart oder master_category), wird er als "Grabstein"
   markiert (hidden+admin_removed, status→void) statt hart gelöscht → (a) die Master-Tages-Guards
   zählen ihn weiter (kein Nachbauen), (b) deterministische Generatoren (smartfav-/smarth2h-) finden
   die ID → posten sie nie wieder. Member-Tips werden weiter hart gelöscht. `master_dedupe_open_slips`
   überspringt `admin_edited`-Scheine (entfernte Legs bleiben entfernt). `/master/avatar` filtert
   jetzt `hidden`. Getestet: Admin-Delete eines smarth2h-Picks → Grabstein, 2× Regen-Lauf postet ihn
   NICHT neu (count bleibt 1, 0 sichtbar). Leg-Entfernen/ganzer-Schein-Delete via bestehendem
   AdminSlipEditor + Delete-Button.
Owner-Kontext: Beschwerde über "Easy = Challenge + 1 Lotto-Spiel" (Club Brugge BTTS) → Admin kann jetzt
das Lotto-Leg ODER den ganzen Schein entfernen, und es bleibt weg. Bodø-Frühtor (vor 30. Min) als
Risk-Banker-Kandidat notiert. HINWEIS: live erst nach "Save to GitHub → Deploy".

## Update 2026-06 (18) — Codemining: Endergebnis + "Beendet"-Tab + Homepage-Zähler
Owner-Wünsche (Codemining-Feed):
1. **Endergebnis auf jedes beendete Spiel**: `settle_code_reads` holt jetzt für ALLE beendeten Reads
   (Counter UND No-Bet) das Schlussergebnis und speichert `score` (No-Bet → outcome="info", nur Score).
   Frontend zeigt bei Counter "gewonnen/verloren X-Y", bei No-Bet eine "🏁 Endergebnis: X-Y"-Pille.
2. **"Beendet"-Tab**: `/code-reading` liefert jetzt `{count, reads(active), finished}` — beendete Spiele
   (Anstoß+150min vorbei ODER outcome/score gesetzt) werden NICHT mehr gelöscht, sondern in `finished`
   verschoben. Frontend (CodeReading.jsx): Tabs "Aktiv"/"Beendet" (code-tab-active/-done), beendete Karten
   mit Endergebnis. i18n de/en/el (tabActive/tabDone/endResult).
3. **Homepage-Zähler**: `/tips/counts` `codereading` zählt nur noch AKTIVE Reads (nicht beendete) — sobald
   ein Spiel in "Beendet" wandert, zählt die Badge es nicht mehr.
GETESTET: Endpoint-Split (aktiv vs. finished mit Scores für Counter+No-Bet) + Screenshot ("Beendet"-Tab
zeigt Widzew 0-0, Rangers 1-1 NO BET, LASK 3-0 NO BET, Sparta 3-1 etc.; Badge "Codemining 8" = ACTIVE).
Owner-Feedback notiert (Widzew Unter 2.5 Treffer, Rangers 1-1 No-Bet korrekt). HINWEIS: live erst nach
"Save to GitHub → Deploy".

## Update 2026-06 (19) — Codemining: Tor-Minuten auf beendeten Spielen
Owner: "Schreib auch in welche Minuten die Tore gefallen sind." → `settle_code_reads` holt jetzt via
`/fixtures/events` die Tor-Minuten je Team (`_code_goal_minutes`), speichert `goal_minutes` + `fixture_id`.
Anzeige im Beendet-Tab als "⚽ {Heim} 17', 25' · {Gast} 63'". Robust: auf reguläre Toranzahl gecappt
(Elfmeterschießen ausgeschlossen), Eigentore korrekt (API listet sie beim profitierenden Team).
Backfill: bereits abgerechnete Spiele bekommen die Minuten nachträglich (Query enthält
`goal_minutes missing & score != 0-0`). GETESTET: settle-Lauf (Bodø 4-0 → 17',25',63',77' inkl. Eigentor;
Brügge–Union 1-1 ohne Shootout; Sparta 3-1 mit Zlin 57') + Screenshot (6 Minuten-Zeilen im Beendet-Tab).
HINWEIS: live erst nach "Save to GitHub → Deploy".
