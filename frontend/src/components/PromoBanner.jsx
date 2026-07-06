import React from "react";
import { BellRing, ArrowRight } from "lucide-react";
import { useI18n } from "../i18n";

export default function PromoBanner() {
  const { t } = useI18n();
  const openAlerts = () => {
    document.getElementById("top")?.scrollIntoView({ behavior: "smooth" });
    window.dispatchEvent(new Event("tj-open-alerts"));
  };
  return (
    <div
      className="relative overflow-hidden border-b border-bell/30 bg-gradient-to-r from-bell/20 via-void to-volt/10"
      data-testid="promo-banner"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-center gap-3 text-center flex-wrap">
        <BellRing size={16} className="text-bell shrink-0 animate-pulse-glow" />
        <span className="text-xs sm:text-sm text-white/90 font-medium">{t("promo.text")}</span>
        <button
          onClick={openAlerts}
          data-testid="promo-cta"
          className="inline-flex items-center gap-1 rounded-full bg-volt text-void font-bold text-xs px-3 py-1 hover:bg-volt-hover active:scale-95 transition-all shrink-0"
        >
          {t("promo.cta")} <ArrowRight size={13} />
        </button>
      </div>
    </div>
  );
}
