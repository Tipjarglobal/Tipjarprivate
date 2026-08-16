import React, { useEffect, useState } from "react";

const SPONSORS = [
  { id: "stake", name: "STAKE", color: "#1A2C38", url: "https://stake.com/?c=tipjar" },
  { id: "roobet", name: "ROOBET", color: "#F5A623", url: "https://roobet.com/?ref=tipjar" },
  { id: "gamdom", name: "GAMDOM", color: "#00FF88", url: "https://gamdom.com/r/tipjar" },
  { id: "rollbit", name: "ROLLBIT", color: "#FF0055", url: "https://rollbit.com/referral/tipjar" },
  { id: "duelbits", name: "DUELBITS", color: "#6C5CE7", url: "https://duelbits.com/?a=tipjar" },
  { id: "shuffle", name: "SHUFFLE", color: "#111111", url: "https://shuffle.com/?r=tipjar" },
  { id: "bcgame", name: "BC.GAME", color: "#1ABF6D", url: "https://bc.game/i-tipjar/" },
  { id: "clash", name: "CLASH.GG", color: "#FF4D00", url: "https://clash.gg/r/tipjar" },
  { id: "wazamba", name: "WAZAMBA", color: "#7C3AED", url: "https://wazamba.com/" },
  { id: "500casino", name: "500 CASINO", color: "#2D2DFF", url: "https://500.casino/r/tipjar" },
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
      <div className="text-[10px] font-black tracking-widest text-zinc-500 mb-2 text-center">
        SPONSOR FEEDER - 10.COM - MAX 5 GOLD / TAG - COIN BATTERY
      </div>
      {animating && (
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-30 pointer-events-none flex flex-col items-center">
          <div className={`${showCoin? 'opacity-100 -translate-y-8' : 'opacity-0 translate-y-2'} transition-all duration-300 text-3xl`}>🪙</div>
          <div className={`text-5xl transition-transform duration-[600ms] ${jarJump? '-translate-y-16 rotate-12 scale-110' : 'translate-y-0 scale-100'}`}>🏺</div>
          {!jarJump && <div className="text-yellow-400 animate-ping text-xl -mt-2">⚡</div>}
        </div>
      )}
      <div className="grid grid-cols-5 gap-2">
        {SPONSORS.map((s) => {
          const isDone = clicked[s.id];
          const disabledGold = limitReached &&!isDone;
          return (
            <button
              key={s.id}
              onClick={() => handleClick(s)}
              className={`h-[56px] rounded-lg font-black text-[11px] tracking-wider border transition-all cursor-pointer relative
                ${isDone? 'brightness-[0.5] scale-[0.96] border-green-500/30' : 'hover:scale-[1.04] border-white/10 hover:border-white/20'}
                ${animating === s.id? 'ring-2 ring-[#D4FF32] z-10' : ''}
                ${disabledGold? 'opacity-60' : ''}`}
              style={{ background: s.color, color: 'white' }}
            >
              {s.name}
              {isDone && <span className="absolute top-1 right-1 text-[8px]">✓</span>}
            </button>
          );
        })}
      </div>
      <div className="text-[9px] text-zinc-500 mt-2 text-center font-mono">
        {limitReached? 'DAILY LIMIT: 5/5 GOLD - Morgen Reset - Links öffnen trotzdem' : `${todayCount}/5 Gold heute - wähle 5 aus 10 - jeder Link öffnet immer`}
      </div>
    </div>
  );
}
