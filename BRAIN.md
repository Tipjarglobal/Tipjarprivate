# TipJar — BRAIN.md
_Konsolidiert 2026-08-14 (Owner-Befehl: memory/ gelöscht, alles in Root BRAIN.md + MEMORY.md)._
_Neue Notizen NUR hier oder in MEMORY.md — NIEMALS wieder einen memory/ Unterordner anlegen._


# ===== HANDBOOK.md =====

# 📘 TipJar Global — AGENTEN-HANDBUCH (bitte VOR jeder Arbeit lesen)

> Zweck: Der Owner will KEINE Anfängerfragen mehr. Alles Nötige steht hier. Latest Owner-Regel gewinnt immer.

---

## 0) ⚠️ DIE 7 WICHTIGSTEN REGELN FÜR DEN AGENTEN
1. **Sprache: IMMER Deutsch** antworten. Der Owner spricht Deutsch.
2. **KEINE Rückfragen zu Umfang/Wortlaut/„ersetzen ja/nein".** Owner gibt eine Codemining-Regel → SOFORT umsetzen. Die neueste Regel gewinnt immer, auch wenn sie einer älteren widerspricht.
3. **Zwei Umgebungen:** Du arbeitest in der **PREVIEW**. Der Owner schaut fast immer auf **PRODUCTION = https://tipjarglobal.com** (Live). Änderungen erscheinen dort ERST nach **„Save to Github → Deploy"**. Wenn der Owner sagt „geht nicht/ist falsch" → zuerst prüfen: schaut er Preview oder Live? Meistens Live + nicht neu deployt.
4. **Keine Demo-/Beispiel-Einträge im Codemining.** Nie hochladen, nie seeden. Beendete Reads NIE anfassen.
5. **Codemining-Text-Mappings sind Gesetz.** Nicht „schlauer" machen, nicht eigene Logik drüberlegen.
6. **Keine „Lotto"-Picks** (generische glatte Siege ohne Edge, willkürliche „Unter 3.5"-Polster).
7. **Nur Fußball. Keine russischen Spiele** (Boykott — Russland/Moskau/etc. sind geblacklistet, auch in OCR-Übersetzungen).

---

## 1) WAS IST DIE APP?
**TipJar Global** — eine KI-gestützte Sportwetten-Tipp-Plattform (PWA). Kernbausteine:
- **TipJarMaster / TipJarHQ**: automatische KI-Tipp-Generierung (Bet-Builder, Kombis, Value-Picks).
- **Codemining** (Herzstück): Der Owner lädt Screenshots von **Trap-Buchmacher-Scheinen** hoch (z.B. „Akku des Tages", Boost-Angebote von Anbietern, die den Spieler in die Falle locken — NICHT Bet365). Die Vision-KI liest den Schein per OCR und spielt bewusst **DAGEGEN** (Counter-Pick) oder gibt **NO BET**.
- **Master Avatar**: zeigt Top-Picks (2 pro Ansicht, manuelles Wischen, nie vergangene Spiele; Teams/Liga/Datum/Uhrzeit).
- **Settlement-Engine**: rechnet Tipps automatisch gegen echte Ergebnisse via **API-Football** ab.
- **Mehrsprachig**: Basissprache Codemining = Englisch, Auto-Übersetzung nach Deutsch/Griechisch je nach User-Sprache.

---

## 2) TECH-STACK & ARCHITEKTUR
- **Frontend**: React PWA (`/app/frontend`), craco, TailwindCSS, shadcn/ui, lucide-react, sonner (Toasts).
- **Backend**: FastAPI (`/app/backend`), alle Routen mit **`/api`**-Prefix (Kubernetes-Ingress).
- **DB**: MongoDB (via `MONGO_URL`, `DB_NAME` aus `backend/.env`).
- **Hosting**: Kubernetes, Supervisor-managed. Backend intern `0.0.0.0:8001`, Frontend `3000`. Hot-Reload aktiv.
- **URLs/Secrets**: NUR aus `.env`. Frontend nutzt `process.env.REACT_APP_BACKEND_URL`. NIE hardcoden.

### Wichtige Dateien
- `/app/backend/server.py` — **Riesig (>12,5k Zeilen)**. Enthält: KI-Generierung, Master-Loops, **Codemining-OCR + Interpret-Logik**, Auto-Übersetzung, alle Endpoints. Bei Regex-Änderungen in `_code_read_interpret` VORSICHTIG sein (Nachbarregeln nicht brechen).
- `/app/backend/settlement.py` — Grading/Abrechnung, API-Football-Events, `judge_market`.
- `/app/backend/learning.py` — KI-Gedächtnis/Veto-Logik (Trefferquote je Muster).
- `/app/backend/match_stats.py` — H2H, Europapokal-Müdigkeit, Formanalyse.
- `/app/frontend/src/components/CodeReading.jsx` — Codemining-UI (Karten, Verdicts, Haken, Löschen).
- `/app/frontend/src/components/MasterAvatar.jsx` — Avatar-Sprechblasen.
- `/app/frontend/src/components/AdminResetBar.jsx` — Homepage-Reset für Pregame-Slips.
- `/app/frontend/src/App.js`, `/app/frontend/src/i18n.js` (Übersetzungen).

### Wichtige Endpoints
- `GET /api/code-reading` — liefert `{count, reads (aktiv), finished (beendet)}`. Ruft beim Öffnen automatisch das **Self-Healing** auf.
- `POST /api/admin/code-reading/scan` — startet Vision-OCR-Scan aus hochgeladenen Bildern (async Job). Neue Reads bekommen automatisch `verified: True`.
- `GET /api/admin/code-reading/scan-status/{job_id}`
- `POST /api/admin/code-reading/manual` — manueller Einzel-Read (bleibt `verified` = false).
- `DELETE /api/admin/code-reading/{id}` — Einzel-Read löschen.
- `POST /api/admin/code-reading/{id}/verify` — „Geprüft"-Haken toggeln (Body `{verified: bool}`).
- `POST /api/admin/code-reading/clear-active` — ALLE aktiven Reads löschen (beendete bleiben).
- `GET /api/master/avatar` — Avatar-Picks.
- `POST /api/admin/pregame/regenerate` — Pregame-Slips neu generieren.
- `GET /api/learning/stats` — ehrliche Trefferquote je Muster/System.
- `POST /api/admin/learning/refresh` — Settlement + Learning refresh.

### DB-Schema (grob)
- `tips`: {id, status, kickoff, category, is_parlay, legs[], master_category, combo_odds, admin_edited, source, from_codemining, ...}
- `code_reads`: {id, home, away, league, kickoff, **code_market** (Original-Code), **our_market** (unser Pick), **read** ("counter"|"no_bet"), reason, **pattern**, stars, **outcome** ("won"|"lost"|"push"|"info"), score, goal_minutes, code_outcome, **verified** (bool), created_at, expires_at}

---

## 3) CODEMINING-PHILOSOPHIE (Owner-Denke)
Trap-Scheine sind gebaut, damit DU verlierst. Wir lesen jeden Leg und nehmen die **sichere Gegen-Lesart** — oder NO BET. Wichtig: **nur Trap-Anbieter hochladen, NIE Bet365** (deren Quoten sind fair). Es geht NICHT um Quoten, sondern zu verstehen, wie die anderen Buchmacher denken.

### 🎯 DIE CODE→PICK-REGELN (aktueller, gültiger Stand — genau so umsetzen)
| Code des Trap-Buchmachers | UNSER Pick |
|---|---|
| **Glatter Sieg / 1X2 / „Team gewinnt" / S1 / S2 / Heimsieg / Auswärtssieg** | **`<dieses Team> Draw No Bet (DNB)`** (verliert nicht; Remis = Einsatz zurück) |
| **Doppelte Chance (1X / X2) / „Team gewinnt nicht"** | **NO BET** (dagegen = X2 spielen = Risiko) |
| **Handicap (glatt, z.B. -1.5)** | **NO BET** |
| **Team-Total Über (Team soll 2+/3+ machen, „Gesamtzahl 1 Über 1.5", „Team 1 Über 1.5")** | **`Asiatisch Über 2.0 Tore`** (keine Team-Tor-Wetten, v.a. nicht in Großbritannien) |
| **Match „über 3.5 Tore" / „genaue Zahl N oder weniger – Nein" (N≥3.5)** | **`Asiatisch Über 2.0 Tore`** |
| **Match „über 1.5 Tore"** (bzw. „genaue Zahl 1 oder weniger – Nein") | **`Über 1.5 Tore` BEHALTEN** (sauberste sichere Linie) |
| **Match „über 2.5 Tore"** | **NO BET** (zu locker) |
| **Nächstes Tor / exaktes N-tes Tor / „kein 4. Tor" (Salzburg-Typ)** | **`Asiatisch Über 2.0 Tore`** |
| **Team trifft NICHT („Über 0.5 – Nein", Clean Sheet)** | **`<Team> trifft (Über 0.5 Tore)`** / BTTS |
| **Tor in engem Zeitfenster (z.B. 46–60 Min)** | **`<Team> Über 0.5 Tore`** (breiter, sicher) |
| **Frühes Remis / Ergebnis in 15./20./30. Min** | **`Über 0.5 Tore 1. Halbzeit`** |
| **Team trifft SPÄT (letztes Tor 55–90 / 2. HZ)** | **`<Team> trifft bis zur 60. Minute`** |
| **Verschachtelte DC-Kombi (1X/X2 + Total), z.B. Everton–Colo Colo** | **`<Team> +2.5 (Handicap)`** |
| **Underdog +1/+1.5 Handicap** | **`<Favorit> -1 (Handicap)`** (2+ = gewonnen, genau 1 = Push) |
| **„Team nicht zweimal treffen"** | **`<Team> Unter 2.5 Tore`** |

**Asiatisch Über 2.0 Tore Grading:** 3+ Tore = **gewonnen**, genau 2 Tore = **Push (Einsatz zurück)**, ≤1 = verloren. Sehr sicher (~1.20).
**DNB Grading:** Team gewinnt = gewonnen, Remis = **Push**, Team verliert = verloren.

> Der Owner sieht Asiatisch Über 2.0 gern als „safe Default" statt NO BET (siehe seine Nachricht). Wenn ein Code Tore erwartet und kein sauberer team-spezifischer Counter passt → Asiatisch Über 2.0.

### Self-Healing (WICHTIG gegen „ich hab's korrigiert, es bleibt trotzdem")
- `_purge_and_refresh_code_reads()` läuft bei jedem Öffnen von `/api/code-reading`.
- Es re-interpretiert **offene** (unabgerechnete) Reads neu, WENN das frische Muster in **`_REINTERP_RULES`** steht (u.a. `match_over_asian2`, `match_over_clean`, `team_total_over_counter`, `team_not_twice`, `goal_window_broaden`, `underdog_plus15_fav_minus1`, `team_total_under_low`).
- Es überspringt: abgerechnete Reads (haben `outcome`), und `_is_straightwin_code`-Codes (die laufen über `_code_straightwin_decision` = DNB).
- ⚠️ Wenn eine neue Regel greifen soll, MUSS ihr Muster in `_REINTERP_RULES` sein, sonst aktualisieren sich alte Einträge nicht.
- Neue Regeln greifen auf Live erst **nach Deploy**.

### Verdict-Farben (CodeReading.jsx, Beendet-Tab)
- Counter **gewonnen** → grün „CORRECT"
- Counter **verloren** → rot „UNCORRECT"
- Counter **Push** (DNB-Remis / Asian genau 2) → himmelblau **„EINSATZ ZURÜCK"**
- NO BET, Trap-Code kam NICHT → blau „CORRECT" (uns gerettet)
- NO BET, Trap-Code KAM doch → orange „UNCORRECT"

### „Geprüft"-Haken (verified)
- Admin kann pro Karte (aktiv + beendet) einen grünen Haken toggeln (`BadgeCheck`).
- **Screenshot-Uploads** bekommen den Haken **automatisch** (`verified: True`).
- **Manuelle** Einträge bleiben ungeprüft, bis der Admin sie abhakt.

---

## 4) INTEGRATIONEN
- **API-Football** — braucht `API_FOOTBALL_KEY` (Owner-Key). Für H2H, Form, Europapokal-Müdigkeit, Fixture-Lookup, Settlement. Quota-geschützt (Batch-Caps, Retry-Budget).
- **Emergent LLM Key** — Gemini (Vision-OCR für Codemining + Textgenerierung). NIE eigene SDKs installieren; über die Emergent-Integration.
- Weitere Scraper (Telegram-Kanäle, Totis Sports, Forebet, Predictz, Statarea) füttern NUR den normalen Tipp-Feed / Bot-Tipster / Master — **NICHT** das Codemining.

---

## 5) UMGEBUNGEN & DEPLOYMENT (der häufigste Reibungspunkt!)
- **PREVIEW** = Entwicklungsumgebung des Agents. Hier testen/ändern.
- **PRODUCTION** = **https://tipjarglobal.com** (Live). Der Agent hat KEINEN direkten Zugriff auf die Live-DB.
- Ablauf, damit Änderungen live gehen: **„Save to Github → Deploy"** (dauert ~10–15 Min).
- Live-DB-Daten (z.B. ein alter Salzburg-Eintrag) heilen sich nach Deploy beim Öffnen des Feeds selbst — sofern die Regel + Muster in `_REINTERP_RULES` deployt sind.
- Bei reinen Production-Themen (Env-Var, Domain) → Emergent Support (support@emergent.sh).

---

## 6) ADMIN-ZUGANG (Test)
- E-Mail: `admin@tipjar.com`
- Passwort: `TipJarAdmin2026!`
(Auch in `/app/memory/test_credentials.md`.)

---

## 7) OFFENE / GEWÜNSCHTE FEATURES (Backlog)
- **Telegram-Auto-Post**: jeder neue Master-Slip, Avatar-Pick, Gift automatisch in einen Telegram-Kanal.
- **Lotto-Filter verschärfen**: „Team Über 0.5" nach echter Tor-Wahrscheinlichkeit filtern; „Unter 3.5/4.5"-Polster aus Same-Game-Buildern raus.
- **Stripe-Zahlungen & PayPal-Auszahlungen**.
- **Live-Picks** („nächstes Team das trifft", „3+ Ecken nach 70. Min") — blockiert bis Settlement zuverlässig.
- **Haken-Filter**: Aktiv-Tab optional nur geprüfte Codes zeigen.

---

## 8) ARBEITSWEISE, DIE DER OWNER ERWARTET
- Regel bekommen → **direkt im Code umsetzen** (meist in `_code_read_interpret` / `_code_straightwin_decision` in `server.py`), testen (`python3 -c` gegen die Interpret-Funktion), fertig.
- Muster ggf. in `_REINTERP_RULES` aufnehmen, damit bestehende Einträge self-healen.
- Danach den Owner erinnern: **auf tipjarglobal.com erst nach Deploy sichtbar.**
- Keine langen Rückfrage-Ketten. Bei echter Mehrdeutigkeit: EINE präzise Frage, sonst sinnvolle Annahme + später nachjustieren.
- Nichts an beendeten Codemining-Reads oder an der Preview/Prod-Konfiguration kaputt machen.

# ===== owner_preferences.md =====

# Owner-Präferenzen (WICHTIG — immer befolgen)

## Kommunikation
- Sprache: **IMMER Deutsch**.
- **KEINE Rückfragen bei Codemining-Regeln.** Der Owner gibt exakte Text-Mappings (z.B. „Cobresal gewinnt → Cobresal DNB", „1X + Unter 2.5 → Underdog +2.5 Handicap"). Diese **direkt umsetzen**, NICHT nachfragen zu:
  1. Umfang (generell vs. einzelnes Team) → immer GENERELL annehmen.
  2. Wortlaut/Markt-Text → den vom Owner genannten Wortlaut übernehmen.
  3. „Soll ich die alte Regel ersetzen? Ja/Nein" → ja, ersetzen. Die neueste Owner-Regel gewinnt immer.
- Owner wurde am 2026-08-01 explizit sauer über genau diese 3 Rückfragen → NIE WIEDER STELLEN.

## Codemining-Philosophie
- Owner-Text-Mappings sind Gesetz. NICHT „schlauer" machen, NICHT eigene Logik drüberlegen.
- Keine „Lotto"-Picks (generische Siege ohne Edge, „Unter 3.5"-Polster).
- Keine Demo-/Seed-Einträge in den aktiven Codemining-Feed. Beendete Reads NIE anfassen.

