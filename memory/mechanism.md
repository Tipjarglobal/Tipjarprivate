# TIPJAR – MECHANISMUS-HANDBUCH (Single Source of Truth)

> Regel: Alles, was hier steht, gilt als IMPLEMENTIERT/verbindlich. Erledigte Aufgaben/Bugs
> werden in anderen .md ENTFERNT (nicht als „erledigt" markiert). Neue Features werden HIER
> als Mechanismus notiert. Sprache: DE. UI ist 8-sprachig: de,en,es,el,fr,it,ar,tr.

## Auth & Rollen
- JWT: POST /api/auth/login → `token`; Header `Authorization: Bearer <token>`.
- Admin: admin@tipjar.com (siehe test_credentials.md). Admin ist aus Public-Stats & Leaderboards ausgeschlossen (nur echte Mitglieder zählen).

## Zeitzonen / i18n
- User-Timezone im Profil; Anstoßzeiten werden entsprechend angezeigt.
- 8 Sprachen (locales/*.js). Neue User-sichtbare Texte IMMER 8-sprachig + RTL für `ar`.

## Coins-Ökonomie & Batterie
- Coins = `user.credits`. Verdienen: AFK Silver Coins, Gold Coins bei Sponsor-Klick, ⭐-Bewertungen, Gewinne, Geschenke.
- Batterie: max 2500. Auszahlung ab 2000+. Batterie in Raster 4 & Raster 6 anklickbar → Wallet (aufladen/spendieren). KEIN „NIEMALS UNTER 125"-Text mehr.
- Spendieren: Wallet Gift-Tab; nach Erfolg fliegende Münzen (`tipjar-boost` Event) + Leaderboard-Refresh.

## Jars (RPG-System, ANTI-GLITCH)
- Besitz ist backend-authoritativ: `user.owned_jars` (Start: nur `common_glass`). NIEMALS aus Coins ableiten.
- Freischalten der Reihe nach: POST /api/jars/acquire {jar_id} – nur der nächste Jar (`_next_unowned`), kostet `JAR_VALUES[jar]` Coins (Sink).
- Verkauf: POST /api/jars/sell {jar_id} – NET-NEUTRAL: Refund = Kaufwert + einmaliger Bonus 50% (`JAR_SELL_PRESTIGE_PCT`, nur beim 1. Verkauf je Jar via `sold_jars`). Jar wird abgegeben (aus owned entfernt). → Kein Coin-Mint möglich.
- Zustand: GET /api/jars/state → {owned_jars, sold_jars, credits, next_jar, next_cost}.
- OpenCase (max 3 aktive) via /api/jars/opencase; veraltete IDs werden beim Laden gefiltert (kein leeres Feld). Bild-Fallback JarImg: open→closed→Farbblock.
- 30 Jars, JAR_VALUES 40–500 (common_glass…infinity). „💰 +Wert"-Badge oben rechts je Jar.

## Schein-Upload (LLM-FREI!)
- OWNER-VORGABE: KEIN LLM, kein Guthaben laden. `extract_win_slip` geht direkt auf lokale Tesseract-OCR.
- Tesseract-Sprachen (Aptfile): eng,deu,spa,fra,ita,por,nld,tur,ell,ara. `_ocr_tesseract` nutzt alle installierten.
- Parser `parse_slip_text_to_legs`: erkennt DE/EN + GRIECHISCH (Άνω→Über, Κάτω→Unter, γκολ→Tore, „και οι δύο…"→Beide Teams treffen, Νίκη→Sieg, Ισοπαλία→Unentschieden; Status χαμένο/έχασε/ήττα = verloren). Markt-Normalisierung: real_odds.normalize_market (multi-lang).
- Win-Typen: gewonnen/ausgezahlt = Kombi mit ≥2 Spielen. LIVE: EIN einzelner gewonnener Live-Treffer reicht (WIN_LIVE_MIN_LEGS=1); Quoten-Hürde >1.60 nur bei Serien (2+).

## Werbe-Pillen (Kauf → erscheint automatisch)
- Stripe Flow B (emergentintegrations, STRIPE_API_KEY=sk_test_emergent, EUR). Test-Karte 4242…
- Pakete PILL_PACKAGES: rent2 300€, rent1 150€, partner 119,99€, sponsor 79,99€, vip 49,99€, fan 19,99€, supporter 9,99€ (Laufzeit 2–6 Wo).
- Flow: POST /api/pills/checkout → Stripe → /pills/success (Käufer trägt Link ein → link_status=pending) → Admin GET/POST /api/admin/pills/{id}/approve|reject → Link wird öffentlich klickbar. Pille erscheint sofort nach Zahlung in Raster 2 unter den Templates. Keine Bild-Uploads (bewusst weggelassen).

## Homepage 6-Raster (App.js)
- Reihenfolge: Raster1(Top-Partner/RENT im SponsorFeeder) → Raster2(Supporter-Templates PARTNER>SPONSOR>VIP>FAN>SUPPORTER, Preis oben links, Klick=Purchase-Window) → Header(Nav, ohne doppelte Picks) → Raster3(KI-Picks inkl. Live) → Raster4(Money + 4 Buttons, keine Batterie) → Raster5(Feedback + 💡-Lern-Hinweis) → Raster6(coole Batterie + Leaderboard) → HERO/Story/Invite/HallOfFame → Footer.
- Werbe-Pillen Standardhöhe (nach 3mm-Trim): 60px (RENT/WAZAMBA), Sponsor-Grid 41px.

## Leaderboard (echte Daten)
- GET /api/gifting/leaderboards: week/all/received/gifted aus credit_transactions(type=gift), nur echte Mitglieder. Keine Platzhalter.
- Fake-Boosts entfernt: MEMBER_DISPLAY_BOOST=0, SUBSCRIBER_DISPLAY_BOOST=0 (nur reale Zahlen überall).

## Glitch-Lexikon (KI-Muster, LLM-frei anzustreben)
- backend/glitch_lexikon.py speist Muster in den Builder. Basis-Glitches (aus confidential-Dateien):
  1) TEAM TRIFFT IMMER – Über 0.5 Team (Antwerp @1.30). 2) Quali reguläre Zeit – Thun @1.06/1.05.
  3) Unter 5.5 absurd – Porto @1.23 (rote @1.25 Linie gelöscht). 4) Shots – Sabah @1.41.
  Money: PAOK Zafeiris Over 0.5 shots @1.33; Almeria -1 AH + Over 1.5 @2.13. Extra: Palermo +0,5 @1.80.
- Confidential-Seiten (statisch, privat): /confidential.html (Menü), /tracker.html (10 Einträge GRÜN/ROT/VOID/PENDING), /confidential_basis.html.

## Deployment
- Preview = dev (hier). Production = tipjarglobal.com (Änderungen erst nach Save to GitHub → Deploy).
- Aptfile installiert Tesseract-Sprachen beim Deploy.
