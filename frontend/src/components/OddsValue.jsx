import React from "react";
import { Zap } from "lucide-react";
import { useI18n } from "../i18n";

export const oddsNum = (o) => {
  const n = parseFloat(String(o == null ? "" : o).replace(",", "."));
  return isNaN(n) ? null : n;
};

// Always shows the real odds value. For very low pregame odds (< 1.04) it adds a
// tiny hint underneath — without ever hiding the actual number.
export const OddsValue = ({ odds, className = "" }) => {
  const { lang } = useI18n();
  const n = oddsNum(odds);
  const low = n !== null && n < 1.04;
  return (
    <span className={`inline-flex flex-col items-end ${className}`}>
      <span>{odds}</span>
      {low && (
        <span className="inline-flex items-center gap-1 text-[9px] leading-tight text-bell/90 font-medium mt-0.5 text-right whitespace-nowrap">
          <Zap size={10} className="shrink-0" />
          {lang === "de" ? "pregame – live evtl. höher" : "pregame – higher live"}
        </span>
      )}
    </span>
  );
};
