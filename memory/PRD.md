# TipJar — Product Requirements & Progress

## Problem Statement (verbatim intent)
Global community platform "TipJar" where people worldwide post football/sports betting tips.
AI auto-rates each tip; users rate them on a Rate Wall (Apex Scale 1–10). Animated jar + alarm bell
(no-signup alerts). Submit = tutorial or screenshot upload; AI auto-detects teams/time/country/league
and auto-rates. Credits economy (Stripe buy, gift w/ 10% fee, redeem at 10k for real money via PayPal).
Languages: EN, DE (primary), EL, FR, IT. Auto results engine (API-Football Pro) flips Pending->Won/Lost.
Automated betting tips scraped from Forebet/Predictz ("TipJarHQ Picks"). System bets. Player-prop
"Smart Bets" from API-Football stats. USER LANGUAGE = GERMAN (respond in German).

### CHANGELOG 2026-07-11e — Settlement Monitor + CRITICAL system-pick persistence fix
- **CRITICAL FIX:** the startup cleanup (`_startup_seed`) was deleting every pending `hqsys-*` system pick on each backend restart/deploy (id regex only whitelisted hqtip-/hqlive-/smart-/hqcur-). Added `hqsys-` → system picks now survive restarts (verified 6→6). Without this the whole "does a system ever win" tracking silently wiped daily.
- **New admin Settlement-Monitor** (`GET /admin/settlement-monitor` + panel in /insights): live status (OFFEN/GEWONNEN/VERLOREN) of all System picks (hq-system) and first-half (HT) combos, with per-leg breakdown, so the owner can watch auto-settlement in production. Verified via screenshot.

### CHANGELOG 2026-07-11d — System der Stunde uses full Anderlecht 3-leg combo
- The hour-system now bundles the complete **"Über 1.5 Tore 1.HZ + Beide Teams treffen + Über 2.5 Tore"** combo per high-scoring game (total≥4, both score) as ONE selection (combo_markets), odds ~4-9. Persisted as a parlay leg carrying all 3 selections (HT-aware settlement). Up to 2 combo games.
- `snapshot_systems` + Systems.jsx (SystemCard + visible filter) updated to allow single-selection combo systems; combo legs render as ✓-bulleted lines. Verified end-to-end (screenshot: card shows 3 legs @ 8.66).

### CHANGELOG 2026-07-11c — Anderlecht-style hot combo (single-match)
- New single-match bet-builder for goal-heavy games (predicted total ≥4, both teams score): **"Über 1.5 Tore 1. Halbzeit + Beide Teams treffen + Über 2.5 Tore"**, higher odds (~4-9), shown in the **Risk** filter. Persisted as a settleable combo (combo_legs kinds ht_o15/btts/o25).
- Added `ht_o15`/`ht_o25`/`ht_u35` to `_grade_goal_leg` (combo HT settlement). BTTS safety-net fixed to NOT strip the first-half "Über 1.5 Tore 1. Halbzeit" leg (only redundant full-match o15). All leg-grading unit-tested.

### CHANGELOG 2026-07-11b — First-half (HT) settlement + HT markets in System der Stunde
- **New `_grade_ht_selection`**: first-half goal markets (Über/Unter X.5 Tore 1. Halbzeit) now settled deterministically from the half-time score (fixtures carry ht_home/ht_away). Wired into `settle_multimatch_parlays` (falls back to LLM judge for non-HT markets; keeps leg open if HT data missing). Unit-tested, all pass.
- **System der Stunde** now leads with "Über 1.5 Tore 1. Halbzeit" for high-scoring games (the Lyon/Anderlecht style) + safe "Über 0.5 / Unter 3.5 Tore 1. Halbzeit" variants. Total odds still enforced >3.6 (test: 4.94).

### CHANGELOG 2026-07-11 — Best-Won/Cashed bucket + System der Stunde + rating overhaul
- **Rating honesty:** Live picks capped at 7★ (never banker/explosion), BTTS capped 6★, 9-10★ only for ultra-safe pre-match bankers. Value singles now need ≥62% win prob (was 42%); "post everything" fallback removed → fewer but safer picks.
- **BTTS replaced** by favourite-anchored bet-builders: `{Fav} Über 0.5 + Über 1.5 (+ Über 0.5 2.HZ)` and `{Fav} Über 0.5 + Doppelte Chance`. Underdog never required to score.
- **Live picks now show real league** (`_fixture_league_label`), friendlies = "Club Friendlies". Blacklist added: gumi, sportstoto, prievidza, "inter bratislava".
- **Settled counts fixed** (real won/lost/cashed from `/tips/counts`), 100-item cap removed (→1000), 24h purge runs on counts fetch. Won-system picks kept forever.
- **Best Won / Cashed Out bucket:** third settled button is ONE button, visually split into two triangles (gold "Best Won" + blue "Cashed Out"), opens ONE combined view = won Smart/Risk/Community/System picks + cash-outs. Green "Won" = normal AI/Live wins only. New `/tips?source=bestwon|normalwon`, counts `bestwon`/`won_normal`.
- **System picks persisted & auto-settled** (`snapshot_systems`, source=hq-system, is_parlay) so we can see if a system ever wins → surfaces in Best Won.
- **NEW "System der Stunde"** (Το Σύστημα της Ώρας): flash combo ~1h before kickoff, flexible full-match legs (team win/DC/over goals/BTTS), total odds MUST be >3.6, persisted per match-set, i18n in all 8 langs.

### CHANGELOG 2026-07-10 — Admin Pick-Manager + void status
- **Fixed P0:** hanging Frankreich–Marokko Smart Pick `smart-rep-fra-mar` (player props "El Aynaoui 1+ Foul · Doué/Barcola 1+ Schuss · Über 1 Tor") set to status="void" (game over, unresolvable by API-Football).
- **New admin Pick-Manager** in `SecretInsights.jsx` (/insights): `GET /api/admin/pending-tips` returns all open (pending/live) tips grouped by source (Smart Picks/Live-Picks/KI-Picks/Mitglieder-Tipps). Admin can one-tap resolve each pick: Gewonnen/Verloren/Void/Löschen via existing `PUT /api/tips/{id}/status` (now accepts "void") + `DELETE /api/tips/{id}`. Solves recurring issue of custom player-prop picks hanging forever. Tested frontend 100% (iteration_35).

### CHANGELOG 2026-07-09 (night 2) — Curated Smart-Pick reports
- Posted 4 owner WC analysis reports as source="smart" picks (Frankreich–Marokko, Spanien–Belgien, Norwegen–England, Argentinien–Schweiz) — one report card per match, BYPASSING the 48h-fixture requirement (player props / qualify markets have no auto-fixture). Full multi-line German analysis per card. Plus a re-written (not 1:1) "iShowSpeed-Fluch" fun note. Seed: `backend/seed_smart_reports.py`, ids `smart-*` (protected from startup cleanup). match_time="" → dateless, so they do NOT auto-settle (informational reports; remove/settle manually).

### CHANGELOG 2026-07-09 (night) — Bundled AI new-count on main button
- Main "KI Single-Game-Picks" button now shows a red bundled count = SUM of new picks across Banker/Value/Risk, using the SAME `tj_cat_seen_ids` store as the tab badges (App.js `computeAiUnread` + `tj-cat-seen` window event kept in sync with RateWall `markCatSeen`). Opening the AI view marks all categories seen → clears main + tab badges together.
- `/tips/counts` `ai` now counts ALL pending AI picks (singles + combos, all days) so the grey total pill matches the red new-count universe (both = 28 verified).

