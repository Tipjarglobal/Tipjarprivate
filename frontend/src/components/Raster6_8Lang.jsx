import React, { useState, useEffect } from "react";
import { Zap, Gift, MousePointerClick, BatteryCharging } from "lucide-react";
import api from "../api";

// 8 SPRACHEN - RASTER 6
const TRANSLATIONS = {
  de: {
    title: "Sich gegenseitig beschenken",
    shortTitle: "Sich gegenseitig beschenken – Die Batterie lädt durch euch",
    subtext: "Die TipJar Batterie ist das Herz. Klicke sie an und feede Credits rein, wenn du welche hast. Auszahlung erst ab 2000+ in der Batterie. Egal ob du einen anderen Tipper beschenkst oder direkt die Batterie – die Batterie bekommt immer Energie dazu. Mehr Energie wenn du direkt die Batterie beschenkst. So wächst TipJar, so wächst deine Auszahlung. Schenken = Energie = Cash.",
    battery: "Batterie",
    feedBtn: "Credits feeden",
    tapHint: "Tippen zum Aufladen",
    giftBtn: "Spendieren",
    empty: "Noch keine Spenden – sei der Erste!",
    coins: "COINS",
    voll: "VOLL",
    neverBelow: "NIEMALS UNTER",
    payoutFrom: "Auszahlung ab",
    tabs: { week: "Diese Woche", all: "Gesamter Zeitraum", received: "Erhalten", gifted: "Verschenkt" }
  },
  en: {
    title: "Gift Each Other",
    shortTitle: "Gift Each Other – The Battery Charges Through You",
    subtext: "The TipJar Battery is the heart. Click it and feed Credits if you have some. Payout only from 2000+ in the Battery. Whether you gift another tipper or directly the Battery – the Battery always gets energy. More energy if you gift directly to the Battery. This is how TipJar grows, this is how your payout grows. Gifting = Energy = Cash.",
    battery: "Battery",
    feedBtn: "Feed Credits",
    tapHint: "Tap to charge",
    giftBtn: "Gift a tipster",
    empty: "No gifts yet – be the first!",
    coins: "COINS",
    voll: "FULL",
    neverBelow: "NEVER BELOW",
    payoutFrom: "Payout from",
    tabs: { week: "This Week", all: "All Time", received: "Received", gifted: "Gifted" }
  },
  es: {
    title: "Regálense entre sí",
    shortTitle: "Regálense entre sí – La Batería se carga por ustedes",
    subtext: "La Batería TipJar es el corazón. Haz clic y alimenta Créditos si tienes. Pago solo desde 2000+ en la Batería. Ya sea que regales a otro tipster o directo a la Batería – la Batería siempre recibe energía. Más energía si regalas directo a la Batería. Así crece TipJar, así crece tu pago. Regalar = Energía = Dinero.",
    battery: "Batería",
    feedBtn: "Alimentar Créditos",
    tapHint: "Toca para cargar",
    giftBtn: "Regalar a un tipster",
    empty: "Aún sin regalos – ¡sé el primero!",
    coins: "COINS",
    voll: "LLENO",
    neverBelow: "NUNCA DEBAJO",
    payoutFrom: "Pago desde",
    tabs: { week: "Esta Semana", all: "Todo el tiempo", received: "Recibido", gifted: "Regalado" }
  },
  el: {
    title: "Χαρίστε ο ένας στον άλλον",
    shortTitle: "Χαρίστε ο ένας στον άλλον – Η Μπαταρία φορτίζει από εσάς",
    subtext: "Η Μπαταρία TipJar είναι η καρδιά. Κάνε κλικ και τάισε Credits αν έχεις. Πληρωμή μόνο από 2000+ στη Μπαταρία. Είτε χαρίζεις σε άλλον tipster είτε απευθείας στη Μπαταρία – η Μπαταρία παίρνει πάντα ενέργεια. Περισσότερη ενέργεια αν χαρίσεις απευθείας στη Μπαταρία. Έτσι μεγαλώνει το TipJar, έτσι μεγαλώνει η πληρωμή σου.",
    battery: "Μπαταρία",
    feedBtn: "Τάισε Credits",
    tapHint: "Πάτησε για φόρτιση",
    giftBtn: "Δώρισε σε tipster",
    empty: "Καμία δωρεά ακόμα – γίνε ο πρώτος!",
    coins: "COINS",
    voll: "ΓΕΜΑΤΟ",
    neverBelow: "ΠΟΤΕ ΚΑΤΩ",
    payoutFrom: "Πληρωμή από",
    tabs: { week: "Αυτή την Εβδομάδα", all: "Όλος ο χρόνος", received: "Ληφθέντα", gifted: "Δωρισμένα" }
  },
  fr: {
    title: "Offrez-vous des cadeaux",
    shortTitle: "Offrez-vous des cadeaux – La Batterie se charge grâce à vous",
    subtext: "La Batterie TipJar est le cœur. Clique dessus et feed des Crédits si tu en as. Paiement seulement à partir de 2000+ dans la Batterie. Que tu offres à un autre tippeur ou directement à la Batterie – la Batterie reçoit toujours de l'énergie. Plus d'énergie si tu offres directement à la Batterie. C'est ainsi que TipJar grandit, c'est ainsi que ton paiement grandit.",
    battery: "Batterie",
    feedBtn: "Nourrir Crédits",
    tapHint: "Touche pour charger",
    giftBtn: "Offrir à un tippeur",
    empty: "Aucun cadeau encore – sois le premier !",
    coins: "COINS",
    voll: "PLEIN",
    neverBelow: "JAMAIS EN DESSOUS",
    payoutFrom: "Paiement dès",
    tabs: { week: "Cette Semaine", all: "Tout le temps", received: "Reçu", gifted: "Offert" }
  },
  it: {
    title: "Regalatevi a vicenda",
    shortTitle: "Regalatevi a vicenda – La Batteria si carica grazie a voi",
    subtext: "La Batteria TipJar è il cuore. Cliccala e alimenta Crediti se ne hai. Pagamento solo da 2000+ nella Batteria. Che tu regali a un altro tipster o direttamente alla Batteria – la Batteria riceve sempre energia. Più energia se regali direttamente alla Batteria. Così cresce TipJar, così cresce il tuo pagamento.",
    battery: "Batteria",
    feedBtn: "Alimenta Crediti",
    tapHint: "Tocca per caricare",
    giftBtn: "Regala a un tipster",
    empty: "Ancora nessun regalo – sii il primo!",
    coins: "COINS",
    voll: "PIENO",
    neverBelow: "MAI SOTTO",
    payoutFrom: "Pagamento da",
    tabs: { week: "Questa Settimana", all: "Sempre", received: "Ricevuto", gifted: "Regalato" }
  },
  ar: {
    title: "أهدوا بعضكم بعضاً",
    shortTitle: "أهدوا بعضكم – البطارية تشحن بكم",
    subtext: "بطارية TipJar هي القلب. انقر عليها وأطعمها Credits إذا كان لديك. الدفع فقط من 2000+ في البطارية. سواء أهديت مراهنًا آخر أو البطارية مباشرة – البطارية تحصل دائمًا على طاقة. طاقة أكثر إذا أهديت مباشرة للبطارية. هكذا ينمو TipJar، هكذا ينمو دفعك.",
    battery: "البطارية",
    feedBtn: "إطعام Credits",
    tapHint: "انقر للشحن",
    giftBtn: "أهدِ لمراهن",
    empty: "لا هدايا بعد – كن الأول!",
    coins: "عملات",
    voll: "ممتلئ",
    neverBelow: "أبداً تحت",
    payoutFrom: "الدفع من",
    tabs: { week: "هذا الأسبوع", all: "كل الوقت", received: "المستلم", gifted: "المهدى" }
  },
  tr: {
    title: "Birbirinize Hediye Edin",
    shortTitle: "Birbirinize Hediye Edin – Batarya sizinle şarj olur",
    subtext: "TipJar Bataryası kalptir. Tıkla ve Kredin varsa besle. Ödeme sadece Bataryada 2000+ olduğunda. İster başka bir bahisçiye hediye et ister doğrudan Bataryaya – Batarya her zaman enerji alır. Doğrudan Bataryaya hediye edersen daha fazla enerji. TipJar böyle büyür, ödemen böyle büyür.",
    battery: "Batarya",
    feedBtn: "Kredi Besle",
    tapHint: "Şarj için dokun",
    giftBtn: "Bir bahisçiye hediye et",
    empty: "Henüz hediye yok – ilk sen ol!",
    coins: "COINS",
    voll: "DOLU",
    neverBelow: "ASLA ALTINDA DEĞİL",
    payoutFrom: "Ödeme",
    tabs: { week: "Bu Hafta", all: "Tüm Zamanlar", received: "Alınan", gifted: "Hediye Edilen" }
  }
};

