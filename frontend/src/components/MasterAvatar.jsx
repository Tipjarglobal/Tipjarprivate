import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Crown, Zap, Shirt } from "lucide-react";
import api from "../api";
import { useI18n, formatSelection } from "../i18n";
import { useProseTranslations } from "../proseI18n";

// TipJarMaster avatar with up to THREE speech bubbles showing today's most confident
// minute-goal calls at once (owner 2026-06). If more than 3 calls exist, the set of 3
// rotates. Bubble text is translated to the viewer's language via the prose cache.
const WINDOW = 3;

export function MasterAvatar({ t }) {
  const { lang } = useI18n();
  const [calls, setCalls] = useState([]);
  const [page, setPage] = useState(0);

  useEffect(() => {
    let alive = true;
    api.get("/master/avatar")
      .then(({ data }) => { if (alive) setCalls(data.calls || []); })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const pages = Math.max(1, Math.ceil(calls.length / WINDOW));
  useEffect(() => {
    if (pages <= 1) return;
    const iv = setInterval(() => setPage((p) => (p + 1) % pages), 8000);
    return () => clearInterval(iv);
  }, [pages]);

  const tr = useProseTranslations(calls.map((c) => c.avatar_text || ""), lang);
  const shown = calls.slice(page * WINDOW, page * WINDOW + WINDOW);

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

      {/* Speech bubbles — up to 3 stacked */}
      <div className="relative flex-1 min-w-0">
        <div className="absolute -left-2 top-4 w-3 h-3 rotate-45 bg-surface border-l border-b border-[#E11D2A]/40" />
        {shown.length === 0 ? (
          <div className="rounded-2xl bg-surface border border-[#E11D2A]/40 px-4 py-3 shadow-lg">
            <span className="font-heading font-black text-[#E11D2A] text-sm uppercase tracking-wide">TipJarMaster</span>
            <p data-testid="master-avatar-bubble" className="text-sm text-zinc-200 leading-snug mt-1">{t("master.avatar.idle")}</p>
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div
              key={page}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.3 }}
              className="flex flex-col gap-2">
              {shown.map((c, k) => (
                <div key={c.id || k} data-testid={`master-avatar-bubble-${k}`}
                  className="rounded-2xl bg-surface border border-[#E11D2A]/40 px-4 py-3 shadow-lg">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    {k === 0 && <span className="font-heading font-black text-[#E11D2A] text-sm uppercase tracking-wide">TipJarMaster</span>}
                    <span data-testid={`master-avatar-minute-${k}`}
                      className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-[#2ECC57] bg-[#2ECC57]/10 border border-[#2ECC57]/30 rounded-full px-2 py-0.5">
                      <Zap size={11} /> {c.avatar_minute}'
                    </span>
                    {c.avatar_scorer && c.avatar_player && (
                      <span data-testid={`master-avatar-scorer-${k}`}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-300 bg-amber-500/10 border border-amber-400/40 rounded-full px-2 py-0.5">
                        <Shirt size={11} /> {c.avatar_player} · 🔥 in Galaform
                      </span>
                    )}
                  </div>
                  <p data-testid={`master-avatar-text-${k}`} className="text-sm text-zinc-200 leading-snug">
                    {tr(c.avatar_text)}
                  </p>
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    <span className="text-[11px] font-bold text-white bg-[#E11D2A] rounded-full px-2 py-0.5">
                      {formatSelection(c.market, t)}
                    </span>
                    {c.odds && <span className="text-[11px] font-mono text-red-200">@ {c.odds}</span>}
                  </div>
                </div>
              ))}
              {pages > 1 && (
                <div className="flex gap-1 pl-1">
                  {Array.from({ length: pages }).map((_, i) => (
                    <span key={i} className={`w-1.5 h-1.5 rounded-full ${i === page ? "bg-[#E11D2A]" : "bg-red-900"}`} />
                  ))}
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}

export default MasterAvatar;
