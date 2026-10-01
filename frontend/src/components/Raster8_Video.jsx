import React from "react";

// RASTER 8 — Intro-Video (Medien-Player)
export default function Raster8_Video() {
  return (
    <section className="relative max-w-3xl mx-auto px-4 sm:px-6 pt-2 pb-10" data-testid="raster8-video">
      <div className="rounded-3xl overflow-hidden border border-volt/25 bg-black shadow-[0_0_40px_rgba(225,255,0,0.12)]">
        <video
          data-testid="intro-video"
          src="/tipjar-intro.mp4"
          poster="/tipjar-crest.png"
          controls
          playsInline
          preload="metadata"
          className="w-full h-auto block"
        />
      </div>
    </section>
  );
}
