import React from "react";
import { Sparkles, Brain, Crown, Flag, Target } from "lucide-react";

// RASTER 3 — KI-Pillen: hellblaues Info-Raster + KI-Pillen kompakt (2 Spalten).
const T = {
  de: { info: "Die KI macht manchmal Fehler. Manchmal stimmen Uhrzeit, Quote oder Markt nicht (z.B. kein Über 0.5). Dafür gibt es oben bei jedem Tipp den blauen Korrektur-Knopf: Foto vom Buchmacher-Schein posten, die KI übernimmt automatisch.",
    single: "KI Single-Game-Picks", smart: "Smart Picks ansehen", smartCta: "Mit der KI reden", master: "Master", settled: "Abgerechnet", stats: "Statistiken" },
  en: { info: "The AI sometimes makes mistakes — kickoff time, odds or market may be off (e.g. no Over 0.5). That's why every tip has the blue correction button on top: post a photo of your bookmaker slip and the AI takes over automatically.",
    single: "AI Single-Game Picks", smart: "See Smart Picks", smartCta: "Talk to the AI", master: "Master", settled: "Settled", stats: "Statistics" },
  es: { info: "La IA a veces se equivoca: la hora, la cuota o el mercado pueden fallar (p. ej. sin Más de 0.5). Por eso cada pronóstico tiene el botón azul de corrección arriba: sube una foto de tu boleto y la IA se encarga.",
    single: "Picks de un partido IA", smart: "Ver Smart Picks", smartCta: "Habla con la IA", master: "Master", settled: "Liquidado", stats: "Estadísticas" },
  el: { info: "Η ΤΝ κάνει μερικές φορές λάθη — ώρα, απόδοση ή αγορά μπορεί να μην ταιριάζουν. Γι' αυτό κάθε tip έχει πάνω το μπλε κουμπί διόρθωσης: ανέβασε φωτό του δελτίου και η ΤΝ αναλαμβάνει.",
    single: "KI Single-Game Picks", smart: "Δες Smart Picks", smartCta: "Μίλα με την ΤΝ", master: "Master", settled: "Εκκαθαρισμένα", stats: "Στατιστικά" },
  fr: { info: "L'IA se trompe parfois — l'heure, la cote ou le marché peuvent être faux (ex. pas de Plus de 0.5). C'est pourquoi chaque pronostic a le bouton bleu de correction en haut : poste une photo de ton ticket et l'IA prend le relais.",
    single: "Picks un match IA", smart: "Voir Smart Picks", smartCta: "Parler à l'IA", master: "Master", settled: "Réglé", stats: "Statistiques" },
  it: { info: "L'IA a volte sbaglia — orario, quota o mercato possono non tornare (es. niente Over 0.5). Per questo ogni tip ha in alto il pulsante blu di correzione: carica la foto della schedina e l'IA fa il resto.",
    single: "Picks singola partita IA", smart: "Vedi Smart Picks", smartCta: "Parla con l'IA", master: "Master", settled: "Regolati", stats: "Statistiche" },
  ar: { info: "قد يخطئ الذكاء الاصطناعي أحيانًا — الوقت أو النسبة أو السوق. لذلك يوجد زر التصحيح الأزرق أعلى كل توقع: انشر صورة قسيمتك وسيتولى الذكاء الاصطناعي الباقي.",
    single: "توقعات مباراة واحدة", smart: "عرض Smart Picks", smartCta: "تحدث مع الذكاء الاصطناعي", master: "ماستر", settled: "مُسوّاة", stats: "إحصائيات" },
  tr: { info: "Yapay zeka bazen hata yapar — saat, oran veya pazar yanlış olabilir. Bu yüzden her tahminin üstünde mavi düzeltme butonu var: kuponunun fotoğrafını yükle, yapay zeka devralsın.",
    single: "YZ Tek Maç Tahminleri", smart: "Smart Picks'e bak", smartCta: "YZ ile konuş", master: "Master", settled: "Sonuçlanan", stats: "İstatistikler" },
};

export default function Raster3_AiPicks({ lang = "de", counts = {}, newCounts = {}, onViewTips, onViewSmart, onViewMaster, onViewSettled, onViewScorers }) {
  const t = T[lang] || T.de;
  const rtl = lang === "ar";
  const pills = [
    { id: "single", label: t.single, icon: Sparkles, badge: counts.ai, nb: newCounts.ai, cls: "bg-[#2ECC57] text-black", onClick: onViewTips, tid: "r3-single" },
    { id: "smart", label: t.smart, icon: Brain, badge: counts.smart, nb: newCounts.smart, cls: "bg-[#2ECC57] text-black", onClick: onViewSmart, tid: "r3-smart", chip: t.smartCta },
    { id: "master", label: t.master, icon: Crown, badge: counts.master, nb: newCounts.master, cls: "bg-[#E11D2A] text-white", onClick: onViewMaster, tid: "r3-master" },
    { id: "settled", label: t.settled, icon: Flag, badge: counts.settled, nb: newCounts.settled, cls: "bg-white text-black", onClick: onViewSettled, tid: "r3-settled" },
    { id: "stats", label: t.stats, icon: Target, cls: "bg-[#F9A8D4] text-black", onClick: onViewScorers, tid: "r3-stats" },
  ];
  return (
    <section className="px-4 py-4" dir={rtl ? "rtl" : "ltr"} data-testid="raster3-ai-picks">
      <div className="max-w-5xl mx-auto rounded-2xl border border-sky-400/40 bg-gradient-to-b from-sky-400/10 to-transparent p-4">
        <p className="text-xs text-sky-100/80 leading-relaxed mb-3">{t.info}</p>
        <div className="grid grid-cols-2 gap-2">
          {pills.map((p) => {
            const Icon = p.icon;
            return (
              <button key={p.id} onClick={p.onClick} data-testid={p.tid}
                className={`relative flex items-center gap-2 rounded-full font-heading font-black text-xs sm:text-sm px-3 py-2.5 active:scale-[0.98] transition-transform ${p.cls}`}>
                {p.nb > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 z-10 min-w-[18px] h-4.5 px-1 flex items-center justify-center rounded-full bg-red-600 text-white text-[10px] font-black border-2 border-void animate-pulse">
                    {p.nb > 99 ? "99+" : p.nb}
                  </span>
                )}
                <Icon size={15} strokeWidth={2.5} />
                <span className="truncate">{p.label}</span>
                {p.badge != null && (
                  <span className="min-w-[18px] text-center text-[10px] font-mono font-black rounded-full bg-black/25 px-1.5 py-0.5">{p.badge}</span>
                )}
                {p.chip && (
                  <span className="ml-auto shrink-0 hidden sm:inline text-[9px] font-bold rounded-full bg-void/80 text-volt border border-volt/50 px-2 py-0.5">{p.chip}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
