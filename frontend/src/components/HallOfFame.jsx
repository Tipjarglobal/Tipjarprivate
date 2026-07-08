import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Trophy, Coins, Radio, Users, Award, X, Gift } from "lucide-react";
import api, { fileUrl } from "../api";
import { useI18n } from "../i18n";

const TYPE_META = {
  played: { icon: Users, label: "win.type.played", color: "text-sky-400" },
  posted: { icon: Trophy, label: "win.type.posted", color: "text-volt" },
  live: { icon: Radio, label: "win.type.live", color: "text-live" },
};

export default function HallOfFame({ refreshKey, onEarn, onUserClick }) {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [viewer, setViewer] = useState(null);

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
          <Coins size={18} /> {t("win.showWin")}
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
                  <button type="button" onClick={() => setViewer(w)} data-testid={`hof-open-${i}`}
                    className="block w-full text-left">
                    <img src={fileUrl(w.image_path)} alt="win" data-testid={`hof-img-${i}`}
                      className="w-full object-contain bg-black/40 cursor-pointer hover:opacity-90 transition-opacity" />
                  </button>
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
                      <button type="button" onClick={() => onUserClick?.(w.username)} data-testid={`hof-gift-user-${i}`}
                        className="text-white font-semibold truncate hover:text-volt underline decoration-dotted underline-offset-2 transition-colors">@{w.username}</button>
                      <span className="text-zinc-400">{w.legs_count} Legs</span>
                    </div>
                  </div>
                )}
              </motion.div>
            );
          })}
        </div>
      )}

      {viewer && (
        <div
          className="fixed inset-0 z-[200] bg-black/92 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={() => setViewer(null)}
          data-testid="hof-viewer"
        >
          <button
            onClick={() => setViewer(null)}
            data-testid="hof-viewer-close"
            className="absolute top-4 right-4 rounded-full p-2 text-zinc-300 hover:text-white hover:bg-white/10 active:scale-90 transition-all"
            aria-label={t("common.close")}
          >
            <X size={26} />
          </button>
          <div className="relative max-w-xl w-full" onClick={(e) => e.stopPropagation()}>
            {viewer.image_path && (
              <img
                src={fileUrl(viewer.image_path)}
                alt="win full view"
                data-testid="hof-viewer-img"
                className="w-full h-auto max-h-[86vh] object-contain rounded-2xl shadow-2xl select-none"
                draggable={false}
              />
            )}
            <button
              type="button"
              onClick={() => { setViewer(null); onUserClick?.(viewer.username); }}
              data-testid="hof-viewer-user"
              title={t("wall.giftUser")}
              className="absolute bottom-3 left-3 flex items-center gap-2 rounded-full bg-black/70 backdrop-blur px-3 py-1.5 text-sm font-semibold text-white hover:text-volt transition-colors"
            >
              <span className="w-6 h-6 rounded-full bg-volt text-void flex items-center justify-center text-xs font-black">
                {viewer.username?.[0]?.toUpperCase() || "?"}
              </span>
              @{viewer.username}
              <Gift size={14} className="text-volt" />
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