### CHANGELOG 2026-07-09 (late) — Scraper reactivated (multi-day) + stability
- **AUTOPOST_PAUSED = False** — auto-scraper is LIVE again, but only posts from TOMORROW onward (`_AUTOPOST_MIN_KO` = start of tomorrow UTC). TODAY stays hand-curated (26 hqcur-* picks untouched). Forebet now scrapes today+tomorrow pages (`FOREBET_TOMORROW_URL`); today rows still feed match_predictions/system-slip but are skipped for picks. Predictz already covers tomorrow+day-after.
- **STABILITY RULE:** a pick, once posted for a match+category, is FIXED (same market+odds) until kickoff. Forebet posting replaced the old delete-and-replace (which caused 11:00 Über1.5 → 14:00 BTTS → 17:00 DC12 flipping) with a prior-check: if a pending pick for (home,away,category) exists, keep it. Same prior-check added to Predictz. Verified: 2nd scraper run posts 0 (no flip).
- Verified: today = curated only; tomorrow (2026-07-10) auto picks appear & categorised (Banker/Value/Risk).

### CHANGELOG 2026-07-09 (evening) — Web Push + tip visibility fix
- **Tip visibility fix:** market text no longer truncates (`Paide Handica…` → full `Paide Handicap +2.5`) and the real odds number is ALWAYS shown. For odds < 1.04 a tiny "pregame – live evtl. höher" hint now sits UNDER the number instead of replacing it (OddsValue.jsx + RateWall card row).
- **Web Push (real notifications, app closed / screen off):** VAPID keys in backend/.env; `pywebpush`. Endpoints `/api/push/vapid-public-key|subscribe|unsubscribe`; `notify_all_push` + `_push_payload_for_tip` (game+market details; LIVE picks → blue `/push-live.png` icon). `push_watch_loop` watches new tips (all sources, watermark=now on first run) and pushes. Frontend: bell toggle now also does `pushManager.subscribe` (iOS PWA-install hint), service-worker.js has `push`+`notificationclick` handlers. NOTE: real delivery needs a physical device after deploy — cannot be e2e-tested in this env.
- OPEN: (1) main "KI Single-Game-Picks" button should show bundled red sum of new picks (user approved, NOT built yet). (2) scraper reactivation multi-day + stability rule (awaiting user a/b).

### CHANGELOG 2026-07-09 (P.M.) — Category coverage, tab badges + CRITICAL fix
- **CRITICAL BUG FIXED:** `seed_showcase()` (runs on every startup/deploy) was deleting all TipJarHQ pending tips whose id didn't match `^(hqtip-|hqlive-|smart-)`. The curated `hqcur-*` picks fell through and got wiped on every backend reload/deploy. Regex now includes `hqcur-`. Curated picks survive restarts (verified).
- **Guaranteed categorisation:** every AI single now always lands in Banker/Value/Risk. Generator has an `else → value` fallback; `/api/tips?category=value` is the catch-all (`category NOT IN [banker,risk]`) so no pick can ever disappear.
- **Per-category red badges** (RateWall AI view): Banker/Value/Risk tabs show a one-time red unread count (localStorage `tj_cat_seen_ids`); clicking a tab clears its badge. Reads all AI pending, buckets risk=-1.5 handicap / banker / else value.
- Verified: 18 singles all categorised (11 banker, 6 value, 1 risk) + 8 value combos; badges 11/14/1 render and clear.
- OPEN: scraper reactivation for multi-day + stability rule (awaiting user a/b); Web Push feature (VAPID keys generated, not yet wired).

### CHANGELOG 2026-07-09 — Curated Single-Picks + Category rework
- **Single-Picks categorisation rewritten** (`_forebet_candidates`/`forebet_autopost`): RISK = ONLY favourite -1.5 handicaps; VALUE = sweet-spot 1.40–2.60 tips (Über/Unter, DC12, handicaps) + all bet-builder combos (1.40–3.0); BANKER = safe (winprob≥0.85). Removed duplicate `-hcpf15` generator; `-hcap15` odds calibrated (1.65/1.95/2.60). Predictz tips now carry `category`.
- **CURATED MODE (owner)**: `AUTOPOST_PAUSED = True` in server.py — Forebet/Predictz auto-scrapers do NOT post/overwrite single picks while curated. The Single-Picks feed is a hand-picked list of exact bookmaker (BetScore) legs+odds seeded via `backend/seed_curated_picks.py` (18 singles + 8 bet-builders, 26 total). Astana -1.5 @5.50 = RISK. To resume automation set AUTOPOST_PAUSED=False and re-run scrapers.
- Settlement unchanged & compatible: singles via `judge_market` (LLM, full-time score), combos via `_grade_goal_leg` (deterministic `kind` per leg). NOT yet live-verified (matches settle this evening).
- Frontend: RateWall card badge now shows correct BANKER/VALUE/RISK label+colour (was VALUE/BANKER only).


### CHANGELOG 2026-07-15b — Benachrichtigungen: Flut gestoppt, Deep-Link, Sammel-Alarm + France–Spanien Abrechnung
- **France–Spanien / "qualifiziert sich" abrechenbar:** `_grade_player_leg` rechnet "{Team} qualifiziert sich" jetzt über das Sieger-Flag des Spiels (inkl. Verlängerung/Elfmeter, Tor-Fallback) ab; Fixture-Daten tragen `home_winner`/`away_winner`. Legacy-Legs bekommen `home`/`away` aus dem Tip injiziert. → Der France–Spanien Mega-Builder rechnet sich nach Deploy automatisch ab (sofern noch nicht gepurged).
- **Benachrichtigungs-Flut behoben (Punkt 2):** OS-Pushes nutzten eindeutige Tags (`tj-{id}`) → stapelten sich → endloses Wischen. Jetzt FESTE Tags (`tipjar-pick` / `tipjar-live`) → ein Rückstau kollabiert zu EINER sichtbaren Benachrichtigung (neueste gewinnt).
- **Sammel-Benachrichtigung (Punkt 4):** `push_watch_loop` sendet bei mehreren frischen Picks EINE Digest-Push ("⚡ N neue Picks …") statt vieler einzelner; bei genau einem Pick eine Detail-Push mit Deep-Link.
- **Deep-Link (Punkt 3):** Push-`url` = `/?pick={id}&area={area}`; Service-Worker navigiert dahin; App.js `jumpToPick` öffnet die Ansicht und scrollt/hebt den Pick hervor (`#pick-{id}` Anker + Glow). Verifiziert per Screenshot.
- **In-App-Alarme (Punkt 4):** Jede Toast-Meldung hat jetzt "Pick ansehen" → springt via `tj-open-pick` direkt auf den jeweiligen Pick.
- HINWEIS: Echte OS-Push-Zustellung ist nur auf echten Geräten testbar; Payload/Tag/Deep-Link-Logik ist verifiziert. Greift auf Produktion nach **Deploy**.

### CHANGELOG 2026-07-15 — Auto-Abrechnung für Spieler-Prop Mega-Bet-Builder (Smart Picks)
- Smart Mega-Bet-Builder (Spieler-Props) konnten bisher NICHT automatisch abgerechnet werden → blieben pending & wurden nach 36h gelöscht (nie in Won/Lost). Jetzt gebaut:
  - `_player_stats_for_fixture` holt per-Spieler Match-Stats aus API-Football `/fixtures/players` (Schüsse, Schüsse aufs Tor, Fouls begangen/gezogen, Karten, Tore, Paraden) + Team-Karten-Summen. An echten Daten verifiziert (Villarreal–Atlético, 45 Spieler geparst).
  - `_grade_player_leg` rechnet jedes Leg deterministisch: sot/shots/fouls_c/fouls_d/scorer/card/saves + "Beide Teams eine Karte". "qualifiziert sich" bleibt ungradbar (None) — wird aber vom aktuellen Generator nicht mehr erzeugt. Inkl. Text-Parser-Fallback für Legacy-Märkte ("Mbappé 1+ Torschüsse" etc.).
  - Generierung erhält jetzt `kind`/`player`/`line`/`team` in combo_legs (vorher als "player" überschrieben).
  - `settle_hq_combos`-Query um `source:"smart"` erweitert (verarbeitete vorher NUR hq-auto) — das war der eigentliche Grund, warum Smart-Builder nie abgerechnet wurden.
  - Ziel-Tab nach Abrechnung: Sieg → **Best Won**, Niederlage → **Lost**, Cash-Out → **Cashed Out**.
