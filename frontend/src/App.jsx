import React from "react";
import "./App.css";

// ============================================================
// APP — SINGLE SOURCE OF TRUTH
// Erste Etage / Skelett: genau 13 Raster (0–12) in Blueprint-Reihenfolge.
// 100% inline-gestylt, Tailwind-frei, bulletproof für Vite/Hetzner.
// Meta AI baut hierauf auf (Logik, i18n, Handler) — Struktur bleibt fix.
// ============================================================
import Raster0_Splash from "./components/Raster0_Splash";
import Raster1_PartnerPillenBisOrange from "./components/Raster1_PartnerPillenBisOrange";
import Raster2_CommunityPricing from "./components/Raster2_CommunityPricing";
import Raster3_ToolbarHeader from "./components/Raster3_ToolbarHeader";
import Raster4_KiInfoAndSixActions from "./components/Raster4_KiInfoAndSixActions";
import Raster5_WettenGeldVerdienen from "./components/Raster5_WettenGeldVerdienen";
import Raster6_Batterie from "./components/Raster6_Batterie";
import Raster7_GlobaleCommunity from "./components/Raster7_GlobaleCommunity";
import Raster8_Video from "./components/Raster8_Video";
import Raster9_WasIstTipJar from "./components/Raster9_WasIstTipJar";
import Raster10_FreundeEinladen from "./components/Raster10_FreundeEinladen";
import Raster11_HallOfFame from "./components/Raster11_HallOfFame";
import Raster12_LegalFooter from "./components/Raster12_LegalFooter";

export default function App() {
  return (
    <div style={{ minHeight: "100vh", overflowX: "hidden", background: "#09090B", color: "#fff", fontFamily: "system-ui, sans-serif" }} id="top">
      <Raster0_Splash />
      <Raster1_PartnerPillenBisOrange />
      <Raster2_CommunityPricing />
      <Raster3_ToolbarHeader />
      <Raster4_KiInfoAndSixActions />
      <Raster5_WettenGeldVerdienen />
      <Raster6_Batterie />
      <Raster7_GlobaleCommunity />
      <Raster8_Video />
      <Raster9_WasIstTipJar />
      <Raster10_FreundeEinladen />
      <Raster11_HallOfFame />
      <Raster12_LegalFooter />
    </div>
  );
}
