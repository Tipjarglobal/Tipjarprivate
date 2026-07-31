import React, { useState } from "react";
import { Target, Droplets, Timer, ScanLine, ChevronDown } from "lucide-react";
import { ScorerRadar } from "./ScorerRadar";
import { GoalThirst } from "./GoalThirst";
import { HtGoals } from "./HtGoals";
import { CodeReading } from "./CodeReading";
import { useI18n } from "../i18n";

const CR_LABEL = { de: "Code Reading", el: "Ανάγνωση Κωδικών", en: "Code Reading" };
const CR_SUB = {
  de: "Wettanbieter-Scheine lesen und dagegen spielen",
  el: "Διάβασε τα κουπόνια των πρακτόρων και παίξε αντίθετα",
  en: "Read bookmaker slips and play against them",
};

export default function StatisticsView() {
  const { t, lang } = useI18n();
  const [tab, setTab] = useState("scorer");
  const [showCR, setShowCR] = useState(false);
  const TABS = [
    ["scorer", "stats.tab.scorer", Target],
    ["thirst", "stats.tab.thirst", Droplets],
    ["htgoal", "stats.tab.htgoal", Timer],
  ];
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-6 pb-16" data-testid="statistics-view">
      <div className="flex items-center gap-2 mb-2 bg-void/50 rounded-full p-1 w-fit flex-wrap">
        {TABS.map(([key, lbl, Icon]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            data-testid={`stats-tab-${key}`}
            className={`flex items-center gap-1.5 text-xs sm:text-sm font-bold px-3.5 py-1.5 rounded-full transition-colors ${
              tab === key ? "bg-volt text-void" : "text-zinc-400 hover:text-white"
            }`}
          >
            <Icon size={14} /> {t(lbl)}
          </button>
        ))}
      </div>
      {tab === "scorer" ? <ScorerRadar /> : tab === "thirst" ? <GoalThirst /> : <HtGoals />}

      {/* Separate grey channel UNDER the statistics (owner: not a stats tab) */}
      <div className="mt-10 pt-8 border-t border-zinc-800">
        <button
          data-testid="code-reading-toggle-btn"
          onClick={() => setShowCR((v) => !v)}
          className={`w-full flex items-center justify-between gap-3 px-5 py-4 rounded-2xl border transition-colors ${
            showCR ? "bg-zinc-800 border-zinc-600" : "bg-zinc-900/70 border-zinc-700 hover:bg-zinc-800/70"
          }`}
        >
          <span className="flex items-center gap-3 text-left">
            <span className="w-10 h-10 rounded-xl bg-zinc-700 flex items-center justify-center shrink-0">
              <ScanLine size={20} className="text-zinc-200" />
            </span>
            <span>
              <span className="block font-heading font-black text-zinc-100 text-base">{CR_LABEL[lang] || CR_LABEL.en}</span>
              <span className="block text-xs text-zinc-400">{CR_SUB[lang] || CR_SUB.en}</span>
            </span>
          </span>
          <ChevronDown size={20} className={`text-zinc-400 transition-transform ${showCR ? "rotate-180" : ""}`} />
        </button>
        {showCR && <div className="mt-5"><CodeReading /></div>}
      </div>
    </div>
  );
}
