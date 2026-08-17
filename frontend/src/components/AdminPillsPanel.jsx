import React, { useEffect, useState } from "react";
import api from "../api";
import { toast } from "sonner";
import { Check, X, ExternalLink, Inbox } from "lucide-react";

// Admin: Freigabe der von Käufern eingereichten Pillen-Links.
export default function AdminPillsPanel() {
  const [pending, setPending] = useState([]);
  const [open, setOpen] = useState(false);

  const load = () => api.get("/admin/pills/pending").then((r) => setPending(r.data || [])).catch(() => {});
  useEffect(() => { load(); }, []);

  const act = async (id, action) => {
    try {
      await api.post(`/admin/pills/${id}/${action}`);
      toast.success(action === "approve" ? "Link freigegeben" : "Link abgelehnt");
      load();
    } catch { toast.error("Aktion fehlgeschlagen"); }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 mt-2" data-testid="admin-pills-panel">
      <button onClick={() => setOpen((o) => !o)} data-testid="admin-pills-toggle"
        className="w-full flex items-center justify-between rounded-xl border border-volt/30 bg-volt/5 px-4 py-2.5 text-left">
        <span className="inline-flex items-center gap-2 font-black text-volt text-sm">
          <Inbox size={16} /> Pillen-Freigaben
          {pending.length > 0 && <span className="ml-1 rounded-full bg-red-600 text-white text-[10px] px-2 py-0.5">{pending.length}</span>}
        </span>
        <span className="text-zinc-400 text-xs">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          {pending.length === 0 && <div className="text-xs text-zinc-500 px-2 py-3">Keine offenen Freigaben.</div>}
          {pending.map((p) => (
            <div key={p.id} data-testid={`admin-pill-${p.id}`} className="rounded-xl border border-elevated bg-surface p-3 flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm font-black text-white">
                  {p.label} <span className="text-zinc-500 font-normal">· {p.username || "—"}</span>
                </div>
                <a href={p.pending_link} target="_blank" rel="noopener noreferrer"
                  className="text-xs text-volt inline-flex items-center gap-1 truncate max-w-full">
                  <ExternalLink size={12} /> {p.pending_link || "(kein Link)"}
                </a>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button onClick={() => act(p.id, "approve")} data-testid={`approve-pill-${p.id}`}
                  className="grid place-items-center w-9 h-9 rounded-full bg-[#22c55e] text-black hover:brightness-110 active:scale-95"><Check size={18} /></button>
                <button onClick={() => act(p.id, "reject")} data-testid={`reject-pill-${p.id}`}
                  className="grid place-items-center w-9 h-9 rounded-full bg-red-600 text-white hover:brightness-110 active:scale-95"><X size={18} /></button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
