import React from "react";
import { motion } from "framer-motion";
import { Star, Flame } from "lucide-react";

// AI confidence shown as 1–10 stars (owner: no more percentages, we play with stars).
// 10 stars → an exploding particle burst. 9 stars → a flaming aura.
const VOLT = "#E1FF00";
const FIRE = "#FF7A18";

function ExplosionBurst() {
  const particles = Array.from({ length: 10 });
  return (
    <span className="pointer-events-none absolute inset-0 flex items-center justify-center" aria-hidden>
      <motion.span
        className="absolute h-6 w-6 rounded-full"
        style={{ background: "radial-gradient(circle, rgba(225,255,0,0.55), transparent 70%)" }}
        animate={{ scale: [0.6, 1.6, 0.6], opacity: [0.7, 0.15, 0.7] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
      />
      {particles.map((_, i) => {
        const angle = (i / particles.length) * Math.PI * 2;
        const dx = Math.cos(angle) * 26;
        const dy = Math.sin(angle) * 26;
        return (
          <motion.span
            key={i}
            className="absolute h-1 w-1 rounded-full"
            style={{ background: VOLT, boxShadow: `0 0 6px ${VOLT}` }}
            animate={{ x: [0, dx], y: [0, dy], opacity: [1, 0], scale: [1, 0.2] }}
            transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.05, ease: "easeOut" }}
          />
        );
      })}
    </span>
  );
}

function FlameAura() {
  return (
    <span className="pointer-events-none absolute -left-1 -top-2 flex gap-0.5" aria-hidden>
      {[0, 0.18, 0.36].map((d, i) => (
        <motion.span
          key={i}
          animate={{ y: [0, -3, 0], scale: [1, 1.25, 1], opacity: [0.85, 1, 0.85], rotate: [-4, 4, -4] }}
          transition={{ duration: 0.7, repeat: Infinity, delay: d, ease: "easeInOut" }}
        >
          <Flame size={12} fill={FIRE} color={FIRE} style={{ filter: `drop-shadow(0 0 4px ${FIRE})` }} />
        </motion.span>
      ))}
    </span>
  );
}

export default function AiRatingStars({ rating = 0 }) {
  const r = Math.max(0, Math.min(10, Math.round(Number(rating) || 0)));
  const isMax = r >= 10;
  const isFire = r === 9;
  const starColor = isFire ? FIRE : VOLT;

  return (
    <div className="relative inline-flex items-center gap-1.5" data-testid="ai-rating-stars">
      {isMax && <ExplosionBurst />}
      {isFire && <FlameAura />}
      <div className="relative flex items-center gap-[1px]">
        {Array.from({ length: 10 }).map((_, i) => {
          const idx = i + 1;
          const filled = idx <= r;
          const el = (
            <Star
              size={13}
              strokeWidth={1.5}
              fill={filled ? starColor : "transparent"}
              color={filled ? starColor : "#52525b"}
              style={filled ? { filter: `drop-shadow(0 0 3px ${starColor}cc)` } : {}}
            />
          );
          if (filled && isMax) {
            return (
              <motion.span
                key={idx}
                animate={{ scale: [1, 1.28, 1] }}
                transition={{ duration: 0.9, repeat: Infinity, delay: idx * 0.04, ease: "easeInOut" }}
                style={{ lineHeight: 0 }}
              >
                {el}
              </motion.span>
            );
          }
          if (filled && isFire) {
            return (
              <motion.span
                key={idx}
                animate={{ y: [0, -1.5, 0] }}
                transition={{ duration: 0.5, repeat: Infinity, delay: idx * 0.05, ease: "easeInOut" }}
                style={{ lineHeight: 0 }}
              >
                {el}
              </motion.span>
            );
          }
          return <span key={idx} style={{ lineHeight: 0 }}>{el}</span>;
        })}
      </div>
      <span
        className="font-mono font-black text-sm"
        style={{ color: starColor, textShadow: (isMax || isFire) ? `0 0 8px ${starColor}` : "none" }}
      >
        {r}
      </span>
    </div>
  );
}
