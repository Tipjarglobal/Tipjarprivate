import React, { useState } from "react";
import Modal, { inputCls } from "./Modal";
import { Trash2, ArrowLeftRight, Plus, X, ShieldCheck, Save } from "lucide-react";
import api, { apiErr } from "../api";
import { toast } from "sonner";

const LEG_STATUSES = ["pending", "live", "won", "lost", "void"];
const STATUS_LABEL = {
  pending: "Offen", live: "Live", won: "Gewonnen", lost: "Verloren", void: "Annulliert",
};

const smallInput =
  "w-full bg-void border border-elevated rounded-lg px-2.5 py-1.5 text-sm text-white placeholder-zinc-600 focus:border-volt focus:outline-none focus:ring-1 focus:ring-volt/40 transition-colors";

export default function AdminSlipEditor({ tip, onClose, onSaved }) {
  const [f, setF] = useState({
    match_time: tip.match_time || "",
    home_team: tip.home_team || "",
    away_team: tip.away_team || "",
    league: tip.league || "",
    country: tip.country || "",
    market: tip.market || "",
    odds: tip.odds || "",
    stake: tip.stake || "",
  });
  const [legs, setLegs] = useState(() =>
    (tip.legs || []).map((l) => ({
      match: l.match || "",
      league: l.league || "",
      kickoff: l.kickoff || "",
      selections: [...(l.selections || [])],
      sel_odds: [...(l.sel_odds || [])],
      banker: !!l.banker,
      status: l.status || "pending",
    }))
  );
  const [saving, setSaving] = useState(false);

  const set = (k, v) => setF((s) => ({ ...s, [k]: v }));
  const swap = () => setF((s) => ({ ...s, home_team: s.away_team, away_team: s.home_team }));

  const setLeg = (i, patch) => setLegs((ls) => ls.map((l, x) => (x === i ? { ...l, ...patch } : l)));
  const removeLeg = (i) => setLegs((ls) => ls.filter((_, x) => x !== i));
  const setSel = (li, si, val) =>
    setLegs((ls) => ls.map((l, x) => (x === li ? { ...l, selections: l.selections.map((s, y) => (y === si ? val : s)) } : l)));
  const setSelOdd = (li, si, val) =>
    setLegs((ls) => ls.map((l, x) => {
      if (x !== li) return l;
      const o = [...(l.sel_odds || [])];
      o[si] = val;
      return { ...l, sel_odds: o };
    }));
  const removeSel = (li, si) =>
    setLegs((ls) => ls.map((l, x) => (x === li ? {
      ...l,
      selections: l.selections.filter((_, y) => y !== si),
      sel_odds: (l.sel_odds || []).filter((_, y) => y !== si),
    } : l)));
  const addSel = (li) =>
    setLegs((ls) => ls.map((l, x) => (x === li ? {
      ...l, selections: [...l.selections, ""], sel_odds: [...(l.sel_odds || []), ""],
    } : l)));

  const save = async () => {
    setSaving(true);
    try {
      const payload = {
        ...f,
        legs: legs.map((l) => ({
          ...l,
          selections: l.selections.map((s) => (s || "").trim()).filter(Boolean),
          sel_odds: (l.sel_odds || []).map((o) => (o || "").toString().trim()),
        })),
      };
      const { data } = await api.patch(`/admin/tips/${tip.id}`, payload);
      toast.success("Schein aktualisiert ✓");
      onSaved?.(data);
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open onClose={onClose} title="Schein bearbeiten (Admin)" maxWidth="max-w-2xl" testId="admin-slip-editor">
      <div className="space-y-5 max-h-[70vh] overflow-y-auto pr-1">
        {/* Match / teams */}
        <div>
          <p className="text-[10px] uppercase tracking-widest text-zinc-500 mb-2">Spiel & Zeit</p>
          <div className="grid grid-cols-2 gap-2">
            <div className="col-span-2 flex items-end gap-2">
              <div className="flex-1">
                <span className="text-[10px] text-zinc-500">Heim</span>
                <input data-testid="edit-home" className={smallInput} value={f.home_team} onChange={(e) => set("home_team", e.target.value)} placeholder="Heimteam" />
              </div>
              <button type="button" onClick={swap} data-testid="edit-swap-teams" title="Teams tauschen"
                className="mb-0.5 p-2 rounded-lg border border-elevated text-zinc-300 hover:text-white hover:border-volt/50 transition-colors">
                <ArrowLeftRight size={16} />
              </button>
              <div className="flex-1">
                <span className="text-[10px] text-zinc-500">Auswärts</span>
                <input data-testid="edit-away" className={smallInput} value={f.away_team} onChange={(e) => set("away_team", e.target.value)} placeholder="Auswärtsteam" />
              </div>
            </div>
            <div>
              <span className="text-[10px] text-zinc-500">Anstoß / Zeit</span>
              <input data-testid="edit-matchtime" className={smallInput} value={f.match_time} onChange={(e) => set("match_time", e.target.value)} placeholder="DD/MM/YYYY HH:MM" />
            </div>
            <div>
              <span className="text-[10px] text-zinc-500">Liga</span>
              <input data-testid="edit-league" className={smallInput} value={f.league} onChange={(e) => set("league", e.target.value)} placeholder="Liga" />
            </div>
            <div>
              <span className="text-[10px] text-zinc-500">Land</span>
              <input className={smallInput} value={f.country} onChange={(e) => set("country", e.target.value)} placeholder="Land" />
            </div>
          </div>
        </div>

        {/* Single-bet market / odds (only when no legs) */}
        {legs.length === 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-zinc-500 mb-2">Auswahl & Quote</p>
            <div className="grid grid-cols-3 gap-2">
              <input data-testid="edit-market" className={`${smallInput} col-span-2`} value={f.market} onChange={(e) => set("market", e.target.value)} placeholder="z.B. Über 0.5 Tore" />
              <input data-testid="edit-odds" className={smallInput} value={f.odds} onChange={(e) => set("odds", e.target.value)} placeholder="Quote" />
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <input className={smallInput} value={f.stake} onChange={(e) => set("stake", e.target.value)} placeholder="Einsatz" />
            </div>
          </div>
        )}

        {/* Legs editor */}
        {legs.length > 0 && (
          <div>
            <p className="text-[10px] uppercase tracking-widest text-zinc-500 mb-2">Beine ({legs.length})</p>
            <div className="space-y-3">
              {legs.map((leg, li) => (
                <div key={li} data-testid={`edit-leg-${li}`} className="rounded-xl border border-elevated bg-void p-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <input className={smallInput} value={leg.match} onChange={(e) => setLeg(li, { match: e.target.value })} placeholder="Heim – Auswärts" />
                    <button type="button" onClick={() => removeLeg(li)} data-testid={`edit-remove-leg-${li}`} title="Bein entfernen"
                      className="shrink-0 p-2 rounded-lg text-zinc-500 hover:text-lost hover:bg-lost/15 transition-colors">
                      <Trash2 size={15} />
                    </button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <input className={smallInput} value={leg.kickoff} onChange={(e) => setLeg(li, { kickoff: e.target.value })} placeholder="Anstoß" />
                    <input className={smallInput} value={leg.league} onChange={(e) => setLeg(li, { league: e.target.value })} placeholder="Liga" />
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <select data-testid={`edit-leg-status-${li}`} value={leg.status} onChange={(e) => setLeg(li, { status: e.target.value })}
                      className={`${smallInput} w-auto`}>
                      {LEG_STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
                    </select>
                    <button type="button" onClick={() => setLeg(li, { banker: !leg.banker })} data-testid={`edit-leg-banker-${li}`}
                      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-black uppercase tracking-wide transition-colors ${leg.banker ? "bg-cyan-400 text-black" : "border border-cyan-400/50 text-cyan-300 hover:bg-cyan-400/15"}`}>
                      <ShieldCheck size={12} /> Banker
                    </button>
                  </div>
                  <div className="space-y-1.5">
                    {leg.selections.map((sel, si) => (
                      <div key={si} className="flex items-center gap-2">
                        <input data-testid={`edit-leg-${li}-sel-${si}`} className={smallInput} value={sel} onChange={(e) => setSel(li, si, e.target.value)} placeholder="Auswahl (z.B. Über 1.5 Tore)" />
                        <input className={`${smallInput} w-20`} value={(leg.sel_odds || [])[si] || ""} onChange={(e) => setSelOdd(li, si, e.target.value)} placeholder="Quote" />
                        <button type="button" onClick={() => removeSel(li, si)} data-testid={`edit-leg-${li}-removesel-${si}`} title="Auswahl streichen"
                          className="shrink-0 p-1.5 rounded-lg text-zinc-500 hover:text-lost hover:bg-lost/15 transition-colors">
                          <X size={14} />
                        </button>
                      </div>
                    ))}
                    <button type="button" onClick={() => addSel(li)} data-testid={`edit-leg-${li}-addsel`}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-volt hover:text-volt-hover transition-colors">
                      <Plus size={13} /> Auswahl hinzufügen
                    </button>
                  </div>
                </div>
              ))}
            </div>
            <div className="grid grid-cols-2 gap-2 mt-3">
              <input data-testid="edit-total-odds" className={smallInput} value={f.odds} onChange={(e) => set("odds", e.target.value)} placeholder="Gesamtquote" />
              <input className={smallInput} value={f.stake} onChange={(e) => set("stake", e.target.value)} placeholder="Einsatz" />
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2 mt-5 pt-4 border-t border-elevated">
        <button onClick={onClose} className="flex-1 rounded-lg border border-elevated py-2.5 text-sm font-semibold text-zinc-300 hover:text-white hover:border-zinc-500 transition-colors">
          Abbrechen
        </button>
        <button onClick={save} disabled={saving} data-testid="admin-slip-save"
          className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-volt text-void py-2.5 text-sm font-bold hover:bg-volt-hover active:scale-95 transition-all disabled:opacity-50">
          <Save size={16} /> {saving ? "Speichern…" : "Speichern"}
        </button>
      </div>
    </Modal>
  );
}
