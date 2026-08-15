import React, { useEffect, useState } from "react";

const SPONSORS = [
  { id: "bet365", name: "bet365", color: "#137C3D" },
  { id: "tipico", name: "Tipico", color: "#D50000" },
  { id: "bwin", name: "bwin", color: "#FFCC00" },
  { id: "wazamba", name: "Wazamba", color: "#7C3AED" },
  { id: "betano", name: "Betano", color: "#FF6B00" },
];

export default function SponsorFeeder() {
  const [claimedToday, setClaimedToday] = useState(false);
  const [animating, setAnimating] = useState(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const last = localStorage.getItem("tipjar_sponsor_last");
    if (last) {
      const d = new Date(last);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) setClaimedToday(true);
    }
  }, []);

  const handleClick = (sponsor) => {
    if (claimedToday) return;
    setAnimating(sponsor.id);
    // 20/20 = 1 full gold coin instantly
    try {
      localStorage.setItem("tipjar_sponsor_last", new Date().toISOString());
    } catch {}
    setClaimedToday(true);

    // Fire gold boost events: 20 silver + 20 gold logic = 1 gold coin
    if (typeof window !== "undefined") {
      window.dispatchEvent(new CustomEvent("tipjar-boost", { detail: { power: 5 } }));
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent("tipjar-boost-gold", { detail: { power: 10 } }));
      }, 200);
    }

    setTimeout(() => setAnimating(null), 1200);
  };

  return (
    <div className="w-full max-w-5xl mx-auto mb-4 p-3 rounded-xl bg-zinc-900 border border-white/10">
      <div className="text-[10px] font-bold tracking-widest text-zinc-500 mb-2">SPONSOR FEEDER - 1 CLICK = 1 GOLD COIN (1x/DAY)</div>
      <div className="grid grid-cols-5 gap-2">
        {SPONSORS.map(s => (
          <button
            key={s.id}
            onClick={() => handleClick(s)}
            disabled={claimedToday}
            className={`h-12 rounded-lg font-black text-[11px] border border-white/10 transition-all ${claimedToday ? 'opacity-30 cursor-not-allowed bg-zinc-800' : 'hover:scale-105 active:scale-95'} ${animating === s.id ? 'animate-bounce ring-2 ring-[#D4FF32]' : ''}`}
            style={{ background: s.color, color: s.id === 'bwin' ? 'black' : 'white' }}
          >
            {s.name}
            {animating === s.id && <div className="text-[9px]">+1 GOLD!</div>}
          </button>
        ))}
      </div>
      {claimedToday && <div className="text-[10px] text-zinc-500 mt-2 text-center">Heute bereits gesammelt - morgen wieder!</div>}
    </div>
  );
}
