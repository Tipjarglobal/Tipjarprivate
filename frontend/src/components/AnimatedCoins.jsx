import React, { useEffect, useState } from "react";

export default function AnimatedCoins() {
  const [coins, setCoins] = useState([]);
  useEffect(() => {
    const handler = (e) => {
      const id = Date.now() + Math.random();
      const amount = e.detail?.amount || 0.05;
      const newCoin = { id, amount: amount === 0.05 ? "1/20" : `+${amount}`, x: 50 + (Math.random() - 0.5) * 20, color: "#D4FF32" };
      setCoins(prev => [...prev, newCoin]);
      setTimeout(() => { setCoins(prev => prev.filter(c => c.id !== id)); }, 1500);
    };
    window.addEventListener("tipjar-boost", handler);
    window.addEventListener("tipjar-boost-gold", handler);
    return () => { window.removeEventListener("tipjar-boost", handler); window.removeEventListener("tipjar-boost-gold", handler); };
  }, []);
  return (
    <div className="fixed top-20 left-0 right-0 pointer-events-none z-[100] flex justify-center">
      <div className="relative w-full max-w-5xl h-0">
        {coins.map(c => (
          <div key={c.id} className="absolute animate-[coinFly_1.5s_ease-out_forwards] flex items-center gap-1 bg-black/80 border px-3 py-1 rounded-full text-[11px] font-black" style={{ left: `${c.x}%`, borderColor: c.color, color: c.color, boxShadow: `0 0 12px ${c.color}60` }}>
            <div className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] text-black font-black" style={{ background: c.color }}>€</div>
            {c.amount}
          </div>
        ))}
      </div>
      <style>{`@keyframes coinFly { 0% { transform: translateY(0) translateX(-50%) scale(0.5); opacity: 0; } 15% { opacity: 1; transform: translateY(-10px) translateX(-50%) scale(1.2); } 100% { transform: translateY(-80px) translateX(-50%) scale(0.8); opacity: 0; } }`}</style>
    </div>
  );
}
