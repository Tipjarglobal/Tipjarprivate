import React, { useEffect, useState } from "react";

export default function CoinBattery() {
  const [power, setPower] = useState(75);
  const [lastBoost, setLastBoost] = useState(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    try {
      const saved = window.localStorage.getItem("tipjar_battery");
      if (saved) {
        const n = parseInt(saved);
        setPower(isNaN(n) || n < 5 ? 5 : n);
      }
    } catch {}

    const onBoost = (e) => {
      const add = e?.detail?.power || 5;
      setPower(p => {
        const next = Math.min(100, p + add);
        try { window.localStorage.setItem("tipjar_battery", String(next)); } catch {}
        return next;
      });
      setLastBoost(`+${add}%`);
      setTimeout(() => setLastBoost(null), 3000);
    };

    window.addEventListener("tipjar-boost", onBoost);
    window.addEventListener("tipjar-boost-gold", onBoost);
    return () => {
      window.removeEventListener("tipjar-boost", onBoost);
      window.removeEventListener("tipjar-boost-gold", onBoost);
    };
  }, []);

  useEffect(() => {
    if (power < 5) setPower(5);
  }, [power]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const boosts = [10, 20, 30, 40];
    const triggerBoost = () => {
      const randomBoost = boosts[Math.floor(Math.random() * boosts.length)];
      setPower(p => {
        const next = Math.min(100, p + randomBoost);
        try { window.localStorage.setItem("tipjar_battery", String(next)); } catch {}
        return next;
      });
      setLastBoost(`+${randomBoost}% BOOST`);
      setTimeout(() => setLastBoost(null), 4000);
    };
    const firstTimeout = setTimeout(triggerBoost, 480000 + Math.random() * 420000);
    const interval = setInterval(() => {
      if (Math.random() < 0.3) triggerBoost();
    }, 2700000 + Math.random() * 2700000);
    return () => {
      clearTimeout(firstTimeout);
      clearInterval(interval);
    };
  }, []);

  const pct = Math.max(5, Math.min(100, power));
  const color = pct > 60 ? "#D4FF32" : pct > 30 ? "#FFD447" : "#ff4444";

  return (
    <div className="w-full max-w-5xl mx-auto mb-4 p-3 rounded-xl bg-zinc-900 border border-white/10 flex items-center justify-between relative overflow-hidden">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-black border border-white/10 flex items-center justify-center text-[12px]">⚡</div>
        <div>
          <div className="text-[10px] font-bold tracking-widest text-zinc-500 flex items-center gap-2">
            TIPJAR POWER
            {lastBoost && <span className="text-[10px] font-black text-black bg-[#D4FF32] px-2 py-0.5 rounded-full animate-bounce">{lastBoost}</span>}
          </div>
          <div className="flex items-center gap-2">
            <div className="w-32 h-2 bg-black rounded-full overflow-hidden border border-white/10">
              <div className="h-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
            </div>
            <span className="text-[11px] font-black" style={{ color }}>{pct}%</span>
          </div>
        </div>
      </div>
      <div className="text-[10px] text-zinc-500">{power}/100</div>
    </div>
  );
}
