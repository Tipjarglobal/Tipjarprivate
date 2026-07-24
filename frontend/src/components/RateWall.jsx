import React, { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import confetti from "canvas-confetti";
import { Flame, Users, Trophy, Zap, RefreshCw, CheckCircle2, XCircle, Radio, Clock, Trash2, Share2, Brain, Send, Lightbulb, ImagePlus, Banknote, MessageCircle, Search, Star, Ticket, ShieldCheck, Ban } from "lucide-react";
import StarRating from "./StarRating";
import AiRatingStars from "./AiRatingStars";
import { Systems } from "./Systems";
import { QualifierBriefing } from "./QualifierBriefing";
import { OddsValue } from "./OddsValue";
import api, { apiErr, fileUrl } from "../api";
import { shareSlip } from "../shareSlip";
import { PlaySlipOverlay } from "./PlaySlipOverlay";
import { useI18n, localizeMarket, localizeProse, formatSelection, toLatin, displayTeam, formatKickoff, kickoffTs, kickoffInfo, isKickoffLive } from "../i18n";
import { useAuth } from "../auth";
import { toast } from "sonner";

const FILTERS = [
  { k: "new", label: "wall.filter.new" },
  { k: "hype", label: "wall.filter.hype" },
  { k: "top", label: "wall.filter.top" },
];
// Live sub-categories — the KI posts all of these automatically (nothing is manual).
const LIVE_CATS = [
  ["banker", "Banker", "bg-cyan-400 text-void border-cyan-400", "text-cyan-300 border-cyan-400/40"],
  ["value", "Value", "bg-volt text-void border-volt", "text-volt border-volt/40"],
  ["banger", "Banger", "bg-orange-500 text-void border-orange-500", "text-orange-400 border-orange-500/40"],
  ["community", "Community", "bg-blue-500 text-white border-blue-500", "text-blue-300 border-blue-500/40"],
];
const LIVE_CAT_KEYS = {
  all: ["livecat.all.t", "livecat.all.d"],
  banker: ["livecat.banker.t", "livecat.banker.d"],
  value: ["livecat.value.t", "livecat.value.d"],
  banger: ["livecat.banger.t", "livecat.banger.d"],
  community: ["livecat.community.t", "livecat.community.d"],
};
const SMART_IDEA_STATUS = {
  pending: { label: "in Prüfung", cls: "bg-amber-500/15 text-amber-400" },
  used: { label: "als Pick veröffentlicht", cls: "bg-[#2ECC57]/15 text-[#2ECC57]" },
  not_actionable: { label: "kein Tipp", cls: "bg-zinc-500/15 text-zinc-400" },
  no_fixture: { label: "kein Spiel gefunden", cls: "bg-zinc-500/15 text-zinc-400" },
  too_far: { label: "zu weit weg", cls: "bg-sky-400/15 text-sky-400" },
};
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
  const [cat, setCat] = useState(null);
  const [liveCat, setLiveCat] = useState(null);
  const [liveCounts, setLiveCounts] = useState({ banker: 0, value: 0, banger: 0, community: 0 });
  const [myRatings, setMyRatings] = useState({});
  const [playData, setPlayData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [streakBubble, setStreakBubble] = useState(false);
  const [wonTips, setWonTips] = useState([]);
  const [lostTips, setLostTips] = useState([]);
  const [cashedTips, setCashedTips] = useState([]);
  const [bestwonTips, setBestwonTips] = useState([]);
  const [voidTips, setVoidTips] = useState([]);
  const [settledCounts, setSettledCounts] = useState({ won: 0, lost: 0, cashed: 0, bestwon: 0, void: 0 });
  const [settledTab, setSettledTab] = useState(null);

  useEffect(() => {
    setStatus(view === "live" ? "live" : "pending");
    setLiveCat(null);
  }, [view]);

  const load = useCallback(async (silent) => {
    if (view === "settled") return;
    if (!silent) setLoading(true);
    try {
      const params = { sort };
      const st = view === "live" ? "live" : status;
      if (st) params.status = st;
      if (view === "ai") { params.source = "ai"; if (win !== "all") params.window = win; if (cat) params.category = cat; }
      else if (view === "live") { if (liveCat === "community") { params.source = "members"; } else if (liveCat) params.category = liveCat; }
      else if (view === "members") params.source = "members";
      else if (view === "smart") params.source = "smart";
      const { data } = await api.get("/tips", { params });
      setTips(data);
    } catch { /* ignore */ } finally { if (!silent) setLoading(false); }
  }, [sort, status, view, win, cat, liveCat]);

  useEffect(() => {
    load();
    const iv = setInterval(() => load(true), 20000);
    return () => clearInterval(iv);
  }, [load, refreshKey]);

  // ── Per-category unread badges (Banker / Value / Risk) ──────────────────
  // Every AI single lands in exactly one bucket (risk = -1.5 handicaps, banker,
  // else value). A red count sits on a tab until the user opens that category.
  const CAT_SEEN_KEY = "tj_cat_seen_ids";
  const catIdsRef = useRef({ banker: [], value: [], risk: [] });
  const [catUnread, setCatUnread] = useState({ banker: 0, value: 0, risk: 0 });
  const getCatSeen = () => {
    try { return JSON.parse(localStorage.getItem(CAT_SEEN_KEY) || "{}"); } catch { return {}; }
  };
  const bucketOf = (tp) => (tp.category === "risk" ? "risk" : tp.category === "banker" ? "banker" : "value");
  const loadCatBadges = useCallback(async () => {
    if (view !== "ai") return;
    try {
      const { data } = await api.get("/tips", { params: { source: "ai", status: "pending", limit: 300 } });
      const seen = getCatSeen();
      const counts = { banker: 0, value: 0, risk: 0 };
      const byCat = { banker: [], value: [], risk: [] };
      data.forEach((tp) => {
        const c = bucketOf(tp);
        byCat[c].push(tp.id);
        if (!(seen[c] || []).includes(tp.id)) counts[c] += 1;
      });
      catIdsRef.current = byCat;
      setCatUnread(counts);
    } catch { /* ignore */ }
  }, [view]);
  useEffect(() => {
    if (view !== "ai") return;
    loadCatBadges();
    const iv = setInterval(loadCatBadges, 20000);
    const onSeen = () => loadCatBadges();
    window.addEventListener("tj-cat-seen", onSeen);
    return () => { clearInterval(iv); window.removeEventListener("tj-cat-seen", onSeen); };
  }, [loadCatBadges, refreshKey]);
  const markCatSeen = (c) => {
    const seen = getCatSeen();
    seen[c] = catIdsRef.current[c] || [];
    localStorage.setItem(CAT_SEEN_KEY, JSON.stringify(seen));
    setCatUnread((u) => ({ ...u, [c]: 0 }));
    window.dispatchEvent(new Event("tj-cat-seen"));
  };

  const loadSettled = useCallback(async () => {
    try {
      const [w, l, c, bw, v, counts] = await Promise.all([
        api.get("/tips", { params: { status: "won", source: "normalwon", sort: "new", limit: 1000 } }),
        api.get("/tips", { params: { status: "lost", sort: "new", limit: 1000 } }),
        api.get("/tips", { params: { status: "cashed_out", sort: "new", limit: 1000 } }),
        api.get("/tips", { params: { status: "won", source: "bestwon", sort: "new", limit: 1000 } }),
        api.get("/tips", { params: { status: "void", sort: "new", limit: 1000 } }),
        api.get("/tips/counts"),
      ]);
      setWonTips(w.data); setLostTips(l.data); setCashedTips(c.data); setBestwonTips(bw.data); setVoidTips(v.data);
      setSettledCounts({
        won: counts.data.won_normal ?? w.data.length,
        lost: counts.data.lost ?? l.data.length,
        cashed: counts.data.cashed ?? c.data.length,
        bestwon: counts.data.bestwon ?? bw.data.length,
        void: counts.data.void ?? v.data.length,
      });
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    if (view !== "settled") return;
    loadSettled();
    const iv = setInterval(loadSettled, 20000);
    return () => clearInterval(iv);
  }, [view, refreshKey, loadSettled]);

  // ── Live sub-tab counts (Banker / Value / Banger) — the KI posts all of these ──
  const loadLiveCounts = useCallback(async () => {
    if (view !== "live") return;
    try {
      const { data } = await api.get("/tips", { params: { status: "live", limit: 200 } });
      const HQ = ["hq-auto", "hq-live", "hq-system", "smart"];
      const c = { banker: 0, value: 0, banger: 0, community: 0 };
      data.forEach((tp) => {
        if (!HQ.includes(tp.source)) { c.community += 1; return; }
        const b = tp.category === "banker" ? "banker" : tp.category === "banger" ? "banger" : "value";
        c[b] += 1;
      });
      setLiveCounts(c);
    } catch { /* ignore */ }
  }, [view]);
  useEffect(() => {
    if (view !== "live") return;
    loadLiveCounts();
    const iv = setInterval(loadLiveCounts, 20000);
    return () => clearInterval(iv);
  }, [view, refreshKey, loadLiveCounts]);

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
      if (view === "settled") loadSettled();
      toast.success(t(`wall.${s === "cashed_out" ? "cashed" : s}`) || "OK");
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
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            <button
              type="button"
              data-testid="settled-won-toggle"
              onClick={() => setSettledTab((v) => (v === "won" ? null : "won"))}
              className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-4 font-heading font-black text-base transition-all ${
                settledTab === "won"
                  ? "bg-won text-void border-won shadow-[0_0_18px_rgba(46,204,87,0.45)]"
                  : "bg-won/10 border-won/40 text-won hover:bg-won/20"
              }`}
            >
              <CheckCircle2 size={20} /> {t("wall.filter.won")}
              <span className={`text-xs font-mono rounded-full px-1.5 ${settledTab === "won" ? "bg-black/20" : "bg-void/60"}`}>{settledCounts.won}</span>
            </button>
            <button
              type="button"
              data-testid="settled-lost-toggle"
              onClick={() => setSettledTab((v) => (v === "lost" ? null : "lost"))}
              className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-4 font-heading font-black text-base transition-all ${
                settledTab === "lost"
                  ? "bg-lost text-white border-lost shadow-[0_0_18px_rgba(239,68,68,0.45)]"
                  : "bg-lost/10 border-lost/40 text-lost hover:bg-lost/20"
              }`}
            >
              <XCircle size={20} /> {t("wall.filter.lost")}
              <span className={`text-xs font-mono rounded-full px-1.5 ${settledTab === "lost" ? "bg-black/20" : "bg-void/60"}`}>{settledCounts.lost}</span>
            </button>
            <button
              type="button"
              data-testid="settled-special-toggle"
              onClick={() => setSettledTab((v) => (v === "special" ? null : "special"))}
              className="relative rounded-xl overflow-hidden min-h-[68px] self-stretch group"
            >
              {/* colour fills only (clipped) — labels sit on top, un-clipped, so both words stay fully readable */}
              <span
                aria-hidden
                style={{ clipPath: "polygon(0 0, 100% 0, 100% 100%)" }}
                className={`pointer-events-none absolute inset-0 transition-colors ${
                  settledTab === "special" ? "bg-amber-400" : "bg-amber-400/15 group-hover:bg-amber-400/25"
                }`}
              />
              <span
                aria-hidden
                style={{ clipPath: "polygon(0 0, 100% 100%, 0 100%)" }}
                className={`pointer-events-none absolute inset-0 transition-colors ${
                  settledTab === "special" ? "bg-sky-400" : "bg-sky-400/15 group-hover:bg-sky-400/25"
                }`}
              />
              {/* diagonal divider */}
              <span aria-hidden className="pointer-events-none absolute inset-0" style={{ background: "linear-gradient(to bottom right, transparent calc(50% - 0.5px), rgba(255,255,255,0.28) 50%, transparent calc(50% + 0.5px))" }} />
              {/* Best Won label — top-right */}
              <span className={`pointer-events-none absolute top-1.5 right-1.5 sm:right-2 flex items-center gap-0.5 sm:gap-1 font-heading font-black text-[9px] sm:text-xs whitespace-nowrap transition-colors ${
                settledTab === "special" ? "text-void" : "text-amber-300"
              }`}>
                <Trophy className="w-3 h-3 sm:w-3.5 sm:h-3.5 shrink-0" /> Best Won
                <span className={`text-[9px] sm:text-[10px] font-mono rounded-full px-1 ${settledTab === "special" ? "bg-black/20" : "bg-void/60"}`}>{settledCounts.bestwon}</span>
              </span>
              {/* Cashed Out label — bottom-left */}
              <span className={`pointer-events-none absolute bottom-1.5 left-1.5 sm:left-2 flex items-center gap-0.5 sm:gap-1 font-heading font-black text-[9px] sm:text-xs whitespace-nowrap transition-colors ${
                settledTab === "special" ? "text-void" : "text-sky-300"
              }`}>
                <Banknote className="w-3 h-3 sm:w-3.5 sm:h-3.5 shrink-0" /> {t("wall.cashed")}
                <span className={`text-[9px] sm:text-[10px] font-mono rounded-full px-1 ${settledTab === "special" ? "bg-black/20" : "bg-void/60"}`}>{settledCounts.cashed}</span>
              </span>
            </button>
            <button
              type="button"
              data-testid="settled-void-toggle"
              onClick={() => setSettledTab((v) => (v === "void" ? null : "void"))}
              className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-4 font-heading font-black text-base transition-all ${
                settledTab === "void"
                  ? "bg-zinc-400 text-void border-zinc-400 shadow-[0_0_18px_rgba(161,161,170,0.4)]"
                  : "bg-zinc-500/10 border-zinc-500/40 text-zinc-300 hover:bg-zinc-500/20"
              }`}
            >
              <Ban size={20} /> Annulliert
              <span className={`text-xs font-mono rounded-full px-1.5 ${settledTab === "void" ? "bg-black/20" : "bg-void/60"}`}>{settledCounts.void}</span>
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
                    <TipCard key={tip.id} tip={tip} i={i} t={t} onRate={rate} myStars={myRatings[tip.id]} isAdmin={user?.role === "admin"} onSettle={settle} onDelete={del} canDelete={user?.role === "admin" || tip.user_id === user?.id} onUserClick={onUserClick} onPlay={setPlayData} />
                  ))}
            </div>
          )}

          {settledTab === "lost" && (
            <div data-testid="settled-lost-col" className="space-y-5">
              {lostTips.length === 0
                ? <p className="text-zinc-600 text-sm py-8 text-center rounded-xl border border-dashed border-elevated">{t("settled.empty.lost")}</p>
                : lostTips.map((tip, i) => (
                    <TipCard key={tip.id} tip={tip} i={i} t={t} onRate={rate} myStars={myRatings[tip.id]} isAdmin={user?.role === "admin"} onSettle={settle} onDelete={del} canDelete={user?.role === "admin" || tip.user_id === user?.id} onUserClick={onUserClick} onPlay={setPlayData} />
                  ))}
            </div>
          )}

          {settledTab === "special" && (
            <div data-testid="settled-special-col" className="space-y-5">
              <p className="text-sm mb-1 flex items-center gap-2">
                <Trophy size={15} className="text-amber-300" />
                <span className="text-amber-300">Best Won</span>
                <span className="text-zinc-500">·</span>
                <Banknote size={15} className="text-sky-300" />
                <span className="text-sky-300">Cashed Out</span>
                <span className="text-zinc-500 text-xs">— gewonnene Smart-, Risk-, Community- & System-Picks + Cash-Outs</span>
              </p>
              {(bestwonTips.length + cashedTips.length) === 0
                ? <p className="text-zinc-600 text-sm py-8 text-center rounded-xl border border-dashed border-elevated">Noch nichts hier — sobald ein Smart/Risk/Community/System-Pick gewinnt (oder ein Schein ausgezahlt wird), erscheint er hier.</p>
                : [...bestwonTips, ...cashedTips].map((tip, i) => (
                    <TipCard key={tip.id} tip={tip} i={i} t={t} onRate={rate} myStars={myRatings[tip.id]} isAdmin={user?.role === "admin"} onSettle={settle} onDelete={del} canDelete={user?.role === "admin" || tip.user_id === user?.id} onUserClick={onUserClick} onPlay={setPlayData} />
                  ))}
            </div>
          )}

          {settledTab === "void" && (
            <div data-testid="settled-void-col" className="space-y-5">
              <p className="text-sm mb-1 flex items-center gap-2">
                <Ban size={15} className="text-zinc-400" />
                <span className="text-zinc-300">Annulliert</span>
                <span className="text-zinc-500 text-xs">— Spiel vorbei, aber nicht automatisch bewertbar (Einsatz gilt als zurück)</span>
              </p>
              {voidTips.length === 0
                ? <p className="text-zinc-600 text-sm py-8 text-center rounded-xl border border-dashed border-elevated">Nichts annulliert — alle abgeschlossenen Picks konnten bewertet werden. 👍</p>
                : voidTips.map((tip, i) => (
                    <TipCard key={tip.id} tip={tip} i={i} t={t} onRate={rate} myStars={myRatings[tip.id]} isAdmin={user?.role === "admin"} onSettle={settle} onDelete={del} canDelete={user?.role === "admin" || tip.user_id === user?.id} onUserClick={onUserClick} onPlay={setPlayData} />
                  ))}
            </div>
          )}
        </div>
      )}

      {/* Systeme der Woche (Lock Bet / Value / Risk / Gamble) */}
      {view === "systems" && <Systems />}

      {view !== "systems" && view !== "settled" && (
        <>
      {view === "smart" && <QualifierBriefing t={t} />}
      {view === "smart" && <SmartLab t={t} user={user} onCreated={() => load(true)} />}
      {view === "members" && <MemberSearch onUserClick={onUserClick} t={t} />}
      {/* filters — hidden entirely in Smart; no "live" toggle anywhere (dedicated Live tab exists) */}
      {view !== "smart" && (
      <div className="flex flex-wrap gap-2 mb-6">
        {view === "ai" ? (
          [["banker", "Banker", "bg-[#2ECC57] text-void border-[#2ECC57]", "text-[#2ECC57] border-[#2ECC57]/40"],
           ["value", "Value", "bg-volt text-void border-volt", "text-volt border-volt/40"],
           ["risk", "Risk", "bg-orange-500 text-void border-orange-500", "text-orange-400 border-orange-500/40"],
           ["mental", "🤯 Mental", "bg-fuchsia-600 text-white border-fuchsia-600", "text-fuchsia-400 border-fuchsia-500/40"]].map(([v, lbl, on, off]) => (
            <button key={v} data-testid={`cat-${v}`}
              onClick={() => { markCatSeen(v); setCat((c) => (c === v ? null : v)); }}
              className={`relative px-5 py-2 rounded-full text-sm font-heading font-black uppercase tracking-wide border transition-all ${cat === v ? on : `bg-surface ${off} hover:text-white`}`}>
              {lbl}
              {catUnread[v] > 0 && (
                <span data-testid={`cat-badge-${v}`}
                  className="absolute -top-2 -right-2 min-w-[20px] h-5 px-1 flex items-center justify-center rounded-full bg-red-600 text-white text-[11px] font-bold leading-none shadow-lg ring-2 ring-void animate-pulse">
                  {catUnread[v] > 99 ? "99+" : catUnread[v]}
                </span>
              )}
            </button>
          ))
        ) : view === "live" ? (
          LIVE_CATS.map(([v, lbl, on, off]) => (
            <button key={v} data-testid={`live-cat-${v}`}
              onClick={() => setLiveCat((c) => (c === v ? null : v))}
              className={`relative px-5 py-2 rounded-full text-sm font-heading font-black uppercase tracking-wide border transition-all ${liveCat === v ? on : `bg-surface ${off} hover:text-white`}`}>
              {lbl}
              <span className={`ml-2 text-[11px] font-mono rounded-full px-1.5 ${liveCat === v ? "bg-black/25" : "bg-void/60"}`}>{liveCounts[v] || 0}</span>
            </button>
          ))
        ) : (
          <>
            {FILTERS.map((f) => (
              <button key={f.k} data-testid={`sort-${f.k}`} onClick={() => setSort(f.k)}
                className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors ${sort === f.k ? "bg-volt text-void" : "bg-surface border border-elevated text-zinc-400 hover:text-white"}`}>
                {t(f.label)}
              </button>
            ))}
          </>
        )}
      </div>
      )}

      {/* Live category explainer — every Banker/Value/Banger pick is posted automatically by the KI */}
      {view === "live" && (
        <div data-testid="live-cat-explain" className="mb-6 rounded-xl border border-live/25 bg-live/5 px-4 py-3">
          <p className="text-sm text-zinc-300 leading-snug">
            <span className="font-heading font-black text-live">{t(LIVE_CAT_KEYS[liveCat || "all"][0])}</span>
            {" — "}{t(LIVE_CAT_KEYS[liveCat || "all"][1])}
          </p>
        </div>
      )}

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
          {[...tips].sort((a, b) => kickoffTs(a) - kickoffTs(b)).map((tip, i) => (
            <TipCard key={tip.id} tip={tip} i={i} t={t} onRate={rate} myStars={myRatings[tip.id]} isAdmin={user?.role === "admin"} onSettle={settle} onDelete={del} canDelete={user?.role === "admin" || tip.user_id === user?.id} onUserClick={onUserClick} onPlay={setPlayData} />
          ))}
        </div>
      )}
        </>
      )}
      <PlaySlipOverlay data={playData} onClose={() => setPlayData(null)} />
    </section>
  );
}

