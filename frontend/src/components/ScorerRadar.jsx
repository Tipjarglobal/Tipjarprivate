import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Target, Flame, RefreshCw, Clock } from "lucide-react";
import api from "../api";
import { useI18n, toLatin } from "../i18n";

const confStyle = (c) => {
  if (c >= 90) return { ring: "border-[#2ECC57]/50", chip: "bg-[#2ECC57] text-black", txt: "text-[#2ECC57]" };
  if (c >= 80) return { ring: "border-volt/50", chip: "bg-volt text-black", txt: "text-volt" };
  return { ring: "border-amber-400/50", chip: "bg-amber-400 text-black", txt: "text-amber-300" };
};

const fmtTime = (iso) => {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

export const ScorerRadar = () => {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (silent) => {
    if (!silent) setLoading(true);
    try {
      const { data } = await api.get("/scorers/today");
      setRows(data.scorers || []);
    } catch {
      /* ignore */
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const iv = setInterval(() => load(true), 60000);
    return () => clearInterval(iv);
  }, [load]);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8" data-testid="scorer-radar">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <h2 className="font-heading font-black text-3xl sm:text-4xl text-white flex items-center gap-3">
            <Target className="text-[#2ECC57]" size={30} />
            {t("scorers.title")}
          </h2>
          <p className="text-sm text-zinc-400 mt-2 max-w-2xl">{t("scorers.sub")}</p>
        </div>
        <button
          data-testid="scorer-radar-refresh"
          onClick={() => load()}
          className="shrink-0 rounded-full p-2.5 bg-surface border border-elevated text-zinc-300 hover:text-white active:scale-90 transition-all"
          aria-label="refresh"
        >
          <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
        </button>
      </div>

      {loading && rows.length === 0 ? (
        <div className="text-center text-zinc-500 py-20" data-testid="scorer-radar-loading">
          <RefreshCw size={26} className="animate-spin mx-auto mb-3" />
          {t("scorers.loading")}
        </div>
      ) : rows.length === 0 ? (
        <div className="text-center text-zinc-500 py-20" data-testid="scorer-radar-empty">
          {t("scorers.empty")}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-3">
          {rows.map((s, i) => {
            const st = confStyle(s.confidence);
            return (
              <motion.div
                key={`${s.team}-${s.opponent}-${i}`}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.5) }}
                data-testid="scorer-card"
                className={`rounded-2xl bg-surface border ${st.ring} p-4 flex items-center gap-4`}
              >
                <div className={`shrink-0 w-12 h-12 rounded-xl ${st.chip} flex flex-col items-center justify-center font-heading font-black leading-none`}>
                  <span className="text-base">{s.confidence}</span>
                  <span className="text-[8px] font-bold uppercase tracking-wide">%</span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-heading font-black text-white text-lg truncate">{toLatin(s.team)}</span>
                    {s.confidence >= 90 && <Flame size={15} className="text-[#2ECC57] shrink-0" />}
                  </div>
                  <div className="text-xs text-zinc-400 truncate">
                    {t("scorers.vs")} {toLatin(s.opponent)}
                    {s.league ? ` · ${s.league}` : ""}
                  </div>
                  <div className={`text-[11px] mt-1 ${st.txt} font-semibold`}>
                    {t("scorers.willScore")} · {s.reason}
                  </div>
                </div>
                {s.kickoff && (
                  <div className="shrink-0 flex items-center gap-1 text-[11px] text-zinc-500 font-mono">
                    <Clock size={12} />
                    {fmtTime(s.kickoff)}
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ScorerRadar;
