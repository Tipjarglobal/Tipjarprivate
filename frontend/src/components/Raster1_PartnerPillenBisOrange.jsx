import React from "react";

// VON: "Deine Partner auf TipJar..." + RENT 2 PILLS 300€ + RENT A PILL 150€ + WAZAMBA + Casino-Grid
// BIS: Ende SGCASINO orange — unter das Orangene, vor roter Trennlinie "Supporte TipJar..."
// RASTER 1 per Blueprint Foto — Alles bis unter Orange SGCASINO
// 100% INLINE — Farben fix verankert (Vite purged keine Tailwind-Klassen weg)
const WRAP = { maxWidth: 960, margin: "0 auto" };
const GRID = [
  { name: "BANKONBET", bg: "#22c55e", fg: "#fff" },
  { name: "ROBOCAT", bg: "#ef4444", fg: "#fff" },
  { name: "PISTOLO", bg: "#eab308", fg: "#000" },
  { name: "5GRINGOS", bg: "#a16207", fg: "#fff" },
  { name: "20BET", bg: "#16a34a", fg: "#fff" },
  { name: "BETSCORE", bg: "#facc15", fg: "#000" },
  { name: "SGCASINO", bg: "#f97316", fg: "#000" },
];

export default function Raster1_PartnerPillenBisOrange({ onInstagram = () => {}, onSponsor = () => {} }) {
  const rent = { width: "100%", marginBottom: 12, border: "2px dashed #ec4899", backgroundColor: "rgba(236,72,153,0.06)", borderRadius: 16, padding: "18px 16px", textAlign: "center", cursor: "pointer", color: "inherit" };
  return (
    <section data-testid="raster-1" data-i18n="raster1" style={{ padding: 16 }}>
      <div style={WRAP}>
        <p data-i18n="raster1.intro" style={{ fontSize: 12, color: "#a1a1aa", marginBottom: 12, lineHeight: 1.6 }}>
          Deine Partner auf TipJar – buche deine eigene Pille für deinen Link oder entdecke unsere Top-Wettanbieter.
          Jede Pille ist ein direkter Link – deine Sichtbarkeit, dein Business.
        </p>

        <button onClick={onInstagram} style={rent} data-testid="r1-rent-2-pills" data-i18n="raster1.rent2">
          <span style={{ display: "block", fontSize: 14, fontWeight: 900, color: "#ec4899" }}>RENT 2 PILLS FOR YOUR LINK · 300€/MONTH</span>
          <span style={{ display: "block", fontSize: 11, color: "#a1a1aa", marginTop: 4 }}>CLICK → INSTAGRAM @tipjarglobal</span>
        </button>

        <button onClick={onInstagram} style={{ ...rent, padding: "14px 16px" }} data-testid="r1-rent-a-pill" data-i18n="raster1.rent1">
          <span style={{ display: "block", fontSize: 14, fontWeight: 900, color: "#ec4899" }}>RENT A PILL FOR YOUR LINK · 150€/MONTH</span>
          <span style={{ display: "block", fontSize: 11, color: "#a1a1aa", marginTop: 4 }}>CLICK → INSTAGRAM @tipjarglobal</span>
        </button>

        <button onClick={onSponsor} data-testid="r1-wazamba" data-i18n="raster1.wazamba"
          style={{ width: "100%", marginBottom: 12, border: "none", borderRadius: 16, padding: "18px 16px", textAlign: "center", cursor: "pointer", backgroundColor: "#a855f7" }}>
          <span style={{ display: "inline-block", fontSize: 10, fontWeight: 900, backgroundColor: "rgba(0,0,0,0.3)", color: "#fff", borderRadius: 999, padding: "2px 8px", marginBottom: 4 }}>TOP</span>
          <span style={{ display: "block", fontSize: 18, fontWeight: 900, color: "#fff", letterSpacing: 1 }}>WAZAMBA</span>
          <span style={{ display: "block", fontSize: 11, color: "rgba(255,255,255,0.9)", marginTop: 4 }}>50% RELOAD BONUS BIS 500€ · 100% BIS 500€ + 200 FS</span>
        </button>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 8 }} data-testid="r1-casino-grid">
          {GRID.map((g) => (
            <button key={g.name} onClick={onSponsor} data-testid={`r1-sponsor-${g.name.toLowerCase()}`}
              style={{ border: "none", borderRadius: 12, padding: "16px 12px", textAlign: "center", fontWeight: 900, fontSize: 14, cursor: "pointer", backgroundColor: g.bg, color: g.fg }}>
              {g.name}
            </button>
          ))}
        </div>
      </div>
      <div style={{ ...WRAP, marginTop: 20, height: 2, backgroundColor: "#dc2626", borderRadius: 999 }} data-testid="r1-red-divider" />
    </section>
  );
}
// TODO Meta AI/Termius: Handler, i18n (data-i18n Keys), Logik hier verdrahten — Struktur bleibt, Farben bleiben inline.