## Deployment
- Owner schaut oft auf Live-Seite `tipjarglobal.com` statt Preview. Bei „geht nicht/ist falsch" → daran erinnern: erst „Save to Github → Deploy".

# ===== master_system_strategy.md =====

# TipJarMaster — Στρατηγική Συστημάτων (owner-teaching, 2026-06)
Ο Master ΠΡΕΠΕΙ να τα ξέρει αυτά και να χτίζει/δείχνει συστήματα σωστά.

## Βασικές έννοιες
- **Στήλες (columns):** κάθε στήλη = ένα ολόκληρο δελτίο (ένας συνδυασμός). Το σύστημα = άθροισμα
  συνδυασμών.
- **Ποντάρισμα = πολλαπλασιαστής:** μπαίνει κάτω. Το συνολικό κόστος = πολλαπλασιαστής × αριθμός στηλών.
  Π.χ. 20 στήλες → πληρώνεις 20× τον πολλαπλασιαστή.
- **Banker (B):** σημείο που θεωρείς σίγουρο και «κλειδώνεται» σε ΚΑΘΕ στήλη. Ο banker ΜΕΙΩΝΕΙ τις στήλες
  → κάνει το δελτίο φθηνότερο. Οι bankers πρέπει να έρθουν ΟΛΟΙ.
- **Ζητούμενα:** τα υπόλοιπα (μη-banker) ματς. Μερικά από αυτά ΕΠΙΤΡΕΠΕΤΑΙ να χαθούν.
  Σύστημα «X στα Y» → από τα Y ζητούμενα φτάνει να πετύχεις X.

## Μαθηματικά στηλών (από bookmaker screenshots)
Χωρίς bankers, με N επιλογές: k-fold = C(N, k).
  Παράδειγμα N=6: Singles=C(6,1)=6, Doubles=15, 3-folds=20, 4-folds=15, 5-folds=6, 6-fold=1.
  Heinz (6 επιλογές) = doubles+trebles+4+5+6 = 15+20+15+6+1 = 57.
Με **B bankers** (οι bankers μπαίνουν σε κάθε στήλη): ένα "k-fold" = οι B bankers + (k−B) από τα (N−B)
ζητούμενα → **στήλες = C(N−B, k−B)**.
  Παράδειγμα N=6, B=2 (επιβεβαιωμένο από screenshot): 3-folds=C(4,1)=4, 4-folds=C(4,2)=6,
  5-folds=C(4,3)=4, 6-fold=C(4,4)=1, Heinz=16, Double=1.

## Πότε αξίζει σύστημα
- **8+ παιχνίδια** → εκεί αξίζει πραγματικά.
- Αν ΟΛΕΣ οι αποδόσεις είναι χαμηλές (~1.40) → ΔΕΝ αξίζει σύστημα 3/4. Τουλάχιστον βάλε 1 banker για να
  μειώσεις μια στήλη, ζητώντας 2/3.
- Όσο ψηλότερες οι αποδόσεις (π.χ. 2.40 παντού) ή όσο ψηλότερη η απόδοση των banker, τόσο ψηλότερα πάει
  το ταμείο.

## Στρατηγικές banker
1. **Πρώτα-στην-ώρα:** βάλε banker τα πρώτα ~5 ματς που ξεκινούν χρονικά. Αν κάνεις 4/4 ή 5/5 στα
   πρώτα, αρχίζει η «παρέλαση» γιατί απομένουν πολλά ζητούμενα και ζητάς λίγα.
   Παράδειγμα: 13 ματς @1.20. Αντί για παρολί 13/13 (δεν αρέσει), banker τα πρώτα 9 → σύστημα 11/13
   (~4 στήλες). Αν ξεκινήσεις 9/9, έχεις δικαίωμα να χάσεις ένα.
2. **Ασφαλείς Over:** αρκετά Over 1.5 α' ημιχρόνου ή Over 2.5 στον αγώνα ως bankers. Αν κάποια πάνε
   void, δεν τρέχει τίποτα.
3. **Ρισκαδόρικος banker (fun / «παρέλαση»):** π.χ. Pavlidis hat-trick @10, ή Παναθηναϊκός τελικό 2-2.
   Τράβα ένα περίεργο ζευγάρι (π.χ. Χ ημιχρόνου + άσο τελικό σε ένα ματς, άσος ημιχρόνου + άσος τελικό
   σε άλλο) που η δυάδα βγάζει ~10, μαρκάρισέ τα banker, και κόλλα εύκολα ζητούμενα (Real/PSG/Barça)
   από πίσω. Αν πιάσει ο ρίσκο-banker → τεράστιο ταμείο.

## Void σε σύστημα
Τα void βγαίνουν από το σύνολο (μικραίνει το Y). Το «X στα Y» γίνεται «X στα (Y−void)» και το ζητούμενο
δεν ξεπερνά ποτέ όσα απομένουν.

## ΥΛΟΠΟΙΗΘΗΚΕ (2026-07-31)
- Ο Master μαρκάρει bankers στα συστήματά του: επιλέγει τα ασφαλέστερα σκέλη (χαμηλότερη
  απόδοση) ΚΑΙ αποφεύγει market-types με κακό banker-ιστορικό (learning). Το ticket + η κάρτα
  δείχνουν το banker badge (ΣΤΑΝΤΑΡ/Banker). Αναφέρει «System X/Y · N Banker», χωρίς μεγάλη ανάλυση.
- Abrechnung (settlement.py): χαμένος banker → όλο το σύστημα χάνεται. Αλλιώς X-αus-Y (κερδίζει
  μόλις won>=need, χάνει όταν γίνει ανέφικτο). Void βγαίνουν από το σύνολο.
- ΜΑΘΗΣΗ ΑΠΟ ΛΑΘΗ (learning.py): πλέον μαθαίνει ΑΝΑ ΣΚΕΛΟΣ από τα δικά του settled συστήματα +
  ειδικά buckets `banker_<market>` για λάθος bankers. Ο builder συμβουλεύεται `learn_verdict` →
  veto σε ό,τι χάνει, boost σε ό,τι κερδίζει. Ανανεώνεται περιοδικά (refresh_learning).

## ΧΡΟΝΙΚΗ ΣΕΙΡΑ BANKER (owner teaching 2026-07-31, κρίσιμο)
- Banker τα ΠΡΩΤΑ (νωρίτερα) σίγουρα ματς → κλειδώνει νωρίς η πρόοδος, μετά «παρέλαση» με τα ζητούμενα.
- ΠΟΤΕ banker στο ΤΕΛΕΥΤΑΙΟ/νυχτερινό ματς: αν πιάσεις τα πάντα και χάσεις το νυχτερινό banker = χειρότερο.
- Άρα: τα ζητούμενα ας είναι τα αργότερα ματς· ο banker φεύγει από το τελευταίο kickoff.
- ΥΛΟΠΟΙΗΘΗΚΕ: ο Master διαλέγει banker με σειρά (learning-safe → νωρίτερο kickoff → χαμηλή απόδοση)
  και ΑΠΟΚΛΕΙΕΙ το ματς με το αργότερο kickoff από banker. nb=min(2 αν n>=5 αλλιώς 1, n-2) ώστε να
  μένουν πάντα >=2 ζητούμενα.

## ΚΑΝΟΝΕΣ ΠΟΙΟΤΗΤΑΣ + «ΡΙΣΚΟ-BANKER → ΠΑΡΕΛΑΣΗ» (2026-07-31)
- ΠΟΤΕ banker για να «κλείσεις» το δελτίο: ο banker πρέπει να είναι πραγματικά σίγουρος (χαλαρός,
  χαμηλή απόδοση). Υλοποίηση: BANKER_MAX=1.55 + όχι veto market· αν δεν υπάρχει σωστή βάση banker →
  ο Master ΔΕΝ φτιάχνει σύστημα, γυρίζει σε απλό Kombi.
- ΠΟΤΕ ρίσκο ζητούμενο για γέμισμα: χαλαρά πράγματα (π.χ. ΠΑΟΚ over 2). Τα ζητούμενα μένουν στη
  ζώνη ασφαλών αποδόσεων του pool.
- «ΡΙΣΚΟ-BANKER → ΠΑΡΕΛΑΣΗ» (νέο, `master_riskparade_build`): 1×/ημέρα στο mittel (system_style=risk).
  Παίρνει ΕΝΑ ρίσκο, υψηλής απόδοσης pick (3.0-12.0) ως banker (το «αγκίστρι») και κρεμάει από πίσω
  3-4 χαλαρά ασφαλή ζητούμενα (1.10-1.55). System (N-1)/N: ο ρίσκο-banker ΠΡΕΠΕΙ να έρθει (banker),
  1 ζητούμενο μπορεί να χαθεί. Αν πιάσει ο banker → παρέλαση/μεγάλο ταμείο. Δοκιμάστηκε: System 4/5
  @12.99, banker Über 3.5 @5.00 + 4 ασφαλή.

## BANKER = ΤΑ ΝΩΡΙΤΕΡΑ (owner 2026-07-31, ξανά με live παράδειγμα)
Λάθος ημέρας: banker 4 ματς που δεν ξεκίνησαν, ενώ 3 νωρίτεροι νικητές έμειναν ζητούμενα («θα ήμουνα
3/3 στα πρώτα»). ΔΙΟΡΘΩΘΗΚΕ: η επιλογή banker ταξινομεί ΠΡΩΤΑ κατά kickoff (νωρίτερα → banker), μετά
χαμηλή απόδοση· φίλτρο ασφαλείας (odds<=1.55, όχι veto) + εξαίρεση του τελευταίου kickoff. nb=min(3 αν
n>=5 αλλιώς 1, n-2). Ρίσκο-banker δομή = ελεύθερη επιλογή (τώρα: 1 high-odds banker + χαλαρά ζητούμενα).