- Verifiziert: Unit-Tests (strukturiert + legacy) + echter End-to-End-Test (Parlay mit Verlierer-Leg → lost, alle Gewinner → won).
- HINWEIS: greift auf Produktion erst nach erneutem **Deploy**.

### CHANGELOG 2026-07-14 — Best Won / Cashed Out Button lesbar gemacht
- Der diagonale Split-Button schnitt beide Labels an der Diagonale ab. Fix (RateWall.jsx): Farbflächen (beschnitten) und Text (nicht beschnitten) getrennt — "Best Won" oben-rechts, "CASHED OUT" unten-links, beide vollständig lesbar in Ruhe- & Aktiv-Zustand. Button etwas höher (68px). Per Screenshot verifiziert.

### CHANGELOG 2026-07-14 — Alte verlorene WM-Demo-Scheine entfernt
- `seed_showcase` erzeugte bei jedem Backend-Start zwei verlorene Demo-Scheine neu: "Portugal & Messi – Winner & Top Scorer" (WM) und die Häcken/Portugal-Spanien-Kombi → tauchten dauerhaft in der "Verloren"-Sammlung auf. Beide entfernt: Seeding + `upsert` gelöscht, aus `allowed_ids` entfernt und beim Start explizit gelöscht (können nicht wiederkommen). Der gewonnene Schaufenster-Schein "Schweiz–Kolumbien" (Best Won) bleibt. Verifiziert (beide weg, won bleibt).
- HINWEIS: greift auf Produktion erst nach erneutem **Deploy**.

### CHANGELOG 2026-07-14 — Fehl-Ideen im "Eingegangene Ideen"-Feed entfernt (Screenshot-Klärung)
- Die 2 "blanken" Ideen waren KEINE textlosen Einträge, sondern Fehl-Einreichungen mit Text aber Status "not_actionable"/"no_fixture" ("KEIN TIPP" / "KEIN SPIEL GEFUNDEN"), z. B. Test-Text + alte iShowSpeed-France-Marokko-Notiz. Der Feed zeigte diese noch an.
- Fix: `recent_smart_ideas` liefert jetzt NUR Ideen mit `status="used"` (Ideen, die tatsächlich zu einem Smart Pick wurden). `_cleanup_smart_junk` löscht zusätzlich alle smart_ideas mit `status != "used"`. Per Testseed verifiziert (used bleibt; not_actionable + no_fixture gelöscht; Feed = nur used).
- HINWEIS: greift auf Produktion erst nach erneutem **Deploy** — dann verschwinden die 2 Fehl-Ideen automatisch beim Backend-Start.

### CHANGELOG 2026-07-14 — Refactor Stufe 1: Pydantic-Modelle ausgelagert (verhaltensneutral)
- Alle 15 Request-Modelle (RegisterInput, LoginInput, TipSaveInput, GiftInput, CheckoutInput, StatusInput, SmartIdeaInput, IdeaRateInput, VisitInput, PushSubIn …) aus `server.py` in neues `backend/models.py` verschoben; `server.py` importiert sie oben. Rein organisatorisch, KEINE Logikänderung. server.py 5947 → 5863 Zeilen. Per curl verifiziert: login, /auth/me, /tips/counts, /tips?source=smart, /systems, /credits/packages, /push/vapid-public-key, /track/visit, register-Validierung (422) — alle OK. Frontend lädt e2e.
- OFFEN (P1, größere Folge-Stufen, jeweils mit Tests): Config/Infra → core.py; danach Domain-Splits (auth, tips, credits, wins, engine/scraper, smart/systems) in eigene Router-Module.

### CHANGELOG 2026-07-14 — Blanke Smart-Ideen verhindert + alte Reports (France–Marokko) auto-gelöscht
- **Blanke "Eingegangene Ideen" behoben (Root-Cause):** `submit_smart_idea` legte den öffentlichen Feed-Eintrag SOFORT an — auch bei reinen Bild-Uploads ohne Text → blanke Karte (@user + Bild-Icon, kein Inhalt). Fix: Feed-Eintrag wird nur noch bei echtem Text (≥6 Zeichen) erstellt; Bild-only-Einreichungen werden weiter zu einem Pick verarbeitet, erzeugen aber KEINE blanke Feed-Karte. Per curl verifiziert (Bild-only → created:false, Feed bleibt leer).
- **Startup-Cleanup `_cleanup_smart_junk()`** (läuft bei jedem Start, inkl. Produktion nach Deploy): (1) löscht blanke `smart_ideas` (Text leer/nur Whitespace/None); (2) löscht alte Smart-**Report**-Picks (report=True, älter als 3 Tage) + alle `status:void` Smart-Picks → entfernt fertige Karten wie France–Marokko. Frische Reports (<3 Tage) bleiben erhalten. Per Testseed verifiziert (fra-mar 5d → gelöscht, frischer Report → bleibt, 2 blanke Ideen → gelöscht).
- HINWEIS: Die 2 blanken Ideen + France–Marokko liegen auf PRODUKTION → verschwinden automatisch nach **Deploy**.

### CHANGELOG 2026-07-11f — Mega Bet-Builder (Smart Picks) UI-Fix VERIFIZIERT
- Alle Spieler-Props eines Matches werden zu EINEM massiven "Mega Bet-Builder" gebündelt (Fouls/Schüsse/Schüsse aufs Tor + Über 8.5 Ecken), Frankreich-Picks + die zwei obersten Fehl-Meldungen entfernt (Backend `smart_autopost`).
- **BUGFIX:** `smart_autopost` befüllte nur `combo_legs`, ließ `legs: []` leer → Frontend (RateWall) rendert `tip.legs` und zeigte daher nur die Titelzeile statt der 7 Props. Fix: `smart_autopost` befüllt jetzt zusätzlich `legs` (ein Display-Leg mit `match` + allen `selections`/`sel_odds`), analog zu AI-Bet-Buildern. Bestand-Pick per Backfill migriert. Per Screenshot verifiziert (Argentina–Switzerland, 7 Legs @3.97, sauberes Layout, kein Clipping).

## Tech Stack
FastAPI + MongoDB (motor) + React (CRA/craco) + Tailwind. framer-motion, canvas-confetti, lucide-react.
AI: Gemini 3.1 Pro via emergentintegrations (EMERGENT_LLM_KEY). Payments: Stripe (test). Object storage:
Emergent. Auth: JWT Bearer. Scrapers: Playwright/Chromium (forebet.py, predictz.py). Results + player
stats: API-Football Pro (api-sports.io, 7500 req/day, season stats available).

## Personas
Tipster, Rater, Anonymous visitor (bell), Admin (settles tips).

## Current areas (tips window tabs + header quick-views)
Order (left→right): 1) KI Single-Game-Picks (ai, source=hq-auto) 2) Smart Bets (smart) 3) KI-System-Picks (systems) 4) Community (members) 5) Live 6) Abgerechnet (settled).
1. KI Single-Game-Picks (source=hq-auto) — Forebet/Predictz bankers/value + dynamic single-game multi-leg Bet-Builders (both teams score + nested Über-lines, 1-goal safety buffer).
2. Smart Bets (source=smart) — player props from API-Football season stats.
3. KI-System-Picks (GET /api/systems) — 4 systems: lock / value / risk / gamble.
4. Community Picks (source NOT in [hq-auto, smart]).
5. Live Picks (status=live) — realistic Poisson-priced live odds (goals-needed + time-remaining).
6. Abgerechnet/Settled — checkered-flag tab; Won(left)/Lost(right) clickable toggles reveal slips on click; settled slips auto-deleted after 24h.

## Key backend endpoints
- GET /api/tips?source=ai|smart|members&status=pending|won|lost|live&window=24|48|48plus&sort
- GET /api/tips/counts -> {ai, ai_total, members, live, systems, smart, settled}
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

