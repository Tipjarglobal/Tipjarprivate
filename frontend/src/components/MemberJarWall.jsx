import React, { useEffect, useState } from "react";

export default function MemberJarWall({ jars = [] }) {
  const [localJars, setLocalJars] = useState(jars);

  useEffect(() => {
    setLocalJars(jars);
  }, [jars]);

  // Decay: silver first -1/h
  useEffect(() => {
    const interval = setInterval(() => {
      setLocalJars(prev => {
        return prev.map(jar => {
          if (jar.type === 'silver' && jar.value > 0) {
            return { ...jar, value: Math.max(0, jar.value - 1) };
          }
          return jar;
        }).filter(j => j.value > 0);
      });
    }, 3600000); // 1h
    return () => clearInterval(interval);
  }, []);

  const goldJars = localJars.filter(j => j.type === 'gold' || j.coins >= 20).slice(0, 3);
  const silverJars = localJars.filter(j => j.type === 'silver' || j.coins < 20).slice(0, 3);

  // 3 open max
  const displayGold = goldJars.slice(0, 3);
  const displaySilver = silverJars.slice(0, 3);

  return (
    <div className="w-full max-w-5xl mx-auto space-y-3">
      {/* Gold oben */}
      <div className="p-3 rounded-xl bg-gradient-to-br from-yellow-900/20 to-amber-900/20 border border-yellow-500/20">
        <div className="text-[10px] font-bold tracking-widest text-yellow-500 mb-2">GOLD JARS (TOP)</div>
        <div className="grid grid-cols-3 gap-2">
          {displayGold.length > 0 ? displayGold.map((jar, i) => (
            <div key={i} className="h-20 rounded-lg bg-yellow-500/20 border border-yellow-500/30 flex flex-col items-center justify-center">
              <div className="text-[20px]">🏆</div>
              <div className="text-[11px] font-black text-yellow-300">{jar.value || jar.coins || 20}/20</div>
              <div className="text-[9px] text-yellow-500/70">{jar.user || 'Member'}</div>
            </div>
          )) : <div className="col-span-3 text-center text-[11px] text-zinc-600 py-4">Keine Gold Jars - sammle 20/20</div>}
        </div>
      </div>

      {/* Silver unten */}
      <div className="p-3 rounded-xl bg-zinc-900 border border-white/10">
        <div className="text-[10px] font-bold tracking-widest text-zinc-500 mb-2">SILVER JARS (DECAY -1/h) - 3 MAX OPEN</div>
        <div className="grid grid-cols-3 gap-2">
          {displaySilver.length > 0 ? displaySilver.map((jar, i) => (
            <div key={i} className="h-20 rounded-lg bg-zinc-800 border border-white/10 flex flex-col items-center justify-center">
              <div className="text-[20px]">🪙</div>
              <div className="text-[11px] font-bold text-zinc-300">{jar.value || jar.coins || 0}/20</div>
              <div className="text-[9px] text-zinc-500">{jar.user || 'Member'}</div>
            </div>
          )) : <div className="col-span-3 text-center text-[11px] text-zinc-600 py-4">Keine Silver Jars offen</div>}
        </div>
      </div>
    </div>
  );
}
