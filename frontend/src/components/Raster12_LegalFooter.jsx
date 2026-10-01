import React from "react";
import { Disclaimer } from "./Disclaimer";

// RASTER 12 — Rechtlicher Footer & Plattform-Meta (Marke, Rechtslinks, Disclaimer)
export default function Raster12_LegalFooter({ onLegal }) {
  return (
    <footer className="border-t border-elevated py-10 text-center px-4" data-testid="raster12-legal-footer">
      <div className="inline-flex flex-col items-center leading-none" data-testid="footer-logo">
        <span className="font-heading font-black text-xl text-white">Tip<span className="text-volt">Jar</span></span>
        <span className="font-heading font-black text-[0.6rem] uppercase tracking-[0.25em] text-orange-500 -mt-0.5">global</span>
      </div>
      <p className="text-xs text-zinc-600 mt-2 mb-6">Post it. Rate it. Cash it.</p>
      <div className="flex items-center justify-center gap-4 mb-6 text-xs" data-testid="footer-legal-links">
        <button onClick={() => onLegal("impressum")} data-testid="footer-impressum" className="text-zinc-400 hover:text-volt transition-colors">Impressum</button>
        <span className="text-zinc-700">·</span>
        <button onClick={() => onLegal("datenschutz")} data-testid="footer-datenschutz" className="text-zinc-400 hover:text-volt transition-colors">Datenschutz</button>
        <span className="text-zinc-700">·</span>
        <button onClick={() => onLegal("agb")} data-testid="footer-agb" className="text-zinc-400 hover:text-volt transition-colors">AGB</button>
      </div>
      <Disclaimer />
    </footer>
  );
}
