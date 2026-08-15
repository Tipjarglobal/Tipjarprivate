import React, { useEffect, useState } from "react";
import { useI18n } from "../i18n";

const TOTAL_COINS = 2500;   // 2500 COINS total
const FLOOR_COINS = 125;    // 5% floor
const PAYOUT_MIN = 2000;    // payout ab 2000 COINS

// Echte Batterie [ ||||| ]> mit Nupsi rechts. Anzeige in COINS, nicht CR.
export default function CoinBattery({ current = 0, max = TOTAL_COINS }) {
  const i18n = useI18n();
  const t = (k, fb) => (i18n && i18n.t && i18n.t(k) !== k ? i18n.t(k) : fb);
  const [flash, setFlash] = useState(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onBoost = (e) => {
      const add = (e && e.detail && (e.detail.coins || e.detail.power)) || 5;
      setFlash(`+${add}`);
      const to = setTimeout(() => setFlash(null), 3000);
      return () => clearTimeout(to);
    };
    window.addEventListener("tipjar-boost", onBoost);
    window.addEventListener("tipjar-boost-gold", onBoost);
    return () => {
      window.removeEventListener("tipjar-boost", onBoost);
      window.removeEventListener("tipjar-boost-gold", onBoost);
    };
  }, []);

  const coins = Math.max(FLOOR_COINS, Math.min(max, Math.round(Number(current) || 0)));
  const pct = Math.round((coins / max) * 100);
  const color = pct >= 75 ? "#22c55e" : pct >= 50 ? "#D4FF32" : pct >= 25 ? "#FFD447" : "#ff4444";
  const canPayout = coins >= PAYOUT_MIN;
  const SEGMENTS = 5;
  const filled = Math.max(1, Math.round((pct / 100) * SEGMENTS));

  return (
    <div
      data-testid="coin-battery"
      className="w-full max-w-5xl mx-auto mb-4 p-3 rounded-xl bg-zinc-900 border border-white/10 flex items-center justify-between relative overflow-hidden"
    >
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-black border border-white/10 flex items-center justify-center text-[12px]">⚡</div>
        <div>
          <div className="text-[10px] font-bold tracking-widest text-zinc-500 flex items-center gap-2">
            {t("battery.title", "COIN BATTERY")}
            {flash && (
              <span data-testid="coin-battery-boost" className="text-[10px] font-black text-black bg-[#D4FF32] px-2 py-0.5 rounded-full animate-bounce">
                {flash}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 mt-1">
            {/* Echte Batterie: Body [ ||||| ] + Nupsi */}
            <div className="flex items-center" data-testid="coin-battery-body">
              <div className="flex items-center gap-[2px] h-4 px-[3px] bg-black rounded-[3px] border border-white/25">
                {Array.from({ length: SEGMENTS }).map((_, i) => (
                  <div
                    key={i}
                    className="w-1.5 h-2.5 rounded-[1px] transition-all duration-500"
                    style={{ background: i < filled ? color : "rgba(255,255,255,0.12)" }}
                  />
                ))}
              </div>
              <div className="w-[3px] h-2 rounded-r-sm ml-[1px]" style={{ background: color }} />
            </div>
            <span className="text-[11px] font-black" style={{ color }} data-testid="coin-battery-amount">
              {coins} <span className="text-zinc-500 font-bold">COINS</span>
            </span>
          </div>
        </div>
      </div>
      <div className="text-right">
        <div className="text-[10px] text-zinc-500" data-testid="coin-battery-total">{coins}/{max} COINS</div>
        <div className="text-[9px] font-bold" style={{ color: canPayout ? "#22c55e" : "#71717a" }} data-testid="coin-battery-payout">
          {canPayout ? t("battery.payoutReady", "Payout ready") : `${PAYOUT_MIN}+ ${t("battery.payoutShort", "to payout")}`}
        </div>
      </div>
    </div>
  );
}
