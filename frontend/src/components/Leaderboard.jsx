import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Crown } from "lucide-react";
import api from "../api";
import { useI18n } from "../i18n";

export default function Leaderboard({ refreshKey }) {
  const { t } = useI18n();
  const [rows, setRows] = useState([]);

  useEffect(() => {
    api.get("/leaderboard").then((r) => setRows(r.data)).catch(() => {});
  }, [refreshKey]);

  return (
    <section id="leaderboard" className="max-w-4xl mx-auto px-4 sm:px-6 py-16 scroll-mt-20">
      <div className="text-center mb-8">
        <span className="text-xs font-bold uppercase tracking-[0.25em] text-volt flex items-center justify-center gap-2"><Crown size={14} /> {t("lb.title")}</span>
        <h2 className="font-heading text-3xl md:text-4xl font-black text-white tracking-tighter mt-2">{t("lb.title")}</h2>
      </div>

      {rows.length === 0 ? (
        <p className="text-center text-zinc-500 py-10" data-testid="leaderboard-empty">{t("lb.empty")}</p>
      ) : (
        <div className="rounded-2xl bg-surface border border-elevated overflow-hidden" data-testid="leaderboard">
          <div className="grid grid-cols-12 px-5 py-3 text-[10px] uppercase tracking-widest text-zinc-500 border-b border-elevated font-bold">
            <span className="col-span-1">{t("lb.rank")}</span>
            <span className="col-span-6">{t("lb.tipster")}</span>
            <span className="col-span-2 text-right">{t("lb.tips")}</span>
            <span className="col-span-1 text-right">{t("lb.won")}</span>
            <span className="col-span-2 text-right">{t("lb.winrate")}</span>
          </div>
          {rows.map((r, i) => (
            <motion.div
              key={r.user_id}
              initial={{ opacity: 0, x: -10 }} whileInView={{ opacity: 1, x: 0 }} viewport={{ once: true }}
              transition={{ delay: i * 0.04 }}
              className="grid grid-cols-12 items-center px-5 py-3 border-b border-elevated/60 last:border-0 hover:bg-void/50 transition-colors"
              data-testid={`lb-row-${i}`}
            >
              <span className={`col-span-1 font-mono font-black ${i === 0 ? "text-volt" : i < 3 ? "text-white" : "text-zinc-500"}`}>{i + 1}</span>
              <span className="col-span-6 flex items-center gap-2 min-w-0">
                <span className="w-7 h-7 rounded-full bg-elevated flex items-center justify-center text-xs font-bold text-white shrink-0">{r.username?.[0]?.toUpperCase()}</span>
                <span className="text-white font-semibold truncate">{r.username}</span>
              </span>
              <span className="col-span-2 text-right font-mono text-zinc-300">{r.total_tips}</span>
              <span className="col-span-1 text-right font-mono text-won">{r.won}</span>
              <span className="col-span-2 text-right font-mono font-bold text-volt">{r.win_rate}%</span>
            </motion.div>
          ))}
        </div>
      )}
    </section>
  );
}
