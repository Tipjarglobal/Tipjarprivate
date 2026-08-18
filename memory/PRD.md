# TipJar Global — PRD (Kurzfassung)

> Vollständige Produktregeln & Historie: `/app/tipjar.md`, `/app/BRAIN.md`, `/app/MEMORY.md`.
> Sprache des Nutzers: **Deutsch** — alle Antworten auf Deutsch.

## Produkt
Sports-Betting-/Tip-Community-PWA. React (frontend) + FastAPI (backend) + MongoDB.
Features: AI-Combo-Generierung & OCR (Gemini via Emergent LLM Key), Live-Settlement-Loops,
30-Tier Coin-Jar-System, i18n (8 Sprachen), Sponsor-Feeder, Coin-Battery, JarDex/Open Case,
privater Admin-Bereich `/insights` (Analytics, Pick-Manager, Sponsor-Ranking, Glitch-Tracker).

## Umgebungen
- PREVIEW (dev): Arbeitsumgebung des Agents.
- PRODUCTION: https://tipjarglobal.com — Änderungen erfordern Redeploy durch den Nutzer.
- Git: kein remote pull/push im Container; Nutzer lädt `.txt`-Dateien hoch bzw. nutzt „Save to GitHub".

## Wichtige Constraints
- Keine automatisierten Massentests (Credits sparen). Nur curl + einzelner Smoke-Screenshot.
- Keine neuen Dependencies ohne Grund. Direkt Dateien überschreiben, kein Refactoring.

## Changelog (Session 16.08.2026)
- 28 Jar-PNGs via `install_all_jars.sh` nach `/app/frontend/public/jars/`.
- Sponsor-Feeder: BETSCORE + SGCASINO ergänzt (7 gesamt).
- Sponsor-Klick-Tracking: `POST /api/sponsors/{id}/click` (Event-basiert; Bots/Crawler aus, Admin zählt) +
  `GET /api/admin/sponsor-stats?period=today|7d|all`. Ranking-UI mit Zeitraum-Filter in `SecretInsights.jsx`.
- Jar-Tabs bereinigt: ProfileModal nur 2 Tabs; JarDex neu aus `JAR_DEFS` (echte PNGs, keine `???`);
  OpenCase Hinweis-Text; Backend `/jars/opencase` → `List[str]`, Register-Default `["common_glass"]`.
- `AnimatedJar.jsx`: frühere Homepage-Version wiederhergestellt (Wappen + Glas + Füll-Animation + Boost-Münzen).
- **Money-Glitch-Lexikon (Typ1–Typ9)**:
  - `/app/backend/glitch_lexikon.py` (FLAGS, GLITCH_LEXIKON, `detect_glitch`, `LEXIKON_PROMPT_BLOCK`, `brain_lessons`).
  - KI-Integration: Lexikon-Block an `AI_SYSTEM` angehängt (Slip-Analyse erkennt/bewertet Muster) +
    9 Lessons idempotent in `db.master_brain` geseedet (Startup).
  - Privater Bet-Tracker (Admin `/insights`): `GET /admin/glitch-lexikon`, `GET/POST /admin/glitch-bets`,
    `PUT/DELETE /admin/glitch-bets/{id}` — Auto-Tagging via `detect_glitch`, Profit-Summary. UI: `GlitchTracker`.
- **TipJarMaster GENERELLER Safety-Glitch-Melder (Patch 16.08.)**:
  - `MasterAvatar.jsx` ersetzt: rotierende Safety-Speech-Blase (alle 4s), generisch für JEDES Team.
  - `glitch_lexikon.py` ersetzt: + `SAFETY_SPEECH_TEMPLATES`, `get_safety_speech`, `build_avatar_speech_for_tip`, `master_pille_must_have_safe`.
  - `/api/master/avatar` reichert jeden Call mit generischem Safety-Speech + `safety_speeches` an (Playable-Filter beibehalten).
