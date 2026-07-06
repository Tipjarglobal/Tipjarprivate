import React, { useEffect, useRef, useState } from "react";
import { Bell, BellRing, Star } from "lucide-react";
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

async function pushNotify(title, body) {
  try {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    if (navigator.serviceWorker) {
      const reg = await navigator.serviceWorker.ready;
      reg.showNotification(title, {
        body,
        icon: "/tipjar-crest.png",
        badge: "/tipjar-crest.png",
        tag: "tipjar-tip",
        renotify: true,
      });
    } else {
      new Notification(title, { body });
    }
  } catch {
    /* ignore */
  }
}

function tipRating(tp) {
  return Math.max(Number(tp.ai_rating || 0), Number(tp.avg_rating || 0));
}

export default function NotificationBell() {
  const { t } = useI18n();
  const [on, setOn] = useState(localStorage.getItem("tj_bell") === "1");
  const [min, setMin] = useState(Number(localStorage.getItem("tj_bell_min")) || 8);
  const [count, setCount] = useState(0);
  const [open, setOpen] = useState(false);
  const seen = useRef(null);
  const onRef = useRef(on);
  const minRef = useRef(min);
  onRef.current = on;
  minRef.current = min;

  useEffect(() => {
    localStorage.setItem("tj_bell_min", String(min));
  }, [min]);

  useEffect(() => {
    const openHandler = () => setOpen(true);
    window.addEventListener("tj-open-alerts", openHandler);
    return () => window.removeEventListener("tj-open-alerts", openHandler);
  }, []);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const stats = await api.get("/notifications/stats");
        if (mounted) setCount(stats.data.subscriber_count);
        const { data } = await api.get("/tips?limit=30&sort=new");
        if (!mounted) return;
        if (seen.current === null) {
          seen.current = new Set(data.map((tp) => tp.id));
          return;
        }
        for (const tp of data) {
          if (!seen.current.has(tp.id)) {
            if (onRef.current && tipRating(tp) >= minRef.current) {
              const name = tp.is_parlay
                ? `${(tp.legs || []).length}-leg parlay`
                : `${tp.home_team || "Tip"}${tp.away_team ? " vs " + tp.away_team : ""}`;
              pushNotify(t("bell.push_title"), `${name} — ${tipRating(tp)}/10 \u2b50`);
            }
            seen.current.add(tp.id);
          }
        }
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
  }, [t]);

  const toggle = async () => {
    const id = anonId();
    if (!on) {
      try {
        if (window.Notification && Notification.permission !== "granted") {
          await Notification.requestPermission();
        }
        const { data } = await api.post("/notifications/subscribe", { anon_id: id });
        setCount(data.subscriber_count);
      } catch {
        /* ignore */
      }
      setOn(true);
      localStorage.setItem("tj_bell", "1");
    } else {
      try {
        const { data } = await api.post("/notifications/unsubscribe", { anon_id: id });
        setCount(data.subscriber_count);
      } catch {
        /* ignore */
      }
      setOn(false);
      localStorage.removeItem("tj_bell");
    }
  };

  return (
    <div className="relative">
      <motion.button
        data-testid="notification-bell"
        onClick={() => setOpen((o) => !o)}
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
        {on && (
          <span className="text-[10px] font-mono font-bold bg-void/40 px-1.5 py-0.5 rounded-full" data-testid="bell-threshold-badge">
            {min}+
          </span>
        )}
        {count > 0 && (
          <span className="absolute -top-1.5 -right-1.5 bg-void text-volt text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full border border-volt/50">
            {count}
          </span>
        )}
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 mt-3 w-72 z-50 rounded-2xl bg-surface border border-bell/40 p-4 text-white shadow-2xl"
            data-testid="bell-settings-panel"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="font-heading font-black text-sm uppercase tracking-wide">{t("bell.settings")}</span>
              <button
                onClick={toggle}
                data-testid="bell-toggle-btn"
                className={`text-[11px] font-bold px-2.5 py-1 rounded-full transition-colors ${
                  on ? "bg-bell text-white" : "bg-bell/15 text-bell hover:bg-bell/25"
                }`}
              >
                {on ? t("bell.enabled") : t("bell.enable")}
              </button>
            </div>

            <div className="flex items-center justify-between text-xs text-zinc-400 mb-1">
              <span>{t("bell.threshold")}</span>
              <span className="flex items-center gap-1 font-mono font-bold text-volt" data-testid="bell-threshold-value">
                {min}/10 <Star size={12} className="fill-volt text-volt" />
              </span>
            </div>
            <input
              type="range"
              min="1"
              max="10"
              step="1"
              value={min}
              onChange={(e) => setMin(Number(e.target.value))}
              data-testid="bell-threshold-slider"
              className="w-full accent-bell cursor-pointer"
            />
            <p className="text-[11px] text-zinc-500 mt-2 leading-snug">{t("bell.threshold_hint")}</p>
            {on && <p className="text-[11px] text-bell mt-2">{t("bell.on")}</p>}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
