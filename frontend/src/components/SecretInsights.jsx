import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Eye, Users, BellRing, TrendingUp, Loader2, Lock } from "lucide-react";
import api from "../api";
import { useAuth } from "../auth";

// PRIVATE analytics — only reachable at /insights and only for the admin account.
// Regular visitors never see this; there is no link to it anywhere in the UI.
export default function SecretInsights() {
  const { user, ready } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    if (!ready) return;
    if (!user || user.role !== "admin") return;
    api.get("/admin/visits").then((r) => setData(r.data)).catch(() => setErr(true));
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
