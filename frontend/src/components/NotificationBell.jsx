import React, { useEffect, useRef, useState } from "react";
import { Bell, BellRing, Star } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
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

// ── Web Push helpers (real notifications when the app is closed / screen off) ──
function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}
function supportsWebPush() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}
function isStandalonePwa() {
  return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
}
function isIos() {
  return /iPhone|iPad|iPod/.test(navigator.userAgent);
}
async function enableWebPush() {
  if (!supportsWebPush()) return { ok: false, reason: "unsupported" };
  if (isIos() && !isStandalonePwa()) return { ok: false, reason: "ios-install" };
  const reg = await navigator.serviceWorker.ready;
  const { data } = await api.get("/push/vapid-public-key");
  if (!data.publicKey) return { ok: false, reason: "no-key" };
  const existing = await reg.pushManager.getSubscription();
  const sub = existing || await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(data.publicKey),
  });
  const json = sub.toJSON();
  await api.post("/push/subscribe", { endpoint: json.endpoint, keys: json.keys });
  return { ok: true };
}
async function disableWebPush() {
  try {
    if (!supportsWebPush()) return;
    const reg = await navigator.serviceWorker.ready;
    const sub = await reg.pushManager.getSubscription();
    if (sub) {
      await api.post("/push/unsubscribe", { endpoint: sub.endpoint, keys: sub.toJSON().keys || {} }).catch(() => {});
      await sub.unsubscribe().catch(() => {});
    }
  } catch { /* ignore */ }
}

// Which picks area does a tip belong to (for area-targeted alerts)?
function tipArea(tp) {
  if (tp.status === "live") return "live";
  if (tp.source === "hq-auto") return "ai";
  if (tp.source === "smart") return "smart";
  return "members";
}

const DEFAULT_AREAS = { ai: true, systems: true, smart: true, members: true, live: true };
const VIEW_KEY = { ai: "viewtips", systems: "viewsystems", smart: "viewsmart", members: "viewmembers", live: "viewlive" };

