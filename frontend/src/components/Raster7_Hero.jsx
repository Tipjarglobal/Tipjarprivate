import React from "react";
import { motion } from "framer-motion";
import { Sparkles, CheckCircle2 } from "lucide-react";
import { useI18n } from "../i18n";
import AnimatedJar from "./AnimatedJar";

const HERO_BG = "https://images.pexels.com/photos/35898730/pexels-photo-35898730.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=1080&w=1920";

// RASTER 7 — Footer-Intro / Wasserzeichen (Hero mit Jar + Tipjarglobal.com)
export default function Raster7_Hero() {
  const { t } = useI18n();
  return (
    <section className="relative overflow-hidden" data-testid="raster7-hero">
      <div className="absolute inset-0">
        <img src={HERO_BG} alt="" className="w-full h-full object-cover opacity-20" />
        <div className="absolute inset-0 bg-gradient-to-b from-void/70 via-void/85 to-void" />
      </div>
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-20 grid lg:grid-cols-2 gap-10 items-center">
        <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="min-w-0">
          <span className="inline-flex items-center gap-2 rounded-full border border-volt/30 bg-volt/5 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-volt">
            <Sparkles size={13} /> {t("hero.badge")}
          </span>
          <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter leading-[1.08] text-white mt-5 pb-1 break-words">
            {t("hero.title")}
          </h1>
          <p className="text-lg text-zinc-400 mt-5 max-w-xl leading-relaxed">{t("hero.subtitle")}</p>
          <div data-testid="playable-only-badge" className="mt-5 flex items-start gap-2.5 rounded-xl border border-volt/40 bg-volt/10 px-4 py-3 max-w-xl">
            <CheckCircle2 size={18} className="text-volt shrink-0 mt-0.5" />
            <span className="text-sm font-semibold text-white leading-snug">{t("hero.playable")}</span>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.15 }} className="flex flex-col items-center gap-3">
          <AnimatedJar />
          <a
            href="https://tipjarglobal.com"
            data-testid="hero-logo-url"
            className="font-heading font-black text-lg sm:text-xl tracking-tight text-volt hover:text-volt-hover transition-colors drop-shadow-[0_0_12px_rgba(225,255,0,0.45)]"
          >
            Tipjarglobal.com
          </a>
        </motion.div>
      </div>
    </section>
  );
}