## Session 2026-07-08 (fork continued)
- Smart Bets "idea chatbox" (SmartLab): logged-in users send an insider hint (text + up to 3
  optional images) → POST /api/smart/idea (multipart) → Gemini turns it into a clever Smart Pick.
  MUST have a real kickoff: find_upcoming_fixture() via API-Football; only posts if a fixture is
  found AND kickoff is within 48h (else created:false, reason no_fixture/too_far/not_actionable).
  Homepage SmartX quick-view button has a pulsing spoiler badge "Mit der KI reden". Tested
  iteration_33/34 PASS + 48h window verified (El Clásico 25/10 → too_far).
- Blacklists: Blumenau + code `brc`; Canadian Championship (`forge`, `saint-laurent`); ~30 obscure
  Brazilian leagues (Série C/D, all A1/A2/A3 state tiers, Paulista/Carioca/Mineiro/Catarinense/etc.).
  Only Brazil Série A/B kept. Owner shorthand: "#<team> @blacklist" = delete tip + blacklist league.
- Dynamic single-game Bet-Builder: both teams score + nested Über-lines (1-goal safety buffer,
  up to 5 legs). Generic Über-line settlement (parse "über N.5"). Combo odds cap raised to 25.0.
- Multi-match parlay auto-settlement: settle_multimatch_parlays() grades each leg via API-Football +
  judge_market; lost if any leg loses, won if all win; writes per-leg status. In loop + /admin/settle-now.
- Settled area "Abgerechnet": new tab (checkered-flag), Won(left)/Lost(right) toggles reveal slips on
  click; purge_settled_tips() deletes non-seed won/lost tips >24h; set_status stamps settled_at.
  counts now include `settled`. Tested iteration_31 (columns) + iteration_32 (toggles) — PASS.
- Renamed AI Picks -> "KI Single-Game-Picks"; tab order: ai, smart, systems, members, live, settled.
- Removed fake `seed-community-pending` showcase (used real UPCOMING fixtures w/ fabricated results).
- LIVE odds fix: _live_odd now Poisson-based on goals-needed + time-left (Über 1.5 @45'/0:0 = ~2.21,
  was 3.75). Callers pass current total goals.


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

## Changelog — 2026-07-08 (2er-Bet-Builder + Fixes nach Test iteration_30)
- 2ER-KOMBI (KI): _forebet_candidates erzeugt Combo (schwaches Team Über 0.5 + Über 1.5 Tore) bei pred 1/2, weak_scores, total>=3. forebet_autopost bevorzugt Combo (höheres Risiko), sonst value/banker. Tip: is_parlay + 2 legs (kind team_o05/o15), erscheint im KI-Bereich. Neue settle_hq_combos() rechnet 2er-Kombis deterministisch aus Endstand ab (im settlement_loop + /admin/settle-now). Unit-getestet: Generierung, Anzeige, Abrechnungspfad.
- FIX (CRITICAL, iteration_30): POST /api/tips/analyze `files`-Feld gab 422 (Optional[List[UploadFile]]). Auf List[UploadFile]=File(default=[]) geändert → Mehrbild-Upload (bis 4) funktioniert.
- ENTFERNT: rohes Buchmacher-Bild auf Tipp-Karten (RateWall) — Regel „keine Rohbilder".
- Test iteration_30: Pflicht-Sterne (400/200), KI-Sort nach Anstoß, Share-Bild, Community-Rename, Publish-Sperre, kein Rohbild → alle PASS.

## Changelog — 2026-07-08 (Slip v2, Sterne-Pflicht, 4 Bilder, LIVE-Badge, KI-Sort)
- SLIP v2: volle Team-Namen (Auto-Shrink + 2-zeiliger Umbruch statt "…"), größere Schrift, Wasserzeichen gedeckelt (kein Clipping), roter LIVE-Kasten mit Minute+Ergebnis. Bugfix: Live-Community-Schein zeigte "WON" → jetzt OFFEN (ctype live_pending).
- LIVE-BADGE ÜBERALL: neuer live_annotate_loop (90s) setzt live_state{minute,score} auf jeden nicht-beendeten Einzeltipp, dessen Spiel laut API-Football läuft (sonst clear). RateWall-Karte zeigt roten LIVE-Kasten. KEINE Kanal-Verschiebung mehr — Live-Kanal = beim Posten bestimmt (create_tip, is_live_post via API-Football, alias-fähig Deutschland=Germany).
- STERNE-PFLICHT: create_tip verlangt self_rating 1–10 (sonst 400), speichert es als Eigen-Rating (tip_ratings + avg). SubmitTipModal: StarRating-Block, Publish gesperrt ohne Sterne.
- 4 BILDER: /tips/analyze nimmt bis zu 4 Files (analyze_tip mit mehreren ImageContent), speichert image_paths. Modal: Vorschau-Grid, entfernen, "Up to 4 images".
- KI-SORT: Single-KI-Bereich (source=ai) nach Anstoßzeit sortiert (nächstes Spiel zuerst), außer bei sort=top/hype. Verifiziert.
- Settle-Engine deckt Live-Einzeltipps ab. Dedup behält höchstes Risiko (Alias/gleicher Anstoß).

## Changelog — 2026-07-08 (Auto-Live für Einzel-Tipps zurück + Alias-Match)
- SOFORT: Ukraine (U-19) vs Germany (U-19)-Member-Schein auf Produktion nach Live verschoben (Admin-API).
- ROOT CAUSE: Auto-Live-Loop war komplett entfernt → einzelne live gepostete Scheine blieben in Community. Zusätzlich matchte _find_live_fixture keine Aliase (Deutschland≠Germany).
- FIX: member_live_loop wieder aktiv, aber NUR für Einzel-Tipps (is_parlay != True) → laufende Einzelwetten gehen automatisch nach Live (via API-Football, zuverlässig), Parlays (7er-Kombi) bleiben in Community. _find_live_fixture jetzt alias/sprach-fähig (Deutschland==Germany, via _team_core). Getestet: Einzel→live, Parlay→pending PASS.
- Braucht Redeploy für automatische Wirkung auf Produktion.

## Changelog — 2026-07-08 (Slip-Redesign, Community-Rename, Dedup, Live-Fixes)
- SLIP-BILD komplett neu (_render_slip_image): Liberation Sans (behebt Tofu-Kästchen bei €/ö/–), viel größere Schrift, TipJar-Crest als dezentes Hintergrund-Wasserzeichen, 1080px breit, sauberes Layout. Visuell verifiziert (Community + Live).
- BEREICHS-PILL auf geteilten Scheinen: "COMMUNITY PICK" (pending) / "LIVE PICK" (live). Bugfix: Live-Community-Schein wurde fälschlich als "WON"/grün gerendert → jetzt ctype "live_pending" (OFFEN/volt). tip_share_image rendert immer frisch (kein Cache) und setzt ctype nach Status.
- UMBENENNUNG "Mitglieder-Picks" → "Community Picks" (nav.viewmembers + bell.* in allen 8 Sprachen). Frontend verifiziert.
- DEDUP robuster (_dedupe_hq_tips): erkennt dasselbe Spiel auch bei Namensvariante (gleicher Anstoß + gleiches Heim ODER Auswärts, z.B. "Orange County SC" vs "Blues"), behält den HÖCHSTEN RISIKO-Pick (Value > Quote). Neuer Helper _team_core. Getestet: Hartford-Fall → Über 1.5 @1.20 bleibt, Über 0.5 @1.10 entfernt.
- LIVE-KLASSIFIZIERUNG nur noch beim Posten (create_tip: _looks_live_now + API-Football-Live-Check). Hintergrund-Promotion-Loop ENTFERNT → pregame-Scheine (z.B. 7er-Kombi) bleiben in Community. Settle-Engine deckt jetzt auch Live-Einzeltipps von Mitgliedern ab.

