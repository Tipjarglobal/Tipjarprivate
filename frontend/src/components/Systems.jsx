import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, TrendingUp, Flame, Dices, Layers } from "lucide-react";
import { OddsValue } from "./OddsValue";
import api from "../api";

const RISK = {
  safe: {
    label: "Sicher", Icon: ShieldCheck,
    ring: "border-volt/40", grad: "from-volt/10", chip: "bg-volt text-void",
    accent: "text-volt", odds: "text-volt",
  },
  value: {
    label: "Value", Icon: TrendingUp,
    ring: "border-cyan-400/40", grad: "from-cyan-400/10", chip: "bg-cyan-400 text-void",
    accent: "text-cyan-300", odds: "text-cyan-300",
  },
  risk: {
    label: "Risk", Icon: Flame,
    ring: "border-orange-400/40", grad: "from-orange-400/10", chip: "bg-orange-400 text-void",
    accent: "text-orange-300", odds: "text-orange-300",
  },
  gamble: {
    label: "Zocker", Icon: Dices,
    ring: "border-rose-400/40", grad: "from-rose-400/10", chip: "bg-rose-400 text-void",
    accent: "text-rose-300", odds: "text-rose-300",
  },
};

const SystemCard = ({ system }) => {
  const cfg = RISK[system.risk] || RISK.safe;
  const { Icon } = cfg;
  if (!system.selections || system.selections.length < 2) return null;
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
                {cfg.label}
              </span>
              <h3 className="font-heading font-black text-white text-base sm:text-lg leading-none truncate">
                {system.title}
              </h3>
            </div>
            <p className="text-xs text-zinc-400 mt-1.5 truncate">{system.week} · {system.system_label}</p>
          </div>
        </div>
        <div className="text-right shrink-0">
          <p className="text-[10px] uppercase tracking-widest text-zinc-500">Gesamtquote</p>
          <p className={`font-mono font-black text-2xl ${cfg.odds}`} data-testid={`system-odds-${system.key}`}>
            {system.total_odds}
          </p>
        </div>
      </div>

      <p className="text-xs text-zinc-400 mb-3">{system.subtitle}</p>

      <div className="space-y-2 flex-1">
        {system.selections.map((s) => (
          <div
            key={s.id}
            data-testid={`system-${system.key}-leg`}
            className="flex items-start justify-between gap-3 rounded-lg bg-void border border-elevated px-3 py-2.5"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                {s.banker && (
                  <span
                    data-testid="system-banker-badge"
                    title="Banker (steht in jeder Spalte)"
                    className={`inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-widest rounded px-1.5 py-0.5 shrink-0 ${cfg.chip}`}
                  >
                    <ShieldCheck size={10} /> Banker
                  </span>
                )}
                <span className="font-heading font-bold text-white text-sm truncate">
                  {s.home_team} <span className="text-zinc-600">vs</span> {s.away_team}
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-0.5 leading-snug break-words">
                {s.market}{s.match_time ? ` · ${s.match_time}` : ""}
              </p>
            </div>
            <div className="text-right shrink-0 pt-0.5">
              <OddsValue odds={s.odds} className={`font-mono font-bold text-sm ${cfg.odds}`} />
            </div>
          </div>
        ))}
      </div>

      <p className={`text-[11px] text-zinc-500 mt-4 border-l-2 pl-2 leading-snug ${cfg.ring}`}>
        {system.key === "lock" && "Die Banker stehen in jeder Spalte. Beim System darfst du einen Tipp verlieren und gewinnst trotzdem."}
        {system.key === "value" && "Nur Auswahlen ab Quote 1,50 — mehr Wert pro Spiel, 1 Fehler abgesichert."}
        {system.key === "risk" && "Bet-Builder pro Spiel: Doppelte Chance kombiniert mit Beide-treffen. Höheres Risiko, höhere Quote."}
        {system.key === "gamble" && "Reine Zocker-Kombi mit genauen Ergebnissen & Außenseitern. Kleiner Einsatz, großer Traum."}
      </p>
    </motion.div>
  );
};

export const Systems = () => {
  const [systems, setSystems] = useState([]);

  useEffect(() => {
    api.get("/systems").then(({ data }) => setSystems(data.systems || [])).catch(() => {});
  }, []);

  const visible = systems.filter((s) => s.selections && s.selections.length >= 2);
  if (visible.length === 0) return null;

  return (
    <section id="systeme" data-testid="systems-section" className="mb-10 scroll-mt-24">
      <div className="flex items-center gap-2.5 mb-5">
        <Layers className="text-volt" size={22} />
        <h3 className="font-heading font-black text-white text-2xl tracking-tight">Systeme der Woche</h3>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {visible.map((s) => <SystemCard key={s.key} system={s} />)}
      </div>
    </section>
  );
};

export default Systems;
