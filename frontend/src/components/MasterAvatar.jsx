import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Crown, Zap, Shirt, ChevronLeft, ChevronRight, Trophy, CalendarClock, Hand, ShieldCheck } from "lucide-react";
import api from "../api";
import { useI18n, formatSelection, formatKickoff, kickoffInfo, displayTeam } from "../i18n";
import { useProseTranslations } from "../proseI18n";

const PAGE = 2;

// GENERELLER Safety Glitch Detector - für JEDES Team, nicht nur 3 Teams
function detectSafetyMessage(call) {
  const market = (call.market || "").toLowerCase();
  const home = displayTeam(call.home_team);
  const away = displayTeam(call.away_team);
  // Team aus Market extrahieren wenn möglich
  let team = home;
  if (market.includes(away.toLowerCase())) team = away;

  // TYP5 / TYP1 - DNB / trifft und verliert nicht
  if (market.includes("draw no bet") || market.includes("dnb") || market.includes("verliert nicht") || market.includes("x2") || market.includes("1x")) {
    return `🛡️ ${team} trifft und verliert nicht`;
  }
  // TYP4 - Immer Lieferant Über 0.5 Team
  if (market.includes("über 0.5") || market.includes("ueber 0.5") || market.includes("over 0.5")) {
    if (market.includes("team") || market.includes("trifft")) {
      return `⚽ ${team} trifft`;
    }
    return `⚽ ${team} trifft - Over 0.5 Safe`;
  }
  // TYP2 - 1 bis 4 Tore
  if ((market.includes("x2") && market.includes("über")) || market.includes("1 bis 4") || market.includes("1-5 tore") || market.includes("unter 5.5") || (market.includes("über") && market.includes("unter"))) {
    return `🔒 ${team} wird 1 bis 4 mal treffen`;
  }
  // TYP7 / TYP9 - Master Pille
  if (market.includes("assist") || (market.includes("sieg") && market.includes("btts")) || market.includes("beide treffen")) {
    return `🎯 ${team} trifft oder bereitet vor`;
  }
  // Fallback generisch
  if (call.avatar_text && call.avatar_text.toLowerCase().includes("trifft")) {
    return call.avatar_text;
  }
  return `✅ ${team} Safety Call - ${formatSelection(call.market, (k)=>k)}`;
}

function Bubble({ c, t, tr }) {
  const dateLabel = formatKickoff(c.match_time, t);
  return (
    <div data-testid="master-avatar-bubble-0" className="rounded-2xl bg-surface border border-[#E11D2A]/40 px-4 py-3 shadow-lg select-none">
      <div className="flex items-center gap-2 mb-1.5 flex-wrap">
        <span className="font-heading font-black text-[#E11D2A] text-sm uppercase tracking-wide">TipJarMaster</span>
        {c.avatar_minute != null && (
          <span className="inline-flex items-center gap-1 text-[11px] font-mono font-bold text-[#2ECC57] bg-[#2ECC57]/10 border border-[#2ECC57]/30 rounded-full px-2 py-0.5">
            <Zap size={11} /> {c.avatar_minute}'
          </span>
        )}
        {c.from_codemining && (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#E11D2A] bg-[#E11D2A]/10 border border-[#E11D2A]/40 rounded-full px-2 py-0.5">
            <Zap size={11} /> Codemining
          </span>
        )}
        {c.avatar_scorer && c.avatar_player && (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-300 bg-amber-500/10 border border-amber-400/40 rounded-full px-2 py-0.5">
            <Shirt size={11} /> {c.avatar_player}
          </span>
        )}
        {/* NEU: Safety Badge wenn Glitch */}
        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-300 bg-emerald-500/10 border border-emerald-400/30 rounded-full px-2 py-0.5">
          <ShieldCheck size={11} /> SAFE
        </span>
      </div>

      <p className="text-base font-bold text-white leading-tight">
        {displayTeam(c.home_team)} <span className="text-zinc-500 font-normal">vs</span> {displayTeam(c.away_team)}
      </p>

      <div className="mt-1.5 flex items-center gap-2 flex-wrap text-[11px] text-zinc-300">
        {c.league && (
          <span className="inline-flex items-center gap-1 bg-elevated/60 border border-elevated rounded-full px-2 py-0.5">
            <Trophy size={11} className="text-amber-300" /> {c.league}
          </span>
        )}
        {dateLabel && (
          <span className="inline-flex items-center gap-1 bg-elevated/60 border border-elevated rounded-full px-2 py-0.5">
            <CalendarClock size={11} className="text-[#2ECC57]" /> {dateLabel}
          </span>
        )}
      </div>

      <div className="mt-2 flex items-center gap-2 flex-wrap">
        <span className="text-[11px] font-bold text-white bg-[#E11D2A] rounded-full px-2 py-0.5">{formatSelection(c.market, t)}</span>
        {c.odds && <span className="text-[11px] font-mono text-red-200">@ {c.odds}</span>}
      </div>

      {c.avatar_text && (
        <p className="mt-2 text-[12px] text-zinc-400 leading-snug">{tr(c.avatar_text)}</p>
      )}
    </div>
  );
}

