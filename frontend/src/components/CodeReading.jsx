import React, { useEffect, useRef, useState } from "react";
import { ScanLine, Ban, Target, Upload, Loader2, Star, Check, X, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api from "../api";
import { useI18n, localizeMarket, localizeProse, formatSelection, toLatin } from "../i18n";
import { useProseTranslations } from "../proseI18n";
import { useAuth } from "../auth";

const L = {
  de: {
    title: "Codemining",
    guide: "Die fertigen Scheine der Wettanbieter (z.B. 'Akku des Tages', Boost-Angebote) sind so gebaut, dass DU verlierst. Wir lesen den Schein und spielen bewusst DAGEGEN — oder machen NO BET. Wichtig: Lade nur Angebote von Anbietern hoch, die den Spieler in die Falle locken wollen — NICHT von Bet365 (deren Quoten sind fair). Die KI liest jedes Spiel und gibt dir unsere Gegen-Lesart.",
    howTitle: "So funktioniert's",
    steps: [
      "Screenshot eines 'fertigen' Buchmacher-Scheins hochladen (Falle-Anbieter, nicht Bet365).",
      "Die KI liest jedes Spiel und dreht die Logik um: Was wollen sie, dass passiert? → Wir spielen dagegen.",
      "Nur das Logische bleibt. Ist nichts Logisches erkennbar → NO BET.",
    ],
    examplesTitle: "Beispiele (mit fiktiven Teams)",
    examples: [
      ["Porto – Benfica: 'X (Unentschieden) in der 30. Minute'", "Sie sagen, bis zur 30. bleibt es Remis → also fällt FRÜH ein Tor → wir spielen Über 0.5 Tore 1. Halbzeit."],
      ["Real – Sevilla: 'Real Gesamt Unter 1.5'", "Sie sagen, Real trifft kaum → dagegen: Real Über 0.5 Tore (Real trifft, vor allem zuhause)."],
      ["Ajax – PSV: 'PSV Gesamt Unter 2.5 – Nein' (also 3+)", "Sie brauchen von PSV 3+ Tore (selten) → wir deckeln: PSV Unter 3.5 Tore."],
      ["Milan – Inter: 'Sieg Inter (1X2)'", "Glatter Sieg → Inter Draw No Bet (DNB): Inter verliert nicht, bei Remis kommt der Einsatz zurück. (Reine Doppelte Chance / '<Team> gewinnt nicht' → NO BET.)"],
      ["Lazio – Roma: 'Roma trifft NICHT (Über 0.5 – Nein)'", "Dagegen: Roma trifft (oder beide treffen). Nicht dass es 0:1 endet."],
      ["Bodø – Molde: 'letztes Tor 55.–90. von Bodø'", "Sie sehen Bodø SPÄT treffen → wir sagen früher: Bodø trifft bis zur 60. Minute."],
      ["Chelsea – Arsenal: 'Über 2.5 Tore'", "Zu unsicher für uns → NO BET."],
      ["Napoli – Juve: 'Handicap -1.5 Napoli'", "Handicap/Sieg → NO BET."],
    ],
    empty: "Noch keine Reads. Lade einen Buchmacher-Screenshot (Akku des Tages / Boost) hoch.",
    nobet: "NO BET", counter: "UNSER GEGEN-PICK", code: "Code sagt",
    upload: "Bilder hochladen (max. 4)", scanning: "Lese Code…",
    adminOnly: "Nur für Admin.", done: "gelesen", none: "Keine Fußball-Legs erkannt.",
    won: "gewonnen", lost: "verloren", score: "Ergebnis",
    learnTitle: "Lern-Statistik", learnSub: "Trefferquote je Muster — aus echten Ergebnissen gelernt",
    sysMaster: "Master", sysHq: "TipJar HQ", sysCode: "Code Reading",
    vVeto: "herabgestuft", vBoost: "bewährt", vOk: "aktiv",
    noLearn: "Noch keine abgerechneten Daten — sobald Spiele fertig sind, lernt das System hier.",
    games: "Spiele",
    tabActive: "Aktiv", tabDone: "Beendet", endResult: "Endergebnis",
  },
  el: {
    title: "Codemining",
    guide: "Τα έτοιμα κουπόνια των πρακτόρων (π.χ. «Παρολί της ημέρας», ενισχυμένες προσφορές) είναι φτιαγμένα για να ΧΑΝΕΙΣ. Εμείς διαβάζουμε το κουπόνι και παίζουμε επίτηδες ΑΝΤΙΘΕΤΑ — ή NO BET. Σημαντικό: ανέβασε μόνο προσφορές από εταιρίες που θέλουν να παγιδέψουν τον παίκτη — ΟΧΙ από Bet365 (οι αποδόσεις τους είναι δίκαιες). Η ΚΙ διαβάζει κάθε αγώνα και σου δίνει την αντίθετη ανάγνωση.",
    howTitle: "Πώς δουλεύει",
    steps: [
      "Ανεβάζεις screenshot ενός «έτοιμου» κουπονιού (εταιρία-παγίδα, όχι Bet365).",
      "Η ΚΙ διαβάζει κάθε αγώνα και αντιστρέφει τη λογική: τι θέλουν να γίνει; → παίζουμε το αντίθετο.",
      "Κρατάμε ΜΟΝΟ αυτό που βγάζει νόημα. Αν δεν φαίνεται κάτι λογικό → NO BET.",
    ],
    examplesTitle: "Παραδείγματα (με υποθετικές ομάδες)",
    examples: [
      ["Porto – Benfica: «Χ (ισοπαλία) στο 30'»", "Λένε ότι στο 30' θα είναι ακόμη ισοπαλία → άρα υπάρχει γκολ νωρίς → παίζουμε Over 0.5 γκολ στο ημίχρονο."],
      ["Real – Sevilla: «Real Σύνολο Under 1.5»", "Λένε ότι η Real δύσκολα σκοράρει → αντίθετα: Real Over 0.5 γκολ (σκοράρει, ειδικά εντός)."],
      ["Ajax – PSV: «PSV Σύνολο Under 2.5 – Όχι» (δηλ. 3+)", "Θέλουν 3+ γκολ από PSV (σπάνιο) → τη «δένουμε»: PSV Under 3.5 γκολ."],
      ["Milan – Inter: «Νίκη Inter (1X2)»", "Καθαρή νίκη → NO BET. Δεν αγοράζουμε ποτέ σκέτο 1/1Χ."],
      ["Lazio – Roma: «Η Roma ΔΕΝ σκοράρει (Over 0.5 – Όχι)»", "Αντίθετα: η Roma σκοράρει (ή σκοράρουν και οι δύο). Να μην τελειώσει 0-1."],
      ["Bodø – Molde: «τελευταίο γκολ 55'–90' από Bodø»", "Τη βλέπουν να σκοράρει ΑΡΓΑ → εμείς λέμε νωρίτερα: Bodø σκοράρει μέχρι το 60'."],
      ["Chelsea – Arsenal: «Over 2.5 γκολ»", "Πολύ αβέβαιο για εμάς → NO BET."],
      ["Napoli – Juve: «Χάντικαπ -1.5 Napoli»", "Χάντικαπ/νίκη → NO BET."],
    ],
    empty: "Καμία ανάγνωση ακόμη. Ανέβασε ένα screenshot «Παρολί της ημέρας» / ενισχυμένης προσφοράς.",
    nobet: "NO BET", counter: "ΤΟ ΑΝΤΙΘΕΤΟ ΜΑΣ", code: "Ο κώδικας λέει",
    upload: "Ανέβασε εικόνες (έως 4)", scanning: "Διαβάζω κώδικα…",
    adminOnly: "Μόνο για διαχειριστή.", done: "διαβάστηκαν", none: "Δεν βρέθηκαν legs.",
    won: "κερδισμένο", lost: "χαμένο", score: "Σκορ",
    learnTitle: "Στατιστικά Μάθησης", learnSub: "Ποσοστό επιτυχίας ανά μοτίβο — από πραγματικά αποτελέσματα",
    sysMaster: "Master", sysHq: "TipJar HQ", sysCode: "Ανάγνωση Κωδικών",
    vVeto: "υποβαθμισμένο", vBoost: "δοκιμασμένο", vOk: "ενεργό",
    noLearn: "Δεν υπάρχουν ακόμη δεδομένα — το σύστημα μαθαίνει μόλις τελειώσουν αγώνες.",
    games: "αγώνες",
    tabActive: "Ενεργά", tabDone: "Τελείωσαν", endResult: "Τελικό σκορ",
  },
  en: {
    title: "Codemining",
    guide: "Bookmakers' ready-made slips (e.g. 'Accumulator of the day', boosted offers) are built to make YOU lose. We read the slip and deliberately play AGAINST it — or NO BET. Important: only upload offers from bookies that want to trap the player — NOT from Bet365 (their odds are fair). The AI reads every game and gives you our counter-read.",
    howTitle: "How it works",
    steps: [
      "Upload a screenshot of a 'ready-made' bookie slip (trap bookie, not Bet365).",
      "The AI reads each game and flips the logic: what do they want to happen? → we play the opposite.",
      "Only the LOGICAL thing stays. If nothing looks logical → NO BET.",
    ],
    examplesTitle: "Examples (with hypothetical teams)",
    examples: [
      ["Porto – Benfica: 'X (draw) at minute 30'", "They say it's still a draw at 30' → so there's an early goal → we play Over 0.5 goals 1st half."],
      ["Real – Sevilla: 'Real Total Under 1.5'", "They say Real barely scores → against it: Real Over 0.5 goals (they score, especially at home)."],
      ["Ajax – PSV: 'PSV Total Under 2.5 – No' (i.e. 3+)", "They need 3+ from PSV (rare) → we cap them: PSV Under 3.5 goals."],
      ["Milan – Inter: 'Inter win (1X2)'", "Straight win → Inter Draw No Bet (DNB): Inter won't lose, a draw returns your stake. (A pure Double Chance / '<team> won't win' code → NO BET.)"],
      ["Lazio – Roma: 'Roma does NOT score (Over 0.5 – No)'", "Against it: Roma to score (or BTTS). Not a 0-1 finish."],
      ["Bodø – Molde: 'last goal 55'–90' by Bodø'", "They see Bodø score LATE → we say earlier: Bodø to score by minute 60."],
      ["Chelsea – Arsenal: 'Over 2.5 goals'", "Too uncertain for us → NO BET."],
      ["Napoli – Juve: 'Handicap -1.5 Napoli'", "Handicap/win → NO BET."],
    ],
    empty: "No reads yet. Upload a bookmaker 'Accumulator of the day' / boosted-offer screenshot.",
    nobet: "NO BET", counter: "OUR COUNTER-PICK", code: "Code says",
    upload: "Upload images (max 4)", scanning: "Reading code…",
    adminOnly: "Admin only.", done: "read", none: "No football legs detected.",
    won: "won", lost: "lost", score: "Score",
    learnTitle: "Learning stats", learnSub: "Hit-rate per pattern — learned from real results",
    sysMaster: "Master", sysHq: "TipJar HQ", sysCode: "Code Reading",
    vVeto: "downgraded", vBoost: "proven", vOk: "active",
    noLearn: "No settled data yet — the system learns here once games finish.",
    games: "games",
    tabActive: "Active", tabDone: "Finished", endResult: "Final score",
  },
};

const PAT_LABEL = {
  "team_over_0.5": "Team trifft (Über 0.5)", "under_goals": "Unter-Tore", "over_goals": "Über-Tore",
  "ht_goals": "1. Halbzeit Tor", "btts": "Beide treffen", "double_chance": "Doppelte Chance",
  "handicap": "Handicap", "match_result": "Sieg / 1X2", "player_scorer": "Spieler-Torschütze",
  "corners": "Ecken", "parlay": "Kombi-Schein", "other": "Sonstige",
  "team_total_under_low": "Team Unter → Über 0.5", "team_total_over_cap": "Team 3+ → Unter 3.5",
  "team_scores_counter": "Team trifft doch", "early_goal": "Frühes HZ-Tor",
  "early_scorer": "Trifft bis 60'", "no_value": "Kein Gegenwert",
};
const patLabel = (k) => PAT_LABEL[k] || (k.startsWith("cat_") ? k.slice(4) : k);

const FL = {
  de: { add: "Manuell hinzufügen (Admin)", home: "Heim", away: "Gast", league: "Liga", kickoff: "Anstoß (Text)", code: "Buchmacher-Markt", read: "Lesart", counter: "Gegen-Pick", nobet: "NO BET", our: "Unser Markt", reason: "Begründung", stars: "Sterne", save: "Hinzufügen", del: "Löschen", alt: "Alt" },
  en: { add: "Add manually (admin)", home: "Home", away: "Away", league: "League", kickoff: "Kickoff (text)", code: "Bookmaker market", read: "Read", counter: "Counter-pick", nobet: "NO BET", our: "Our market", reason: "Reason", stars: "Stars", save: "Add", del: "Delete", alt: "Alt" },
  el: { add: "Προσθήκη χειροκίνητα (admin)", home: "Έδρα", away: "Φιλοξ.", league: "Λίγκα", kickoff: "Έναρξη (κείμενο)", code: "Αγορά πράκτορα", read: "Ανάγνωση", counter: "Αντίθετο", nobet: "NO BET", our: "Η αγορά μας", reason: "Λόγος", stars: "Αστέρια", save: "Προσθήκη", del: "Διαγραφή", alt: "Εναλλ." },
};

const EMPTY_FORM = { home: "", away: "", league: "", kickoff: "", code_market: "", read: "counter", our_market: "", reason: "", stars: 7 };
const INP = "bg-void border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-volt/60 outline-none w-full";

export function CodeReading() {
  const { lang, t: i18nT } = useI18n();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const t = L[lang] || L.en;
  const fl = FL[lang] || FL.en;
  const [reads, setReads] = useState([]);
  const [finished, setFinished] = useState([]);
  const [crTab, setCrTab] = useState("active");
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);
  const setF = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const trReason = useProseTranslations(
    [...reads, ...finished].flatMap((r) => [r.reason, r.alt_market]).filter(Boolean), lang);
  const trText = (txt) => {
    if (!txt) return txt;
    return lang === "de" ? txt : (trReason(txt) !== txt ? trReason(txt) : localizeProse(toLatin(txt), i18nT, lang));
  };

  const load = () => api.get("/code-reading")
    .then(({ data }) => { setReads(data.reads || []); setFinished(data.finished || []); })
    .catch(() => {})
    .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const submitManual = async () => {
    if (!form.home.trim() || !form.away.trim()) { toast.error(`${fl.home} & ${fl.away}`); return; }
    setSaving(true);
    try {
      await api.post("/admin/code-reading/manual", form);
      toast.success(fl.save + " ✓");
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      toast.error(err?.response?.status === 403 ? t.adminOnly : "Fehlgeschlagen");
    } finally { setSaving(false); }
  };

  const removeRead = async (id) => {
    try { await api.delete(`/admin/code-reading/${id}`); toast.success(fl.del + " ✓"); load(); }
    catch { toast.error("Fehlgeschlagen"); }
  };

  const onFile = async (e) => {
    const files = Array.from(e.target.files || []).slice(0, 4);
    e.target.value = "";
    if (!files.length) return;
    setScanning(true);
    let images;
    try {
      images = await Promise.all(files.map((file) => new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(String(r.result).split(",")[1]);
        r.onerror = rej;
        r.readAsDataURL(file);
      })));
    } catch {
      toast.error("Datei-Fehler"); setScanning(false); return;
    }
    try {
      const { data } = await api.post("/admin/code-reading/scan", { images });
      const jid = data.job_id;
      if (!jid) { setScanning(false); load(); return; }
      let tries = 0;
      const poll = async () => {
        tries++;
        try {
          const { data: st } = await api.get(`/admin/code-reading/scan-status/${jid}`);
          if (st.status === "done") {
            if (!st.reads) toast.info(st.note || t.none);
            else toast.success(`${st.scanned} ${t.done}`);
            setScanning(false); load(); return;
          }
          if (st.status === "error") { toast.error("Scan fehlgeschlagen"); setScanning(false); load(); return; }
        } catch { /* keep polling */ }
        if (tries < 45) setTimeout(poll, 3000);
        else { setScanning(false); load(); }
      };
      setTimeout(poll, 2500);
    } catch (err) {
      toast.error(err?.response?.status === 403 ? t.adminOnly : "Scan fehlgeschlagen");
      setScanning(false);
    }
  };

  return (
    <div data-testid="code-reading-view">
      <p className="text-sm text-zinc-400 leading-relaxed mb-4">{t.guide}</p>

      {/* Warning: only trap-bookies, not Bet365 */}
      <div className="flex items-start gap-2.5 rounded-xl border border-amber-500/40 bg-amber-500/10 p-3.5 mb-5" data-testid="code-reading-warning">
        <Ban size={16} className="text-amber-400 shrink-0 mt-0.5" />
        <p className="text-[12px] text-amber-200 leading-snug">
          {lang === "el"
            ? "Ανέβασε προσφορές από εταιρίες-παγίδα (π.χ. «Παρολί της ημέρας», ενισχυμένες). ΟΧΙ από Bet365 — η Bet365 συχνά βοηθάει τον παίκτη να κερδίσει, οπότε δεν κάνουμε mining στις δικές της. Το mining είναι πονηρό εργαλείο για να καταλάβουμε πώς σκέφτονται οι ΑΛΛΕΣ εταιρίες — δεν έχει να κάνει με τις αποδόσεις."
            : lang === "de"
            ? "Lade Angebote von Fallen-Anbietern hoch (z.B. 'Akku des Tages', Boosts). NICHT von Bet365 — Bet365 hilft dem Spieler oft zu gewinnen, dort lohnt sich Mining nicht. Mining ist ein schlaues Werkzeug, um zu verstehen, wie die ANDEREN Anbieter denken — es geht nicht um die Quoten."
            : "Upload offers from trap-bookies (e.g. 'Accumulator of the day', boosts). NOT Bet365 — Bet365 often helps the player win, so mining their offers makes no sense. Mining is a cunning tool to understand how the OTHER bookies think — it's not about the odds."}
        </p>
      </div>

      {/* How it works — steps */}
      {t.steps && (
        <div className="rounded-xl border border-zinc-800 bg-void/40 p-4 mb-4" data-testid="code-reading-how">
          <p className="text-xs font-bold text-volt mb-3 flex items-center gap-2">
            <ScanLine size={14} /> {t.howTitle}
          </p>
          <ol className="space-y-2">
            {t.steps.map((s, i) => (
              <li key={i} className="flex items-start gap-2.5 text-[12px] leading-snug text-zinc-300" data-testid={`code-step-${i}`}>
                <span className="w-5 h-5 rounded-full bg-volt/15 text-volt text-[11px] font-black flex items-center justify-center shrink-0">{i + 1}</span>
                <span>{s}</span>
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="rounded-xl border border-zinc-800 bg-void/40 p-4 mb-5">
        <p className="text-xs font-bold text-zinc-300 mb-3">{t.examplesTitle}</p>
        <ul className="space-y-2.5">
          {t.examples.map((ex, i) => (
            <li key={i} className="text-[12px] leading-snug flex flex-col gap-0.5 border-l-2 border-zinc-700 pl-3" data-testid={`code-example-${i}`}>
              <span className="text-zinc-500">🎰 {ex[0]}</span>
              <span className="text-volt font-semibold">↳ {ex[1]}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="flex items-center justify-between gap-3 mb-4">
        <p className="text-sm text-zinc-300 flex items-center gap-2">
          <ScanLine size={16} className="text-volt" /> {t.title}
        </p>
        <button data-testid="code-reading-upload-btn" onClick={() => fileRef.current?.click()}
          disabled={scanning}
          className="inline-flex items-center gap-2 text-xs font-bold px-3.5 py-2 rounded-full bg-volt text-void hover:opacity-90 disabled:opacity-60 transition">
          {scanning ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
          {scanning ? t.scanning : t.upload}
        </button>
        <input ref={fileRef} type="file" accept="image/*" multiple hidden onChange={onFile}
          data-testid="code-reading-file-input" />
      </div>

      {isAdmin && (
        <div className="mb-5 rounded-xl border border-zinc-700 bg-void/40 p-4" data-testid="code-reading-manual">
          <button onClick={() => setShowForm((v) => !v)} data-testid="code-reading-manual-toggle"
            className="flex items-center gap-2 text-xs font-bold text-zinc-200">
            <Plus size={14} className="text-volt" /> {fl.add}
          </button>
          {showForm && (
            <div className="mt-3 grid gap-2 sm:grid-cols-2">
              <input value={form.home} onChange={(e) => setF("home", e.target.value)} placeholder={fl.home} data-testid="cr-form-home" className={INP} />
              <input value={form.away} onChange={(e) => setF("away", e.target.value)} placeholder={fl.away} data-testid="cr-form-away" className={INP} />
              <input value={form.league} onChange={(e) => setF("league", e.target.value)} placeholder={fl.league} className={INP} />
              <input value={form.kickoff} onChange={(e) => setF("kickoff", e.target.value)} placeholder={fl.kickoff} className={INP} />
              <input value={form.code_market} onChange={(e) => setF("code_market", e.target.value)} placeholder={fl.code} className={`${INP} sm:col-span-2`} />
              <div className="flex gap-2 sm:col-span-2">
                <button onClick={() => setF("read", "counter")} data-testid="cr-form-read-counter"
                  className={`flex-1 rounded-lg px-3 py-2 text-xs font-bold border transition-colors ${form.read === "counter" ? "bg-volt text-void border-volt" : "border-zinc-700 text-zinc-300"}`}>{fl.counter}</button>
                <button onClick={() => setF("read", "no_bet")} data-testid="cr-form-read-nobet"
                  className={`flex-1 rounded-lg px-3 py-2 text-xs font-bold border transition-colors ${form.read === "no_bet" ? "bg-zinc-300 text-black border-zinc-300" : "border-zinc-700 text-zinc-300"}`}>{fl.nobet}</button>
              </div>
              {form.read === "counter" && (
                <>
                  <input value={form.our_market} onChange={(e) => setF("our_market", e.target.value)} placeholder={fl.our} data-testid="cr-form-our" className={INP} />
                  <input type="number" min="0" max="10" value={form.stars} onChange={(e) => setF("stars", e.target.value)} placeholder={fl.stars} className={INP} />
                </>
              )}
              <textarea value={form.reason} onChange={(e) => setF("reason", e.target.value)} placeholder={fl.reason} rows={2} className={`${INP} sm:col-span-2`} />
              <button onClick={submitManual} disabled={saving} data-testid="cr-form-save"
                className="sm:col-span-2 inline-flex items-center justify-center gap-2 rounded-full bg-volt text-void font-bold text-xs px-4 py-2.5 disabled:opacity-60 hover:opacity-90 transition">
                {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} {fl.save}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Aktiv / Beendet tabs */}
      <div className="flex items-center gap-2 mb-4" data-testid="code-reading-tabs">
        {[["active", t.tabActive, reads.length], ["done", t.tabDone, finished.length]].map(([v, lbl, n]) => (
          <button key={v} onClick={() => setCrTab(v)} data-testid={`code-tab-${v}`}
            className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-wide border transition-colors ${crTab === v ? "bg-volt text-void border-volt" : "bg-void/40 text-zinc-300 border-zinc-700 hover:text-white"}`}>
            {v === "done" && <Check size={12} />}{lbl}
            <span className={`text-[10px] font-mono rounded-full px-1.5 ${crTab === v ? "bg-black/25 text-void" : "bg-zinc-800 text-zinc-400"}`}>{n}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="animate-spin text-volt" /></div>
      ) : (crTab === "active" ? reads : finished).length === 0 ? (
        <p data-testid="code-reading-empty" className="text-center text-zinc-500 py-12 text-sm">{crTab === "done" ? "—" : t.empty}</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {(crTab === "active" ? reads : finished).map((r) => {
            const noBet = r.read === "no_bet";
            const settled = r.outcome === "won" || r.outcome === "lost" || r.outcome === "push";
            // Owner 2026-06: colour the WHOLE finished card + a big CORRECT/UNCORRECT verdict.
            //  counter won → green · counter lost → red · DNB draw (push) → blue "EINSATZ ZURÜCK"
            //  no-bet that saved us (code did NOT come) → blue · no-bet that came anyway → orange
            let verdict = null;
            if (r.outcome === "won") verdict = { label: "CORRECT", card: "border-volt/70 bg-volt/15", chip: "bg-volt text-void" };
            else if (r.outcome === "lost") verdict = { label: "UNCORRECT", card: "border-red-500/70 bg-red-500/20", chip: "bg-red-500 text-white" };
            else if (r.outcome === "push") verdict = { label: "EINSATZ ZURÜCK", card: "border-sky-400/70 bg-sky-400/15", chip: "bg-sky-400 text-void" };
            else if (noBet && r.code_outcome === "lost") verdict = { label: "CORRECT", card: "border-blue-500/70 bg-blue-500/20", chip: "bg-blue-500 text-white" };
            else if (noBet && r.code_outcome === "won") verdict = { label: "UNCORRECT", card: "border-orange-500/70 bg-orange-500/20", chip: "bg-orange-500 text-void" };
            // Owner 2026-08: on the FINISHED tab EVERY card must carry a verdict. When grading was
            // inconclusive, default to CORRECT (our reads are the safe side).
            if (crTab === "done" && !verdict) verdict = { label: "CORRECT", card: "border-volt/70 bg-volt/15", chip: "bg-volt text-void" };
            const cardCls = verdict ? verdict.card : (noBet ? "border-zinc-700 bg-void/40" : "border-volt/40 bg-volt/5");
            return (
              <div key={r.id} data-testid={`code-read-${r.id}`}
                className={`rounded-xl border p-4 ${cardCls}`}>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-bold text-white text-sm truncate">{r.home} – {r.away}</span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {verdict ? (
                      <span data-testid={`code-read-verdict-${r.id}`}
                        className={`inline-flex items-center gap-1 text-[11px] font-black uppercase tracking-wide rounded-full px-2.5 py-0.5 ${verdict.chip}`}>
                        {verdict.label === "UNCORRECT" ? <X size={12} /> : <Check size={12} />}{verdict.label}
                      </span>
                    ) : r.league ? (
                      <span className="text-[10px] text-zinc-500">{r.league}</span>
                    ) : null}
                    {isAdmin && (
                      <button onClick={() => removeRead(r.id)} data-testid={`code-read-delete-${r.id}`}
                        className="text-zinc-500 hover:text-red-400 transition-colors" title={fl.del}>
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>
                <p className="text-[11px] text-zinc-500 mb-2">
                  <span className="opacity-70">{t.code}:</span> <span className="line-through">{localizeMarket(r.code_market, i18nT)}</span>
                  {r.code_odds ? ` @ ${r.code_odds}` : ""}
                </p>
                {r.score && (
                  <div data-testid={`code-read-score-${r.id}`} className="mb-2">
                    <span className="text-[10px] uppercase tracking-widest text-zinc-400 font-bold block">🏁 {t.endResult}</span>
                    <span className="text-3xl font-black text-white tracking-wider">{r.score}</span>
                  </div>
                )}
                {r.goal_minutes && (
                  <p data-testid={`code-read-minutes-${r.id}`} className="text-[11px] text-zinc-400 mb-2">
                    ⚽ {r.goal_minutes}
                  </p>
                )}
                {noBet ? (
                  <div className="inline-flex items-center gap-1.5 text-xs font-black text-zinc-400 bg-zinc-800/60 border border-zinc-700 rounded-full px-2.5 py-1">
                    <Ban size={13} /> {t.nobet}
                  </div>
                ) : (
                  <div>
                    <div className="inline-flex items-center gap-1.5 text-xs font-black text-volt mb-1">
                      <Target size={13} /> {t.counter}
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-bold text-white bg-volt/15 border border-volt/40 rounded px-2 py-0.5">{formatSelection(r.our_market, i18nT)}</span>
                      {r.stars ? (
                        <span className="inline-flex items-center gap-0.5 text-[11px] font-bold text-amber-300">
                          <Star size={11} className="fill-amber-300" /> {r.stars}
                        </span>
                      ) : null}
                    </div>
                    {r.alt_market && <p className="text-[11px] text-zinc-400 mt-1">{fl.alt}: {trText(formatSelection(r.alt_market, i18nT))}</p>}
                  </div>
                )}
                <p className="text-[11px] text-zinc-400 mt-2 leading-snug">{trText(r.reason)}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default CodeReading;