## Changelog — 2026-07-08 (Live-Erkennung robust via API-Football)
- ROOT CAUSE: Slip-Kickoff-Strings tragen keine Zeitzone ("18:00" als UTC gelesen → Spiel wirkt zukünftig). member_live_sync verschob CEST-Live-Spiele daher nicht.
- FIX: member_live_sync konsultiert jetzt zusätzlich API-Football (/fixtures?live=all) via _find_live_fixture → zuverlässige Live-Erkennung unabhängig von der Slip-Uhrzeit. Nur vom Loop selbst verschobene Tipps (live_auto=True) werden je auto-zurückgesetzt; manuell (Admin) verschobene bleiben live. Getestet: TZ-verschobenes Live-Spiel → korrekt nach Live (live_auto); manueller Live-Tipp bleibt.
- Braucht Redeploy: Produktion lief noch mit zeitbasierter Version (Olympiakos blieb bei Mitgliedern).

## Changelog — 2026-07-08 (Auto-Live-Loop + KI-Live-Picks)
- MEMBER AUTO-LIVE: neuer member_live_loop (alle 3 Min) verschiebt eingereichte Member-Tipps automatisch nach Live, sobald ihr Spiel läuft (_looks_live_now), und nach Spielende zurück auf pending (damit die Auto-Abrechnung greift). Getestet (pending→live→pending PASS).
- KI-LIVE-PICKS: live_autopost erzeugt jetzt zusätzlich FRISCHE Live-Goal-Picks (Über 1.5/2.5) für laufende Spiele (Minute 10–80, Stand 0-0/1 Tor) mit echter Torgefahr (_live_pressure_ok). Quota-Guard LIVE_STAT_CALL_CAP=20/Run. Verifiziert: 19 Live-Spiele → 8 Picks gepostet (u.a. Olympiakos vs Raków Über 1,5 @ 3,75), rendern korrekt im Live-Kanal mit LIVE-Badge + Teilen.
- Admin "→ Nach Live"/"→ Nach Offen" Button (PUT status akzeptiert live). i18n wall.toLive/toPending in 8 Sprachen (Bugfix: fehlender el-Eintrag + verirrtes i18n.js-Fragment am Dateiende entfernt).

## Changelog — 2026-07-08 (Admin: Tip nach Live/Offen verschieben)
- PUT /api/tips/{id}/status akzeptiert jetzt auch "live" (vorher nur won/lost/pending).
- RateWall: Admin-Button "→ Nach Live" / "→ Nach Offen" auf Member-Tip-Karten (data-testid admin-tolive-{id}). i18n wall.toLive/wall.toPending in allen 8 Sprachen.
- Zweck: einzelne Member-Picks manuell in den Live-Kanal schieben (z.B. Olympiacos-Pick d432a864 auf Produktion). Preview getestet (curl live<->pending). Produktion braucht Redeploy, dann Verschiebung per API/Button möglich.

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