- **Real Odds (mehrsprachige echte Quoten) — immer MongoDB**:
  - `/app/backend/real_odds.py` (Markt-Normalisierung über Sprachen: Über/Over/Más de/Üst/Più di… + `REAL_QUOTES_DB` + Persistenz-Helfer `snapshot_providers`/`hydrate`).
  - `/app/backend/ticket_collector.py` (Parser + Collectors: `ingest_instagram`, `ingest_experten`, `ingest_capella_scraper`, `universal_ticket_parser`). Quoten-Parser gefixt (nahm fälschlich Markt-Linie 0.5 statt @1.46).
  - Persistenz: MongoDB `real_quotes` (`{match, market, providers, updated_at}`); Startup-Hydration in `REAL_QUOTES_DB`.
  - API (Admin): `POST /api/odds/ingest` (source: raw|instagram|experten|capella), `GET /api/odds/quote`, `GET /api/odds/all`, `DELETE /api/odds/{match}/{market}`.
  - 2c: Win-Claim-Reader (`extract_win_slip`) füttert via `_auto_ingest_slip_odds` jeden echten Schein automatisch in die Odds-DB (anbieter=username, defensiv).
  - Hinweis: Top-Level-Module (nicht `core/`, da `core.py` schon existiert).
- **LLM-freie Schein-Annahme (Option A, Tesseract-Fallback)**:
  - `extract_win_slip` (server.py): zuerst Gemini Vision; wenn LLM-Budget leer / LLM aus / leeres Ergebnis → lokaler **Tesseract-OCR-Fallback** (`_ocr_tesseract`) → `parse_slip_text_to_legs` (Regex + `real_odds.normalize_market`). Kostet 0 Credits, kein LLM.
  - `parse_slip_text_to_legs`: stateful mehrzeiliger Parser (Team-Zeile + Markt-Zeile getrennt, überspringt Summenzeilen, strippt angehängte Quoten). Auch für Pipe-Format „Heim vs Gast | Markt | Quote".
  - `claim_win`: optionaler `slip_text`-Form-Param (Text-Einreichung möglich, aber KEIN Frontend-Button — vom Nutzer nicht gewünscht).
  - Deps: `tesseract-ocr` (System-Binary, in Preview via apt) + `pytesseract` (requirements.txt).
  - ⚠️ PRODUCTION-WARNUNG: Tesseract-System-Binary muss im Deploy-Image vorhanden sein. Kein Aptfile/Dockerfile im Repo → Emergent Support kontaktieren, ob `tesseract-ocr` in Production installiert ist, sonst greift der Fallback dort nicht.

