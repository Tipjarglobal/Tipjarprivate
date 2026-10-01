import React from "react";
import { useI18n } from "../i18n";

// RASTER 9 — Was ist TipJar? / System-Modus (konsolidierte Textblöcke + Vorteil-Box + CTA)
export default function Raster9_Story() {
  const { t } = useI18n();
  return (
    <section id="how" className="relative max-w-4xl mx-auto px-4 sm:px-6 py-16 scroll-mt-20" data-testid="raster9-story">
      <div className="rounded-3xl bg-surface border border-elevated p-8 md:p-12">
        <h2 className="font-heading text-3xl md:text-4xl font-black text-white tracking-tighter">{t("hero.story.title")}</h2>
        <p className="text-zinc-400 mt-5 text-lg leading-relaxed">{t("hero.story")}</p>

        <div className="mt-8 pt-8 border-t border-elevated">
          <span className="inline-flex items-center gap-2 text-volt font-bold text-xs uppercase tracking-[0.2em]" data-testid="story-why-label">{t("story.why.label")}</span>
          <h3 className="font-heading text-2xl md:text-3xl font-black text-white tracking-tight mt-3" data-testid="story-why-title">{t("story.why.title")}</h3>
          <p className="text-zinc-400 mt-4 text-base md:text-lg leading-relaxed" data-testid="story-why-body">{t("story.why.body")}</p>
          <div className="mt-5 rounded-xl bg-volt/5 border-l-2 border-volt pl-4 py-3">
            <p className="text-base md:text-lg leading-relaxed text-zinc-200" data-testid="story-advantage">{t("story.why.advantage")}</p>
          </div>
          <p className="mt-6 text-sm text-zinc-500 leading-relaxed border border-dashed border-elevated rounded-xl px-4 py-3" data-testid="story-not">{t("story.not")}</p>
          <p className="mt-8 text-lg md:text-xl font-heading font-bold text-white leading-snug" data-testid="story-cta">{t("story.cta")}</p>
        </div>
      </div>
    </section>
  );
}