## RISK CATEGORY → «ΝΟΣΤΙΜΑ» + ROLES (owner 2026-07-31)
- Τα risk bankers του Master = «νόστιμα» markets: ημίχρονα/τελικά (HT/FT) & σκόρερς, δεμένα ως ΖΕΥΓΟΣ
  δύο ματς που ξεκινούν ~ίδια ώρα (±90') — `master_riskparade_build`: προτιμά _is_tasty markets,
  ζευγαρώνει 2 tasty same-time, combined <=15.
- Τα ζητούμενα από πίσω = ΔΩΡΑ (gift) + VALUE picks (χαλαρά). `_master_leg_candidates` επιστρέφει τώρα
  `category` ώστε να ξεχωρίζουν gift/value. Fallback σε γενικό ασφαλές pool αν <3 gift/value.
- Single-pick pool: lookahead ήδη 5 μέρες (SMART_LOOKAHEAD_H=120) → καλύπτει 48h+. Παράγεται από
  predictions/στατιστικά/codemining/scorer/HT-FT/K.o.-Duell/mental/gifts. Ο Master διαλέγει ό,τι του αρέσει.

## Owner-Treffer / Muster-Notizen (bestätigt vom Owner)
- 2026-06: Owner lag RICHTIG — Bodø/Glimt trifft VOR der 30. Minute (Frühstarter). Im Codemining
  ("Code-Reading"/Smart Picks) entdeckt/bestätigt. → Bodø/Glimt-Heimspiele: "Tor vor 30. Min /
  frühes Tor" ist ein wertvolles wiederkehrendes Muster. Bei künftiger Live-/Frühtor-Logik oder
  Smart-Picks für Bodø/Glimt berücksichtigen.
- 2026-06 (Ergänzung): Owner: "Bodø trifft bis zur 30. Minute" kann man als RISK-BANKER probieren.
  → Kandidat für master_riskparade / Risk-Banker: Bodø/Glimt Heimspiel "Tor vor 30. Min" (@~1.30-1.5)
  als risk-banker-Bein testen (nur wenn abrechenbar via API-Football HZ/Minute-Events).

## Codemining Owner-Feedback (bestätigte Treffer)
- 2026-06: Widzew Łódź (Wisla Płock – Widzew) endete 0-0. Owner nahm "Unter 2.5" (Gegen-Pick) → gewonnen.
  Counter-Read für "S2 + Gesamtzahl 2 Unter 2.5 Nein" (Auswärts muss 3+ treffen) → deckeln auf Unter 2.5/3.5.
- 2026-06: Dundee United – Rangers endete 1-1. Owner: "no bet 2 war sehr richtig" → NO-BET auf glatten
  Rangers-Sieg (1X2/Sieg2) war korrekt. NO-BET-Logik für glatte Siege bestätigt.

## British-Isles-Regel (Owner 2026-06) — WICHTIG für Geschenke/Picks
- England/Schottland/Wales/Irland/Nordirland: "jeder schlägt jeden", 3:0 kann 0:3 werden. 1X2 und
  "wer zuerst 2 Tore" sind dort reines LOTTO (v. a. Saisonstart, wenn Teamform unbekannt = nur Schätzung).
- REGEL: Auf britischen Inseln KEINE direktionalen Geschenke (first_two / Halbzeit-Sieg / 1X2).
  Stattdessen Totals-Geschenk "Über 2 asiatische Tore" (Push/Rückgabe bei genau 2) — nur wenn Torspiel
  (Prognose >=3 / over25 & 0:0 unwahrscheinlich).
- Detektor `_is_british_isles`: NUR nach Nation/Ländercode (england/scotland/wales/ireland, eng./sco./
  wal./nir./irl.) — NIE nach "championship"/"premier league" (sonst USL/Ghana Fehlalarm).

# ===== master_learnings.md =====

# TipJar Master / Tipp-Logik — Owner Learnings (2026-07-30)

Der Owner ist frustriert über schwache Master-Picks. Diese Regeln MÜSSEN eingebaut werden.

## 1. TIMING bei "Team trifft" / Über 0.5
- Fehler: App sagte "The New Saints treffen" → stimmte, ABER erst 91'. Owner hatte "trifft bis 85'" getippt → verloren.
- Regel: Nicht blind "Team trifft" sagen. Berücksichtigen WANN ein Team typischerweise trifft.
- Markiere Teams, die LOCKER früh treffen (bis 40', 60', 75').
- Ausgabe entweder:
  - generell "Über 0.5 Tore bis zur 60. Minute", ODER
  - konkretes Team: "Team X trifft bis zur X. Minute"
  - X ist IMMER eine von: 40, 60, 75, 90.
- Teams, die nur spät treffen können, NICHT für frühe Zeitfenster empfehlen.

## 2. "Durstig auf Tore" (goal-thirst) — Ausschlüsse
- Grundregel bleibt: Team, das letztes Spiel NICHT getroffen hat, trifft wohl im nächsten. (Pafos-Beispiel war korrekt: Pafos 4-0.)
- ABER: Master gab fälschlich "Hajduk trifft" (Auswärts-Underdog) → Pafos-Hajduk 4-0, Hajduk 0. → Master soll die STARKE Seite backen, nicht blind den durstigen Auswärts-Underdog.
- Qarabag: hatte ZUHAUSE nicht getroffen → auswärts noch schwerer → evtl. schlecht geworden → NICHT in Durstig-Statistik aufnehmen.
- Ausschluss: Teams, die selbst zuhause nicht treffen / vom Modell auf 0 Tore gesetzt werden / klare Auswärts-Underdogs.

## 3. Statistik-UI (erste Halbzeit)
- Kürzer & übersichtlicher machen — Owner will nicht so viel scrollen.
- KEINE doppelten Einträge: z.B. "Paok - Dinamo Tor erste HZ" darf NICHT zweimal erscheinen
  (einmal weil man für Paok spricht, einmal für Dinamo). Pro Spiel nur EIN Eintrag.

## 4. Konkrete beobachtete Ergebnisse (zur Kalibrierung)
- Pafos - Hajduk 4-0 (Master lag mit "Hajduk trifft" falsch)
- Paok - Konstantelias: 2 Tore
- Panathinaikos: beide treffen bereits 1-1
- Qarabag: zuhause kein Tor

## 5. Master-Avatar (neue Idee)
- Im Master-Kanal einen Master-Avatar mit Sprechblase.
- Er sagt konkret, was sicher passieren wird, z.B.:
  "Pafos hatte nicht getroffen und wird diesmal treffen. Zuhause sind sie stark."

## Kosten (separat, vom Owner genehmigt)
- B) Text-LLM (Analyse/Moderation/Übersetzung) auf günstiges Modell (Gemini Flash), Vision-OCR bleibt Pro.
- C) Scraper: nur Picks mit guten Sternen posten.

## 6. K.o.-Duelle: NUR die starke / aggregat-führende Seite backen (2026-07-30)
- Fehler (Owner-Screenshots, Wazamba): "So viele gute Spiele und wir backen Torshavn."
  - HB Torshavn: Hinspiel 0:2 hinten, auswärts Underdog → Rückspiel 0:3 → Handicap +0.75 VERLOREN.
  - Hajduk Split: 0:2 hinten, auswärts → "Über 0.5 Tore" → Pafos 4:0, Hajduk 0 Tore → VERLOREN.
  - Gewinner-Seiten waren die STARKEN: Pafos (0:2 vorn → 4:0), Nordsjaelland (→ 6:0), Derry Under 3.
- REGEL: In Zwei-Bein-Duellen (und generell bei klarem Favoriten) NIE die schwache/zurückliegende
  Auswärts-Seite backen (kein Sieg/Handicap/"trifft"/Über 0.5 auf den Underdog). IMMER die
  aggregat-führende / starke Seite. Umgesetzt:
  - `_favourite_side_map` + `_leg_backs_clear_underdog` (server.py): Master-Bein-Pool
    (`_master_leg_candidates`) droppt team-spezifische Beine auf der klaren Underdog-Seite (fav_prob≥62).
  - `goal_thirst`: klare Underdogs (fav_prob≥62, Gegenseite Favorit) werden aus "trifft"-Liste
    ausgeschlossen, außer das Modell erwartet selbst 2+ Tore.
  - `knockout_tie_autopost` backt ohnehin bereits den Hinspiel-Sieger (korrekt).

## 7. Avatar-Calls NUR auf verifizierte, reale Spiele (2026-07-30)
- Fehler (Owner): "Spiel existiert nicht" — ein Avatar-Call (Arges Pitesti – Miercurea Ciuc) war
  ein Phantom-Spiel aus match_predictions, das API-Football nicht bestätigte.
- Fix: `master_avatar_calls` verifiziert JEDES Spiel vor dem Posten via `resolve_team_id` +
  `find_upcoming_fixture` (auch reversed). Ohne bestätigtes Fixture (echter Anstoß im Fenster) →
  Call wird übersprungen. Nutzt reale Namen/Anstoß/Liga aus dem Fixture. Kein Phantom-Spiel mehr.
- Avatar-Sprechblase + Karten sind vollständig lokalisiert (Sprechblasen-Text via prose-Cache,
  Idle-Zeile + Tab-Label via i18n-Keys master.avatar.idle / master.cat.avatar in allen 8 Sprachen).

## 8. 10★ NUR für echte Banks — Live-"noch ein Tor" ist NIE 10★ (2026-07-30)
- Fehler (Owner): "10 Sterne Austria Über 4.5 Tore verloren — rote Karte, Spiel vorbei, sie wollten
  nicht mehr." Live-Banger in `live_autopost` vergaben pauschal `rating=10.0` für die nächste
  Over-Linie (oft "Über (total+1).5" = ZWEI Tore mehr nötig!).
- REGEL: Ein Live-Bet, der noch ein/zwei Tore BRAUCHT, ist keine Bank. Owner-Regel "live nie
  unschlagbar, Cap 7★" galt bisher nur für die Push-Anzeige, nicht für die gespeicherte Bewertung.
- Fix (`live_autopost`, server.py): Bewertung jetzt EHRLICH aus der Live-Quote abgeleitet
  (rating ≈ min(7, 1/odd·10)), gedeckelt bei 7★. "Über 4.5" (2 Tore nötig) → ~3★ statt 10★.
  Bestehende Live-Banger-Tips >7★ einmalig auf 7★ geklemmt. Analyse-Text warnt jetzt ehrlich
  (rote Karte / Zeitspiel kann kippen).
- NUANCE (Owner): "Manche Über 4.5 sind sicherer — aber ein Aggregat 5:1 mit roter Karte kann das
  Spiel früher enden." → Nicht pauschal alle Über-Linien abwerten. Kontext-Strafen NUR bei
  Gefahrensignalen (`_live_overline_penalty`): klarer Vorsprung/Blowout (|Tor-Differenz|≥3 → −2★),
  rote Karte im Spiel (aus denselben Live-Stats, kein Extra-Call → −1★), K.o.-Duell/Pokal
  (führende Seite verwaltet → −1.5★). Offene, ausgeglichene Nicht-K.o.-Spiele behalten bis 7★.
  Bei zu vielen Signalen (Rating <3★) wird die Über-Linie gar nicht mehr angeboten.

## 9. Stürmer in Galaform als Signal (2026-07-30)
- Owner: "Pavlidis hat für Benfica 4 Tore gemacht." → Ein Stürmer, der gerade einen 4-Packer
  (oder Doppelpack) gemacht hat, ist ein starkes Signal: sein Team trifft/gewinnt, und er selbst
  ist ein Top-"Anytime-Scorer"-Kandidat im nächsten Spiel.
- IDEE (noch NICHT umgesetzt — braucht Spieler-Daten aus API-Football /players): "In-Form-Scorer"-
  Boost für Avatar/Master: wenn ein Schlüsselstürmer zuletzt 2+ Tore machte, dessen Team-Über-0.5 /
  Team-Sieg höher bewerten und ggf. einen "Spieler trifft"-Call ausgeben. Owner fragen, bevor gebaut.

## 11. Hot-Scorer-Kombi = Hall-of-Fame-Schein (2026-07-30)
- Owner: "Hätten wir Konstantelias UND Pavlidis über 1.5 Tore gespielt, dann wäre der Schein in der
  Hall of Fame." → mehrere In-Form-Stürmer in EINEN aggressiven Doppelpack-Schein kombinieren.
- Umgesetzt: `master_hotscorer_combo()` (server.py, in master_loop, 1×/Berlin-Tag): findet 2–3
  brace-fähige Galaform-Stürmer (gl≥0.6) in VERIFIZIERTEN Fixtures, baut ein Multi-Match-Parlay
  "{Spieler} trifft 2+ (Doppelpack)" mit Gesamtquote → Hall-of-Fame-Kandidat. Eigener Tab
  "🔥 Torjäger-Kombi" (master_category=hotscorer). Gift-Guard aktiv.
- Zusätzlich: Avatar-Einzel-Call wird bei richtig heißen Stürmern (gl≥0.8) zu "{Spieler} — 2+ Tore
  (Doppelpack)" statt nur Anytime.
- SETTLEMENT: `_grade_player_leg` scorer respektiert jetzt `need` (line+1) → Doppelpack (2 Tore)
  korrekt abgerechnet; `settle_multimatch_parlays` wertet Spieler-Torschützen-Legs pro Fixture
  (holt player-stats). Anytime (need=1) unverändert. Unit-getestet: 2 Tore=WON, 1 Tor=LOST.

## 10. GESCHENKE haben Vorrang — keine andere KI darf widersprechen (2026-07-30)
- Owner: "Wenn das Geschenk sagt Qarabag unter 2.5, dann darf in der Statistik NICHT 'Qarabag
  trifft' stehen, der Master darf NICHT 'Qarabag über 2.5' wählen und der Mental darf es NICHT
  'über 4.5' geben. Was die Geschenke sagen, hat Vorrang — keine weitere KI kann dagegen tippen.
  Der Master soll meistens aus Geschenken, Smart-Picks und Statistiken auswählen."
- Umgesetzt (server.py): `_gift_stance_map()` liest alle offenen Geschenk-Tips (is_gift) und leitet
  je Spiel eine Haltung ab (team_over/team_under, match_over/match_under). `_conflicts_with_gift()`
  + `_gift_under_lean()` erkennen Widersprüche. Eingebaut in:
  - `goal_thirst` (Statistik "trifft") — widersprechende Teams raus.
  - `mental_autopost` — Geschenk-"unter"-Spiele bekommen keinen Über-4.5-Mental.
  - `_master_leg_candidates` — kein widersprechendes Master-Bein.
  - `master_doublepack`, `master_special_build` — Geschenk-"unter"-Spiele übersprungen.
  - `master_avatar_calls` — kein Avatar-"Fav trifft" gegen ein Geschenk.
