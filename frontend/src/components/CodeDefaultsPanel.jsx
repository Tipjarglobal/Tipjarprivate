import React, { useEffect, useState, useCallback } from "react";
import { X, Plus, Trash2, Check, Loader2, Wand2, Layers, Lock } from "lucide-react";
import { toast } from "sonner";
import api from "../api";

const T = {
  de: {
    title: "Code-Defaults", sub: "Pro Code temporär experimentieren, dann den wahren Default einwurzeln.",
    empty: "Noch keine Codes aktiv.", games: "Spiele", temp: "Temporär (experimentell)",
    perm: "Permanent (final)", tempHint: "Wird auf alle Spiele mit diesem Code angewendet. Frei wechselbar.",
    permHint: "Einwurzeln = gilt endgültig für alle Spiele mit diesem Code und wird gelockt.",
    active: "Aktiv", activate: "Aktivieren", nobet: "No Bet", pickPh: "Pick (z.B. Team gewinnt 6 Ecken)",
    notePh: "Notiz (optional)", addOpt: "Option speichern", root: "Einwurzeln", locked: "Eingewurzelt",
    clearPerm: "Permanent entfernen", noOpts: "Keine Optionen — füge eine hinzu.", close: "Schließen",
    saved: "Gespeichert", done: "Erledigt", fail: "Fehlgeschlagen",
  },
  en: {
    title: "Code defaults", sub: "Experiment per code, then root the true default.",
    empty: "No active codes yet.", games: "games", temp: "Temporary (experimental)",
    perm: "Permanent (final)", tempHint: "Applied to every game with this code. Switch freely.",
    permHint: "Root = becomes the final default for every game with this code and locks them.",
    active: "Active", activate: "Activate", nobet: "No Bet", pickPh: "Pick (e.g. team wins 6 corners)",
    notePh: "Note (optional)", addOpt: "Save option", root: "Root", locked: "Rooted",
    clearPerm: "Remove permanent", noOpts: "No options — add one.", close: "Close",
    saved: "Saved", done: "Done", fail: "Failed",
  },
  el: {
    title: "Code defaults", sub: "Πειραματίσου ανά κωδικό, μετά ρίζωσε το αληθινό default.",
    empty: "Κανένας ενεργός κωδικός.", games: "παιχνίδια", temp: "Προσωρινό (πειραματικό)",
    perm: "Μόνιμο (τελικό)", tempHint: "Εφαρμόζεται σε όλα τα παιχνίδια με αυτόν τον κωδικό. Αλλάζει ελεύθερα.",
    permHint: "Ρίζωμα = γίνεται το τελικό default για όλα τα παιχνίδια με αυτόν τον κωδικό και κλειδώνει.",
    active: "Ενεργό", activate: "Ενεργοποίηση", nobet: "No Bet", pickPh: "Pick (π.χ. ομάδα κερδίζει 6 κόρνερ)",
    notePh: "Σημείωση (προαιρετικό)", addOpt: "Αποθήκευση", root: "Ρίζωμα", locked: "Ρίζωσε",
    clearPerm: "Αφαίρεση μόνιμου", noOpts: "Καμία επιλογή — πρόσθεσε μία.", close: "Κλείσιμο",
    saved: "Αποθηκεύτηκε", done: "Έγινε", fail: "Απέτυχε",
  },
};

const INP = "w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-xs text-white placeholder-zinc-500 focus:border-fuchsia-500 outline-none";

function optLabel(o, fl) {
  if (o.no_bet) return fl.nobet;
  return o.our_market || fl.pickPh;
}

