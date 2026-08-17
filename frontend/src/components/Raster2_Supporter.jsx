import React, { useState } from "react";
import { Crown, Eye, Link2, Image as ImageIcon, X } from "lucide-react";

// RASTER 2 — Supporter: 5 Blank-Templates (bleiben IMMER), teuerste oben.
// Preis oben links (gelb), Badge oben rechts, Münzen darunter. Klick → Purchase-Window.
const T = {
  de: { intro: "Supporte TipJar – werde Teil der Community. Jede Pille hilft TipJar zu wachsen. Deine Pille erscheint sofort nach dem Kauf.", wk: "Wochen", coins: "Münzen", buy: "Jetzt kaufen", getTitle: "Das bekommst du", contact: "Kauf abschließen → Instagram @tipjarglobal", close: "Schließen" },
  en: { intro: "Support TipJar – become part of the community. Every pill helps TipJar grow. Your pill appears right after purchase.", wk: "weeks", coins: "coins", buy: "Buy now", getTitle: "What you get", contact: "Complete purchase → Instagram @tipjarglobal", close: "Close" },
  es: { intro: "Apoya a TipJar y únete a la comunidad. Cada píldora ayuda a crecer. Tu píldora aparece justo tras la compra.", wk: "semanas", coins: "monedas", buy: "Comprar", getTitle: "Esto obtienes", contact: "Completar compra → Instagram @tipjarglobal", close: "Cerrar" },
  el: { intro: "Στήριξε το TipJar – γίνε μέλος της κοινότητας. Κάθε pill βοηθά να μεγαλώσει. Εμφανίζεται αμέσως μετά την αγορά.", wk: "εβδομάδες", coins: "νομίσματα", buy: "Αγορά", getTitle: "Τι παίρνεις", contact: "Ολοκλήρωση → Instagram @tipjarglobal", close: "Κλείσιμο" },
  fr: { intro: "Soutiens TipJar – rejoins la communauté. Chaque pilule aide TipJar à grandir. Ta pilule apparaît juste après l'achat.", wk: "semaines", coins: "pièces", buy: "Acheter", getTitle: "Ce que tu obtiens", contact: "Finaliser → Instagram @tipjarglobal", close: "Fermer" },
  it: { intro: "Sostieni TipJar – entra nella community. Ogni pillola aiuta a crescere. Appare subito dopo l'acquisto.", wk: "settimane", coins: "monete", buy: "Acquista", getTitle: "Cosa ottieni", contact: "Completa → Instagram @tipjarglobal", close: "Chiudi" },
  ar: { intro: "ادعم TipJar وكن جزءًا من المجتمع. كل حبة تساعد على النمو. تظهر حبتك فور الشراء.", wk: "أسابيع", coins: "عملات", buy: "اشترِ الآن", getTitle: "ما ستحصل عليه", contact: "إتمام الشراء → Instagram @tipjarglobal", close: "إغلاق" },
  tr: { intro: "TipJar'ı destekle – topluluğun parçası ol. Her hap büyümeye yardım eder. Hapın satın alımdan hemen sonra görünür.", wk: "hafta", coins: "jeton", buy: "Satın al", getTitle: "Ne alıyorsun", contact: "Tamamla → Instagram @tipjarglobal", close: "Kapat" },
};

// Features je Pille (im Purchase-Window angezeigt)
const FEATURES = {
  de: {
    xxl: ["Wunsch-Link frei wählbar", "3 Bilder hochladen (Admin-Freigabe)", "Name + Mini-OpenCase-Ansicht"],
    xl: ["Wunsch-Link frei wählbar", "2 Bilder hochladen (Admin-Freigabe)", "Name + Mini-OpenCase-Ansicht"],
    l: ["Wunsch-Link frei wählbar", "1 Bild hochladen (Admin-Freigabe)", "Name + Mini-OpenCase-Ansicht"],
    m: ["Nur OpenCases anzeigen", "Name in der Pille"],
    s: ["Nur OpenCases anzeigen", "Name in der Pille"],
  },
  en: {
    xxl: ["Free choice of your link", "Upload 3 images (admin approval)", "Name + mini OpenCase view"],
    xl: ["Free choice of your link", "Upload 2 images (admin approval)", "Name + mini OpenCase view"],
    l: ["Free choice of your link", "Upload 1 image (admin approval)", "Name + mini OpenCase view"],
    m: ["Show OpenCases only", "Name inside the pill"],
    s: ["Show OpenCases only", "Name inside the pill"],
  },
};

