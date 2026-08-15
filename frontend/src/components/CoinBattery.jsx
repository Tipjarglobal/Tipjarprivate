import React, { useEffect, useState } from "react";
import { useI18n } from "../i18n";

const TOTAL_COINS = 2500;   // 2500 COINS = VOLL
const FLOOR_COINS = 125;    // 5% — fällt NIEMALS darunter
const PAYOUT_MIN = 2000;    // Auszahlung ab 2000

// FETTE LANGE Münz-Batterie über die ganze Breite: [ |||||||||| ]▶ mit Nupsi.
export default function CoinBattery({ current = 0, max = TOTAL_COINS }) {
  const i18n = useI18n();
  const t = (k, fb) => (i18n && i18n.t && i18n.t(k) !== k ? i18n.t(k) : fb);
  const [flash, setFlash] = useState(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onBoost = (e) => {
      const add = (e && e.detail && (e.detail.coins || e.detail.power)) || 10;
      setFlash(`+${add}`);
      const to = setTimeout(() => setFlash(null), 3500);
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
  // Farben exakt: <25% rot, <50% amber, <75% lime, >=75% grün
  const color = pct >= 75 ? "#22c55e" : pct >= 50 ? "#D4FF32" : pct >= 25 ? "#FFD447" : "#ff4444";
  const canPayout = coins >= PAYOUT_MIN;
  const SEGMENTS = 10;
  const filled = Math.max(1, Math.round((pct / 100) * SEGMENTS));

  return (
    <div
      data-testid="coin-battery"
      className="w-full max-w-5xl mx-auto mb-4 rounded-2xl bg-zinc-900 border border-white/10 p-4"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-black tracking-widest text-zinc-300">
            ⚡ {t("battery.title", "MÜNZ-BATTERIE")}
          </span>
          {flash && (
            <span data-testid="coin-battery-boost" className="text-[11px] font-black text-black bg-[#FFD447] px-2.5 py-0.5 rounded-full animate-bounce shadow-lg">
              {flash} 🪙
            </span>
          )}
        </div>
        <span className="text-[13px] font-black" style={{ color }} data-testid="coin-battery-amount">
          {coins.toLocaleString()} <span className="text-zinc-500 font-bold text-[11px]">COINS</span>
        </span>
      </div>

      {/* FETTE LANGE Batterie: Body flex-1 volle Breite + Nupsi */}
      <div className="flex items-center gap-1">
        <div
          className="flex-1 flex items-center gap-1 h-10 px-1.5 bg-black rounded-lg border-2 border-white/25"
          data-testid="coin-battery-body"
        >
          {Array.from({ length: SEGMENTS }).map((_, i) => (
            <div
              key={i}
              className="flex-1 h-6 rounded-[3px] transition-all duration-500"
              style={{
                background: i < filled ? color : "rgba(255,255,255,0.10)",
                boxShadow: i < filled ? `0 0 10px ${color}, 0 0 3px ${color}` : "none",
              }}
            />
          ))}
        </div>
        {/* Nupsi */}
        <div className="w-4 h-6 rounded-r-md" style={{ background: color, boxShadow: `0 0 10px ${color}` }} />
      </div>

      <div className="flex items-center justify-between mt-2">
        <p className="text-[10px] text-zinc-500 font-semibold">
          {t("battery.full", "2500 COINS = VOLL — NIEMALS UNTER 125")}
        </p>
        <p className="text-[10px] font-bold" style={{ color: canPayout ? "#22c55e" : "#71717a" }} data-testid="coin-battery-payout">
          {canPayout ? t("battery.payoutReady", "Auszahlung bereit") : `${PAYOUT_MIN}+ ${t("battery.payoutShort", "für Auszahlung")}`}
        </p>
      </div>
    </div>
  );
}
