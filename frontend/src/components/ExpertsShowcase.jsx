import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Star, Flame, TrendingUp, Crown } from "lucide-react";
import api from "../api";
import { useI18n, toLatin, flamesActive } from "../i18n";

export default function ExpertsShowcase({ onExpertClick, onMasterClick }) {
  const { t } = useI18n();
  const [experts, setExperts] = useState([]);

  useEffect(() => {
    let alive = true;
    api.get("/experts").then((r) => { if (alive) setExperts(r.data.experts || []); }).catch(() => {});
    return () => { alive = false; };
  }, []);

  if (experts.length === 0 && !onMasterClick) return null;

  return (
    <section
      data-testid="experts-showcase"
      className="relative max-w-7xl mx-auto px-4 sm:px-6 -mt-6 pb-8"
    >
      <div className="rounded-3xl bg-gradient-to-br from-orange-500/15 via-surface to-surface border border-orange-500/25 p-5 sm:p-7 shadow-[0_0_40px_rgba(249,122,0,0.08)]">
        <div className="flex items-center gap-2 mb-1">
          <span className="flex items-center gap-1.5 text-orange-400 font-heading font-black text-lg sm:text-xl">
            <Star size={20} className="fill-orange-400" /> {t("experts.showcase.title")}
          </span>
        </div>
        <p className="text-sm text-zinc-400 mb-5 max-w-2xl">{t("experts.showcase.sub")}</p>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          {onMasterClick && (
            <motion.button
              type="button"
              data-testid="showcase-master"
              onClick={onMasterClick}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={{ y: -3 }}
              className="group text-left rounded-2xl bg-gradient-to-br from-[#E11D2A]/25 to-void/50 border border-[#E11D2A]/50 hover:border-[#E11D2A] p-4 transition-colors col-span-2 sm:col-span-3 lg:col-span-4 shadow-[0_0_28px_rgba(225,29,42,0.12)]"
            >
              <div className="flex items-center gap-3">
                <span className="w-11 h-11 rounded-full bg-gradient-to-br from-[#E11D2A] to-[#8f0f18] text-white flex items-center justify-center shrink-0 shadow-[0_0_14px_rgba(225,29,42,0.5)]">
                  <Crown size={20} />
                </span>
                <div className="min-w-0">
                  <div className="font-heading font-black text-white text-lg sm:text-2xl leading-tight break-words group-hover:text-red-300 transition-colors">
                    TipJarMaster
                  </div>
                  <div className="text-xs sm:text-sm text-red-200/90 leading-snug">{t("master.showcase.sub")}</div>
                </div>
                <span className="ml-auto shrink-0 inline-flex items-center gap-1 text-[10px] sm:text-xs font-black uppercase tracking-widest text-white bg-[#E11D2A] rounded-full px-3 py-1">
                  <Crown size={12} /> Master
                </span>
              </div>
            </motion.button>
          )}
          {experts.map((e, i) => (
            <motion.button
              key={e.username}
              type="button"
              data-testid={`showcase-expert-${e.username}`}
              onClick={() => onExpertClick?.(e.username)}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.05, 0.5) }}
              whileHover={{ y: -3 }}
              className="group text-left rounded-2xl bg-void/50 border border-orange-500/20 hover:border-orange-500/50 p-4 transition-colors"
            >
              <div className="flex items-center gap-3">
                <span className="relative w-11 h-11 rounded-full bg-gradient-to-br from-orange-400 to-orange-600 text-void flex items-center justify-center text-lg font-black shrink-0">
                  {e.username?.[0]?.toUpperCase() || "?"}
                  {flamesActive() && e.apex_flame && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-void flex items-center justify-center">
                      <Flame size={12} className="text-orange-400 fill-orange-500" />
                    </span>
                  )}
                </span>
                <div className="min-w-0">
                  <div className="font-heading font-black text-white text-lg sm:text-xl leading-tight break-words group-hover:text-orange-300 transition-colors">
                    {toLatin(e.username)}
                  </div>
                  <div className="flex items-center gap-1 text-[11px] text-zinc-400">
                    <TrendingUp size={11} className="text-orange-400" />
                    {e.tips_count} {t("experts.showcase.tips")}
                  </div>
                </div>
              </div>
              <span className="mt-3 inline-block text-[10px] font-black uppercase tracking-widest text-orange-300 bg-orange-500/15 rounded px-2 py-0.5">
                {t("experts.showcase.badge")}
              </span>
            </motion.button>
          ))}
        </div>
      </div>
    </section>
  );
}
