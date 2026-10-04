import React, { useState, useEffect } from "react";

// VON: Sich gegenseitig beschenken
// BIS: Noch keine Spenden - sei der Erste!
// RASTER 6 — Batterie. GEILER LOOK BLEIBT: CoinBattery + AnimatedCoins + MemberJarWall
// jetzt als INTERNE Funktionen in dieser EINEN Schale (kein Import).
// 100% inline-style, kein Tailwind, kein framer-motion. Animation via CSS @keyframes.

function CoinBatteryVisual({ coins = 0 }) {
  const pct = Math.min((coins / 2500) * 100, 100);
  const color = pct < 25 ? "#ef4444" : pct < 50 ? "#f59e0b" : pct < 75 ? "#84cc16" : "#22c55e";
  return (
    <div style={{ padding: "12px 0" }}>
      <div style={{ height: 28, backgroundColor: "#27272a", borderRadius: 999, overflow: "hidden", border: "1px solid #3f3f46" }}>
        <div style={{ width: `${pct}%`, height: "100%", backgroundColor: color, transition: "width 0.6s ease", boxShadow: `0 0 12px ${color}` }} />
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 12, color: "#a1a1aa" }}>
        <span>{coins}/2500</span>
        <span style={{ color, fontWeight: 900 }}>{pct >= 100 ? "VOLL - CASE ÖFFNEN!" : `${pct.toFixed(1)}%`}</span>
      </div>
    </div>
  );
}

function AnimatedCoinsVisual({ count = 3 }) {
  return (
    <div style={{ display: "flex", gap: 8, justifyContent: "center", padding: 12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ width: 32, height: 32, borderRadius: "50%", background: "radial-gradient(circle at 30% 30%, #fde047, #eab308)", border: "2px solid #a16207", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 14, color: "#78350f", boxShadow: "0 2px 8px rgba(234,179,8,0.5)", animation: `tjBounce 0.6s ${i * 0.1}s infinite alternate` }}>
          $
        </div>
      ))}
    </div>
  );
}

function MemberJarWallVisual() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(60px, 1fr))", gap: 8, padding: 12 }}>
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} style={{ width: 56, height: 56, borderRadius: 16, backgroundColor: "#27272a", border: "1px solid #3f3f46", display: "flex", alignItems: "center", justifyContent: "center", color: "#a1a1aa" }}>
          {i}
        </div>
      ))}
    </div>
  );
}

export default function Raster6_Batterie({ coins = 1247 }) {
  return (
    <section data-testid="raster-6" data-i18n="raster6" style={{ padding: "24px 16px", backgroundColor: "#09090b", borderTop: "1px solid #27272a", borderBottom: "1px solid #27272a" }}>
      {/* CSS @keyframes inline statt framer-motion (Vite-sicher) */}
      <style>{`@keyframes tjBounce { from { transform: translateY(0); } to { transform: translateY(-8px); } }`}</style>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        <h2 style={{ fontSize: 24, fontWeight: 900, color: "#fafafa", marginBottom: 4 }}>Sich gegenseitig beschenken</h2>
        <p style={{ fontSize: 14, color: "#a1a1aa", marginBottom: 16 }}>Je mehr Coins du sammelst, desto mehr Cases kannst du öffnen. Batterie füllt sich pro Tipp.</p>

        <CoinBatteryVisual coins={coins} />
        <AnimatedCoinsVisual count={5} />
        <MemberJarWallVisual />

        <div style={{ marginTop: 16, padding: 12, borderRadius: 12, backgroundColor: "#18181b", border: "1px dashed #3f3f46", textAlign: "center", color: "#71717a", fontSize: 13 }}>
          Noch keine Spenden - sei der Erste!
        </div>
        <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
          <button style={{ flex: 1, padding: "12px", borderRadius: 12, backgroundColor: "#a855f7", color: "white", fontWeight: 900, border: "none", cursor: "pointer" }}>Case öffnen</button>
          <button style={{ flex: 1, padding: "12px", borderRadius: 12, backgroundColor: "#27272a", color: "#fafafa", fontWeight: 700, border: "1px solid #3f3f46", cursor: "pointer" }}>JarDex</button>
        </div>
      </div>
    </section>
  );
}
// TODO Meta AI/Termius: Handler/Logik verdrahten — Struktur bleibt, Farben inline, Look bleibt.
