import React from "react";
import { Download, Bell, Globe, Plus } from "lucide-react";

// ============================================================
// RASTER 3 — ZENTRALE TOOLBAR / HEADER (h-20 big)
// VON: TipJar GLOBAL Logo + Download + Glocke + Sprache + Registrieren gelb + Plus
// BIS: Ende Toolbar vor Info-Box "Die KI macht manchmal Fehler..."
// 100% INLINE-STYLE — bulletproof
// ============================================================
const iconBtn = { width: 40, height: 40, borderRadius: 999, border: "1px solid #27272A", background: "#18181B", display: "flex", alignItems: "center", justifyContent: "center", color: "#d4d4d8", cursor: "pointer" };

export default function Raster3_ToolbarHeader({ onDownload = () => {}, onBell = () => {}, onLang = () => {}, onRegister = () => {}, onPlus = () => {} }) {
  return (
    <header data-testid="raster3-toolbar-header"
      style={{ height: 80, padding: "0 16px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #27272A", background: "rgba(9,9,11,0.95)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }} data-testid="r3-logo">
        <span style={{ fontSize: 24, fontWeight: 900, color: "#fff", letterSpacing: "-0.02em" }}>TipJar</span>
        <span style={{ fontSize: 24, fontWeight: 900, color: "#E1FF00", letterSpacing: "-0.02em" }}>GLOBAL</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <button onClick={onDownload} style={iconBtn} data-testid="r3-download"><Download size={18} /></button>
        <button onClick={onBell} style={{ ...iconBtn, position: "relative" }} data-testid="r3-bell">
          <Bell size={18} />
          <span style={{ position: "absolute", top: -2, right: -2, width: 12, height: 12, background: "#FF1E56", borderRadius: 999 }} />
        </button>
        <button onClick={onLang} style={iconBtn} data-testid="r3-lang"><Globe size={18} /></button>
        <button onClick={onRegister} data-testid="r3-register"
          style={{ borderRadius: 999, background: "#E1FF00", color: "#09090B", fontWeight: 900, fontSize: 14, padding: "10px 16px", border: "none", cursor: "pointer" }}>
          Registrieren
        </button>
        <button onClick={onPlus} style={iconBtn} data-testid="r3-plus"><Plus size={18} /></button>
      </div>
    </header>
  );
}
