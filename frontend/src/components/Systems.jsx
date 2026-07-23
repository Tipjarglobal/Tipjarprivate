import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, TrendingUp, Flame, Dices, Layers, Timer, CalendarDays, CalendarRange, Clock, Trophy, Ticket } from "lucide-react";
import { OddsValue } from "./OddsValue";
import { useI18n, localizeMarket, formatSelection, toLatin, formatKickoff, kickoffInfo } from "../i18n";
import api from "../api";
import { PlaySlipOverlay } from "./PlaySlipOverlay";

const LegMeta = ({ matchTime, league }) => {
  const { t } = useI18n();
  const ko = formatKickoff(matchTime, t);
  if (!ko && !league) return null;
  return (
    <div className="flex flex-wrap items-center gap-2 mt-1.5">
      {ko && (
        <span className="inline-flex items-center gap-1 rounded-md bg-volt/10 border border-volt/30 px-2 py-0.5 text-[11px] font-bold text-volt">
          <Clock size={11} />{ko}
        </span>
      )}
      {league && (
        <span className="inline-flex items-center gap-1 min-w-0 text-[10px] text-zinc-500 font-medium"><Trophy size={11} className="text-volt/70 shrink-0" /><span className="truncate">{league}</span></span>
      )}
    </div>
  );
};

const RISK = {
  safe: {
    riskKey: "safe", Icon: ShieldCheck,
    ring: "border-volt/40", grad: "from-volt/10", chip: "bg-volt text-void",
    accent: "text-volt", odds: "text-volt",
  },
  value: {
    riskKey: "value", Icon: TrendingUp,
    ring: "border-cyan-400/40", grad: "from-cyan-400/10", chip: "bg-cyan-400 text-void",
    accent: "text-cyan-300", odds: "text-cyan-300",
  },
  risk: {
    riskKey: "risk", Icon: Flame,
    ring: "border-orange-400/40", grad: "from-orange-400/10", chip: "bg-orange-400 text-void",
    accent: "text-orange-300", odds: "text-orange-300",
  },
  gamble: {
    riskKey: "gamble", Icon: Dices,
    ring: "border-rose-400/40", grad: "from-rose-400/10", chip: "bg-rose-400 text-void",
    accent: "text-rose-300", odds: "text-rose-300",
  },
};