## Changelog — 2026-07-09 (Logo, Live-Settlement-Rootfix, Bewertungswand, Cashed-Out)
- Header-Logo: "TipJar" (Tip weiß / Jar mint) mit "GLOBAL" (orange) direkt darunter, leicht links (Team-Foto-Look). Hero-Shield: klickbarer Link "Tipjarglobal.com" (mint, glow) unter dem AnimatedJar.
- ROOT-FIX Live-Picks blieben ewig im Live-Bereich: `_parse_kickoff()` konnte ISO-Datum (`...T22:00:00+00:00`) nicht parsen → ko=None → zeitbasierte Abrechnung feuerte nie. ISO-8601-Parsing ergänzt. Zusätzlich `live_autopost`-Sweep: überfällige (>3.5h, LIVE_MAX_OPEN_HOURS) oder terminale (PST/CANC/ABD) Live-Picks werden zwangs-abgerechnet/void statt behalten. LIVE_STATUSES-Set eingeführt. Verifiziert (closed:2 bei Testfällen).
- Bewertungswand zeigt nur noch OFFENE Scheine: Won/Lost-Filter-Tabs aus der Wand entfernt (nur Pending + Live). Abgerechnete Scheine leben ausschließlich im "Abgerechnet"-Tab.
- NEU Status "cashed_out" (Ausgezahlt): wiederverwendbar, setzbar von Admin UND Ersteller (PUT /tips/{id}/status jetzt get_current_user + owner/admin-Check, 403 sonst). Hellblaues "CASHED OUT"-Badge; jedes Leg zeigt grünes "Gewonnen". Dritter Toggle im Abgerechnet-Tab (hellblau). Erscheint auch in Hall of Fame (type "cashed", aus tips-Collection gemappt). NICHT im 24h-Purge (bleibt als Trophäe). counts.settled inkl. cashed_out. i18n EN+DE ergänzt. E2E verifiziert (owner=erlaubt, non-owner=403, HoF zeigt 'cashed').
- FIX (2026-07-09b) Cashed-Out-Claim war im Upload-Formular NICHT wählbar (WinClaimModal TYPES hatte nur played/posted/live) → Nutzer landete zwangsweise im "nur GEWONNEN"-Zweig, Ablehnung. Behoben: 4. Button "Ausgezahlt" (Banknote) ergänzt, grid-cols-2. Zusätzlich Backend-Härtung: played/posted-Branch akzeptiert jetzt auch slip status "cashed" (ohne System-Match-Zwang, WIN_CASHED_CREDITS=20), egal welcher Typ gewählt wurde. E2E: Button rendert, Beschreibung + Upload sichtbar (Admin-Token injiziert).
- FEATURE (2026-07-09c) ECKEN-MÄRKTE (Corners) im Bet-Builder + Single-Picks. Generierung (`_forebet_candidates`): Poisson-Modell auf geschätztem Ecken-Erwartungswert `corner_lam = clamp(6.5+1.4*lam, 7..14)`; Single-Lines Über 7.5/8.5 & Unter 10.5/11.5 Ecken, plus Corner-Bet-Builder "Über 1.5 Tore + Über 8.5 Ecken" (kind `corner_o`). Settlement: NEU deterministisch aus API-Football `/fixtures/statistics` — `find_finished_fixture` liefert jetzt `fixture_id`; `_corner_total_for_fixture()` summiert Ecken via `_live_stat_totals`; `_grade_goal_leg` versteht `corner_o/corner_u` (Über/Unter X.5, None wenn keine Statistik). `settle_pending_tips` routet Ecken-Singles deterministisch (statt LLM judge_market), `settle_hq_combos` holt Ecken-Total wenn ein Leg Ecken enthält. Frontend i18n `localizeMarket`: dynamische Ecken-Lines → EN "Over/Under X.5 Corners", DE "Über/Unter X.5 Ecken" (keys mkt.ovr/und/corners in EN+DE, Fallback EN). Kuratierte Corner-Builder in seed_curated_picks.py (CORNER_COMBOS, id-Präfix hqcur-cc-, 3 Stück: Dynamo Kyiv, Qarabag, Sheriff). VERIFIZIERT: Generierung (unit), Grading (unit: 11 Ecken → Über 8.5=won/Unter 11.5=won/keine Stats=None), echte API-Football Ecken-Abfrage (corners=5), Rendering im Value-Tab (auto Shandong-Karte + kuratierte), EN-Localisierung "Over 8.5 Corners". LIMIT: obskure Ligen ohne Ecken-Statistik → Leg settelt nicht (settle_attempts cap 4).
- FIX (2026-07-09d) SMART-LAB nahm Bild-Einreichungen (Bet-Builder / Kombi-Scheine / Analyse-Sheets) NICHT an und hinterließ leere Posts. Ursachen: (1) submit_smart_idea verlangte ZWINGEND eine reale API-Football-Fixture ≤48h → WC-/fiktive Spiele wurden abgelehnt (no_fixture/too_far), (2) die Idee wurde VOR der Prüfung gespeichert → blanke Waisen-Einträge im "Eingegangene Ideen"-Feed. Behoben: submit_smart_idea postet jetzt IMMER einen Smart-Pick, wenn die KI Team+Markt erkennt — Fixture nur noch optional für die Anstoßzeit; ohne nahe Fixture wird als REPORT (report=True, KEINE Auto-Abrechnung) gepostet, wie die kuratierten WC-Analysen. Bild-only-Einreichungen ohne Ergebnis werden gelöscht (kein blanker Waise). recent_smart_ideas filtert leere Texte raus → nie wieder blanke Karten. settle_pending_tips schließt report-Tips aus (`report:{$ne:True}`). generate_smart_from_idea liest jetzt Datum vom Screenshot, fasst Bet-Builder-Legs zu EINEM Markt zusammen (' · '), akzeptiert leniente. VERIFIZIERT: echtes France-v-Morocco-Bet-Builder-Bild via API → created:true, Markt "El Aynaoui 1+ Foul · Doué 1+ Schuss · Barcola 1+ Schuss · Über 1 Tor" + volle DE-Analyse, report:true. HINWEIS: die 3 blanken Posts des Nutzers liegen auf PRODUKTION (Preview hatte keine) — nach DEPLOY werden sie durch den Feed-Filter ausgeblendet.
- FIX (2026-07-09e) GEWINN-SCHEIN-BILD (`_render_slip_image`) war zu hoch/luftig → Schrift wirkte auf dem Handy winzig, Schein zu breit, Abstände zu groß. Kompaktiert: head_h 258→212, foot_h 440→344, mrow_h 106→76, gap 40→22, sub_h 62→46, Titelzeilen-Abstand +34→+16; Fonts leicht reduziert (logo 110→92, big 124→96, footer-Labels). Footer-Layout enger neu gesetzt (passt jetzt sauber in die Card). WON-Badge-Padding korrigiert (war rechts abgeschnitten). VERIFIZIERT: 6-Leg- und 3-Leg-Schein gerendert & visuell geprüft — dicht, lesbar, Unterzeile (Liga·Datum·Zeit) vollständig, Badge komplett sichtbar.
- FIX (2026-07-09f) (1) BTTS-BET-BUILDER schrieb "beide Teams treffen" als zwei Einzel-Legs "{Team} Über 0.5 Tore" + teils redundantes "Über 1.5 Tore". Owner-Regel: nur "Beide Teams treffen" und mehr nicht. Block (c) in _forebet_candidates umgebaut: EIN sauberes btts-Leg; reines BTTS (total=3) → als SINGLE "Beide Teams treffen" (kein 1er-Kombi); höhere Totals → "Beide Teams treffen + Über X.5 Tore (Ner-Bet-Builder)" (nur NICHT-implizierte Over-Lines ab 2.5). Verifiziert per Generierung. (2) RISK-Single "Dinamo Tirana vs Astana — Astana Handicap -1.5 @5.50" war unsichtbar: durch mein seed_curated-Rerun war match_time=None → fiel aus dem Default-Fenster "Next 24h". Fixture aufgelöst (09/07/2026 19:00 UTC, ECL, NS), Live-Record repariert + seed_curated_picks.py mit META_OVERRIDE gehärtet (kein None mehr). Verifiziert per Screenshot im Risk-Tab. HINWEIS: kuratierte Picks liegen NUR in der DB (nicht im Code) → Produktion braucht die Picks in ihrer eigenen DB; Code-Änderungen (BTTS, seed) greifen erst nach Deploy.
- FIX+FEATURE (2026-07-09g) ABRECHNUNG-ROBUSTHEIT + STERNE-SYSTEM. (a) Spiele die seit ~2h zu Ende waren blieben "offen": Root-Cause = Produktion läuft mit 2 Replicas → beide fahren dieselben Background-Loops → 2× API-Football-Calls (Quota-Exhaustion über 7500/Tag) und 2× settle_attempts → der aggressive Cap 4 (=~1h bei 15-Min-Loop, ~30 Min bei 2 Replicas) wurde erreicht bevor API-Football FT publizierte. Fix1: SETTLE_MAX_ATTEMPTS 4→24 (~6h Retries). Fix2: Mongo-basierte Single-Leader-Lease (`system_locks.bg_leader`, TTL 90s, `_leadership_loop` renewt alle 30s, FAIL-OPEN) — nur EINE Replica fährt settlement/forebet/predictz/smart/live/member_live/push_watch-Loops (`if not _is_leader(): continue`). Halbiert API-Verbrauch, verhindert Doppel-settle_attempts & Doppel-Push. Verifiziert: Lock gehalten von Server-Prozess, Loops laufen. (b) STERNE statt Prozente: ai_rating kommt jetzt aus win_prob (stars=clamp(1,10,round(win_prob*10))) → 8.5-Cap weg, ≥96%→10★, 90%→9★. (c) Owner-Regel: JEDER Single-Pick mit win_prob≥0.90 → Banker (vor Value-Check in _forebet_candidates-Kategorisierung). (d) Prozente entfernt: ≈X%-Badge aus RateWall raus + bestehende ai_analysis-Prosa bereinigt (7 Picks, "ca. NN% Trefferchance"→"N/10 Sterne"), neue Analysen ohne %. (e) NEU AiRatingStars.jsx: ai_rating als 1-10 Sterne; 10★ = explodierende Partikel-Animation (ExplosionBurst, framer-motion), 9★ = flammende Aura (FlameAura, orange). Ersetzt die AI-Zahl im Card-Footer. Bestehende Picks re-kategorisiert (≥90%→banker) + re-rated aus win_prob (31 Picks). VERIFIZIERT per Screenshot: 10★ (volt) + 9★ (orange+Flammen), kein %-Badge mehr.
- REFINE (2026-07-09h) Banker-Regel an Sterne gekoppelt + Produktions-Daten-Migration. (1) Kategorisierung nutzt jetzt `round(winprob*10) >= 9` (statt win_prob≥0.90) → JEDER 9- oder 10-Sterne-Single → Banker. (2) `-1.5`/`-1,5` Handicap-Singles → immer Risk. (3) NEU `_migrate_stars_and_categories()` läuft in `_startup_seed` (idempotent, auch auf Produktion): re-ratet ai_rating aus win_prob (≤10), verschiebt 9/10★-Singles → Banker, -1.5-Handicaps → Risk, und strippt "ca. NN% Trefferchance"/"(Value ≥1,60)" aus bestehenden Analyse-Texten. WICHTIG: Grund für "nach Deploy nix geändert" war, dass bestehende Produktions-Picks alte Daten (Kategorie/Rating/%-Text) hatten — nur der Frontend-Code (Sterne, kein %-Badge) war live. Migration zieht die Bestandsdaten beim Start nach. VERIFIZIERT: 0 Picks mit %-Text, Sternverteilung 2–10, 0 von 9/10★ in Value, alle 3 -1.5-Handicaps (Astana/Sheriff/Qarabag) in Risk.
- REFINE (2026-07-09j) Owner-Regel: wenn "Beide Teams treffen" Teil eines Bet-Builders ist, muss "Über 1.5 Tore" RAUS (redundant, BTTS garantiert bereits ≥2 Tore). Migration `_migrate_stars_and_categories` erweitert: beim Zusammenführen der team_o05-Legs zu einem btts-Leg wird jede o15/"Über 1.5 Tore"-Leg entfernt, Gesamtquote + market + combo_legs + Display neu berechnet. Über 2.5+ bleibt erhalten (nicht impliziert). VERIFIZIERT: BTTS+Über1.5 → "Beide Teams treffen" @1.69 (1 Leg btts); BTTS+Über2.5 → "Beide Teams treffen + Über 2.5 Tore" @3.38 (btts+o25). Neu-Generierung war bereits korrekt (fügt nie Über 1.5 zu BTTS hinzu).
- FEATURE (2026-07-09k) GEHEIMER BESUCHERZÄHLER (nur Admin). Backend: `POST /api/track/visit` (anonym, cookiefrei — visitor_id = zufällige localStorage-ID; deduped pro Besucher/Tag via upsert in `visits`-Collection → hits + unique). `GET /api/admin/visits` (require_admin, 401 für alle anderen): total/today/week unique+hits, 14-Tage-Verlauf, members, subscribers. Frontend: App.js pingt beim Laden einmal pro Session (sessionStorage-Guard). NEU SecretInsights.jsx unter Route `/insights` — KEIN Link irgendwo in der UI, zeigt für Nicht-Admins "Nichts zu sehen hier", für Admin ein Dashboard (Heute/7T/Gesamt-Besucher, Registrierungen, Push-Abos, 14-Tage-Balkenchart). VERIFIZIERT: Tracking zählt unique+hits, /admin/visits 401 ohne Admin, /insights rendert für Admin (Screenshot). Kein Visitor-Tracking existierte vorher.
- FEATURE (2026-07-09l) PUSH-OPT-IN-PROMPT (Conversion). Dezentes Banner (NotificationPrompt.jsx) gleitet 2,5s nach dem ersten Öffnen einer Picks-Ansicht hoch (Trigger: `tj-viewed-pick` Event aus openTipsView). Einmalig, dismissbar ("Später"/X → localStorage tj_push_prompt_dismissed). Gated: nur wenn Web-Push unterstützt, Notification.permission != 'denied', tj_bell != '1' (nicht schon an), nicht iOS-ohne-PWA. "Aktivieren" → pushClient.js `enablePushFull()` (permission + /notifications/subscribe + /push/subscribe VAPID) → dispatcht `tj-push-enabled`, NotificationBell hört darauf und setzt on=true. i18n EN+DE (push.prompt.*). Wired in App.js Home. VERIFIZIERT: kompiliert fehlerfrei, Gating korrekt (Headless-Browser=permission denied → korrekt nicht angezeigt); echte Sichtprüfung auf Gerät mit permission=default steht aus (Headless erzwingt denied).
- FEATURE (2026-07-09m) NOTIFICATION-SOUNDS + gezielte High-Impact-Pushes + Abo-Boost.
  (1) COIN-SOUND: neue Assets in public/ (coin.wav, coin_explosion.wav=Münze+kleine Explosion, coin_fire.wav=Münze+Feuerknistern; per numpy synthetisiert). Neues Modul src/coinSound.js `playCoin(kind)`. NotificationPrompt.jsx spielt Coin-Ding beim Hochgleiten des Opt-in-Prompts. Bei eingehendem Push (Vordergrund) postet der Service-Worker `{type:'tj-push-coin', sound}` an alle Clients; index.js hört darauf und spielt den passenden Sound. Autoplay-Blockade wird still geschluckt (NotAllowedError catch).
  (2) SOUND-MAPPING nach Sternen (round(win_prob*10)): 10★→'explosion' (Münze+Explosion), 9★→'fire' (Münze+Feuer), sonst→'coin'. Live-Picks bekommen 'explosion' ab 9★.
  (3) GEZIELTE PUSH-TITEL in `_push_payload_for_tip`: hq-auto Banker 10★ → "💥 10-Sterne-Banker!", Banker 9★ → "🔥 9-Sterne-Banker!". Payload trägt jetzt `sound`-Feld. Live bleibt "🔵 LIVE-Pick".
  (4) ABO-BOOST auf ALLE öffentlichen Endpoints ausgeweitet: `_sub_boost()` (+140 bis 2026-09-09, danach 0) jetzt auch in /api/stats (subscribers), /api/notifications/stats (subscriber_count) und /notifications/unsubscribe — vorher nur /notifications/subscribe. Insights-Dashboard bleibt roh (echte Zahl). VERIFIZIERT via curl: /api/stats subscribers=141 (real 1 +140), /notifications/stats=141.
  VERIFIZIERT: Backend-Syntax OK + läuft; Payload-Logik-Test (0.97 banker→10★/explosion/💥-Titel, 0.90→9★/fire/🔥, 0.75→coin); Frontend kompiliert; alle 3 Audio-Assets liefern HTTP 200; Homepage lädt. HINWEIS: tatsächliche Audio-Wiedergabe ist autoplay-policy-/interaktionsabhängig → finale Ohrenprobe am echten Gerät durch Nutzer. Produktion braucht Re-Deploy.
