import React from "react";
import { Trophy } from "lucide-react";

// VON: Badge HALL OF FAME + Hall of Fame Best of
// BIS: Ende Gewinn-Anzeigebereich "Noch keine Gewinne" + Footer-Signatur
// RASTER 11 — Hall of Fame. GEILER LOOK IN SCHALE: SponsorFeeder + HofPin-Grid als interne Funktionen
// (vormals HallOfFame/HofPinPanel/WinClaimModal/SponsorFeeder/PromoBanner/AdminPillsPanel/AdminResetBar/AdminSlipEditor/AnimatedJar).
// 100% inline, kein Tailwind, kein framer-motion.
const WRAP = { maxWidth: 760, margin: "0 auto", textAlign: "center" };

function SponsorFeederVisual() {
  const sponsors = [
    { n: "WAZAMBA", c: "#a855f7" }, { n: "BANKONBET", c: "#22c55e" }, { n: "20BET", c: "#16a34a" }, { n: "SGCASINO", c: "#f97316" },
  ];
  return (
    <div style={{ maxWidth: 760, margin: "20px auto 0" }} data-testid="r11-sponsorfeeder">
      <p style={{ fontSize: 10, letterSpacing: 2, textTransform: "uppercase", color: "#71717a", margin: "0 0 8px" }}>Unsere Partner</p>
      <div style={{ display: "flex", gap: 8, overflowX: "auto", justifyContent: "center" }}>
        {sponsors.map((s) => (
          <span key={s.n} style={{ flex: "0 0 auto", padding: "8px 14px", borderRadius: 999, backgroundColor: s.c, color: s.c === "#f97316" ? "#000" : "#fff", fontWeight: 900, fontSize: 12 }}>{s.n}</span>
        ))}
      </div>
    </div>
  );
}

function HofPinGridVisual() {
  return (
    <div style={{ maxWidth: 760, margin: "20px auto 0", display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 8 }} data-testid="r11-hofpin">
      {[1, 2, 3].map((i) => (
        <div key={i} style={{ padding: 14, borderRadius: 16, backgroundColor: "#18181B", border: "1px solid #27272A", textAlign: "center" }}>
          <Trophy size={20} color="#E1FF00" />
          <p style={{ fontSize: 11, color: "#71717a", margin: "8px 0 0" }}>Platz {i} · frei</p>
        </div>
      ))}
    </div>
  );
}

export default function Raster11_HallOfFame({ onShowWin = () => {} }) {
  return (
    <section style={{ padding: "32px 16px" }} data-testid="raster-11" data-i18n="raster11">
      <div style={WRAP}>
        <span style={{ display: "inline-block", fontSize: 11, fontWeight: 800, letterSpacing: 1, color: "#000", backgroundColor: "#E1FF00", borderRadius: 999, padding: "4px 12px", marginBottom: 12 }}>🏆 HALL OF FAME</span>
        <h2 style={{ fontSize: 28, fontWeight: 900, color: "#fff", margin: "0 0 8px" }}>Hall of Fame — Best of</h2>
        <p style={{ fontSize: 14, color: "#a1a1aa", margin: "0 0 20px" }}>Die größten verifizierten Gewinne der TipJar-Community.</p>
        <button onClick={onShowWin} data-testid="r11-show-win"
          style={{ display: "inline-flex", alignItems: "center", gap: 8, borderRadius: 999, backgroundColor: "#E1FF00", color: "#09090B", fontWeight: 900, fontSize: 15, padding: "14px 24px", border: "none", cursor: "pointer", marginBottom: 20 }}>
          <Trophy size={18} /> Zeig, was du mit TipJar gewonnen hast
        </button>
        <div style={{ border: "1px dashed #27272A", borderRadius: 16, padding: 24, color: "#71717a", fontSize: 13 }} data-testid="r11-empty">
          Noch keine Gewinne — sei der Erste, der ein TipJar-System knackt und sich seinen Platz sichert.
        </div>
      </div>
      <HofPinGridVisual />
      <SponsorFeederVisual />
      <div style={{ ...WRAP, marginTop: 24 }}>
        <p style={{ fontSize: 18, fontWeight: 900, color: "#fff", margin: 0 }}>TipJar GLOBAL</p>
        <p style={{ fontSize: 12, color: "#E1FF00", margin: "4px 0 0" }}>Post it. Rate it. Cash it.</p>
      </div>
    </section>
  );
}
// TODO Meta AI/Termius: HofPin/WinClaim/Sponsor/Admin-Logik verdrahten — Struktur bleibt, Look bleibt.
