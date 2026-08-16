import React, { useEffect, useState } from "react";
const SPONSORS = [
  { id: "wazamba", name: "WAZAMBA", color: "#7C3AED", url: "https://wazamba.com/" },
  { id: "bankonbet", name: "BANKONBET", color: "#00D084", url: "https://bankonbet.com/?ref=tipjar" },
  { id: "robocat", name: "ROBOCAT", color: "#FF3B30", url: "https://robocat.com/?ref=tipjar" },
  { id: "pistolo", name: "PISTOLO", color: "#FFCC00", url: "https://pistolo.com/?ref=tipjar" },
  { id: "bet22", name: "BET22", color: "#0A84FF", url: "https://bet22.com/?ref=tipjar" },
  { id: "5gringos", name: "5GRINGOS", color: "#8B4513", url: "https://5gringos.com/?ref=tipjar" },
  { id: "freshbet", name: "FRESHBET", color: "#FF4500", url: "https://freshbet.me/?ref=tipjar" },
  { id: "supabet", name: "SUPABET", color: "#E30613", url: "https://supabet1.com/?ref=tipjar" },
  { id: "betlab", name: "BETLAB", color: "#111111", url: "https://betlab.com/?ref=tipjar" },
  { id: "20bet", name: "20BET", color: "#00B050", url: "https://20bet.com/?ref=tipjar" },
  { id: "granswin", name: "GRANSWIN", color: "#FFD700", url: "https://granswin.com/?ref=tipjar" },
  { id: "scored", name: "SCORED", color: "#00CCFF", url: "https://scored.com/?ref=tipjar" },
  { id: "sportaza", name: "SPORTAZA", color: "#FF6B00", url: "https://sportaza.com/?ref=tipjar" },
  { id: "soringos", name: "SORINGOS", color: "#FF1493", url: "https://soringos.com/?ref=tipjar" },
  { id: "spinbetter", name: "SPINBETTER", color: "#00A3E0", url: "https://spinbetter.com/?ref=tipjar" },
];
const STORAGE_KEY = "tipjar_sponsor_clicks_v2";
export default function SponsorFeeder() {
  const [clicked, setClicked] = useState({});
  const [animating, setAnimating] = useState(null);
  const [jarJump, setJarJump] = useState(false);
  const [showCoin, setShowCoin] = useState(false);
  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    try {
      const data = JSON.parse(raw);
      if (data.date === new Date().toDateString()) setClicked(data.clicked || {});
      else localStorage.removeItem(STORAGE_KEY);
    } catch {}
  }, []);
  const todayCount = Object.keys(clicked).length;
  const limitReached = todayCount >= 5;
  const handleClick = (s) => {
    const isDone = clicked[s.id];
    setAnimating(s.id);
    setJarJump(true);
    setTimeout(() => setShowCoin(true), 250);
    setTimeout(() => {
      setShowCoin(false);
      setJarJump(false);
      if (!isDone && !limitReached) {
        const today = new Date().toDateString();
        const next = { ...clicked, [s.id]: true };
        setClicked(next);
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ date: today, clicked: next }));
        window.dispatchEvent(new CustomEvent("tipjar-boost", { detail: { amount: 1, power: 5, source: s.id } }));
      }
      setTimeout(() => setAnimating(null), 300);
      window.open(s.url, "_blank", "noopener,noreferrer");
    }, 1000);
  };
  return (
    <div className="w-full max-w-5xl mx-auto mb-4 p-3 rounded-xl bg-zinc-900 border border-white/10 relative overflow-hidden">
      <div className="text-[10px] font-black tracking-widest text-zinc-500 mb-2 text-center">
        SPONSOR FEEDER - 15 BOOKIES - MAX 5 GOLD / TAG - COIN BATTERY
      </div>
      {animating && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-30 pointer-events-none flex flex-col items-center">
          <div className={`${showCoin ? 'opacity-100 -translate-y-8' : 'opacity-0 translate-y-2'} transition-all duration-300 text-3xl`}>🪙</div>
          <div className={`text-5xl transition-transform duration-[600ms] ${jarJump ? '-translate-y-16 rotate-12 scale-110' : 'translate-y-0 scale-100'}`}>🏺</div>
          {!jarJump && <div className="text-yellow-400 animate-ping text-xl -mt-2">⚡</div>}
        </div>
      )}
      <div className="grid grid-cols-5 gap-2">
        {SPONSORS.map((s) => {
          const isDone = clicked[s.id];
          return (
            <button key={s.id} onClick={() => handleClick(s)} className={`h-[56px] rounded-lg font-black text-[10px] tracking-wider border transition-all cursor-pointer relative ${isDone ? 'brightness-[0.5] scale-[0.96] border-green-500/30' : 'hover:scale-[1.04] border-white/10 hover:border-white/20'} ${animating === s.id ? 'ring-2 ring-[#D4FF32] z-10' : ''}`} style={{ background: s.color, color: 'white' }}>
              {s.name}
              {isDone && <span className="absolute top-1 right-1 text-[8px]">✓</span>}
            </button>
          );
        })}
      </div>
      <div className="text-[9px] text-zinc-500 mt-2 text-center font-mono">
        {limitReached ? 'DAILY LIMIT: 5/5 GOLD - Morgen Reset - Links öffnen trotzdem' : `${todayCount}/5 Gold heute - 15 zur Auswahl`}
      </div>
    </div>
  );
}