- FEATURE/FIX (2026-07-09n) LIVE-FRÜH-ABRECHNUNG + Mitglieder-Boost + Produktions-Diagnose.
  (1) LIVE EARLY-SETTLE: in `live_autopost()` (Abschnitt 1) werden Over-/BTTS-Live-Picks jetzt SOFORT mitten im Spiel als "won" nach Abgerechnet verschoben, sobald `_live_bet_landed(...) is True` (unumkehrbar, da Tore nur steigen) — kein Warten mehr auf FT. Fügt vor dem "in-play weiterlaufen"-Zweig eine Prüfung ein (settled_by="auto-live-early", schreibt final_home/away + live_score/minute). VERIFIZIERT: admin/live-run schloss 4 laufende Picks korrekt (Vllaznia 2:1 Über2.5 @65', CSKA 3:1 @64', Glentoran 1:1 Über1.5 @45', Petrovac 1:1 @37').
  (2) MITGLIEDER-BOOST: neue Konstante MEMBER_DISPLAY_BOOST=400 (+`_member_boost()`, läuft bis 2026-09-09 aus) auf /api/stats `members` addiert (Homepage-Fortschrittsbalken InviteSection). VERIFIZIERT: /api/stats members Preview 76→476 (Prod real ~22→422). Insights-Dashboard bleibt roh.
  (3) DIAGNOSE-ENDPOINT: neuer GET /api/admin/live-health (require_admin) meldet in EINEM Call: api_football_key_set, is_leader, hq_account_exists, current_live_tips, pending_prematch_tips, API-Football /status (http/errors/requests/plan) und live=all results. Zweck: Produktions-Ursache für "keine Lives" bestimmen ohne Log-Zugriff. JETZT AUCH als mobiles Panel oben in SecretInsights.jsx (/insights) mit Klartext-Verdikt (grün/rot) — Nutzer ist am Handy, kann keine Konsole nutzen. VERIFIZIERT: Panel rendert auf Preview /insights, Verdikt "✅ Alles ok", zeigt Key gesetzt/Pro/1412 Requests, 14 live, Leader=true, 6 Live-Picks, 31 Vor-Spiel-Picks.
  LEADER-LOCK ANALYSE: Preview zeigte kurz is_leader=false — Ursache war ein abgelaufener Lock eines toten Reload-Workers; heilt sich in ≤30s selbst (nach 35s is_leader=true). Kein Produktions-Blocker. Leader-Logik funktioniert.
  OFFEN (Produktion, nur mit Env-Zugriff lösbar): "keine Live-Picks den ganzen Tag" auf tipjarglobal.com. Hauptverdacht: API_FOOTBALL_KEY fehlt/ungültig in der Deployment-Umgebung (Live braucht API-Football; Vor-Spiel-Picks per Scraper laufen ohne). Nächster Schritt: nach Re-Deploy /api/admin/live-health auf Produktion auswerten.

## Offene Punkte / Hinweise
- Produktion (tipjarglobal.com) läuft mit ALTEM Code bis Nutzer erneut deployt → verschwundener 7-Leg-Community-Schein war auf Produktion (eigene DB, kein Zugriff, nicht wiederherstellbar). Nutzer muss DEPLOY klicken, damit Live-Settlement + Bewertungswand-Fix + Cashed-Out live gehen.
- Live-Bereich zeigt viele obskure US-Amateurligen — evtl. striktere Liga-Whitelist für Live-Loop gewünscht (offen).


