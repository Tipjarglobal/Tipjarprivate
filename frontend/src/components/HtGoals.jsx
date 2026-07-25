import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Timer, RefreshCw, Clock, Zap } from "lucide-react";
import api from "../api";
import { useI18n, toLatin } from "../i18n";

const confStyle = (c) => {
  if (c >= 85) return { chip: "bg-[#2ECC57] text-black", txt: "text-[#2ECC57]" };
  if (c >= 75) return { chip: "bg-volt text-black", txt: "text-volt" };
  return { chip: "bg-amber-400 text-black", txt: "text-amber-300" };
};

const fmtWhen = (iso) => {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString([], { weekday: "short", day: "2-digit", month: "2-digit" })
      + " · " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

export const HtGoals = () => {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/ht-goal-forecast");
      setRows(r.data.matches || []);
    } catch {
      setRows([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6" data-testid="ht-goals">
      <div className="flex items-start justify-between gap-4 mb-2">
        <div>
          <h2 className="font-heading font-black text-2xl sm:text-3xl flex items-center gap-2">
            <Timer className="text-orange-400" size={26} /> {t("htg.title")}
          </h2>
          <p className="text-sm text-zinc-400 mt-1 max-w-2xl">{t("htg.intro")}</p>
        </div>
        <button onClick={load} data-testid="htg-refresh" className="shrink-0 flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-full bg-elevated text-zinc-300 hover:text-white transition-colors">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> {t("thirst.refresh")}
        </button>
      </div>

      {loading ? (
        <div className="text-center text-zinc-500 py-20" data-testid="htg-loading">{t("thirst.loading")}</div>
      ) : rows.length === 0 ? (
        <div className="text-center text-zinc-500 py-16 rounded-2xl border border-dashed border-elevated" data-testid="htg-empty">
          {t("htg.empty")}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4 mt-4">
          {rows.map((r, i) => {
            const cs = confStyle(r.confidence);
            return (
              <motion.div
                key={`${r.home}-${r.away}-${i}`}
                data-testid="htg-card"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.4) }}
                className="rounded-2xl bg-surface border border-elevated p-4 hover:border-orange-400/40 transition-colors"
              >
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="font-heading font-black text-lg text-white truncate">
                    {toLatin(r.home)} <span className="text-zinc-600 text-sm">vs</span> {toLatin(r.away)}
                  </span>
                  <span className={`text-xs font-black px-2 py-1 rounded-full ${cs.chip}`}>{r.confidence}%</span>
                </div>

                <div className="flex items-center gap-2 text-[13px] text-zinc-300 mb-2">
                  <Clock size={14} className="shrink-0 text-zinc-500" />
                  <span>{r.league ? `${toLatin(r.league)} · ` : ""}{fmtWhen(r.kickoff)}</span>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-[12px] text-zinc-400 mb-3">
                  <span className="rounded bg-void/60 px-2 py-0.5">{t("htg.pred")}: <span className="font-mono font-bold text-white">{r.predicted}</span></span>
                  {r.over25 && <span className="rounded bg-volt/10 text-volt px-2 py-0.5 font-bold">Über 2.5</span>}
                  {r.btts && <span className="rounded bg-sky-400/10 text-sky-300 px-2 py-0.5 font-bold">BTTS</span>}
                </div>

                <div className={`flex items-center gap-2 text-sm font-bold ${cs.txt} bg-void/40 rounded-lg px-3 py-2`}>
                  <Zap size={15} className="shrink-0" />
                  <span>{r.market}</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default HtGoals;
