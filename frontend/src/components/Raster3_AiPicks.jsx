import React from "react";
import { Sparkles, Brain, Crown, Flag, Target, Wifi, Info } from "lucide-react";

// RASTER 3 — KI-Pillen: Info-Raster (ⓘ) + Pillen. Live KI Picks jetzt hier (neben Abgerechnet).
const T = {
  de: { info: "Die KI macht manchmal Fehler. Manchmal stimmen Uhrzeit, Quote oder Markt nicht (z.B. gibt es bei manchen Spielen kein Über 0.5). Dafür gibt es oben bei jedem Tipp den blauen Korrektur-Knopf: Poste einfach ein Foto deines Scheins vom Buchmacher, dann übernimmt die KI die richtige Auswahl und Quote automatisch. So bleibt jeder Schein sauber und spielbar.",
    single: "KI Single-Game-Picks", smart: "Smart Picks ansehen", smartCta: "Mit der KI reden", master: "Master", settled: "Abgerechnet", stats: "Statistiken", live: "Live KI Picks" },
  en: { info: "The AI sometimes makes mistakes — kickoff time, odds or market may be off (e.g. no Over 0.5 for some games). That's why every tip has the blue correction button on top: post a photo of your bookmaker slip and the AI takes the right selection and odds automatically. Every slip stays clean and playable.",
    single: "AI Single-Game Picks", smart: "See Smart Picks", smartCta: "Talk to the AI", master: "Master", settled: "Settled", stats: "Statistics", live: "Live AI Picks" },
  es: { info: "La IA a veces se equivoca: la hora, la cuota o el mercado pueden fallar. Por eso cada pronóstico tiene el botón azul de corrección arriba: sube una foto de tu boleto y la IA se encarga de la selección y cuota correctas.",
    single: "Picks de un partido IA", smart: "Ver Smart Picks", smartCta: "Habla con la IA", master: "Master", settled: "Liquidado", stats: "Estadísticas", live: "Live AI Picks" },
  el: { info: "Η ΤΝ κάνει μερικές φορές λάθη — ώρα, απόδοση ή αγορά. Γι' αυτό κάθε tip έχει πάνω το μπλε κουμπί διόρθωσης: ανέβασε φωτό του δελτίου και η ΤΝ αναλαμβάνει σωστή επιλογή και απόδοση.",
    single: "KI Single-Game Picks", smart: "Δες Smart Picks", smartCta: "Μίλα με την ΤΝ", master: "Master", settled: "Εκκαθαρισμένα", stats: "Στατιστικά", live: "Live KI Picks" },
  fr: { info: "L'IA se trompe parfois — l'heure, la cote ou le marché. C'est pourquoi chaque pronostic a le bouton bleu de correction en haut : poste une photo de ton ticket et l'IA prend la bonne sélection et cote.",
    single: "Picks un match IA", smart: "Voir Smart Picks", smartCta: "Parler à l'IA", master: "Master", settled: "Réglé", stats: "Statistiques", live: "Live AI Picks" },
  it: { info: "L'IA a volte sbaglia — orario, quota o mercato. Per questo ogni tip ha in alto il pulsante blu di correzione: carica la foto della schedina e l'IA sistema selezione e quota.",
    single: "Picks singola partita IA", smart: "Vedi Smart Picks", smartCta: "Parla con l'IA", master: "Master", settled: "Regolati", stats: "Statistiche", live: "Live AI Picks" },
  ar: { info: "قد يخطئ الذكاء الاصطناعي أحيانًا — الوقت أو النسبة أو السوق. لذلك يوجد زر التصحيح الأزرق أعلى كل توقع: انشر صورة قسيمتك وسيتولى الذكاء الاصطناعي الاختيار والنسبة الصحيحة.",
    single: "توقعات مباراة واحدة", smart: "عرض Smart Picks", smartCta: "تحدث مع الذكاء الاصطناعي", master: "ماستر", settled: "مُسوّاة", stats: "إحصائيات", live: "Live AI Picks" },
  tr: { info: "Yapay zeka bazen hata yapar — saat, oran veya pazar. Bu yüzden her tahminin üstünde mavi düzeltme butonu var: kuponunun fotoğrafını yükle, yapay zeka doğru seçim ve oranı alsın.",
    single: "YZ Tek Maç Tahminleri", smart: "Smart Picks'e bak", smartCta: "YZ ile konuş", master: "Master", settled: "Sonuçlanan", stats: "İstatistikler", live: "Canlı YZ Picks" },
};

