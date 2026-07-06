import React, { useState } from "react";
import { BellRing, ArrowRight, X } from "lucide-react";
import { useI18n } from "../i18n";

export default function PromoBanner() {
  const { t } = useI18n();
  const [dismissed, setDismissed] = useState(localStorage.getItem("tj_promo_dismissed") === "1");
  const openAlerts = () => {
    document.getElementById("top")?.scrollIntoView({ behavior: "smooth" });
    window.dispatchEvent(new Event("tj-open-alerts"));
  };
  const dismiss = () => {
    localStorage.setItem("tj_promo_dismissed", "1");
    setDismissed(true);
  };
  if (dismissed) return null;
  return (
    <div
      className="relative overflow-hidden border-b border-bell/30 bg-gradient-to-r from-bell/20 via-void to-volt/10"
      data-testid="promo-banner"
    >
      <div className="max-w-7xl mx-auto pl-4 pr-10 sm:px-6 py-2.5 flex items-center justify-center gap-3 text-center flex-wrap">
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
      <button
        onClick={dismiss}
        data-testid="promo-dismiss"
        aria-label={t("promo.dismiss")}
        title={t("promo.dismiss")}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-full text-white/60 hover:text-white hover:bg-white/10 active:scale-90 transition-all"
      >
        <X size={16} />
      </button>
    </div>
  );
}
