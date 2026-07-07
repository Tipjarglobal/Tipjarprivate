import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Layers, ShieldCheck, TrendingUp } from "lucide-react";
import api from "../api";

export const SystemSlipCard = () => {
  const [slip, setSlip] = useState(null);

  useEffect(() => {
    api.get("/system-slip").then(({ data }) => setSlip(data)).catch(() => {});
  }, []);

  if (!slip || !slip.selections || slip.selections.length < 3) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      data-testid="system-slip-card"
      className="mb-8 rounded-2xl border border-volt/40 bg-gradient-to-br from-volt/10 via-surface to-surface p-5 sm:p-6"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-10 h-10 rounded-xl bg-volt/15 flex items-center justify-center">
            <Layers className="text-volt" size={20} />
          </div>
          <div>
            <h3 className="font-heading font-black text-white text-lg leading-none">System-Schein der Woche</h3>
            <p className="text-xs text-zinc-400 mt-1">{slip.week} · {slip.system_label}</p>
          </div>
        </div>
        <div className="text-right">
          <p className="text-[10px] uppercase tracking-widest text-zinc-500">Gesamtquote</p>
          <p className="font-mono font-black text-2xl text-volt flex items-center gap-1" data-testid="system-slip-total-odds">
            <TrendingUp size={16} /> {slip.total_odds}
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {slip.selections.map((s) => (
          <div
            key={s.id}
            data-testid={`system-slip-leg-${s.id}`}
            className="flex items-center justify-between gap-3 rounded-lg bg-void border border-elevated px-3 py-2.5"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                {s.banker && (
                  <span
                    data-testid="system-slip-banker-badge"
                    title="Banker (steht in jeder Spalte)"
                    className="inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-widest text-void bg-volt rounded px-1.5 py-0.5 shrink-0"
                  >
                    <ShieldCheck size={10} /> Banker
                  </span>
                )}
                <span className="font-heading font-bold text-white text-sm truncate">
                  {s.home_team} <span className="text-zinc-600">vs</span> {s.away_team}
                </span>
              </div>
              <p className="text-xs text-zinc-400 mt-0.5 truncate">
                {s.market}{s.match_time ? ` · ${s.match_time}` : ""}
              </p>
            </div>
            <div className="text-right shrink-0">
              <span className="font-mono font-bold text-volt text-sm">{s.odds}</span>
              <p className="text-[10px] text-zinc-500">{s.rating}★</p>
            </div>
          </div>
        ))}
      </div>

      <p className="text-[11px] text-zinc-500 mt-4 border-l-2 border-volt/50 pl-2 leading-snug">
        Die <span className="text-volt font-semibold">Banker</span> stehen in jeder Spalte. Beim {slip.system_label} darfst du
        einen Tipp verlieren und gewinnst trotzdem — TipJarHQ bündelt automatisch die sichersten Banker für dich.
      </p>
    </motion.div>
  );
};
