TipJar — MEMORY.md — FINAL — 15.08.2026
Konsolidiert aus altem 193k MEMORY.md + LEAN MEMORY + COIN JAR 30 Jars. Root-only.

OWNER
Languages: 3 equally well German, English, Greek
Communication: German preferred
Watches live tipjarglobal.com not preview
Deployment: Save to Github -> Deploy otherwise not working wrong
DO NOT propose unsolicited features
===== COIN JAR SYSTEM - 30 JARS =====
ECONOMY ENGINE
packet_size=10000 Coins=1 Packet | base_payout=50.00 EUR | bonus_per_packet=0.025 | max_bonus=0.25 | max_payout=62.50 EUR | cap_after=10 Packets | live_condition members>=1000 | battery>2000 | queue only 1 Packet ready

KOSTENKONTROLLE
Volles Jar nur 40-500 Coins (NIEMALS 150k). 250x Wood voll = 10.000 Coins = 1 Packet = 62,50€ max

JAR DEFINITIONS - 30 JARS BALANCIERT - Carton Box statt Cork
Seal = 5% vom vollen Wert, rundet auf bei ,5. Einmalig kaufen, für immer auf diesem Jar.

TIER 1 COMMON 6 Jars 40-80
Common Glass Jar: 40 Coins | Seal 2 | COMMON // START
Wood Jar: 50 | 3 | COMMON
Stone Jar: 60 | 3 | COMMON
Clay Jar: 70 | 4 | COMMON
Bamboo Jar: 75 | 4 | COMMON
Carton Box Jar: 80 | 4 | COMMON // Carton Box
TIER 2 UNCOMMON 6 Jars 90-170
Bronze Jar: 90 | 5 | UNCOMMON
Iron Jar: 110 | 6 | UNCOMMON
Tin Jar: 130 | 7 | UNCOMMON
Copper Jar: 150 | 8 | UNCOMMON
Aluminum Jar: 160 | 8 | UNCOMMON
Brass Jar: 170 | 9 | UNCOMMON
TIER 3 RARE 6 Jars 180-280
Steel Jar: 180 | 9 | RARE
Silver Jar: 200 | 10 | RARE
Nickel Jar: 220 | 11 | RARE
Chrome Jar: 240 | 12 | RARE
Carbon Jar: 260 | 13 | RARE
Crystal Jar: 280 | 14 | RARE
TIER 4 EPIC 6 Jars 300-420
Gold Jar: 300 | 15 | EPIC
Platinum Jar: 350 | 18 | EPIC
Titanium Jar: 380 | 19 | EPIC
Ruby Jar: 400 | 20 | EPIC
Sapphire Jar: 410 | 21 | EPIC
Emerald Jar: 420 | 21 | EPIC
TIER 5 LEGENDARY 4 Jars 450-500
Diamond Jar: 450 | 23 | LEGENDARY
Obsidian Jar: 475 | 24 | LEGENDARY
Galaxy Jar: 500 | 25 | LEGENDARY
Void Jar: 500 | 25 | LEGENDARY
TIER 6 MYTHIC 2 Jars 500 Endgame
Nebula Jar: 500 | 25 | MYTHIC
Infinity Jar: 500 | 25 | MYTHIC
JAR STATES
CLOSED nicht versiegelt: Verliert LANGSAM -5% pro Tag wenn nicht 5 Calls gedrückt. Wachstum NUR wenn 5 Calls.
OPEN in OPEN CASE: Verdient AFK Silver automatisch. Coins Animation. Max 3 Jars gleichzeitig. Ohne Deckel offen.
SEALED versiegelt: Verliert GAR NICHTS mehr. Wenn zu=Stand bleibt für immer. Wenn offen=verdient AFK aber kein Verlust=perfekt. Siegel einmalig für immer auch nach Leeren.

BATTERY SYSTEM
total_capacity=2500 CR | floor=5% (125 CR) fällt nie unter 5% | per_click +0.01% | main_charge Credits spenden MASSIVE | colors <25% rot <50% amber <75% lime >75% grün | payout_unlock >2000 CR | component CreditBattery.jsx user.credits/2500 | App.js <CreditBattery current={user?.credits} max={2500}/> + <MemberJarWall/> | Backend GET /api/users/public-jars

