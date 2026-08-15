import React, { useEffect, useState } from "react";

const SPONSORS = [
  { id: "bet365", name: "bet365", color: "#137C3D", url: "https://www.bet365.com" },
  { id: "tipico", name: "Tipico", color: "#D50000", url: "https://www.tipico.de" },
  { id: "bwin", name: "bwin", color: "#FFCC00", url: "https://www.bwin.de" },
  { id: "wazamba", name: "Wazamba", color: "#7C3AED", url: "https://wazamba.com" },
  { id: "betano", name: "Betano", color: "#FF6B00", url: "https://www.betano.de" },
];

const STORAGE_KEY = "tipjar_sponsor_clicks_v2";

export default function SponsorFeeder() {
  const [clicked, setClicked] = useState({});
  const [animating, setAnimating] = useState(null);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      const data = JSON.parse(raw);
      const today = new Date().toDateString();
      if (data.date === today) {
        setClicked(data.clicked || {});
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {}
  }, []);

  const handleClick = (sponsor) => {
    if (clicked[sponsor.id]) return;
    const today = new Date().toDateString();
    const newClicked = { ...clicked, [sponsor.id]: true };
    setClicked(newClicked);
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ date: today, clicked: newClicked }));
    setAnimating(sponsor.id);
    window.dispatchEvent(new CustomEvent("tipjar-boost", { detail: { amount: 1, power: 5, source: sponsor.id } }));
    window.dispatchEvent(new CustomEvent("tipjar-boost-gold", { detail: { power: 5 } }));
    setTimeout(() => setAnimating(null), 800);
    window.open(sponsor.url, "_blank", "noopener,noreferrer");
  };

  const todayCount = Object.keys(clicked).length;

  return (
    <div className="w-full max-w-5xl mx-auto mb-4 p-3 rounded-xl bg-zinc-900 border border-white/10">
      <div className="flex justify-between items-center mb-2">
        <div className="text-[10px] font-bold tracking-widest text-zinc-500">SPONSOR FEEDER - 1 CLICK FÜR 1 GOLD COIN + 5 POWER (1x/Tag pro Anbieter)</div>
        <div className="text-[9px] text-zinc-600">{todayCount}/5 heute</div>
      </div>
      <div className="grid grid-cols-5 gap-2">
        {SPONSORS.map(s => {
          const isDone = clicked[s.id];
          return (
            <button
              key={s.id}
              onClick={() => handleClick(s)}
              className={`h-14 rounded-lg font-black text-[12px] border transition-all flex items-center justify-center cursor-pointer select-none
                ${isDone ? 'border-[#22c55e]/50 shadow-inner scale-[0.96] brightness-[0.85]' : 'border-white/10 hover:scale-[1.03] active:scale-[0.97] hover:border-[#D4FF32]/50'}
                ${animating === s.id ? 'ring-2 ring-[#D4FF32] scale-105' : ''}`}
              style={{ 
                background: s.color,
                color: s.id === 'bwin' ? 'black' : 'white',
                opacity: isDone ? 0.8 : 1,
                boxShadow: isDone ? 'inset 0 2px 8px rgba(0,0,0,0.4)' : 'none'
              }}
            >
              <span className={isDone ? 'opacity-80' : ''}>{s.name}</span>
            </button>
          );
        })}
      </div>
      <div className="text-[9px] text-zinc-600 mt-2 text-center">
        {todayCount === 5 ? 'Alle 5 heute erledigt - morgen Reset! = 5 Gold + 25 Power' : `${5 - todayCount} Anbieter noch offen heute (${todayCount}/5)`}
      </div>
    </div>
  );
}
