import React, { useEffect, useState } from "react";
import api from "../api";

// Owner 2026-08: public Member Jar Wall — 20 materials from Wood to Galaxy, by jar "fill"
// (received_credits + credits). Higher contribution → rarer material.
const MATERIALS = [
  { name: "Wood", min: 0, grad: ["#6b4423", "#8a5a2b"], glow: "#8a5a2b" },
  { name: "Stone", min: 50, grad: ["#5a5a5a", "#7d7d7d"], glow: "#7d7d7d" },
  { name: "Bronze", min: 120, grad: ["#7a4a1e", "#cd7f32"], glow: "#cd7f32" },
  { name: "Iron", min: 250, grad: ["#43464b", "#8a8f98"], glow: "#8a8f98" },
  { name: "Copper", min: 400, grad: ["#7a3b1a", "#e07b39"], glow: "#e07b39" },
  { name: "Silver", min: 600, grad: ["#8a8f98", "#e6e8ec"], glow: "#e6e8ec" },
  { name: "Gold", min: 900, grad: ["#8a6d10", "#ffd447"], glow: "#ffd447" },
  { name: "Platinum", min: 1300, grad: ["#9fb0b5", "#e5f0f2"], glow: "#e5f0f2" },
  { name: "Emerald", min: 1800, grad: ["#065f46", "#10d98e"], glow: "#10d98e" },
  { name: "Ruby", min: 2500, grad: ["#7a0c2e", "#ff2d6b"], glow: "#ff2d6b" },
  { name: "Sapphire", min: 3500, grad: ["#0b2a6b", "#3b82f6"], glow: "#3b82f6" },
  { name: "Amethyst", min: 5000, grad: ["#4a1d73", "#a855f7"], glow: "#a855f7" },
  { name: "Diamond", min: 7000, grad: ["#0e7490", "#67e8f9"], glow: "#67e8f9" },
  { name: "Obsidian", min: 10000, grad: ["#0a0a0a", "#3a3a3a"], glow: "#5b5b5b" },
  { name: "Titanium", min: 15000, grad: ["#3a4a5a", "#9fb8cc"], glow: "#9fb8cc" },
  { name: "Plasma", min: 22000, grad: ["#7a0f5a", "#ff4fd8"], glow: "#ff4fd8" },
  { name: "Neon", min: 32000, grad: ["#0f5a3a", "#E1FF00"], glow: "#E1FF00" },
  { name: "Cosmic", min: 50000, grad: ["#1a0f5a", "#7c5cff"], glow: "#7c5cff" },
  { name: "Aurora", min: 75000, grad: ["#0f5a5a", "#00FF94"], glow: "#00FF94" },
  { name: "Galaxy", min: 120000, grad: ["#1b0a3a", "#b14cff"], glow: "#b14cff" },
];

function materialFor(fill) {
  let m = MATERIALS[0];
  for (const mat of MATERIALS) if (fill >= mat.min) m = mat;
  return m;
}

function Jar({ member }) {
  const mat = materialFor(member.fill || 0);
  const g = `linear-gradient(160deg, ${mat.grad[0]}, ${mat.grad[1]})`;
  return (
    <div className="flex flex-col items-center gap-1.5" data-testid={`member-jar-${member.username}`}>
      <div className="relative w-16 h-20 flex items-end justify-center">
        {/* lid */}
        <div className="absolute -top-1 w-11 h-2.5 rounded-t-md border border-white/20" style={{ background: g }} />
        {/* jar body */}
        <div
          className="w-14 h-16 rounded-b-2xl rounded-t-md border border-white/15 relative overflow-hidden"
          style={{ background: g, boxShadow: `0 0 12px ${mat.glow}55` }}
        >
          <div className="absolute inset-0 opacity-30" style={{ background: "linear-gradient(115deg, rgba(255,255,255,.55), transparent 45%)" }} />
        </div>
      </div>
      <span className="text-[10px] font-bold text-white/90 truncate max-w-[72px]">{member.username}</span>
      <span className="text-[9px] font-semibold uppercase tracking-wider" style={{ color: mat.glow }}>{mat.name}</span>
    </div>
  );
}

export default function MemberJarWall() {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let alive = true;
    api.get("/users/public-jars?limit=40")
      .then(({ data }) => { if (alive) setMembers(data.members || []); })
      .catch(() => { if (alive) setMembers([]); })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  return (
    <div data-testid="member-jar-wall" className="w-full max-w-4xl mx-auto mt-6">
      <div className="flex items-center justify-center gap-2 mb-4">
        <span className="text-xs font-bold uppercase tracking-[0.25em] text-volt">Member Jars</span>
      </div>
      {loading ? (
        <p className="text-center text-zinc-500 text-sm">Lade Member…</p>
      ) : members.length === 0 ? (
        <p className="text-center text-zinc-500 text-sm">Noch keine Member-Jars — lade Credits, um deinen Jar zu füllen.</p>
      ) : (
        <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-4 justify-items-center">
          {members.map((m) => <Jar key={m.username} member={m} />)}
        </div>
      )}
    </div>
  );
}
