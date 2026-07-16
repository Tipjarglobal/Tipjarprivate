import React, { useCallback, useEffect, useRef, useState } from "react";
import { Mail, Check, X, Star } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import api, { apiErr } from "../api";
import { useAuth } from "../auth";

export default function Mailbox() {
  const { user, setUser } = useAuth();
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [unread, setUnread] = useState(0);
  const [busy, setBusy] = useState(false);
  const ref = useRef();

  const load = useCallback(async () => {
    if (!user) return;
    try {
      const { data } = await api.get("/inbox");
      setMessages(data.messages || []);
      setUnread(data.unread || 0);
    } catch { /* ignore */ }
  }, [user]);

  useEffect(() => {
    if (!user) { setMessages([]); setUnread(0); return; }
    load();
    const iv = setInterval(load, 30000);
    return () => clearInterval(iv);
  }, [user, load]);

  useEffect(() => {
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const toggle = async () => {
    const next = !open;
    setOpen(next);
    if (next && unread > 0) {
      try {
        await api.post("/inbox/read-all");
        setUnread(0);
        setMessages((m) => m.map((x) => ({ ...x, read: true })));
      } catch { /* ignore */ }
    }
  };

  const accept = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/inbox/expert-accept");
      if (data.user) setUser(data.user);
      toast.success("Du bist jetzt Experte! 🎯");
      await load();
    } catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  const decline = async () => {
    setBusy(true);
    try { await api.post("/inbox/expert-decline"); await load(); }
    catch (e) { toast.error(apiErr(e)); } finally { setBusy(false); }
  };

  if (!user) return null;

  return (
    <div className="relative" ref={ref}>
      <button
        data-testid="mailbox-btn"
        onClick={toggle}
        title="Postfach"
        className="relative flex items-center justify-center w-9 h-9 rounded-full border border-elevated text-zinc-300 hover:border-volt/50 hover:text-volt transition-colors"
      >
        <Mail size={18} />
        {unread > 0 && (
          <span data-testid="mailbox-unread"
            className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] px-1 flex items-center justify-center rounded-full bg-red-600 text-white text-[10px] font-black leading-none border-2 border-void animate-pulse">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
            data-testid="mailbox-panel"
            className="absolute right-0 mt-2 z-[60] w-[22rem] max-w-[92vw] rounded-2xl bg-surface border border-elevated shadow-2xl overflow-hidden"
          >
            <div className="flex items-center gap-2 px-4 py-3 border-b border-elevated">
              <Mail size={16} className="text-volt" />
              <span className="font-heading font-black text-white text-sm uppercase tracking-wide">Postfach</span>
            </div>
            <div className="max-h-[70vh] overflow-y-auto p-2 space-y-2">
              {messages.length === 0 ? (
                <p className="text-zinc-500 text-sm py-8 text-center" data-testid="mailbox-empty">
                  Keine Nachrichten.
                </p>
              ) : messages.map((m) => (
                <div
                  key={m.id}
                  data-testid={`mailbox-msg-${m.id}`}
                  className={`rounded-xl border p-3 ${m.cta === "expert_invite"
                    ? "bg-orange-500/10 border-orange-500/40"
                    : "bg-void/60 border-white/5"}`}
                >
                  <div className="flex items-start gap-2">
                    {m.cta === "expert_invite" && <Star size={15} className="text-orange-400 mt-0.5 shrink-0" />}
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-bold text-white">{m.title}</p>
                      <p className="text-xs text-zinc-300 mt-1 leading-snug">{m.body}</p>
                      {m.cta === "expert_invite" && (
                        <div className="flex items-center gap-2 mt-3">
                          <button
                            data-testid="expert-accept-btn"
                            onClick={accept}
                            disabled={busy}
                            className="flex items-center gap-1.5 rounded-lg bg-orange-500 text-void font-bold text-xs px-3 py-1.5 hover:brightness-110 active:scale-95 transition-all disabled:opacity-50"
                          >
                            <Check size={13} /> Ja, Experte werden
                          </button>
                          <button
                            data-testid="expert-decline-btn"
                            onClick={decline}
                            disabled={busy}
                            className="flex items-center gap-1.5 rounded-lg bg-elevated text-zinc-300 font-bold text-xs px-3 py-1.5 hover:bg-white/10 active:scale-95 transition-all disabled:opacity-50"
                          >
                            <X size={13} /> Nein danke
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
