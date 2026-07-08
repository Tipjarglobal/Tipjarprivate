import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import confetti from "canvas-confetti";
import { Flame, Users, Trophy, Zap, RefreshCw, CheckCircle2, XCircle, Radio, Clock, Trash2, Share2, Brain, Send, Lightbulb } from "lucide-react";
import StarRating from "./StarRating";
import { Systems } from "./Systems";
import { OddsValue } from "./OddsValue";
import api, { apiErr, fileUrl } from "../api";
import { shareSlip } from "../shareSlip";
import { useI18n, localizeMarket, formatSelection } from "../i18n";
import { useAuth } from "../auth";
import { toast } from "sonner";

const FILTERS = [
  { k: "new", label: "wall.filter.new" },
  { k: "hype", label: "wall.filter.hype" },
  { k: "top", label: "wall.filter.top" },
];
const VIEW_TITLE_KEY = {
  ai: "nav.viewtips",
  systems: "nav.viewsystems",
  members: "nav.viewmembers",
  live: "nav.viewlive",
  smart: "nav.viewsmart",
  settled: "nav.viewsettled",
};
const STATUS = [
  { k: "", label: "wall.filter.pending", val: "pending" },
];

export default function RateWall({ refreshKey, requireLogin, view = "ai", onUserClick }) {
  const { t } = useI18n();
  const { user, setUser } = useAuth();
  const [tips, setTips] = useState([]);
  const [sort, setSort] = useState("new");
  const [status, setStatus] = useState(view === "live" ? "live" : "pending");
  const [win, setWin] = useState("24");
  const [myRatings, setMyRatings] = useState({});
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [streakBubble, setStreakBubble] = useState(false);
  const [wonTips, setWonTips] = useState([]);
  const [lostTips, setLostTips] = useState([]);
  const [settledTab, setSettledTab] = useState(null);

  useEffect(() => {
    setStatus(view === "live" ? "live" : "pending");
  }, [view]);

  const load = useCallback(async (silent) => {
    if (view === "settled") return;
    if (!silent) setLoading(true);
    try {
      const params = { sort };
      const st = view === "live" ? "live" : status;
      if (st) params.status = st;
      if (view === "ai") { params.source = "ai"; if (win !== "all") params.window = win; }
      else if (view === "members") params.source = "members";
      else if (view === "smart") params.source = "smart";
      const { data } = await api.get("/tips", { params });
      setTips(data);
    } catch { /* ignore */ } finally { if (!silent) setLoading(false); }
  }, [sort, status, view, win]);

  useEffect(() => {
    load();
    const iv = setInterval(() => load(true), 20000);
    return () => clearInterval(iv);
  }, [load, refreshKey]);

  useEffect(() => {
    if (view !== "settled") return;
    let alive = true;
    const loadSettled = async () => {
      try {
        const [w, l] = await Promise.all([
          api.get("/tips", { params: { status: "won", sort: "new", limit: 50 } }),
          api.get("/tips", { params: { status: "lost", sort: "new", limit: 50 } }),
        ]);
        if (alive) { setWonTips(w.data); setLostTips(l.data); }
      } catch { /* ignore */ }
    };
    loadSettled();
    const iv = setInterval(loadSettled, 20000);
    return () => { alive = false; clearInterval(iv); };
  }, [view, refreshKey]);

  const rate = async (tip, stars) => {
    if (!user) { requireLogin(); return; }
    try {
      const { data } = await api.post(`/tips/${tip.id}/rate`, { stars });
      if (data.deleted) {
        setTips((ts) => ts.filter((x) => x.id !== data.tip_id));
        if (user) setUser({ ...user, streak: data.streak });
        toast.success(t("wall.removed"));
        return;
      }
      setMyRatings((m) => ({ ...m, [tip.id]: stars }));
      setTips((ts) => ts.map((x) => (x.id === tip.id ? data.tip : x)));
      if (user) setUser({ ...user, streak: data.streak, apex_flame: data.apex_flame ?? user.apex_flame, ratings_given: (user.ratings_given || 0) + 1 });
      confetti({ particleCount: 45, spread: 60, origin: { y: 0.7 }, colors: ["#E1FF00", "#00FF94", "#FFFFFF"] });
      if (data.apex_flame_new) {
        confetti({ particleCount: 160, spread: 100, origin: { y: 0.5 }, colors: ["#E1FF00", "#FF6A00", "#FFFFFF"] });
        toast.success(t("wall.flameUnlocked"), { duration: 6000 });
      } else {
        toast.success(t("wall.thanks"));
      }
    } catch (err) {
      toast.error(apiErr(err));
    }
  };

  const settle = async (tip, s) => {
    try {
      const { data } = await api.put(`/tips/${tip.id}/status`, { status: s });
      setTips((ts) => ts.map((x) => (x.id === tip.id ? data : x)));
    } catch (err) { toast.error(apiErr(err)); }
  };

  const del = async (tip) => {
    if (!window.confirm(t("wall.delete_confirm"))) return;
    try {
      await api.delete(`/tips/${tip.id}`);
      setTips((ts) => ts.filter((x) => x.id !== tip.id));
      toast.success(t("wall.deleted"));
    } catch (err) { toast.error(apiErr(err)); }
  };

  const syncNow = async () => {
    setSyncing(true);
    try {
      const { data } = await api.post("/admin/settle-now");
      if (!data.ok) toast.error(data.reason || "Results engine not configured");
      else toast.success(`✅ ${data.settled} settled / ${data.checked} checked`);
      load();
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setSyncing(false);
    }
  };

  return (
    <section id="ratewall" className="max-w-7xl mx-auto px-4 sm:px-6 py-16 scroll-mt-20">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
        <div>
          <span className="text-xs font-bold uppercase tracking-[0.25em] text-volt flex items-center gap-2"><Zap size={14} /> Apex Scale</span>
          <h2 className="font-heading text-3xl md:text-5xl font-black text-white tracking-tighter mt-2">{t(VIEW_TITLE_KEY[view] || "wall.title")}</h2>
          <p className="text-zinc-400 mt-2 max-w-lg">{t("wall.subtitle")}</p>
        </div>
        {user && (
          <div className="flex items-center gap-3">
            {user.role === "admin" && (
              <button data-testid="sync-results-btn" onClick={syncNow} disabled={syncing}
                className="flex items-center gap-2 rounded-2xl border border-volt/40 text-volt font-semibold px-4 py-3 hover:bg-volt/10 active:scale-95 transition-all disabled:opacity-50">
                <RefreshCw size={18} className={syncing ? "animate-spin" : ""} />
                <span className="text-sm">{syncing ? t("wall.syncing") : t("wall.sync")}</span>
              </button>
            )}
            {user && !user.apex_flame && (
            <div className="relative">
              <button
                type="button"
                onClick={() => setStreakBubble((v) => !v)}
                data-testid="streak-widget"
                className="flex items-center gap-3 rounded-2xl bg-surface border border-elevated px-4 py-3 hover:border-bell/50 transition-colors"
              >
                <Flame className="text-bell" size={28} />
                <div className="text-left">
                  <p className="text-[10px] uppercase tracking-widest text-zinc-500">{t("wall.streak")}</p>
                  <p className="font-mono font-black text-2xl text-white">{user.streak || 0} <span className="text-sm text-zinc-500">{t("wall.days")}</span></p>
                </div>
              </button>
              {streakBubble && (
                <div
                  data-testid="streak-bubble"
                  className="absolute left-0 top-full mt-2 z-30 w-64 rounded-2xl bg-void border border-bell/40 p-4 shadow-[0_0_30px_rgba(255,106,0,0.25)]"
                >
                  <div className="absolute -top-1.5 left-10 w-3 h-3 rotate-45 bg-void border-l border-t border-bell/40" />
                  <p className="text-sm text-zinc-200 leading-snug">
                    🔥 {t("wall.streakGoal1")} <span className="font-black text-bell">{Math.max(0, 30 - (user.streak || 0))}</span> {t("wall.streakGoal2")}
                  </p>
                  <div className="mt-3 h-2 rounded-full bg-elevated overflow-hidden">
                    <div className="h-full bg-bell" style={{ width: `${Math.min(100, ((user.streak || 0) / 30) * 100)}%` }} />
                  </div>
                </div>
              )}
            </div>
            )}
          </div>
        )}
      </div>

      {/* Abgerechnet — Won (left) / Lost (right) as clickable toggles.
          Slips are shown only AFTER a category is selected. Auto-deleted after 24h. */}
      {view === "settled" && (
        <div data-testid="settled-area">
          <div className="flex items-center gap-2 mb-6 rounded-xl border border-white/15 bg-white/5 px-4 py-3">
            <Clock size={16} className="text-zinc-400 shrink-0" />
            <p className="text-sm text-zinc-300">{t("settled.note")}</p>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-8">
            <button
              type="button"
              data-testid="settled-won-toggle"
              onClick={() => setSettledTab((v) => (v === "won" ? null : "won"))}
              className={`flex items-center justify-center gap-2 rounded-xl border px-4 py-4 font-heading font-black text-lg transition-all ${
                settledTab === "won"
                  ? "bg-won text-void border-won shadow-[0_0_18px_rgba(46,204,87,0.45)]"
                  : "bg-won/10 border-won/40 text-won hover:bg-won/20"
              }`}
            >
              <CheckCircle2 size={22} /> {t("wall.filter.won")}
              <span className={`text-xs font-mono rounded-full px-1.5 ${settledTab === "won" ? "bg-black/20" : "bg-void/60"}`}>{wonTips.length}</span>
            </button>
            <button
              type="button"
              data-testid="settled-lost-toggle"
              onClick={() => setSettledTab((v) => (v === "lost" ? null : "lost"))}
              className={`flex items-center justify-center gap-2 rounded-xl border px-4 py-4 font-heading font-black text-lg transition-all ${
                settledTab === "lost"
                  ? "bg-lost text-white border-lost shadow-[0_0_18px_rgba(239,68,68,0.45)]"
                  : "bg-lost/10 border-lost/40 text-lost hover:bg-lost/20"
              }`}
            >
              <XCircle size={22} /> {t("wall.filter.lost")}
              <span className={`text-xs font-mono rounded-full px-1.5 ${settledTab === "lost" ? "bg-black/20" : "bg-void/60"}`}>{lostTips.length}</span>
            </button>
          </div>

          {settledTab === null && (
            <p data-testid="settled-hint" className="text-zinc-500 text-sm py-10 text-center rounded-xl border border-dashed border-elevated">
              {t("settled.choose")}
            </p>
          )}

          {settledTab === "won" && (
            <div data-testid="settled-won-col" className="space-y-5">
              {wonTips.length === 0
                ? <p className="text-zinc-600 text-sm py-8 text-center rounded-xl border border-dashed border-elevated">{t("settled.empty.won")}</p>
                : wonTips.map((tip, i) => (
                    <TipCard key={tip.id} tip={tip} i={i} t={t} onRate={rate} myStars={myRatings[tip.id]} isAdmin={user?.role === "admin"} onSettle={settle} onDelete={del} canDelete={user?.role === "admin" || tip.user_id === user?.id} onUserClick={onUserClick} />
                  ))}
            </div>
          )}

          {settledTab === "lost" && (
            <div data-testid="settled-lost-col" className="space-y-5">
              {lostTips.length === 0
                ? <p className="text-zinc-600 text-sm py-8 text-center rounded-xl border border-dashed border-elevated">{t("settled.empty.lost")}</p>
                : lostTips.map((tip, i) => (
                    <TipCard key={tip.id} tip={tip} i={i} t={t} onRate={rate} myStars={myRatings[tip.id]} isAdmin={user?.role === "admin"} onSettle={settle} onDelete={del} canDelete={user?.role === "admin" || tip.user_id === user?.id} onUserClick={onUserClick} />
                  ))}
            </div>
          )}
        </div>
      )}

      {/* Systeme der Woche (Lock Bet / Value / Risk / Gamble) */}
      {view === "systems" && <Systems />}

      {view !== "systems" && view !== "settled" && (
        <>
      {view === "smart" && <SmartLab t={t} user={user} onCreated={() => load(true)} />}
      {/* filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        {FILTERS.map((f) => (
          <button key={f.k} data-testid={`sort-${f.k}`} onClick={() => setSort(f.k)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors ${sort === f.k ? "bg-volt text-void" : "bg-surface border border-elevated text-zinc-400 hover:text-white"}`}>
            {t(f.label)}
          </button>
        ))}
        {view !== "live" && <span className="w-px bg-elevated mx-1" />}
        {view !== "live" && [["pending", "wall.filter.pending"], ["live", "wall.filter.live"], ["won", "wall.filter.won"], ["lost", "wall.filter.lost"]].map(([v, lbl]) => (
          <button key={v} data-testid={`status-${v}`} onClick={() => setStatus(v)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors ${status === v ? "bg-white text-void" : "bg-surface border border-elevated text-zinc-400 hover:text-white"}`}>
            {t(lbl)}
          </button>
        ))}
      </div>

      {view === "ai" && (
        <div className="flex flex-wrap gap-2 mb-6" data-testid="window-filter">
          <span className="flex items-center gap-1.5 text-xs uppercase tracking-widest text-zinc-500 mr-1 self-center"><Clock size={13} /> Anstoß</span>
          {[["24", "wall.win.24"], ["48", "wall.win.48"], ["48plus", "wall.win.48plus"], ["all", "wall.win.all"]].map(([v, lbl]) => (
            <button key={v} data-testid={`window-${v}`} onClick={() => setWin(v)}
              className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors ${win === v ? "bg-volt text-void" : "bg-surface border border-elevated text-zinc-400 hover:text-white"}`}>
              {t(lbl)}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <p className="text-zinc-500 text-center py-16">{t("common.loading")}</p>
      ) : tips.length === 0 ? (
        <div className="text-center py-20 rounded-2xl border border-dashed border-elevated" data-testid="wall-empty">
          <Trophy className="mx-auto text-zinc-700 mb-3" size={40} />
          <p className="text-zinc-500">{t("wall.empty")}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {tips.map((tip, i) => (
            <TipCard key={tip.id} tip={tip} i={i} t={t} onRate={rate} myStars={myRatings[tip.id]} isAdmin={user?.role === "admin"} onSettle={settle} onDelete={del} canDelete={user?.role === "admin" || tip.user_id === user?.id} onUserClick={onUserClick} />
          ))}
        </div>
      )}
        </>
      )}
    </section>
  );
}

const STATUS_META = {
  won: { cls: "bg-won/15 text-won", text: "text-won", Icon: CheckCircle2, key: "wall.won" },
  lost: { cls: "bg-lost/15 text-lost", text: "text-lost", Icon: XCircle, key: "wall.lost" },
  live: { cls: "bg-live/15 text-live", text: "text-live", Icon: Radio, key: "wall.live" },
  pending: { cls: "bg-amber-500/15 text-amber-400", text: "text-amber-400", Icon: Clock, key: "wall.pending" },
};

function StatusBadge({ status, t }) {
  const s = STATUS_META[status] || STATUS_META.pending;
  const { Icon } = s;
  return (
    <span data-testid={`status-badge-${status || "pending"}`} className={`inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded ${s.cls}`}>
      <Icon size={11} className={status === "live" ? "animate-pulse" : ""} /> {t(s.key)}
    </span>
  );
}

const NATION_FLAGS = {
  portugal: "🇵🇹", spain: "🇪🇸", spanien: "🇪🇸", argentina: "🇦🇷", argentinien: "🇦🇷",
  brazil: "🇧🇷", brasilien: "🇧🇷", germany: "🇩🇪", deutschland: "🇩🇪", france: "🇫🇷", frankreich: "🇫🇷",
  england: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", italy: "🇮🇹", italien: "🇮🇹", netherlands: "🇳🇱", niederlande: "🇳🇱", holland: "🇳🇱",
  sweden: "🇸🇪", schweden: "🇸🇪", norway: "🇳🇴", norwegen: "🇳🇴", denmark: "🇩🇰", dänemark: "🇩🇰",
  belgium: "🇧🇪", belgien: "🇧🇪", croatia: "🇭🇷", kroatien: "🇭🇷", usa: "🇺🇸", mexico: "🇲🇽",
  greece: "🇬🇷", griechenland: "🇬🇷", turkey: "🇹🇷", türkei: "🇹🇷", poland: "🇵🇱", polen: "🇵🇱",
  austria: "🇦🇹", österreich: "🇦🇹", switzerland: "🇨🇭", schweiz: "🇨🇭", scotland: "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
};
const LEAGUE_FLAGS = {
  allsvenskan: "🇸🇪", "la liga": "🇪🇸", "premier league": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", bundesliga: "🇩🇪",
  "serie a": "🇮🇹", "ligue 1": "🇫🇷", eredivisie: "🇳🇱", "super league": "🇬🇷",
};
const GLOBAL_KEYS = ["world cup", "länderspiel", "laenderspiel", "international", "nations league", "friendly", " wm", " em", "euro", "champions league", "europa league"];

function tipFlags(tip) {
  const flags = new Set();
  const texts = [tip.country, tip.home_team, tip.away_team, tip.league];
  (tip.legs || []).forEach((l) => { texts.push(l.match, l.league); });
  const hay = " " + texts.filter(Boolean).join(" ").toLowerCase() + " ";
  Object.entries(NATION_FLAGS).forEach(([k, f]) => { if (hay.includes(k)) flags.add(f); });
  Object.entries(LEAGUE_FLAGS).forEach(([k, f]) => { if (hay.includes(k)) flags.add(f); });
  if (flags.size === 0 && GLOBAL_KEYS.some((k) => hay.includes(k))) flags.add("🌍");
  return [...flags].slice(0, 5);
}

function SmartLab({ t, user, onCreated }) {
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const send = async () => {
    if (!user) { toast.error(t("smart.chat.login")); return; }
    const v = text.trim();
    if (v.length < 6) return;
    setSending(true);
    try {
      const { data } = await api.post("/smart/idea", { text: v });
      setText("");
      if (data.created) { toast.success(t("smart.chat.created")); onCreated?.(); }
      else toast.success(t("smart.chat.stored"));
    } catch (e) {
      toast.error(t("smart.chat.error"));
    } finally {
      setSending(false);
    }
  };
  return (
    <div
      data-testid="smart-lab"
      className="mb-10 rounded-2xl border border-volt/25 bg-gradient-to-br from-surface to-void p-5 md:p-7 grid grid-cols-1 lg:grid-cols-[1.15fr_1fr] gap-6 lg:gap-8"
    >
      {/* LEFT — explanation, text pushed left */}
      <div className="text-left">
        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-volt">
          <Brain size={15} /> Smart Bets
        </span>
        <h3 className="font-heading text-2xl md:text-3xl font-black text-white tracking-tight mt-2">{t("smart.title")}</h3>
        <p className="text-zinc-400 text-sm md:text-base mt-3 leading-relaxed">{t("smart.intro")}</p>
      </div>

      {/* RIGHT — chatbox */}
      <div className="flex flex-col justify-center">
        <div className="flex items-center gap-2 mb-2 text-zinc-300">
          <Lightbulb size={16} className="text-volt" />
          <span className="text-sm font-semibold">{t("smart.chat.title")}</span>
        </div>
        <div className="rounded-2xl bg-white/95 border border-white/20 p-2.5 shadow-lg">
          <textarea
            data-testid="smart-idea-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send(); }}
            placeholder={t("smart.chat.placeholder")}
            rows={3}
            maxLength={600}
            className="w-full resize-none bg-transparent text-void placeholder:text-zinc-500 text-sm px-2 py-1.5 focus:outline-none"
          />
          <div className="flex items-center justify-between pl-2">
            <span className="text-[11px] text-zinc-500 font-mono">{text.length}/600</span>
            <button
              type="button"
              data-testid="smart-idea-send"
              onClick={send}
              disabled={sending || text.trim().length < 6}
              className="flex items-center gap-2 rounded-xl bg-volt text-void font-bold text-sm px-4 py-2 hover:brightness-110 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {sending ? <span className="animate-pulse">{t("smart.chat.sending")}</span> : (<><Send size={15} /> {t("smart.chat.send")}</>)}
            </button>
          </div>
        </div>
        {!user && <p className="text-xs text-zinc-500 mt-2">{t("smart.chat.login")}</p>}
      </div>
    </div>
  );
}

function TipCard({ tip, i, t, onRate, myStars, isAdmin, onSettle, onDelete, canDelete, onUserClick }) {
  const flags = tipFlags(tip);
  const [sharing, setSharing] = useState(false);
  const isShareable = ["pending", "live"].includes(tip.status) && !["hq-auto", "smart"].includes(tip.source);
  const doShare = async () => {
    setSharing(true);
    try {
      const { data } = await api.post(`/tips/${tip.id}/share-image`);
      await shareSlip({ imageUrl: fileUrl(data.path), username: tip.username, odds: tip.odds });
    } catch (e) {
      toast.error(t("wall.shareErr"));
    } finally {
      setSharing(false);
    }
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
      transition={{ delay: (i % 6) * 0.05 }}
      data-testid={`tip-card-${tip.id}`}
      className="rounded-xl bg-surface border border-elevated p-4 hover:-translate-y-1 hover:border-volt/50 transition-all flex flex-col"
    >
      <div className="flex items-center justify-between mb-3">
        <button
          type="button"
          onClick={() => onUserClick?.(tip.username)}
          data-testid={`gift-user-btn-${tip.id}`}
          title={t("wall.giftUser")}
          className="flex items-center gap-2 min-w-0 group"
        >
          <div className="w-7 h-7 rounded-full bg-elevated flex items-center justify-center text-xs font-bold text-white shrink-0 group-hover:bg-volt group-hover:text-void transition-colors">
            {tip.username?.[0]?.toUpperCase() || "?"}
          </div>
          <span className="text-sm text-zinc-400 truncate">{t("wall.by")} <span className="text-white font-semibold group-hover:text-volt underline decoration-dotted underline-offset-2 transition-colors">{tip.username}</span></span>
        </button>
        <div className="flex items-center gap-2 shrink-0">
          {isShareable && (
            <button
              onClick={doShare}
              disabled={sharing}
              data-testid={`share-tip-${tip.id}`}
              title={t("wall.share")}
              className="flex items-center gap-1 text-[11px] font-bold text-volt hover:text-volt-hover disabled:opacity-50 transition-colors"
            >
              <Share2 size={13} /> {t("wall.share")}
            </button>
          )}
          {flags.length > 0 && (
            <span className="text-base leading-none tracking-tight" data-testid="tip-flags">{flags.join(" ")}</span>
          )}
          {tip.final_home != null && tip.final_away != null && (
            <span className="text-[10px] font-mono font-bold text-white bg-void border border-elevated px-2 py-1 rounded" data-testid="final-score">
              {t("wall.final")} {tip.final_home}-{tip.final_away}
            </span>
          )}
          <StatusBadge status={tip.status} t={t} />
          {canDelete && (
            <button
              onClick={() => onDelete(tip)}
              data-testid="delete-tip-btn"
              title={t("wall.delete")}
              className="p-1.5 rounded-lg text-zinc-500 hover:text-lost hover:bg-lost/15 transition-colors"
            >
              <Trash2 size={15} />
            </button>
          )}
        </div>
      </div>

      {tip.live_state && (
        <div data-testid={`live-state-${tip.id}`} className="inline-flex items-center gap-2 bg-[#F0443C] text-white font-bold text-xs rounded-lg px-3 py-1.5 mb-2">
          <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
          LIVE{tip.live_state.minute ? `  ${tip.live_state.minute}'` : ""}{tip.live_state.score ? `   ·   ${tip.live_state.score}` : ""}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500 mb-2">
        {tip.league && <span>{tip.league}</span>}
        {tip.country && <span>· {tip.country}</span>}
        {tip.match_time && !(tip.legs && tip.legs.length) && <span>· {tip.match_time}</span>}
      </div>

      {tip.legs && tip.legs.length ? (
        <div className="space-y-2">
          {tip.is_parlay && (
            <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-volt bg-volt/10 border border-volt/30 rounded px-2 py-0.5">
              Parlay · {tip.legs.length} {tip.legs.length > 1 ? "Spiele" : "Spiel"}
            </span>
          )}
          {tip.legs.map((leg, li) => {
            const ls = STATUS_META[leg.status];
            const settled = ls && leg.status !== "pending";
            return (
            <div key={li} className={`rounded-lg bg-void border px-3 py-2.5 ${settled ? ls.cls.split(" ")[0].replace("/15", "/30") : "border-elevated"}`}>
              <div className="flex items-center justify-between gap-2">
                <span className={`font-heading font-bold text-sm leading-tight ${settled ? ls.text : "text-white"}`}>{leg.match || "—"}</span>
                <div className="flex items-center gap-2 shrink-0">
                  {ls && (
                    <span data-testid={`leg-status-${leg.status}`} className={`inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded ${ls.cls}`}>
                      <ls.Icon size={9} className={leg.status === "live" ? "animate-pulse" : ""} /> {t(ls.key)}
                    </span>
                  )}
                  {leg.kickoff && <span className="text-[10px] text-zinc-500 font-mono">{leg.kickoff}</span>}
                </div>
              </div>
              {leg.league && <span className="text-[10px] text-volt/80 font-semibold uppercase tracking-wider">{leg.league}</span>}
              <div className="flex flex-wrap gap-1.5 mt-2">
                {(leg.selections || []).map((s, si) => {
                  const od = (leg.sel_odds || [])[si];
                  return (
                  <span key={si} className="text-[11px] text-zinc-100 bg-elevated rounded px-2 py-1 leading-tight">
                    {formatSelection(s, t)}{od ? <span className="ml-1 font-mono font-bold text-volt">@{od}</span> : null}
                  </span>
                  );
                })}
              </div>
            </div>
          );})}
          {(tip.odds || tip.stake || tip.potential_return) && (
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-xs pt-1 px-1">
              {tip.odds && <span className="text-zinc-500">Quote <span className="font-mono font-bold text-volt">{tip.odds}</span></span>}
              {tip.stake && <span className="text-zinc-500">Einsatz <span className="text-white font-medium">{tip.stake}</span></span>}
              {tip.potential_return && <span className="text-zinc-500">Gewinn <span className="text-won font-medium">{tip.potential_return}</span></span>}
            </div>
          )}
        </div>
      ) : (
        <>
          <h4 className="font-heading font-bold text-white text-lg leading-tight">
            {tip.home_team || "—"} <span className="text-zinc-600 text-sm">vs</span> {tip.away_team || "—"}
          </h4>
          {tip.pick_type && (
            <div className="flex items-center gap-2 mt-1.5" data-testid={`pick-type-${tip.pick_type}`}>
              <span className={`text-[10px] font-black uppercase tracking-widest rounded px-2 py-0.5 ${tip.pick_type === "value" ? "bg-volt/15 text-volt" : "bg-cyan-400/15 text-cyan-300"}`}>
                {tip.pick_type === "value" ? "VALUE" : "BANKER"}
              </span>
              {tip.win_prob != null && (
                <span className="text-[11px] text-zinc-400 font-mono">≈{Math.round(tip.win_prob * 100)}%</span>
              )}
            </div>
          )}
          <div className="flex items-center justify-between rounded-lg bg-void px-3 py-2 mt-3">
            <span className="text-white font-semibold text-sm truncate">{formatSelection(tip.market, t) || "—"}</span>
            {tip.odds && <OddsValue odds={tip.odds} className="font-mono font-bold text-volt shrink-0 ml-2" />}
          </div>
          {(tip.stake || tip.potential_return) && (
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-xs pt-2 px-1">
              {tip.stake && <span className="text-zinc-500">Einsatz <span className="text-white font-medium">{tip.stake}</span></span>}
              {tip.potential_return && <span className="text-zinc-500">Gewinn <span className="text-won font-medium">{tip.potential_return}</span></span>}
            </div>
          )}
        </>
      )}

      {tip.ai_analysis && (
        <p className="text-xs text-zinc-400 mt-2 border-l-2 border-volt pl-2 leading-snug">
          <span className="text-volt font-semibold">{t("wall.aisays")}:</span> {tip.ai_analysis}
        </p>
      )}

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-elevated">
        <div className="text-center">
          <p className="text-[9px] uppercase tracking-widest text-zinc-500">{t("wall.aisays")}</p>
          <p className="font-mono font-black text-lg text-volt">{tip.ai_rating}</p>
        </div>
        <div className="text-center">
          <p className="text-[9px] uppercase tracking-widest text-zinc-500">{t("wall.community")}</p>
          <p className="font-mono font-black text-lg text-white">{tip.avg_rating || "—"} <span className="text-[10px] text-zinc-500">({tip.ratings_count})</span></p>
        </div>
      </div>

      <div className="mt-3">
        <p className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1.5">{myStars ? t("wall.your") + `: ${myStars}` : t("wall.apex")}</p>
        <StarRating value={myStars || 0} onRate={(s) => onRate(tip, s)} size={20} />
      </div>

      {isAdmin && tip.status === "pending" && (
        <div className="flex gap-2 mt-3" data-testid={`admin-settle-${tip.id}`}>
          <button onClick={() => onSettle(tip, "won")} className="flex-1 text-xs font-bold py-1.5 rounded-lg bg-won/15 text-won hover:bg-won/25 transition-colors">{t("wall.won")}</button>
          <button onClick={() => onSettle(tip, "lost")} className="flex-1 text-xs font-bold py-1.5 rounded-lg bg-lost/15 text-lost hover:bg-lost/25 transition-colors">{t("wall.lost")}</button>
        </div>
      )}
      {isAdmin && !["hq-auto", "smart"].includes(tip.source) && (tip.status === "pending" || tip.status === "live") && (
        <button
          onClick={() => onSettle(tip, tip.status === "live" ? "pending" : "live")}
          data-testid={`admin-tolive-${tip.id}`}
          className="w-full text-xs font-bold py-1.5 mt-2 rounded-lg bg-live/15 text-live hover:bg-live/25 transition-colors"
        >
          {tip.status === "live" ? t("wall.toPending") : t("wall.toLive")}
        </button>
      )}
    </motion.div>
  );
}