## Changelog (Session 17.08.2026 — Homepage 6-Raster Migration)
- Homepage nach `/app/memory/pille.md` in modulare Raster überführt (alle 8-sprachig: de/en/es/el/fr/it/ar/tr).
- Neu gebaut & in `App.js` eingebunden:
  - `Raster2_Supporter.jsx` — 5 Supporter-Templates (XXL 119,99€ → S 9,99€), Bestseller-Badge, Instagram-Buchung. Platziert direkt unter Raster 1.
  - `Raster3_AiPicks.jsx` — hellblaues KI-Info-Raster + KI-Pillen kompakt 2-Spaltig (Single/grün, Smart/grün+„Mit der KI reden", Master/rot+Crown, Abgerechnet/weiß, Statistiken/rosa). Verdrahtet an `openTipsView(...)`.
  - `Raster4_Money.jsx` — „Willst du mit Wetten Geld verdienen?"-Text + Globale-Tipp-Community-Section (Badge/Headline/Body/Info-Box) + eingebettete `CoinBattery` + 2 Buttons (Tipp einwerfen / Münzen verdienen).
  - `Raster4b_CommunityLive.jsx` — Community Picks (gelb, links, mit blauem LIVE-Button) + Live KI Picks (blau, rechts, Wifi-Icon).
- Reihenfolge oben→unten: Raster1 → Raster2(Supporter) → Header(Nav) → CoinBattery → Raster3 → Raster4 → Raster4b → (Legacy Hero/Story/Invite/HallOfFame beibehalten) → Raster5 → Raster6 → Footer.
- Bestehende Header-Nav (`Raster2_Header`/QuickView-Pills), Hero, Story, InviteSection, HallOfFame NICHT entfernt (additive Migration, Homepage nicht gebrochen).
- Verifikation: sauberer Webpack-Compile (nur bestehende ESLint-Warnings), keine React-Runtime-Fehler in Konsole, `raster3-ai-picks` im DOM auffindbar. ⚠️ Kein sauberer Live-Screenshot möglich (Screenshot-Tool liefert bei dieser App nur den frühen Splash-PNG-Frame).

## Offene Tasks (nächste Session)
- P1: Feed-Limit auf 300 erhöhen + Community-Picks-Fallback in `backend/server.py` (`GET /api/feed`).
- P1: Homepage-Raster visuell final abnehmen (User oder testing_agent).

### Patch 17.08.2026 (Reihenfolge + Batterie-Cleanup + Jar-Reward ×10)
- **Raster 5 & 6 verschoben**: jetzt direkt unter Raster 4 (vor der „DIE GLOBALE TIPP-COMMUNITY"/HERO-Sektion). Neue Reihenfolge: Raster1→2→Header→3→4→5→6→HERO/Story/Invite/HallOfFame→Footer.
- **Kleine Batterie aus Raster 4 entfernt** (CoinBattery raus) – die große Batterie lebt jetzt nur noch in Raster 6.
- **„NIEMALS UNTER 125" entfernt** aus der Raster-6-Batterie (`Raster6_8Lang.jsx`), zeigt nur noch „Auszahlung ab 2000+ • VOLL 2500".
- **Jar-Verkaufs-Reward erhöht**: `JAR_SELL_MULTIPLIER=10` (Backend), Reward = Jar-Wert ×10 (z.B. common 400, top 5000). Anzeige **oben rechts in jedem Jar** als goldenes „💰 +X"-Badge (INVENTORY/JARDEX/OPEN CASE, `SELL_MULT=10` im Frontend synchron).
- Verifikation: Compile ok; Playwright-Assertions (Reihenfolge 4→5→HERO, keine Batterie in Raster4, kein „NIEMALS UNTER").

### Patch 17.08.2026 (Kauf→Pille Stripe-Flow + Jar verkaufen)
**Kauf→Pille (Stripe Flow B, `emergentintegrations`, `STRIPE_API_KEY=sk_test_emergent`, EUR):**
- Backend `server.py`: `PILL_PACKAGES` (rent2 300€, rent1 150€, partner 119,99€, sponsor 79,99€, vip 49,99€, fan 19,99€, supporter 9,99€; Laufzeit 2–6 Wo).
  - `POST /api/pills/checkout`, `GET /api/pills/checkout/status/{sid}` (fulfillt Pille idempotent bei paid), Webhook `/api/webhook/stripe` erweitert (kind=pill).
  - `GET /api/pills` (public, nur freigegebene Links), `GET /api/pills/mine`, `PUT /api/pills/{id}/link` (→ pending), `GET /api/admin/pills/pending`, `POST /api/admin/pills/{id}/approve|reject`.
  - `partner_pills`-Collection: tier/label/price/weeks/coins/link/pending_link/link_status/status/expires_at.
- Frontend: `Raster2_Supporter` Kauf-Button → Stripe-Checkout; aktive gekaufte Pillen erscheinen sofort UNTER den Templates (approved-Link klickbar, sonst „Link in Prüfung"). Neue Route `/pills/success` (`PillsSuccess`) mit Link-Eingabe (→ Freigabe). `AdminPillsPanel` im Admin-Bereich mit Freigeben/Ablehnen.
- Ablauf: Zahlung → Pille sofort live → Käufer trägt Link ein → Admin gibt frei → Link klickbar. KEINE Bilder/Objekt-Storage (auf Wunsch weggelassen).

**Jar verkaufen (In-App Coins):**
- `POST /api/jars/sell {jar_id}`: nur bei 100% vollem Jar (coins ≥ nächste Tier-Schwelle), jeder Jar 1× verkaufbar (`user.sold_jars`), Reward = Jar-Wert in Coins. `JAR_VALUES` (30 Jars) im Backend.
- Frontend `JarDex`: „Jar verkaufen 💰"-Button auf 100%-Jars in INVENTORY & OPEN CASE, aktualisiert Coins via `useAuth`.
- ⚠️ Ökonomie-Hinweis: Reward = Jar-Schwellenwert (bis 500 Coins), einmal pro Jar. Bei Bedarf anpassbar.

**Verifikation (curl E2E):** Jar-Verkauf (Reward 40, Credits 100→140, Doppelverkauf blockiert) ✅; Pillen-Lifecycle Link→Admin-pending→approve→public sichtbar ✅; Stripe-Checkout-URL erzeugt ✅; Frontend-Smoke (Homepage rendert, Purchase-Window, Buy-Button = Preis) ✅.
- test_credentials.md aktualisiert (war leer).

### Patch 17.08.2026 (Pillen-Trim, Tiers, klickbare Batterie, Jar-Instruktionen, Handbücher)
- **3mm-Trim** (`SponsorFeeder.jsx`): RENT2/RENT1/WAZAMBA auf einheitliche Standardhöhe 60px, Sponsor-Grid 41px, innere Elemente angepasst. Standardhöhe = getrimmte Höhe.
- **Supporter-Tiers** (`Raster2_Supporter.jsx`): alle 5 Pillen haben jetzt Badge oben rechts – PARTNER > SPONSOR > VIP > FAN > SUPPORTER. Höhen vereinheitlicht (py-5/py-4/py-3).
- **Klickbare Batterie** (`CoinBattery.jsx` + `Raster4_Money` + `App.js`): CoinBattery nimmt `onClick`; in Raster 4 öffnet Klick das Wallet zum Aufladen. Deutlicher Hinweis „👆 Antippen zum Aufladen" + Hover-Ring.
- **Jar-Instruktionen + %-Anzeige** (`JarDex.jsx`): 
  - OPEN CASE Info-Box: AFK Silver Coins, Gold Coins bei Sponsor-Klick, volles Jar (100%) verkaufbar.
  - INVENTORY Info-Box: neue Jars durch Coins + zufällige Besuche + ⭐ Sterne-Bewertungen.
  - Neuer %-Füllbalken pro Jar (INVENTORY + OPEN CASE), 100% = „verkaufbar 💰".
- **Handbücher gesichert** (`/app/memory/`): 9 aus Git wiederhergestellt (HANDBOOK, CHANGELOG, betting_notes, betting_strategy_notes, bugs, master_learnings, master_system_strategy, owner_preferences, smart_picks_principle) + tipjar.md/MEMORY.md/BRAIN.md/PLAY_STORE_GUIDE.md/STORE_LISTING.md hineinkopiert. Hinweis: `meta.md` existiert nicht in der Git-Historie (vermutlich = MEMORY.md).
- Verifikation: Compile sauber; Assertions bestanden (Batterie-Klick-Hinweis + alle 5 Tier-Badges).

## OFFEN / benötigt Entscheidung
- **Kauf → Pille automatisch einbauen** (User-Wunsch): braucht echten Checkout (Stripe) + Admin-Freigabe + `partner_pills`-Collection + dynamisches Rendern in Raster 1/2. Aktuell läuft Kauf über Instagram-DM (manuell). NICHT gefälscht – muss als eigenes Feature gebaut werden.
- **„Alles aus den Handbüchern zu Wahrheit machen"**: sehr großer, offener Scope. Nächster Schritt: Handbücher (tipjar.md/MEMORY.md/HANDBOOK.md) gemeinsam durchgehen und als priorisierte Task-Liste abarbeiten.

### Patch 17.08.2026 (UPGRADE_FINAL_v3 – Duplikate entfernt)
Nach `/app/memory/UPGRADE_FINAL_v3.md`:
- **Header-Duplikat gelöscht** (`Header.jsx`): der ganze „Quick-view CTAs"-Block (member-guide „Willst du von Wetten Geld verdienen?", ai-correction-guide KI-Text, 9er-Picks-Grid) entfernt. Diese Inhalte leben jetzt einzig in Raster 3 + 4. Header zeigt nur noch die Nav-Leiste. ⚠️ Nebeneffekt: Admin-only Pills „Systems" & „Codemining" waren nur hier erreichbar → aktuell nicht mehr über die Startseite erreichbar (bei Bedarf Admin-Shortcut neu setzen).
- **Raster 1** (`Raster1_RentPills.jsx`): eigene 2 „DEIN LINK HIER"-Templates gelöscht (waren Duplikat). Es bleiben nur die RENT-Templates im `SponsorFeeder` + Intro-Text + Wettanbieter-Grid.
- **SponsorFeeder.jsx**: Preise gefixt: „RENT 2 PILLS FOR YOUR LINK" 80€→**300€/MONTH**, „RENT A PILL FOR YOUR LINK" 50€→**150€/MONTH**.
- Verifikation (Playwright-Assertions, kein Fehler): Header-Pick-Pills & member-guide weg; „300€/MONTH"+„150€/MONTH" im DOM, „80€/MONTH"+„50€/MONTH" nicht mehr vorhanden; Raster 1 & 3 rendern.
- OFFEN (Plattform): GitHub neu autorisieren → Save to GitHub → Deploy, damit tipjarglobal.com den bereinigten Stand zeigt.

### Patch 17.08.2026 (UPGRADE_FINAL – Raster 1–4 Refactor)
Umgesetzt nach `/app/memory/UPGRADE_FINAL.md`:
- **Raster 1**: Titel auf Englisch „RENT 2 PILLS FOR YOUR LINK" (300€) / „RENT A PILL FOR YOUR LINK" (150€), Instagram-Klick, Wettanbieter unverändert.
- **Raster 2 (Supporter)**: Instagram-Text entfernt, weiße Titel-Wörter (PARTNER/SPONSOR/VIP/…) entfernt (nur noch gelbe Badges oben rechts), **Preis oben links gelb fett**, Höhen gesqueezed (XXL groß, XL/L mittel, M/S klein). Klick öffnet **Purchase-Window** (Modal mit Features je Paket + Kauf-CTA → Instagram), statt direkt Instagram.
- **Raster 3 (KI)**: ⓘ-Info-Icon ergänzt. Neues Layout: Zeile1 Single|Smart(+„Mit der KI reden"), Zeile2 Master (full), Zeile3 Abgerechnet|**Live KI Picks** (aus 4b hierher), Zeile4 Statistiken (full).
- **Raster 4**: Community-Marketing-Block gelöscht (Badge/Headline/Body/Infobox). Batterie bleibt, **„NIEMALS UNTER 125" entfernt** (in `CoinBattery.jsx`, sprachneutral). 4 Actions: Tipp einwerfen / Münzen verdienen / Meine Sammlung / **Community Picks ansehen (gelb + LIVE)** – letzteres aus 4b hierher.
- **Raster 4b entfernt** (aus `App.js`), Standalone-Batterie oben entfernt (keine Doppel-Batterie mehr).
- **OpenCase-Bug (JarDex)**: veraltete Jar-IDs (frosted/cosmic) werden beim Laden gefiltert → kein leeres erstes Feld mehr; neuer `JarImg` mit Fallback-Kette (open→closed→Farb-Block) fixt broken images (Wood/Bamboo).
- Verifikation: sauberer Compile; funktionaler Smoke-Test (alle Raster-Testids + Supporter-Purchase-Window öffnet) ohne Fehler.
- OFFEN (Plattform, nicht durch Agent machbar): GitHub-OAuth neu autorisieren → Save to GitHub → Deploy/Publish, damit tipjarglobal.com aktuell wird.

### Patch 17.08.2026 (Leaderboard echte Daten + fliegende Münzen + Fake-Zahlen entfernt)
- **Fake-Social-Proof entfernt**: `core.py` `MEMBER_DISPLAY_BOOST` (war 400) und `SUBSCRIBER_DISPLAY_BOOST` (war 140) auf **0** gesetzt. `/api/stats`, `/api/notifications/stats`, Subscribe/Unsubscribe zeigen jetzt NUR reale Zahlen (Mitglieder, Benachrichtigungs-Abos). Keine Platzhalter mehr im Frontend gefunden (InviteSection/NotificationBell nutzen bereits echte APIs).
- **Echtes Gifting-Leaderboard**: neues `GET /api/gifting/leaderboards` — aggregiert `credit_transactions` (type=gift) zu 4 Boards: `week` (7 Tage Aktivität = verschenkt+erhalten), `all` (All-Time Aktivität), `received` (All-Time erhalten), `gifted` (All-Time verschenkt). Nur echte Mitglieder (`REAL_MEMBER_QUERY`, Test/Bot/Admin gefiltert). Top 10, Medaillen-Ränge.
- `Raster6_8Lang.jsx`: Platzhalter-Liste entfernt, lädt echte Boards via `api.get('/gifting/leaderboards')`, aktualisiert bei `tipjar-boost`. 8-sprachiger Empty-State (`empty`). Avatar-Initiale + Coins pro Zeile.
- **Fliegende Münzen nach Spendieren**: `AnimatedCoins.jsx` jetzt in `App.js` gemountet (war nirgends eingebunden). `WalletModal.gift()` dispatcht nach Erfolg `tipjar-boost` mit `amount=received` → fliegende Münze + CoinBattery-Flash + Leaderboard-Refresh.
- Hinweis: Admin-Account ist absichtlich aus dem Leaderboard/Stats ausgeschlossen (nur reale Mitglieder), daher sieht man sich beim Testen mit Admin dort nicht.
- `Raster6_8Lang.jsx`: Haupt-Batterie deutlich klickbar gemacht (pulsierender „Tippen zum Aufladen"-Hinweis, Klick-Icon, Ring-Highlight, ganze Karte als Button) + 2 Aktionen: **„Credits feeden"** (`onFeedClick`) und **„Spendieren"** (`onGiftClick`). Emoji durch lucide-Icons ersetzt. Neue 8-sprachige Keys `tapHint`, `giftBtn`. RTL für ar.
- `App.js`: `onFeedClick`→`openGiftBattery` (Wallet Top-Up), `onGiftClick`→`openGift` (Wallet Gift-Tab, `walletGift`-State). Beide mit Login-Guard.
- `Raster4_Money.jsx`: dritter Button **„Meine Sammlung"** (`onCollection`, Boxes-Icon) neben Tipp einwerfen / Münzen verdienen. 8-sprachiger Key `collection`.
- `App.js` + `ProfileModal.jsx`: `openCollection` öffnet Profil direkt auf dem **Sammlung (JARDEX)**-Tab via neuem `initialTab`-Prop.

## Backlog / offene Ideen
- P1: Sponsor-Klick-Verlauf als 14-Tage-Balkenchart.
- P2: Sponsor-Buttons automatisch nach Klicks sortieren.
- P2: Fliegende Boost-Münze auch in die CoinBattery integrieren.
- P2: Glitch-Muster tiefer in die algorithmischen Master-Combo-Builder einbauen (größeres Projekt).

## Test-Credentials
Admin: `admin@tipjar.com` / `TipJarAdmin2026!`

## 2026-08-18 — JarDex → SHOP Refactor (owner request)
- JarDex (Profil → Tab jetzt "Shop") komplett zum SHOP umgebaut. Backend-basiert, echte Coins (credits).
- Katalog: 30 Jars in 4 Kategorien (COMMON 10 / UNCOMMON 8 / RARE 7 / LEGENDARY 5), sellReward 40…12000.
- Mechanik: buyPrice = sellReward * 0.75 (BUY_DISCOUNT=0.25, Gewinn eingebaut). Alle Jars sofort kaufbar (KEINE Lock-/Reihenfolge-Logik mehr).
- Verkauf nur bei fill==100 %, gibt vollen sellReward, Jar bleibt owned, fill→0. Auto-Fill zeitbasiert, LANGSAM: JAR_FILL_SECONDS=8h (server-berechnet). Das bremst den Gewinn-Automaten.
- Endpoints: GET /api/jars/shop, POST /api/jars/shop/buy, POST /api/jars/shop/sell. State in users.jar_shop = {jar_id:{owned,filled_at}}.
- Lucky Drop: _bump_jar_activity() an rate_tip (+1) und create_tip (+3). Threshold (random 12-22, dann 18-34) → gewährt zufälliges NOCH-NICHT-besessenes Jar gratis, pushed in users.pending_jar_drops; GET /jars/shop liefert new_drops und leert sie (Frontend-Toast).
- Frontend: JarDex.jsx = 2-Spalten-Shop-UI, Sub-Tabs EINKAUFEN/VERKAUFEN, 4 Kategorie-Tabs, 8 Sprachen (DE/EN/ES/FR/IT/PT/TR/PL), Erklärungstext pro Tab + Bonus-Hinweis, 5s-Polling für Live-Fill. Grafiken via JAR_DEFS-Lookup, Fallback farbiger Block.
- Getestet: buy (Abzug/owned/fill0), sell-Gating (<100 abgelehnt), sell-Erfolg (+reward/fill0/owned bleibt), Lucky-Drop-Notification, UI-Screenshot beide Tabs. ALLES OK.

## 2026-08-18 (später) — Fixes.md aus Live-Deployment
- BUG 4 (confidential öffnet neues Programm): GEFIXT. Raster4_Money.jsx: statt `target="_blank"` jetzt In-App-Modal (data-testid=confidential-modal) mit dunklem TipJar-Header + X + Loading-Watermark (TJ-Shield), iframe /glitch/index.html bleibt in der App. Deckt auch BUG 2/3 (Watermark, TipJar-Modal statt native Window) für diese Pille ab.
- BUG 6 (Posten blockiert wegen KI-Tageslimit): GEFIXT KI-frei. SubmitTipModal.jsx publish(): wenn KI nichts erkennt und Markt-Feld leer, wird der getippte Text als Auswahl genutzt → man kann IMMER posten. Backend akzeptiert (needs_clarification statt reject). Getestet per curl (text-only Tipp → status live).
- OFFEN (Entscheidung/Reproduktion nötig): BUG 1/3 „alle anderen Pillen öffnen gleiches/native Window" (beschreibt Live-Build; in Preview-Code kein window.open für diese Pillen gefunden). BUG 7 großer geführter Offline-Post-Flow (Team-Name → 3 Vorschläge, „noch ein Spiel adden?", Text komplett optional) = eigener größerer Umbau des Post-Modals, NICHT gemacht.

## 2026-08-18 (Fix-Runde 2) — Shop-Tabs korrigiert + Inventory/Open Case wiederhergestellt
- WICHTIG: Beim Shop-Umbau hatte ich Inventory + Open Case gelöscht. Aus git (d6ab5a5) zurückgeholt und in EINE Komponente JarDex.jsx vereint.
- Tab-Struktur jetzt: INVENTORY | SHOP | OPEN CASE (Shop in der Mitte). Alles über /jars/shop (eine Datenquelle). "Meine Sammlung" (openCollection) → JARDEX-Container → interner Tab INVENTORY default.
- Shop-Sub-Tabs: EINKAUFEN (default) / VERKAUFEN. Kein Sprach-Switcher mehr (nutzt localStorage tj_lang → T.DE/T.EN Fallback).
- Glass = STARTER_JAR: Backend erzwingt owned=true + fill 100 (default), buy /jars/shop/buy lehnt glass ab, Lucky-Drop schließt glass aus. Inventory/Shop zeigen "Free starter • ready".
- Open Case: 3-Slot-Set via /jars/opencase (filtert veraltete IDs), Fill aus /jars/shop, verkaufen bei 100%.
- Confidential /glitch/index.html: Sprach-Switcher (langs-Buttons + JS) entfernt, bleibt Deutsch. tracker.html lang-bar sind nur OCR-Info-Labels (kein Switcher) → bleiben.
- Getestet: curl (glass starter owned+nicht kaufbar), Screenshots (3 Tabs, Reihenfolge, Shop=BUY default, Glass-Starter). Kein testing_agent (Credits sparen).
