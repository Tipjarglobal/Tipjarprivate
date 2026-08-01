import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Crown, Zap, Shirt, ChevronLeft, ChevronRight, Trophy, CalendarClock, Hand } from "lucide-react";
import api from "../api";
import { useI18n, formatSelection, formatKickoff, kickoffInfo, displayTeam } from "../i18n";
import { useProseTranslations } from "../proseI18n";

const PAGE = 2; // owner 2026-08: show 2 tips per view

function Bubble({ c, t, tr }) {
  const dateLabel = formatKickoff(c.match_time, t);
  return (
    <div data-testid="master-avatar-bubble-0" className="rounded-2xl bg-surface border border-[#E11D2A]/40 px-4 py-3 shadow-lg select-none">
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <span className="font-heading font-black text-[#E11D2A] text-sm uppercase tracking-wide">TipJarMaster</span>
        {c.avatar_minute != null && (
          <span data-testid="master-avatar-minute-0" className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-[#2ECC57] bg-[#2ECC57]/10 border border-[#2ECC57]/30 rounded-full px-2 py-0.5">
            <Zap size={11} /> {c.avatar_minute}'
          </span>
        )}
        {c.from_codemining && (
          <span data-testid="master-avatar-codemining-0" className="inline-flex items-center gap-1 text-[11px] font-bold text-[#E11D2A] bg-[#E11D2A]/10 border border-[#E11D2A]/40 rounded-full px-2 py-0.5">
            <Zap size={11} /> Codemining
          </span>
        )}
        {c.avatar_scorer && c.avatar_player && (
          <span data-testid="master-avatar-scorer-0" className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-300 bg-amber-500/10 border border-amber-400/40 rounded-full px-2 py-0.5">
            <Shirt size={11} /> {c.avatar_player}
          </span>
        )}
      </div>

      {/* 1) Teams */}
      <p data-testid="master-avatar-teams-0" className="text-base font-bold text-white leading-tight">
        {displayTeam(c.home_team)} <span className="text-zinc-500 font-normal">vs</span> {displayTeam(c.away_team)}
      </p>

      {/* 2) League · 3+4) Date + Time */}
      <div className="mt-1.5 flex items-center gap-2 flex-wrap text-[11px] text-zinc-300">
        {c.league && (
          <span data-testid="master-avatar-league-0" className="inline-flex items-center gap-1 bg-elevated/60 border border-elevated rounded-full px-2 py-0.5">
            <Trophy size={11} className="text-amber-300" /> {c.league}
          </span>
        )}
        {dateLabel && (
          <span data-testid="master-avatar-kickoff-0" className="inline-flex items-center gap-1 bg-elevated/60 border border-elevated rounded-full px-2 py-0.5">
            <CalendarClock size={11} className="text-[#2ECC57]" /> {dateLabel}
          </span>
        )}
      </div>

      {/* pick */}
      <div className="mt-2 flex items-center gap-2 flex-wrap">
        <span className="text-[11px] font-bold text-white bg-[#E11D2A] rounded-full px-2 py-0.5">{formatSelection(c.market, t)}</span>
        {c.odds && <span className="text-[11px] font-mono text-red-200">@ {c.odds}</span>}
      </div>

      {c.avatar_text && (
        <p data-testid="master-avatar-text-0" className="mt-2 text-[12px] text-zinc-400 leading-snug">{tr(c.avatar_text)}</p>
      )}
    </div>
  );
}

// TipJarMaster avatar speech bubbles. Manual swipe only (no auto-rotation), 2 tips per view,
// each bubble clearly showing Teams · League · Date · Time. Only PLAYABLE (upcoming) games.
export function MasterAvatar({ t }) {
  const { lang } = useI18n();
  const [calls, setCalls] = useState([]);
  const [page, setPage] = useState(0);
  const [dir, setDir] = useState(0);
  const [hint, setHint] = useState(true);

  useEffect(() => {
    let alive = true;
    api.get("/master/avatar")
      .then(({ data }) => {
        if (!alive) return;
        const now = Date.now();
        const playable = (data.calls || []).filter((c) => {
          const ts = kickoffInfo(c.match_time).ts;
          return ts != null && ts > now; // only upcoming, must have a valid kickoff
        });
        setCalls(playable);
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  const tr = useProseTranslations(calls.map((c) => c.avatar_text || ""), lang);
  const pages = Math.max(1, Math.ceil(calls.length / PAGE));
  const safePage = ((page % pages) + pages) % pages;
  const view = calls.slice(safePage * PAGE, safePage * PAGE + PAGE);
  const multi = pages > 1;
  const go = (d) => { setDir(d); setPage((p) => p + d); setHint(false); };

  const swipeHint = lang === "de" ? "Wischen für mehr" : lang === "el" ? "Σύρετε για περισσότερα" : "Swipe for more";

  return (
    <div data-testid="master-avatar" className="mb-6 flex items-start gap-3 sm:gap-4">
      <div className="relative shrink-0">
        <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-gradient-to-br from-[#E11D2A] to-[#7a0a12] border border-[#E11D2A]/60 shadow-[0_0_22px_rgba(225,29,42,0.45)] flex items-center justify-center">
          <Crown size={30} className="text-white drop-shadow" />
        </div>
        <span className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-void border border-[#E11D2A] flex items-center justify-center">
          <span className="w-2 h-2 rounded-full bg-[#2ECC57] animate-pulse" />
        </span>
      </div>

      <div className="relative flex-1 min-w-0">
        <div className="absolute -left-2 top-4 w-3 h-3 rotate-45 bg-surface border-l border-b border-[#E11D2A]/40" />
        {calls.length === 0 ? (
          <div className="rounded-2xl bg-surface border border-[#E11D2A]/40 px-4 py-3 shadow-lg">
            <span className="font-heading font-black text-[#E11D2A] text-sm uppercase tracking-wide">TipJarMaster</span>
            <p data-testid="master-avatar-bubble" className="text-sm text-zinc-200 leading-snug mt-1">{t("master.avatar.idle")}</p>
          </div>
        ) : (
          <>
            <AnimatePresence mode="wait" custom={dir}>
              <motion.div
                key={safePage}
                custom={dir}
                drag={multi ? "x" : false}
                dragConstraints={{ left: 0, right: 0 }}
                dragElastic={0.35}
                onDragEnd={(e, info) => { if (info.offset.x < -60) go(1); else if (info.offset.x > 60) go(-1); }}
                initial={{ opacity: 0, x: dir > 0 ? 40 : dir < 0 ? -40 : 0 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: dir > 0 ? -40 : 40 }}
                transition={{ duration: 0.25 }}
                className="grid gap-2 cursor-grab active:cursor-grabbing">
                {view.map((c) => <Bubble key={c.id} c={c} t={t} tr={tr} />)}
              </motion.div>
            </AnimatePresence>

            {multi && (
              <div className="mt-2 flex items-center justify-between">
                <button data-testid="master-avatar-prev" onClick={() => go(-1)}
                  className="w-7 h-7 rounded-full bg-elevated border border-[#E11D2A]/40 flex items-center justify-center text-zinc-300 hover:text-white hover:border-[#E11D2A] transition-colors">
                  <ChevronLeft size={16} />
                </button>
                <div className="flex items-center gap-2">
                  {hint && (
                    <motion.span data-testid="master-avatar-swipe-hint" className="inline-flex items-center gap-1 text-[10px] text-zinc-400"
                      animate={{ x: [-3, 3, -3] }} transition={{ duration: 1.6, repeat: Infinity }}>
                      <Hand size={11} className="text-[#E11D2A]" /> {swipeHint}
                    </motion.span>
                  )}
                  <div className="flex gap-1">
                    {Array.from({ length: pages }).map((_, i) => (
                      <span key={i} className={`w-1.5 h-1.5 rounded-full transition-colors ${i === safePage ? "bg-[#E11D2A]" : "bg-red-900"}`} />
                    ))}
                  </div>
                </div>
                <button data-testid="master-avatar-next" onClick={() => go(1)}
                  className="w-7 h-7 rounded-full bg-elevated border border-[#E11D2A]/40 flex items-center justify-center text-zinc-300 hover:text-white hover:border-[#E11D2A] transition-colors">
                  <ChevronRight size={16} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default MasterAvatar;
