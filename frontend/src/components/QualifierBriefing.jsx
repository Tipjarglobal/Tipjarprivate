import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Trophy, ChevronDown, RefreshCw, Sparkles } from "lucide-react";
import api from "../api";

const renderInline = (text, keyBase) => {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) => {
    if (p.startsWith("**") && p.endsWith("**")) {
      return (
        <strong key={`${keyBase}-${i}`} className="text-white font-heading font-black">
          {p.slice(2, -2)}
        </strong>
      );
    }
    return <span key={`${keyBase}-${i}`}>{p}</span>;
  });
};

export const QualifierBriefing = ({ t }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [open, setOpen] = useState(true);

  useEffect(() => {
    let alive = true;
    const load = async (silent) => {
      try {
        const { data } = await api.get("/smart/qualifier-briefing");
        if (alive) setData(data);
        if (data?.building) setTimeout(() => alive && load(true), 15000);
      } catch {
        /* ignore */
      } finally {
        if (alive && !silent) setLoading(false);
      }
    };
    load();
    return () => { alive = false; };
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border border-volt/20 bg-surface p-5 mb-4 flex items-center gap-3 text-zinc-400 text-sm" data-testid="qual-briefing-loading">
        <RefreshCw size={16} className="animate-spin text-volt" /> {t("brief.building")}
      </div>
    );
  }
  if (!data || (!data.narrative && !data.building)) return null;

  const lines = (data.narrative || "").split("\n").map((l) => l.trim()).filter(Boolean);
  const updated = data.generated_at ? new Date(data.generated_at).toLocaleDateString() : "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      data-testid="qual-briefing"
      className="rounded-2xl border border-volt/30 bg-gradient-to-br from-volt/[0.07] via-surface to-surface p-5 sm:p-6 mb-5"
    >
      <button
        data-testid="qual-briefing-toggle"
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between gap-3 text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-10 h-10 rounded-xl bg-volt/15 flex items-center justify-center shrink-0">
            <Trophy className="text-volt" size={20} />
          </div>
          <div className="min-w-0">
            <h3 className="font-heading font-black text-white text-lg leading-tight flex items-center gap-2">
              {t("brief.title")}
              <Sparkles size={14} className="text-volt shrink-0" />
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              {data.count} {t("brief.sub")}{updated ? ` · ${updated}` : ""}
              {data.building ? ` · ${t("brief.building")}` : ""}
            </p>
          </div>
        </div>
        <ChevronDown
          size={20}
          className={`text-zinc-400 shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden"
          >
            <div className="mt-4 space-y-2.5 text-sm text-zinc-300 leading-relaxed" data-testid="qual-briefing-body">
              {lines.length === 0 ? (
                <p className="text-zinc-500">{t("brief.empty")}</p>
              ) : (
                lines.map((line, i) => {
                  const isHeader = /^\*\*[^*]+\*\*$/.test(line);
                  return (
                    <p
                      key={i}
                      className={isHeader ? "text-base pt-2 border-t border-elevated/60 first:border-0 first:pt-0" : ""}
                    >
                      {renderInline(line, i)}
                    </p>
                  );
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default QualifierBriefing;
