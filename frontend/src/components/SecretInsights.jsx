import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, Users, BellRing, TrendingUp, Loader2, Lock, Activity, CheckCircle2, XCircle, Trophy, Ban, Trash2, RefreshCw, SlidersHorizontal } from "lucide-react";
import api, { apiErr } from "../api";
import { useAuth } from "../auth";

// PRIVATE analytics — only reachable at /insights and only for the admin account.
// Regular visitors never see this; there is no link to it anywhere in the UI.
export default function SecretInsights() {
  const { user, ready } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);
  const [health, setHealth] = useState(null);
  const [healthErr, setHealthErr] = useState(false);

  useEffect(() => {
    if (!ready) return;
    if (!user || user.role !== "admin") return;
    api.get("/admin/visits").then((r) => setData(r.data)).catch(() => setErr(true));
    api.get("/admin/live-health").then((r) => setHealth(r.data)).catch(() => setHealthErr(true));
  }, [ready, user]);

  if (ready && (!user || user.role !== "admin")) {
    return (
      <div className="min-h-screen bg-void flex flex-col items-center justify-center text-center px-6" data-testid="insights-locked">
        <Lock className="text-zinc-700 mb-4" size={40} />
        <p className="text-zinc-500">Nichts zu sehen hier.</p>
        <button onClick={() => navigate("/")} className="mt-6 text-volt text-sm underline">Zurück</button>
      </div>
    );
  }

  const maxHits = data ? Math.max(1, ...data.daily.map((d) => d.hits)) : 1;

  return (
    <div className="min-h-screen bg-void text-white px-4 py-10" data-testid="insights-page">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 mb-1">
          <Eye className="text-volt" size={26} />
          <h1 className="font-heading text-2xl font-black">Geheime Insights</h1>
        </div>
        <p className="text-xs text-zinc-500 mb-8">Nur für dich sichtbar · anonym & cookiefrei</p>

        <LiveHealth health={health} healthErr={healthErr} />

        <PickManager />

        {!data && !err && (
          <div className="flex items-center gap-2 text-zinc-500"><Loader2 className="animate-spin" size={18} /> lädt…</div>
        )}
        {err && <p className="text-lost">Konnte Daten nicht laden.</p>}

        {data && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
              <Stat testid="stat-today-unique" icon={Eye} label="Heute (Besucher)" value={data.today_unique} sub={`${data.today_hits} Aufrufe`} />
              <Stat testid="stat-week-unique" icon={TrendingUp} label="7 Tage (Besucher)" value={data.week_unique} sub={`${data.week_hits} Aufrufe`} />
              <Stat testid="stat-total-unique" icon={Eye} label="Gesamt (Besucher)" value={data.total_unique} sub={`${data.total_hits} Aufrufe`} />
              <Stat testid="stat-members" icon={Users} label="Registriert" value={data.members} sub={`${data.subscribers} mit Push`} />
            </div>

            <div className="rounded-2xl border border-elevated bg-surface p-5">
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="text-volt" size={16} />
                <p className="text-xs uppercase tracking-widest text-zinc-400">Besucher — letzte 14 Tage</p>
              </div>
              <div className="flex items-end justify-between gap-1 h-40" data-testid="insights-chart">
                {data.daily.map((d) => (
                  <div key={d.day} className="flex-1 flex flex-col items-center gap-1 group">
                    <span className="text-[9px] text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity">{d.hits}</span>
                    <div
                      className="w-full rounded-t bg-volt/80 hover:bg-volt transition-colors"
                      style={{ height: `${Math.max(4, (d.hits / maxHits) * 130)}px` }}
                      title={`${d.day}: ${d.unique} Besucher / ${d.hits} Aufrufe`}
                    />
                    <span className="text-[8px] text-zinc-600">{d.day.slice(5)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6 flex items-center gap-2 text-xs text-zinc-500">
              <BellRing size={13} /> {data.subscribers} von {data.members} registrierten Nutzern haben Push aktiviert.
            </div>
          </>
        )}

        <button onClick={() => navigate("/")} className="mt-10 text-zinc-500 text-sm underline" data-testid="insights-back">← Zurück zur Seite</button>
      </div>
    </div>
  );
}

const Stat = ({ icon: Icon, label, value, sub, testid }) => (
  <div className="rounded-2xl border border-elevated bg-surface p-4" data-testid={testid}>
    <Icon className="text-volt mb-2" size={16} />
    <p className="font-mono font-black text-2xl leading-none">{value}</p>
    <p className="text-[10px] uppercase tracking-widest text-zinc-500 mt-1">{label}</p>
    {sub && <p className="text-[10px] text-zinc-600 mt-0.5">{sub}</p>}
  </div>
);

// Row with a green/red verdict — mobile-friendly, no console needed.
const Check = ({ ok, label, detail }) => (
  <div className="flex items-start gap-2 py-1.5">
    {ok ? <CheckCircle2 className="text-won shrink-0 mt-0.5" size={16} /> : <XCircle className="text-lost shrink-0 mt-0.5" size={16} />}
    <div className="min-w-0">
      <p className="text-sm text-white">{label}</p>
      {detail && <p className="text-[11px] text-zinc-500 break-words">{detail}</p>}
    </div>
  </div>
);

const LiveHealth = ({ health, healthErr }) => {
  const errs = health && Array.isArray(health.live_feed_errors) ? health.live_feed_errors : [];
  const apiErrs = health && Array.isArray(health.api_football_errors) ? health.api_football_errors : [];
  const apiOk = !!(health && health.api_football_key_set && health.api_football_http === 200 && apiErrs.length === 0);
  // Build a one-line plain-language verdict for the top of the card.
  let verdict = "Prüfe…";
  let verdictOk = false;
  if (health) {
    if (!health.api_football_key_set) verdict = "❌ API-Football-Key fehlt in dieser Umgebung → deshalb keine Live-Picks.";
    else if (health.api_football_http !== 200 || apiErrs.length) verdict = "❌ API-Football antwortet mit Fehler (Key ungültig/gesperrt?).";
    else if (!health.hq_account_exists) verdict = "❌ HQ-Konto fehlt in der Datenbank → keine Picks möglich.";
    else if (!health.is_leader) verdict = "⚠️ Diese Instanz ist gerade nicht Leader — normal, andere Replica arbeitet.";
    else if ((health.live_fixtures_available_now || 0) === 0) verdict = "ℹ️ Gerade laufen 0 Spiele weltweit — später kommen automatisch Lives.";
    else { verdict = "✅ Alles ok — Live-System sollte Picks liefern."; verdictOk = true; }
  }
  const req = health && health.api_football_requests;

  return (
    <div className="rounded-2xl border border-elevated bg-surface p-5 mb-8" data-testid="live-health">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="text-volt" size={16} />
        <p className="text-xs uppercase tracking-widest text-zinc-400">Live-Diagnose</p>
      </div>
      {!health && !healthErr && (
        <div className="flex items-center gap-2 text-zinc-500"><Loader2 className="animate-spin" size={16} /> lädt…</div>
      )}
      {healthErr && <p className="text-lost text-sm">Konnte Diagnose nicht laden.</p>}
      {health && (
        <>
          <div className={`rounded-xl px-3 py-2.5 mb-3 text-sm font-semibold ${verdictOk ? "bg-won/10 text-won" : "bg-lost/10 text-lost"}`} data-testid="live-verdict">
            {verdict}
          </div>
          <Check ok={health.api_football_key_set} label="API-Football-Key gesetzt"
                 detail={health.api_football_key_set ? `Plan: ${health.api_football_plan || "?"} · ${req ? `${req.current}/${req.limit_day} Requests heute` : ""}` : "Fehlt in der Deployment-Umgebung!"} />
          <Check ok={apiOk} label="API-Football erreichbar"
                 detail={`HTTP ${health.api_football_http ?? "?"}${apiErrs.length ? " · Fehler: " + JSON.stringify(apiErrs) : ""}`} />
          <Check ok={health.hq_account_exists} label="HQ-Konto vorhanden" />
          <Check ok={health.is_leader} label="Diese Instanz ist Leader (läuft Background-Loops)"
                 detail={health.is_leader ? "" : "andere Replica ist Leader — das ist ok"} />
          <Check ok={(health.live_fixtures_available_now || 0) > 0} label="Laufende Spiele weltweit"
                 detail={`${health.live_fixtures_available_now ?? 0} live${errs.length ? " · Feed-Fehler: " + JSON.stringify(errs) : ""}`} />
          <div className="grid grid-cols-2 gap-3 mt-3">
            <div className="rounded-xl border border-elevated p-3">
              <p className="font-mono font-black text-xl">{health.current_live_tips ?? 0}</p>
              <p className="text-[10px] uppercase tracking-widest text-zinc-500 mt-1">aktive Live-Picks</p>
            </div>
            <div className="rounded-xl border border-elevated p-3">
              <p className="font-mono font-black text-xl">{health.pending_prematch_tips ?? 0}</p>
              <p className="text-[10px] uppercase tracking-widest text-zinc-500 mt-1">offene Vor-Spiel-Picks</p>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

// ── Pick-Manager ─────────────────────────────────────────────
// Lists every open tip (pending/live) and lets the admin resolve it
// with one tap: Gewonnen · Verloren · Void · Löschen. Perfect for custom
// player-prop Smart Picks that API-Football can't settle automatically.
const SETTLE_ACTIONS = [
  { key: "won", label: "Gewonnen", icon: Trophy, cls: "bg-won/15 text-won hover:bg-won/25" },
  { key: "lost", label: "Verloren", icon: XCircle, cls: "bg-lost/15 text-lost hover:bg-lost/25" },
  { key: "void", label: "Void", icon: Ban, cls: "bg-zinc-700/40 text-zinc-300 hover:bg-zinc-700/60" },
];

const SRC_ORDER = ["Smart Picks", "Live-Picks", "KI-Picks", "Mitglieder-Tipps"];

const PickManager = () => {
  const [items, setItems] = useState(null);
  const [err, setErr] = useState(false);
  const [busy, setBusy] = useState({});

  const load = () => {
    setErr(false);
    api.get("/admin/pending-tips")
      .then((r) => setItems(r.data.items || []))
      .catch(() => setErr(true));
  };
  useEffect(load, []);

  const act = async (tip, action) => {
    const verb = action === "delete" ? "löschen" : action;
    if (!window.confirm(`Wette „${tip.label}" wirklich als "${verb}" markieren?`)) return;
    setBusy((b) => ({ ...b, [tip.id]: true }));
    try {
      if (action === "delete") await api.delete(`/tips/${tip.id}`);
      else await api.put(`/tips/${tip.id}/status`, { status: action });
      setItems((cur) => cur.filter((t) => t.id !== tip.id));
    } catch (e) {
      alert(apiErr(e, "Aktion fehlgeschlagen."));
    } finally {
      setBusy((b) => ({ ...b, [tip.id]: false }));
    }
  };

  const groups = {};
  (items || []).forEach((t) => {
    (groups[t.source_name] = groups[t.source_name] || []).push(t);
  });
  const groupNames = Object.keys(groups).sort(
    (a, b) => (SRC_ORDER.indexOf(a) + 1 || 99) - (SRC_ORDER.indexOf(b) + 1 || 99)
  );

  return (
    <div className="rounded-2xl border border-elevated bg-surface p-5 mb-8" data-testid="pick-manager">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="text-volt" size={16} />
          <p className="text-xs uppercase tracking-widest text-zinc-400">Pick-Manager · offene Wetten</p>
        </div>
        <button onClick={load} className="text-zinc-500 hover:text-volt transition-colors" title="Neu laden" data-testid="pm-refresh">
          <RefreshCw size={15} />
        </button>
      </div>

      {!items && !err && (
        <div className="flex items-center gap-2 text-zinc-500"><Loader2 className="animate-spin" size={16} /> lädt…</div>
      )}
      {err && <p className="text-lost text-sm">Konnte offene Wetten nicht laden.</p>}
      {items && items.length === 0 && (
        <p className="text-sm text-zinc-500" data-testid="pm-empty">🎉 Keine offenen Wetten — alles abgerechnet.</p>
      )}

      {groupNames.map((name) => (
        <div key={name} className="mb-5 last:mb-0">
          <p className="text-[10px] uppercase tracking-widest text-zinc-500 mb-2">{name} · {groups[name].length}</p>
          <div className="space-y-2">
            {groups[name].map((t) => (
              <div key={t.id} className="rounded-xl border border-elevated bg-void/40 p-3" data-testid={`pm-item-${t.id}`}>
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm text-white font-semibold truncate">{t.label}</p>
                    <p className="text-[11px] text-zinc-400 break-words">{t.market || "—"}</p>
                    <div className="flex items-center gap-2 mt-1 text-[10px] text-zinc-600">
                      <span className={`px-1.5 py-0.5 rounded ${t.status === "live" ? "bg-lost/20 text-lost" : "bg-zinc-700/40 text-zinc-400"}`}>
                        {t.status === "live" ? "LIVE" : "OFFEN"}
                      </span>
                      {t.odds ? <span>Quote {t.odds}</span> : null}
                      {t.match_time ? <span>{new Date(t.match_time).toLocaleString("de-DE", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</span> : null}
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2 mt-2.5">
                  {SETTLE_ACTIONS.map((a) => (
                    <button
                      key={a.key}
                      disabled={busy[t.id]}
                      onClick={() => act(t, a.key)}
                      className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-colors disabled:opacity-40 ${a.cls}`}
                      data-testid={`pm-${a.key}-${t.id}`}
                    >
                      <a.icon size={13} /> {a.label}
                    </button>
                  ))}
                  <button
                    disabled={busy[t.id]}
                    onClick={() => act(t, "delete")}
                    className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-lost/10 text-lost/80 hover:bg-lost/20 transition-colors disabled:opacity-40"
                    data-testid={`pm-delete-${t.id}`}
                  >
                    <Trash2 size={13} /> Löschen
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

