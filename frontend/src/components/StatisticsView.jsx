import React, { useState } from "react";
import { Target, Droplets } from "lucide-react";
import { ScorerRadar } from "./ScorerRadar";
import { GoalThirst } from "./GoalThirst";
import { useI18n } from "../i18n";

export default function StatisticsView() {
  const { t } = useI18n();
  const [tab, setTab] = useState("scorer");
  const TABS = [
    ["scorer", "stats.tab.scorer", Target],
    ["thirst", "stats.tab.thirst", Droplets],
  ];
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 pt-6" data-testid="statistics-view">
      <div className="flex items-center gap-2 mb-2 bg-void/50 rounded-full p-1 w-fit">
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
      {tab === "scorer" ? <ScorerRadar /> : <GoalThirst />}
    </div>
  );
}