const STATUS_META = {
  won: { cls: "bg-won/15 text-won", text: "text-won", Icon: CheckCircle2, key: "wall.won" },
  lost: { cls: "bg-lost/15 text-lost", text: "text-lost", Icon: XCircle, key: "wall.lost" },
  live: { cls: "bg-live/15 text-live", text: "text-live", Icon: Radio, key: "wall.live" },
  pending: { cls: "bg-amber-500/15 text-amber-400", text: "text-amber-400", Icon: Clock, key: "wall.pending" },
  cashed_out: { cls: "bg-sky-400/15 text-sky-400", text: "text-sky-400", Icon: Banknote, key: "wall.cashed" },
  void: { cls: "bg-zinc-500/15 text-zinc-400", text: "text-zinc-400", Icon: Ban, key: "wall.void" },
};

function StatusBadge({ status, t, report }) {
  if (report) {
    return (
      <span data-testid="status-badge-report" className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded bg-indigo-500/15 text-indigo-300">
        <Brain size={11} /> Analyse
      </span>
    );
  }
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
  const [images, setImages] = useState([]);
  const [sending, setSending] = useState(false);
  const fileRef = useRef(null);
  const addImages = (e) => {
    const picked = Array.from(e.target.files || []);
    setImages((prev) => [...prev, ...picked].slice(0, 3));
    if (fileRef.current) fileRef.current.value = "";
  };
  const removeImage = (idx) => setImages((prev) => prev.filter((_, i) => i !== idx));
  const send = async () => {
    if (!user) { toast.error(t("smart.chat.login")); return; }
    const v = text.trim();
    if (v.length < 6 && images.length === 0) return;
    setSending(true);
    try {
      const fd = new FormData();
      fd.append("text", v);
      images.forEach((img) => fd.append("files", img));
      const { data } = await api.post("/smart/idea", fd);
      setText(""); setImages([]);
      if (data.created) { toast.success(t("smart.chat.created")); onCreated?.(); }
      else { toast.success(t("smart.chat.stored")); }
    } catch (e) {
      // Owner: never show a blank/error reply — the KI always gives something. On a hiccup,
      // stay friendly and invite a retry instead of a bare error message.
      toast.success(t("smart.chat.stored"));
    } finally {
      setSending(false);
    }
  };
  return (
    <>
    <div
      data-testid="smart-lab"
      className="mb-10 rounded-2xl border border-volt/25 bg-gradient-to-br from-surface to-void p-5 md:p-7 grid grid-cols-1 lg:grid-cols-[1.15fr_1fr] gap-6 lg:gap-8"
    >
      {/* LEFT — explanation, text pushed left */}
      <div className="text-left">
        <span className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-volt">
          <Brain size={15} /> Smart Picks
        </span>
        <h3 className="font-heading text-2xl md:text-3xl font-black text-white tracking-tight mt-2">{t("smart.title")}</h3>
        <p className="text-zinc-400 text-sm md:text-base mt-3 leading-relaxed">{t("smart.intro")}</p>
      </div>

      {/* RIGHT — chatbox with optional image upload */}
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
          {images.length > 0 && (
            <div className="flex gap-2 px-2 pb-1 flex-wrap" data-testid="smart-idea-thumbs">
              {images.map((img, idx) => (
                <div key={idx} className="relative w-14 h-14 rounded-lg overflow-hidden border border-zinc-300">
                  <img src={URL.createObjectURL(img)} alt="" className="w-full h-full object-cover" />
                  <button type="button" onClick={() => removeImage(idx)}
                    className="absolute top-0 right-0 bg-lost text-white w-4 h-4 flex items-center justify-center text-[10px] leading-none">×</button>
                </div>
              ))}
            </div>
          )}
          <div className="flex items-center justify-between pl-2">
            <div className="flex items-center gap-3">
              <button
                type="button"
                data-testid="smart-idea-attach"
                onClick={() => fileRef.current?.click()}
                disabled={images.length >= 3}
                title={t("smart.chat.attach")}
                className="flex items-center gap-1 text-zinc-500 hover:text-void text-xs font-semibold disabled:opacity-40"
              >
                <ImagePlus size={16} /> {images.length}/3
              </button>
              <input ref={fileRef} type="file" accept="image/*" multiple onChange={addImages} className="hidden" data-testid="smart-idea-file" />
              <span className="text-[11px] text-zinc-500 font-mono">{text.length}/600</span>
            </div>
            <button
              type="button"
              data-testid="smart-idea-send"
              onClick={send}
              disabled={sending || (text.trim().length < 6 && images.length === 0)}
              className="flex items-center gap-2 rounded-xl bg-volt text-void font-bold text-sm px-4 py-2 hover:brightness-110 active:scale-95 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {sending ? <span className="animate-pulse">{t("smart.chat.sending")}</span> : (<><Send size={15} /> {t("smart.chat.send")}</>)}
            </button>
          </div>
        </div>
        {!user && <p className="text-xs text-zinc-500 mt-2">{t("smart.chat.login")}</p>}
      </div>
      </div>

    </>
  );
}

