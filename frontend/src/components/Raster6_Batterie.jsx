import React from "react";
import { Zap, Gift } from "lucide-react";

// ============================================================
// RASTER 6 — BATTERIE ("Sich gegenseitig beschenken")
// VON: Header "Sich gegenseitig beschenken"
// BIS: Ende Leaderboard "Noch keine Spenden - sei der Erste!"
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 960, margin: "0 auto" };

export default function Raster6_Batterie({ coins = 0, max = 2500, onFeed = () => {}, onGift = () => {} }) {
  const pct = Math.min(100, Math.round((coins / max) * 100));
  const redBtn = { flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 8, borderRadius: 999, background: "#dc2626", color: "#fff", fontWeight: 800, padding: "14px 16px", border: "none", cursor: "pointer", fontSize: 14 };
  return (
    <section style={{ padding: 16 }} data-testid="raster-6" data-i18n="raster6">
      <div style={WRAP}>
        <h2 style={{ fontSize: 22, fontWeight: 900, color: "#fff", margin: "0 0 8px" }} data-testid="r6-title">Sich gegenseitig beschenken</h2>
        <p style={{ fontSize: 13, color: "#a1a1aa", lineHeight: 1.6, margin: "0 0 4px" }}>
          Die TipJar Batterie ist das Herz. Klicke sie an und feede Credits rein, wenn du welche hast. Auszahlung erst ab 2000+ in der Batterie.
          Egal ob du einen anderen Tipper beschenkst oder direkt die Batterie – die Batterie bekommt immer Energie dazu. Schenken = Energie = Cash.
        </p>
        <p style={{ fontSize: 12, color: "#71717a", margin: "0 0 12px" }}>Sich gegenseitig beschenken – Die Batterie lädt durch euch</p>

        <div style={{ border: "1px solid #dc2626", borderRadius: 16, padding: 16, marginBottom: 12 }} data-testid="r6-battery">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
            <span style={{ fontWeight: 900, color: "#fff" }}>⚡ Batterie - COINS</span>
            <span style={{ fontSize: 11, color: "#f87171", fontWeight: 700 }}>Auszahlung ab 2000+ · VOLL 2500</span>
          </div>
          <div style={{ height: 36, borderRadius: 999, background: "#27272A", overflow: "hidden", position: "relative" }}>
            <div style={{ height: "100%", width: `${pct}%`, background: "#dc2626", transition: "width 0.4s" }} />
            <span style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 800, color: "#fff" }}>{coins} / {max} COINS</span>
          </div>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          <button onClick={onFeed} style={redBtn} data-testid="r6-feed"><Zap size={16} /> Credits feeden Batterie</button>
          <button onClick={onGift} style={redBtn} data-testid="r6-gift"><Gift size={16} /> Spendieren</button>
        </div>

        <div style={{ marginTop: 16 }} data-testid="r6-leaderboard">
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            {["Diese Woche", "Gesamter Zeitraum", "Erhalten"].map((tab, i) => (
              <span key={tab} style={{ fontSize: 12, fontWeight: 700, padding: "6px 12px", borderRadius: 999, background: i === 0 ? "#fff" : "transparent", color: i === 0 ? "#000" : "#a1a1aa", border: "1px solid #27272A" }}>{tab}</span>
            ))}
          </div>
          <p style={{ fontSize: 10, letterSpacing: 2, textTransform: "uppercase", color: "#71717a", margin: "8px 0" }}>Diese Woche – Leaderboard</p>
          <p style={{ fontSize: 13, color: "#71717a", margin: 0 }}>Noch keine Spenden – sei der Erste!</p>
        </div>
      </div>
    </section>
  );
}
