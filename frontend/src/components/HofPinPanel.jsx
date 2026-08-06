import React, { useEffect, useState } from "react";
import { Trophy, Loader2, Pin, PinOff } from "lucide-react";
import Modal from "./Modal";
import api, { apiErr } from "../api";
import { toast } from "sonner";

// Admin panel: pin a single won slip into the Hall of Fame as a one-off exception (e.g. a
// sub-3.00 combo while the HoF is still empty). Does NOT change the main HoF quote rule.
export default function HofPinPanel({ open, onClose }) {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/admin/wins/recent");
      setClaims(data.claims || []);
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (open) load(); }, [open]); // eslint-disable-line

  const toggle = async (c) => {
    const pinned = !!c.hof_force;
    setBusy(c.id);
    try {
      await api.post(`/admin/wins/${c.id}/${pinned ? "unpin" : "pin"}`);
      toast.success(pinned ? "Aus Hall of Fame entfernt" : "In Hall of Fame gepinnt");
      await load();
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setBusy("");
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Hall of Fame — Schein pinnen" maxWidth="max-w-2xl" testId="admin-hof-pin">
      <div className="space-y-3" data-testid="admin-hof-pin-panel">
        <p className="text-xs text-zinc-400 leading-snug">
          Ausnahme: Pinne einen gewonnenen Schein in die Hall of Fame, auch wenn er die
          Mindestquote (3.00) nicht erreicht. Die Hauptregel bleibt unverändert — nur der
          gepinnte Schein erscheint zusätzlich.
        </p>

        {loading ? (
          <div className="flex items-center justify-center py-10 text-zinc-400">
            <Loader2 className="animate-spin" size={20} />
          </div>
        ) : claims.length === 0 ? (
          <p className="text-sm text-zinc-500 py-8 text-center">Keine eingereichten Gewinn-Scheine gefunden.</p>
        ) : (
          <div className="space-y-2 max-h-[60vh] overflow-y-auto pr-1">
            {claims.map((c) => (
              <div key={c.id} data-testid={`hof-claim-${c.id}`}
                className="flex items-center justify-between gap-3 rounded-xl border border-elevated bg-black/20 px-3 py-2.5">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-bold text-white truncate">@{c.username}</span>
                    <span className="text-[11px] font-black text-amber-300">Quote {Number(c.total_odds).toFixed(2)}</span>
                    <span className="text-[10px] text-zinc-400">{c.legs_count} Legs · {c.type}</span>
                    {c.in_hof && (
                      <span className="text-[9px] font-black uppercase tracking-wide rounded-full bg-emerald-500/15 text-emerald-300 px-2 py-0.5">
                        in HoF
                      </span>
                    )}
                  </div>
                  <div className="text-[10px] text-zinc-500 truncate">
                    {(c.legs || []).map((l) => `${l.home}–${l.away}`).join(" · ") || c.id}
                  </div>
                </div>
                <button
                  data-testid={`hof-pin-toggle-${c.id}`}
                  onClick={() => toggle(c)}
                  disabled={busy === c.id}
                  className={`inline-flex items-center justify-center gap-1.5 shrink-0 rounded-full px-3 py-1.5 text-xs font-bold active:scale-95 transition-all disabled:opacity-50 ${
                    c.hof_force
                      ? "border border-[#E11D2A]/60 text-[#E11D2A] hover:bg-[#E11D2A]/10"
                      : "bg-amber-400 text-black hover:bg-amber-300"
                  }`}>
                  {busy === c.id ? <Loader2 className="animate-spin" size={13} /> : c.hof_force ? <PinOff size={13} /> : <Pin size={13} />}
                  {c.hof_force ? "Unpin" : "Pinnen"}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}
