import React from "react";
import { Play } from "lucide-react";

// ============================================================
// RASTER 8 — VIDEO-SEKTION
// VON: Video SPORTS BETTING Background
// BIS: Ende Video Player + Overlay "Try it free at tipjarglobal.com"
// 100% INLINE-STYLE — bulletproof
// ============================================================
export default function Raster8_Video({ onPlay = () => {} }) {
  return (
    <section style={{ padding: 16 }} data-testid="raster8-video">
      <div style={{ maxWidth: 960, margin: "0 auto", position: "relative", borderRadius: 16, overflow: "hidden", aspectRatio: "16 / 9", background: "linear-gradient(135deg,#0b1220,#1e293b)" }}>
        <button onClick={onPlay} data-testid="r8-play"
          style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", border: "none", background: "transparent", cursor: "pointer" }}>
          <span style={{ width: 72, height: 72, borderRadius: 999, background: "rgba(255,255,255,0.15)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Play size={30} color="#fff" fill="#fff" />
          </span>
        </button>
        <span style={{ position: "absolute", bottom: 12, left: 12, fontSize: 12, fontWeight: 700, color: "#fff", background: "rgba(0,0,0,0.6)", borderRadius: 8, padding: "6px 10px" }}>
          Try it free at tipjarglobal.com
        </span>
      </div>
    </section>
  );
}
