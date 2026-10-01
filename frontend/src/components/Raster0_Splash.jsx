import React, { useEffect, useState } from "react";

// VON: App Start, Lade-Animation, TipJar GLOBAL Logo
// BIS: Ende Splash, Übergang zu Raster 1 (Partner-Pillen)
// RASTER 0 per Blueprint — Splash/Loading Screen
// 100% INLINE, kein Tailwind, kein framer-motion. Gelber Schlangen-Rand via CSS @keyframes.
export default function Raster0_Splash() {
  const [hide, setHide] = useState(false);
  const [gone, setGone] = useState(false);
  useEffect(() => {
    const t1 = setTimeout(() => setHide(true), 2500);
    const t2 = setTimeout(() => setGone(true), 3100);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);
  if (gone) return null;
  return (
    <div data-testid="raster-0" data-i18n="raster0" style={{
      position: "fixed", inset: 0, zIndex: 200, backgroundColor: "#09090B",
      display: "flex", alignItems: "center", justifyContent: "center",
      transition: "transform 0.5s ease-in-out", transform: hide ? "translateY(-100%)" : "translateY(0)",
    }}>
      {/* CSS @keyframes statt framer-motion (Vite Tree-Shaking killt motion.path) */}
      <style>{`@keyframes tjSnake { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }`}</style>
      <img src="/splash-de.png" alt="TipJar GLOBAL" draggable={false}
        style={{ width: "100%", height: "100%", objectFit: "contain", maxWidth: 420, margin: "0 auto", userSelect: "none", pointerEvents: "none" }} />
      <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }} viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <path d="M50 1.5 H98.5 V98.5 H1.5 V1.5 Z" fill="none" stroke="#E1FF00" strokeWidth={5} strokeLinecap="round"
          vectorEffect="non-scaling-stroke" pathLength="1" strokeDasharray="1" strokeDashoffset="1"
          style={{ filter: "drop-shadow(0 0 6px #E1FF00)", animation: "tjSnake 2.5s linear forwards" }} />
      </svg>
    </div>
  );
}
// TODO Meta AI/Termius: Handler, i18n, Logik hier verdrahten — Struktur bleibt, Farben bleiben inline.
