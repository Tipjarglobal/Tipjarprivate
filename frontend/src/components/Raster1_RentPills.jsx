import React from "react";
import { Crown, Instagram } from "lucide-react";
import SponsorFeeder from "./SponsorFeeder";

// RASTER 1 — Top Partner: Intro + 2 Rent-Templates (bleiben IMMER) + Wettanbieter-Pillen.
const IG = "https://instagram.com/tipjarglobal";
const T = {
  de: { intro: "Deine Partner auf TipJar – buche deine eigene Pille für deinen Link oder entdecke unsere Top-Wettanbieter. Jede Pille ist ein direkter Link – deine Sichtbarkeit, dein Business.", rent2: "2× DEIN LINK HIER", rent1: "DEIN LINK HIER", top: "TOP", per: "/Monat", book: "Jetzt buchen → Instagram" },
  en: { intro: "Your partners on TipJar – book your own pill for your link or discover our top bookmakers. Every pill is a direct link – your visibility, your business.", rent2: "2× YOUR LINK HERE", rent1: "YOUR LINK HERE", top: "TOP", per: "/month", book: "Book now → Instagram" },
  es: { intro: "Tus socios en TipJar: reserva tu propia píldora para tu enlace o descubre nuestras mejores casas. Cada píldora es un enlace directo: tu visibilidad, tu negocio.", rent2: "2× TU ENLACE AQUÍ", rent1: "TU ENLACE AQUÍ", top: "TOP", per: "/mes", book: "Reservar → Instagram" },
  el: { intro: "Οι συνεργάτες σου στο TipJar – κλείσε το δικό σου pill για το link σου ή ανακάλυψε κορυφαία στοιχηματικά. Κάθε pill είναι άμεσος σύνδεσμος.", rent2: "2× ΤΟ LINK ΣΟΥ", rent1: "ΤΟ LINK ΣΟΥ", top: "TOP", per: "/μήνα", book: "Κράτηση → Instagram" },
  fr: { intro: "Tes partenaires sur TipJar – réserve ta propre pilule pour ton lien ou découvre nos meilleurs bookmakers. Chaque pilule est un lien direct.", rent2: "2× TON LIEN ICI", rent1: "TON LIEN ICI", top: "TOP", per: "/mois", book: "Réserver → Instagram" },
  it: { intro: "I tuoi partner su TipJar – prenota la tua pillola per il tuo link o scopri i migliori bookmaker. Ogni pillola è un link diretto.", rent2: "2× IL TUO LINK QUI", rent1: "IL TUO LINK QUI", top: "TOP", per: "/mese", book: "Prenota → Instagram" },
  ar: { intro: "شركاؤك على TipJar – احجز حبتك الخاصة لرابطك أو اكتشف أفضل المراهنات. كل حبة رابط مباشر.", rent2: "2× رابطك هنا", rent1: "رابطك هنا", top: "TOP", per: "/شهر", book: "احجز الآن → Instagram" },
  tr: { intro: "TipJar'daki ortakların – kendi hapını linkin için kirala ya da en iyi bahis sitelerini keşfet. Her hap doğrudan bir link.", rent2: "2× LİNKİN BURADA", rent1: "LİNKİN BURADA", top: "TOP", per: "/ay", book: "Hemen kirala → Instagram" },
};

export default function Raster1_RentPills({ lang = "de", ...rest }) {
  const t = T[lang] || T.de;
  const open = () => window.open(IG, "_blank");
  return (
    <section className="px-4 py-4" dir={lang === "ar" ? "rtl" : "ltr"} data-testid="raster1-top-partner">
      <div className="max-w-5xl mx-auto">
        <p className="text-xs text-zinc-400 mb-3 leading-relaxed">{t.intro}</p>
        <div className="grid grid-cols-1 gap-3 mb-3">
          <button onClick={open} data-testid="rent2-template"
            className="relative w-full rounded-2xl border-2 border-volt bg-surface hover:bg-elevated transition-colors px-4 py-5 text-center">
            <span className="absolute top-2 left-3 inline-flex items-center gap-1 bg-volt text-black text-[9px] font-black px-2 py-0.5 rounded-full"><Crown size={11} /> {t.top}</span>
            <span className="block text-base font-black text-white">{t.rent2}</span>
            <span className="block text-volt font-black text-sm mt-1">300€ {t.per}</span>
            <span className="block text-[11px] text-zinc-400 mt-1 inline-flex items-center gap-1 justify-center"><Instagram size={12} /> {t.book}</span>
          </button>
          <button onClick={open} data-testid="rent1-template"
            className="w-full rounded-2xl border border-elevated bg-surface hover:border-volt/50 transition-colors px-4 py-4 text-center">
            <span className="block text-sm font-black text-white">{t.rent1}</span>
            <span className="block text-volt font-black text-sm mt-1">150€ {t.per}</span>
            <span className="block text-[11px] text-zinc-400 mt-1 inline-flex items-center gap-1 justify-center"><Instagram size={12} /> {t.book}</span>
          </button>
        </div>
      </div>
      {/* Wettanbieter-Pillen (bestehender Feeder, Klick-Tracking bleibt) */}
      <SponsorFeeder {...rest} />
    </section>
  );
}