const SystemCard = ({ system }) => {
  const { t } = useI18n();
  const [playData, setPlayData] = useState(null);
  const cfg = RISK[system.risk] || RISK.safe;
  const { Icon } = cfg;
  const titleKey = `sys.title.${system.key}`;
  const subKey = `sys.sub.${system.key}`;
  const title = t(titleKey) === titleKey ? (system.title || system.key) : t(titleKey);
  const subtitle = t(subKey) === subKey ? (system.subtitle || "") : t(subKey);
  const hasCombo = (system.selections || []).some((s) => s.combo_markets);
  if (!system.selections || (system.selections.length < 2 && !hasCombo)) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      data-testid={`system-card-${system.key}`}
      className={`rounded-2xl border ${cfg.ring} bg-gradient-to-br ${cfg.grad} via-surface to-surface p-5 sm:p-6 flex flex-col`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center shrink-0`}>
            <Icon className={cfg.accent} size={20} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={`text-[9px] font-black uppercase tracking-widest rounded px-1.5 py-0.5 ${cfg.chip}`}>
                {t(`sys.risk.${cfg.riskKey}`)}
              </span>
              <h3 className="font-heading font-black text-white text-base sm:text-lg leading-none truncate">
                {title}
              </h3>
            </div>
            <p className="text-xs text-zinc-400 mt-1.5 truncate">{system.week} · {system.count} {t("sys.picks")}</p>
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="text-[10px] uppercase tracking-widest text-zinc-500">{t("sys.totalodds")}</p>
          <p className={`font-mono font-black text-2xl ${cfg.odds}`} data-testid={`system-odds-${system.key}`}>
            {system.total_odds}
          </p>
        </div>
      </div>

      <p className="text-xs text-zinc-400 mb-3">{subtitle}</p>

      <div className="space-y-2 flex-1">
        {[...system.selections].sort((a, b) => (kickoffInfo(a.match_time).ts ?? Infinity) - (kickoffInfo(b.match_time).ts ?? Infinity)).map((s) => (
          <div
            key={s.id}
            data-testid={`system-${system.key}-leg`}
            className="flex items-start justify-between gap-3 rounded-lg bg-void border border-elevated px-3 py-2.5"
          >
            <div className="min-w-0">
              <div className="flex items-start gap-2 flex-wrap">
                {s.banker && (
                  <span
                    data-testid="system-banker-badge"
                    className={`inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-widest rounded px-1.5 py-0.5 shrink-0 mt-0.5 ${cfg.chip}`}
                  >
                    <ShieldCheck size={10} /> {t("sys.banker")}
                  </span>
                )}
                <span className="font-heading font-bold text-white text-sm break-words min-w-0">
                  {toLatin(s.home_team)} <span className="text-zinc-600">vs</span> {toLatin(s.away_team)}
                </span>
              </div>
              {s.combo_markets ? (
                <div className="mt-1 space-y-0.5">
                  {s.combo_markets.map((m, idx) => (
                    <p key={idx} className="text-xs text-zinc-300 leading-snug break-words flex items-start gap-1.5">
                      <span className="text-volt mt-0.5">✓</span> {formatSelection(m, t)}
                    </p>
                  ))}
                  <LegMeta matchTime={s.match_time} league={s.league} />
                </div>
              ) : (
                <>
                  <p className="text-xs text-zinc-400 mt-0.5 leading-snug break-words">
                    {formatSelection(s.market, t)}
                  </p>
                  <LegMeta matchTime={s.match_time} league={s.league} />
                </>
              )}
            </div>
            <div className="text-right shrink-0 pt-0.5">
              <OddsValue odds={s.odds} className={`font-mono font-bold text-sm ${cfg.odds}`} />
            </div>
          </div>
        ))}
      </div>

      <button
        data-testid={`play-system-${system.key}`}
        onClick={() => {
          const legs = [...system.selections]
            .sort((a, b) => (kickoffInfo(a.match_time).ts ?? Infinity) - (kickoffInfo(b.match_time).ts ?? Infinity))
            .map((s) => ({
              match: `${toLatin(s.home_team)} vs ${toLatin(s.away_team)}`,
              market: s.combo_markets
                ? s.combo_markets.map((m) => formatSelection(m, t)).join(" + ")
                : formatSelection(s.market, t),
              odds: s.odds,
              kickoff: s.match_time,
            }));
          setPlayData({ legs, meta: { totalOdds: system.total_odds, title } });
        }}
        className="w-full mt-4 flex items-center justify-center gap-2 rounded-xl bg-volt text-void font-bold text-sm py-2.5 hover:brightness-110 active:scale-[0.99] transition-all"
      >
        <Ticket size={16} /> {t("play.btn")}
      </button>
      <PlaySlipOverlay data={playData} onClose={() => setPlayData(null)} />
    </motion.div>
  );
};

export const Systems = () => {
  const { t } = useI18n();
  const [systems, setSystems] = useState([]);

  useEffect(() => {
    api.get("/systems").then(({ data }) => setSystems(data.systems || [])).catch(() => {});
  }, []);

  const visible = systems.filter((s) => s.selections
    && (s.selections.length >= 2 || s.selections.some((sel) => sel.combo_markets)));
  if (visible.length === 0) return null;

  // Split slips into time buckets — every slip lands in exactly one.
  const BUCKETS = [
    { k: "now", label: "sys.bucket.now", Icon: Timer },
    { k: "today", label: "sys.bucket.today", Icon: CalendarDays },
    { k: "week", label: "sys.bucket.week", Icon: CalendarRange },
  ];
  const grouped = BUCKETS.map((b) => ({
    ...b,
    items: visible.filter((s) => (s.time_bucket || "week") === b.k),
  })).filter((b) => b.items.length > 0);

  return (
    <section id="systeme" data-testid="systems-section" className="mb-10 scroll-mt-24">
      <div className="flex items-center gap-2.5 mb-5">
        <Layers className="text-volt" size={22} />
        <h3 className="font-heading font-black text-white text-2xl tracking-tight">{t("sys.heading")}</h3>
      </div>
      <div className="space-y-8">
        {grouped.map((b) => (
          <div key={b.k} data-testid={`systems-bucket-${b.k}`}>
            <div className="flex items-center gap-2 mb-3">
              <b.Icon size={16} className="text-volt" />
              <h4 className="font-heading font-black uppercase tracking-widest text-sm text-volt">{t(b.label)}</h4>
              <span className="text-[11px] text-zinc-500 font-mono">({b.items.length})</span>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              {b.items.map((s) => <SystemCard key={s.key} system={s} />)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};

export default Systems;
