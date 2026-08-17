import React from "react";
import { Crown, Instagram } from "lucide-react";

// RASTER 2 — Supporter: 5 Blank-Templates (bleiben IMMER), teuerste oben.
const IG = "https://instagram.com/tipjarglobal";
const T = {
  de: { intro: "Supporte TipJar – werde Teil der Community. Jede Pille hilft TipJar zu wachsen. Deine Pille erscheint sofort nach dem Kauf.", wk: "Wochen", coins: "Münzen", book: "Buchen → Instagram", best: "BESTSELLER" },
  en: { intro: "Support TipJar – become part of the community. Every pill helps TipJar grow. Your pill appears right after purchase.", wk: "weeks", coins: "coins", book: "Book → Instagram", best: "BESTSELLER" },
  es: { intro: "Apoya a TipJar y únete a la comunidad. Cada píldora ayuda a crecer. Tu píldora aparece justo tras la compra.", wk: "semanas", coins: "monedas", book: "Reservar → Instagram", best: "MÁS VENDIDO" },
  el: { intro: "Στήριξε το TipJar – γίνε μέλος της κοινότητας. Κάθε pill βοηθά να μεγαλώσει. Εμφανίζεται αμέσως μετά την αγορά.", wk: "εβδομάδες", coins: "νομίσματα", book: "Κράτηση → Instagram", best: "BESTSELLER" },
  fr: { intro: "Soutiens TipJar – rejoins la communauté. Chaque pilule aide TipJar à grandir. Ta pilule apparaît juste après l'achat.", wk: "semaines", coins: "pièces", book: "Réserver → Instagram", best: "BEST-SELLER" },
  it: { intro: "Sostieni TipJar – entra nella community. Ogni pillola aiuta a crescere. Appare subito dopo l'acquisto.", wk: "settimane", coins: "monete", book: "Prenota → Instagram", best: "PIÙ VENDUTO" },
  ar: { intro: "ادعم TipJar وكن جزءًا من المجتمع. كل حبة تساعد على النمو. تظهر حبتك فور الشراء.", wk: "أسابيع", coins: "عملات", book: "احجز → Instagram", best: "الأكثر مبيعًا" },
  tr: { intro: "TipJar'ı destekle – topluluğun parçası ol. Her hap büyümeye yardım eder. Hapın satın alımdan hemen sonra görünür.", wk: "hafta", coins: "jeton", book: "Kirala → Instagram", best: "ÇOK SATAN" },
};
const PILLS = [
  { id: "xxl", title: "TipJar PARTNER", price: "119,99€", weeks: 6, coins: 1600, badge: "PARTNER", crown: true, size: "text-base" },
  { id: "xl", title: "TipJar SPONSOR", price: "79,99€", weeks: 5, coins: 950, badge: "SPONSOR", size: "text-base" },
  { id: "l", title: "TipJar VIP", price: "49,99€", weeks: 4, coins: 460, best: true, size: "text-sm" },
  { id: "m", title: "TipJar Fan", price: "19,99€", weeks: 3, coins: 150, size: "text-sm" },
  { id: "s", title: "TipJar Supporter", price: "9,99€", weeks: 2, coins: 50, size: "text-sm" },
];

export default function Raster2_Supporter({ lang = "de" }) {
  const t = T[lang] || T.de;
  const open = () => window.open(IG, "_blank");
  return (
    <section className="px-4 py-4" dir={lang === "ar" ? "rtl" : "ltr"} data-testid="raster2-supporter">
      <div className="max-w-5xl mx-auto">
        <p className="text-xs text-zinc-400 mb-3 leading-relaxed">{t.intro}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {PILLS.map((p) => (
            <button key={p.id} onClick={open} data-testid={`supporter-${p.id}`}
              className={`relative w-full rounded-2xl border ${p.best ? "border-volt" : "border-elevated"} bg-surface hover:border-volt/50 transition-colors px-4 py-4 text-left ${p.id === "xxl" ? "sm:col-span-2" : ""}`}>
              {p.best && <span className="absolute -top-2 left-3 bg-volt text-black text-[9px] font-black px-2 py-0.5 rounded-full">{t.best}</span>}
              {p.badge && <span className="absolute top-2 right-3 inline-flex items-center gap-1 text-[9px] font-black text-volt">{p.crown && <Crown size={11} />} {p.badge}</span>}
              <span className={`block font-black text-white ${p.size}`}>{p.title}</span>
              <span className="block text-volt font-black text-sm mt-1">{p.price} · {p.weeks} {t.wk}</span>
              <span className="block text-[11px] text-zinc-400">{p.coins} {t.coins}</span>
              <span className="block text-[11px] text-zinc-400 mt-1 inline-flex items-center gap-1"><Instagram size={12} /> {t.book}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
