import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Trophy, Coins, Radio, Users, Award } from "lucide-react";
import api, { fileUrl } from "../api";
import { useI18n } from "../i18n";

const TYPE_META = {
  played: { icon: Users, label: "win.type.played", color: "text-sky-400" },
  posted: { icon: Trophy, label: "win.type.posted", color: "text-volt" },
  live: { icon: Radio, label: "win.type.live", color: "text-live" },
};

export default function HallOfFame({ refreshKey, onEarn }) {
  const { t } = useI18n();
  const [items, setItems] = useState([]);

  useEffect(() => {
    let mounted = true;
    api.get("/wins/hall-of-fame")
      .then(({ data }) => { if (mounted) setItems(data || []); })
      .catch(() => {});
    return () => { mounted = false; };
  }, [refreshKey]);

  return (
    <section id="hall-of-fame" className="relative max-w-7xl mx-auto px-4 sm:px-6 py-16 scroll-mt-20" data-testid="hall-of-fame">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 text-volt font-bold text-xs uppercase tracking-[0.15em]">
            <Award size={14} /> {t("win.hof.badge")}
          </div>
          <h2 className="font-heading text-3xl md:text-4xl font-black text-white tracking-tighter mt-2">{t("win.hof.title")}</h2>
          <p className="text-zinc-400 mt-2 max-w-xl">{t("win.hof.subtitle")}</p>
        </div>
        <button
          onClick={onEarn} data-testid="hof-earn-btn"
          className="self-start flex items-center gap-2 rounded-full bg-volt text-void font-bold px-5 py-3 hover:bg-volt-hover active:scale-95 transition-all shadow-[0_0_30px_rgba(225,255,0,0.25)]"
        >
          <Coins size={18} /> {t("win.earn")}
        </button>
      </div>

      {items.length === 0 ? (
        <div className="rounded-3xl border border-dashed border-elevated p-12 text-center text-zinc-500" data-testid="hof-empty">
          {t("win.hof.empty")}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((w, i) => {
            const meta = TYPE_META[w.type] || TYPE_META.played;
            const Icon = meta.icon;
            return (
              <motion.div
                key={w.id}
                initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }} transition={{ delay: i * 0.04 }}
                className="relative rounded-2xl bg-surface border border-elevated overflow-hidden hover:border-volt/40 transition-colors"
                data-testid={`hof-card-${i}`}
              >
                {i < 3 && (
                  <span className="absolute top-2 right-2 z-10 text-xs font-black text-void bg-volt rounded-full px-2.5 py-0.5 shadow-lg">#{i + 1}</span>
                )}
                {w.image_path ? (
                  <img src={fileUrl(w.image_path)} alt="win" data-testid={`hof-img-${i}`}
                    className="w-full object-contain bg-black/40" />
                ) : (
                  <div className="p-4">
                    <div className="flex items-center justify-between">
                      <span className={`inline-flex items-center gap-1.5 text-xs font-bold ${meta.color}`}>
                        <Icon size={13} /> {t(meta.label)}
                      </span>
                    </div>
                    <div className="mt-3 flex items-baseline justify-between">
                      <span className="text-zinc-400 text-xs">{t("win.hof.odds")}</span>
                      <span className="font-mono font-black text-2xl text-volt">{w.total_odds?.toFixed(2)}</span>
                    </div>
                    <div className="mt-1 flex items-center justify-between text-sm">
                      <span className="text-white font-semibold truncate">@{w.username}</span>
                      <span className="text-zinc-400">{w.legs_count} Legs</span>
                    </div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}
    </section>
  );
}