## Changelog — 2026-07-09 (Realistische Tor-Quoten via Poisson)
- Owner spielte Single-Picks real bei BetScore nach → Schätzquoten waren „extrem falsch". Fix: neue `_pois_line_odds(lam, line, over, margin=0.95)` berechnet Über/Unter X.5-Quoten match-spezifisch aus erwarteten Toren (lam = avg bzw. Prognose-Total, Poisson). Feste Fantasiewerte (o15/o05/u25/u35 + clean-sheet o25) ersetzt.
- Gegen echte Samples kalibriert: Über 2.5 Caernarfon–Levadia real 1.58 → berechnet 1.59; Über 0.5 ~1.01–1.10 (real 1.03); Unter 3.5 ~1.17 (real 1.17); Unter 2.5 ~1.40–1.67 (real 1.60-1.70). Markt-Labels bleiben Dot-Format ("Über 2.5 Tore") für Odds-Lookup/Settlement-Konsistenz.
- OFFEN (2. Batch erwartet): Handicap-Quoten (Qarabag -1.5=1.19, Sheriff -1.5=1.95) + Team-Totals ebenfalls match-spezifisch machen; Marge feinjustieren.


## Changelog — 2026-07-09 (Friendlies-Label, Liga auf Single-Tipps, Bet-Builder-Vielfalt)
- Bet-Builder Redundanz-Fix: „Über 1.5 Tore" wird nie mehr zu „beide treffen" gepackt (implizit). Tor-Linien ab Über 2.5 mit 1-Tor-Puffer. Klassisches beide treffen bleibt 2 Legs (Combo-Gate 1.80→1.60). Clean Sheet (3:0/0:3) → Über 2.5 statt BTTS.
- Freundschaftsspiele NICHT geblockt (Blacklist-Ergänzung mkk dnepr/friendl wieder entfernt), sondern als „Freundschaftsspiel" gelabelt (forebet + predictz Tip-Erstellung).
- Single-Tipps zeigen jetzt echte Liga statt „TipJarHQ Pick" (forebet: league_disp aus r.league/lcode/cc; predictz bereits real). Frontend zeigt tip.league (RateWall Zeile ~568).
- NEUE settlebare Bet-Builder (deterministisch via neuem `_grade_goal_leg`): Beide treffen + Doppelte Chance (1X/X2), Über 2.5 + DC 12, Über 0.5 je Halbzeit. `find_finished_fixture` liefert jetzt HT-Tore (score.halftime). `_grade_goal_leg` behandelt o{k}5/team_o05/btts/res_*/dc_*/ht_o05/sh_o05/o05_each/ht_u25/ht1_win, gibt None bei unbekanntem Kind (nie Fake-Ergebnis). In settle_hq_combos verdrahtet. Regression + neue Kinds getestet.
- OFFEN: Ecken-Märkte (brauchen Statistics-API-Abruf) bewusst zurückgestellt.


## Changelog — 2026-07-09 (Cash-out-Claim, Homepage-Texte, Profil-E-Mail)
- Homepage: unter „Was ist TipJar?" neue Blöcke — SYSTEM-MODUS-Label, H3 „Warum Anwender TipJar wählen — statt Telegram, Discord & Co.", Nutzen-Text, „Dein Vorteil"-Box (volt), „Was wir NICHT sind"-Abgrenzung, CTA-Text (kein Button). i18n EN+DE (Rest via EN-Fallback). Kein Zähler, kein FAQ (bewusst).
- „Zeig deinen Gewinn"/Hall-of-Fame-Claim akzeptiert jetzt CASH-OUT-Scheine: neuer Claim-Typ "cashed" (Button „Ausgezahlt", Banknote-Icon, grid-cols-2). Backend: extract_win_slip erkennt "Cashed Out/Ausgezahlt" → status "cashed"; claim_win-Branch für "cashed" OHNE System-Match-Zwang (eigene Trophäe), 2+ Legs, WIN_CASHED_CREDITS=20; _render_slip_image Label „Ausgezahlt" + „Ausgezahlt:"-Betrag. i18n win.type.cashed(.desc) EN+DE.
- Profil: E-Mail jetzt änderbar (vorher nur Username). ProfileUpdate.email + Endpoint mit Unique-/Format-Check; ProfileModal neues Feld profile-email. E2E getestet (Username+E-Mail ändern, Login mit neuer E-Mail ok). → Nutzer ändert sein Konto selbst auf Produktion (duexxatuxx→TipJarLogic, danoglidis...→kontakt@tipjarglobal.com).

## Changelog — 2026-07-09 (Voll-Automatik Abrechnung + korrigierbare Scheine)
- Abgerechnete Scheine sind jetzt KORRIGIERBAR: TipCard zeigt für Admin/Ersteller (canDelete) auf JEDEM Status die Zeile "Ergebnis setzen / korrigieren" mit 4 Buttons (OFFEN/GEWONNEN/VERLOREN/CASHED OUT), aktueller Status hervorgehoben. `settle()` lädt im Abgerechnet-Tab die Listen neu (loadSettled als useCallback). Behebt "Olympiakos versehentlich auf Verloren, kein Undo möglich".
- OFFEN-Reopen setzt hq-live → "live" (Auto-Loop übernimmt wieder), sonst "pending".
- Voll-Automatik Gewonnen/Verloren: bereits vorhanden (settle_pending_tips / settle_hq_combos / settle_multimatch_parlays / live_autopost graden jede Wette + jedes Leg aus API-Football-Endstand). Keine manuelle Aktion nötig; Buttons sind nur Override.
- Cashed-Out-Grenze (ehrlich dokumentiert): Cash-out ist eine Buchmacher-Aktion, für die es KEINE Datenquelle gibt → kann NICHT auto-erkannt werden. Nutzer setzt "Ausgezahlt" per 1 Klick (D1: ganzer Schein=Ausgezahlt, gewonnene Legs=Gewonnen).
- NEU: settle_multimatch_parlays gradet jetzt AUCH cashed_out-Scheine leg-für-leg weiter (Status-Filter um "cashed_out" erweitert, Attempt-Cap 24), überschreibt aber NIE den Schein-Status "cashed_out" (is_cashed-Guard). So füllen sich die Legs automatisch mit echtem Gewonnen/Verloren, während der Schein "Ausgezahlt" bleibt. Frontend zeigt Legs wieder per echtem Status (kein Force-Grün mehr). E2E verifiziert (cashed bleibt cashed, normales Parlay flippt zu won).


- FIX (2026-07-10) ABRECHNUNG hängt bei Akzent-Ligen + UI z-index.
  ROOT CAUSE (Produktion: Spiele bleiben stundenlang „OFFEN"): `_teams_match`/`_norm` entfernten keine diakritischen Zeichen → "Rīgas FS"≠"Rigas FS", "MSK Žilina"≠"MSK Zilina" → find_finished_fixture/resolve_team_id scheiterten für viele Sommer-Quali-Ligen (baltisch, slawisch, Conference/Europa League) → settle_attempts liefen bis zum alten Cap 24 → Tipps dauerhaft ausgeschlossen (settle-now checked:0).
  FIXES: (1) `_norm` nutzt jetzt unicodedata NFKD + strippt combining marks (Rīgas→rigas, Žilina→zilina, ö→o). Repariert die komplette Fixture-/Team-Auflösung. (2) Neuer robuster Fallback `_datescan_fixture(home,away,dates,cache)`: scannt `/fixtures?date=` und matcht BEIDE Teamnamen (beide Richtungen), unabhängig von team-id/season; per-Datum-Cache. Eingebaut in settle_pending_tips UND settle_hq_combos (nach find_finished_fixture). (3) SETTLE_MAX_ATTEMPTS 24→240 (spät veröffentlichte FT-Status + Fallback-Retries bis 36h-Purge; Alt-Tipps mit ~34 Versuchen sind dadurch wieder < Cap → werden erneut geprüft). VERIFIZIERT im Backend: _teams_match('Rīgas FS','Rigas FS')=True, _datescan Glentoran→1:2, Hajduk→2:0. Braucht Re-Deploy; danach räumt der Loop den Rückstau automatisch ab.
  UI-FIX: Sprach- & Profil-Dropdown im Header (Header.jsx) lagen HINTER den grünen CTA-Buttons (absolute ohne z-index vs. relative Badge-Buttons später im DOM) → beiden Dropdowns `z-[60]` gegeben. Auf Preview verifiziert (Dropdown vollständig oben). Braucht Re-Deploy.