COIN SYSTEM GOLD & SILVER GETRENNT
GOLD aktiv: Jeder Click=1 Gold. Gold fällt in random offenes Jar im OPEN CASE. Sponsor 1-5 Clicks=5 Gold ab 6 KEIN Gold nur Batterie+Silver. Sterne Picks COMMON 20 Clicks=1 Gold UNCOMMON 25 RARE 40 EPIC 75 LEGENDARY 150. Jeder Stern-Click +0.01% Batterie auch ohne Gold. Gold zählt für Packet 10k=50€ Hauptwährung
SILVER AFK passiv: Sammelt passiv über Zeit auch ohne Clicks. AFK Credits wenn Jar offen im OPEN CASE. Sponsor ab Click 6 Nur Silver+Batterie. Max 3 Jars gleichzeitig

UI 3 TABS
Tab1 INVENTORY Owned: Alle Jars die User besitzt Lager
Tab2 JARDEX Alle Jars: Alle 30 Ghosts Infos immer sichtbar Wie Pokedex Sammelanreiz
Tab3 OPEN CASE Arbeitsfläche: Max 3 offene Jars LEER Slots 0-3 Hier fallen Gold Coins rein Hier AFK Silver verdient
Start: 1x Common Glass Jar direkt im OPEN CASE

===== HARD RULES - MUST ALWAYS APPLY =====
Codemining Owner mappings law
Text mappings directly e.g. Cobresal wins->Cobresal DNB, 1X+Under2.5->Underdog+2.5 Handicap. NEVER ask scope general vs single always GENERAL take wording replace old rule newest wins. No lotto generic wins without edge Under3.5 cushion no demo seed in active feed never touch finished reads. NEVER add own logic. NO exact scores REMOVE redundant legs -1.5 HC+BTTS omit Over2.5/3.5. Risk-averse avoid 0:0 leagues Value Bankers combos custom Asian-line.

Knockout duels Only strong side
NEVER back weak trailing away side no win handicap scores over0.5 underdog. ALWAYS back aggregate leading strong fav_prob>=62. _favourite_side_map _leg_backs_clear_underdog _master_leg_candidates drops underdog

Gifts priority
What gifts say has priority no AI contradict. Qarabag under2.5 then stats NOT Qarabag scores master NOT over2.5 mental NOT over4.5. _gift_stance_map is_gift team_over under match_over under _conflicts_with_gift. Gift on ONE team blocks only this team opponent may score Match under blocks every over

British Isles No directional
England Scotland Wales Ireland Northern Ireland everyone beats everyone lotto. NO first_two halftime win 1X2 on British Isles. Instead over2 Asian goals push at exactly2 only if goal game forecast>=3 over25 0:0 unlikely. Detector _is_british_isles ONLY nation country code england scotland wales ireland eng sco wal nir irl NEVER championship premier league

10 stars only real banks
Live another goal NEVER 10 stars cap 7. Rating from odds rating=min(7,1/odd*10). _live_overline_penalty Blowout diff>=3 -2 stars red card -1 knockout cup -1.5 <3 not offer

Avatar only verified games
EVERY game before posting via resolve_team_id find_upcoming_fixture verify. Without fixture no call no phantom Arges Pitesti Miercurea Ciuc. Bubble only unfuckable statements still win at 2:2 half_any wins at least one half ht_no_loss not losing at HT f1>=o1 dc Double Chance over15 Over1.5 ah_minus1 -1 Asian win2+=won exactly1=void else lost. Rotation ah_minus1->half_any->ht_no_loss->dc->over15 goal-friendly

System banker rules
Banker safe low odds BANKER_MAX=1.55 no veto otherwise no system but simple combo. Banker EARLIEST earlier matches NEVER last nightly. nb=min(2 if n>=5 else1,n-2) always>=2 zeta remain. Selection kickoff earlier->banker then low odds filter safety. Settlement settlement.py lost banker whole system lost otherwise X-out-of-Y won>=need Void out of total. Risk-banker parade master_riskparade_build 1x day 1 risk high odds 3.0-12.0 as banker+3-4 safe zeta 1.10-1.55 System N-1/N. Tasty markets HT/FT scorer pair same time ±90 combined<=15 zeta gift value

DNB settlement
Draw No Bet draw hg==ag VOID refund backed team wins won loses lost. Team from market {Team} DNB via _teams_match Default Home. Void leg in parlay push odds new

Flags
ONE flag top left before each game single combo old row top right removed. flagFor Country Name->ISO2 co->flag league keyword->fallback every MUST flag. Master combo stores country

Value Goals
Value=weak team scores double over1.5 team odds high market underestimates. Same-Game Builder {weaker} over1.5+over3.5 Gate total>=3.6 min(ph,pa)>=1.4 pw>=0.40 pt>=0.42 Fallback single over1.5 over3.5 Slim 2-4 legs Cap60. H2H _h2h_team_scores_2plus 2+ in >=50% last duels otherwise model gate. Only goal rich balanced both score min>=1.4 total>=3.6 never one sided blowout

