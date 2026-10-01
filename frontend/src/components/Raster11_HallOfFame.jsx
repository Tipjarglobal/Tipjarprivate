import React from "react";
import { Trophy } from "lucide-react";

// ============================================================
// RASTER 11 — HALL OF FAME
// VON: Badge HALL OF FAME + Hall of Fame Best of
// BIS: Ende Gewinn-Anzeigebereich "Noch keine Gewinne" + Footer TipJar GLOBAL
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 760, margin: "0 auto", textAlign: "center" };

export default function Raster11_HallOfFame({ onShowWin = () => {} }) {
  return (
    <section style={{ padding: "32px 16px" }} data-testid="raster-11" data-i18n="raster11">
      <div style={WRAP}>
        <span style={{ display: "inline-block", fontSize: 11, fontWeight: 800, letterSpacing: 1, color: "#000", background: "#E1FF00", borderRadius: 999, padding: "4px 12px", marginBottom: 12 }}>
          🏆 HALL OF FAME
        </span>
        <h2 style={{ fontSize: 28, fontWeight: 900, color: "#fff", margin: "0 0 8px" }}>Hall of Fame — Best of</h2>
        <p style={{ fontSize: 14, color: "#a1a1aa", margin: "0 0 20px" }}>Die größten verifizierten Gewinne der TipJar-Community.</p>
        <button onClick={onShowWin} data-testid="r11-show-win"
          style={{ display: "inline-flex", alignItems: "center", gap: 8, borderRadius: 999, background: "#E1FF00", color: "#09090B", fontWeight: 900, fontSize: 15, padding: "14px 24px", border: "none", cursor: "pointer", marginBottom: 20 }}>
          <Trophy size={18} /> Zeig, was du mit TipJar gewonnen hast
        </button>
        <div style={{ border: "1px dashed #27272A", borderRadius: 16, padding: 24, color: "#71717a", fontSize: 13 }} data-testid="r11-empty">
          Noch keine Gewinne — sei der Erste, der ein TipJar-System knackt und sich seinen Platz sichert.
        </div>
        <div style={{ marginTop: 24 }}>
          <p style={{ fontSize: 18, fontWeight: 900, color: "#fff", margin: 0 }}>TipJar GLOBAL</p>
          <p style={{ fontSize: 12, color: "#E1FF00", margin: "4px 0 0" }}>Post it. Rate it. Cash it.</p>
        </div>
      </div>
    </section>
  );
}
