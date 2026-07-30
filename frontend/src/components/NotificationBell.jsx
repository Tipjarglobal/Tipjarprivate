import React, { useEffect, useRef, useState } from "react";
import { Bell, BellRing, Star, Volume2, VolumeX, Inbox, Settings, Trash2, X, Crown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import api from "../api";
import { isMobileDevice, playCoin } from "../coinSound";
import { useI18n, toLatin } from "../i18n";

function anonId() {
  let id = localStorage.getItem("tj_anon");
  if (!id) {
    id = "anon-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("tj_anon", id);
  }
  return id;
}

async function pushNotify(title, body, url, vibrate, icon) {
  try {
    // Foreground buzz: showNotification's vibrate is often ignored while the tab is
    // focused, so trigger the device vibration directly too (mobile only).
    if (vibrate && navigator.vibrate) { try { navigator.vibrate(vibrate); } catch { /* ignore */ } }
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    const ic = icon || "/tipjar-crest.png";
    if (navigator.serviceWorker) {
      const reg = await navigator.serviceWorker.ready;
      reg.showNotification(title, {
        body,
        icon: ic,
        badge: "/tipjar-crest.png",
        tag: "tipjar-tip",
        renotify: true,
        vibrate: vibrate || [60, 30, 60],
        data: { url: url || "/" },
        actions: url ? [{ action: "open", title: "Zum Pick →" }] : [],
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
async function enableWebPush(areas, minStars) {
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
  const body = { endpoint: json.endpoint, keys: json.keys, areas };
  if (minStars != null) body.min_stars = minStars;
  await api.post("/push/subscribe", body);
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
// Live is split: KI-live by category (live_banker / live_value / live_banger) vs
// community-live (live). Each live class fires its OWN kind of notification.
function tipArea(tp) {
  if (tp.is_expert) return "experts";
  const isAI = ["hq-auto", "hq-live", "hq-system", "smart"].includes(tp.source);
  if (tp.status === "live") {
    if (!isAI) return "live";
    const c = (tp.category || "").toLowerCase();
    if (c === "banker" || c === "value" || c === "banger") return `live_${c}`;
    return "live_value";
  }
  if (tp.source === "hq-auto") return "ai";
  if (tp.source === "smart") return "smart";
  return "members";
}

const DEFAULT_AREAS = { ai: true, systems: true, smart: true, experts: true, members: true, live: true, live_banker: true, live_value: true, live_banger: true };
const VIEW_KEY = { ai: "viewtips", systems: "viewsystems", smart: "viewsmart", experts: "viewmembers", members: "viewmembers", live: "viewlive", live_banker: "viewlive", live_value: "viewlive", live_banger: "viewlive" };
// Distinct emoji per live class so each alert type is instantly recognisable.
const LIVE_EMOJI = { live: "🔴", live_banker: "🟢", live_value: "🔵", live_banger: "🔥" };

function loadAreas() {
  try {
    const raw = localStorage.getItem("tj_bell_areas");
    if (raw) return { ...DEFAULT_AREAS, ...JSON.parse(raw) };
  } catch { /* ignore */ }
  return DEFAULT_AREAS;
}

const HISTORY_KEY = "tj_alert_history";
const HISTORY_CAP = 60;
function loadHistory() {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (raw) return JSON.parse(raw);
  } catch { /* ignore */ }
  return [];
}
function timeAgo(ts, nowLabel) {
  const s = Math.max(0, Math.floor((Date.now() - ts) / 1000));
  if (s < 45) return nowLabel;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}
const AREA_DOT = {
  ai: "bg-[#2ECC57]", smart: "bg-sky-400", members: "bg-volt", systems: "bg-purple-400",
  experts: "bg-orange-500",
  live: "bg-live", live_banker: "bg-cyan-400", live_value: "bg-[#E1FF00]", live_banger: "bg-orange-500",
};

export default function NotificationBell() {
  const { t } = useI18n();
  const [on, setOn] = useState(localStorage.getItem("tj_bell") === "1");
  const [min, setMin] = useState(Number(localStorage.getItem("tj_bell_min")) || 8);
  const [areas, setAreas] = useState(loadAreas());
  const [count, setCount] = useState(0);
  const [unseen, setUnseen] = useState(0);
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState("board");
  const [toastCount, setToastCount] = useState(0);
  const bumpToast = () => setToastCount((n) => n + 1);
  const dropToast = () => setToastCount((n) => Math.max(0, n - 1));
  const clearToasts = () => { toast.dismiss(); setToastCount(0); };
  const [history, setHistory] = useState(loadHistory);

  const pushHistory = (entry) => {
    setHistory((h) => {
      const next = [entry, ...h.filter((x) => x.key !== entry.key)].slice(0, HISTORY_CAP);
      try { localStorage.setItem(HISTORY_KEY, JSON.stringify(next)); } catch { /* ignore */ }
      return next;
    });
  };
  const clearHistory = () => {
    setHistory([]);
    try { localStorage.removeItem(HISTORY_KEY); } catch { /* ignore */ }
  };
  const [soundOn, setSoundOn] = useState(() => {
    try { return localStorage.getItem("tj_sound") !== "off"; } catch { return true; }
  });
  const mobile = isMobileDevice();
  const toggleSound = () => setSoundOn((v) => {
    const nx = !v;
    try { localStorage.setItem("tj_sound", nx ? "on" : "off"); } catch { /* ignore */ }
    return nx;
  });
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
    // Sync choices to the server so the REAL Web Push (app closed / screen off)
    // respects them too — not just the in-app popups. Includes the star threshold so a
    // "9★+" device only gets pushed 9-10★ picks server-side as well.
    (async () => {
      try {
        if (!supportsWebPush()) return;
        const reg = await navigator.serviceWorker.ready;
        const sub = await reg.pushManager.getSubscription();
        if (sub) await api.post("/push/preferences", { endpoint: sub.endpoint, areas, min_stars: min });
      } catch { /* ignore */ }
    })();
  }, [areas, min]);

  useEffect(() => {
    // Self-heal: if the browser already has push permission, make sure the SERVER
    // still holds our current subscription. It can silently vanish after a redeploy /
    // DB change or when the browser rotates the endpoint — leaving the user with no
    // pushes while the browser still thinks it's subscribed. Re-register idempotently
    // on every load (no prompt, since permission is already granted).
    (async () => {
      try {
        if (!supportsWebPush()) return;
        if (typeof Notification === "undefined" || Notification.permission !== "granted") return;
        const res = await enableWebPush(areasRef.current, minRef.current);
        if (res && res.ok) setOn(true);
      } catch { /* ignore */ }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);


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
    const isLive = area.startsWith("live");
    const navArea = area.startsWith("live") ? "live" : area;
    const areaLabel = t(`bell.area.${area}`);
    const name = tp.is_parlay
      ? `${(tp.legs || []).length}-leg parlay`
      : `${toLatin(tp.home_team) || "Tip"}${tp.away_team ? " vs " + toLatin(tp.away_team) : ""}`;
    const rating = tipRating(tp);
    const title = isLive
      ? `${LIVE_EMOJI[area] || "🔴"} ${t("bell.new.live")} — ${areaLabel}`
      : `${t(`bell.new.${area}`)}`;
    const body = `${areaLabel}: ${name}${rating ? ` — ${rating}/10 \u2b50` : ""}`;
    const vibrate = area === "live_banger" ? [200, 80, 200, 80, 300] : undefined;
    const icon = area === "experts" ? "/push-expert.png" : undefined;
    if (area === "experts") { try { playCoin("expert"); } catch { /* ignore */ } }
    // Master picks live under a sub-tab (special/safe/…) — carry it so the deep-link opens
    // the right tab and the pick actually loads.
    const sub = (tp.is_master || tp.source === "hq-master")
      ? (tp.master_category || "slips") : null;
    const pickUrl = tp.id
      ? `/?pick=${tp.id}&area=${navArea}${sub ? `&sub=${sub}` : ""}` : "/";
    pushNotify(title, body, pickUrl, vibrate, icon);
    pushHistory({
      key: `${tp.id || area}-${Date.now()}`, title, body, area, navArea,
      pickId: tp.id || null, ts: Date.now(),
    });
    toast[isLive ? "message" : "success"](title, {
      description: body,
      duration: isLive ? 15000 : 8000,
      onDismiss: dropToast,
      onAutoClose: dropToast,
      action: {
        label: tp.id ? t("bell.view_pick") : t(`nav.${VIEW_KEY[area] || "viewtips"}`),
        onClick: () => window.dispatchEvent(
          tp.id
            ? new CustomEvent("tj-open-pick", { detail: { area: navArea, id: tp.id, sub } })
            : new CustomEvent("tj-open-view", { detail: navArea })
        ),
      },
    });
    bumpToast();
    setUnseen((u) => u + 1);
  };

  // Coalesce a whole WAVE of new picks (same area) into ONE toast, so the user isn't
  // buried under a never-ending stack (owner: "es hört nie auf").
  const fireAlertBatch = (tps, area) => {
    const areaLabel = t(`bell.area.${area}`);
    const navArea = area.startsWith("live") ? "live" : area;
    const title = `${tps.length} × ${areaLabel}`;
    const names = tps.slice(0, 3).map((tp) => tp.is_parlay
      ? `${(tp.legs || []).length}-leg`
      : (toLatin(tp.home_team) || "Tip")).join(", ");
    const body = tps.length > 3 ? `${names} +${tps.length - 3}` : names;
    if (area === "experts") { try { playCoin("expert"); } catch { /* ignore */ } }
    pushHistory({ key: `batch-${area}-${Date.now()}`, title, body, area, navArea, pickId: null, ts: Date.now() });
    toast.message(title, {
      description: body,
      duration: 8000,
      onDismiss: dropToast,
      onAutoClose: dropToast,
      action: {
        label: t(`nav.${VIEW_KEY[area] || "viewtips"}`),
        onClick: () => window.dispatchEvent(new CustomEvent("tj-open-view", { detail: navArea })),
      },
    });
    bumpToast();
    setUnseen((u) => u + tps.length);
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
          const newByArea = {};
          for (const tp of data) {
            if (!seen.current.has(tp.id)) {
              const area = tipArea(tp);
              const isLive = area.startsWith("live");
              // The star slider now also governs EXPERT picks (they used to always ring
              // and flood the feed). Only live picks bypass it — those are time-critical
              // and already opt-in per area.
              const bypassThreshold = isLive;
              if (onRef.current && (areasRef.current[area] !== false) &&
                  (bypassThreshold || tipRating(tp) >= minRef.current)) {
                (newByArea[area] = newByArea[area] || []).push(tp);
              }
              seen.current.add(tp.id);
            }
          }
          // One toast per area per poll: single pick → detailed, a wave → one summary.
          for (const [area, tps] of Object.entries(newByArea)) {
            if (tps.length === 1) fireAlert(tps[0], area);
            else fireAlertBatch(tps, area);
          }
        }

        // 2) Live picks — detected separately so a tip going LIVE always rings
        const live = await api.get("/tips?status=live&limit=30");
        if (!mounted) return;
        if (seenLive.current === null) {
          seenLive.current = new Set(live.data.map((tp) => tp.id));
        } else {
          const newLiveByArea = {};
          for (const tp of live.data) {
            if (!seenLive.current.has(tp.id)) {
              const larea = tipArea({ ...tp, status: "live" });
              if (onRef.current && areasRef.current[larea] !== false) {
                (newLiveByArea[larea] = newLiveByArea[larea] || []).push({ ...tp, status: "live" });
              }
              seenLive.current.add(tp.id);
            }
          }
          for (const [larea, tps] of Object.entries(newLiveByArea)) {
            if (tps.length === 1) fireAlert(tps[0], larea);
            else fireAlertBatch(tps, larea);
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
        const res = await enableWebPush(areasRef.current, minRef.current);
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
      {toastCount > 0 && (
        <button
          type="button"
          data-testid="clear-toasts-btn"
          onClick={clearToasts}
          className="fixed top-2 right-2 z-[9999] flex items-center gap-1.5 rounded-full bg-bell text-white text-xs font-bold px-3 py-2 shadow-[0_0_20px_rgba(255,30,86,0.6)] active:scale-95 transition-transform"
        >
          <X size={14} /> {t("bell.clearToasts")} ({toastCount})
        </button>
      )}
      <motion.button
        data-testid="notification-bell"
        onClick={() => setOpen((o) => { const nx = !o; if (nx) setUnseen(0); return nx; })}
        whileTap={{ scale: 0.9 }}
        title={t("bell.tooltip")}
        className={`relative flex items-center gap-1.5 sm:gap-2 rounded-full px-2.5 sm:pl-3 sm:pr-4 py-1.5 sm:py-2 font-semibold text-sm transition-colors ${
          on
            ? "bg-bell text-white shadow-[0_0_20px_rgba(255,30,86,0.55)]"
            : "bg-bell/15 text-bell hover:bg-bell/25 animate-pulse-glow"
        }`}
      >
        <motion.span
          animate={on ? { rotate: [0, 14, -14, 10, -8, 0] } : {}}
          transition={{ duration: 1, repeat: on ? Infinity : 0, repeatDelay: 2.5 }}
        >
          {on ? <BellRing size={16} className="sm:hidden" /> : <Bell size={16} className="sm:hidden" />}
          {on ? <BellRing size={18} className="hidden sm:block" /> : <Bell size={18} className="hidden sm:block" />}
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
            <div className="flex items-center justify-between mb-3 gap-2">
              <div className="flex items-center gap-1 bg-void/50 rounded-full p-0.5" data-testid="bell-tabs">
                <button
                  onClick={() => setTab("board")}
                  data-testid="bell-tab-board"
                  className={`flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1 rounded-full transition-colors ${tab === "board" ? "bg-bell text-white" : "text-zinc-400 hover:text-white"}`}
                >
                  <Inbox size={12} /> {t("bell.board")}
                  {history.length > 0 && <span className="text-[9px] font-mono bg-void/40 px-1 rounded-full">{history.length > 99 ? "99+" : history.length}</span>}
                </button>
                <button
                  onClick={() => setTab("settings")}
                  data-testid="bell-tab-settings"
                  className={`flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1 rounded-full transition-colors ${tab === "settings" ? "bg-bell text-white" : "text-zinc-400 hover:text-white"}`}
                >
                  <Settings size={12} /> {t("bell.board_settings")}
                </button>
              </div>
              <button
                onClick={toggle}
                data-testid="bell-toggle-btn"
                className={`text-[11px] font-bold px-2.5 py-1 rounded-full transition-colors shrink-0 ${
                  on ? "bg-bell text-white" : "bg-bell/15 text-bell hover:bg-bell/25"
                }`}
              >
                {on ? t("bell.enabled") : t("bell.enable")}
              </button>
            </div>

            {tab === "board" && (
              <div data-testid="bell-board">
                {history.length > 0 && (
                  <div className="flex items-center justify-end mb-2">
                    <button
                      onClick={clearHistory}
                      data-testid="bell-board-clear"
                      className="flex items-center gap-1 text-[11px] font-semibold text-zinc-400 hover:text-bell transition-colors"
                    >
                      <Trash2 size={12} /> {t("bell.board_clear")}
                    </button>
                  </div>
                )}
                <div className="max-h-[60vh] sm:max-h-80 overflow-y-auto -mx-1 px-1 space-y-1.5">
                  {history.length === 0 ? (
                    <div className="flex flex-col items-center gap-2 py-10 text-center" data-testid="bell-board-empty">
                      <Inbox size={28} className="text-zinc-600" />
                      <p className="text-[13px] text-zinc-500 leading-snug px-4">{t("bell.board_empty")}</p>
                    </div>
                  ) : history.map((h) => (
                    <button
                      key={h.key}
                      data-testid="bell-board-item"
                      onClick={() => {
                        setOpen(false);
                        window.dispatchEvent(
                          h.pickId
                            ? new CustomEvent("tj-open-pick", { detail: { area: h.navArea, id: h.pickId } })
                            : new CustomEvent("tj-open-view", { detail: h.navArea })
                        );
                      }}
                      className="w-full text-left rounded-xl bg-void/60 border border-white/5 hover:border-bell/40 p-2.5 transition-colors"
                    >
                      <div className="flex items-start gap-2">
                        <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${AREA_DOT[h.area] || "bg-zinc-500"}`} />
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-[13px] font-bold text-white truncate">{h.title}</p>
                            <span className="text-[10px] font-mono text-zinc-500 shrink-0">{timeAgo(h.ts, t("bell.board_now"))}</span>
                          </div>
                          <p className="text-[11px] text-zinc-400 mt-0.5 leading-snug line-clamp-2">{h.body}</p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {tab === "settings" && (<>
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
              {[["master", "bell.area.master"], ["ai", "bell.area.ai"], ["systems", "bell.area.systems"], ["smart", "bell.area.smart"], ["experts", "bell.area.experts"], ["members", "bell.area.members"]].map(([k, lbl]) => (
                <label key={k} data-testid={`bell-area-${k}`} className="flex items-center justify-between py-1.5 cursor-pointer">
                  <span className={`text-sm flex items-center gap-2 ${k === "master" ? "text-[#E11D2A] font-black" : "text-zinc-300"}`}>
                    {k === "experts" && <span className="w-2 h-2 rounded-full bg-orange-500" />}
                    {k === "master" && <Crown size={13} className="text-[#E11D2A]" />}
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
              {/* Live is the only area where KI + Community post together. The KI-live
                  side is split into three notification classes (Banker / Value / Banger),
                  each with its own alert type; the community-live box stays separate. */}
              <div data-testid="bell-area-live" className="py-1.5 border-t border-elevated/60 mt-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-zinc-300 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-live animate-pulse" />
                    {t("bell.area.live")}
                  </span>
                  <label className="flex items-center gap-1.5 cursor-pointer" data-testid="bell-area-live-community">
                    <span className="text-[11px] font-bold text-zinc-400 uppercase tracking-wide">{t("bell.area.members")}</span>
                    <input
                      type="checkbox"
                      checked={areas.live !== false}
                      onChange={(e) => setAreas((a) => ({ ...a, live: e.target.checked }))}
                      data-testid="bell-area-toggle-live"
                      className="w-4 h-4 cursor-pointer accent-bell"
                    />
                  </label>
                </div>
                <div className="mt-1.5 ml-4 space-y-1">
                  {[["live_banker", "Banker", "text-cyan-300", "accent-cyan-400"],
                    ["live_value", "Value", "text-[#E1FF00]", "accent-[#E1FF00]"],
                    ["live_banger", "Banger", "text-orange-400", "accent-orange-500"]].map(([k, lbl, txt, acc]) => (
                    <label key={k} data-testid={`bell-area-${k}`} className="flex items-center justify-between py-1 cursor-pointer">
                      <span className={`text-[13px] font-bold uppercase tracking-wide ${txt}`}>{lbl}</span>
                      <input
                        type="checkbox"
                        checked={areas[k] !== false}
                        onChange={(e) => setAreas((a) => ({ ...a, [k]: e.target.checked }))}
                        data-testid={`bell-area-toggle-${k}`}
                        className={`w-4 h-4 cursor-pointer ${acc}`}
                      />
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Sound — on mobile it always follows the phone's ring/silent switch */}
            <div className="mt-3 pt-3 border-t border-elevated" data-testid="bell-sound-section">
              {mobile ? (
                <p className="text-[11px] text-zinc-400 leading-snug flex items-start gap-1.5" data-testid="bell-sound-mobile-note">
                  <VolumeX size={13} className="mt-0.5 shrink-0 text-zinc-500" />
                  {t("bell.sound_mobile")}
                </p>
              ) : (
                <label className="flex items-center justify-between py-1 cursor-pointer" data-testid="bell-sound-toggle-row">
                  <span className="text-sm text-zinc-300 flex items-center gap-2">
                    {soundOn ? <Volume2 size={15} className="text-bell" /> : <VolumeX size={15} className="text-zinc-500" />}
                    {t("bell.sound")}
                  </span>
                  <input
                    type="checkbox"
                    checked={soundOn}
                    onChange={toggleSound}
                    data-testid="bell-sound-toggle"
                    className="accent-bell w-4 h-4 cursor-pointer"
                  />
                </label>
              )}
            </div>

            {on && supportsWebPush() && (
              <button
                data-testid="bell-test-push"
                onClick={async () => {
                  try {
                    const reg = await navigator.serviceWorker.ready;
                    const sub = await reg.pushManager.getSubscription();
                    if (!sub) { toast.error(t("bell.test_fail")); return; }
                    const json = sub.toJSON();
                    await api.post("/push/subscribe", { endpoint: json.endpoint, keys: json.keys, areas: areasRef.current });
                    const { data } = await api.post("/push/test", { endpoint: json.endpoint, keys: json.keys });
                    if (data.ok) {
                      toast.success(t("bell.test_sent"), { description: t("bell.test_hint"), duration: 9000 });
                    } else {
                      toast.error(`${t("bell.test_fail")}${data.reason ? ` — ${data.reason}` : ""}`, { duration: 12000 });
                    }
                  } catch (e) { toast.error(`${t("bell.test_fail")}${e && e.message ? ` — ${e.message}` : ""}`); }
                }}
                className="mt-3 w-full text-sm py-2 rounded-lg border border-bell/40 text-bell hover:bg-bell/10 transition-colors flex items-center justify-center gap-2"
              >
                <BellRing size={14} /> {t("bell.test")}
              </button>
            )}


            {on && <p className="text-[11px] text-bell mt-2">{t("bell.on")}</p>}
            {count > 0 && (
              <p className="text-[11px] text-zinc-500 mt-3 pt-3 border-t border-elevated flex items-center gap-1.5" data-testid="bell-subscriber-count">
                <BellRing size={12} className="text-bell" /> {count} {t("bell.subscribers")}
              </p>
            )}
            </>)}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
