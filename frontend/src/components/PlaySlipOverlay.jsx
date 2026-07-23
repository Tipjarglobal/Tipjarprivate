import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Check, ExternalLink, Copy, Ticket, Clock } from "lucide-react";
import { toast } from "sonner";
import { useI18n, formatKickoff } from "../i18n";
import { buildSlipText, copySlip, openBookmaker } from "../playSlip";

export const PlaySlipOverlay = ({ data, onClose }) => {
  const { t } = useI18n();
  const [checked, setChecked] = useState({});
  const legs = (data && data.legs) || [];
  const meta = (data && data.meta) || {};

  useEffect(() => {
    if (data) {
      setChecked({});
      copySlip(buildSlipText(legs, meta, t)).then((ok) => {
        if (ok) toast.success(t("play.copied"));
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

  if (!data) return null;
  const doneCount = legs.filter((_, i) => checked[i]).length;
  const allDone = legs.length > 0 && doneCount === legs.length;

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm sm:p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        data-testid="playslip-overlay"
      >
        <motion.div
          className="w-full sm:max-w-lg bg-void border border-elevated rounded-t-3xl sm:rounded-3xl max-h-[92vh] flex flex-col overflow-hidden"
          initial={{ y: 50, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: 50, opacity: 0 }}
          transition={{ type: "spring", damping: 28, stiffness: 300 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between px-5 py-4 border-b border-elevated">
            <div className="flex items-center gap-2.5 min-w-0">
              <Ticket className="text-volt shrink-0" size={22} />
              <div className="min-w-0">
                <p className="text-white font-bold leading-tight truncate">{t("play.overlayTitle")}</p>
                {meta.totalOdds && (
                  <p className="text-xs text-volt font-bold">{t("play.totalOdds")} {meta.totalOdds}</p>
                )}
              </div>
            </div>
            <button onClick={onClose} data-testid="playslip-close" className="text-zinc-400 hover:text-white transition-colors">
              <X size={22} />
            </button>
          </div>

          <div className="px-5 pt-3">
            <p className="text-xs text-zinc-400 mb-2">{t("play.overlayHint")}</p>
            <div className="flex items-center gap-2 mb-1">
              <div className="flex-1 h-2 rounded-full bg-elevated overflow-hidden">
                <div className="h-full bg-volt transition-all duration-300" style={{ width: `${legs.length ? (doneCount / legs.length) * 100 : 0}%` }} />
              </div>
              <span className="text-xs font-bold text-white tabular-nums">{doneCount}/{legs.length}</span>
            </div>
          </div>

          <div className="px-5 py-3 overflow-y-auto space-y-2 flex-1">
            {legs.map((leg, i) => {
              const on = !!checked[i];
              const ko = formatKickoff(leg.kickoff, t);
              return (
                <button
                  key={i}
                  data-testid={`playslip-leg-${i}`}
                  onClick={() => setChecked((c) => ({ ...c, [i]: !c[i] }))}
                  className={`w-full text-left flex items-start gap-3 rounded-xl border p-3 transition-all ${on ? "border-volt/60 bg-volt/10" : "border-elevated bg-surface hover:border-zinc-600"}`}
                >
                  <span className={`shrink-0 mt-0.5 w-6 h-6 rounded-full flex items-center justify-center border-2 transition-colors ${on ? "bg-volt border-volt" : "border-zinc-500"}`}>
                    {on && <Check size={15} className="text-void" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className={`block font-bold text-sm ${on ? "text-zinc-400" : "text-white"}`}>{leg.match || "—"}</span>
                    <span className={`block text-sm font-semibold ${on ? "text-volt/70" : "text-volt"}`}>
                      {leg.market}{leg.odds ? ` · @${leg.odds}` : ""}
                    </span>
                    {ko && (
                      <span className="inline-flex items-center gap-1 mt-1 text-[11px] font-bold text-zinc-400">
                        <Clock size={11} />{ko}
                      </span>
                    )}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="px-5 py-4 border-t border-elevated space-y-2.5">
            {allDone && (
              <p className="text-center text-sm font-bold text-volt" data-testid="playslip-done">{t("play.allDone")}</p>
            )}
            <div className="flex gap-2">
              <button
                onClick={() => copySlip(buildSlipText(legs, meta, t)).then((ok) => ok && toast.success(t("play.copied")))}
                data-testid="playslip-copy"
                title={t("play.copyBtn")}
                className="flex items-center justify-center gap-1.5 rounded-xl border border-elevated px-4 py-3 text-sm font-semibold text-zinc-200 hover:text-white hover:border-zinc-500 transition-colors"
              >
                <Copy size={16} />
              </button>
              <button
                onClick={openBookmaker}
                data-testid="playslip-open"
                className="flex-1 flex items-center justify-center gap-2 rounded-xl bg-volt text-void font-bold text-sm py-3 hover:brightness-110 active:scale-[0.99] transition-all"
              >
                <ExternalLink size={16} /> {t("play.open")}
              </button>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};

export default PlaySlipOverlay;
