import React, { useEffect, useRef, useState } from "react";
import { X, Trash2, Plus, Upload, Play, Save, Loader2 } from "lucide-react";
import api, { apiErr } from "../api";
import { toast } from "sonner";

// Admin panel: pflege die Startelf-Watchlist (Value-Spieler). Steht ein Spieler ~20 Min vor
// Anpfiff in der Startelf, postet TipJarHQ automatisch je aktiviertem Markt einen Pick.
export default function LineupWatchPanel({ open, onClose }) {
  const [catalog, setCatalog] = useState([]);
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState("");
  const [name, setName] = useState("");
  const [team, setTeam] = useState("");
  const fileRef = useRef(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/lineup-watch");
      setCatalog(data.catalog || []);
      setPlayers(data.players || []);
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (open) load(); }, [open]); // eslint-disable-line

  const addManual = async () => {
    if (!name.trim() || !team.trim()) { toast.error("Spieler und Team angeben"); return; }
    setBusy("add");
    try {
      await api.post("/admin/lineup-watch", { player_name: name.trim(), team_display: team.trim() });
      toast.success(`${name.trim()} hinzugefügt`);
      setName(""); setTeam("");
      await load();
    } catch (err) { toast.error(apiErr(err)); } finally { setBusy(""); }
  };

  const onUpload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy("ocr");
    try {
      const fd = new FormData();
      fd.append("file", f);
      const { data } = await api.post("/admin/lineup-watch/ocr", fd);
      if (data.ok) { toast.success(`Gespeichert: ${data.player.player_name} · ${data.player.team_display}`); await load(); }
      else toast.error(data.error || "Bild nicht lesbar");
    } catch (err) { toast.error(apiErr(err)); } finally { setBusy(""); if (fileRef.current) fileRef.current.value = ""; }
  };

  const toggleMarket = (pi, mi) => {
    setPlayers((prev) => prev.map((p, i) => i !== pi ? p : {
      ...p, markets: p.markets.map((m, j) => j !== mi ? m : { ...m, enabled: !m.enabled }),
    }));
  };
  const editMarket = (pi, mi, field, val) => {
    setPlayers((prev) => prev.map((p, i) => i !== pi ? p : {
      ...p, markets: p.markets.map((m, j) => j !== mi ? m : { ...m, [field]: val }),
    }));
  };

  const savePlayer = async (p) => {
    setBusy(p.id);
    try {
      await api.patch(`/admin/lineup-watch/${p.id}`, { markets: p.markets });
      toast.success(`${p.player_name} gespeichert`);
      await load();
    } catch (err) { toast.error(apiErr(err)); } finally { setBusy(""); }
  };

  const delPlayer = async (p) => {
    if (!window.confirm(`${p.player_name} von der Watchlist entfernen?`)) return;
    setBusy(p.id);
    try {
      await api.delete(`/admin/lineup-watch/${p.id}`);
      toast.success(`${p.player_name} entfernt`);
      await load();
    } catch (err) { toast.error(apiErr(err)); } finally { setBusy(""); }
  };

  const runNow = async () => {
    setBusy("run");
    try {
      const { data } = await api.post("/admin/lineup-watch/run");
      toast.success(`Prüfung: ${data.posted || 0} Picks gepostet · ${data.checked || 0} Spiele geprüft`);
    } catch (err) { toast.error(apiErr(err)); } finally { setBusy(""); }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/75 p-3 overflow-y-auto"
         data-testid="lineup-watch-panel" onClick={onClose}>
      <div className="w-full max-w-2xl rounded-2xl border border-elevated bg-[#0e0e10] my-6"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-elevated px-5 py-4">
          <div className="min-w-0">
            <h2 className="text-lg font-black text-white">Startelf-Watchlist</h2>
            <p className="text-xs text-zinc-400">Value-Spieler → Auto-Pick ~20 Min vor Anpfiff, wenn in der Startelf.</p>
          </div>
          <button onClick={onClose} data-testid="lineup-watch-close" className="text-zinc-400 hover:text-white p-1"><X size={18} /></button>
        </div>

        {/* Add row */}
        <div className="px-5 py-4 border-b border-elevated space-y-3">
          <div className="flex flex-col sm:flex-row gap-2">
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Spielername (z.B. Kevin Kelsy)"
                   data-testid="lineup-add-name" className="flex-1 rounded-lg bg-[#161618] border border-elevated px-3 py-2 text-sm text-white placeholder-zinc-500" />
            <input value={team} onChange={(e) => setTeam(e.target.value)} placeholder="Team (z.B. Portland Timbers)"
                   data-testid="lineup-add-team" className="flex-1 rounded-lg bg-[#161618] border border-elevated px-3 py-2 text-sm text-white placeholder-zinc-500" />
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={addManual} disabled={busy === "add"} data-testid="lineup-add-btn"
                    className="inline-flex items-center gap-2 rounded-full bg-[#E11D2A] text-white font-bold px-4 py-2 text-sm hover:bg-[#c4141f] active:scale-95 transition-all disabled:opacity-50">
              {busy === "add" ? <Loader2 size={15} className="animate-spin" /> : <Plus size={15} />} Hinzufügen
            </button>
            <button onClick={() => fileRef.current?.click()} disabled={busy === "ocr"} data-testid="lineup-ocr-btn"
                    className="inline-flex items-center gap-2 rounded-full border border-elevated text-zinc-200 font-bold px-4 py-2 text-sm hover:border-zinc-500 active:scale-95 transition-all disabled:opacity-50">
              {busy === "ocr" ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />} Bild hochladen
            </button>
            <input ref={fileRef} type="file" accept="image/*" onChange={onUpload} className="hidden" data-testid="lineup-ocr-input" />
            <button onClick={runNow} disabled={busy === "run"} data-testid="lineup-run-btn"
                    className="inline-flex items-center gap-2 rounded-full border border-emerald-500/50 text-emerald-300 font-bold px-4 py-2 text-sm hover:bg-emerald-500/10 active:scale-95 transition-all disabled:opacity-50">
              {busy === "run" ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />} Jetzt prüfen
            </button>
          </div>
        </div>

        {/* Players */}
        <div className="px-5 py-4 space-y-4">
          {loading && <p className="text-sm text-zinc-400">Lädt…</p>}
          {!loading && players.length === 0 && <p className="text-sm text-zinc-400">Noch keine Spieler in der Watchlist.</p>}
          {players.map((p, pi) => (
            <div key={p.id} className="rounded-xl border border-elevated bg-[#141416] p-4" data-testid={`lineup-player-${p.player_key}`}>
              <div className="flex items-center justify-between gap-2 mb-3">
                <div className="min-w-0">
                  <div className="font-bold text-white truncate">{p.player_name}</div>
                  <div className="text-xs text-zinc-400 truncate">{p.team_display}</div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => savePlayer(p)} disabled={busy === p.id} data-testid={`lineup-save-${p.player_key}`}
                          className="inline-flex items-center gap-1.5 rounded-full bg-[#E11D2A] text-white font-bold px-3 py-1.5 text-xs hover:bg-[#c4141f] active:scale-95 transition-all disabled:opacity-50">
                    {busy === p.id ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />} Speichern
                  </button>
                  <button onClick={() => delPlayer(p)} disabled={busy === p.id} data-testid={`lineup-del-${p.player_key}`}
                          className="text-zinc-400 hover:text-[#E11D2A] p-1.5"><Trash2 size={15} /></button>
                </div>
              </div>
              <div className="space-y-1.5">
                {(p.markets || []).map((m, mi) => (
                  <div key={m.id} className="flex items-center gap-2 flex-wrap">
                    <label className="flex items-center gap-2 flex-1 min-w-[180px] cursor-pointer">
                      <input type="checkbox" checked={!!m.enabled} onChange={() => toggleMarket(pi, mi)}
                             data-testid={`lineup-mkt-${p.player_key}-${m.id}`}
                             className="h-4 w-4 accent-[#E11D2A]" />
                      <span className={`text-sm ${m.enabled ? "text-white" : "text-zinc-500"}`}>{m.label}</span>
                    </label>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-zinc-500">Quote</span>
                      <input value={m.odds} onChange={(e) => editMarket(pi, mi, "odds", e.target.value)}
                             data-testid={`lineup-odds-${p.player_key}-${m.id}`}
                             className="w-16 rounded bg-[#0e0e10] border border-elevated px-2 py-1 text-xs text-white text-center" />
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="text-[10px] text-zinc-500">★</span>
                      <input type="number" min="1" max="10" value={m.stars}
                             onChange={(e) => editMarket(pi, mi, "stars", parseInt(e.target.value) || 1)}
                             data-testid={`lineup-stars-${p.player_key}-${m.id}`}
                             className="w-12 rounded bg-[#0e0e10] border border-elevated px-2 py-1 text-xs text-white text-center" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
