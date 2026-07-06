import React, { useMemo } from "react";
import { motion } from "framer-motion";

// Signature TipJar centerpiece: a glass jar with coins floating up and down.
const COIN_COLORS = [
  "#E1FF00", "#00FF94", "#FF1E56", "#E1FF00", "#FFFFFF",
  "#00FF94", "#E1FF00", "#FF1E56", "#E1FF00",
];

export default function AnimatedJar() {
  const coins = useMemo(
    () =>
      COIN_COLORS.map((c, i) => ({
        color: c,
        size: 26 + ((i * 7) % 22),
        left: 12 + ((i * 29) % 66),
        delay: (i % 5) * 0.4,
        dur: 2.6 + (i % 4) * 0.6,
        drift: (i % 2 === 0 ? 1 : -1) * (8 + (i % 3) * 6),
        base: 20 + ((i * 23) % 55),
      })),
    []
  );

  return (
    <div className="relative mx-auto" style={{ width: 300, height: 380 }} data-testid="animated-jar">
      {/* volt glow behind */}
      <div
        className="absolute inset-0 blur-3xl opacity-30"
        style={{ background: "radial-gradient(circle at 50% 60%, #E1FF00, transparent 62%)" }}
      />

      {/* lid */}
      <div
        className="absolute left-1/2 -translate-x-1/2 z-20 rounded-t-2xl rounded-b-md"
        style={{
          top: 6, width: 168, height: 34,
          background: "linear-gradient(180deg,#3f3f46,#18181b)",
          border: "2px solid #52525b", boxShadow: "0 6px 18px rgba(0,0,0,0.6)",
        }}
      />
      <div
        className="absolute left-1/2 -translate-x-1/2 z-20"
        style={{ top: 38, width: 150, height: 12, background: "#27272a", borderRadius: 6 }}
      />

      {/* jar body */}
      <div
        className="absolute overflow-hidden z-10"
        style={{
          top: 48, left: 26, right: 26, bottom: 6,
          borderRadius: "22px 22px 42px 42px",
          background: "linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02))",
          border: "2px solid rgba(225,255,0,0.35)",
          boxShadow: "inset 0 0 55px rgba(225,255,0,0.12), inset 0 -20px 40px rgba(0,0,0,0.5), 0 0 40px rgba(225,255,0,0.08)",
          backdropFilter: "blur(6px)",
        }}
      >
        {/* glass shine */}
        <div
          className="absolute top-4 left-5 w-10 rounded-full opacity-40"
          style={{ height: "60%", background: "linear-gradient(180deg,rgba(255,255,255,0.5),transparent)", filter: "blur(3px)" }}
        />

        {/* floating coins */}
        {coins.map((coin, i) => (
          <motion.div
            key={i}
            className="absolute rounded-full flex items-center justify-center font-mono font-bold"
            style={{
              width: coin.size, height: coin.size,
              left: `${coin.left}%`, bottom: `${coin.base}%`,
              background: `radial-gradient(circle at 32% 28%, ${coin.color}, ${coin.color}99)`,
              boxShadow: `0 0 14px ${coin.color}88, inset 0 -3px 6px rgba(0,0,0,0.35)`,
              color: "#09090b", fontSize: coin.size * 0.42,
            }}
            animate={{ y: [0, -coin.drift, 0], x: [0, coin.drift * 0.4, 0] }}
            transition={{ duration: coin.dur, delay: coin.delay, repeat: Infinity, ease: "easeInOut" }}
          >
            €
          </motion.div>
        ))}

        {/* TipJar crest logo */}
        <img
          src="/tipjar-crest.png?v=2"
          alt="TipJar"
          draggable="false"
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-30 w-36 h-36 object-contain"
          style={{ filter: "drop-shadow(0 0 22px rgba(225,255,0,0.45))" }}
        />
      </div>
    </div>
  );
}
