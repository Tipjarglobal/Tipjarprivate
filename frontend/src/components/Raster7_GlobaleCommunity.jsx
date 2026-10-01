import React from "react";
import { CheckCircle2 } from "lucide-react";

// ============================================================
// RASTER 7 — GLOBALE TIPP-COMMUNITY (Über uns + Wasserzeichen)
// VON: Badge DIE GLOBALE TIPP-COMMUNITY + Posten. Bewerten. Kassieren.
// BIS: Ende Wasserzeichen TIPJAR + Tipjarglobal.com
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 960, margin: "0 auto", textAlign: "center" };

export default function Raster7_GlobaleCommunity() {
  return (
    <section style={{ padding: "32px 16px" }} data-testid="raster7-globale-community">
      <div style={WRAP}>
        <span style={{ display: "inline-block", fontSize: 11, fontWeight: 800, letterSpacing: 1, color: "#E1FF00", border: "1px solid rgba(225,255,0,0.3)", borderRadius: 999, padding: "4px 12px", marginBottom: 12 }}>
          ✨ DIE GLOBALE TIPP-COMMUNITY
        </span>
        <h2 style={{ fontSize: 34, fontWeight: 900, color: "#fff", margin: "0 0 12px" }}>Posten. Bewerten. Kassieren.</h2>
        <p style={{ fontSize: 14, color: "#a1a1aa", lineHeight: 1.6, maxWidth: 640, margin: "0 auto 16px" }}>
          Wirf deine Fußballtipps in den Jar. Unsere KI bewertet jeden Schein sofort, die Community bewertet mit —
          und erfolgreiche Tipper verwandeln Münzen in echtes Geld.
        </p>
        <div style={{ display: "inline-flex", alignItems: "flex-start", gap: 10, textAlign: "left", border: "1px solid rgba(0,255,148,0.3)", background: "rgba(0,255,148,0.05)", borderRadius: 16, padding: "12px 16px", maxWidth: 560, marginBottom: 24 }}>
          <CheckCircle2 size={20} color="#00FF94" style={{ flexShrink: 0, marginTop: 2 }} />
          <p style={{ fontSize: 13, color: "#d4d4d8", lineHeight: 1.6, margin: 0 }}>
            Hier gibt's NUR spielbare Tipps — niemals Gewinn-Benachrichtigungen. Einfach reinschauen & nachspielen, immer mit kontrolliertem Einsatz.
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }} data-testid="r7-watermark">
          <div style={{ width: 72, height: 72, borderRadius: 16, border: "2px solid rgba(225,255,0,0.4)", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 0 30px rgba(225,255,0,0.25)" }}>
            <span style={{ color: "#E1FF00", fontWeight: 900, fontSize: 20 }}>TJ</span>
          </div>
          <span style={{ fontWeight: 900, letterSpacing: 2, color: "#fff" }}>TIPJAR</span>
          <span style={{ fontSize: 13, color: "#E1FF00" }}>Tipjarglobal.com</span>
        </div>
      </div>
    </section>
  );
}
