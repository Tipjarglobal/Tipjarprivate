import React, { useEffect, useState } from "react";

const SPONSORS = [
  { id: "bet365", name: "bet365", color: "#137C3D" },
  { id: "tipico", name: "Tipico", color: "#D50000" },
  { id: "bwin", name: "bwin", color: "#FFCC00" },
  { id: "wazamba", name: "Wazamba", color: "#7C3AED" },
  { id: "betano", name: "Betano", color: "#FF6B00" },
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
    window.dispatchEvent(new CustomEvent("tipjar-boost", { detail: { amount: 0.05, power: 5, source: sponsor.id } }));
    window.dispatchEvent(new CustomEvent("tipjar-boost-gold", { detail: { power: 5 } }));
    setTimeout(() => setAnimating(null), 1200);
  };

  const todayCount = Object.keys(clicked).length;

  return (
    <div className="w-full max-w-5xl mx-auto mb-4 p-3 rounded-xl bg-zinc-900 border border-white/10">
      <div className="flex justify-between items-center mb-2">
        <div className="text-[10px] font-bold tracking-widest text-zinc-500">SPONSOR FEEDER - 1 CLICK = 1/20 COIN + 5 POWER (1x/Tag pro Anbieter)</div>
        <div className="text-[9px] text-zinc-600">{todayCount}/5 heute</div>
      </div>
      <div className="grid grid-cols-5 gap-2">
        {SPONSORS.map(s => {
          const isDone = clicked[s.id];
          return (
            <button
              key={s.id}
              onClick={() => handleClick(s)}
              className={`h-14 rounded-lg font-black text-[11px] border transition-all flex flex-col items-center justify-center gap-1 cursor-pointer ${isDone ? 'bg-zinc-800 border-[#22c55e]/30 text-zinc-400' : 'border-white/10 hover:scale-105 active:scale-95 hover:border-[#D4FF32]/50 text-white'} ${animating === s.id ? 'animate-bounce ring-2 ring-[#D4FF32] scale-110' : ''}`}
              style={{ background: isDone ? '#18181b' : s.color, color: !isDone && s.id === 'bwin' ? 'black' : isDone ? '#a1a1aa' : 'white' }}
            >
              <span>{s.name}</span>
              {isDone ? <span className="text-[8px] text-[#22c55e]">✓ +1/20 heute</span> : animating === s.id ? <span className="text-[9px]">+1/20!</span> : <span className="text-[7px] opacity-70">+5 Power</span>}
            </button>
          );
        })}
      </div>
      <div className="text-[9px] text-zinc-600 mt-2 text-center">
        {todayCount === 5 ? 'Alle 5 heute erledigt - morgen Reset! = 5/20 Coin + 25 Power' : `${5 - todayCount} Anbieter noch offen heute`}
      </div>
    </div>
  );
}
