import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import confetti from "canvas-confetti";
import { Flame, Users, Trophy, Zap, RefreshCw, CheckCircle2, XCircle, Radio, Clock, Trash2 } from "lucide-react";
import StarRating from "./StarRating";
import api, { apiErr, fileUrl } from "../api";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";
import { toast } from "sonner";

const FILTERS = [
  { k: "new", label: "wall.filter.new" },
  { k: "hype", label: "wall.filter.hype" },
  { k: "top", label: "wall.filter.top" },
];
const STATUS = [
  { k: "", label: "wall.filter.pending", val: "pending" },
];

export default function RateWall({ refreshKey, requireLogin }) {
  const { t } = useI18n();
  const { user, setUser } = useAuth();
  const [tips, setTips] = useState([]);
  const [sort, setSort] = useState("new");
  const [status, setStatus] = useState("pending");
  const [myRatings, setMyRatings] = useState({});
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const load = useCallback(async (silent) => {
    if (!silent) setLoading(true);
    try {
      const params = { sort };
      if (status) params.status = status;
      const { data } = await api.get("/tips", { params });
      setTips(data);
    } catch { /* ignore */ } finally { if (!silent) setLoading(false); }
  }, [sort, status]);

  useEffect(() => {
    load();
    const iv = setInterval(() => load(true), 20000);
    return () => clearInterval(iv);
  }, [load, refreshKey]);

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
      if (user) setUser({ ...user, streak: data.streak, ratings_given: (user.ratings_given || 0) + 1 });
      confetti({ particleCount: 45, spread: 60, origin: { y: 0.7 }, colors: ["#E1FF00", "#00FF94", "#FFFFFF"] });
      toast.success(t("wall.thanks"));
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
          <h2 className="font-heading text-3xl md:text-5xl font-black text-white tracking-tighter mt-2">{t("wall.title")}</h2>
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
            <div className="flex items-center gap-3 rounded-2xl bg-surface border border-elevated px-4 py-3" data-testid="streak-widget">
              <Flame className="text-bell" size={28} />
              <div>
                <p className="text-[10px] uppercase tracking-widest text-zinc-500">{t("wall.streak")}</p>
                <p className="font-mono font-black text-2xl text-white">{user.streak || 0} <span className="text-sm text-zinc-500">{t("wall.days")}</span></p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* filters */}
      <div className="flex flex-wrap gap-2 mb-6">
        {FILTERS.map((f) => (
          <button key={f.k} data-testid={`sort-${f.k}`} onClick={() => setSort(f.k)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors ${sort === f.k ? "bg-volt text-void" : "bg-surface border border-elevated text-zinc-400 hover:text-white"}`}>
            {t(f.label)}
          </button>
        ))}
        <span className="w-px bg-elevated mx-1" />
        {[["pending", "wall.filter.pending"], ["live", "wall.filter.live"], ["won", "wall.filter.won"], ["lost", "wall.filter.lost"]].map(([v, lbl]) => (
          <button key={v} data-testid={`status-${v}`} onClick={() => setStatus(v)}
            className={`px-4 py-2 rounded-full text-sm font-semibold transition-colors ${status === v ? "bg-white text-void" : "bg-surface border border-elevated text-zinc-400 hover:text-white"}`}>
            {t(lbl)}
          </button>
        ))}
      </div>

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
            <TipCard key={tip.id} tip={tip} i={i} t={t} onRate={rate} myStars={myRatings[tip.id]} isAdmin={user?.role === "admin"} onSettle={settle} onDelete={del} canDelete={user?.role === "admin" || tip.user_id === user?.id} />
          ))}
        </div>
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

function TipCard({ tip, i, t, onRate, myStars, isAdmin, onSettle, onDelete, canDelete }) {
  const flags = tipFlags(tip);
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
      transition={{ delay: (i % 6) * 0.05 }}
      data-testid={`tip-card-${tip.id}`}
      className="rounded-xl bg-surface border border-elevated p-4 hover:-translate-y-1 hover:border-volt/50 transition-all flex flex-col"
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-full bg-elevated flex items-center justify-center text-xs font-bold text-white shrink-0">
            {tip.username?.[0]?.toUpperCase() || "?"}
          </div>
          <span className="text-sm text-zinc-400 truncate">{t("wall.by")} <span className="text-white font-semibold">{tip.username}</span></span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
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

      {tip.image_path && (
        <img src={fileUrl(tip.image_path)} alt="slip" className="w-full h-36 object-cover rounded-lg mb-3 border border-elevated" loading="lazy" />
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
                {(leg.selections || []).map((s, si) => (
                  <span key={si} className="text-[11px] text-zinc-100 bg-elevated rounded px-2 py-1 leading-tight">{s}</span>
                ))}
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
          <div className="flex items-center justify-between rounded-lg bg-void px-3 py-2 mt-3">
            <span className="text-white font-semibold text-sm truncate">{tip.market || "—"}</span>
            {tip.odds && <span className="font-mono font-bold text-volt shrink-0 ml-2">{tip.odds}</span>}
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
    </motion.div>
  );
}
