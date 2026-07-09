// Shared notification sounds. The coin "ding" plays when the push opt-in prompt
// appears; richer variants play (best-effort, foreground only) when a push lands:
//   • "explosion" → coin + small explosion  (10★ banker / high-impact)
//   • "fire"      → coin + fire crackle      (9★)
//   • "coin"      → plain coin ding          (default / opt-in prompt)
// Browser autoplay policies block sound until the user has interacted with the
// page, so we swallow NotAllowedError silently — the sound is a nice-to-have.
const SRC = {
  coin: "/coin.wav",
  explosion: "/coin_explosion.wav",
  fire: "/coin_fire.wav",
};

const _cache = {};

function getAudio(kind) {
  const src = SRC[kind] || SRC.coin;
  if (!_cache[src]) {
    const a = new Audio(src);
    a.preload = "auto";
    a.volume = 0.55;
    _cache[src] = a;
  }
  return _cache[src];
}

export function playCoin(kind = "coin") {
  try {
    const a = getAudio(kind);
    a.currentTime = 0;
    const p = a.play();
    if (p && typeof p.catch === "function") p.catch(() => {});
  } catch {
    /* ignore — autoplay blocked or unsupported */
  }
}
