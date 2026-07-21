import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Target, Flame, RefreshCw, Clock, Table2 } from "lucide-react";
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

// Row of ⚽ balls (or a muted dash when goalless).
const Balls = ({ n, muted }) => {
  if (!n) return <span className="text-zinc-600 text-sm font-mono">—</span>;
  return (
    <span className={`text-base leading-none tracking-tight ${muted ? "opacity-40 grayscale" : ""}`}>
      {"⚽".repeat(Math.min(n, 6))}
    </span>
  );
};

const TeamGoalRow = ({ name, goals, dim }) => (
  <div className="flex items-center justify-between gap-3 py-1">
    <span className={`font-heading font-bold text-sm truncate ${dim ? "text-zinc-500" : "text-white"}`}>
      {toLatin(name)}
    </span>
    <div className="flex items-center gap-2 shrink-0">
      <Balls n={goals} muted={dim} />
      <span className={`w-5 text-right font-mono text-xs ${goals ? "text-volt" : "text-zinc-600"}`}>{goals}</span>
    </div>
  </div>
);

const RadarView = ({ rows, t }) => {
  if (rows.length === 0) {
    return <div className="text-center text-zinc-500 py-20" data-testid="scorer-radar-empty">{t("scorers.empty")}</div>;
  }
  return (
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
                {t("scorers.vs")} {toLatin(s.opponent)}{s.league ? ` · ${s.league}` : ""}
              </div>
              <div className={`text-[11px] mt-1 ${st.txt} font-semibold`}>
                {t("scorers.willScore")} · {s.reason}
              </div>
            </div>
            {s.kickoff && (
              <div className="shrink-0 flex items-center gap-1 text-[11px] text-zinc-500 font-mono">
                <Clock size={12} />{fmtTime(s.kickoff)}
              </div>
            )}
          </motion.div>
        );
      })}
    </div>
  );
};

const TableView = ({ matches, t }) => {
  if (matches.length === 0) {
    return <div className="text-center text-zinc-500 py-20" data-testid="goals-table-empty">{t("scorers.empty")}</div>;
  }
  return (
    <div className="grid sm:grid-cols-2 gap-3" data-testid="goals-table">
      {matches.map((m, i) => {
        const goalless = m.total === 0;
        return (
          <motion.div
            key={`${m.home}-${m.away}-${i}`}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: Math.min(i * 0.025, 0.4) }}
            data-testid="goals-row"
            className={`rounded-2xl bg-surface border p-4 ${goalless ? "border-zinc-700/60" : m.total >= 4 ? "border-[#2ECC57]/40" : "border-elevated"}`}
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <span className="text-[11px] text-zinc-500 truncate">{m.league || "—"}</span>
              {m.kickoff && (
                <span className="shrink-0 flex items-center gap-1 text-[11px] text-zinc-500 font-mono">
                  <Clock size={11} />{fmtTime(m.kickoff)}
                </span>
              )}
            </div>
            <TeamGoalRow name={m.home} goals={m.home_goals} dim={goalless} />
            <TeamGoalRow name={m.away} goals={m.away_goals} dim={goalless} />
            <div className={`text-[11px] mt-2 font-medium ${goalless ? "text-amber-300/80" : m.total >= 4 ? "text-[#2ECC57]" : "text-zinc-400"}`}>
              {m.note}{m.confidence ? ` · ${m.confidence}%` : ""}
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};

export const ScorerRadar = () => {
  const { t } = useI18n();
  const [tab, setTab] = useState("table");
  const [rows, setRows] = useState([]);
  const [matches, setMatches] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (silent) => {
    if (!silent) setLoading(true);
    try {
      const [r, g] = await Promise.all([
        api.get("/scorers/today"),
        api.get("/goals-forecast"),
      ]);
      setRows(r.data.scorers || []);
      setMatches(g.data.matches || []);
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

  const empty = rows.length === 0 && matches.length === 0;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8" data-testid="scorer-radar">
      <div className="flex items-start justify-between gap-4 mb-5">
        <div>
          <h2 className="font-heading font-black text-3xl sm:text-4xl text-white flex items-center gap-3">
            <Target className="text-[#2ECC57]" size={30} />
            {t("scorers.title")}
          </h2>
          <p className="text-sm text-zinc-400 mt-2 max-w-2xl">
            {tab === "table" ? t("scorers.tableSub") : t("scorers.sub")}
          </p>
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

      <div className="inline-flex items-center gap-1 p-1 rounded-full bg-surface border border-elevated mb-6">
        <button
          data-testid="scorer-tab-table"
          onClick={() => setTab("table")}
          className={`flex items-center gap-1.5 text-xs font-bold px-4 py-2 rounded-full transition-all ${tab === "table" ? "bg-volt text-void" : "text-zinc-400 hover:text-white"}`}
        >
          <Table2 size={14} />{t("scorers.tabTable")}
        </button>
        <button
          data-testid="scorer-tab-radar"
          onClick={() => setTab("radar")}
          className={`flex items-center gap-1.5 text-xs font-bold px-4 py-2 rounded-full transition-all ${tab === "radar" ? "bg-volt text-void" : "text-zinc-400 hover:text-white"}`}
        >
          <Target size={14} />{t("scorers.tabRadar")}
        </button>
      </div>

      {loading && empty ? (
        <div className="text-center text-zinc-500 py-20" data-testid="scorer-radar-loading">
          <RefreshCw size={26} className="animate-spin mx-auto mb-3" />
          {t("scorers.loading")}
        </div>
      ) : tab === "table" ? (
        <TableView matches={matches} t={t} />
      ) : (
        <RadarView rows={rows} t={t} />
      )}
    </div>
  );
};

export default ScorerRadar;
