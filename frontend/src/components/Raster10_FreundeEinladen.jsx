import React from "react";

// ============================================================
// RASTER 10 — FREUNDE EINLADEN (Ziel 1.000 Mitglieder)
// VON: Badge ZIEL 1.000 MITGLIEDER + Lade deine Freunde ein
// BIS: Ende Sharing Icons WhatsApp Telegram X + Einladungslink
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 760, margin: "0 auto" };

export default function Raster10_FreundeEinladen({ members = 1, goal = 1000, onCopy = () => {}, onShare = () => {} }) {
  const pct = Math.min(100, Math.round((members / goal) * 100));
  return (
    <section style={{ padding: "32px 16px" }} data-testid="raster10-freunde-einladen">
      <div style={WRAP}>
        <span style={{ display: "inline-block", fontSize: 11, fontWeight: 800, letterSpacing: 1, color: "#00FF94", border: "1px solid rgba(0,255,148,0.3)", borderRadius: 999, padding: "4px 12px", marginBottom: 12 }}>
          ✨ ZIEL: 1.000 MITGLIEDER
        </span>
        <h2 style={{ fontSize: 28, fontWeight: 900, color: "#fff", margin: "0 0 12px" }}>Lade deine Freunde ein</h2>
        <p style={{ fontSize: 14, color: "#a1a1aa", lineHeight: 1.6, margin: "0 0 6px" }}>
          TipJar wird mit jedem Tipper stärker. Hilf uns, 1.000 Mitglieder zu erreichen — bring die Freunde mit, deren Tipps du wirklich vertraust.
        </p>
        <p style={{ fontSize: 13, color: "#E1FF00", margin: "0 0 16px" }}>Verdiene 100 Münzen für jeden Freund, der über deinen Link beitritt und seine E-Mail bestätigt.</p>

        <p style={{ fontSize: 10, letterSpacing: 2, textTransform: "uppercase", color: "#71717a", margin: "0 0 6px" }}>Weg zu 1.000 Mitgliedern</p>
        <div style={{ height: 14, borderRadius: 999, background: "#27272A", overflow: "hidden", marginBottom: 4 }}>
          <div style={{ height: "100%", width: `${pct}%`, background: "#00FF94" }} />
        </div>
        <p style={{ fontSize: 12, color: "#a1a1aa", margin: "0 0 16px" }}>{members} / {goal} · {pct}% · {goal - members} Mitglieder to go</p>

        <p style={{ fontSize: 10, letterSpacing: 2, textTransform: "uppercase", color: "#71717a", margin: "0 0 6px" }}>Einladungslink kopieren</p>
        <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
          <input readOnly value="https://tipjarglobal.com/?ref=…" data-testid="r10-link"
            style={{ flex: 1, background: "#09090B", border: "1px solid #27272A", borderRadius: 12, padding: "10px 12px", color: "#a1a1aa", fontSize: 13 }} />
          <button onClick={onCopy} data-testid="r10-copy"
            style={{ borderRadius: 12, background: "#E1FF00", color: "#09090B", fontWeight: 900, fontSize: 13, padding: "0 18px", border: "none", cursor: "pointer" }}>Kopieren</button>
        </div>
        <div style={{ display: "flex", gap: 8 }} data-testid="r10-share">
          {["WhatsApp", "Telegram", "X"].map((s) => (
            <button key={s} onClick={onShare} data-testid={`r10-share-${s.toLowerCase()}`}
              style={{ flex: 1, borderRadius: 12, border: "1px solid #27272A", background: "#18181B", color: "#fff", fontWeight: 700, padding: "10px 0", cursor: "pointer", fontSize: 13 }}>{s}</button>
          ))}
        </div>
      </div>
    </section>
  );
}