export default function CodeDefaultsPanel({ open, onClose, lang = "de" }) {
  const fl = T[lang] || T.de;
  const [defs, setDefs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [forms, setForms] = useState({}); // per-key add-option form
  const [perms, setPerms] = useState({}); // per-key permanent form

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/code-reading/defaults");
      setDefs(data.defaults || []);
      const p = {};
      (data.defaults || []).forEach((d) => {
        const pm = d.permanent || {};
        p[d.key] = { our_market: pm.our_market || "", no_bet: !!pm.no_bet, note: pm.note || "" };
      });
      setPerms(p);
    } catch { toast.error(fl.fail); } finally { setLoading(false); }
  }, [fl.fail]);

  useEffect(() => { if (open) load(); }, [open, load]);

  if (!open) return null;

  const f = (k) => forms[k] || { our_market: "", no_bet: false, note: "" };
  const setF = (k, patch) => setForms((s) => ({ ...s, [k]: { ...f(k), ...patch } }));
  const setP = (k, patch) => setPerms((s) => ({ ...s, [k]: { ...(s[k] || { our_market: "", no_bet: false, note: "" }), ...patch } }));

  const addOption = async (d, activate) => {
    const form = f(d.key);
    if (!form.no_bet && !form.our_market.trim()) { toast.error(fl.pickPh); return; }
    setBusy(true);
    try {
      await api.post(`/admin/code-reading/defaults/${encodeURIComponent(d.key)}/option`, {
        code_market: d.code_market, our_market: form.our_market, no_bet: form.no_bet, note: form.note, activate,
      });
      setF(d.key, { our_market: "", no_bet: false, note: "" });
      toast.success(fl.saved + " ✓");
      await load();
    } catch { toast.error(fl.fail); } finally { setBusy(false); }
  };

  const activate = async (key, oid) => {
    setBusy(true);
    try {
      await api.post(`/admin/code-reading/defaults/${encodeURIComponent(key)}/activate`, { option_id: oid });
      toast.success(fl.done + " ✓"); await load();
    } catch { toast.error(fl.fail); } finally { setBusy(false); }
  };

  const delOption = async (key, oid) => {
    setBusy(true);
    try {
      await api.delete(`/admin/code-reading/defaults/${encodeURIComponent(key)}/option/${oid}`);
      await load();
    } catch { toast.error(fl.fail); } finally { setBusy(false); }
  };

  const rootPerm = async (d) => {
    const p = perms[d.key] || {};
    if (!p.no_bet && !(p.our_market || "").trim()) { toast.error(fl.pickPh); return; }
    setBusy(true);
    try {
      await api.post(`/admin/code-reading/defaults/${encodeURIComponent(d.key)}/permanent`, {
        code_market: d.code_market, our_market: p.our_market, no_bet: p.no_bet, note: p.note,
      });
      toast.success(fl.locked + " ✓"); await load();
    } catch { toast.error(fl.fail); } finally { setBusy(false); }
  };

  const clearPerm = async (key) => {
    setBusy(true);
    try {
      await api.delete(`/admin/code-reading/defaults/${encodeURIComponent(key)}/permanent`);
      toast.success(fl.done + " ✓"); await load();
    } catch { toast.error(fl.fail); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center bg-black/75 p-3 overflow-y-auto" data-testid="code-defaults-panel" onClick={onClose}>
      <div className="bg-void border border-zinc-700 rounded-2xl w-full max-w-2xl my-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between gap-2 p-4 border-b border-zinc-800 sticky top-0 bg-void rounded-t-2xl z-10">
          <div className="flex items-center gap-2">
            <Layers size={18} className="text-fuchsia-400" />
            <div>
              <h3 className="font-black text-white text-sm">{fl.title}</h3>
              <p className="text-[11px] text-zinc-400">{fl.sub}</p>
            </div>
          </div>
          <button onClick={onClose} data-testid="code-defaults-close" className="text-zinc-400 hover:text-white p-1"><X size={18} /></button>
        </div>

        <div className="p-4 space-y-4">
          {loading && <div className="flex justify-center py-8"><Loader2 className="animate-spin text-fuchsia-400" /></div>}
          {!loading && defs.length === 0 && <p className="text-center text-zinc-500 text-sm py-8">{fl.empty}</p>}

          {!loading && defs.map((d) => {
            const hasPerm = !!(d.permanent && (d.permanent.our_market || d.permanent.no_bet || d.permanent.note));
            const p = perms[d.key] || { our_market: "", no_bet: false, note: "" };
            const form = f(d.key);
            return (
              <div key={d.key} className="border border-zinc-800 rounded-xl p-3" data-testid={`code-default-${d.key}`}>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-bold text-white text-sm">{d.code_market}</span>
                  <span className="text-[10px] text-zinc-500">{d.count} {fl.games}</span>
                </div>

                {/* TEMPORARY */}
                <div className={`rounded-lg p-2.5 mb-2 ${hasPerm ? "opacity-50" : "bg-zinc-900/50"}`}>
                  <p className="text-[11px] font-black text-amber-300 uppercase tracking-wide mb-1">{fl.temp}</p>
                  <p className="text-[10px] text-zinc-500 mb-2">{fl.tempHint}</p>
                  <div className="space-y-1.5 mb-2">
                    {(d.options || []).length === 0 && <p className="text-[11px] text-zinc-600">{fl.noOpts}</p>}
                    {(d.options || []).map((o) => {
                      const isActive = d.active_id === o.id && !hasPerm;
                      return (
                        <div key={o.id} className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs ${isActive ? "bg-amber-500/15 border border-amber-500/40" : "bg-zinc-800/60"}`} data-testid={`code-default-opt-${o.id}`}>
                          <div className="flex-1 min-w-0">
                            <span className={`font-semibold ${o.no_bet ? "text-red-300" : "text-white"}`}>{optLabel(o, fl)}</span>
                            {o.note && <span className="text-zinc-500 block truncate text-[10px]">{o.note}</span>}
                          </div>
                          {isActive ? (
                            <span className="inline-flex items-center gap-1 text-[10px] font-black text-amber-300 uppercase"><Check size={12} />{fl.active}</span>
                          ) : (
                            <button disabled={busy || hasPerm} onClick={() => activate(d.key, o.id)} data-testid={`code-default-activate-${o.id}`}
                              className="text-[10px] font-bold text-amber-300 border border-amber-500/40 rounded-full px-2 py-0.5 hover:bg-amber-500/15 disabled:opacity-40">{fl.activate}</button>
                          )}
                          <button disabled={busy} onClick={() => delOption(d.key, o.id)} className="text-zinc-500 hover:text-red-400 disabled:opacity-40"><Trash2 size={13} /></button>
                        </div>
                      );
                    })}
                  </div>
                  {/* add option */}
                  <div className="flex flex-col gap-1.5">
                    <label className="flex items-center gap-2 text-[11px] text-zinc-300 cursor-pointer">
                      <input type="checkbox" checked={form.no_bet} data-testid={`code-default-nobet-${d.key}`}
                        onChange={(e) => setF(d.key, { no_bet: e.target.checked })} /> {fl.nobet}
                    </label>
                    {!form.no_bet && (
                      <input className={INP} placeholder={fl.pickPh} data-testid={`code-default-pick-${d.key}`}
                        value={form.our_market} onChange={(e) => setF(d.key, { our_market: e.target.value })} />
                    )}
                    <input className={INP} placeholder={fl.notePh}
                      value={form.note} onChange={(e) => setF(d.key, { note: e.target.value })} />
                    <div className="flex gap-2">
                      <button disabled={busy} onClick={() => addOption(d, false)} data-testid={`code-default-add-${d.key}`}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-zinc-300 border border-zinc-600 rounded-full px-3 py-1 hover:bg-zinc-700/40 disabled:opacity-40"><Plus size={13} />{fl.addOpt}</button>
                      <button disabled={busy} onClick={() => addOption(d, true)}
                        className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-300 border border-amber-500/40 rounded-full px-3 py-1 hover:bg-amber-500/15 disabled:opacity-40"><Check size={13} />{fl.activate}</button>
                    </div>
                  </div>
                </div>

                {/* PERMANENT */}
                <div className={`rounded-lg p-2.5 ${hasPerm ? "bg-fuchsia-500/10 border border-fuchsia-500/40" : "bg-zinc-900/50"}`}>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-[11px] font-black text-fuchsia-300 uppercase tracking-wide flex items-center gap-1">
                      {hasPerm && <Lock size={11} />}{fl.perm}{hasPerm && <span className="text-fuchsia-400">· {fl.locked}</span>}
                    </p>
                    {hasPerm && (
                      <button disabled={busy} onClick={() => clearPerm(d.key)} data-testid={`code-default-clearperm-${d.key}`}
                        className="text-[10px] text-zinc-400 hover:text-red-400">{fl.clearPerm}</button>
                    )}
                  </div>
                  <p className="text-[10px] text-zinc-500 mb-2">{fl.permHint}</p>
                  <div className="flex flex-col gap-1.5">
                    <label className="flex items-center gap-2 text-[11px] text-zinc-300 cursor-pointer">
                      <input type="checkbox" checked={p.no_bet} data-testid={`code-default-permnobet-${d.key}`}
                        onChange={(e) => setP(d.key, { no_bet: e.target.checked })} /> {fl.nobet}
                    </label>
                    {!p.no_bet && (
                      <input className={INP} placeholder={fl.pickPh} data-testid={`code-default-permpick-${d.key}`}
                        value={p.our_market} onChange={(e) => setP(d.key, { our_market: e.target.value })} />
                    )}
                    <input className={INP} placeholder={fl.notePh}
                      value={p.note} onChange={(e) => setP(d.key, { note: e.target.value })} />
                    <button disabled={busy} onClick={() => rootPerm(d)} data-testid={`code-default-root-${d.key}`}
                      className="inline-flex items-center justify-center gap-1.5 text-xs font-black text-void bg-fuchsia-500 rounded-full px-3 py-1.5 hover:bg-fuchsia-400 disabled:opacity-40">
                      {busy ? <Loader2 size={13} className="animate-spin" /> : <Wand2 size={13} />}{fl.root}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
