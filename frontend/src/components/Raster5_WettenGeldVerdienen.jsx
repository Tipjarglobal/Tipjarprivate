import React from "react";
import { Crown, Sparkles, Coins, Boxes, Users, Lock } from "lucide-react";

// ============================================================
// RASTER 5 — WETTEN GELD VERDIENEN (CTA + Aktions-Pillen)
// VON: Rotes Kronen-Symbol "Willst du mit Wetten Geld verdienen? Dann..."
// BIS: Ende Glühbirne "Jeder Schein macht die KI schlauer."
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 960, margin: "0 auto" };

export default function Raster5_WettenGeldVerdienen({ onSubmit = () => {}, onEarn = () => {}, onCollection = () => {}, onCommunity = () => {}, onLive = () => {}, onConfidential = () => {} }) {
  const base = { display: "flex", alignItems: "center", justifyContent: "center", gap: 8, borderRadius: 999, fontWeight: 700, padding: "14px 24px", cursor: "pointer", fontSize: 15 };
  return (
    <section style={{ padding: 16 }} data-testid="raster-5" data-i18n="raster5">
      <div style={{ ...WRAP, border: "1px solid #27272A", background: "#18181B", borderRadius: 16, padding: 20 }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 20 }}>
          <Crown size={18} color="#E11D2A" style={{ flexShrink: 0, marginTop: 2 }} />
          <p style={{ fontSize: 14, color: "#d4d4d8", lineHeight: 1.6, margin: 0 }}>
            Willst du mit Wetten Geld verdienen? Dann brauchst du diese Seite. Melde dich an, aktiviere deinen Standort,
            wähle deine Sprache und schalte bei den Benachrichtigungen den Master an – so verpasst du keinen einzigen Pick.
            Dann spiele einfach, was der Master dir gibt, immer mit kontrolliertem Einsatz. So wird aus Wetten ein System statt Glücksspiel.
          </p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }}>
          <button onClick={onSubmit} data-testid="r5-submit" style={{ ...base, background: "#E1FF00", color: "#09090B", border: "none" }}>
            <Sparkles size={18} /> Tipp einwerfen
          </button>
          <button onClick={onEarn} data-testid="r5-earn" style={{ ...base, background: "#3f3f1a", color: "#E1FF00", border: "1px solid rgba(225,255,0,0.4)" }}>
            <Coins size={18} /> Münzen verdienen
          </button>
          <button onClick={onCollection} data-testid="r5-collection" style={{ ...base, background: "rgba(255,255,255,0.05)", color: "#fff", border: "1px solid rgba(255,255,255,0.2)" }}>
            <Boxes size={18} /> Meine Sammlung
          </button>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 4, borderRadius: 999, background: "#E3A81B", color: "#000", fontWeight: 700, padding: 4 }} data-testid="r5-community-wrap">
            <button onClick={onCommunity} data-testid="r5-community"
              style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0, flex: 1, justifyContent: "center", paddingLeft: 8, paddingTop: 10, paddingBottom: 10, borderRadius: 999, border: "none", background: "transparent", color: "#000", cursor: "pointer" }}>
              <Users size={17} strokeWidth={2.5} /><span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", fontSize: 14 }}>Community Picks ansehen</span>
            </button>
            <button onClick={onLive} data-testid="r5-live"
              style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0, borderRadius: 999, background: "#2563eb", color: "#fff", padding: "8px 12px", fontSize: 12, fontWeight: 900, textTransform: "uppercase", border: "none", cursor: "pointer" }}>
              <span style={{ width: 8, height: 8, borderRadius: 999, background: "#fff" }} /> LIVE
            </button>
          </div>
        </div>

        <button onClick={onConfidential} data-testid="r5-confidential"
          style={{ ...base, width: "100%", marginTop: 12, background: "#a855f7", color: "#fff", border: "none" }}>
          <Lock size={18} /> confidential menu
        </button>
      </div>

      <div style={{ ...WRAP, marginTop: 12, display: "flex", alignItems: "flex-start", gap: 10, border: "1px solid rgba(225,255,0,0.3)", background: "linear-gradient(90deg,rgba(225,255,0,0.1),transparent)", borderRadius: 16, padding: "12px 16px" }} data-testid="r5-bulb-hint">
        <span style={{ fontSize: 18, lineHeight: 1, marginTop: 2 }}>💡</span>
        <p style={{ fontSize: 13, color: "#e4e4e7", lineHeight: 1.6, margin: 0 }}>
          Je mehr Scheine ihr postet – gespielte, gewonnene UND verlorene – desto mehr bringt ihr TipJar bei:
          richtigere Quoten zu tippen und bessere Tipps zu treffen. Jeder Schein macht die KI schlauer.
        </p>
      </div>
    </section>
  );
}