Smart picks no lotto
Safe logical well justified from real data form single calm value singles 1.3-1.6 ideal Robbie Ure @1.41 Halmstad vs Sirius Anytime Goalscorer sub scores. NEVER cycle logic team hasn't scored won long time now due DEACTIVATED smart_h2h_autopost return Code exists but unreachable+self-heal deletes open cycle picks. Complete community combo take over Dembélé shot+PSG scores+PSG not losing @1.81 ALL legs[] faithfully nothing drop swap invent player odds keep analysis exact selections is_combo same_match legs[] total_odds Parlay Same-Match Builder combo_legs

No feature suggestions
At finish tool NO invented feature ideas Next Action Items. Only build what owner explicitly says short final summary

Friendship no scorers
Friendship test games lineups not scrapeable Barcelona 08.08.26 2 games same day 1-0 Forest+Udinese1-0 split squad weak few goals. No scorers over blind strong club name not A-team. Friendship from scorer combo EXCLUDED friendl friendship testspiel φιλικ amistoso amichev

Contrarian Hard 2:2
What fucks slips mass scraper 3-1 can end 2-2 always think what fucks mass. Hard area master_hard_2_2 ONE daily combo exact 2:2 traps fav_prob50-72 ph>=2 pa>=2 total<=5 |ph-pa|<=1 Cap6 odds2197. Settlement Correct Score2:2 deterministic judge_market

Timing team scores
Not blind team scores consider WHEN team typically scores. Mark teams loosely early scoring until 40 60 75 90 Output either generally over0.5 until60 or concrete team scores until X X always 40 60 75 90 Teams only late not for early

Thirsty for goals exclusions
Team last game not scored scores probably next Pafos 4-0 correct BUT back strong side not blind thirsty away underdog Pafos-Hajduk 4-0 Hajduk0 false. Exclusion itself at home not scoring Model 0 goals clear away underdogs Qarabag at home not scored away harder not in stats

OCR fixes
DRAW NO BET DNB win without draw draw no bet =><Team> Draw No Bet team MUST in NEVER pure winner. TEAM goals Over Under Molde over0.5=>Molde over0.5 goals team+line keep NOT total. Per-leg kickoff exact next to match printed time never empty move invent. Shots over23.5 Shots shots on target SHOTS not Goals never convert to goals

English base
Main language ENGLISH Master labels EN Double Chance {fav} wins at least one half not losing at half-time Over1.5 Goals Top Scorer Combo HARD Correct Score2:2 Badge tabs EN. localizeMarket {Team} Team-Tore Über X en Team Goals de Team-Tore Fix

System picks off + Admin only
System picks off snapshot_systems return0 no hq-system saves settlement existing open deleted. Buttons System Picks Codemining only Admin Header.jsx App.js Overlay-Nav isAdmin user.role==admin. Train the Master every logged user freetext EVERY language EVERY philosophy up to4 images POST /api/master/train distills ONCE LLM Vision clear English lesson keeps numbers odds teams results exact db.master_brain {text images lesson topic language status} Admin review GET /api/admin/master-brain. One-click correction POST /api/master/correct-leg blacklists fixture order-independent _match_key db.match_blacklist time-boxed7days removes leg recalculates odds market anew under2 legs slip DELETED lesson db.master_brain

Zeitzonen + Void + Live Frühabrechnung
Zeitzonen Basis Europe/Berlin Umrechnung Intl i18n.js getViewerTz/setViewerTz/applyAccountTz _toViewer formatKickoff Header timezone-switcher tz-<IANA>. Live-Frühabrechnung JEDER offene Einzel-Schein (Experten HQ-Auto Mitglieder) mit Über-Tore oder BTTS SOFORT als GEWONNEN sobald Live nötige Tore erreicht _live_bet_landed+_align_goals+_find_live_fixture (fixture_id ODER Teamnamen) Nur WIN früh Verlust wartet Full-Time Team-Über≥1.5 ausgeschlossen Läuft live_loop LIVE_POLL_SECONDS E2E 2:1/61 Über2.5&BTTS->won Über3.5->offen. Void-Timing H1 ~1h Ganzspiel ~2,5h Kombis mit Ganzspiel-Bein warten Full-Time Void NACH Settle-Pass attempts≥1 gradebare ABGERECHNET statt annulliert zeitlose sofort 12h Backstop Loop 15 Min Unit-getestet H1 60min Ganzspiel 150min H1-in-Kombi 150min. void_stale_expert_slips Grenze 3h nach geparstem Anstoß.

