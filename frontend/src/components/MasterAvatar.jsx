import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Crown, Zap, Shirt } from "lucide-react";
import api from "../api";
import { useI18n, formatSelection } from "../i18n";
import { useProseTranslations } from "../proseI18n";

// TipJarMaster avatar with a speech bubble that cycles through today's confident
// minute-goal calls (owner 2026-07-30). Crown/logo style, red Master branding.
// Bubble text is translated to the viewer's language via the prose-translation cache.
export function MasterAvatar({ t }) {
  const { lang } = useI18n();
  const [calls, setCalls] = useState([]);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    let alive = true;
    api.get("/master/avatar")
      .then(({ data }) => { if (alive) setCalls(data.calls || []); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (calls.length <= 1) return;
    const iv = setInterval(() => setIdx((i) => (i + 1) % calls.length), 6500);
    return () => clearInterval(iv);
  }, [calls.length]);

  // translate every dynamic call's German prose to the viewer's language
  const tr = useProseTranslations(calls.map((c) => c.avatar_text || ""), lang);

  const active = calls[idx];
  const bubble = active ? tr(active.avatar_text) : t("master.avatar.idle");

  return (
    <div data-testid="master-avatar" className="mb-6 flex items-start gap-3 sm:gap-4">
      {/* Crown / logo avatar */}
      <div className="relative shrink-0">
        <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-[#E11D2A] to-[#7a0a12] border border-[#E11D2A]/60 shadow-[0_0_22px_rgba(225,29,42,0.45)] flex items-center justify-center">
          <Crown size={30} className="text-white drop-shadow" />
        </div>
        <span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-void border border-[#E11D2A] flex items-center justify-center">
          <span className="w-2 h-2 rounded-full bg-[#2ECC57] animate-pulse" />
        </span>
      </div>

      {/* Speech bubble */}
      <div className="relative flex-1 min-w-0">
        <div className="absolute -left-2 top-4 w-3 h-3 rotate-45 bg-surface border-l border-b border-[#E11D2A]/40" />
        <div className="rounded-2xl bg-surface border border-[#E11D2A]/40 px-4 py-3 shadow-lg">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-heading font-black text-[#E11D2A] text-sm uppercase tracking-wide">TipJarMaster</span>
            {active && (
              <span data-testid="master-avatar-minute"
                className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-[#2ECC57] bg-[#2ECC57]/10 border border-[#2ECC57]/30 rounded-full px-2 py-0.5">
                <Zap size={11} /> {active.avatar_minute}'
              </span>
            )}
            {active?.avatar_scorer && active?.avatar_player && (
              <span data-testid="master-avatar-scorer"
                className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-300 bg-amber-500/10 border border-amber-400/40 rounded-full px-2 py-0.5">
                <Shirt size={11} /> {active.avatar_player} · 🔥 in Galaform
              </span>
            )}
          </div>
          <AnimatePresence mode="wait">
            <motion.p
              key={idx + (active?.id || "x")}
              data-testid="master-avatar-bubble"
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.3 }}
              className="text-sm text-zinc-200 leading-snug">
              {bubble}
            </motion.p>
          </AnimatePresence>
          {active && (
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <span className="text-[11px] font-bold text-white bg-[#E11D2A] rounded-full px-2 py-0.5">
                {formatSelection(active.market, t)}
              </span>
              {active.odds && (
                <span className="text-[11px] font-mono text-red-200">@ {active.odds}</span>
              )}
              {calls.length > 1 && (
                <span className="ml-auto flex gap-1">
                  {calls.map((_, i) => (
                    <span key={i} className={`w-1.5 h-1.5 rounded-full ${i === idx ? "bg-[#E11D2A]" : "bg-red-900"}`} />
                  ))}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default MasterAvatar;
