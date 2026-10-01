import React from "react";
import { Info, Camera } from "lucide-react";

// ============================================================
// RASTER 4 — KI-INFO + 6 AKTIONS-PILLEN
// VON: Info-Box "Die KI macht manchmal Fehler..." + blauer Korrektur-Knopf
// BIS: Nach rosa Pille "Statistiken" vor "Willst du mit Wetten Geld verdienen?"
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 960, margin: "0 auto" };
const PILLS = [
  { label: "KI Single-Game", count: 9, bg: "#16a34a", fg: "#fff" },
  { label: "Smart Picks", count: 1, bg: "#16a34a", fg: "#fff" },
  { label: "Master", count: 3, bg: "#dc2626", fg: "#fff" },
  { label: "Abgerechnet", count: 1, bg: "#f4f4f5", fg: "#000" },
  { label: "Live KI Picks", count: 0, bg: "#2563eb", fg: "#fff" },
  { label: "Statistiken", count: null, bg: "#ec4899", fg: "#fff" },
];

export default function Raster4_KiInfoAndSixActions({ onCorrection = () => {}, onPill = () => {} }) {
  return (
    <section style={{ padding: 16 }} data-testid="raster4-ki-info-actions">
      <div style={WRAP}>
        <div style={{ border: "1px solid #27272A", background: "#18181B", borderRadius: 16, padding: 16, marginBottom: 12 }} data-testid="r4-ki-info">
          <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
            <Info size={18} color="#a1a1aa" style={{ flexShrink: 0, marginTop: 2 }} />
            <p style={{ fontSize: 14, color: "#d4d4d8", lineHeight: 1.6, margin: 0 }}>
              Die KI macht manchmal Fehler bei Uhrzeiten, Quoten oder Märkten. Sie analysiert Wettscheine per OCR –
              manchmal erkennt sie Quoten falsch. Wenn du einen Fehler siehst, klicke auf Korrektur und lade ein Foto vom Schein hoch.
            </p>
          </div>
          <button onClick={onCorrection} data-testid="r4-correction-btn"
            style={{ marginTop: 12, display: "inline-flex", alignItems: "center", gap: 8, borderRadius: 999, background: "#2563eb", color: "#fff", fontWeight: 700, fontSize: 14, padding: "10px 16px", border: "none", cursor: "pointer" }}>
            <Camera size={16} /> Korrektur – Foto vom Schein
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 8 }} data-testid="r4-pills">
          {PILLS.map((p) => (
            <button key={p.label} onClick={onPill} data-testid={`r4-pill-${p.label.toLowerCase().replace(/\s+/g, "-")}`}
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderRadius: 999, padding: "14px 20px", fontWeight: 900, fontSize: 14, border: "none", cursor: "pointer", background: p.bg, color: p.fg }}>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.label}</span>
              {p.count !== null && (
                <span style={{ marginLeft: 8, flexShrink: 0, minWidth: 22, height: 20, padding: "0 6px", borderRadius: 999, background: "rgba(0,0,0,0.25)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11 }}>{p.count}</span>
              )}
            </button>
          ))}
        </div>
      </div>
      <div style={{ ...WRAP, marginTop: 20, height: 2, background: "rgba(220,38,38,0.8)", borderRadius: 999 }} data-testid="r4-red-divider" />
    </section>
  );
}
