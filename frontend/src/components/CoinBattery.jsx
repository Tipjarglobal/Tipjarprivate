import React from "react";
import { Zap } from "lucide-react";

// TIPJAR POWER battery. Shows the user's coins out of full power (2500). No "CR" suffix.
// Colour by charge: <25% red, <50% amber, <75% lime, else green.
export default function CoinBattery({ current = 0, max = 2500 }) {
  const cur = Math.max(0, Number(current) || 0);
  const cap = Math.max(1, Number(max) || 2500);
  const pct = Math.min(100, Math.round((cur / cap) * 100));
  const color =
    pct < 25 ? "#FF1E56" : pct < 50 ? "#FFB020" : pct < 75 ? "#E1FF00" : "#00FF94";

  return (
    <div
      data-testid="coin-battery"
      className="w-full max-w-md mx-auto rounded-2xl border border-white/10 bg-[#18181B]/80 backdrop-blur p-4 md:p-5"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Zap size={16} style={{ color }} />
          <span className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-300">TIPJAR POWER</span>
        </div>
        <span data-testid="coin-battery-value" className="font-mono text-sm font-bold" style={{ color }}>
          {cur.toLocaleString()}/{cap.toLocaleString()}
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="relative flex-1 h-7 rounded-md border-2 border-white/25 bg-void/70 overflow-hidden">
          <div
            className="h-full rounded-sm transition-[width] duration-700 ease-out"
            style={{ width: `${pct}%`, backgroundColor: color, boxShadow: `0 0 14px ${color}` }}
            data-testid="coin-battery-fill"
          />
          <span className="absolute inset-0 flex items-center justify-center text-[11px] font-black text-white/90 mix-blend-difference">
            {pct}%
          </span>
        </div>
        <div className="w-1.5 h-4 rounded-r-sm bg-white/25" />
      </div>
    </div>
  );
}
