import React, { useState } from "react";

// 8 SPRACHEN - RASTER 6
const TRANSLATIONS = {
  de: {
    title: "Sich gegenseitig beschenken",
    shortTitle: "Sich gegenseitig beschenken – Die Batterie lädt durch euch",
    subtext: "Die TipJar Batterie ist das Herz. Klicke sie an und feede Credits rein, wenn du welche hast. Auszahlung erst ab 2000+ in der Batterie. Egal ob du einen anderen Tipper beschenkst oder direkt die Batterie – die Batterie bekommt immer Energie dazu. Mehr Energie wenn du direkt die Batterie beschenkst. So wächst TipJar, so wächst deine Auszahlung. Schenken = Energie = Cash.",
    battery: "Batterie",
    feedBtn: "Credits feeden",
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
    coins: "COINS",
    voll: "DOLU",
    neverBelow: "ASLA ALTINDA DEĞİL",
    payoutFrom: "Ödeme",
    tabs: { week: "Bu Hafta", all: "Tüm Zamanlar", received: "Alınan", gifted: "Hediye Edilen" }
  }
};

// RASTER 6 COMPONENT
export default function Raster6_Battery_Gifting({ lang = "de", batteryCoins = 125, onFeedClick }) {
  const t = TRANSLATIONS[lang] || TRANSLATIONS.de;
  const [activeTab, setActiveTab] = useState("week");

  const tabs = [
    { id: "week", label: t.tabs.week },
    { id: "all", label: t.tabs.all },
    { id: "received", label: t.tabs.received },
    { id: "gifted", label: t.tabs.gifted },
  ];

  return (
    <div className="w-full rounded-3xl bg-[#111] border border-[#222] p-4 md:p-6">
      {/* TITLE - MUSS ALLES ERKLÄREN */}
      <div className="mb-6">
        <h2 className="text-2xl md:text-3xl font-black text-white">{t.title}</h2>
        <p className="text-sm md:text-base text-[#aaa] mt-2 leading-relaxed">{t.subtext}</p>
        <p className="text-xs text-[#666] mt-2 font-bold">{t.shortTitle}</p>
      </div>

      {/* OBEN - BATTERIE 1 - ANKLICKBAR */}
      <div
        onClick={onFeedClick}
        className="cursor-pointer w-full rounded-2xl bg-gradient-to-b from-[#1a1a1a] to-[#0a0a0a] border-2 border-[#ff3b3b] p-5 mb-5 hover:scale-[1.01] transition-transform"
      >
        <div className="flex justify-between items-center mb-3">
          <span className="text-white font-black text-lg">{t.battery} - {t.coins}</span>
          <span className="text-[#ff3b3b] text-xs font-bold">{t.payoutFrom} 2000+ • {t.neverBelow} 125 • {t.voll} 2500</span>
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
        <div className="mt-3 text-center">
          <button className="bg-[#ff3b3b] text-white font-black px-6 py-2 rounded-full text-sm">
            🔋 {t.feedBtn} {t.battery}
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
        {/* Leaderboard Content */}
        <div className="p-4">
          <div className="text-[#666] text-xs font-bold mb-3 uppercase">
            {t.tabs[activeTab]} - Leaderboard
          </div>
          {/* Placeholder Leaderboard - hier echte Daten einbinden */}
          <div className="space-y-2">
            {[1,2,3,4,5].map((rank) => (
              <div key={rank} className="flex items-center gap-3 bg-[#222] rounded-xl p-3">
                <div className="w-6 h-6 rounded-full bg-[#ff3b3b] text-white text-xs font-black flex items-center justify-center">
                  {rank}
                </div>
                <div className="w-8 h-8 rounded-full bg-[#333]" />
                <div className="flex-1">
                  <div className="text-white text-sm font-bold">User {rank}</div>
                  <div className="text-[#666] text-xs">{rank * 123} {t.coins} {activeTab === 'received' ? t.tabs.received : activeTab === 'gifted' ? t.tabs.gifted : ''}</div>
                </div>
                <div className="text-[#ff3b3b] font-black text-sm">{rank * 123} 🪙</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// EXPORT FÜR LOCALES JSON - für i18n.js / locales/*.json
export { TRANSLATIONS };
