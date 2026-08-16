import React from "react";

export default function AnimatedJar() {
  return (
    <div className="relative mx-auto flex flex-col items-center w-full max-w-[480px] py-8" data-testid="animated-jar">
      {/* DAS KLEINE SCHWEBENDE LOGO - JETZT GROSS UND ALLEINE - KEIN SCHWEBEN, KEIN JAR */}
      <img
        src="/tipjar-crest.png?v=5"
        alt="TipJar"
        className="w-[340px] h-[340px] md:w-[440px] md:h-[440px] lg:w-[480px] lg:h-[480px] object-contain select-none"
        style={{ filter: "drop-shadow(0 0 30px rgba(225,255,0,0.4))" }}
      />
    </div>
  );
}

// Behält die JAR_DEFS für andere Komponenten die es importieren (z.B. JarDex, MemberJarWall)
export const JAR_DEFS = [
  { id: "common_glass", name: "Common Glass", coins: 40, color: "#e5e7eb", tier: "common", graphic: "/jars/graphic_common_glass_closed_front.png" },
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
  { id: "gold", name: "Gold", coins: 300, color: "#facc15", tier: "epic", graphic: "/jars/g_ruby_closed.png", isLuxury: true },
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

export function getJarForCredits(c) {
  let best = JAR_DEFS[0];
  for (const j of JAR_DEFS) if (c >= j.coins) best = j;
  return best;
}