- Regel-Nuance: Geschenk auf EIN Team ("Qarabag unter") sperrt nur dieses Team (Gegner darf
  weiter "trifft"); ein Match-"unter" sperrt jedes "über"/"trifft" im ganzen Spiel.


## 12. KEINE Feature-Vorschläge / Next Action Items (Owner 2026-07-31)
- Owner: "Frag diese 4 Sachen nicht wieder." → beim finish-Tool KEINE ausgedachten
  Feature-Ideen / Enhancement-Vorschläge auflisten. Nur bauen, was der Owner explizit sagt.
  Kurze Abschluss-Zusammenfassung ohne "Next Action Items"-Ideen.

## 8. FREUNDSCHAFTSSPIELE / TESTSPIELE — kein Torschützen-Vertrauen (Owner 2026-08-08)
- Beobachtung (Owner): Es gibt im Sommer SEHR viele Freundschaftsspiele. Aufstellungen sind NICHT scrapebar → man weiß vorher nicht, wer wirklich spielt.
- Barcelona spielte am 08.08.26 ZWEI Spiele am SELBEN Tag (Barcelona 1-0 Forest UND Udinese 1-0 Barcelona) → geteilter Kader, beide Aufstellungen schwach → "Scheiße gespielt", kaum Tore.
- REGEL: Der Master soll in Freundschaftsspielen KEINE Torschützen-/Über-Tore-Picks blind setzen. Ein starker Klubname (Barça, Bournemouth, Real …) heißt NICHT, dass die A-Elf aufläuft oder trifft.
- UMSETZUNG (Code, master_hotscorer_combo): Freundschaftsspiele werden aus der Torjäger-Kombi komplett AUSGESCHLOSSEN (Liga-Name enthält friendl/freundschaft/testspiel/φιλικ/amistoso/amichev). Zusätzlich existiert _is_domestic_league_fx (schließt friendl/cup aus) für die Ligaklassifizierung.
- MASTER-VERSTÄNDNIS (Ziel): Falls Freundschaftsspiele doch mal genutzt werden, muss der Master erkennen, welche Teams "verstärkt genug antreten" (A-Kader) um zu treffen — sonst NICHT backen. Bis Aufstellungsdaten sicher vorliegen: Testspiele meiden.

## HINWEIS ZUM BRAIN
- Alles, was der Owner mir gibt (Screenshots, Ergebnisse, Regeln), wird HIER im Brain notiert. HQ und Master lernen daraus. Dieses File ist die Quelle für Kalibrierung & Regeln.

## 9. CONTRARIAN-DENKE: "Was fickt die Scheine der größten Masse?" (Owner 2026-08-09)
- Grundprinzip: Wenn die Scraper 3-1 andeuten, kann es genauso 2-2 enden. Der Master soll IMMER denken "was fickt die Masse".
- Beobachtete Fehlschläge der Masse (Favoriten, die NICHT gewannen): Bochum-Hertha 0-1; PSV nicht gewonnen; Sporting nicht gewonnen; Wolfsburg 0-0; Darmstadt. Hunderte weitere.
- REGEL 1 — Sprechblase (Avatar) nur UNFICKBARE Aussagen: statt "Über 0.5 1.HZ" / "Torschütze" (fällt bei 0-0 durch) jetzt Rotation aus (a) "{Favorit} gewinnt mindestens eine Halbzeit", (b) "Doppelte Chance {Favorit}", (c) "Über 1,5 Tore" (nur goal-friendly). Diese gewinnen SELBST bei einem 2-2. Umgesetzt in master_avatar_calls.
- REGEL 2 — Neuer "Hard"-Bereich (master_hard_2_2): EINE tägliche Kombi aus EXAKTEN 2:2 für Fallen-Spiele. Faktoren wie gestern PSV/Sporting/Darmstadt: klarer-aber-nicht-überragender Favorit (fav_prob 50-72), BEIDE Seiten laut Prognose ~2 Tore (ph>=2 & pa>=2), Gesamt <=5, |ph-pa|<=1, keine Friendlies. Cap 6 Beine (sonst astronomische Quote). Settlement: "Genaues Ergebnis 2:2" deterministisch (judge_market Shortcut).
- Beispiel: 3 Spiele × 2:2 ≈ Quote 2197 (Owner-Idee "8000er"). Mini-Einsatz, Mega-Traum.

## 10. FLAGGEN + OCR-Feedback (Owner 2026-08-09)
- Flaggen: EINE Landesflagge oben links VOR jedem einzelnen Spiel (Single & Kombi-Beine). Die alte Flaggen-Reihe oben rechts wurde ENTFERNT. flagFor(): Country-Name → ISO2-Code (z.B. "co"→🇨🇴) → Liga-Keyword → 🌍-Fallback (jedes Spiel MUSS eine Flagge haben). NATION/LEAGUE-Maps stark erweitert (EN+DE). Master-Kombi-Beine speichern jetzt "country".
- Konnte KEINE von "Agent E3" vorbereitete Flaggen-Version im Code finden → frisch implementiert.
- OFFEN (braucht LLM-Vision-Credits zum Testen): TipJarLogic/Codemining-OCR liest Slips falsch: "FC Sion" statt "FC Sion Draw No Bet"; "Molde Über 0.5 Team-Tore" falsch übernommen. Außerdem sollen die RICHTIGEN Uhrzeiten aus dem Slip übernommen werden. → mit Owner abstimmen, bevor Credits verbraucht werden.

## 11. OCR-Prompt-Fixes (Owner 2026-08-09, Option B: nur Prompt, kein Test)
- AI_SYSTEM (TipJarLogic-Slip-Reader) + read_betslip (Win-Claim) ergänzt:
  • DRAW NO BET: 'Draw No Bet'/'DNB'/'Sieg ohne Unentschieden'/'Unentschieden keine Wette' => '<Team> Draw No Bet' (Team MUSS drin bleiben, NIE zum reinen Sieger verkürzen). Beispiel-Fehler war 'FC Sion' statt 'FC Sion Draw No Bet'.
  • TEAM-Tore Over/Under: 'Molde over 0.5' => 'Molde Über 0.5 Tore' (Team + Linie behalten, NICHT zu Gesamt-Tore machen).
  • Per-Bein 'kickoff' = exakt die neben DEM Match gedruckte Uhrzeit (nie leeren/verschieben/erfinden).
- Nicht getestet (Owner wollte Credits sparen). Bei nächstem echten Upload prüfen.
- KNOWN FOLLOW-UP (Settlement): betting_logic _leg_predicate wertet DNB-Remis aktuell als WIN (h>=a) statt VOID/Rückzahlung. Falls DNB-Beine künftig falsch abgerechnet werden → dort Remis=void nachrüsten.

## 12. DNB-Abrechnung korrigiert (Owner 2026-08-09)
- judge_market (settlement.py) hat jetzt einen deterministischen DRAW-NO-BET-Shortcut (kein LLM/Credits):
  Remis (hg==ag) => VOID (Rückzahlung); gebacktes Team gewinnt => won; verliert => lost.
  Team wird aus dem Markt gelesen ("{Team} Draw No Bet"/"{Team} DNB") und via _teams_match Home/Away zugeordnet (Default Home).
- Getestet mit 6 Fällen (Sion/Servette, Home & Away, Sieg/Remis/Niederlage) → ALLE OK.
- Gilt für Einzel- UND Kombi-Beine (beide laufen über judge_market). Void-Bein wird im Parlay als Push behandelt und die Quote neu gerechnet.
- Der frühere Follow-up (Remis-als-Win) ist damit erledigt.

## 13. Sprechblasen-Vielfalt: neue unfickbare Aussage (Owner 2026-08-09)
- Neu in der Avatar-Rotation: "{Favorit} verliert nicht zur Halbzeit" (settlement kind=ht_no_loss: f1>=o1, Favorit liegt zur HZ NICHT hinten). Überlebt selbst 0-0/2-2 zur Pause; verliert nur, wenn der Favorit zur HZ zurückliegt.
- Rotation jetzt: half_any → ht_no_loss → dc (→ over15 nur goal-friendly).
- Settlement: _special_gift_kind erkennt "verliert nicht zur halbzeit/hz"; _grade_special_gift kind ht_no_loss; _fav_side_in_fixture splittet jetzt auch auf " verliert" (Team-Zuordnung Heim/Auswärts).
- Deterministisch getestet (6 Fälle Heim+Auswärts, Sieg/Remis/Rückstand HZ) → ALLE OK. Keine Credits.

## 14. KOSTEN-SENKUNG: teures LLM-Modell nur noch für Vision (Owner 2026-08-09)
- Problem: gemini-3.1-pro-preview (AI_MODEL) lief auf JEDEM Tipp-Rating (analyze_tip) → Hauptkostentreiber. Übersetzung war NIE das Problem (bereits Flash + DB-Cache).
- Fix (core.py): AI_MODEL = "gemini-2.5-flash" (günstig, für häufige TEXT-Analyse), NEU AI_VISION_MODEL = "gemini-3.1-pro-preview" (stark, nur für Bild/OCR).
- server.py: analyze_tip (1342) + SmartLab-Fan-Hint (9240) wählen jetzt pro Aufruf: Bild vorhanden → AI_VISION_MODEL (OCR-Genauigkeit bleibt, schützt Draw-No-Bet/Team-Tore/Uhrzeiten-Fixes); nur Text → AI_MODEL (Flash). Reine Vision-OCR (Win-Slip 3310, Code-Reader 9808, Lineup 12365) bleiben auf AI_VISION_MODEL.
- Getestet: Text-Rating läuft auf gemini-2.5-flash (Log bestätigt), Rating 9.0, kein Fehler. Backend startet sauber.
- Info: App nutzt EINEN EMERGENT_LLM_KEY (nicht 3). Kosten = Modell-Wahl + Token-Volumen, nicht Übersetzung.

## 15. Englisch als Basissprache + Asian Handicap -1 + Hard-Umbenennung (Owner 2026-08-09)
- HAUPTSPRACHE = ENGLISCH. Master-Markt-Labels jetzt Englisch: "Double Chance {fav}" (nicht "Doppelte Chance"), "{fav} wins at least one half", "{fav} not losing at half-time", "Over 1.5 Goals". Combo-Titel: "🔥 Top Scorer Combo", "🎯 HARD". Hard-Beine: "Correct Score 2:2". Badge-Labels + Tabs Englisch.
- NEU in Sprechblasen-Rotation: "{fav} -1 Asian Handicap" (Sieg mit 2+ = won, mit genau 1 = VOID/Rückzahlung, sonst lost). Owner-Hauptwunsch "Lugano -1". Rotation: ah_minus1 → half_any → ht_no_loss → dc (→ over15 goal-friendly).
- Settlement: _special_gift_kind erkennt jetzt EN+DE (half_any, ht_no_loss) + neu ah_fav_1; _grade_special_gift ah_fav_1 gibt True/"void"/False; _fav_side_in_fixture bilingual (Team am Marktanfang, startswith). Einzel-Settler finalisiert deterministischen Push (void) statt Endlos-Retry (definitive_push-Flag).
- "Hard 2:2"-Bereich heißt jetzt nur noch "Hard" (Tab + Badge).
- Getestet: AH -1 Grading (5-0=won, 2-1=void, 1-1=lost, Auswärts analog) + EN-Kind-Erkennung → OK. Screenshot: Bubble zeigt "FK Crvena Zvezda -1 Asian Handicap @1.70" (EN), Hard-Tab, Flaggen pro Spiel.
- NOCH OFFEN (Owner-Wunschliste, nicht gebaut): Team-Total-Value-Picks im Master ("Sion over 1.5 team", "Vaduz over 1.5 team", "St. Gallen total over 3.5"), lockere ~10er Tore-Kombi, "over 23.5 shots"-Markt aus Experten-Reads.

## 16. Value Goals Combo + Shots-OCR + Team-Total-Englisch-Fix (Owner 2026-08-09)
- NEU master_value_goals_combo() → master_category "valuecombo", Tab "💎 Value Goals". 1x/Berlin-Tag, ~6er-Kombi (~6-15x): "{Team} Over 1.5 Goals" für starke Scorer (ph/pa>=1.8, prob>=0.45) + "Over 3.5 Goals" für torreiche Spiele (total>=3.6). Odds via _prob_over/_odds_from_prob. Keine Friendlies. Deckt Owner-Wunsch "Sion/Vaduz over 1.5 team + St.Gallen total over 3.5 + lockere 10er Kombi" ab. Getestet: 6 Beine @14.72.
- Verdrahtet: master_loop, reset-refresh, mcat-Filter, Frontend Tab+Counts+Badge.
- SHOTS-OCR: AI_SYSTEM erkennt jetzt Shots-Märkte ("Over 23.5 Shots"/"Schüsse"/"shots on target") und lässt sie als SHOTS (nicht Goals) stehen — nie in Tore umwandeln.
- BUGFIX (app-weit): localizeMarket hatte KEINE Regel für die deutsche Team-Total-Kanonform "{Team} Team-Tore Über X" → blieb bei EN-Locale deutsch. Neu: Regel + Key mkt.teamgoals (en "Team Goals", de "Team-Tore"). Jetzt zeigt EN "Team Goals Over 1.5" (Screenshot bestätigt). Betraf ALLE Team-Total-Picks, nicht nur den neuen Combo.

