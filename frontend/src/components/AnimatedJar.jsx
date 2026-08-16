import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "../auth";

const JAR_DEFS = [
  { id: "common_glass", name: "Common Glass", coins: 40, color: "#e5e7eb", tier: "common", graphic: "/jars/graphic_common_glass_closed_front.png", graphicOpen: "/jars/g_common_open_top.png" },
  { id: "wood", name: "Wood", coins: 50, color: "#92400e", tier: "common", graphic: "/jars/graphic_wood_closed_front.png" },
  { id: "stone", name: "Stone", coins: 60, color: "#78716c", tier: "common", graphic: "/jars/graphic_stone_closed_front.png" },
  { id: "clay", name: "Clay", coins: 70, color: "#a16207", tier: "common", graphic: "/jars/graphic_wood_closed_front.png" },
  { id: "bamboo", name: "Bamboo", coins: 75, color: "#65a30d", tier: "common", graphic: "/jars/graphic_wood_closed_front.png" },
  { id: "carton_box", name: "Carton Box", coins: 80, color: "#d6c7a5", tier: "common", graphic: "/jars/graphic_wood_closed_front.png" },
  { id: "bronze", name: "Bronze", coins: 90, color: "#b45309", tier: "common", graphic: "/jars/g_bronze_closed.png" },
  { id: "tin", name: "Tin", coins: 100, color: "#a1a1aa", tier: "uncommon", graphic: "/jars/g_tin_closed.png" },
  { id: "iron", name: "Iron", coins: 110, color: "#57534e", tier: "uncommon", graphic: "/jars/g_tin_closed.png" },
  { id: "steel", name: "Steel", coins: 120, color: "#71717a", tier: "uncommon", graphic: "/jars/g_steel_closed.png" },
  { id: "brass", name: "Brass", coins: 130, color: "#ca8a04", tier: "uncommon", graphic: "/jars/g_bronze_closed.png" },
  { id: "copper", name: "Copper", coins: 150, color: "#c2410c", tier: "uncommon", graphic: "/jars/g_copper_closed.png" },
  { id: "aluminum", name: "Aluminum", coins: 170, color: "#d4d4d8", tier: "uncommon", graphic: "/jars/g_aluminum_closed.png" },
  { id: "frosted_glass", name: "Frosted Glass", coins: 180, color: "#e4e4e7", tier: "rare", graphic: "/jars/g_frosted_closed.png" },
  { id: "silver", name: "Silver", coins: 200, color: "#e4e4e7", tier: "rare", graphic: "/jars/g_chrome_closed.png" },
  { id: "chrome", name: "Chrome", coins: 220, color: "#f4f4f5", tier: "rare", graphic: "/jars/g_chrome_closed.png" },
  { id: "titanium", name: "Titanium", coins: 250, color: "#a1a1aa", tier: "rare", graphic: "/jars/g_titanium_closed.png" },
  { id: "obsidian", name: "Obsidian", coins: 280, color: "#18181b", tier: "epic", graphic: "/jars/g_obsidian_closed.png" },
  { id: "gold", name: "Gold", coins: 300, color: "#facc15", tier: "epic", graphic: "/jars/g_ruby_closed.png", graphicOpen: "/jars/g_gold_open_top.png", isLuxury: true },
  { id: "ruby", name: "Ruby", coins: 320, color: "#dc2626", tier: "epic", graphic: "/jars/g_ruby_closed.png", isLuxury: true },
  { id: "sapphire", name: "Sapphire", coins: 330, color: "#2563eb", tier: "epic", graphic: "/jars/g_sapphire_closed.png", isLuxury: true },
  { id: "platinum", name: "Platinum", coins: 350, color: "#e7e5e4", tier: "epic", graphic: "/jars/g_platinum_closed.png", isLuxury: true },
  { id: "emerald", name: "Emerald", coins: 400, color: "#16a34a", tier: "legendary", graphic: "/jars/g_emerald_closed.png", isLuxury: true },
  { id: "crystal", name: "Crystal", coins: 420, color: "#06b6d4", tier: "legendary", graphic: "/jars/g_crystal_closed.png", isLuxury: true },
  { id: "diamond", name: "Diamond", coins: 450, color: "#22d3ee", tier: "legendary", graphic: "/jars/g_diamond_closed.png", isLuxury: true },
  { id: "cosmic", name: "Cosmic", coins: 480, color: "#8b5cf6", tier: "legendary", graphic: "/jars/g_cosmic_closed.png", isLuxury: true },
  { id: "galaxy", name: "Galaxy", coins: 500, color: "#7c3aed", tier: "mystic", graphic: "/jars/g_galaxy2_closed.png", isLuxury: true },
  { id: "void", name: "Void", coins: 510, color: "#000000", tier: "mystic", graphic: "/jars/g_void_closed.png", isLuxury: true },
  { id: "nebula", name: "Nebula", coins: 520, color: "#ec4899", tier: "mystic", graphic: "/jars/g_nebula_closed.png", isLuxury: true },
  { id: "infinity", name: "Infinity", coins: 530, color: "#f0f9ff", tier: "mystic", graphic: "/jars/g_infinity_closed.png", isLuxury: true },
];