const PILLS = [
  { id: "xxl", price: "119,99€", weeks: 6, coins: 1600, badge: "PARTNER", crown: true, size: "xxl", hasLink: true },
  { id: "xl", price: "79,99€", weeks: 5, coins: 950, badge: "SPONSOR", size: "md", hasLink: true },
  { id: "l", price: "49,99€", weeks: 4, coins: 460, badge: "BESTSELLER", best: true, size: "md", hasLink: true },
  { id: "m", price: "19,99€", weeks: 3, coins: 150, size: "sm" },
  { id: "s", price: "9,99€", weeks: 2, coins: 50, size: "sm" },
];

// Höhen: xxl wie 300€-Template, md wie 150€, sm etwas kleiner
const H = { xxl: "py-6", md: "py-5", sm: "py-3.5" };

export default function Raster2_Supporter({ lang = "de" }) {
  const t = T[lang] || T.de;
  const feats = (FEATURES[lang] || FEATURES.en);
  const [sel, setSel] = useState(null);
  const IG = "https://instagram.com/tipjarglobal";

  return (
    <section className="px-4 py-4" dir={lang === "ar" ? "rtl" : "ltr"} data-testid="raster2-supporter">
      <div className="max-w-5xl mx-auto">
        <p className="text-xs text-zinc-400 mb-3 leading-relaxed">{t.intro}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {PILLS.map((p) => (
            <button key={p.id} onClick={() => setSel(p)} data-testid={`supporter-${p.id}`}
              className={`relative w-full rounded-2xl border ${p.best ? "border-volt" : "border-elevated"} bg-surface hover:border-volt/50 transition-colors px-4 ${H[p.size]} text-left ${p.id === "xxl" ? "sm:col-span-2" : ""}`}>
              {/* Top row: Preis links (gelb fett) + Badge rechts (gelb) */}
              <div className="flex items-start justify-between gap-2">
                <span className="text-volt font-black text-lg leading-none">{p.price}<span className="text-zinc-500 font-bold text-[11px]"> / {p.weeks} {t.wk}</span></span>
                {p.badge && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-black text-volt shrink-0">
                    {p.crown && <Crown size={12} />} {p.badge}
                  </span>
                )}
              </div>
              <span className="block text-[11px] text-zinc-400 mt-2">{p.coins} {t.coins}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Purchase-Window */}
      {sel && (
        <div className="fixed inset-0 z-[120] flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          data-testid="supporter-purchase-modal" onClick={() => setSel(null)}>
          <div className="w-full max-w-md rounded-2xl border border-volt/30 bg-[#0d0d0f] p-6 shadow-2xl"
            onClick={(e) => e.stopPropagation()} dir={lang === "ar" ? "rtl" : "ltr"}>
            <div className="flex items-start justify-between gap-3 mb-4">
              <div>
                <div className="inline-flex items-center gap-1 text-[10px] font-black text-volt mb-1">
                  {sel.crown && <Crown size={12} />} {sel.badge || "SUPPORTER"}
                </div>
                <div className="text-volt font-black text-2xl leading-none">{sel.price}</div>
                <div className="text-xs text-zinc-500 mt-1">{sel.weeks} {t.wk} · {sel.coins} {t.coins}</div>
              </div>
              <button onClick={() => setSel(null)} data-testid="supporter-modal-close" className="text-zinc-500 hover:text-white"><X size={20} /></button>
            </div>
            <p className="text-[11px] font-black uppercase tracking-widest text-zinc-500 mb-2">{t.getTitle}</p>
            <ul className="space-y-2 mb-5">
              {(feats[sel.id] || []).map((f, i) => (
                <li key={i} className="flex items-center gap-2 text-sm text-zinc-200">
                  <span className="grid place-items-center w-6 h-6 rounded-lg bg-volt/15 text-volt shrink-0">
                    {i === 0 && sel.hasLink ? <Link2 size={13} /> : (f.toLowerCase().includes("bild") || f.toLowerCase().includes("image")) ? <ImageIcon size={13} /> : <Eye size={13} />}
                  </span>
                  {f}
                </li>
              ))}
            </ul>
            <button data-testid="supporter-buy-btn" onClick={() => window.open(IG, "_blank")}
              className="w-full rounded-full bg-volt text-void font-black py-3 hover:brightness-110 active:scale-95 transition-all">
              {t.contact}
            </button>
            <button onClick={() => setSel(null)} className="w-full text-center text-xs text-zinc-500 mt-3 hover:text-white">{t.close}</button>
          </div>
        </div>
      )}
    </section>
  );
}