Tech Essentials
AI_MODEL gemini-2.5-flash cheap TEXT AI_VISION_MODEL gemini-3.1-pro-preview strong only image OCR Text->FLASH image->VISION 3310 9808 12365 stay VISION1 EMERGENT_LLM_KEY not3. React PWA Tailwind shadcn lucide FastAPI api K8s 0.0.0.0:8001 3000 Hot-Reload REACT_APP_BACKEND_URL server.py>12.5k settlement.py learning.py match_stats.py ticket_render.py. DB tips code_reads team_cache emptips_seen users role=expert is_bot translation_cache learn_stats dyn_blacklist match_blacklist push_sent odds_cache. API-Football API_FOOTBALL_KEY H2H form Europe fatigue quota batch retry. Admin admin@tipjar.com TipJarAdmin2026! ENV. 3000 burnt 30 credits day fake70 real40 left 0.05 vCPU 520 settlement loop Repo tipjarprivate-main VALHALLA

Experten-UI + Bot Voting 🔥
Experten-Panel entfernt Showcase inkl Master-Karte UND ExpertBanner Header vollständig entfernt Master über Header-Button erreichbar. Apex-Box profile-apex-flame entfernt 🔥 neben Namen bleibt gated flamesActive ab1.9. Experten-Bots voten & verdienen 🔥 expert_vote_loop expert_bot_voting jeder Bot bewertet täglich1-4 zufällige Tipps ANDERER Experten+Master Sterne3-5 tip_ratings aktualisiert avg/count Ein Vote-Tag=+1 Serie via _bump_rating_streak 30-Tage-Serie->apex_flame=True. Bots mit apex_flame:False erstellt Flammen erst ab1.9.2026 sichtbar.

Team-Total-Quoten
_parse_odds liest auch Team-Totals Heim/Gast über/unter X.5 aus /odds-Feed robust gegen Namensvarianten Total-Home Home Team Total -> Keys home_over05/15/25 away_over... _real_odd_for mappt deutsche Team-Total-Märkte Heim über1.5 Tore {Team} über0.5 via _side_in_market Heim/Gast-Keywords ODER signifikantes Team-Namenswort auf echten Team-Total-Quoten GEPRÜFT vor Match-Total-Linie damit nie fälschlich auf Gesamt-Tor-Linie. _enrich_legs_real_odds Übersprung-Regel für Team-Über/Unter entfernt auch diese Beine echte Quoten Fallback plausibilitätsgefilterte Pool-Quote wenn Feed keinen Preis hat.

2026-08-14 Credit Battery + Member Jar Wall rebuilt in /app
Owner hatte direkt in separatem Repo Tipjarprivate gebaut -> NICHT in /app -> kam nie in Deploy -> live unsichtbar. Neu in /app gebaut deployt garantiert: CreditBattery.jsx echte user.credits/2500 CR Farbe nach Ladung <25% rot <50% amber <75% lime sonst grün. MemberJarWall.jsx 20 Materialien Wood->Galaxy nach fill received_credits+credits. Backend GET /api/users/public-jars echte Member Test-System gefiltert. App.js Import+Render unter Header. Verifiziert Screenshot Batterie 0/2500 CR rot logged out+Jar-Grid Bronze/Stone etc Endpoint200. HINWEIS memory/: laufende App liest KEINE memory-Dateien reine Notizen Kein App-Fix nötig /app/memory bleibt als Builder-Wissensbasis.

GitHub-Sync i18n.js WICHTIG
Beim Übernehmen .txt hochgeladenen i18n.js war Datei KOMPLETT dupliziert T I18nContext I18nProvider useI18n je2x -> Compile-Fehler Identifier T has already been declared. Erster Block Z1-3895 Helper+echt übersetztes T es/it/el/tr korrekt Zweiter Block angehängt keine Helper viele englische Platzhalter -> Ersten Block behalten angehängtes Duplikat ab export const T entfernt Backup /tmp/i18n_backup_original.js. Learning: Bei .txt-Uploads i18n.js immer zuerst grep -n const T = |I18nProvider|useI18n auf Duplikate prüfen dann Babel-Syntaxcheck BEVOR restart.

OPEN IDEAS - NICHT BAUEN BIS OWNER SAGT
EVERYTHING under BRAIN.md OPEN IDEAS NOT built must NOT be built automatically only when owner explicitly says build X
Includes AGB without real address only admin@tipjar.com FundMe striker gala form table motivation travel distance odds matching flashscore last-hour Bodo until30 min risk-banker team total value Sion Vaduz St.Gallen over23.5 shots in-form scorer Hall-of-Fame extend master never empty Sabah 29:14 late goals signal
One UNIQUE in-house bot per scraped tipster channel never mix personas
API-Football quotas tight always use caching never live-hit loops