function getJarForCredits(c) { let best = JAR_DEFS[0]; for (const j of JAR_DEFS) if (c >= j.coins) best = j; return best; }

export { JAR_DEFS, getJarForCredits };

export default function AnimatedJar() {
  const { user } = useAuth();
  const [boostFlash, setBoostFlash] = useState(false);
  const [fallingCoins, setFallingCoins] = useState([]);
  const credits = (user?.received_credits || 0) + (user?.credits || 0);
  const currentJar = getJarForCredits(credits);
  const idx = JAR_DEFS.findIndex(j => j.id === currentJar.id);
  const nextJar = JAR_DEFS[idx + 1];
  const prevCoins = currentJar.coins;
  const nextCoins = nextJar ? nextJar.coins : currentJar.coins + 100;
  const progress = nextJar ? ((credits - prevCoins) / (nextCoins - prevCoins)) * 100 : 100;
  const fillPercent = Math.min(100, Math.max(5, progress));

  useEffect(() => {
    const onBoost = (e) => {
      setBoostFlash(true);
      const isGold = Math.random() > 0.5;
      const id = Date.now() + Math.random();
      setFallingCoins(prev => [...prev, { id, type: isGold ? 'gold' : 'silver', x: 40 + Math.random()*20 }]);
      setTimeout(() => setFallingCoins(prev => prev.filter(c => c.id !== id)), 1000);
      setTimeout(() => setBoostFlash(false), 700);
    };
    window.addEventListener("tipjar-boost", onBoost);
    return () => window.removeEventListener("tipjar-boost", onBoost);
  }, []);

  return (
    <div className="relative mx-auto flex flex-col items-center w-full max-w-[440px]" data-testid="animated-jar">
      <motion.img src="/tipjar-crest.png?v=5" alt="TipJar" className="w-[120px] h-[120px] object-contain mb-2" style={{ filter: "drop-shadow(0 0 20px rgba(225,255,0,0.4))" }} animate={{ y: [0, -6, 0] }} transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }} />
      
      {/* Graphic Jar Container - optimized for coin animation */}
      <div className={`relative w-[200px] h-[260px] flex items-end justify-center overflow-hidden transition-all ${boostFlash ? 'scale-105 drop-shadow-[0_0_30px_#D4FF32]' : ''}`}>
        {/* Fill inside jar - behind graphic */}
        <div className="absolute bottom-[18px] left-[30px] right-[30px] top-[60px] rounded-b-[30px] overflow-hidden z-0">
          <div className="absolute bottom-0 left-0 right-0 rounded-b-[20px] transition-all duration-700 ease-out" style={{ height: `${fillPercent}%`, background: `linear-gradient(180deg, ${currentJar.color}cc, ${currentJar.color})`, boxShadow: `inset 0 0 20px ${currentJar.color}60` }}>
            {/* liquid surface */}
            <div className="absolute -top-[6px] left-0 right-0 h-[12px] rounded-full" style={{ background: currentJar.color, filter: "brightness(1.2)" }} />
          </div>
          {/* falling coins */}
          {fallingCoins.map(c => (
            <motion.div key={c.id} className={`absolute w-[14px] h-[14px] rounded-full border-2 z-10 ${c.type === 'gold' ? 'bg-[#facc15] border-[#eab308]' : 'bg-[#e4e4e7] border-[#a1a1aa]'}`} style={{ left: `${c.x}%` }} initial={{ top: -20, rotate: 0 }} animate={{ top: `${100 - fillPercent}%`, rotate: 360 }} transition={{ duration: 0.9, ease: "easeIn" }} />
          ))}
        </div>
        {/* Graphic image on top */}
        <img src={currentJar.graphic} alt={currentJar.name} className="relative z-10 w-full h-full object-contain pointer-events-none" style={{ filter: boostFlash ? "drop-shadow(0 0 10px #D4FF32)" : "none" }} />
        {boostFlash && (<div className="absolute top-[40%] left-1/2 -translate-x-1/2 z-20"><div className="bg-[#D4FF32] text-black font-black text-[11px] px-3 py-1 rounded-full animate-bounce">+1</div></div>)}
      </div>

      <div className="mt-3 text-center">
        <div className="text-[11px] font-black tracking-widest" style={{ color: currentJar.color }}>{currentJar.name.toUpperCase()} • {fillPercent.toFixed(0)}%</div>
        <div className="text-[9px] text-zinc-500">{credits.toFixed(0)} / {nextCoins} COINS • {idx+1}/30 • {currentJar.tier.toUpperCase()}</div>
      </div>
    </div>
  );
}
