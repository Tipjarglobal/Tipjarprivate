import React, { useEffect, useState } from "react";
import api from "../api";

const WAZAMBA = { 
  id: "wazamba", 
  name: "WAZAMBA", 
  color: "#7C3AED", 
  url: "https://wazamba.com/?ref=tipjar",
  bonus: "50% RELOAD BONUS BIS 500€",
};

const OTHERS = [
  { id: "bankonbet", name: "BANKONBET", color: "#00D084", url: "https://bankonbet.com/?ref=tipjar" },
  { id: "robocat", name: "ROBOCAT", color: "#FF3B30", url: "https://robocat.com/?ref=tipjar" },
  { id: "pistolo", name: "PISTOLO", color: "#FFCC00", url: "https://pistolo.com/?ref=tipjar" },
  { id: "5gringos", name: "5GRINGOS", color: "#8B4513", url: "https://5gringos.com/?ref=tipjar" },
  { id: "20bet", name: "20BET", color: "#00B050", url: "https://20bet.com/?ref=tipjar" },
  { id: "betscore", name: "BETSCORE", color: "#FFD600", url: "https://betscore.com/?ref=tipjar" },
  { id: "sgcasino", name: "SGCASINO", color: "#F59E0B", url: "https://sgcasino.com/?ref=tipjar" },
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
    api.post(`/sponsors/${s.id}/click`).catch(() => {});
    setAnimating(s.id);
    setJarJump(true);
    setTimeout(() => setShowCoin(true), 250);
    setTimeout(() => {
      setShowCoin(false);
      setJarJump(false);
      if (!isDone && !limitReached) {
        const today = new Date().toDateString();
        const next = {...clicked, [s.id]: true };
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
      
      {animating && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-30 pointer-events-none flex flex-col items-center">
          <div className={`${showCoin? 'opacity-100 -translate-y-8' : 'opacity-0 translate-y-2'} transition-all duration-300 text-3xl`}>🪙</div>
          <div className={`text-5xl transition-transform duration-[600ms] ${jarJump? '-translate-y-16 rotate-12 scale-110' : 'translate-y-0 scale-100'}`}>🏺</div>
          {!jarJump && <div className="text-yellow-400 animate-ping text-xl -mt-2">⚡</div>}
        </div>
      )}

      {/* 1. RENT 2 PILLS - GEFLOCHTEN - INSTAGRAM */}
      <button
        onClick={() => window.open("https://www.instagram.com/tipjarglobal", "_blank")}
        className="w-full h-[72px] mb-3 rounded-xl font-black border-2 border-dashed border-pink-500/50 hover:border-pink-400 bg-zinc-800/50 hover:bg-zinc-800 transition-all cursor-pointer relative overflow-hidden group"
      >
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex items-center justify-center -space-x-6 opacity-60">
            <div className="w-[180px] h-[48px] rounded-full bg-gradient-to-r from-zinc-700 to-zinc-600 border-2 border-white/20 flex items-center justify-center transform -rotate-3 group-hover:rotate-0 transition-transform">
              <span className="text-[10px] text-zinc-300">YOUR LINK</span>
            </div>
            <div className="w-[180px] h-[48px] rounded-full bg-gradient-to-r from-zinc-600 to-zinc-700 border-2 border-white/20 flex items-center justify-center transform rotate-3 group-hover:rotate-0 transition-transform z-10">
              <span className="text-[10px] text-zinc-300">YOUR LINK</span>
            </div>
          </div>
        </div>
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/40 backdrop-blur-[1px]">
          <div className="text-[13px] text-[#D4FF32] tracking-widest flex items-center gap-2">📸 RENT 2 PILLS FOR YOUR LINK 80€/MONTH</div>
          <div className="text-[9px] text-pink-300 mt-1">CLICK -> INSTAGRAM @tipjarglobal</div>
        </div>
      </button>

      {/* 2. RENT 1 PILL - GLEICHE BREITE WIE WAZAMBA - INSTAGRAM */}
      <button
        onClick={() => window.open("https://www.instagram.com/tipjarglobal", "_blank")}
        className="w-full h-[64px] mb-3 rounded-xl font-bold border-2 border-dashed border-pink-500/30 hover:border-pink-400 bg-zinc-800/30 hover:bg-zinc-800/60 transition-all cursor-pointer relative overflow-hidden flex items-center justify-center group"
      >
        <div className="w-[60%] h-[44px] rounded-full bg-zinc-700/30 border border-white/5 flex items-center justify-center">
          <span className="text-[10px] text-zinc-600">YOUR LINK HERE</span>
        </div>
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/30">
          <div className="text-[12px] text-white tracking-widest flex items-center gap-2">📸 RENT A PILL FOR YOUR LINK 50€/MONTH</div>
          <div className="text-[8px] text-pink-300 mt-1">CLICK -> INSTAGRAM @tipjarglobal</div>
        </div>
      </button>

      {/* 3. WAZAMBA */}
      <button
        onClick={() => handleClick(WAZAMBA)}
        className={`w-full h-[72px] mb-3 rounded-xl font-black border-2 transition-all cursor-pointer relative overflow-hidden flex items-center justify-between px-4
          ${clicked[WAZAMBA.id]? 'brightness-[0.6] border-green-500/50' : 'border-[#D4FF32]/50 hover:border-[#D4FF32] hover:scale-[1.01]'}
          ${animating === WAZAMBA.id? 'ring-2 ring-[#D4FF32] scale-[1.02]' : ''}`}
        style={{ background: `linear-gradient(135deg, ${WAZAMBA.color} 0%, #4C1D95 100%)`, color: 'white' }}
      >
        <div className="flex flex-col items-start">
          <div className="flex items-center gap-2">
            <span className="text-[16px] tracking-widest">WAZAMBA</span>
            <span className="text-[8px] bg-[#D4FF32] text-black px-2 py-[2px] rounded-full font-black">TOP</span>
          </div>
          <div className="text-[11px] font-bold text-[#D4FF32]">{WAZAMBA.bonus}</div>
        </div>
        <div className="text-[10px] bg-white/20 px-3 py-1 rounded-full">100% BIS 500€ + 200 FS</div>
      </button>

      <div className="grid grid-cols-5 gap-2">
        {OTHERS.map((s) => {
          const isDone = clicked[s.id];
          return (
            <button key={s.id} onClick={() => handleClick(s)}
              className={`h-[52px] rounded-lg font-black text-[10px] tracking-wider border transition-all cursor-pointer relative
                ${isDone? 'brightness-[0.5] scale-[0.96] border-green-500/30' : 'hover:scale-[1.04] border-white/10'}
                ${animating === s.id? 'ring-2 ring-[#D4FF32] z-10' : ''}`}
              style={{ background: s.color, color: 'white' }}>
              {s.name}
              {isDone && <span className="absolute top-1 right-1 text-[8px]">✓</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
