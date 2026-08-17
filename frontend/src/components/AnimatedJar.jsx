import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "../auth";

const JAR_DEFS = [
  { id: "common_glass", name: "Common Glass", coins: 40, color: "#e5e7eb", tier: "common", graphic: "/jars/graphic_common_glass_closed_front.png", graphicOpen: "/jars/g_common_open_top.png" },
  { id: "wood", name: "Wood", coins: 50, color: "#92400e", tier: "common", graphic: "/jars/graphic_wood_closed_front.png", graphicOpen: "/jars/g_wood_open_top.png" },
  { id: "stone", name: "Stone", coins: 60, color: "#78716c", tier: "common", graphic: "/jars/graphic_stone_closed_front.png", graphicOpen: "/jars/g_stone_open_top.png" },
  { id: "clay", name: "Clay", coins: 70, color: "#a16207", tier: "common", graphic: "/jars/graphic_wood_closed_front.png", graphicOpen: "/jars/g_clay_open_top.png" },
  { id: "bamboo", name: "Bamboo", coins: 75, color: "#65a30d", tier: "common", graphic: "/jars/graphic_wood_closed_front.png", graphicOpen: "/jars/g_bamboo_open_top.png" },
  { id: "carton_box", name: "Carton Box", coins: 80, color: "#d6c7a5", tier: "common", graphic: "/jars/graphic_wood_closed_front.png", graphicOpen: "/jars/g_carton_box_open_top.png" },
  { id: "bronze", name: "Bronze", coins: 90, color: "#b45309", tier: "common", graphic: "/jars/g_bronze_closed.png", graphicOpen: "/jars/g_bronze_open_top.png" },
  { id: "tin", name: "Tin", coins: 100, color: "#a1a1aa", tier: "uncommon", graphic: "/jars/g_tin_closed.png", graphicOpen: "/jars/g_tin_open_top.png" },
  { id: "iron", name: "Iron", coins: 110, color: "#57534e", tier: "uncommon", graphic: "/jars/g_tin_closed.png", graphicOpen: "/jars/g_iron_open_top.png" },
  { id: "steel", name: "Steel", coins: 120, color: "#71717a", tier: "uncommon", graphic: "/jars/g_steel_closed.png", graphicOpen: "/jars/g_steel_open_top.png" },
  { id: "brass", name: "Brass", coins: 130, color: "#ca8a04", tier: "uncommon", graphic: "/jars/g_bronze_closed.png", graphicOpen: "/jars/g_brass_open_top.png" },
  { id: "copper", name: "Copper", coins: 150, color: "#c2410c", tier: "uncommon", graphic: "/jars/g_copper_closed.png", graphicOpen: "/jars/g_copper_open_top.png" },
  { id: "aluminum", name: "Aluminum", coins: 170, color: "#d4d4d8", tier: "uncommon", graphic: "/jars/g_aluminum_closed.png", graphicOpen: "/jars/g_aluminum_open_top.png" },
  { id: "frosted_glass", name: "Frosted Glass", coins: 180, color: "#e4e4e7", tier: "rare", graphic: "/jars/g_frosted_closed.png", graphicOpen: "/jars/g_frosted_open_top.png" },
  { id: "silver", name: "Silver", coins: 200, color: "#e4e4e7", tier: "rare", graphic: "/jars/g_chrome_closed.png", graphicOpen: "/jars/g_silver_open_top.png" },
  { id: "chrome", name: "Chrome", coins: 220, color: "#f4f4f5", tier: "rare", graphic: "/jars/g_chrome_closed.png", graphicOpen: "/jars/g_chrome_open_top.png" },
  { id: "titanium", name: "Titanium", coins: 250, color: "#a1a1aa", tier: "rare", graphic: "/jars/g_titanium_closed.png", graphicOpen: "/jars/g_titanium_open_top.png" },
  { id: "obsidian", name: "Obsidian", coins: 280, color: "#18181b", tier: "epic", graphic: "/jars/g_obsidian_closed.png", graphicOpen: "/jars/g_obsidian_open_top.png" },
  { id: "gold", name: "Gold", coins: 300, color: "#facc15", tier: "epic", graphic: "/jars/g_ruby_closed.png", graphicOpen: "/jars/g_gold_open_top.png", isLuxury: true },
  { id: "ruby", name: "Ruby", coins: 320, color: "#dc2626", tier: "epic", graphic: "/jars/g_ruby_closed.png", graphicOpen: "/jars/g_ruby_open_top.png", isLuxury: true },
  { id: "sapphire", name: "Sapphire", coins: 330, color: "#2563eb", tier: "epic", graphic: "/jars/g_sapphire_closed.png", graphicOpen: "/jars/g_sapphire_open_top.png", isLuxury: true },
  { id: "platinum", name: "Platinum", coins: 350, color: "#e7e5e4", tier: "epic", graphic: "/jars/g_platinum_closed.png", graphicOpen: "/jars/g_platinum_open_top.png", isLuxury: true },
  { id: "emerald", name: "Emerald", coins: 400, color: "#16a34a", tier: "legendary", graphic: "/jars/g_emerald_closed.png", graphicOpen: "/jars/g_emerald_open_top.png", isLuxury: true },
  { id: "crystal", name: "Crystal", coins: 420, color: "#06b6d4", tier: "legendary", graphic: "/jars/g_crystal_closed.png", graphicOpen: "/jars/g_crystal_open_top.png", isLuxury: true },
  { id: "diamond", name: "Diamond", coins: 450, color: "#22d3ee", tier: "legendary", graphic: "/jars/g_diamond_closed.png", graphicOpen: "/jars/g_diamond_open_top.png", isLuxury: true },
  { id: "cosmic", name: "Cosmic", coins: 480, color: "#8b5cf6", tier: "legendary", graphic: "/jars/g_cosmic_closed.png", graphicOpen: "/jars/g_cosmic_open_top.png", isLuxury: true },
  { id: "galaxy", name: "Galaxy", coins: 500, color: "#7c3aed", tier: "mystic", graphic: "/jars/g_galaxy2_closed.png", graphicOpen: "/jars/g_galaxy_open_top.png" },
  { id: "void", name: "Void", coins: 510, color: "#000000", tier: "mystic", graphic: "/jars/g_void_closed.png", graphicOpen: "/jars/g_void_open_top.png", isLuxury: true },
  { id: "nebula", name: "Nebula", coins: 520, color: "#ec4899", tier: "mystic", graphic: "/jars/g_nebula_closed.png", graphicOpen: "/jars/g_nebula_open_top.png", isLuxury: true },
  { id: "infinity", name: "Infinity", coins: 530, color: "#f0f9ff", tier: "mystic", graphic: "/jars/g_infinity_closed.png", graphicOpen: "/jars/g_infinity_open_top.png", isLuxury: true },
];

