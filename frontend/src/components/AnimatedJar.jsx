import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useAuth } from "../auth";

// FINAL 15.08.2026 - GEMAPPT AUF DEINE EXISTIERENDEN PNGs aus Screenshots
// Du hast laut Screenshots: g_aluminum_closed, g_bronze_closed, g_chrome_closed, g_common_open_top, g_copper_closed, g_cosmic_closed, g_crystal_closed, g_diamond_closed, g_emerald_closed, g_frosted_closed, g_galaxy2_closed, g_gold_open_top, g_infinity_closed, g_nebula_closed, g_obsidian_closed, g_platinum_closed, g_ruby_closed, g_sapphire_closed, g_steel_closed, g_tin_closed, g_titanium_closed, g_void_closed, graphic_common_glass_closed_front, graphic_common_glass_open_top

const JAR_DEFS = [
  // TIER 1 COMMON 40-80 - nutzt graphic_common_glass_* wo vorhanden
  { id: "common_glass", name: "Common Glass", coins: 40, seal: 2, color: "#e5e7eb", tier: "common", minCredits: 0, graphic: "/jars/graphic_common_glass_closed_front.png", graphicOpen: "/jars/g_common_open_top.png" },
  { id: "wood", name: "Wood", coins: 50, seal: 3, color: "#92400e", tier: "common", minCredits: 40, graphic: "/jars/g_bronze_closed.png", graphicOpen: "/jars/g_wood_open_top.png" },
  { id: "stone", name: "Stone", coins: 60, seal: 3, color: "#78716c", tier: "common", minCredits: 50, graphic: "/jars/g_tin_closed.png", graphicOpen: "/jars/g_stone_open_top.png" },
  { id: "clay", name: "Clay", coins: 70, seal: 4, color: "#a16207", tier: "common", minCredits: 60, graphic: "/jars/g_bronze_closed.png", graphicOpen: "/jars/g_clay_open_top.png" },
  { id: "bamboo", name: "Bamboo", coins: 75, seal: 4, color: "#65a30d", tier: "common", minCredits: 70, graphic: "/jars/g_steel_closed.png", graphicOpen: "/jars/g_bamboo_open_top.png" },
  { id: "carton_box", name: "Carton Box", coins: 80, seal: 4, color: "#d6c7a5", tier: "common", minCredits: 75, graphic: "/jars/g_aluminum_closed.png", graphicOpen: "/jars/g_carton_box_open_top.png" },
  // TIER 2 UNCOMMON 90-170 - nutzt existierende closed
  { id: "bronze", name: "Bronze", coins: 90, seal: 5, color: "#b45309", tier: "uncommon", minCredits: 80, graphic: "/jars/g_bronze_closed.png", graphicOpen: "/jars/g_bronze_open_top.png" },
  { id: "iron", name: "Iron", coins: 110, seal: 6, color: "#57534e", tier: "uncommon", minCredits: 90, graphic: "/jars/g_tin_closed.png", graphicOpen: "/jars/g_iron_open_top.png" },
  { id: "tin", name: "Tin", coins: 130, seal: 7, color: "#a1a1aa", tier: "uncommon", minCredits: 110, graphic: "/jars/g_tin_closed.png", graphicOpen: "/jars/g_tin_open_top.png" },
  { id: "copper", name: "Copper", coins: 150, seal: 8, color: "#c2410c", tier: "uncommon", minCredits: 130, graphic: "/jars/g_copper_closed.png", graphicOpen: "/jars/g_copper_open_top.png" },
  { id: "aluminum", name: "Aluminum", coins: 160, seal: 8, color: "#d4d4d8", tier: "uncommon", minCredits: 150, graphic: "/jars/g_aluminum_closed.png", graphicOpen: "/jars/g_aluminum_open_top.png" },
  { id: "brass", name: "Brass", coins: 170, seal: 9, color: "#ca8a04", tier: "uncommon", minCredits: 160, graphic: "/jars/g_bronze_closed.png", graphicOpen: "/jars/g_brass_open_top.png" },
  // TIER 3 RARE 180-280
  { id: "steel", name: "Steel", coins: 180, seal: 9, color: "#71717a", tier: "rare", minCredits: 170, graphic: "/jars/g_steel_closed.png", graphicOpen: "/jars/g_steel_open_top.png" },
  { id: "silver", name: "Silver", coins: 200, seal: 10, color: "#e4e4e7", tier: "rare", minCredits: 180, graphic: "/jars/g_chrome_closed.png", graphicOpen: "/jars/g_silver_open_top.png" },
  { id: "nickel", name: "Nickel", coins: 220, seal: 11, color: "#a8a29e", tier: "rare", minCredits: 200, graphic: "/jars/g_chrome_closed.png", graphicOpen: "/jars/g_nickel_open_top.png" },
  { id: "chrome", name: "Chrome", coins: 240, seal: 12, color: "#f4f4f5", tier: "rare", minCredits: 220, graphic: "/jars/g_chrome_closed.png", graphicOpen: "/jars/g_chrome_open_top.png" },
  { id: "carbon", name: "Carbon", coins: 260, seal: 13, color: "#27272a", tier: "rare", minCredits: 240, graphic: "/jars/g_obsidian_closed.png", graphicOpen: "/jars/g_carbon_open_top.png" },
  { id: "crystal", name: "Crystal", coins: 280, seal: 14, color: "#06b6d4", tier: "rare", minCredits: 260, graphic: "/jars/g_crystal_closed.png", graphicOpen: "/jars/g_crystal_open_top.png" },
  // TIER 4 EPIC 300-420
  { id: "gold", name: "Gold", coins: 300, seal: 15, color: "#facc15", tier: "epic", minCredits: 280, graphic: "/jars/g_gold_open_top.png", graphicOpen: "/jars/g_gold_open_top.png", isLuxury: true },
  { id: "platinum", name: "Platinum", coins: 350, seal: 18, color: "#e7e5e4", tier: "epic", minCredits: 300, graphic: "/jars/g_platinum_closed.png", graphicOpen: "/jars/g_platinum_open_top.png", isLuxury: true },
  { id: "titanium", name: "Titanium", coins: 380, seal: 19, color: "#a1a1aa", tier: "epic", minCredits: 350, graphic: "/jars/g_titanium_closed.png", graphicOpen: "/jars/g_titanium_open_top.png", isLuxury: true },
  { id: "ruby", name: "Ruby", coins: 400, seal: 20, color: "#dc2626", tier: "epic", minCredits: 380, graphic: "/jars/g_ruby_closed.png", graphicOpen: "/jars/g_ruby_open_top.png", isLuxury: true },
  { id: "sapphire", name: "Sapphire", coins: 410, seal: 21, color: "#2563eb", tier: "epic", minCredits: 400, graphic: "/jars/g_sapphire_closed.png", graphicOpen: "/jars/g_sapphire_open_top.png", isLuxury: true },
  { id: "emerald", name: "Emerald", coins: 420, seal: 21, color: "#16a34a", tier: "epic", minCredits: 410, graphic: "/jars/g_emerald_closed.png", graphicOpen: "/jars/g_emerald_open_top.png", isLuxury: true },
  // TIER 5 LEGENDARY 450-500
  { id: "diamond", name: "Diamond", coins: 450, seal: 23, color: "#22d3ee", tier: "legendary", minCredits: 420, graphic: "/jars/g_diamond_closed.png", graphicOpen: "/jars/g_diamond_open_top.png", isLuxury: true },
  { id: "obsidian", name: "Obsidian", coins: 475, seal: 24, color: "#18181b", tier: "legendary", minCredits: 450, graphic: "/jars/g_obsidian_closed.png", graphicOpen: "/jars/g_obsidian_open_top.png", isLuxury: true },
  { id: "galaxy", name: "Galaxy", coins: 500, seal: 25, color: "#7c3aed", tier: "legendary", minCredits: 475, graphic: "/jars/g_galaxy2_closed.png", graphicOpen: "/jars/g_galaxy2_open_top.png", isLuxury: true },
  { id: "void", name: "Void", coins: 500, seal: 25, color: "#000000", tier: "legendary", minCredits: 475, graphic: "/jars/g_void_closed.png", graphicOpen: "/jars/g_void_open_top.png", isLuxury: true },
  // TIER 6 MYTHIC 500
  { id: "nebula", name: "Nebula", coins: 500, seal: 25, color: "#ec4899", tier: "mythic", minCredits: 500, graphic: "/jars/g_nebula_closed.png", graphicOpen: "/jars/g_nebula_open_top.png", isLuxury: true },
  { id: "infinity", name: "Infinity", coins: 500, seal: 25, color: "#f0f9ff", tier: "mythic", minCredits: 500, graphic: "/jars/g_infinity_closed.png", graphicOpen: "/jars/g_infinity_open_top.png", isLuxury: true },
];