function loadAreas() {
  try {
    const raw = localStorage.getItem("tj_bell_areas");
    if (raw) return { ...DEFAULT_AREAS, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return DEFAULT_AREAS;
}

export default function NotificationBell() {
  const { t } = useI18n();
  const [on, setOn] = useState(localStorage.getItem("tj_bell") === "1");
  const [min, setMin] = useState(Number(localStorage.getItem("tj_bell_min")) || 8);
  const [areas, setAreas] = useState(loadAreas());
  const [count, setCount] = useState(0);
  const [unseen, setUnseen] = useState(0);
  const [open, setOpen] = useState(false);
  const seen = useRef(null);
  const seenLive = useRef(null);
  const lastSystems = useRef(null);
  const onRef = useRef(on);
  const minRef = useRef(min);
  const areasRef = useRef(areas);
  onRef.current = on;
  minRef.current = min;
  areasRef.current = areas;

  useEffect(() => {
    localStorage.setItem("tj_bell_min", String(min));
  }, [min]);

  useEffect(() => {
    localStorage.setItem("tj_bell_areas", JSON.stringify(areas));
  }, [areas]);

  useEffect(() => {
    const openHandler = () => { setOpen(true); setUnseen(0); };
    window.addEventListener("tj-open-alerts", openHandler);
    const enabledHandler = () => setOn(true);  // synced when the prompt enables push
    window.addEventListener("tj-push-enabled", enabledHandler);
    return () => {
      window.removeEventListener("tj-open-alerts", openHandler);
      window.removeEventListener("tj-push-enabled", enabledHandler);
    };
  }, []);

  const fireAlert = (tp, area) => {
    const areaLabel = t(`bell.area.${area}`);
    const name = tp.is_parlay
      ? `${(tp.legs || []).length}-leg parlay`
      : `${tp.home_team || "Tip"}${tp.away_team ? " vs " + tp.away_team : ""}`;
    const rating = tipRating(tp);
    const title = area === "live"
      ? `\uD83D\uDD34 ${t("bell.new.live")} — ${areaLabel}`
      : `${t(`bell.new.${area}`)}`;
    const body = `${areaLabel}: ${name}${rating ? ` — ${rating}/10 \u2b50` : ""}`;
    pushNotify(title, body);
    toast[area === "live" ? "message" : "success"](title, {
      description: body,
      duration: area === "live" ? 15000 : 10000,
      action: {
        label: tp.id ? t("bell.view_pick") : t(`nav.${VIEW_KEY[area] || "viewtips"}`),
        onClick: () => window.dispatchEvent(
          tp.id
            ? new CustomEvent("tj-open-pick", { detail: { area, id: tp.id } })
            : new CustomEvent("tj-open-view", { detail: area })
        ),
      },
    });
    setUnseen((u) => u + 1);
  };

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const stats = await api.get("/notifications/stats");
        if (mounted) setCount(stats.data.subscriber_count);

        // 1) New posts (AI / members) — detected by new tip ids
        const { data } = await api.get("/tips?limit=30&sort=new");
        if (!mounted) return;
        if (seen.current === null) {
          seen.current = new Set(data.map((tp) => tp.id));
        } else {
          for (const tp of data) {
            if (!seen.current.has(tp.id)) {
              const area = tipArea(tp);
              if (onRef.current && (areasRef.current[area] !== false) &&
                  (area === "live" || tipRating(tp) >= minRef.current)) {
                fireAlert(tp, area);
              }
              seen.current.add(tp.id);
            }
          }
        }

        // 2) Live picks — detected separately so a tip going LIVE always rings
        const live = await api.get("/tips?status=live&limit=30");
        if (!mounted) return;
        if (seenLive.current === null) {
          seenLive.current = new Set(live.data.map((tp) => tp.id));
        } else {
          for (const tp of live.data) {
            if (!seenLive.current.has(tp.id)) {
              if (onRef.current && areasRef.current.live !== false) {
                fireAlert({ ...tp, status: "live" }, "live");
              }
              seenLive.current.add(tp.id);
            }
          }
        }

        // 3) System Picks — no per-tip event, so ring when the systems count grows
        const counts = await api.get("/tips/counts");
        if (!mounted) return;
        const sysN = Number(counts.data.systems || 0);
        if (lastSystems.current === null) {
          lastSystems.current = sysN;
        } else if (sysN > lastSystems.current) {
          if (onRef.current && areasRef.current.systems !== false) {
            fireAlert({ home_team: t("bell.area.systems"), away_team: "" }, "systems");
          }
          lastSystems.current = sysN;
        } else {
          lastSystems.current = sysN;
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
          const perm = await Notification.requestPermission();
          if (perm !== "granted") { toast.error(t("bell.denied")); return; }
        }
        const { data } = await api.post("/notifications/subscribe", { anon_id: id });
        setCount(data.subscriber_count);
      } catch {
        /* ignore */
      }
      // Real Web Push (works when app closed / screen off)
      try {
        const res = await enableWebPush();
        if (res.ok) toast.success(t("bell.push_on"));
        else if (res.reason === "ios-install") toast.info(t("bell.ios_hint"), { duration: 9000 });
      } catch { /* ignore */ }
      setOn(true);
      localStorage.setItem("tj_bell", "1");
    } else {
      try {
        const { data } = await api.post("/notifications/unsubscribe", { anon_id: id });
        setCount(data.subscriber_count);
      } catch {
        /* ignore */
      }
      await disableWebPush();
      setOn(false);
      localStorage.removeItem("tj_bell");
    }
  };

  return (
    <div className="relative">
      <motion.button
        data-testid="notification-bell"
        onClick={() => setOpen((o) => { const nx = !o; if (nx) setUnseen(0); return nx; })}
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
        {on && unseen > 0 && (
          <span className="absolute -top-1.5 -right-1.5 bg-void text-volt text-[10px] font-mono font-bold px-1.5 py-0.5 rounded-full border border-volt/50" data-testid="bell-unseen-badge">
            {unseen > 9 ? "9+" : unseen}
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
            className="fixed left-4 right-4 top-20 w-auto max-w-xs mx-auto sm:absolute sm:left-auto sm:right-0 sm:top-auto sm:mt-3 sm:w-72 sm:max-w-none sm:mx-0 z-50 rounded-2xl bg-surface border border-bell/40 p-4 text-white shadow-2xl"
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

            <div className="mt-3 pt-3 border-t border-elevated">
              <p className="text-[11px] uppercase tracking-widest text-zinc-500 mb-1.5">{t("bell.areas")}</p>
              {[["ai", "bell.area.ai"], ["systems", "bell.area.systems"], ["smart", "bell.area.smart"], ["members", "bell.area.members"], ["live", "bell.area.live"]].map(([k, lbl]) => (
                <label key={k} data-testid={`bell-area-${k}`} className="flex items-center justify-between py-1.5 cursor-pointer">
                  <span className="text-sm text-zinc-300 flex items-center gap-2">
                    {k === "live" && <span className="w-2 h-2 rounded-full bg-live animate-pulse" />}
                    {t(lbl)}
                  </span>
                  <input
                    type="checkbox"
                    checked={areas[k] !== false}
                    onChange={(e) => setAreas((a) => ({ ...a, [k]: e.target.checked }))}
                    data-testid={`bell-area-toggle-${k}`}
                    className="accent-bell w-4 h-4 cursor-pointer"
                  />
                </label>
              ))}
            </div>

            {on && <p className="text-[11px] text-bell mt-2">{t("bell.on")}</p>}
            {count > 0 && (
              <p className="text-[11px] text-zinc-500 mt-3 pt-3 border-t border-elevated flex items-center gap-1.5" data-testid="bell-subscriber-count">
                <BellRing size={12} className="text-bell" /> {count} {t("bell.subscribers")}
              </p>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
