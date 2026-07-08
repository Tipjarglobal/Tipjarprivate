import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useI18n } from "../i18n";

const SPLASH_BY_LANG = {
  en: "/splash-en.png",
  de: "/splash-de.png",
  es: "/splash-es.png",
  el: "/splash-el.png",
  fr: "/splash-fr.png",
  it: "/splash-it.png",
  ar: "/splash-ar.png",
  tr: "/splash-tr.png",
};

export default function SplashScreen() {
  const { lang } = useI18n();
  const [show, setShow] = useState(true);
  const src = SPLASH_BY_LANG[lang] || SPLASH_BY_LANG.en;
  useEffect(() => {
    const timer = setTimeout(() => setShow(false), 2500);
    return () => clearTimeout(timer);
  }, []);
  return (
    <AnimatePresence>
      {show && (
        <motion.div
          data-testid="splash-screen"
          className="fixed inset-0 z-[200] bg-void flex items-center justify-center"
          initial={{ y: 0 }}
          exit={{ y: "-100%" }}
          transition={{ duration: 0.6, ease: [0.76, 0, 0.24, 1] }}
        >
          <motion.img
            key={src}
            src={src}
            alt="TipJar"
            className="w-full h-full object-contain sm:max-w-md mx-auto select-none pointer-events-none"
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
            draggable={false}
          />
          <svg
            className="absolute inset-0 w-full h-full pointer-events-none"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <motion.path
              d="M50 1.5 H98.5 V98.5 H1.5 V1.5 Z"
              fill="none"
              stroke="#E1FF00"
              strokeWidth={5}
              strokeLinecap="round"
              vectorEffect="non-scaling-stroke"
              pathLength={1}
              initial={{ strokeDasharray: 1, strokeDashoffset: 1 }}
              animate={{ strokeDashoffset: 0 }}
              transition={{ duration: 2.5, ease: "linear" }}
              style={{ filter: "drop-shadow(0 0 6px #E1FF00)" }}
            />
          </svg>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