// RASTER 6 COMPONENT
export default function Raster6_Battery_Gifting({ lang = "de", batteryCoins = 125, onFeedClick, onGiftClick }) {
  const t = TRANSLATIONS[lang] || TRANSLATIONS.de;
  const [activeTab, setActiveTab] = useState("week");
  const [boards, setBoards] = useState({ week: [], all: [], received: [], gifted: [] });
  const rtl = lang === "ar";

  useEffect(() => {
    let on = true;
    api.get("/gifting/leaderboards")
      .then((r) => { if (on && r.data) setBoards(r.data); })
      .catch(() => {});
    const onBoost = () => {
      api.get("/gifting/leaderboards").then((r) => { if (on && r.data) setBoards(r.data); }).catch(() => {});
    };
    window.addEventListener("tipjar-boost", onBoost);
    window.addEventListener("tipjar-boost-gold", onBoost);
    return () => { on = false; window.removeEventListener("tipjar-boost", onBoost); window.removeEventListener("tipjar-boost-gold", onBoost); };
  }, []);

  const tabs = [
    { id: "week", label: t.tabs.week },
    { id: "all", label: t.tabs.all },
    { id: "received", label: t.tabs.received },
    { id: "gifted", label: t.tabs.gifted },
  ];

  return (
    <div className="w-full rounded-3xl bg-[#111] border border-[#222] p-4 md:p-6" dir={rtl ? "rtl" : "ltr"}>
      {/* TITLE - MUSS ALLES ERKLÄREN */}
      <div className="mb-6">
        <h2 className="text-2xl md:text-3xl font-black text-white">{t.title}</h2>
        <p className="text-sm md:text-base text-[#aaa] mt-2 leading-relaxed">{t.subtext}</p>
        <p className="text-xs text-[#666] mt-2 font-bold">{t.shortTitle}</p>
      </div>

      {/* OBEN - BATTERIE 1 - DEUTLICH ANKLICKBAR */}
      <div className="relative mb-5">
        {/* pulsierender Klick-Hinweis oben rechts */}
        <span data-testid="battery-tap-hint"
          className="absolute -top-3 right-4 z-10 inline-flex items-center gap-1.5 rounded-full bg-[#ff3b3b] text-white text-[11px] font-black px-3 py-1 shadow-[0_0_16px_rgba(255,59,59,0.7)] animate-bounce">
          <MousePointerClick size={13} /> {t.tapHint}
        </span>
        <button
          type="button"
          onClick={onFeedClick}
          data-testid="battery-main-click"
          className="group cursor-pointer w-full text-left rounded-2xl bg-gradient-to-b from-[#1a1a1a] to-[#0a0a0a] border-2 border-[#ff3b3b] p-5 hover:scale-[1.01] hover:shadow-[0_0_28px_rgba(255,59,59,0.35)] active:scale-[0.99] transition-all ring-2 ring-[#ff3b3b]/30 ring-offset-2 ring-offset-[#111]"
        >
          <div className="flex justify-between items-center mb-3 gap-2">
            <span className="text-white font-black text-lg inline-flex items-center gap-2">
              <BatteryCharging size={20} className="text-[#ff3b3b]" /> {t.battery} - {t.coins}
            </span>
            <span className="text-[#ff3b3b] text-[11px] sm:text-xs font-bold text-right">{t.payoutFrom} 2000+ • {t.neverBelow} 125 • {t.voll} 2500</span>
          </div>
          {/* Batterie Visual */}
          <div className="w-full h-10 bg-[#222] rounded-full overflow-hidden border border-[#333] relative">
            <div
              className="h-full bg-gradient-to-r from-[#ff3b3b] to-[#ff0000] transition-all duration-700"
              style={{ width: `${(batteryCoins / 2500) * 100}%` }}
            />
            <div className="absolute inset-0 flex items-center justify-center text-white font-black text-sm">
              {batteryCoins} / 2500 {t.coins}
            </div>
          </div>
        </button>
        {/* 2 klare Aktionen: Batterie feeden + Spendieren */}
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
          <button
            type="button"
            onClick={onFeedClick}
            data-testid="battery-feed-btn"
            className="inline-flex items-center justify-center gap-2 bg-[#ff3b3b] text-white font-black px-6 py-3 rounded-full text-sm hover:brightness-110 active:scale-95 transition-all"
          >
            <Zap size={16} /> {t.feedBtn} {t.battery}
          </button>
          <button
            type="button"
            onClick={onGiftClick}
            data-testid="battery-gift-btn"
            className="inline-flex items-center justify-center gap-2 bg-transparent border border-[#ff3b3b]/60 text-[#ff3b3b] font-black px-6 py-3 rounded-full text-sm hover:bg-[#ff3b3b]/10 active:scale-95 transition-all"
          >
            <Gift size={16} /> {t.giftBtn}
          </button>
        </div>
      </div>

      {/* UNTEN - BATTERIE 2 - CREDIT VERKEHR / LEADERBOARD WIE LOVOO */}
      <div className="w-full rounded-2xl bg-[#1a1a1a] border border-[#333] overflow-hidden">
        {/* Tabs */}
        <div className="flex overflow-x-auto gap-1 p-2 bg-[#0f0f0f] border-b border-[#222]">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap px-4 py-2 rounded-full text-xs font-bold transition-all ${
                activeTab === tab.id
                  ? "bg-white text-black"
                  : "bg-[#222] text-[#888] hover:bg-[#333] hover:text-white"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
        {/* Leaderboard Content — echte Spendier-Daten, keine Platzhalter */}
        <div className="p-4">
          <div className="text-[#666] text-xs font-bold mb-3 uppercase">
            {t.tabs[activeTab]} - Leaderboard
          </div>
          {(boards[activeTab] || []).length === 0 ? (
            <div data-testid="leaderboard-empty" className="text-center text-[#666] text-sm py-8">
              {t.empty}
            </div>
          ) : (
            <div className="space-y-2" data-testid={`leaderboard-${activeTab}`}>
              {(boards[activeTab] || []).map((row, i) => {
                const rank = i + 1;
                const medal = rank === 1 ? "#FFD447" : rank === 2 ? "#C0C0C0" : rank === 3 ? "#CD7F32" : "#ff3b3b";
                return (
                  <div key={`${row.username}-${i}`} className="flex items-center gap-3 bg-[#222] rounded-xl p-3">
                    <div className="w-6 h-6 rounded-full text-black text-xs font-black flex items-center justify-center" style={{ background: medal }}>
                      {rank}
                    </div>
                    <div className="w-8 h-8 rounded-full bg-[#333] flex items-center justify-center text-white text-sm font-black">
                      {(row.username || "?")[0].toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-white text-sm font-bold truncate">{row.username}</div>
                      <div className="text-[#666] text-xs">
                        {row.coins.toLocaleString()} {t.coins} {activeTab === "received" ? t.tabs.received : activeTab === "gifted" ? t.tabs.gifted : ""}
                      </div>
                    </div>
                    <div className="text-[#ff3b3b] font-black text-sm inline-flex items-center gap-1">
                      <Zap size={13} /> {row.coins.toLocaleString()}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// EXPORT FÜR LOCALES JSON - für i18n.js / locales/*.json
export { TRANSLATIONS };
