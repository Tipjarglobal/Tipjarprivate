import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "../auth";

const JAR_DEFS = [
  { id: "common_glass", name: "Common Glass", coins: 40, color: "#e5e7eb" },
  { id: "wood", name: "Wood", coins: 50, color: "#92400e" },
  { id: "stone", name: "Stone", coins: 60, color: "#78716c" },
  { id: "clay", name: "Clay", coins: 70, color: "#a16207" },
  { id: "bamboo", name: "Bamboo", coins: 75, color: "#65a30d" },
  { id: "carton_box", name: "Carton Box", coins: 80, color: "#d6c7a5" },
  { id: "bronze", name: "Bronze", coins: 90, color: "#b45309" },
  { id: "iron", name: "Iron", coins: 110, color: "#57534e" },
  { id: "silver", name: "Silver", coins: 200, color: "#e4e4e7" },
  { id: "gold", name: "Gold", coins: 300, color: "#facc15" },
  { id: "platinum", name: "Platinum", coins: 350, color: "#e7e5e4" },
  { id: "diamond", name: "Diamond", coins: 450, color: "#22d3ee" },
  { id: "galaxy", name: "Galaxy", coins: 500, color: "#7c3aed" },
  { id: "void", name: "Void", coins: 500, color: "#000" },
  { id: "nebula", name: "Nebula", coins: 500, color: "#ec4899" },
  { id: "infinity", name: "Infinity", coins: 500, color: "#f0f9ff" },
];

function getJarForCredits(c) { let best = JAR_DEFS[0]; for (const j of JAR_DEFS) if (c >= j.coins) best = j; return best; }

export default function AnimatedJar() {
  const { user } = useAuth();
  const [boostFlash, setBoostFlash] = useState(false);
  const credits = (user?.received_credits || 0) + (user?.credits || 0);
  const currentJar = getJarForCredits(credits);
  const fillPercent = Math.min(100, (credits / currentJar.coins) * 100);
  useEffect(() => {
    const onBoost = () => { setBoostFlash(true); setTimeout(() => setBoostFlash(false), 700); };
    window.addEventListener("tipjar-boost", onBoost);
    return () => window.removeEventListener("tipjar-boost", onBoost);
  }, []);
  return (
    <div className="relative mx-auto flex flex-col items-center w-full max-w-[440px]" data-testid="animated-jar">
      <motion.img src="/tipjar-crest.png?v=5" alt="TipJar" className="w-[120px] h-[120px] object-contain mb-2" style={{ filter: "drop-shadow(0 0 20px rgba(225,255,0,0.4))" }} animate={{ y: [0, -6, 0] }} transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }} />
      <div className={`relative w-[180px] h-[220px] rounded-b-[40px] rounded-t-[16px] border-2 bg-zinc-900 overflow-hidden transition-all ${boostFlash ? 'scale-105 border-[#D4FF32] shadow-[0_0_30px_#D4FF32]' : 'border-white/10'}`}>
        <div className="absolute top-0 left-0 right-0 h-[22px] bg-gradient-to-b from-zinc-700 to-zinc-900 border-b border-white/10 rounded-t-[14px] z-20 flex items-center justify-center"><div className="w-[80%] h-[6px] rounded-full bg-zinc-600" /></div>
        <div className="absolute bottom-0 left-[4px] right-[4px] rounded-b-[36px] transition-all duration-700" style={{ height: `${Math.min(100, fillPercent)}%`, background: `linear-gradient(180deg, ${currentJar.color}cc, ${currentJar.color})`, boxShadow: `0 -10px 30px ${currentJar.color}80 inset, 0 0 20px ${currentJar.color}60` }}>
          <div className="absolute -top-[6px] left-0 right-0 h-[12px] rounded-full" style={{ background: currentJar.color }} />
        </div>
        <div className="absolute left-[12%] top-[18%] bottom-[15%] w-[3px] bg-white/10 rounded-full blur-[0.5px] z-10" />
        {boostFlash && (<div className="absolute inset-0 flex items-center justify-center z-30"><div className="bg-[#D4FF32] text-black font-black text-[11px] px-3 py-1 rounded-full animate-bounce">+1/20</div></div>)}
      </div>
      <div className="mt-3 text-center"><div className="text-[11px] font-black tracking-widest" style={{ color: currentJar.color }}>{currentJar.name.toUpperCase()} • {fillPercent.toFixed(0)}%</div><div className="text-[9px] text-zinc-500">{credits.toFixed(2)} / {currentJar.coins} COINS</div></div>
    </div>
  );
}
