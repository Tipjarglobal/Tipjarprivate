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
  expert: "/coin_expert.wav",
};

const _cache = {};

// The phone's mute/ring switch is NOT readable from JavaScript. Our own
// `new Audio().play()` bypasses it, so on touch/mobile devices we NEVER play a
// custom sound — the system push notification (which DOES respect mute / Do Not
// Disturb) is the single source of sound there. On desktop we honour an explicit
// user preference (tj_sound).
export function isMobileDevice() {
  if (typeof window === "undefined") return false;
  try {
    if (window.matchMedia && window.matchMedia("(pointer: coarse)").matches) return true;
  } catch { /* ignore */ }
  return /Android|iPhone|iPad|iPod|Mobile|Silk|Kindle|BlackBerry|Opera Mini/i.test(navigator.userAgent || "");
}

export function soundsEnabled() {
  if (isMobileDevice()) return false;
  try { return localStorage.getItem("tj_sound") !== "off"; } catch { return true; }
}

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
  if (!soundsEnabled()) return;
  try {
    const a = getAudio(kind);
    a.currentTime = 0;
    const p = a.play();
    if (p && typeof p.catch === "function") p.catch(() => {});
  } catch {
    /* ignore — autoplay blocked or unsupported */
  }
}
