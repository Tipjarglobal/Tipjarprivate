import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Droplets, RefreshCw, Clock, Target, ShieldAlert } from "lucide-react";
import api from "../api";
import { useI18n, toLatin, isKickoffTimeUnknown } from "../i18n";

const confStyle = (c) => {
  if (c >= 85) return { chip: "bg-[#2ECC57] text-black", txt: "text-[#2ECC57]" };
  if (c >= 75) return { chip: "bg-volt text-black", txt: "text-volt" };
  return { chip: "bg-amber-400 text-black", txt: "text-amber-300" };
};

const fmtWhen = (iso) => {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    const day = d.toLocaleDateString([], { weekday: "short", day: "2-digit", month: "2-digit" });
    // Unknown kickoff time (23:59 sentinel) → show the DATE only, never a bogus ~01:59 night time.
    if (isKickoffTimeUnknown(iso)) return day;
    return day + " · " + d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
};

export const GoalThirst = () => {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/goal-thirst");
      setRows(r.data.teams || []);
    } catch {
      setRows([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const oppText = (lvl) => (lvl === "high" ? t("thirst.oppHigh") : lvl === "mid" ? t("thirst.oppMid") : t("thirst.oppLow"));
  const oppCls = (lvl) => (lvl === "high" ? "text-[#2ECC57]" : lvl === "mid" ? "text-amber-300" : "text-zinc-400");

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6" data-testid="goal-thirst">
      <div className="flex items-start justify-between gap-4 mb-2">
        <div>
          <h2 className="font-heading font-black text-2xl sm:text-3xl flex items-center gap-2">
            <Droplets className="text-sky-400" size={26} /> {t("thirst.title")}
          </h2>
          <p className="text-sm text-zinc-400 mt-1 max-w-2xl">{t("thirst.intro")}</p>
        </div>
        <button onClick={load} data-testid="thirst-refresh" className="shrink-0 flex items-center gap-1.5 text-xs font-bold px-3 py-2 rounded-full bg-elevated text-zinc-300 hover:text-white transition-colors">
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} /> {t("thirst.refresh")}
        </button>
      </div>

      {loading ? (
        <div className="text-center text-zinc-500 py-20" data-testid="thirst-loading">{t("thirst.loading")}</div>
      ) : rows.length === 0 ? (
        <div className="text-center text-zinc-500 py-16 rounded-2xl border border-dashed border-elevated" data-testid="thirst-empty">
          {t("thirst.empty")}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4 mt-4">
          {rows.map((r, i) => {
            const cs = confStyle(r.confidence);
            return (
              <motion.div
                key={`${r.team}-${i}`}
                data-testid="thirst-card"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(i * 0.03, 0.4) }}
                className="rounded-2xl bg-surface border border-elevated p-4 hover:border-sky-400/40 transition-colors"
              >
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="font-heading font-black text-lg text-white truncate">{toLatin(r.team)}</span>
                  <span className={`text-xs font-black px-2 py-1 rounded-full ${cs.chip}`}>{r.confidence}%</span>
                </div>

                <div className="flex items-center gap-2 text-[13px] text-sky-300 mb-2">
                  <Droplets size={14} className="shrink-0" />
                  <span>{t("thirst.drought")}</span>
                </div>

                <div className="flex items-center gap-2 text-[13px] text-zinc-300 mb-2">
                  <Clock size={14} className="shrink-0 text-zinc-500" />
                  <span>{t("thirst.next")} <span className="font-semibold text-white">{toLatin(r.opponent)}</span>{r.league ? ` · ${toLatin(r.league)}` : ""} · {fmtWhen(r.kickoff)}</span>
                </div>

                <div className="flex items-center gap-2 text-[13px] mb-3">
                  <ShieldAlert size={14} className={`shrink-0 ${oppCls(r.opp_level)}`} />
                  <span className={oppCls(r.opp_level)}>{oppText(r.opp_level)}</span>
                </div>

                <div className={`flex items-center gap-2 text-sm font-bold ${cs.txt} bg-void/40 rounded-lg px-3 py-2`}>
                  <Target size={15} className="shrink-0" />
                  <span><span className="text-white">{toLatin(r.team)}</span> {t("thirst.willscore")}</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default GoalThirst;