function getJarForCredits(c = 0) { 
  let best = JAR_DEFS[0]; 
  for (const j of JAR_DEFS) {
    if (c >= j.minCredits) best = j;
    else break;
  }
  return best; 
}

export { JAR_DEFS, getJarForCredits };

export default function AnimatedJar() {
  const { user } = useAuth();
  const [boostFlash, setBoostFlash] = useState(false);
  const credits = (user?.received_credits || 0) + (user?.credits || 0);
  const currentJar = getJarForCredits(credits);
  const idx = JAR_DEFS.findIndex(j => j.id === currentJar.id);
  const nextJar = JAR_DEFS[idx + 1];
  const prevCoins = currentJar.minCredits;
  const nextCoins = nextJar ? nextJar.minCredits : currentJar.coins + 100;
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
      <motion.img 
        src="/tipjar-crest.png?v=5" 
        alt="TipJar" 
        className="w-[220px] h-[220px] md:w-[260px] md:h-[260px] object-contain" 
        style={{ filter: "drop-shadow(0 0 30px rgba(225,255,0,0.5)) drop-shadow(0 0 60px rgba(225,255,0,0.2))" }} 
        animate={{ y: [0, -8, 0], scale: boostFlash ? [1, 1.1, 1] : 1 }} 
        transition={{ y: { duration: 3, repeat: Infinity, ease: "easeInOut" }, scale: { duration: 0.5, ease: "easeOut" } }} 
      />
    </div>
  );
}
