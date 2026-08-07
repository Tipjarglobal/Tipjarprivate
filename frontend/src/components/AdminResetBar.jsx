import React, { useState } from "react";
import { RotateCcw, AlertTriangle, Trash2, Users, Trophy, RefreshCw, Radar } from "lucide-react";
import Modal from "./Modal";
import LineupWatchPanel from "./LineupWatchPanel";
import HofPinPanel from "./HofPinPanel";
import ScoutFeedPanel from "./ScoutFeedPanel";
import api, { apiErr } from "../api";
import { toast } from "sonner";

// Admin-only homepage bar: "shut down & refill" — hides/removes all PENDING pregame KI-single,
// KI-system and Master slips (never lives / settled) and kicks a fresh regeneration.
export default function AdminResetBar() {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [clearOpen, setClearOpen] = useState(false);
  const [lineupOpen, setLineupOpen] = useState(false);
  const [hofOpen, setHofOpen] = useState(false);
  const [scoutOpen, setScoutOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const doReset = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/admin/reset-pregames");
      toast.success(`Runtergefahren: ${data.removed} Pregame-Scheine entfernt · neue Picks werden erzeugt…`);
      setConfirmOpen(false);
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setBusy(false);
    }
  };

  const doClearLiveSettled = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/admin/clear-live-settled", { scope: "both" });
      toast.success(`Gelöscht: ${data.live_removed} Live · ${data.settled_removed} Abgerechnete`);
      setClearOpen(false);
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setBusy(false);
    }
  };

  const doSettleNow = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/admin/settle-now");
      let cm = 0;
      try {
        const r = await api.post("/admin/code-reading/settle-finished");
        cm = r.data?.settled || 0;
      } catch { /* codemining settle optional */ }
      if (data.ok === false && data.reason) {
        toast.error(data.reason);
      } else {
        toast.success(`Abgerechnet: ${data.settled || 0} Tipps · ${data.parlays?.settled || 0} Parlays · ${data.combos?.settled || 0} Combos · ${cm} Codemining`);
      }
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 pt-4">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[#E11D2A]/40 bg-[#E11D2A]/5 px-4 py-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-[10px] font-black uppercase tracking-widest text-[#E11D2A]">Admin</span>
            <span className="text-sm text-zinc-300 truncate">HQ- & Master-Pregames neu aufsetzen</span>
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center gap-2 w-full sm:w-auto sm:shrink-0">
            <button
              data-testid="admin-lineup-watch-btn"
              onClick={() => setLineupOpen(true)}
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-full border border-emerald-500/60 text-emerald-300 font-bold px-4 py-2 text-sm hover:bg-emerald-500/10 active:scale-95 transition-all">
              <Users size={15} /> Startelf-Watchlist
            </button>
            <button
              data-testid="admin-settle-now-btn"
              onClick={doSettleNow}
              disabled={busy}
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-full border border-sky-500/60 text-sky-300 font-bold px-4 py-2 text-sm hover:bg-sky-500/10 active:scale-95 transition-all disabled:opacity-50">
              <RefreshCw size={15} /> {busy ? "Läuft…" : "Jetzt abrechnen"}
            </button>
            <button
              data-testid="admin-scout-feed-btn"
              onClick={() => setScoutOpen(true)}
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-full border border-fuchsia-500/60 text-fuchsia-300 font-bold px-4 py-2 text-sm hover:bg-fuchsia-500/10 active:scale-95 transition-all">
              <Radar size={15} /> Scout füttern
            </button>
            <button
              data-testid="admin-hof-pin-btn"
              onClick={() => setHofOpen(true)}
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-full border border-amber-400/60 text-amber-300 font-bold px-4 py-2 text-sm hover:bg-amber-400/10 active:scale-95 transition-all">
              <Trophy size={15} /> Hall of Fame pinnen
            </button>
            <button
              data-testid="admin-clear-live-settled-btn"
              onClick={() => setClearOpen(true)}
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-full border border-[#E11D2A]/60 text-[#E11D2A] font-bold px-4 py-2 text-sm hover:bg-[#E11D2A]/10 active:scale-95 transition-all">
              <Trash2 size={15} /> Live & Abgerechnete löschen
            </button>
            <button
              data-testid="admin-reset-pregames-btn"
              onClick={() => setConfirmOpen(true)}
              className="inline-flex items-center justify-center gap-2 w-full sm:w-auto rounded-full bg-[#E11D2A] text-white font-bold px-4 py-2 text-sm hover:bg-[#c4141f] active:scale-95 transition-all">
              <RotateCcw size={15} /> Runterfahren & aufstocken
            </button>
          </div>
        </div>
      </div>

      <Modal open={clearOpen} onClose={() => setClearOpen(false)} title="Alle Live & Abgerechnete löschen?" maxWidth="max-w-md" testId="admin-clear-confirm">
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-xl border border-[#E11D2A]/40 bg-[#E11D2A]/10 px-4 py-3">
            <AlertTriangle size={18} className="text-[#E11D2A] shrink-0 mt-0.5" />
            <p className="text-sm text-zinc-200 leading-snug">
              Entfernt <b>alle aktuellen Live-Picks</b> und die <b>komplette abgerechnete Historie</b>
              (gewonnen/verloren/void) aus <b>dieser</b> Datenbank. Offene Pregame-Tipps bleiben. Nicht umkehrbar.
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setClearOpen(false)} disabled={busy}
              className="flex-1 rounded-lg border border-elevated py-2.5 text-sm font-semibold text-zinc-300 hover:text-white hover:border-zinc-500 transition-colors">
              Abbrechen
            </button>
            <button onClick={doClearLiveSettled} disabled={busy} data-testid="admin-clear-confirm-btn"
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-[#E11D2A] text-white py-2.5 text-sm font-bold hover:bg-[#c4141f] active:scale-95 transition-all disabled:opacity-50">
              <Trash2 size={16} /> {busy ? "Läuft…" : "Ja, löschen"}
            </button>
          </div>
        </div>
      </Modal>

      <Modal open={confirmOpen} onClose={() => setConfirmOpen(false)} title="Wirklich alle Pregame-Scheine löschen?" maxWidth="max-w-md" testId="admin-reset-confirm">
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-xl border border-amber-400/40 bg-amber-500/10 px-4 py-3">
            <AlertTriangle size={18} className="text-amber-300 shrink-0 mt-0.5" />
            <p className="text-sm text-zinc-200 leading-snug">
              Entfernt <b>alle offenen</b> KI-Single-, KI-System- und Master-Scheine (Pregames).
              <b> Live-Scheine und die Historie bleiben unberührt.</b> Direkt danach werden frische
              Picks erzeugt und alle Pregame-Felder wieder aufgefüllt.
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => setConfirmOpen(false)} disabled={busy}
              className="flex-1 rounded-lg border border-elevated py-2.5 text-sm font-semibold text-zinc-300 hover:text-white hover:border-zinc-500 transition-colors">
              Abbrechen
            </button>
            <button onClick={doReset} disabled={busy} data-testid="admin-reset-confirm-btn"
              className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-[#E11D2A] text-white py-2.5 text-sm font-bold hover:bg-[#c4141f] active:scale-95 transition-all disabled:opacity-50">
              <RotateCcw size={16} /> {busy ? "Läuft…" : "Ja, runterfahren"}
            </button>
          </div>
        </div>
      </Modal>

      <LineupWatchPanel open={lineupOpen} onClose={() => setLineupOpen(false)} />
      <HofPinPanel open={hofOpen} onClose={() => setHofOpen(false)} />
      <ScoutFeedPanel open={scoutOpen} onClose={() => setScoutOpen(false)} />
    </>
  );
}
