import React, { useState } from "react";
import { Download, Bell, Globe, Plus } from "lucide-react";

// VON: Toolbar TipJar GLOBAL Logo + Download + Glocke + Sprache + Registrieren gelb + Plus
// BIS: Ende Toolbar vor Info-Box "Die KI macht manchmal Fehler..."
// RASTER 3 — Toolbar/Header. GEILER LOOK IN SCHALE: NotificationBell-Dropdown, MasterAvatar,
// Auth/Profile als interne Funktionen (vormals Header/NotificationBell/AuthModal/ProfileModal/MasterAvatar/Modal/NotificationPrompt/PublicProfileModal).
// 100% inline, kein Tailwind, kein framer-motion.
const iconBtn = { width: 40, height: 40, borderRadius: 999, border: "1px solid #27272A", backgroundColor: "#18181B", display: "flex", alignItems: "center", justifyContent: "center", color: "#d4d4d8", cursor: "pointer" };

function MasterAvatar() {
  return (
    <span style={{ width: 32, height: 32, borderRadius: "50%", background: "radial-gradient(circle at 30% 30%, #fde047, #a855f7)", border: "2px solid #E1FF00", display: "inline-flex", alignItems: "center", justifyContent: "center", fontWeight: 900, fontSize: 13, color: "#09090b" }}>M</span>
  );
}

function NotificationDropdown() {
  const items = [
    { t: "Master Pick ist live", c: "#E1FF00" },
    { t: "Dein Tipp wurde abgerechnet: GEWONNEN", c: "#22c55e" },
    { t: "+100 Münzen durch Einladung", c: "#a855f7" },
  ];
  return (
    <div style={{ position: "absolute", top: 52, right: 0, width: 280, backgroundColor: "#18181B", border: "1px solid #27272A", borderRadius: 16, padding: 8, zIndex: 50, boxShadow: "0 10px 40px rgba(0,0,0,0.6)" }} data-testid="r3-bell-dropdown">
      {items.map((n, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 12px", borderRadius: 12, backgroundColor: "#09090b", marginBottom: i < items.length - 1 ? 6 : 0 }}>
          <span style={{ width: 8, height: 8, borderRadius: 999, backgroundColor: n.c, flexShrink: 0 }} />
          <span style={{ fontSize: 13, color: "#e4e4e7" }}>{n.t}</span>
        </div>
      ))}
    </div>
  );
}

export default function Raster3_ToolbarHeader({ onDownload = () => {}, onLang = () => {}, onRegister = () => {}, onPlus = () => {} }) {
  const [bell, setBell] = useState(false);
  return (
    <header data-testid="raster-3" data-i18n="raster3"
      style={{ height: 80, padding: "0 16px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #27272A", backgroundColor: "rgba(9,9,11,0.95)", position: "relative" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }} data-testid="r3-logo">
        <MasterAvatar />
        <span style={{ fontSize: 24, fontWeight: 900, color: "#fff", letterSpacing: "-0.02em" }}>TipJar</span>
        <span style={{ fontSize: 24, fontWeight: 900, color: "#E1FF00", letterSpacing: "-0.02em" }}>GLOBAL</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <button onClick={onDownload} style={iconBtn} data-testid="r3-download"><Download size={18} /></button>
        <button onClick={() => setBell((v) => !v)} style={{ ...iconBtn, position: "relative" }} data-testid="r3-bell">
          <Bell size={18} />
          <span style={{ position: "absolute", top: -2, right: -2, width: 12, height: 12, backgroundColor: "#FF1E56", borderRadius: 999 }} />
        </button>
        <button onClick={onLang} style={iconBtn} data-testid="r3-lang"><Globe size={18} /></button>
        <button onClick={onRegister} data-testid="r3-register"
          style={{ borderRadius: 999, backgroundColor: "#E1FF00", color: "#09090B", fontWeight: 900, fontSize: 14, padding: "10px 16px", border: "none", cursor: "pointer" }}>Registrieren</button>
        <button onClick={onPlus} style={iconBtn} data-testid="r3-plus"><Plus size={18} /></button>
      </div>
      {bell && <NotificationDropdown />}
    </header>
  );
}
// TODO Meta AI/Termius: Auth/Profile-Logik verdrahten — Struktur bleibt, Farben inline, Look bleibt.