function Pill({ label, icon: Icon, badge, nb, cls, onClick, tid, chip, live, span }) {
  return (
    <button onClick={onClick} data-testid={tid}
      className={`relative flex items-center gap-2 rounded-full font-heading font-black text-xs sm:text-sm px-3 py-2.5 active:scale-[0.98] transition-transform ${cls} ${span ? "col-span-2" : ""} ${live ? "animate-pulse" : ""}`}>
      {nb > 0 && (
        <span className="absolute -top-1.5 -right-1.5 z-10 min-w-[18px] h-4.5 px-1 flex items-center justify-center rounded-full bg-red-600 text-white text-[10px] font-black border-2 border-void animate-pulse">
          {nb > 99 ? "99+" : nb}
        </span>
      )}
      <Icon size={15} strokeWidth={2.5} />
      <span className="truncate">{label}</span>
      {badge != null && (
        <span className="min-w-[18px] text-center text-[10px] font-mono font-black rounded-full bg-black/25 px-1.5 py-0.5">{badge}</span>
      )}
      {chip && (
        <span className="ml-auto shrink-0 hidden sm:inline text-[9px] font-bold rounded-full bg-void/80 text-volt border border-volt/50 px-2 py-0.5">{chip}</span>
      )}
    </button>
  );
}

export default function Raster3_AiPicks({ lang = "de", counts = {}, newCounts = {}, onViewTips, onViewSmart, onViewMaster, onViewSettled, onViewScorers, onViewLive }) {
  const t = T[lang] || T.de;
  const rtl = lang === "ar";
  return (
    <section className="px-4 py-4" dir={rtl ? "rtl" : "ltr"} data-testid="raster3-ai-picks">
      <div className="max-w-5xl mx-auto rounded-2xl border border-sky-400/40 bg-gradient-to-b from-sky-400/10 to-transparent p-4">
        <div className="flex items-start gap-2 mb-3">
          <Info size={16} className="text-sky-300 shrink-0 mt-0.5" />
          <p className="text-xs text-sky-100/80 leading-relaxed">{t.info}</p>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {/* Zeile 1 */}
          <Pill label={t.single} icon={Sparkles} badge={counts.ai} nb={newCounts.ai} cls="bg-[#2ECC57] text-black" onClick={onViewTips} tid="r3-single" />
          <Pill label={t.smart} icon={Brain} badge={counts.smart} nb={newCounts.smart} cls="bg-[#2ECC57] text-black" onClick={onViewSmart} tid="r3-smart" chip={t.smartCta} />
          {/* Zeile 2 */}
          <Pill label={t.master} icon={Crown} badge={counts.master} nb={newCounts.master} cls="bg-[#E11D2A] text-white" onClick={onViewMaster} tid="r3-master" span />
          {/* Zeile 3: Abgerechnet + Live nebeneinander */}
          <Pill label={t.settled} icon={Flag} badge={counts.settled} nb={newCounts.settled} cls="bg-white text-black" onClick={onViewSettled} tid="r3-settled" />
          <Pill label={t.live} icon={Wifi} badge={counts.live} nb={newCounts.live} cls="bg-[#2563eb] text-white" onClick={onViewLive} tid="r3-live" live />
          {/* Zeile 4: Statistiken full width */}
          <Pill label={t.stats} icon={Target} cls="bg-[#F9A8D4] text-black" onClick={onViewScorers} tid="r3-stats" span />
        </div>
      </div>
    </section>
  );
}
