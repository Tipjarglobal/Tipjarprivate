import React from "react";
import { Crown } from "lucide-react";

// ============================================================
// RASTER 2 — COMMUNITY PRICING (zwischen den roten Linien)
// VON: "Supporte TipJar – werde Teil der Community..."
// BIS: Untere rote Linie vor Toolbar — 9,99€ SUPPORTER klein → 119,99€ PARTNER groß
// 100% INLINE-STYLE — bulletproof
// ============================================================
const WRAP = { maxWidth: 960, margin: "0 auto" };
const PILLS = [
  { price: "119,99€", weeks: 6, coins: 1600, badge: "PARTNER", crown: true, jar: "Legendäre Jars", pad: 24, big: true },
  { price: "79,99€", weeks: 5, coins: 950, badge: "SPONSOR", jar: "Epische Jars", pad: 20 },
  { price: "49,99€", weeks: 4, coins: 460, badge: "VIP", jar: "Rare Jars", pad: 16, best: true },
  { price: "19,99€", weeks: 3, coins: 150, badge: "FAN", jar: "Uncommon Jars", pad: 14 },
  { price: "9,99€", weeks: 2, coins: 50, badge: "SUPPORTER", jar: "Common Jars", pad: 12 },
];

export default function Raster2_CommunityPricing({ onBuy = () => {} }) {
  return (
    <section style={{ padding: 16 }} data-testid="raster2-community-pricing">
      <div style={WRAP}>
        <p style={{ fontSize: 12, color: "#a1a1aa", marginBottom: 12, lineHeight: 1.6 }} data-testid="r2-intro">
          Supporte TipJar – werde Teil der Community. Jede Pille hilft TipJar zu wachsen. Deine Pille erscheint sofort nach dem Kauf.
          Erster Monat 50% Rabatt.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {PILLS.map((p) => (
            <button key={p.badge} onClick={onBuy} data-testid={`r2-pill-${p.badge.toLowerCase()}`}
              style={{ width: "100%", border: p.best ? "1px solid #E1FF00" : "1px solid #27272A", background: "#18181B", borderRadius: 16, padding: `${p.pad}px 20px`, textAlign: "left", cursor: "pointer", color: "#fff" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
                <span style={{ color: "#E1FF00", fontWeight: 900, fontSize: p.big ? 24 : 18, lineHeight: 1 }}>
                  {p.price}<span style={{ color: "#71717a", fontWeight: 700, fontSize: 11 }}> / {p.weeks} Wochen</span>
                </span>
                <span style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11, fontWeight: 900, color: "#E1FF00" }}>
                  {p.crown && <Crown size={13} />} {p.badge}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 8 }}>
                <span style={{ fontSize: 11, color: "#a1a1aa" }}>{p.coins} Münzen</span>
                <span style={{ fontSize: 10, color: "#71717a" }}>repräsentiert: {p.jar}</span>
              </div>
            </button>
          ))}
        </div>
      </div>
      <div style={{ ...WRAP, marginTop: 20, height: 2, background: "rgba(220,38,38,0.8)", borderRadius: 999 }} data-testid="r2-red-divider" />
    </section>
  );
}
