import React from "react";
import { motion } from "framer-motion";

// TipJar centerpiece: the club crest logo only, enlarged, with a soft volt glow.
export default function AnimatedJar() {
  return (
    <div
      className="relative mx-auto flex items-center justify-center"
      style={{ width: 440, height: 440 }}
      data-testid="animated-jar"
    >
      <div
        className="absolute inset-0 blur-3xl opacity-30"
        style={{ background: "radial-gradient(circle at 50% 50%, #E1FF00, transparent 62%)" }}
      />
      <motion.img
        src="/tipjar-crest.png?v=4"
        alt="TipJar"
        draggable="false"
        className="relative z-10 w-[420px] h-[420px] object-contain"
        style={{ filter: "drop-shadow(0 0 34px rgba(225,255,0,0.4))" }}
        animate={{ y: [0, -14, 0] }}
        transition={{ duration: 4.5, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
