import React from "react";
import { AlertTriangle } from "lucide-react";

// ============================================================
// RASTER 12 — RECHTLICHER FOOTER
// VON: Footer TipJar GLOBAL + Impressum Datenschutz AGB
// BIS: Ende WICHTIGER HINWEIS + Disclaimer + 18+ + BZgA + kontakt@tipjarglobal.com
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 760, margin: "0 auto", textAlign: "center" };
const link = { color: "#a1a1aa", fontSize: 13, textDecoration: "none", cursor: "pointer" };

export default function Raster12_LegalFooter({ onLegal = () => {} }) {
  return (
    <footer style={{ padding: "32px 16px 48px", borderTop: "1px solid #27272A", background: "#09090B" }} data-testid="raster12-legal-footer">
      <div style={WRAP}>
        <p style={{ fontSize: 18, fontWeight: 900, color: "#fff", margin: 0 }}>TipJar GLOBAL</p>
        <p style={{ fontSize: 12, color: "#E1FF00", margin: "4px 0 16px" }}>Post it. Rate it. Cash it.</p>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", marginBottom: 20 }}>
          <span onClick={() => onLegal("impressum")} style={link} data-testid="r12-impressum">Impressum</span>
          <span onClick={() => onLegal("datenschutz")} style={link} data-testid="r12-datenschutz">Datenschutz</span>
          <span onClick={() => onLegal("agb")} style={link} data-testid="r12-agb">AGB</span>
        </div>
        <div style={{ border: "1px solid rgba(220,38,38,0.4)", background: "rgba(220,38,38,0.05)", borderRadius: 16, padding: 16, textAlign: "left" }} data-testid="r12-hinweis">
          <p style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, fontWeight: 900, color: "#f87171", margin: "0 0 8px" }}>
            <AlertTriangle size={16} /> ⚠️ WICHTIGER HINWEIS
          </p>
          <p style={{ fontSize: 12, color: "#a1a1aa", lineHeight: 1.6, margin: "0 0 8px" }}>
            TipJar ist kein Buchmacher und kein Wettanbieter. Alle Tipps, Bewertungen und Analysen dienen ausschließlich Informations- und Unterhaltungszwecken
            und stellen keine Aufforderung zum Wetten dar. Es besteht keine Garantie auf Gewinne — Wetten erfolgen auf eigenes Risiko bei lizenzierten Drittanbietern.
          </p>
          <p style={{ fontSize: 12, color: "#a1a1aa", lineHeight: 1.6, margin: "0 0 8px" }}>Nur für Personen ab 18 Jahren. Glücksspiel kann süchtig machen.</p>
          <p style={{ fontSize: 12, color: "#a1a1aa", lineHeight: 1.6, margin: 0 }}>Hilfe &amp; Beratung: BZgA · check-dein-spiel.de · kostenlose Sucht-Hotline 0800 1 37 27 00</p>
        </div>
        <p style={{ fontSize: 12, color: "#71717a", marginTop: 16 }}>Kontakt: kontakt@tipjarglobal.com</p>
      </div>
    </footer>
  );
}
