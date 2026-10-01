import React from "react";

// ============================================================
// RASTER 1 — PARTNER-PILLEN (ALLES BIS UNTER ORANGE SGCASINO)
// VON: "Deine Partner auf TipJar..." + RENT 2 PILLS 300€ + RENT A PILL 150€ + WAZAMBA + Casino-Grid
// BIS: Ende SGCASINO orange — vor roter Trennlinie "Supporte TipJar..."
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 960, margin: "0 auto" };
const SEC = { padding: "16px" };
const GRID = [
  { name: "BANKONBET", bg: "#16a34a", fg: "#fff" },
  { name: "ROBOCAT", bg: "#dc2626", fg: "#fff" },
  { name: "PISTOLO", bg: "#eab308", fg: "#000" },
  { name: "5GRINGOS", bg: "#92400e", fg: "#fff" },
  { name: "20BET", bg: "#16a34a", fg: "#fff" },
  { name: "BETSCORE", bg: "#eab308", fg: "#000" },
  { name: "SGCASINO", bg: "#f97316", fg: "#000" },
];

export default function Raster1_PartnerPillenBisOrange({ onInstagram = () => {}, onSponsor = () => {} }) {
  const rent = { width: "100%", marginBottom: 12, border: "2px dashed #ec4899", background: "rgba(236,72,153,0.06)", borderRadius: 16, padding: "18px 16px", textAlign: "center", cursor: "pointer", color: "inherit" };
  return (
    <section style={SEC} data-testid="raster1-partner-pillen">
      <div style={WRAP}>
        <p style={{ fontSize: 12, color: "#a1a1aa", marginBottom: 12, lineHeight: 1.6 }} data-testid="r1-intro">
          Deine Partner auf TipJar – buche deine eigene Pille für deinen Link oder entdecke unsere Top-Wettanbieter.
          Jede Pille ist ein direkter Link – deine Sichtbarkeit, dein Business.
        </p>

        <button onClick={onInstagram} style={rent} data-testid="r1-rent-2-pills">
          <span style={{ display: "block", fontSize: 14, fontWeight: 900, color: "#f472b6" }}>RENT 2 PILLS FOR YOUR LINK · 300€/MONTH</span>
          <span style={{ display: "block", fontSize: 11, color: "#a1a1aa", marginTop: 4 }}>CLICK → INSTAGRAM @tipjarglobal</span>
        </button>

        <button onClick={onInstagram} style={{ ...rent, padding: "14px 16px" }} data-testid="r1-rent-a-pill">
          <span style={{ display: "block", fontSize: 14, fontWeight: 900, color: "#f472b6" }}>RENT A PILL FOR YOUR LINK · 150€/MONTH</span>
          <span style={{ display: "block", fontSize: 11, color: "#a1a1aa", marginTop: 4 }}>CLICK → INSTAGRAM @tipjarglobal</span>
        </button>

        <button onClick={onSponsor} data-testid="r1-wazamba"
          style={{ width: "100%", marginBottom: 12, border: "none", borderRadius: 16, padding: "18px 16px", textAlign: "center", cursor: "pointer", background: "linear-gradient(90deg,#7c3aed,#a855f7)" }}>
          <span style={{ display: "inline-block", fontSize: 10, fontWeight: 900, background: "rgba(0,0,0,0.3)", color: "#fff", borderRadius: 999, padding: "2px 8px", marginBottom: 4 }}>TOP</span>
          <span style={{ display: "block", fontSize: 18, fontWeight: 900, color: "#fff", letterSpacing: 1 }}>WAZAMBA</span>
          <span style={{ display: "block", fontSize: 11, color: "rgba(255,255,255,0.9)", marginTop: 4 }}>50% RELOAD BONUS BIS 500€ · 100% BIS 500€ + 200 FS</span>
        </button>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 8 }} data-testid="r1-casino-grid">
          {GRID.map((g) => (
            <button key={g.name} onClick={onSponsor} data-testid={`r1-sponsor-${g.name.toLowerCase()}`}
              style={{ border: "none", borderRadius: 12, padding: "16px 12px", textAlign: "center", fontWeight: 900, fontSize: 14, cursor: "pointer", background: g.bg, color: g.fg }}>
              {g.name}
            </button>
          ))}
        </div>
      </div>
      <div style={{ ...WRAP, marginTop: 20, height: 2, background: "rgba(220,38,38,0.8)", borderRadius: 999 }} data-testid="r1-red-divider" />
    </section>
  );
}