export function MasterAvatar({ t }) {
  const { lang } = useI18n();
  const [calls, setCalls] = useState([]);
  const [page, setPage] = useState(0);
  const [dir, setDir] = useState(0);
  const [hint, setHint] = useState(true);
  const [speechIdx, setSpeechIdx] = useState(0);

  useEffect(() => {
    let alive = true;
    api.get("/master/avatar")
      .then(({ data }) => {
        if (!alive) return;
        const now = Date.now();
        const playable = (data.calls || []).filter((c) => {
          const ts = kickoffInfo(c.match_time).ts;
          return ts != null && ts > now;
        });
        setCalls(playable);
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);

  // Safety Speech Rotation - generell für alle Teams
  const safetySpeeches = React.useMemo(() => {
    if (calls.length === 0) return [];
    return calls.map(detectSafetyMessage).filter(Boolean);
  }, [calls]);

  // Auto-Rotate Safety Speech alle 4 Sekunden
  useEffect(() => {
    if (safetySpeeches.length <= 1) return;
    const iv = setInterval(() => {
      setSpeechIdx((i) => (i + 1) % safetySpeeches.length);
    }, 4000);
    return () => clearInterval(iv);
  }, [safetySpeeches.length]);

  const tr = useProseTranslations(calls.map((c) => c.avatar_text || ""), lang);
  const pages = Math.max(1, Math.ceil(calls.length / PAGE));
  const safePage = ((page % pages) + pages) % pages;
  const view = calls.slice(safePage * PAGE, safePage * PAGE + PAGE);
  const multi = pages > 1;
  const go = (d) => { setDir(d); setPage((p) => p + d); setHint(false); };

  const swipeHint = lang === "de" ? "Wischen für mehr" : lang === "el" ? "Σύρετε για περισσότερα" : "Swipe for more";

  const currentSpeech = safetySpeeches[speechIdx] || (lang==="de" ? "Ich lese die heutigen Spiele – meine sicheren Tor-Calls erscheinen gleich hier. Nur die starke Seite, klare Minuten." : t("master.avatar.idle"));

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
        
        {/* NEU: TOP Safety Speech Blase - GENERELL */}
        <div className="rounded-2xl bg-gradient-to-br from-surface to-elevated border border-emerald-500/30 px-4 py-3 shadow-lg mb-2">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-heading font-black text-emerald-400 text-sm uppercase tracking-wide">TipJarMaster</span>
            <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-300 bg-emerald-500/20 border border-emerald-400/40 rounded-full px-2 py-0.5 animate-pulse">
              <ShieldCheck size={10} /> SAFETY GLITCH
            </span>
          </div>
          <AnimatePresence mode="wait">
            <motion.p
              key={speechIdx}
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.3 }}
              className="text-sm font-bold text-white leading-snug"
            >
              {currentSpeech}
            </motion.p>
          </AnimatePresence>
          {safetySpeeches.length > 1 && (
            <div className="mt-2 flex gap-1">
              {safetySpeeches.map((_, i) => (
                <span key={i} className={`h-1 rounded-full transition-all ${i===speechIdx ? "w-6 bg-emerald-400" : "w-1.5 bg-emerald-900"}`} />
              ))}
            </div>
          )}
        </div>

        {calls.length === 0 ? (
          <div className="rounded-2xl bg-surface border border-[#E11D2A]/40 px-4 py-3 shadow-lg">
            <span className="font-heading font-black text-[#E11D2A] text-sm uppercase tracking-wide">TipJarMaster</span>
            <p className="text-sm text-zinc-200 leading-snug mt-1">{currentSpeech}</p>
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
                <button onClick={() => go(-1)} className="w-7 h-7 rounded-full bg-elevated border border-[#E11D2A]/40 flex items-center justify-center text-zinc-300 hover:text-white">
                  <ChevronLeft size={16} />
                </button>
                <div className="flex items-center gap-2">
                  {hint && (
                    <motion.span className="inline-flex items-center gap-1 text-[10px] text-zinc-400" animate={{ x: [-3, 3, -3] }} transition={{ duration: 1.6, repeat: Infinity }}>
                      <Hand size={11} className="text-[#E11D2A]" /> {swipeHint}
                    </motion.span>
                  )}
                  <div className="flex gap-1">
                    {Array.from({ length: pages }).map((_, i) => (
                      <span key={i} className={`w-1.5 h-1.5 rounded-full ${i === safePage ? "bg-[#E11D2A]" : "bg-red-900"}`} />
                    ))}
                  </div>
                </div>
                <button onClick={() => go(1)} className="w-7 h-7 rounded-full bg-elevated border border-[#E11D2A]/40 flex items-center justify-center text-zinc-300 hover:text-white">
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
