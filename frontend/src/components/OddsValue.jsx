import React from "react";
import { Zap } from "lucide-react";
import { useI18n } from "../i18n";

export const oddsNum = (o) => {
  const n = parseFloat(String(o == null ? "" : o).replace(",", "."));
  return isNaN(n) ? null : n;
};

// Renders the odds value, or a "low pregame odds" note when odds < 1.04.
export const OddsValue = ({ odds, className = "" }) => {
  const { lang } = useI18n();
  const n = oddsNum(odds);
  if (n !== null && n < 1.04) {
    const note =
      lang === "de"
        ? "Niedrige Quote pregame – live evtl. höher"
        : "Low pregame odds – may be higher live";
    return (
      <span className="inline-flex items-center gap-1 text-[10px] leading-tight text-bell/90 font-medium max-w-[60%] text-right">
        <Zap size={11} className="shrink-0" /> {note}
      </span>
    );
  }
  return <span className={className}>{odds}</span>;
};
