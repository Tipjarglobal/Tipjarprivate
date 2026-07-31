import React, { useEffect, useRef, useState } from "react";
import { ScanLine, Ban, Target, Upload, Loader2, Star, Check, X, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import api from "../api";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";

const L = {
  de: {
    title: "Code Reading",
    guide: "Die fertigen Scheine der Wettanbieter (z.B. Akku des Tages) sind meistens so gebaut, dass DU verlierst. Wir lesen den Schein und spielen bewusst DAGEGEN — oder machen NO BET. Lade unten einen Screenshot hoch, die KI liest jedes Spiel und gibt dir unsere Gegen-Lesart. Danach lernt das System aus dem echten Ergebnis, welche Lesart spielbar ist.",
    examplesTitle: "Beispiele",
    examples: [
      ["Sie sagen: Motor 'Gesamtzahl 1 Unter 1.5'", "Motor Über 0.5 Tore — sie treffen zuhause / wenn der Gegner ein wichtigeres Spiel vor der Brust hat."],
      ["Sie sagen: Widzew 'Gesamtzahl 2 Unter 2.5 – Nein' (also 3+)", "Widzew Unter 3.5 Tore — 3 Tore sind selten, wir deckeln."],
      ["Sie sagen: Rangers Sieg (1X2 S2)", "NO BET — es ist nicht normal, auf glatten Sieg / 1X zu gehen."],
      ["Sie sagen: Team trifft NICHT (Über 0.5 – Nein)", "Wir nehmen: Team trifft (oder beide treffen). Nicht dass es 0:1 endet."],
      ["Sie sagen: Unentschieden in der 15. Minute", "Bis dahin fällt ein Tor → Über 0.5 Tore 1. Halbzeit, 10 Sterne."],
    ],
    empty: "Noch keine Reads. Lade einen Buchmacher-Screenshot (Akku des Tages) hoch.",
    nobet: "NO BET", counter: "UNSER GEGEN-PICK", code: "Code sagt",
    upload: "Screenshot hochladen", scanning: "Lese Code…",
    adminOnly: "Nur für Admin.", done: "gelesen", none: "Keine Fußball-Legs erkannt.",
    won: "gewonnen", lost: "verloren", score: "Ergebnis",
    learnTitle: "Lern-Statistik", learnSub: "Trefferquote je Muster — aus echten Ergebnissen gelernt",
    sysMaster: "Master", sysHq: "TipJar HQ", sysCode: "Code Reading",
    vVeto: "herabgestuft", vBoost: "bewährt", vOk: "aktiv",
    noLearn: "Noch keine abgerechneten Daten — sobald Spiele fertig sind, lernt das System hier.",
    games: "Spiele",
  },
  el: {
    title: "Ανάγνωση Κωδικών",
    guide: "Τα έτοιμα κουπόνια των πρακτόρων (π.χ. «Παρολί ημέρας») είναι φτιαγμένα για να ΧΑΝΕΙΣ. Διαβάζουμε το κουπόνι και παίζουμε ΑΝΤΙΘΕΤΑ — ή NO BET. Ανέβασε screenshot· μετά το σύστημα μαθαίνει από το πραγματικό αποτέλεσμα.",
    examplesTitle: "Παραδείγματα",
    examples: [
      ["Λένε: Ομάδα «Σύνολο Under 1.5»", "Ομάδα Over 0.5 — σκοράρει, ειδικά εντός έδρας."],
      ["Λένε: Ομάδα «Σύνολο Under 2.5 – Όχι» (δηλ. 3+)", "Ομάδα Under 3.5 — τα 3 γκολ είναι σπάνια."],
      ["Λένε: Νίκη Rangers (1X2 S2)", "NO BET — δεν πάμε σε καθαρή νίκη / 1X."],
      ["Λένε: Ομάδα ΔΕΝ σκοράρει", "Παίρνουμε: σκοράρει (ή σκοράρουν και οι δύο)."],
      ["Λένε: Ισοπαλία στο 15'", "Over 0.5 γκολ ημιχρόνου, 10 αστέρια."],
    ],
    empty: "Καμία ανάγνωση ακόμη. Ανέβασε ένα screenshot «Παρολί ημέρας».",
    nobet: "NO BET", counter: "ΤΟ ΑΝΤΙΘΕΤΟ ΜΑΣ", code: "Ο κώδικας λέει",
    upload: "Ανέβασε screenshot", scanning: "Διαβάζω κώδικα…",
    adminOnly: "Μόνο για διαχειριστή.", done: "διαβάστηκαν", none: "Δεν βρέθηκαν legs.",
    won: "κερδισμένο", lost: "χαμένο", score: "Σκορ",
    learnTitle: "Στατιστικά Μάθησης", learnSub: "Ποσοστό επιτυχίας ανά μοτίβο — από πραγματικά αποτελέσματα",
    sysMaster: "Master", sysHq: "TipJar HQ", sysCode: "Ανάγνωση Κωδικών",
    vVeto: "υποβαθμισμένο", vBoost: "δοκιμασμένο", vOk: "ενεργό",
    noLearn: "Δεν υπάρχουν ακόμη δεδομένα — το σύστημα μαθαίνει μόλις τελειώσουν αγώνες.",
    games: "αγώνες",
  },
  en: {
    title: "Code Reading",
    guide: "Bookmakers' ready-made slips (e.g. 'Accumulator of the day') are mostly built to make YOU lose. We read the slip and deliberately play AGAINST it — or NO BET. Upload a screenshot; then the system learns from the real result which reads are playable.",
    examplesTitle: "Examples",
    examples: [
      ["They say: Team 'Total Under 1.5'", "Team Over 0.5 — they score, especially at home."],
      ["They say: Team 'Total Under 2.5 – No' (i.e. 3+)", "Team Under 3.5 — 3 goals is rare, we cap them."],
      ["They say: Rangers win (1X2 S2)", "NO BET — backing a straight win / 1X isn't our style."],
      ["They say: Team does NOT score", "We take: team to score (or BTTS). Not a 0-1 finish."],
      ["They say: Draw at minute 15", "Over 0.5 goals 1st half, 10 stars."],
    ],
    empty: "No reads yet. Upload a bookmaker 'Accumulator of the day' screenshot.",
    nobet: "NO BET", counter: "OUR COUNTER-PICK", code: "Code says",
    upload: "Upload screenshot", scanning: "Reading code…",
    adminOnly: "Admin only.", done: "read", none: "No football legs detected.",
    won: "won", lost: "lost", score: "Score",
    learnTitle: "Learning stats", learnSub: "Hit-rate per pattern — learned from real results",
    sysMaster: "Master", sysHq: "TipJar HQ", sysCode: "Code Reading",
    vVeto: "downgraded", vBoost: "proven", vOk: "active",
    noLearn: "No settled data yet — the system learns here once games finish.",
    games: "games",
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
  de: { add: "Manuell hinzufügen (Admin)", home: "Heim", away: "Gast", league: "Liga", kickoff: "Anstoß (Text)", code: "Buchmacher-Markt", read: "Lesart", counter: "Gegen-Pick", nobet: "NO BET", our: "Unser Markt", reason: "Begründung", stars: "Sterne", save: "Hinzufügen", del: "Löschen" },
  en: { add: "Add manually (admin)", home: "Home", away: "Away", league: "League", kickoff: "Kickoff (text)", code: "Bookmaker market", read: "Read", counter: "Counter-pick", nobet: "NO BET", our: "Our market", reason: "Reason", stars: "Stars", save: "Add", del: "Delete" },
  el: { add: "Προσθήκη χειροκίνητα (admin)", home: "Έδρα", away: "Φιλοξ.", league: "Λίγκα", kickoff: "Έναρξη (κείμενο)", code: "Αγορά πράκτορα", read: "Ανάγνωση", counter: "Αντίθετο", nobet: "NO BET", our: "Η αγορά μας", reason: "Λόγος", stars: "Αστέρια", save: "Προσθήκη", del: "Διαγραφή" },
};

const EMPTY_FORM = { home: "", away: "", league: "", kickoff: "", code_market: "", read: "counter", our_market: "", reason: "", stars: 7 };
const INP = "bg-void border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-zinc-500 focus:border-volt/60 outline-none w-full";

export function CodeReading() {
  const { lang } = useI18n();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const t = L[lang] || L.en;
  const fl = FL[lang] || FL.en;
  const [reads, setReads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);
  const setF = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const load = () => api.get("/code-reading")
    .then(({ data }) => setReads(data.reads || []))
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
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setScanning(true);
    try {
      const b64 = await new Promise((res, rej) => {
        const r = new FileReader();
        r.onload = () => res(String(r.result).split(",")[1]);
        r.onerror = rej;
        r.readAsDataURL(file);
      });
      const { data } = await api.post("/admin/code-reading/scan", { images: [b64] });
      if (!data.reads) { toast.info(data.note || t.none); }
      else { toast.success(`${data.scanned} ${t.done}`); }
      load();
    } catch (err) {
      toast.error(err?.response?.status === 403 ? t.adminOnly : "Scan fehlgeschlagen");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div data-testid="code-reading-view">
      <p className="text-sm text-zinc-400 leading-relaxed mb-4">{t.guide}</p>

      <div className="rounded-xl border border-zinc-800 bg-void/40 p-4 mb-5">
        <p className="text-xs font-bold text-zinc-300 mb-2">{t.examplesTitle}</p>
        <ul className="space-y-2">
          {t.examples.map((ex, i) => (
            <li key={i} className="text-[12px] leading-snug" data-testid={`code-example-${i}`}>
              <span className="text-zinc-500">{ex[0]} →</span>{" "}
              <span className="text-zinc-200 font-medium">{ex[1]}</span>
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
        <input ref={fileRef} type="file" accept="image/*" hidden onChange={onFile}
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

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="animate-spin text-volt" /></div>
      ) : reads.length === 0 ? (
        <p data-testid="code-reading-empty" className="text-center text-zinc-500 py-12 text-sm">{t.empty}</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {reads.map((r) => {
            const noBet = r.read === "no_bet";
            const settled = r.outcome === "won" || r.outcome === "lost";
            return (
              <div key={r.id} data-testid={`code-read-${r.id}`}
                className={`rounded-xl border p-4 ${noBet ? "border-zinc-700 bg-void/40" : "border-volt/40 bg-volt/5"}`}>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-bold text-white text-sm truncate">{r.home} – {r.away}</span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    {settled ? (
                      <span data-testid={`code-read-outcome-${r.id}`}
                        className={`inline-flex items-center gap-1 text-[10px] font-black rounded-full px-2 py-0.5 ${r.outcome === "won" ? "bg-volt/20 text-volt" : "bg-red-500/15 text-red-400"}`}>
                        {r.outcome === "won" ? <Check size={11} /> : <X size={11} />}
                        {r.outcome === "won" ? t.won : t.lost}{r.score ? ` ${r.score}` : ""}
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
                  <span className="opacity-70">{t.code}:</span> <span className="line-through">{r.code_market}</span>
                  {r.code_odds ? ` @ ${r.code_odds}` : ""}
                </p>
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
                      <span className="text-sm font-bold text-white bg-volt/15 border border-volt/40 rounded px-2 py-0.5">{r.our_market}</span>
                      {r.stars ? (
                        <span className="inline-flex items-center gap-0.5 text-[11px] font-bold text-amber-300">
                          <Star size={11} className="fill-amber-300" /> {r.stars}
                        </span>
                      ) : null}
                    </div>
                    {r.alt_market && <p className="text-[11px] text-zinc-400 mt-1">alt: {r.alt_market}</p>}
                  </div>
                )}
                <p className="text-[11px] text-zinc-400 mt-2 leading-snug">{r.reason}</p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default CodeReading;
