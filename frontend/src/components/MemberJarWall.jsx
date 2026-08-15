import React, { useEffect, useState } from "react";
import api from "../api";

// 30-Jar System (tipjar.md FINAL): Carton Box 80 statt Cork, Starter = Common Glass 40.
// fill = received_credits + credits. getJarForCredits(fill) -> höchstes erreichtes Material.
const MATERIALS = [
  // TIER 1 COMMON 40-80
  { name: "Common Glass", min: 40, tier: "COMMON" },
  { name: "Wood", min: 50, tier: "COMMON" },
  { name: "Stone", min: 60, tier: "COMMON" },
  { name: "Clay", min: 70, tier: "COMMON" },
  { name: "Bamboo", min: 75, tier: "COMMON" },
  { name: "Carton Box", min: 80, tier: "COMMON" },
  // TIER 2 UNCOMMON 90-170
  { name: "Bronze", min: 90, tier: "UNCOMMON" },
  { name: "Iron", min: 110, tier: "UNCOMMON" },
  { name: "Tin", min: 130, tier: "UNCOMMON" },
  { name: "Copper", min: 150, tier: "UNCOMMON" },
  { name: "Aluminum", min: 160, tier: "UNCOMMON" },
  { name: "Brass", min: 170, tier: "UNCOMMON" },
  // TIER 3 RARE 180-280
  { name: "Steel", min: 180, tier: "RARE" },
  { name: "Silver", min: 200, tier: "RARE" },
  { name: "Nickel", min: 220, tier: "RARE" },
  { name: "Chrome", min: 240, tier: "RARE" },
  { name: "Carbon", min: 260, tier: "RARE" },
  { name: "Crystal", min: 280, tier: "RARE" },
  // TIER 4 EPIC 300-420
  { name: "Gold", min: 300, tier: "EPIC" },
  { name: "Platinum", min: 350, tier: "EPIC" },
  { name: "Titanium", min: 380, tier: "EPIC" },
  { name: "Ruby", min: 400, tier: "EPIC" },
  { name: "Sapphire", min: 410, tier: "EPIC" },
  { name: "Emerald", min: 420, tier: "EPIC" },
  // TIER 5 LEGENDARY 450-500
  { name: "Diamond", min: 450, tier: "LEGENDARY" },
  { name: "Obsidian", min: 475, tier: "LEGENDARY" },
  { name: "Galaxy", min: 500, tier: "LEGENDARY" },
  { name: "Void", min: 500, tier: "LEGENDARY" },
  // TIER 6 MYTHIC 500
  { name: "Nebula", min: 500, tier: "MYTHIC" },
  { name: "Infinity", min: 500, tier: "MYTHIC" },
];

const TIER_STYLE = {
  COMMON: { ring: "border-zinc-600", text: "text-zinc-300", glow: "" },
  UNCOMMON: { ring: "border-emerald-500/60", text: "text-emerald-400", glow: "shadow-[0_0_10px_rgba(16,185,129,0.25)]" },
  RARE: { ring: "border-sky-500/60", text: "text-sky-400", glow: "shadow-[0_0_10px_rgba(56,189,248,0.3)]" },
  EPIC: { ring: "border-fuchsia-500/60", text: "text-fuchsia-400", glow: "shadow-[0_0_12px_rgba(217,70,239,0.35)]" },
  LEGENDARY: { ring: "border-amber-400/70", text: "text-amber-300", glow: "shadow-[0_0_16px_rgba(251,191,36,0.45)]" },
  MYTHIC: { ring: "border-pink-400/80", text: "text-pink-300", glow: "shadow-[0_0_20px_rgba(244,114,182,0.55)]" },
};

export function getJarForCredits(fill) {
  let cur = null;
  for (const m of MATERIALS) {
    if (fill >= m.min) cur = m;
  }
  return cur; // null wenn < 40 (noch kein Jar)
}

export default function MemberJarWall() {
  const [members, setMembers] = useState([]);

  useEffect(() => {
    api.get("/users/public-jars?limit=20")
      .then((r) => setMembers((r.data?.members || []).slice(0, 20)))
      .catch(() => setMembers([]));
  }, []);

  if (!members.length) return null;

  return (
    <div data-testid="member-jar-wall" className="w-full max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-2 px-1">
        <h3 className="text-[11px] font-black tracking-widest text-zinc-400">🏆 MEMBER JARS</h3>
        <span className="text-[10px] text-zinc-600">30 Materialien · Common Glass → Infinity</span>
      </div>
      <div className="grid grid-cols-3 sm:grid-cols-5 lg:grid-cols-10 gap-2">
        {members.map((m, i) => {
          const fill = (Number(m.received_credits) || 0) + (Number(m.credits) || 0);
          const jar = getJarForCredits(fill);
          const st = jar ? TIER_STYLE[jar.tier] : { ring: "border-white/10", text: "text-zinc-500", glow: "" };
          return (
            <div
              key={m.username || i}
              data-testid={`member-jar-${i}`}
              className={`rounded-xl bg-zinc-900 border ${st.ring} ${st.glow} p-2.5 flex flex-col items-center text-center transition-transform hover:scale-[1.03]`}
            >
              <span className="text-lg leading-none">🫙</span>
              <span className="mt-1 text-[11px] font-bold text-white truncate w-full">{m.username}</span>
              <span className={`text-[9px] font-black ${st.text}`}>{jar ? jar.name : "—"}</span>
              <span className="text-[9px] text-zinc-500 font-mono">{fill.toLocaleString()}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