## 17. VALUE = schwaches Team trifft doppelt (Owner 2026-08-10)
- Gewinner-Schein (Owner): Sirius vs IF Brommapojkarna — "Brommapojkarna (schwaches/Auswärts-Team) Over 1.5 Tore" + "Total Over 3.5" als Same-Game Bet-Builder @4.75, gewonnen bei 2:2. Zweites Beispiel: AZ Alkmaar Res vs FC Eindhoven — "Eindhoven Over 1.5 + Total Over 3.5" @2.90.
- KERN-LEARNING: Der VALUE steckt darin, das SCHWÄCHERE Team zu backen, dass es ZWEIMAL trifft (Over 1.5 Team-Tore) — die Quote ist hoch, weil der Markt es unterschätzt. Kombiniert mit "Total Over 3.5" im SELBEN Spiel = großer Value.
- LEAN halten: Owner "könnte noch Tor 1.HZ / Sirius Over 1.5 dazunehmen, aber die Quote steigt kaum und mehr Beine = mehr Risiko". Also nicht überladen.
- WICHTIGE NUANCE (nicht Learning #6 widersprechen): NUR in torreichen, AUSGEGLICHENEN Spielen backen, wo BEIDE Teams treffen (min. projizierte Tore ≥1.4 pro Team, Gesamt ≥3.6). NIEMALS ein einseitiges Blowout-Underdog-"trifft".
- UMSETZUNG (server.py master_value_goals_combo): jedes Bein ist jetzt ein Same-Game-Builder "{schwächeres Team} Over 1.5 Goals" + "Over 3.5 Goals" (Gate: total≥3.6 & min(ph,pa)≥1.4 & pw≥0.40 & pt≥0.42). Fallback = einzelnes starkes Over-1.5 / Over-3.5. Schlank: 2–4 Beine, Cap Quote 60. Getestet (Mock): Brommapojkarna O1.5 @2.1 + O3.5 @1.9 korrekt gebaut. Abrechnung über bestehende settle_multimatch_parlays (2-Selektions-Beine wie Special).

## 18. WARUM „schwaches Team trifft doppelt" Value ist — die Faktoren (Owner 2026-08-10)
Owner erklärt den Sirius–Brommapojkarna-Schein (2:2, Quote 4.75) im Detail. Diese Denke soll der Master lernen:
- **Kurze Anreise / lokales Derby**: Brommapojkarna reist nur ~53 km → keine Reisemüdigkeit, das Auswärtsteam kann voll auftreten. Große Distanzen schwächen Auswärtsteams, kurze nicht.
- **H2H-Muster (STÄRKSTES Signal, umgesetzt)**: „Sirius kassiert zuhause IMMER 2 Tore von denen." Direktvergleich bestätigt: Brommapojkarna traf 2+ in fast jedem Duell (0-3, 3-2, 3-2 bei Sirius zuhause; 2-4 auswärts). → Value-Bein „schwaches Team Over 1.5" wird jetzt nur gebaut, wenn der H2H (match_stats.h2h_detailed, gecacht) real 2+ in ≥50% der letzten Duelle zeigt (`_h2h_team_scores_2plus`). Ohne H2H-Daten → Modell-Gate.
- **Tabellenkonstellation / Motivation**: Sirius steht 1. mit 10 Punkten Vorsprung → auch ein Remis tut nicht weh → verwaltet, verteidigt lockerer → offenes Spiel. Brommapojkarna (13.) hat „Punkte-Not" → maximale Aggression → trifft. (NOCH NICHT im Code — bräuchte /standings-Daten, quota. Als Mental-Modell notiert.)
- **„Fickerei-Faktor" / Contrarian**: Die MASSE kauft das Offensichtliche — „Sirius Sieg" + „Sirius Over 1.5" @1.40. Der Value liegt im 2:2 (beide treffen, hohes Total) @4.75. Immer fragen: „Was fickt die Scheine der Masse?" → Genau der Kern der Value Goals Combo (siehe auch Learning #9).
- UMSETZUNG heute: H2H-Bestätigung im Value-Builder (server.py master_value_goals_combo + `_h2h_team_scores_2plus`). Standings/Motivation + Reisedistanz bleiben als Mental-Modell (quota/Datenlage) — bei Bedarf mit Owner abstimmen, bevor gebaut.

## 19. SMART PICKS: KOMPLETTE Community-Kombi übernehmen (Owner 2026-08-10)
- Fehler (Owner-Screenshot): @TipJarLogic postete eine Kombi "Dembélé Torschuss + PSG trifft + PSG verliert nicht @1.81" (PSG–Aston Villa Finale). Die KI kollabierte das auf EIN eigenes Bein "PSG Team-Tore Über 0.5 @1.81" und erfand eigenen Text. FALSCH.
- REGEL: "Du musst IMMER die gesamte Kombi annehmen, nicht jedes Mal etwas Eigenes aussuchen und eigenen Text erfinden. Übernimm, was der Spieler nimmt, und passe den Text darauf an. Nur ändern, wenn eine Selektion zu unlogisch klingt." Nur wenn KEINE konkrete Wette vorliegt (reine Frage) darf die KI selbst einen Tipp vorschlagen.
- UMSETZUNG (server.py):
  • `generate_smart_from_idea` Prompt umgebaut: bei konkreter Wette/Slip ALLE Selektionen als `legs[]` faithfully übernehmen (nichts droppen/tauschen/erfinden), Spieler-Quoten behalten, Selektion nur bei Unlogik ändern, Analyse an die EXAKTEN Selektionen anpassen. JSON neu: is_combo, same_match, legs[], total_odds.
  • `submit_smart_idea`: bei ≥2 Beinen → Parlay-Tip. Same-Match-Builder → `combo_legs` (Abrechnung via settle_hq_combos) + display `legs`; Multi-Match → nur `legs` (settle_multimatch_parlays). market = Selektionen mit " · " verbunden, odds = total_odds. Single-Fall unverändert.
- Getestet (Mock): 3-Bein-PSG-Kombi korrekt gebaut (legs 3 + combo_legs 3, is_parlay, odds 1.81, Analyse passt). Frontend rendert legs[] automatisch als Parlay (RateWall 1308+) — keine FE-Änderung.
- NICHT mit echten LLM-Credits getestet (Owner-Kostenwunsch) — beim nächsten echten Upload prüfen.

## 20. DOPPEL-K.O.: Psychologie > Quoten (Owner 2026-08-11)
- Bei Zwei-Bein-K.o.-Duellen WENIGER auf Quoten schauen, MEHR auf Psychologie:
  • Το γκολ της τιμής: das "Ehrentor", das die schlechte/unterlegene Mannschaft am Ende doch macht.
  • Η ομάδα που πιέζει και δεν σκοράρει, στο τέλος το δέχεται: das Team, das verzweifelt drückt und einfach nicht trifft, kassiert am Ende selbst.
- AGGREGAT-REGEL (Owner-Kalibrierung, echte Ergebnisse 11.08.26):
  • Wenn das FINALE AGGREGAT für die gute Mannschaft ÜBER 4 Tore geht, trifft am Ende meist auch die schlechte Mannschaft mindestens 1 Tor. Beispiel: Dinamo Zagreb Hinspiel 5:0 → Rückspiel Žalgiris 1:2 (Debeljuh 56'), finales Aggregat 1:7 → Žalgiris hat doch getroffen.
  • Vorschlag: in solchen einseitigen Rückspielen "{schwache Mannschaft} trifft / Über 0.5 Tore" anbieten (z.B. "Žalgiris trifft über 0.5").
  • NUR SEHR WENIGE Teams treffen über ZWEI Spiele GAR NICHT: an dem Tag nur Kairat (Aggregat 0:2) und Sparta Praha (Aggregat 0:3). Also die "schlechte trifft am Ende doch"-Regel ist stark.
- ERGEBNISSE zur Kalibrierung: NEC–Olympiacos 2:1 n.V. (agg 2:1); CSKA Sofia–Panathinaikos 1:2 (agg 2:3, Ehrentor Dvali 87'); Bodø/Glimt–USG 3:2 n.V. (agg 6:5, torreich beide); Sturm–Fenerbahçe 0:1 (agg 0:3).
- HALTUNG: Hab KEINE ANGST, im Master (Hard-Bereich) ernste, schlaue Wetten zu geben. Die Master-Bereiche dürfen NICHT leer sein.

## 21. Master-Bereiche NIE leer + Beispiel-Wetten (Owner 2026-08-11)
- Genaue Ergebnisse (Hard): Olympiakos 1:1, Panathinaikos 1:1, Bodø/Glimt 2:2.
- Oder weniger Risiko: Union SG trifft 2× (Über 1.5) + Über 3.5 Tore; schwächere Mannschaft (Nijmegen) trifft und verliert nicht; die bulgarische Mannschaft trifft und verliert nicht.
- Sabah gewann mit 29:14 Torschüssen (Geschenk @1.44) UND 4:0 mit VIER späten Toren → Schuss-Dominanz + späte Tore sind ein starkes Über-/Team-trifft-Signal.

## 22. LIVE-CUTS + HZ-Tor in die Sprechblase (Owner 2026-08-11)
- HZ-Tor-Tipps LIVE komplett GECUTTET: gewinnen nur ~1 von 5 (an dem Tag Bodø, Roter Stern, Sabah alle 0:0 zur HZ). Live "Über 0.5 Tore 1. Halbzeit" wird nicht mehr gepostet.
- ALLE Live-Vierer ("Vierer-Live-Kombi") GECUTTET — schaut kein Mensch, zu kleine Community. (server.py live_autopost Abschnitt 5 → `if False`.)
- Ein SERIÖSES Pregame-HZ-Tor (kein Joker/Geschenk) gibt jetzt der MASTER in der Sprechblase (master_avatar_calls: neue Option "ht_goal", nur bei über25 + total≥3.2 + 0:0 praktisch ausgeschlossen → "Over 0.5 Goals 1st Half" @1.44, bilingual gradebar).

## 23. SYSTEM PICKS AUS + Buttons Admin-only (Owner 2026-08-11, Credit-Notfall)
- ALLE System-Picks abgeschaltet: `snapshot_systems()` → return 0 (keine hq-system-Scheine mehr, spart Settlement-Quote). Bestehende offene hq-system-Scheine gelöscht.
- Buttons "System Picks" und "Codemining" nur noch für Admin sichtbar (Header.jsx + App.js Overlay-Nav via isAdmin = user.role==admin). Verifiziert per Screenshot: für Nicht-Admin beide weg.

## 24. MASTER-TRAINING per Button = fast 0 Credits (Owner-Frage 2026-08-11)
- Owner fragt, ob ein Button zum "Trainieren" des Masters (Ergebnisse zeigen, gewonnene Freunde-Scheine, Kommentare/Analysen) weniger Credits kostet.
- ANTWORT: JA, drastisch. Das SPEICHERN von Ergebnissen/Kommentaren kostet 0 LLM-Credits (nur DB-Text). Die Lernregeln wirken über CODE-Regeln + dieses Brain-File, nicht über teure LLM-Dauerläufe. Ein Trainings-Button (Owner tippt/fotografiert Ergebnisse → landet in master_learnings/DB) ist der günstigste Weg, das Gehirn zu schärfen. Kann als nächstes gebaut werden.

## 25. "TRAIN THE MASTER"-Button gebaut (Owner 2026-08-11)
- Jeder eingeloggte Nutzer kann den Master trainieren: Freitext (JEDE Sprache, JEDE Philosophie) + bis zu 4 Bilder.
- Backend POST /api/master/train (server.py): destilliert die Eingabe EINMAL per LLM (Vision bei Bildern) in eine klare englische LEKTION (behält konkrete Zahlen/Quoten/Teams/Ergebnisse exakt), speichert in db.master_brain {text, images, lesson, topic, language, status}. Storing = ~0 Credits, 1 günstiger Distill-Call pro Teach.
- Admin-Review: GET /api/admin/master-brain (neueste zuerst). Starke Lektionen werden vom Agenten in Code-Regeln/dieses Brain-File übernommen (so wirkt Training, ohne teure LLM-Dauerläufe).
- Frontend: rote "Train the Master"-Box im Master-Bereich unter der Sprechblase (RateWall TrainMaster). Getestet: Endpoint destilliert die Quoten-Philosophie des Owner-Freundes korrekt; Box rendert (Screenshot).
- OWNER-FREUND-PHILOSOPHIE (als Beispiel erfasst, NICHT als Automatik gebaut — Owner nannte die Datenprobleme selbst): 1X2-Quoten vergleichen (z.B. 1.60 / 2.90 / 2.60) und aus der Vergangenheit ein IDENTISCHES 1X2-Set von flashscore.com finden → gleiches Ergebnis erwarten (Porto 1.60/2.90/2.60 → 3:1 → also Bodø gleiche Quoten → 3:1, außer es "bricht" zu 2:2). BLOCKER laut Owner: (1) TipJar-KI übernimmt oft unrealistische Quoten, (2) Quoten ändern sich in der letzten Stunde stark (Freund schaut nur letzte Stunde), (3) Freund nutzt flashscore.com-Quoten. → Quoten-Matching-Engine erst bauen, wenn eine verlässliche Last-Hour-Odds-Quelle (z.B. flashscore) angebunden ist.

## 26. Ein-Klick Bein-Korrektur statt teurer KI-Checks (Owner 2026-08-12)
- Problem: Master postete ein bereits BEENDETES Spiel (Bolívar 1:1 São Paulo) in einem Schein. KI-Dauerprüfung wäre teuer.
- Lösung (credit-sparend): Zwei Ein-Klick-Buttons pro Master/AI-Parlay-Bein (nur bei pending):
  • "Spiel vorbei" (reason=finished) • "Kein Spiel" (reason=nonexistent).
- Backend POST /api/master/correct-leg: (1) blacklistet das Fixture (order-independent _match_key) in db.match_blacklist + in-memory _MATCH_BL_KEYS, time-boxed 7 Tage; (2) _pred_whitelisted() schließt es aus → KEIN Builder postet es neu; (3) entfernt das Bein, rechnet Quote + market neu; (4) fällt der Schein unter 2 Beine → Schein wird GELÖSCHT (der tägliche Builder baut an seiner Stelle einen neuen, jetzt ohne das korrigierte Spiel); (5) Korrektur landet als Lektion in db.master_brain.
- Jeder eingeloggte Nutzer darf korrigieren (Community-Korrektur). Getestet: 3→2 Beine (Quote 8.00→4.00, market neu, blacklist aktiv), 2→1 Bein → gelöscht.

# ===== betting_strategy_notes.md =====

# TipJar — Owner's Betting Strategy Notes (INTERNAL ONLY — never show on website/UI)

These are the app owner's personal betting philosophy notes. Use them to tune the
auto-tip engines (ratings, source trust, markets). DO NOT display any of this text
publicly. Language: owner speaks German + Greek + Spanish.

## Star-rating discipline (MOST IMPORTANT)
- Be VERY careful with 9★ and 10★. A 9-10★ pick must almost never lose. Losing a
  9-10★ destroys trust. When in doubt, rate lower.
- Automated ceiling: do NOT auto-assign 10★. Keep auto-tips at 9.0★ max, and only
  the very safest markets (1+ goal in a high-scoring expected game) reach 9.0.

## Source trust
- DO NOT trust Predictz at all on its own. Its predicted scores are unreliable
  (e.g. it says 4-1 and the game ends 0-2).
- Predictz is only acceptable when it AGREES with Forebet on the same match
  (same over/goals signal or same favourite). Otherwise ignore Predictz.
- Forebet is the primary/more reliable engine.

## Theories to explore / encode over time
1. "Identical 1X2 odds type → similar results": matches that share the same 1X2
   odds shape/category tend to produce similar outcomes (cluster by odds profile).
2. "All results must make a circle / cycle": outcomes rotate over time; patterns
   repeat in cycles — don't assume the recent trend continues forever.
3. "Traditions are made to be broken" (Οι παραδόσεις είναι για να σπάνε):
   Historical head-to-head dominance is NOT reliable. Example: Lens–Arsenal was
   Lens's first-ever European home game and they had never beaten Arsenal, yet it
   looked like a both-teams-score first-half game. Owner tipped HT 1-1 and FT 2-1
   (odds ~40). So: do not over-weight historical H2H; read the current match shape.
4. "Good teams must score roughly every ~70 minutes": if a strong/attacking team
   has gone a whole match without scoring, treat 'they WILL score (next match /
   remaining time)' as a ~10★ conviction. i.e. regression-to-mean on goal drought
   for quality attacking sides → strong 'to score' / Over 0.5 team-goals angle.

## Practical mapping (current)
- Favor GOALS markets (Over 0.5 / Over 1.5 / BTTS / team-to-score) over match-result
  bets. Result bets (favorite to win) fail on upsets (see Olympiacos draws Sundays).
- Über 0.5 Tore (1+ goal in match) = the true banker (loses only on 0-0).
- Real bookmaker odds now come from API-Football /odds (per match), so 'not every
  1.70 is equal' is respected — odds are real where the fixture is priced.

_Last updated: 2026-07-07 by main agent, per owner voice notes._

## Winning example the owner shared — "Banker-Kombi" (favorites accumulator)
A 6-fold ACCUMULATOR of heavy favorites on the MATCH RESULT (1X2) market, each at
very short odds, multiplied together:
- Argentina 1.41 (3-2 vs Egypt), FC Sabah 1.22 (2-0), Una Strassen 1.29 (1-0),
  Hannover 96 1.14 (3-1), Spain (W) U19 1.15 (3-0), FC Lugano 1.14 (0-4).
- Total odds ~3.32, stake 250€ → 829,12€ won. All 6 legs won.
Insight: combining MANY very strong favorites (odds ~1.10–1.45) into one parlay is a
winning pattern — individual upset risk is small, the multiplier makes it pay. This
is DIFFERENT from betting a single favorite to win (which the owner distrusts). The
key is short-priced, high-confidence favorites across leagues, bundled.
→ TODO idea: add a "Banker-Kombi" system = 5–6 strongest Match-Winner favorites
  (real odds ~1.10–1.45, highest win% from Forebet probs) combined into one parlay.

## Over-market timing insight (owner voice note, 2026-07-08)
- Even the "banker" Über 0.5 can wobble until the 90th minute (real case: Víkingur
  0-0 bis zur letzten Minute, dann 1-0). So Über 0.5 is NEVER a true 10★ — keep the
  auto ceiling at 9.0.
- Prefer matches that score EARLY and score ENOUGH, so the bet turns green quickly
  and comfortably (3 goals by the 20th minute = Über 2.5 already won). We can't get
  goal minutes from Forebet, so use goal EXPECTANCY as the proxy: high Ø goals/game +
  high predicted total = attacking, early-scoring game.
- Engine mapping: goals-picks are now ranked by rating AND predicted Ø goals, so the
  most torreiche games surface first. Ambitious over-markets (Über 2.5, Über 2.5+BTTS)
  are only offered with a clear cushion (predicted total ≥ 4 AND Ø ≥ 3.2).
- Rule: ONE selection per match only — the "smartest" (best rating × odds). No more
  overlapping Über 0.5 + Über 2.5+BTTS on the same game.

## Underdog-scores-early rule (owner voice note, 2026-07-08) — HIGHEST PRIORITY
- In a game with a CLEAR favourite (e.g. Real – Atlético), prioritise the UNDERDOG /
  weaker side "<Team> Über 0.5 Tore" (team-to-score). The weaker team usually finds
  the net and often scores EARLY, so the bet turns green fast and wins even when they
  lose the match. This beats a plain match Über 0.5.
- Engine: when Forebet predicts pred=1/2 (clear favourite) AND the underdog's predicted
  score ≥ 1, we post "<Underdog> Über 0.5 Tore" with priority — it is chosen over all
  other markets for that match.

## LIVE tips theory (owner voice note, 2026-07-08) — for the empty "Live Picks" channel
Real cases that shape the live logic:
- Víkingur: 0-0 the whole game, scored in the LAST minute → a live "match still to see
  a goal" can land very late; strong attacking pressure = keep faith in Über 0.5 live.
- Argentina: was 1-2 and turned it in the last ~10 minutes → late comebacks/goals are
  a real live edge when a quality side trails.
- Schweiz–Kolumbien: 0-0, NEVER a goal → warning: not every game gets a goal, so live
  "goal will come" is NOT automatic. Read the actual match, don't force it.
Owner's live angles to auto-generate (in-play, from API-Football live fixtures + stats):
1. First-goal timing: many games score in the first ~3 minutes, then stay flat. If a
   game is still 0-0 with heavy pressure (shots/corners), consider live Über 0.5 /
   next-goal; if it's flat and low-quality, DON'T.
2. Corners edge: if a team is TRAILING and winning lots of corners (piling pressure)
   but you feel they can't finish, give a live tip on THAT team to win MORE corners
   (team corners over X) instead of a goal.
3. Half-based goal markets: "Tor in der 1. Halbzeit", "Tor in der 2. Halbzeit",
   "Tor gegen Ende" — good live markets when the shape supports it.
Practical signals from live stats: shots on target, total shots, corners, ball
possession, dangerous attacks, current minute + score. Use these to pick ONE smart
live market per match, same one-pick-per-match discipline as the pre-match engine.

## LIVE "nachreichen" rule (owner voice note, 2026-07-08) — CORE of the live engine
- We already post ~37 pre-match AI picks at 8–9★ (Über 0.5 / BTTS / Über 2.5 etc.).
- When one of those matches is LIVE and the bet has NOT yet landed (e.g. an Über 0.5
  pick still 0-0), RE-OFFER it live at the (now higher) live odds. Second chance,
  better value.
- BUT be careful: only re-offer if there is still realistic pressure (shots on goal /
  corners). Do NOT re-offer a dead, flat game (à la Schweiz–Kolumbien 0-0 with no
  chances), especially late.
- Live tips auto-settle (won/lost) from the final score once the match ends.

## VALUE-ONLY rule (owner voice note, 2026-07-08) — OVERRIDES everything above
- STOP giving 50/50 (coin-flip) bets. Only give bets we win ~80% of the time (80/20),
  AND the odds must be > 1.60. I.e. give ~80% win chance at odd ≥ 1.60 = genuine value
  (bookmaker mispricing). If a market can't meet BOTH, don't post it.
- If a market family loses too often over time, STOP giving that family (self-learning).
- Engine mapping (Forebet + Predictz, source hq-auto): each candidate carries an
  estimated winprob; we apply the REAL bookmaker odd (API-Football) and keep only
  winprob ≥ 0.78 AND odd ≥ 1.60. `_banned_market_families()` disables any family whose
  settled win-rate < 0.55 over ≥ 8 samples. Coin-flip families (BTTS, Über 2.5,
  Über 2.5+BTTS, correct-score) are never posted; plain Über 0.5 (odds ~1.08) is filtered
  out by the 1.60 rule. Result: far FEWER but higher-quality picks. The prime value market
  is "Über 1.5 Tore" in clearly high-scoring games and DC/DNB on solid favourites when the
  book prices them ≥ 1.60.
- Trade-off the owner accepted: volume drops sharply (e.g. 1 pick out of 42 scanned).
  Threshold WIN_PROB_MIN can be relaxed toward 0.72 if more volume is wanted.


## Slip image + markets update (owner voice note, 2026-06)
- Generated "Fantasy Slip" (Pillow, `_render_slip_image`) now shows: TipJar title top-left
  + tagline, and per match a grey subline "Liga · Datum · Uhrzeit". These are read from
  the uploaded slip via Gemini Vision (`extract_win_slip` now returns league/date/time per
  leg). If any of the three is unreadable, that part is simply omitted. Word "Über"/"Unter"
  always spelled out; team-specific markets keep the team name.
- AI picks: added "Doppelte Chance 12" (home OR away, no draw) — offered when draw is
  unlikely; real dc_12 bookmaker odd from API-Football decides the value gate. Unter 2.5 /
  Unter 3.5 Tore now use REAL bookmaker odds too (under25/under35 parsed from /odds).

## Handicaps + Blacklist + Dedup (owner voice notes, 2026-07-08)
- HANDICAP theory (owner): Außenseiter-Handicap +3.5 ist SICHERER als "Unter 3.5 Tore".
  Beispiel Kairat–Sutjeska: Sutjeska +3.5 verliert NUR bei 4+ Toren Unterschied (0:4 verloren,
  1:4 GEWONNEN), während "Unter 3.5" bei 1:4 (5 Tore) verliert. → Handicap überlebt torreiche Spiele.
- Engine: bei jedem Favoriten (pred 1/2) werden jetzt Underdog-Handicaps angeboten:
  +3.5 (wp 0.92, Banker), +2.5 (0.87, Banker), +1.5 (0.73, Value wenn Quote≥1.60).
  Favorit -1.5 (wp 0.72) nur wenn erwartete Tordifferenz ≥2. Handicap schlägt "Unter X.5" im
  Banker-Tie-Break (0.92 > 0.90). Echte Asian-Handicap-Quoten noch nicht gemappt → Schätzquote.
- Korrekte Schreibweise beim Auslesen: "Sutjeska 3.5" → "Sutjeska Handicap +3.5" (Vision-Prompt).
- Doppelte Chance 12 + Unter 2.5/3.5 mit echten Quoten (früher ergänzt).
- BLACKLIST (Teams/Ligen, Keyword-Match auf home/away/league): "golden", "mogadishu", "kahibah".
  In forebet + predictz Autopostern und in _slip_eligible (Systeme) durchgesetzt. Erweiterbar in
  TEAM_LEAGUE_BLACKLIST.
- DEDUP: _dedupe_hq_tips() erzwingt EIN Pick pro Spiel über alle pending hq-auto (forebet+predictz).
  Bei Duplikaten (z.B. Über 0.5 + Über 1.5) bleibt der wertvollste (value>banker, dann höchste Quote),
  die risikoärmsten Duplikate werden gelöscht. Läuft am Ende beider Autoposter.

# ===== betting_notes.md =====

# TipJar — Owner Betting Notes (Private)

Persönliche Wett-Lernnotizen des Owners ("TipjarLogic"). Diese Regeln spiegeln die reale
Erfahrung des Owners wider und sollen die KI-Tippgenerierung steuern. IMMER hier nachschlagen,
bevor Tippgenerierungslogik geändert wird. Owner-Sprache: DEUTSCH.

## Harte Regeln (in Code umgesetzt)
1. **Verlängerung zählt NICHT.** Alle Tor-Märkte (Über/Unter) und Spieler-Props
   (z.B. "Messi Über 0,5 Torschüsse", "Über 1,5 Tore") gelten NUR für die reguläre
   Spielzeit (90 Min). → Helper `_reg_goals()` nutzt `score.fulltime` statt `goals`
   (API-Football zählt bei AET/PEN die Verlängerung mit). Angewandt in
   `find_finished_fixture`, `_datescan_fixture`, `_align_goals`. (2026-07-20)
   HINWEIS: Spieler-Schuss-Statistiken (/fixtures/players) trennen ET nicht separat —
   dort bleibt eine kleine Datenlücke bei K.-o.-Spielen mit Verlängerung.
2. **Keine Doppelte Chance (1X/X2) als Banker in Skandinavien/Nordics.** Diese Ligen
   (Allsvenskan, Superettan, Veikkausliiga, Eliteserien, Superligaen, Úrvalsdeild, …) sind
   zu unberechenbar. Beispiel-Verlust: "Ilves gewinnt nicht" → Ilves gewann 3:1.
   → `_is_scandinavian()` in `_forebet_candidates`: DC-Option wird dort übersprungen. (2026-07-20)
2. **Keine wertlosen Handicaps.** +2,5 / +3,5 Handicap = reale Quoten ~1,005–1,05 → null Value.
   NUR +1,5 anbieten (reale Quote ~1,55). +2,5/+3,5 entfernt. (2026-07-20)
3. **Keine eigenständige "Über 0,5 Tore"-Wette** (nur als Zweit-Leg im Builder). (2026-07-18)
4. **Kein Lotto-1X / kein "beide treffen" als Zufalls-Lotto.**
   - Bsp: Spanien–Argentinien → KI gab "beide treffen" (Lotto). Besser wäre: **Unter 2,5 Tore + 1X**.
5. **Brasilien NICHT löschen, aber NIE als Pfeffer/Über-Tipp!** Brasilianische Top-Ligen
   (Série A/B) bleiben bettbar; obskure Staatsmeisterschaften (paulista, carioca, …) geblockt.
   ABER: Brasilien NIE für Über-Tore/Pfeffer verwenden (Owner 2026-07-21: "Ich hasse es,
   Brasilien als Pfeffer zu benutzen"). Prognosen dort überschätzen Tore massiv:
   Atletico Mineiro (pred total 5 → real 1:1), Gremio Novorizontino (pred 4 → real 0:1).
   → Helper `_bad_for_overs()` schließt Brasilien aus Pfeffer- & TipJarLogic-Über-Kombis aus.
6. **Exakt-2-Tore-Falle (Asian Handicap):** Bei Über 2.0 mit genau 2 Toren = Push (Einsatz
   zurück, kein Gewinn). Bei Über 2.25 mit 2 Toren = halber Verlust. → Über 2.5 nur bei
   echten Torfesten (torreiche Ligen), niemals in torarmen Ligen wo 1:1/2:x typisch ist.

## Muster-Wissen (für zukünftige Features / KI-Prompts)
- **Markt-Mechanik DC + Über (Owner 2026-07-22, wichtig!):**
  - „{Fav} Doppelte Chance + Über 1.5 (SPIEL)" → ein **1:1 reicht** (Favorit verliert nicht + 2 Tore im Spiel). SICHER. ← Pfeffer-Banker nutzen genau das.
  - „{Fav} Sieg + Über 1.5" oder team-spezifisch „{Fav} Über 1.5" → Favorit braucht **2+ eigene Tore** (1:0-Sieg verliert). RISKANTER (Fenerbahce 1:0 hat so einen Schein gekillt).
- **GEWINNER-MUSTER (2026-07-22, vom Owner beobachtet):** Ein cleverer Tipper spielte dominante
  Favoriten, die 4:0 gewinnen: Sturm (1X + Über 0.5), Crvena Zvezda (Sieg + Über 1.5), Lech
  (Gegner +2.5 + Über 1.5) — alle trafen 4 Tore. Verlor nur wegen Fenerbahce (Über 1.5, aber nur 1:0).
  → LEHRE: Auf den STARKEN FAVORITEN setzen, der SELBST 2+ trifft: „{Favorit} Doppelte Chance +
  {Favorit} Über 1.5 Tore". Der Favorit trägt den Schein — nie vom schwachen Team abhängen.
  → Pfeffer-Banker sind jetzt genau so gebaut. VORSICHT: auch Top-Teams gewinnen mal 1:0
  (Fenerbahce) → nur Favoriten mit vorhergesagten 2+ Toren nehmen (fav_goals≥2).
- **Nie von schwachen Teams abhängen (2026-07-21):** Radar sagte „Lincoln trifft" → Mjällby 3:0 Lincoln (Lincoln traf NICHT). Larne 0:4 Crvena zvezda, AGF 1:4 Lech. Lehre: NICHT auf das schwache Team setzen (BTTS/each-half, das das schwache Team braucht). Stattdessen den STARKEN FAVORITEN spielen (Favorit verliert nicht + Über-Linie, die der Favorit selbst liefert).
  → Pfeffer ist jetzt favoriten-verankert (`_pepper_qualifies`: nur Spiele mit starkem Favoriten, der 2+ Tore erwartet, ODER echtem Torfest total≥4 & btts). Banker = „{Favorit} Doppelte Chance + Über-Linie" oder Über/Unter-Range.
- **Zwei Pfeffer-Fenster (2026-07-21):** Di→Fr 12:00 (`pepper`) und Fr→Di 12:00 (`pepperwk`). Beide oben in den System-Picks.
- **Favoriten-Tracker (`db.favourite_teams`):** sammelt automatisch starke Favoriten (fav_prob≥60) → wächst zur ~50-Team-Liste. TODO: aus Ergebnissen lernen (Trefferquote je Team, chronische Versager wie Lincoln soft-blocken).
- **0:0 in Skandinavien real (2026-07-20 bestätigt):** Örgryte–Djurgården endete 0:0,
  Hafnarfjörður–Breidablik endete 0:0. Beweis, dass 0:0 dort möglich ist → bei Über-Wetten
  in nordischen Ligen vorsichtig, torlose Spiele ehrlich als solche kennzeichnen.
  → Tor-Prognose-Tabelle zeigt 0:0-erwartete Spiele als "kein Tor erwartet".
- **Tor-Prognose-Tabelle (umgesetzt 2026-07-20):** `/api/goals-forecast` zeigt pro Spiel,
  wie viele Tore jedes Team laut Vorhersagescore (ph/pa) schießt (⚽ = 1 Tor). WICHTIG:
  Bälle kommen aus der PROGNOSE, nicht aus der Quote — kein Ball nur weil ein Favorit @1.20
  steht. Ein Team mit 0 vorhergesagten Toren bekommt 0 Bälle.
- **"Hungrige" Torteams jagen:** Wenn ein Team wie **Göteborg** in einem Spiel gar nicht trifft,
  trifft es sehr wahrscheinlich im nächsten. Solche Teams gezielt auf "Team trifft" backen.
- **0:0-Historie:**
  - Team mit LANGER Historie OHNE 0:0 → ein 0:0 ist bald fällig (Vorsicht bei Overs, evtl. Under/0:0).
  - Team mit FRISCHER 0:0-Historie → wird bald wieder Tore schießen (Overs / Team trifft backen).
- **Sichere Live-Kombi (Owner-Style, umgesetzt):** 2–4 bereits erfüllte Über-Legs (Spiel hat schon
  Tore → "Über 0,5/1,5" ist gesperrt) aus verschiedenen laufenden Spielen → Gesamtquote ~1,5.
- **Banger (umgesetzt):** Goal-Fest-Momentum — wenn schon ≥3 Tore + offen/schnell → höhere Über-Linie.
  Offenes 0/1-Tor-Spiel mit Druck → "Asian Über 2.0" (Push bei genau 2).
- **Smart-KI (umgesetzt):** gibt IMMER einen konkreten, coolen Tipp; nie leere Fehlermeldung.

## Offene Owner-Wünsche (Backlog)
- **"Wer trifft heute?"-Radar:** Über viele Spiele hinweg einfach sagen, WELCHE Teams heute treffen
  werden (Bsp genannt: **Malmö, Breidablik, Göteborg**). Fokus auf verlässliche Torteams +
  "hungrige" Teams (siehe Muster oben). → eigenes Feature, noch zu bauen.

## Referenz-Quoten (User-Vorgabe 2026-07-23, Wettz-Screenshots)
Für Ligen OHNE echte Buchmacher-Quoten (Armenien, Baltikum, Kirgistan, Kosovo, MLS Next Pro II etc.) muss die Fallback-Heuristik (base_odd) ungefähr so aussehen:
- Team "Über 0.5 Tore" (Team trifft): ~1.10 (sehr niedrig, war 1.22)
- Match "Über 1.5 Tore": ~1.35-1.44 → base_odd 1.38 (war 1.28/1.30)
- Match "Über 2.5 Tore": ~1.65-1.70 → base_odd 1.70 (war 1.85)
- "Beide Teams treffen (Ja)": ~1.60-1.65 → base_odd 1.65 (war 1.80)
- "Über 8.5 Ecken": ~1.55 (ok)
- HT "Über 1.5 Tore": ~2.4-2.6 (ok)
- Match "Unter 3.5": ~1.40 | "Unter 3": ~1.36
Beispiel-Referenz-Combos: CFR Cluj Team Ü0.5 + Ü1.5 = 1.58 | Herediano Ü0.5+Ü1.5 = 1.37 | NE Rev II Ü2.5+BTTS = 1.81 | Liepaja Ü2.5+HT Ü1.5+BTTS = 3.80.

## Neue Muster vom Owner (2026-07-23) — "lern von mir, sei offener, mehr Ideen"
Der Owner will MEHR Vielfalt, nicht immer dieselben 3 Bausteine. Zwei konkrete neue Muster:

1) SAFE-FAVOURITE "Braga"-Dreiereck (10★, sehr sicher): ein starker Favorit, der knapp & tor-arm gewinnt.
   - Doppelte Chance 1X/X2  +  {Fav} Über 0,5 Tore  +  {Fav} Unter 3,5 Tore
   - Logik: Favorit verliert nicht UND trifft 1–3 Tore. Ein 1:0/2:1 reicht; ein Kantersieg schadet nicht (unter 3,5 pro Team).
   - Umgesetzt als opt "-favsafe" (rating 8.5). Neuer Grader-Kind team_u35 (team-spezifisches Unter).

2) VALUE-BANKER "Austria-Wien": frühes Tor in offenen Spielen.
   - Über 0,5 Tore 1. Halbzeit (asiatisches HT-Tor)  +  {Fav} Über 0,5 Tore
   - Als "Value-Banker" gedacht (hohe Trefferquote, faire Quote). Umgesetzt als opt "-htvalue" (rating 8.0).

GENERELLE ANWEISUNG: Bei der Tipp-Generierung offener/kreativer sein — verschiedene Markt-Kombis je nach Spielcharakter (tor-arm vs. offen), nicht stur dieselben Templates. Favoriten-Tipps immer absichern (DC statt reiner Sieg), Kantersieg-Risiko mit "Unter X,5 (Team)" abfedern.

## Asiatisch Über 1.0 HZ (Asian Over 1.0 First Half) — Grading-Regel (2026-07-23)
- 0 Tore in HZ1 → VERLOREN
- genau 1 Tor in HZ1 → PUSH/VOID (Einsatz zurück) — GRADE_VOID Sentinel in _grade_goal_leg (kind: ht_asian_o1)
- 2+ Tore in HZ1 → GEWONNEN
- Im Parlay: void-Leg zählt als Quote 1.0 (Rest zählt normal); wenn ALLE Legs void → ganzer Schein void. Payout wird neu berechnet (Gesamtquote / Produkt der void-Quoten).

## Value-Banker (Owner-Wunsch) — Generator (2026-07-23)
- Muster: "Tor in jeder Halbzeit + {Favorit} Über 0.5 Tore (Value-Banker)" → kinds goal_each_half + team_o05. Nur offene torreiche Spiele (total>=3, xg>=2.8, Favorit trifft). Rating 8.0.
- Asian-Variante: "{Favorit} Über 0.5 Tore + Über 1.0 Tore 1. Halbzeit (Asiatisch)" → team_o05 + ht_asian_o1 (HZ-Leg ist versichert: 1 Tor = Push statt Verlust). total>=3, xg>=3.0. Rating 7.5.

## 2026-07-24 — Owner rules: combo redundancy, handicaps, no correct-score
CRITICAL logic the AI + combo/system builder MUST follow:

1. NO REDUNDANT LEGS in a slip. Never include a selection that is logically ENTAILED
   by the combination of the other legs (adds no odds/value). Compute the minimal
   implied scoreline/total from the existing legs and drop any leg whose condition is
   already guaranteed.
   - Worked example (Red Star vs Vojvodina): legs {Home -1.5, BTTS}.
     * Home -1.5 => home wins by >=2 goals.
     * BTTS => away >=1, home >=1.
     * Minimal satisfying scoreline = 3-1 => total >=4.
     * => Over 3.5 (>=4) is REDUNDANT. Home team Over 2.5 (>=3) is REDUNDANT.
     * Goal-in-each-half is NOT implied (timing) => genuine added value, keep.
     * Only Over 4.5 (>=5) meaningfully raises risk/odds above the implied floor.

2. LEARN HANDICAPS properly:
   - Team -1.5 => that team must win by >=2 (2-0, 3-1, 3-0, ...).
   - Team -2.5 => win by >=3. Team +1.5 => lose by <=1 or better (i.e. not lose by 2+).
   - Draw No Bet => favourite win OR stake back on draw.
   - When combining a handicap with BTTS/over lines, derive the implied minimum
     total/scoreline and use it to detect redundancy (rule 1).

3. NEVER give an exact/correct score as a pick. Express the intended scoreline via a
   COMBINATION of markets (handicap + BTTS + over/under + halves) that together imply
   the desired scenario, choosing only legs that each add real value/odds.

Apply in: build_systems / combo candidate generation / _finalize_system, and in the
match-analysis prose (explain WHY, EMP-Tips style, with implied-goal reasoning).

### IMPLEMENTED 2026-07-24
- New module `betting_logic.py`: market_constraint() (parses handicaps/totals/BTTS/1X2/DC over a
  scoreline grid), dedupe_implied_legs() (fixpoint: removes the weakest logically-entailed leg),
  scoreline_to_combo() (predicted score → non-redundant market combination, never a correct score).
- server.py `_dedupe_builder_legs()` applied in mental_autopost + favourite_smart_autopost.
- JACKPOT system: correct-score ("Genaues Ergebnis X:Y") REPLACED by scoreline_to_combo combinations.
- Prompts: _ANALYST_SYSTEM upgraded to sharp EMP-tipster style (NO fabricated stats — only given
  data; no exact score; explains handicaps). AI_SYSTEM (slip reader) now flags redundant selections.
- VERIFIED live: mental "FK Crvena Zvezda v Vojvodina" dropped redundant "Crvena Zvezda Über 2.5",
  kept {Über 4.5, BTTS, Tor je HZ, -1.5}. /api/systems JACKPOT has NO correct-score.
- PENDING: real historical hit-rates ("BTTS 6/7") need a stats feed (API-Football, quota-limited).
  @EmpTips X monitoring needs X API credentials (route via integration_expert).

### IMPLEMENTED 2026-07-24 (part 2) — real stats + EMP ingestion
- `match_stats.py`: team_form()/h2h_stats() from API-Football last-N (cached 12h in db.stats_cache,
  quota-safe short-circuit, NEVER fabricates). compute_form/compute_h2h are pure + unit-tested.
- server `_pick_stats_line(p)` resolves team ids + builds real hit-rate line
  ("Form WWDWW · BTTS 6/8 · Über 2.5 7/8 · H2H BTTS 4/5"). Appended (📊) to mental & favourite
  auto-picks + stored as tip.stats_line; passed into llm_pick_analysis(context, stats_line).
- EMP Tips ingestion: POST /api/admin/emptips/ingest (image(s)+/or text) → analyze_tip vision →
  posts public pick source="emptips", username "EMP Tips", category "expert", enriched with stats_line.
  VERIFIED: AI flagged redundant "Over 3.5" (−1.5+BTTS ⇒ 3-1 ⇒ 4+ goals) automatically.
- Free auto X-polling of @EmpTips is NOT reliably possible (syndication 429 / token-gated, nitter dead).
  Owner won't pay for X API → use the ingestion endpoint (forward/paste the slip). Needs a small admin
  UI button (backend ready). If X API key is ever provided, add a poller on top of the same ingestion.

### IMPLEMENTED 2026-07-25 — EMP Tips AUTOMATIC monitoring (free, no X API)
- X free access (Nitter mirrors) is unreliable (403/challenge). SOLUTION: read EMP's PUBLIC
  Telegram channel via free t.me/s/ web preview — reliable, no keys.
- `emptips_watch.py`: fetch_telegram(channel) parses messages (text, betslip image URLs telesco.pe,
  ids) newest-last; fetch_timeline(handle) = X/Nitter fallback; fetch_image().
- server `emptips_autopost()`: Telegram-first (EMPTIPS_TG_CHANNEL) then X fallback. FIRST run =
  BASELINE (mark backlog seen, post nothing). Then each NEW post: download betslip → analyze_tip
  vision-AI → _ingest_emptips → public 'EMP Tips' pick (+ real stats). skip_if_empty drops
  promo/results posts; _EMP_RESULT_KW filters "BOOOM/winner". MAX_PER_RUN=4 (vision is slow),
  dedup via db.emptips_seen. `emptips_loop()` every 20min (leader-gated); startup task added.
- Admin: POST /api/admin/emptips/ingest (manual image/text), POST /api/admin/emptips/run
  (fires autopost in BACKGROUND — vision calls exceed the 100s gateway limit, so never block).
- .env: EMPTIPS_HANDLE="EmpTips", EMPTIPS_TG_CHANNEL="EMPTipsTele".
- VERIFIED: baseline marked 18 posts, 0 dumped; simulated 3 new → auto-posted 2 real accas
  (5-leg @10.00, 2-leg @2.10) with legs parsed from betslip screenshots via vision-AI.
- NOTE: vision-AI ingestion uses Emergent LLM credits (~1 call per new EMP betslip).

### UPDATED 2026-07-25 — Anonymous expert bot "Orion" + multi-channel
- Monitored tipster slips are now re-posted ANONYMOUSLY under an in-house expert bot "Orion"
  (user orion@tipjar.com, role="expert" → auto orange card + EXPERTE badge in Community feed).
- source="orion", category="value", user_id=bot, username="Orion", is_expert=True. Lands in the
  members/community bucket. No frontend change needed (is_expert already styles orange).
- Source anonymity: _scrub_source() strips URLs / t.me links / @handles / "EMP Tips" from
  raw_text + analysis. Tip id prefix orion-. Analysis prefixed "🔮 Orion:".
- MULTI-CHANNEL: env WATCH_TG_CHANNELS = comma-separated Telegram channels (fallback to
  EMPTIPS_TG_CHANNEL, then X handle). emptips_autopost() iterates all channels; Telegram msg ids
  now "tg-<channel>-<id>" to avoid cross-channel collisions.
- VERIFIED: Community feed shows 2 orange "by Orion" EXPERTE parlays parsed from betslips.
- To add channels: append to WATCH_TG_CHANNELS in backend/.env (comma) + restart backend.

# ===== smart_picks_principle.md =====

# Smart Picks — Owner-Prinzip (2026-08-03)

**Smart Picks sind KEIN Lotto.** Owner-Regel, verbindlich für alle Generatoren und alle künftigen Agents.

## Was ein Smart Pick IST
- Sicher & logisch, gut begründbar aus echten Daten/Form.
- Einzelne, ruhige Value-Singles (~1.3–1.6) sind ideal.
- Beispiel (Owner-Referenz, 03.08.2026): **„Anytime Goalscorer o. Ersatzspieler — Robbie Ure" @ 1.41**
  (Halmstad vs. Sirius). Die Absicherung „oder sein Ersatzspieler trifft" macht den Pick ruhig —
  ein einzelnes Tor aus der Position reicht.

## Was ein Smart Pick NIE ist (= Lotto, verboten)
- „Zyklus"-Logik: „Team hat lange nicht getroffen/gewonnen → jetzt fällig". → DEAKTIVIERT
  (`smart_h2h_autopost` gibt sofort `return` zurück, Code erhalten aber unerreichbar).
- „Team, das nie 3 Tore macht, macht plötzlich 3 Tore" / Torfestival-Wetten auf schwache Angriffe.
- Alles, was auf „Trendumkehr/fällig" statt auf echter Stärke basiert.

## Enforcement
- `smart_h2h_autopost` bleibt deaktiviert + self-heal (löscht offene Zyklus-Picks bei jedem Lauf).
- Neue Smart-Generatoren nur mit sicheren, logischen Linien. Keine „due/fällig"-Heuristik.

# ===== bugs.md =====

# TipJar — Bug-Liste (verifiziert gegen echten Code)

Protokoll (Owner 2026-08-13): Bugs werden IMMER hier notiert. Beim Stichwort **"Valhalla"** liefert der Agent
je Bug einen credit-minimalen Prompt + fertigen Code-Block (zum Selbsteinsetzen in der Produktion),
damit der Owner möglichst wenig Credits verbraucht.

Status-Legende: 🔴 offen · 🟡 teilweise/needs-verify · 🟢 gefixt · 🟣 Valhalla-Code geliefert (2026-08-13), noch nicht deployed

VALHALLA 2026-08-13: Root-Causes final verifiziert. BUG-001+002 = Multi-Match-Routing + eingefrorener leg.live_score.
Fix-Blöcke geliefert für settlement.py (settle_hq_combos + settle_multimatch_parlays), betting_logic.py (precise_label), RateWall.jsx (leg-score-Anzeige).

---

## BUG-001 🟡 — Master-Scheine landen nicht (immer) im Settled / gewonnener Schein „verschwindet"
**Owner-Wunsch:** ALLE Master-Scheine müssen runter ins Settled — entweder „Lost" oder „Best-Of/Won".
**Verifiziert im Code:**
- `settle_pending_tips` (settlement.py:782) schließt Parlays aus (`is_parlay: {$ne: True}`) → nur Singles. KORREKT so.
- `settle_hq_combos` (settlement.py:931-934) fordert `status:"pending"` UND `combo_legs:{$exists:True}` und löst
  EIN Fixture (home/away des Tipps) für ALLE Beine → nur für SAME-MATCH-Builder gedacht. Ein Master-Parlay
  über MEHRERE Spiele, das fälschlich `combo_legs` trägt, würde hier alle Beine gegen EIN Spiel bewerten (falsch).
  Und sobald ein Bein „live" ist, fällt der Schein aus `status:"pending"` → wird hier nie erfasst.
- ABER `settle_multimatch_parlays` (settlement.py:1119-1130) EXISTIERT und verarbeitet Multi-Match-Parlays
  (`status in [pending,live,cashed_out]`, `is_parlay:True`, `combo_legs:{$exists:False}`, `legs.0 exists`)
  Bein-für-Bein gegen JEWEILS EIGENES Fixture. → Die frühere Analyse „keine Funktion erfasst Multi-Match" ist FALSCH.
**Wahrscheinliche echte Ursache (bei Valhalla final verifizieren):**
- Master-Multi-Match-Builder speichert evtl. `combo_legs` (→ landet in hq_combos → All-gegen-ein-Fixture-Fehlgrading)
  ODER der Schein bleibt „live" und wird nur von hq_combos gesucht (das aber `pending` fordert).
- TODO Valhalla: prüfen, ob Master-Multi-Match-Builds `combo_legs` ODER nur `legs` setzen; hq_combos-Query um
  `status:{$in:[pending,live]}` erweitern und combo_legs-Zwang nur für echte Same-Match-Builder.

## BUG-002 🔴 — Settled zeigt Zwischenstand statt Endergebnis (z.B. „Boca trifft" bei 1:1 gewonnen → final 1:1 statt 3:1)
**Owner:** Scheine, die VOR dem Abpfiff (sobald Bein gewonnen) ins Settled wandern, müssen den Finalstand nachkorrigieren.
**Ursache (Hypothese, bei Valhalla verifizieren):** Der pro Bein/Schein angezeigte Score-Snapshot wird im Moment
der ersten „won"-Erkennung gespeichert und beim echten Full-Time nicht aktualisiert. Fix: beim finalen Settlement
(FT-Fixture) den echten Endstand jedes Beins (gh:ga aus find_finished_fixture) überschreiben, auch wenn das Bein
schon als „won" markiert war.

## BUG-003 🟢-ready — Spieler-Schuss-Bein wird als „Gesamt-Tore Über 0.5" gelabelt
**WICHTIG (Owner 2026-08-13) — zwei UNTERSCHIEDLICHE Märkte, nicht verwechseln:**
- **Schuss / Schüsse** = normaler Schuss (shots, gr. σουτ) → niedrigere Quote, weniger Risiko. (Zafeiris-Fall = DIESER.)
- **Torschuss / Torschüsse** = Schuss AUFS TOR (shot on target / SOT, gr. σουτ στην εστία) → höhere Quote, mehr Risiko.
- Grading/OCR MÜSSEN beide getrennt behandeln (unterschiedliche Fixture-Stats: total shots vs. shots on target).
  Beim Labeln zählen aber BEIDE als Spieler-Prop → beide dürfen NIE zu „Gesamt-Tore" werden.
**Verifiziert:** `precise_label` (betting_logic.py:209). Zeile 225-228 Exklusions-Liste enthält KEIN
„schuss/schüsse/torschuss/torschüsse/shots/sot". Ein Bein „Zafeiris über 0.5 Schüsse" (Spielername, kein Teamname
im String) matcht `über 0.5` (Z.221), fällt durch die Exklusion und endet in Zeile 237 → „Gesamt-Tore Über 0.5".
**Fix (1 Zeile, sicher):** in das Tuple Z.225-228 aufnehmen:
`"schuss", "schüsse", "schusse", "torschuss", "torschüsse", "torschusse", "shots", " sot", "shot on"`
Nur Anzeige (precise_label ist display-only, ändert NICHT den Grading-String) → risikolos.

## BUG-004 🟢 GEFIXT — Bild-Upload crasht mit Cloudflare 520 (Owner 2026-08-14)
Ursache: AI_VISION_MODEL = "gemini-3.1-pro-preview" hing/retried endlos bei JEDEM Bild (LiteLLM-Retries
20:07:11→20:07:58→20:08:18) → >25s → Ingress-Proxy antwortet mit unparsebarem 520. OCR funktionierte nie.
Fix:
1. core.py: AI_VISION_MODEL → "gemini-2.5-flash" (multimodal, ~5s, günstiger). Bild-Upload liest jetzt in 5s.
2. server.py analyze_tip: LLM-Call in asyncio.wait_for(timeout=20) → fällt bei Hänger/Down schnell in den
   bestehenden Fallback (ai_error=True, safe=True) → Tipp ist IMMER postbar, auch ohne LLM.
Getestet: Text-Pfad (Flash) 5.6s ok; Bild-Pfad vorher 25s Timeout→jetzt 5.1s HTTP200 mit echten Teams/Quote.