function MemberSearch({ onUserClick, t }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [games, setGames] = useState([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (q.trim().length < 2) { setResults([]); setGames([]); return; }
    setLoading(true);
    const id = setTimeout(async () => {
      try {
        const { data } = await api.get(`/users/search?q=${encodeURIComponent(q.trim())}`);
        setResults(data.results || []);
        setGames(data.games || []);
      } catch { setResults([]); setGames([]); }
      finally { setLoading(false); }
    }, 300);
    return () => clearTimeout(id);
  }, [q]);
  const gameArea = (tp) => tp.status === "live" ? "live"
    : (tp.source === "hq-auto" ? "ai"
      : (tp.source === "smart" ? "smart"
        : (tp.source === "hq-system" ? "systems" : "members")));
  const openGame = (tp) => window.dispatchEvent(
    new CustomEvent("tj-open-pick", { detail: { area: gameArea(tp), id: tp.id } }));
  const empty = q.trim().length >= 2 && !loading && results.length === 0 && games.length === 0;
  return (
    <div className="mb-6" data-testid="member-search">
      <div className="relative">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
        <input
          data-testid="member-search-input"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={t("wall.searchMembers")}
          className="w-full rounded-full bg-surface border border-elevated pl-10 pr-4 py-3 text-sm text-white placeholder:text-zinc-500 focus:border-volt/60 focus:outline-none transition-colors"
        />
      </div>
      {q.trim().length >= 2 && (
        <div className="mt-2 rounded-xl bg-surface border border-elevated overflow-hidden" data-testid="member-search-results">
          {loading && <p className="px-4 py-3 text-sm text-zinc-500">{t("wall.searching")}</p>}
          {empty && <p className="px-4 py-3 text-sm text-zinc-500" data-testid="member-search-empty">{t("wall.noMembers")}</p>}
          {games.length > 0 && (
            <div className="border-b border-elevated">
              <p className="px-4 pt-2.5 pb-1 text-[10px] uppercase tracking-widest text-volt/80 font-bold">{t("wall.gamesLabel")}</p>
              {games.map((g) => (
                <button
                  key={g.id}
                  type="button"
                  data-testid={`game-result-${g.id}`}
                  onClick={() => openGame(g)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-elevated transition-colors"
                >
                  {g.status === "live"
                    ? <span className="w-2 h-2 rounded-full bg-live animate-pulse shrink-0" />
                    : <span className="w-2 h-2 rounded-full bg-zinc-600 shrink-0" />}
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-white font-semibold truncate">
                      {displayTeam(g.home_team, g.home_team_latin)}{g.away_team ? ` vs ${displayTeam(g.away_team, g.away_team_latin)}` : ""}
                    </p>
                    <p className="text-[11px] text-zinc-500 truncate">{toLatin(g.league)}{g.status === "live" ? " · LIVE" : ""}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
          {results.length > 0 && (
            <div>
              <p className="px-4 pt-2.5 pb-1 text-[10px] uppercase tracking-widest text-zinc-500 font-bold">{t("wall.membersLabel")}</p>
              {results.map((m) => (
                <button
                  key={m.username}
                  type="button"
                  data-testid={`member-result-${m.username}`}
                  onClick={() => onUserClick?.(m.username)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-elevated transition-colors"
                >
                  <div className="w-8 h-8 rounded-full bg-elevated flex items-center justify-center text-xs font-bold text-white shrink-0">
                    {toLatin(m.username)?.[0]?.toUpperCase() || "?"}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-white font-semibold truncate">{toLatin(m.username)}{m.apex_flame ? " 🔥" : ""}</p>
                    <p className="text-[11px] text-zinc-500">{m.tips_count} {t("wall.tipsLabel")} · {m.received_credits} Credits</p>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function TipCard({ tip, i, t, onRate, myStars, isAdmin, onSettle, onDelete, canDelete, onUserClick, onPlay }) {
  const { lang } = useI18n();
  const flags = tipFlags(tip);
  const [sharing, setSharing] = useState(false);
  const isShareable = ["pending", "live"].includes(tip.status) && !["hq-auto", "smart"].includes(tip.source);
  const warmedPath = useRef(null);
  const warming = useRef(false);
  // Pre-generate the share image as soon as the slip is on screen, so the tap→share is
  // instant (cached). Big 15-leg slips take up to ~20s to render+upload — without this the
  // tap's user-activation expires and navigator.share() is blocked ("wird nicht geteilt").
  const warmShare = useCallback(async () => {
    if (!isShareable || warmedPath.current || warming.current) return;
    warming.current = true;
    try {
      const { data } = await api.post(`/tips/${tip.id}/share-image`);
      warmedPath.current = data.path;
    } catch { /* keep sharing possible via the slow path on tap */ }
    finally { warming.current = false; }
  }, [isShareable, tip.id]);
  const doShare = async () => {
    if (sharing) return;
    setSharing(true);
    try {
      let path = warmedPath.current;
      if (!path) {
        const { data } = await api.post(`/tips/${tip.id}/share-image`);
        path = data.path;
        warmedPath.current = path;
      }
      await shareSlip({ imageUrl: fileUrl(path), username: tip.username, odds: tip.odds });
    } catch (e) {
      toast.error(t("wall.shareErr"));
    } finally {
      setSharing(false);
    }
  };
  const isMemberPick = !["hq-auto", "hq-system", "hq-live", "smart"].includes(tip.source);
  const isExpert = !!tip.is_expert;
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
      onViewportEnter={warmShare}
      transition={{ delay: (i % 6) * 0.05 }}
      id={`pick-${tip.id}`}
      data-testid={`tip-card-${tip.id}`}
      className={`rounded-xl border p-4 hover:-translate-y-1 transition-all flex flex-col scroll-mt-24 ${
        isExpert
          ? "bg-[#2a1a08] border-orange-500/45 hover:border-orange-400/80 shadow-[0_0_18px_rgba(249,115,22,0.18)]"
          : isMemberPick
          ? "bg-[#1b1030] border-purple-500/25 hover:border-purple-400/70"
          : "bg-surface border-elevated hover:border-volt/50"
      }`}
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
          <span className="text-sm text-zinc-400 truncate">{t("wall.by")} <span className="text-white font-semibold group-hover:text-volt underline decoration-dotted underline-offset-2 transition-colors">{toLatin(tip.username)}</span></span>
        </button>
        <div className="flex items-center gap-2 shrink-0">
          {isExpert && (
            <span data-testid="expert-badge" className="inline-flex items-center gap-1 text-[9px] font-black uppercase tracking-widest px-2 py-1 rounded bg-orange-500/20 text-orange-400 border border-orange-500/40">
              <Star size={10} /> Experte
            </span>
          )}
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
          <StatusBadge status={tip.status} t={t} report={tip.report} />
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

      {(() => {
        const liveState = tip.live_state
          || ((tip.live_minute != null || tip.live_score)
            ? { minute: tip.live_minute, score: tip.live_score }
            : null);
        if (!liveState) return null;
        // Guard a STUCK live badge: if kickoff was clearly long ago (>2.5h) the match is over,
        // so never show LIVE even if the backend live loop froze (e.g. API-quota outage that
        // stopped updates mid-match) — owner 2026-07-26: "Vasteras kollierte auf live".
        const mtLive = tip.match_time || (tip.legs || []).map((l) => l.kickoff).find(Boolean) || "";
        const koTs = kickoffInfo(mtLive).ts;
        if (koTs != null && Date.now() - koTs > 2.5 * 3600 * 1000) return null;
        return (
          <div data-testid={`live-state-${tip.id}`} className="inline-flex items-center gap-2 bg-[#F0443C] text-white font-bold text-xs rounded-lg px-3 py-1.5 mb-2">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
            LIVE{liveState.minute ? `  ${liveState.minute}'` : ""}{liveState.score ? `   ·   ${liveState.score}` : ""}
          </div>
        );
      })()}

      {(() => {
        const hasLiveState = tip.live_state || tip.live_minute != null || tip.live_score;
        const mt = tip.match_time || (tip.legs || []).map((l) => l.kickoff).find(Boolean) || "";
        const ko = formatKickoff(tip.match_time, t)
          || (tip.legs || []).map((l) => formatKickoff(l.kickoff, t)).find(Boolean) || "";
        const live = !hasLiveState && isKickoffLive(mt);
        if (live) {
          return (
            <div data-testid={`tip-live-${tip.id}`} className="inline-flex items-center gap-1.5 mb-2 rounded-lg bg-[#F0443C]/15 border border-[#F0443C]/40 px-2.5 py-1 text-sm font-bold text-[#F0443C]">
              <span className="w-2 h-2 rounded-full bg-[#F0443C] animate-pulse" /> {t("kickoff.live")}
            </div>
          );
        }
        if (!ko) return null;
        return (
          <div data-testid={`tip-kickoff-${tip.id}`} className="inline-flex items-center gap-1.5 mb-2 rounded-lg bg-volt/10 border border-volt/30 px-2.5 py-1 text-sm font-bold text-volt">
            <Clock size={14} /> {ko}
          </div>
        );
      })()}
      {(tip.league || tip.country) && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-zinc-500 mb-2">
          {tip.league && <span>{toLatin(tip.league)}</span>}
          {tip.country && <span>· {toLatin(tip.country)}</span>}
        </div>
      )}

      {tip.legs && tip.legs.length ? (
        <div className="space-y-2">
          {tip.is_parlay && (
            <span className="inline-flex items-center gap-1 text-[10px] font-bold uppercase tracking-widest text-volt bg-volt/10 border border-volt/30 rounded px-2 py-0.5">
              {t("wall.parlay")} · {tip.legs.length} {tip.legs.length > 1 ? t("wall.games") : t("wall.game")}
            </span>
          )}
          {[...tip.legs].sort((a, b) => (kickoffInfo(a.kickoff).ts ?? Infinity) - (kickoffInfo(b.kickoff).ts ?? Infinity)).map((leg, li) => {
            const ls = STATUS_META[leg.status];
            const settled = ls && leg.status !== "pending";
            return (
            <div key={li} className={`rounded-lg bg-void border px-3 py-2.5 ${settled ? ls.cls.split(" ")[0].replace("/15", "/30") : "border-elevated"}`}>
              <div className="flex items-center justify-between gap-2">
                <span className={`font-heading font-bold text-sm leading-tight ${settled ? ls.text : "text-white"}`}>{toLatin(leg.match) || "—"}</span>
                <div className="flex items-center gap-2 shrink-0">
                  {leg.banker && (
                    <span data-testid={`leg-banker-${li}`} className="inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded bg-cyan-400/15 text-cyan-300">
                      <ShieldCheck size={9} /> Banker
                    </span>
                  )}
                  {ls && (
                    <span data-testid={`leg-status-${leg.status}`} className={`inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded ${ls.cls}`}>
                      <ls.Icon size={9} className={leg.status === "live" ? "animate-pulse" : ""} /> {t(ls.key)}
                    </span>
                  )}
                  {leg.live && leg.live_score ? (
                    <span data-testid={`leg-live-score-${li}`} className="inline-flex items-center gap-1 text-[11px] font-bold text-white bg-[#F0443C] rounded px-1.5 py-0.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />{leg.live_score}{leg.live_minute != null ? ` ${leg.live_minute}'` : ""}
                    </span>
                  ) : (leg.status === "live" || leg.live || isKickoffLive(leg.kickoff)) ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-[#F0443C] bg-[#F0443C]/10 border border-[#F0443C]/30 rounded px-1.5 py-0.5"><span className="w-1.5 h-1.5 rounded-full bg-[#F0443C] animate-pulse" />{t("kickoff.live")}</span>
                  ) : leg.kickoff && formatKickoff(leg.kickoff, t) ? (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold text-volt bg-volt/10 border border-volt/25 rounded px-1.5 py-0.5"><Clock size={10} />{formatKickoff(leg.kickoff, t)}</span>
                  ) : null}
                </div>
              </div>
              {leg.league && <span className="text-[10px] text-volt/80 font-semibold uppercase tracking-wider">{toLatin(leg.league)}</span>}
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
              {tip.odds && <span className="text-zinc-500">{t("wall.odds")} <span className="font-mono font-bold text-volt">{tip.odds}</span></span>}
              {tip.stake && <span className="text-zinc-500">{t("wall.stake")} <span className="text-white font-medium">{tip.stake}</span></span>}
              {tip.potential_return && <span className="text-zinc-500">{t("wall.payout")} <span className="text-won font-medium">{tip.potential_return}</span></span>}
            </div>
          )}
        </div>
      ) : (
        <>
          <h4 className="font-heading font-bold text-white text-lg leading-tight">
            {displayTeam(tip.home_team, tip.home_team_latin) || "—"} <span className="text-zinc-600 text-sm">vs</span> {displayTeam(tip.away_team, tip.away_team_latin) || "—"}
          </h4>
          {(tip.category || tip.pick_type) && (() => {
            const cat = tip.category || (tip.pick_type === "value" || tip.pick_type === "combo" ? "value" : tip.pick_type);
            const meta = {
              banker: ["BANKER", "bg-cyan-400/15 text-cyan-300"],
              value: ["VALUE", "bg-volt/15 text-volt"],
              risk: ["RISK", "bg-orange-500/15 text-orange-400"],
              banger: ["BANGER", "bg-orange-500/15 text-orange-400"],
            }[cat] || ["VALUE", "bg-volt/15 text-volt"];
            return (
              <div className="flex items-center gap-2 mt-1.5" data-testid={`pick-type-${cat}`}>
                <span className={`text-[10px] font-black uppercase tracking-widest rounded px-2 py-0.5 ${meta[1]}`}>
                  {meta[0]}
                </span>
              </div>
            );
          })()}
          <div className="flex items-start justify-between gap-3 rounded-lg bg-void px-3 py-2 mt-3">
            <span className="text-white font-semibold text-sm break-words flex-1 min-w-0">{formatSelection(tip.market, t) || "—"}</span>
            {tip.odds && <OddsValue odds={tip.odds} className="font-mono font-bold text-volt shrink-0" />}
          </div>
          {(tip.stake || tip.potential_return) && (
            <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-xs pt-2 px-1">
              {tip.stake && <span className="text-zinc-500">{t("wall.stake")} <span className="text-white font-medium">{tip.stake}</span></span>}
              {tip.potential_return && <span className="text-zinc-500">{t("wall.payout")} <span className="text-won font-medium">{tip.potential_return}</span></span>}
            </div>
          )}
        </>
      )}

      {["pending", "live"].includes(tip.status) && (
        <button
          data-testid={`play-slip-${tip.id}`}
          onClick={() => {
            const legs = (tip.legs && tip.legs.length)
              ? tip.legs.map((l) => ({
                  match: toLatin(l.match) || `${displayTeam(tip.home_team, tip.home_team_latin)} vs ${displayTeam(tip.away_team, tip.away_team_latin)}`,
                  market: (l.selections || []).map((s, si) => `${formatSelection(s, t)}${(l.sel_odds || [])[si] ? ` @${(l.sel_odds)[si]}` : ""}`).join(" + "),
                  kickoff: l.kickoff,
                  league: l.league || "",
                  banker: !!l.banker,
                }))
              : [{
                  match: `${displayTeam(tip.home_team, tip.home_team_latin) || ""} vs ${displayTeam(tip.away_team, tip.away_team_latin) || ""}`.trim(),
                  market: formatSelection(tip.market, t),
                  odds: tip.odds,
                  kickoff: tip.match_time,
                }];
            onPlay && onPlay({ legs, meta: { totalOdds: tip.odds, stake: tip.stake, winnings: tip.potential_return, title: tip.is_parlay ? t("wall.parlay") : "" } });
          }}
          className="w-full mt-3 flex items-center justify-center gap-2 rounded-xl bg-volt text-void font-bold text-sm py-2.5 hover:brightness-110 active:scale-[0.99] transition-all"
        >
          <Ticket size={16} /> {t("play.btn")}
        </button>
      )}

      {tip.ai_analysis && (
        <p className="text-xs text-zinc-400 mt-2 border-l-2 border-volt pl-2 leading-snug">
          <span className="text-volt font-semibold">{t("wall.aisays")}:</span> {localizeProse(toLatin(tip.ai_analysis), t, lang)}
        </p>
      )}

      <div className="mt-3 pt-3 border-t border-elevated space-y-2">
        <div className="flex items-center justify-between gap-2">
          <p className="text-[9px] uppercase tracking-widest text-zinc-500">{t("wall.aisays")}</p>
          <AiRatingStars rating={tip.ai_rating} />
        </div>
        <div className="flex items-center justify-between gap-2">
          <p className="text-[9px] uppercase tracking-widest text-zinc-500">{t("wall.community")}</p>
          <p className="font-mono font-black text-base text-white">{tip.avg_rating || "—"} <span className="text-[10px] text-zinc-500">({tip.ratings_count})</span></p>
        </div>
      </div>

      <div className="mt-3">
        <p className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1.5">{myStars ? t("wall.your") + `: ${myStars}` : t("wall.apex")}</p>
        <StarRating value={myStars || 0} onRate={(s) => onRate(tip, s)} size={20} />
      </div>

      {canDelete && (
        <div className="mt-3" data-testid={`settle-${tip.id}`}>
          <p className="text-[10px] uppercase tracking-widest text-zinc-500 mb-1.5">{t("wall.setresult")}</p>
          <div className="grid grid-cols-4 gap-1.5">
            <button onClick={() => onSettle(tip, tip.source === "hq-live" ? "live" : "pending")} data-testid={`settle-open-${tip.id}`}
              className={`text-[11px] font-bold py-1.5 rounded-lg transition-colors ${["pending","live"].includes(tip.status) ? "bg-amber-400 text-void" : "bg-amber-500/15 text-amber-400 hover:bg-amber-500/25"}`}>{t("wall.open")}</button>
            <button onClick={() => onSettle(tip, "won")} data-testid={`settle-won-${tip.id}`}
              className={`text-[11px] font-bold py-1.5 rounded-lg transition-colors ${tip.status === "won" ? "bg-won text-void" : "bg-won/15 text-won hover:bg-won/25"}`}>{t("wall.won")}</button>
            <button onClick={() => onSettle(tip, "lost")} data-testid={`settle-lost-${tip.id}`}
              className={`text-[11px] font-bold py-1.5 rounded-lg transition-colors ${tip.status === "lost" ? "bg-lost text-white" : "bg-lost/15 text-lost hover:bg-lost/25"}`}>{t("wall.lost")}</button>
            <button onClick={() => onSettle(tip, "cashed_out")} data-testid={`settle-cashed-${tip.id}`}
              className={`flex items-center justify-center gap-1 text-[11px] font-bold py-1.5 rounded-lg transition-colors ${tip.status === "cashed_out" ? "bg-sky-400 text-void" : "bg-sky-400/15 text-sky-400 hover:bg-sky-400/25"}`}><Banknote size={12} /> {t("wall.cashed")}</button>
          </div>
        </div>
      )}
    </motion.div>
  );
}
