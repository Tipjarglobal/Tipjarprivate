import React from "react";
import { Info, Camera, Star } from "lucide-react";

// VON: Info-Box "Die KI macht manchmal Fehler..." + blauer Korrektur-Knopf
// BIS: Nach rosa Pille "Statistiken" + geiler Look (RateWall/ScorerRadar/Systems/OddsValue/Stats)
// RASTER 4 — KI-Info + 6 Pillen. GEILER LOOK IN SCHALE als interne Funktionen
// (vormals RateWall/ScorerRadar/Systems/OddsValue/AiRatingStars/QualifierBriefing/StatisticsView/SecretInsights/GoalThirst/HtGoals/ExpertsShowcase/Disclaimer).
// 100% inline, kein Tailwind, kein framer-motion.
const WRAP = { maxWidth: 960, margin: "0 auto" };
const PILLS = [
  { label: "KI Single-Game", count: 9, bg: "#16a34a", fg: "#fff" },
  { label: "Smart Picks", count: 1, bg: "#16a34a", fg: "#fff" },
  { label: "Master", count: 3, bg: "#dc2626", fg: "#fff" },
  { label: "Abgerechnet", count: 1, bg: "#f4f4f5", fg: "#000" },
  { label: "Live KI Picks", count: 0, bg: "#2563eb", fg: "#fff" },
  { label: "Statistiken", count: null, bg: "#ec4899", fg: "#fff" },
];

function AiRatingStars({ value = 8 }) {
  return (
    <div style={{ display: "flex", gap: 2 }}>
      {Array.from({ length: 10 }).map((_, i) => (
        <Star key={i} size={14} color={i < value ? "#E1FF00" : "#3f3f46"} fill={i < value ? "#E1FF00" : "none"} />
      ))}
    </div>
  );
}

function RateWallVisual() {
  const rows = [
    { team: "Bayern – Dortmund · Über 2.5", v: 9, odd: "1.72" },
    { team: "Real – Barça · BTTS", v: 7, odd: "1.85" },
    { team: "City – Arsenal · 1X", v: 6, odd: "1.40" },
  ];
  return (
    <div style={{ marginTop: 12 }} data-testid="r4-ratewall">
      <p style={{ fontSize: 10, letterSpacing: 2, textTransform: "uppercase", color: "#71717a", margin: "0 0 8px" }}>Bewertungswand (RateWall)</p>
      {rows.map((r, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, padding: "10px 12px", borderRadius: 12, backgroundColor: "#18181B", border: "1px solid #27272A", marginBottom: 6 }}>
          <span style={{ fontSize: 13, color: "#e4e4e7", minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.team}</span>
          <span style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
            <AiRatingStars value={r.v} />
            <span style={{ fontSize: 12, fontWeight: 900, color: "#E1FF00" }}>{r.odd}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

function ScorerRadarVisual() {
  const bars = [{ l: "Form", v: 82 }, { l: "Angriff", v: 68 }, { l: "Defensive", v: 55 }, { l: "Value", v: 74 }];
  return (
    <div style={{ marginTop: 12 }} data-testid="r4-radar">
      <p style={{ fontSize: 10, letterSpacing: 2, textTransform: "uppercase", color: "#71717a", margin: "0 0 8px" }}>ScorerRadar · Systems</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 8 }}>
        {bars.map((b) => (
          <div key={b.l} style={{ padding: "10px 12px", borderRadius: 12, backgroundColor: "#18181B", border: "1px solid #27272A" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#a1a1aa", marginBottom: 6 }}><span>{b.l}</span><span style={{ color: "#fff", fontWeight: 800 }}>{b.v}%</span></div>
            <div style={{ height: 6, borderRadius: 999, backgroundColor: "#27272a", overflow: "hidden" }}><div style={{ width: `${b.v}%`, height: "100%", backgroundColor: "#22c55e" }} /></div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Raster4_KiInfoAndSixActions({ onCorrection = () => {}, onPill = () => {} }) {
  return (
    <section style={{ padding: 16 }} data-testid="raster-4" data-i18n="raster4">
      <div style={WRAP}>
        <div style={{ border: "1px solid #27272A", backgroundColor: "#18181B", borderRadius: 16, padding: 16, marginBottom: 12 }} data-testid="r4-ki-info">
          <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
            <Info size={18} color="#a1a1aa" style={{ flexShrink: 0, marginTop: 2 }} />
            <p style={{ fontSize: 14, color: "#d4d4d8", lineHeight: 1.6, margin: 0 }}>
              Die KI macht manchmal Fehler bei Uhrzeiten, Quoten oder Märkten. Sie analysiert Wettscheine per OCR –
              manchmal erkennt sie Quoten falsch. Wenn du einen Fehler siehst, klicke auf Korrektur und lade ein Foto vom Schein hoch.
            </p>
          </div>
          <button onClick={onCorrection} data-testid="r4-correction-btn"
            style={{ marginTop: 12, display: "inline-flex", alignItems: "center", gap: 8, borderRadius: 999, backgroundColor: "#2563eb", color: "#fff", fontWeight: 700, fontSize: 14, padding: "10px 16px", border: "none", cursor: "pointer" }}>
            <Camera size={16} /> Korrektur – Foto vom Schein
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 8 }} data-testid="r4-pills">
          {PILLS.map((p) => (
            <button key={p.label} onClick={onPill} data-testid={`r4-pill-${p.label.toLowerCase().replace(/\s+/g, "-")}`}
              style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderRadius: 999, padding: "14px 20px", fontWeight: 900, fontSize: 14, border: "none", cursor: "pointer", backgroundColor: p.bg, color: p.fg }}>
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.label}</span>
              {p.count !== null && (
                <span style={{ marginLeft: 8, flexShrink: 0, minWidth: 22, height: 20, padding: "0 6px", borderRadius: 999, backgroundColor: "rgba(0,0,0,0.25)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11 }}>{p.count}</span>
              )}
            </button>
          ))}
        </div>

        <RateWallVisual />
        <ScorerRadarVisual />
      </div>
      <div style={{ ...WRAP, marginTop: 20, height: 2, backgroundColor: "#dc2626", borderRadius: 999 }} data-testid="r4-red-divider" />
    </section>
  );
}
// TODO Meta AI/Termius: RateWall/Radar/Stats mit echten Daten verdrahten — Struktur bleibt, Look bleibt.
