import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, TrendingUp, Flame, Dices, Layers } from "lucide-react";
import { OddsValue } from "./OddsValue";
import { useI18n, localizeMarket, formatSelection } from "../i18n";
import api from "../api";

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
  const cfg = RISK[system.risk] || RISK.safe;
  const { Icon } = cfg;
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
                {t(`sys.title.${system.key}`)}
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

      <p className="text-xs text-zinc-400 mb-3">{t(`sys.sub.${system.key}`)}</p>

      <div className="space-y-2 flex-1">
        {system.selections.map((s) => (
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
                  {s.home_team} <span className="text-zinc-600">vs</span> {s.away_team}
                </span>
              </div>
              {s.combo_markets ? (
                <div className="mt-1 space-y-0.5">
                  {s.combo_markets.map((m, idx) => (
                    <p key={idx} className="text-xs text-zinc-300 leading-snug break-words flex items-start gap-1.5">
                      <span className="text-volt mt-0.5">✓</span> {formatSelection(m, t)}
                    </p>
                  ))}
                  {s.match_time && <p className="text-[10px] text-zinc-600 mt-0.5">{s.match_time}</p>}
                </div>
              ) : (
                <p className="text-xs text-zinc-400 mt-0.5 leading-snug break-words">
                  {formatSelection(s.market, t)}{s.match_time ? ` · ${s.match_time}` : ""}
                </p>
              )}
            </div>
            <div className="text-right shrink-0 pt-0.5">
              <OddsValue odds={s.odds} className={`font-mono font-bold text-sm ${cfg.odds}`} />
            </div>
          </div>
        ))}
      </div>
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

  return (
    <section id="systeme" data-testid="systems-section" className="mb-10 scroll-mt-24">
      <div className="flex items-center gap-2.5 mb-5">
        <Layers className="text-volt" size={22} />
        <h3 className="font-heading font-black text-white text-2xl tracking-tight">{t("sys.heading")}</h3>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {visible.map((s) => <SystemCard key={s.key} system={s} />)}
      </div>
    </section>
  );
};

export default Systems;
