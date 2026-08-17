import React from "react";
import { Sparkles, Coins, Crown, Boxes, Users } from "lucide-react";
import CoinBattery from "./CoinBattery";

// RASTER 4 — "Willst du mit Wetten Geld verdienen?" + Batterie + 4 Actions.
const T = {
  de: { lead: "Willst du mit Wetten Geld verdienen? Dann brauchst du diese Seite. Melde dich an, aktiviere deinen Standort, wähle deine Sprache und schalte bei den Benachrichtigungen den Master an – so verpasst du keinen einzigen Pick. Dann spiele einfach, was der Master dir gibt, immer mit kontrolliertem Einsatz. So wird aus Wetten ein System statt Glücksspiel.",
    submit: "Tipp einwerfen", earn: "Münzen verdienen", collection: "Meine Sammlung", community: "Community Picks ansehen", live: "Live" },
  en: { lead: "Want to make money betting? Then you need this page. Sign up, enable your location, pick your language and turn on the Master in notifications — so you never miss a single pick. Then just play what the Master gives you, always with a controlled stake. That turns betting into a system instead of gambling.",
    submit: "Drop a tip", earn: "Earn coins", collection: "My Collection", community: "See Community Picks", live: "Live" },
  es: { lead: "¿Quieres ganar dinero apostando? Entonces necesitas esta página. Regístrate, activa tu ubicación, elige tu idioma y activa el Master en las notificaciones — así no te pierdes ningún pick. Luego juega lo que el Master te da, siempre con apuesta controlada.",
    submit: "Lanzar pronóstico", earn: "Ganar monedas", collection: "Mi colección", community: "Ver Community Picks", live: "Live" },
  el: { lead: "Θέλεις να βγάλεις χρήματα με στοιχήματα; Τότε χρειάζεσαι αυτή τη σελίδα. Κάνε εγγραφή, ενεργοποίησε την τοποθεσία, διάλεξε γλώσσα και άναψε τον Master στις ειδοποιήσεις — για να μη χάνεις κανένα pick.",
    submit: "Ρίξε tip", earn: "Κέρδισε νομίσματα", collection: "Η συλλογή μου", community: "Δες Community Picks", live: "Live" },
  fr: { lead: "Tu veux gagner de l'argent en pariant ? Alors il te faut cette page. Inscris-toi, active ta localisation, choisis ta langue et active le Master dans les notifications — pour ne rater aucun pronostic.",
    submit: "Déposer un prono", earn: "Gagner des pièces", collection: "Ma collection", community: "Voir Community Picks", live: "Live" },
  it: { lead: "Vuoi guadagnare con le scommesse? Allora ti serve questa pagina. Registrati, attiva la posizione, scegli la lingua e accendi il Master nelle notifiche — così non perdi nessun pick.",
    submit: "Butta un tip", earn: "Guadagna monete", collection: "La mia raccolta", community: "Vedi Community Picks", live: "Live" },
  ar: { lead: "هل تريد كسب المال من الرهانات؟ إذًا تحتاج هذه الصفحة. سجّل، فعّل موقعك، اختر لغتك وشغّل الماستر في الإشعارات — كي لا تفوّت أي توقع.",
    submit: "ألقِ توقعًا", earn: "اكسب عملات", collection: "مجموعتي", community: "عرض Community Picks", live: "مباشر" },
  tr: { lead: "Bahisle para kazanmak mı istiyorsun? O zaman bu sayfa şart. Kayıt ol, konumunu aç, dilini seç ve bildirimlerde Master'ı aç — hiçbir tahmini kaçırma.",
    submit: "Tahmin at", earn: "Jeton kazan", collection: "Koleksiyonum", community: "Community Picks'e bak", live: "Canlı" },
};

export default function Raster4_Money({ lang = "de", batteryCoins = 0, onSubmit, onEarn, onCollection, onViewMembers, onViewLiveCommunity }) {
  const t = T[lang] || T.de;
  const rtl = lang === "ar";
  return (
    <section className="px-4 py-4" dir={rtl ? "rtl" : "ltr"} data-testid="raster4-money">
      <div className="max-w-5xl mx-auto rounded-2xl border border-elevated bg-surface p-5">
        <div className="flex items-start gap-2.5 mb-5">
          <Crown size={18} className="text-[#E11D2A] shrink-0 mt-0.5" />
          <p className="text-sm text-zinc-300 leading-relaxed">{t.lead}</p>
        </div>

        <CoinBattery current={batteryCoins} max={2500} />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
          <button onClick={onSubmit} data-testid="r4-submit-btn"
            className="flex items-center justify-center gap-2 rounded-full bg-volt text-void font-bold px-6 py-3.5 hover:bg-volt-hover active:scale-95 transition-all shadow-[0_0_30px_rgba(225,255,0,0.3)]">
            <Sparkles size={18} /> {t.submit}
          </button>
          <button onClick={onEarn} data-testid="r4-earn-btn"
            className="flex items-center justify-center gap-2 rounded-full border border-volt/40 bg-volt/10 text-volt font-bold px-6 py-3.5 hover:bg-volt/20 active:scale-95 transition-all">
            <Coins size={18} /> {t.earn}
          </button>
          <button onClick={onCollection} data-testid="r4-collection-btn"
            className="flex items-center justify-center gap-2 rounded-full border border-white/20 bg-white/5 text-white font-bold px-6 py-3.5 hover:bg-white/10 hover:border-white/40 active:scale-95 transition-all">
            <Boxes size={18} /> {t.collection}
          </button>
          {/* Community Picks ansehen — GELB, mit LIVE-Button (aus Raster 4b hierher) */}
          <div className="flex items-center justify-between gap-1 rounded-full bg-[#E3A81B] text-black font-bold p-1" data-testid="r4-community-wrap">
            <button onClick={onViewMembers} data-testid="r4-community-btn"
              className="flex items-center gap-2 min-w-0 flex-1 justify-center pl-2 py-2.5 rounded-full active:scale-[0.98] transition-transform">
              <Users size={17} strokeWidth={2.5} />
              <span className="truncate text-sm">{t.community}</span>
            </button>
            <button onClick={onViewLiveCommunity} data-testid="r4-community-live"
              className="flex items-center gap-1.5 shrink-0 rounded-full bg-[#2563eb] text-white px-3 py-2 text-xs font-black uppercase tracking-wide hover:bg-[#1d4fd8] active:scale-95 transition-all">
              <span className="w-2 h-2 rounded-full bg-white animate-pulse" /> {t.live}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
