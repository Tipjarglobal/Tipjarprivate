import React, { useEffect, useRef, useState } from "react";
import { ScanLine, Ban, Target, Upload, Loader2, Star } from "lucide-react";
import { toast } from "sonner";
import api from "../api";
import { useI18n } from "../i18n";

const L = {
  de: {
    title: "Code Reading",
    guideTitle: "So funktioniert dieser Bereich",
    guide: "Die fertigen Scheine der Wettanbieter (z.B. „Akku des Tages") sind meistens so gebaut, dass DU verlierst. Wir lesen den Schein und spielen bewusst DAGEGEN — oder machen NO BET. Lade unten einen Screenshot hoch, die KI liest jedes Spiel und gibt dir unsere Gegen-Lesart.",
    examplesTitle: "Beispiele",
    examples: [
      ["Sie sagen: Rangers Sieg (1X2 S2)", "NO BET — es ist nicht normal, auf glatten Sieg / 1X zu gehen."],
      ["Sie sagen: Brügge gewinnt & Union trifft NICHT", "Wir nehmen Union trifft (oder beide treffen). Nicht dass es 0:1 endet."],
      ["Sie sagen: Bodø/Glimt Unentschieden in der 15. Minute", "Wir denken, bis dahin fällt ein Tor → Über 0.5 Tore 1. Halbzeit, 10 Sterne."],
      ["Sie sagen: LASK Über 2.5 Tore", "NO BET — zu unsicher."],
      ["Sie sagen: Sparta Prag trifft spät (55–90)", "Dann haben sie bis zur 55.–60. schon getroffen → Sparta trifft bis zur 60."],
    ],
    empty: "Noch keine Reads. Lade einen SpinBetter-„Akku des Tages"-Screenshot hoch.",
    nobet: "NO BET", counter: "UNSER GEGEN-PICK", code: "Code sagt",
    upload: "SpinBetter-Screenshot hochladen", scanning: "Lese Code…",
    adminOnly: "Nur für Admin.", done: "gelesen", none: "Keine Fußball-Legs erkannt.",
    resultsTitle: "Die KI-Ergebnisse",
  },
  el: {
    title: "Ανάγνωση Κωδικών",
    guideTitle: "Πώς λειτουργεί αυτή η ενότητα",
    guide: "Τα έτοιμα κουπόνια των πρακτόρων (π.χ. «Παρολί ημέρας») είναι συνήθως φτιαγμένα για να ΧΑΝΕΙΣ. Εμείς διαβάζουμε το κουπόνι και παίζουμε ΑΝΤΙΘΕΤΑ — ή κάνουμε NO BET. Ανέβασε ένα screenshot και η AI διαβάζει κάθε ματς.",
    examplesTitle: "Παραδείγματα",
    examples: [
      ["Λένε: Νίκη Rangers (1X2 S2)", "NO BET — δεν είναι φυσιολογικό να πας σε καθαρή νίκη / 1X."],
      ["Λένε: Μπρυζ νικά & η Union ΔΕΝ σκοράρει", "Παίρνουμε Union σκοράρει (ή σκοράρουν και οι δύο)."],
      ["Λένε: Bodø/Glimt ισοπαλία στο 15'", "Πιστεύουμε ότι θα πέσει γκολ → Over 0.5 γκολ ημιχρόνου, 10 αστέρια."],
      ["Λένε: LASK Over 2.5", "NO BET — πολύ αβέβαιο."],
      ["Λένε: Σπάρτα Πράγας σκοράρει αργά (55–90)", "Άρα θα έχει σκοράρει ως το 55'–60' → σκοράρει ως το 60'."],
    ],
    empty: "Καμία ανάγνωση ακόμη. Ανέβασε ένα screenshot «Παρολί ημέρας».",
    nobet: "NO BET", counter: "ΤΟ ΑΝΤΙΘΕΤΟ ΜΑΣ", code: "Ο κώδικας λέει",
    upload: "Ανέβασε screenshot", scanning: "Διαβάζω κώδικα…",
    adminOnly: "Μόνο για διαχειριστή.", done: "διαβάστηκαν", none: "Δεν βρέθηκαν ποδοσφαιρικά legs.",
    resultsTitle: "Τα αποτελέσματα της AI",
  },
  en: {
    title: "Code Reading",
    guideTitle: "How this section works",
    guide: "Bookmakers' ready-made slips (e.g. 'Accumulator of the day') are mostly built to make YOU lose. We read the slip and deliberately play AGAINST it — or NO BET. Upload a screenshot below; the AI reads every game and gives our counter-read.",
    examplesTitle: "Examples",
    examples: [
      ["They say: Rangers win (1X2 S2)", "NO BET — backing a straight win / 1X isn't our style."],
      ["They say: Bruges win & Union DON'T score", "We take Union to score (or BTTS). Not a 0-1 finish."],
      ["They say: Bodø/Glimt draw at minute 15", "We expect a goal by then → Over 0.5 goals 1st half, 10 stars."],
      ["They say: LASK Over 2.5 goals", "NO BET — too loose."],
      ["They say: Sparta Prague scores late (55–90)", "Then they've scored by the 55–60' → scores by minute 60."],
    ],
    empty: "No reads yet. Upload a SpinBetter 'Accumulator of the day' screenshot.",
    nobet: "NO BET", counter: "OUR COUNTER-PICK", code: "Code says",
    upload: "Upload SpinBetter screenshot", scanning: "Reading code…",
    adminOnly: "Admin only.", done: "read", none: "No football legs detected.",
    resultsTitle: "The AI results",
  },
};

export function CodeReading() {
  const { lang } = useI18n();
  const t = L[lang] || L.en;
  const [reads, setReads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const fileRef = useRef(null);

  const load = () => api.get("/code-reading")
    .then(({ data }) => setReads(data.reads || []))
    .catch(() => {})
    .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
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

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="animate-spin text-volt" /></div>
      ) : reads.length === 0 ? (
        <p data-testid="code-reading-empty" className="text-center text-zinc-500 py-16 text-sm">{t.empty}</p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {reads.map((r) => {
            const noBet = r.read === "no_bet";
            return (
              <div key={r.id} data-testid={`code-read-${r.id}`}
                className={`rounded-xl border p-4 ${noBet ? "border-zinc-700 bg-void/40" : "border-volt/40 bg-volt/5"}`}>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="font-bold text-white text-sm truncate">{r.home} – {r.away}</span>
                  {r.league && <span className="text-[10px] text-zinc-500 shrink-0">{r.league}</span>}
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