function getJarForCredits(c) { let best = JAR_DEFS[0]; for (const j of JAR_DEFS) if (c >= j.coins) best = j; return best; }

export { JAR_DEFS, getJarForCredits };

export default function AnimatedJar() {
  const { user } = useAuth();
  const [boostFlash, setBoostFlash] = useState(false);
  const credits = (user?.received_credits || 0) + (user?.credits || 0);
  const currentJar = getJarForCredits(credits);
  const idx = JAR_DEFS.findIndex(j => j.id === currentJar.id);
  const nextJar = JAR_DEFS[idx + 1];
  const prevCoins = currentJar.coins;
  const nextCoins = nextJar ? nextJar.coins : currentJar.coins + 100;
  const progress = nextJar ? ((credits - prevCoins) / (nextCoins - prevCoins)) * 100 : 100;
  const fillPercent = Math.min(100, Math.max(5, progress));

  useEffect(() => {
    const onBoost = () => setBoostFlash(true);
    window.addEventListener("tipjar-boost", onBoost);
    return () => window.removeEventListener("tipjar-boost", onBoost);
  }, []);

  useEffect(() => {
    if (boostFlash) {
      const t = setTimeout(() => setBoostFlash(false), 700);
      return () => clearTimeout(t);
    }
  }, [boostFlash]);

  return (
    <div className="relative mx-auto flex flex-col items-center w-full max-w-[440px] py-6" data-testid="animated-jar">
      {/* NUR NOCH DAS CREST - VERGRÖSSERT */}
      <motion.img 
        src="/tipjar-crest.png?v=5" 
        alt="TipJar" 
        className="w-[220px] h-[220px] md:w-[260px] md:h-[260px] object-contain" 
        style={{ filter: "drop-shadow(0 0 30px rgba(225,255,0,0.5)) drop-shadow(0 0 60px rgba(225,255,0,0.2))" }} 
        animate={{ 
          y: [0, -8, 0],
          scale: boostFlash ? [1, 1.1, 1] : 1
        }} 
        transition={{ 
          y: { duration: 3, repeat: Infinity, ease: "easeInOut" },
          scale: { duration: 0.5, ease: "easeOut" }
        }} 
      />
      
      {/* Optional: Kleiner Progress unter Crest falls du willst - sonst lösch diesen Block */}
      <div className="mt-4 text-center">
        <div className="text-[11px] font-black tracking-widest" style={{ color: currentJar.color }}>{currentJar.name.toUpperCase()} • {fillPercent.toFixed(0)}%</div>
        <div className="text-[9px] text-zinc-500">{credits.toFixed(0)} / {nextCoins} COINS • {idx+1}/30 • {currentJar.tier.toUpperCase()}</div>
      </div>

      {/* Das Jar wurde GELÖSCHT wie gewünscht - war hier */}
    </div>
  );
}
