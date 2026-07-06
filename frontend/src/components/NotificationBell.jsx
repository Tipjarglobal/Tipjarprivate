import React, { useEffect, useRef, useState } from "react";
import { Bell, BellRing } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import api from "../api";
import { useI18n } from "../i18n";

function anonId() {
  let id = localStorage.getItem("tj_anon");
  if (!id) {
    id = "anon-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("tj_anon", id);
  }
  return id;
}

export default function NotificationBell() {
  const { t } = useI18n();
  const [on, setOn] = useState(localStorage.getItem("tj_bell") === "1");
  const [count, setCount] = useState(0);
  const [toast, setToast] = useState(false);
  const lastTotal = useRef(null);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const { data } = await api.get("/notifications/stats");
        if (!mounted) return;
        setCount(data.subscriber_count);
        if (on && lastTotal.current !== null && data.total_tips > lastTotal.current) {
          if (window.Notification && Notification.permission === "granted") {
            new Notification("TipJar 🔔", { body: "A fresh tip just dropped in the jar!" });
          }
        }
        lastTotal.current = data.total_tips;
      } catch {
        /* ignore */
      }
    };
    poll();
    const iv = setInterval(poll, 15000);
    return () => {
      mounted = false;
      clearInterval(iv);
    };
  }, [on]);

  const toggle = async () => {
    const id = anonId();
    if (!on) {
      try {
        if (window.Notification && Notification.permission !== "granted") {
          await Notification.requestPermission();
        }
        const { data } = await api.post("/notifications/subscribe", { anon_id: id });
        setCount(data.subscriber_count);
      } catch { /* ignore */ }
      setOn(true);
      localStorage.setItem("tj_bell", "1");
      setToast(true);
      setTimeout(() => setToast(false), 3200);
    } else {
      try {
        const { data } = await api.post("/notifications/unsubscribe", { anon_id: id });
        setCount(data.subscriber_count);
      } catch { /* ignore */ }
      setOn(false);
      localStorage.removeItem("tj_bell");
    }
  };

  return (
    <div className="relative">
      <motion.button
        data-testid="notification-bell"
        onClick={toggle}
        whileTap={{ scale: 0.9 }}
        title={t("bell.tooltip")}
        className={`relative flex items-center gap-2 rounded-full pl-3 pr-4 py-2 font-semibold text-sm transition-colors ${
          on
            ? "bg-bell text-white shadow-[0_0_20px_rgba(255,30,86,0.55)]"
            : "bg-bell/15 text-bell hover:bg-bell/25 animate-pulse-glow"
        }`}
      >
        <motion.span
          animate={on ? { rotate: [0, 14, -14, 10, -8, 0] } : {}}
          transition={{ duration: 1, repeat: on ? Infinity : 0, repeatDelay: 2.5 }}
        >
          {on ? <BellRing size={18} /> : <Bell size={18} />}
        </motion.span>
        <span className="hidden sm:inline">{on ? t("bell.enabled") : t("bell.enable")}</span>
        {count > 0 && (
          <span className="absolute -top-1.5 -right-1.5 bg-void text-volt text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full border border-volt/50">
            {count}
          </span>
        )}
      </motion.button>

      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8 }}
            className="absolute right-0 mt-3 w-64 z-50 rounded-xl bg-surface border border-bell/40 p-3 text-xs text-white shadow-2xl"
          >
            {t("bell.on")}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
