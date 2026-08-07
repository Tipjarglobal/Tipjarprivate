import React, { useState, useRef } from "react";
import { Radar, Loader2, Upload, CheckCircle2 } from "lucide-react";
import Modal from "./Modal";
import api, { apiErr } from "../api";
import { toast } from "sonner";

// Admin panel: feed a SILENT scout's (Instagram @thatsfootball90x → "Spica") betslip
// screenshots. OCR reads the picks → hidden, Master-learning tip. Never shown publicly.
export default function ScoutFeedPanel({ open, onClose }) {
  const [busy, setBusy] = useState(false);
  const [last, setLast] = useState(null);
  const inputRef = useRef(null);

  const onFiles = async (fileList) => {
    const files = Array.from(fileList || []).slice(0, 6);
    if (!files.length) return;
    setBusy(true);
    setLast(null);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      fd.append("handle", "thatsfootball90x");
      const { data } = await api.post("/admin/scout/ingest", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (data.ok === false) {
        toast.error(data.reason || "Kein Pick erkannt");
      } else {
        toast.success(`${data.bot}: Pick gespeichert (${data.legs} Legs)`);
        setLast(data);
      }
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <Modal open={open} onClose={onClose} title="Scout füttern — @thatsfootball90x" maxWidth="max-w-lg" testId="admin-scout-feed">
      <div className="space-y-4" data-testid="admin-scout-feed-panel">
        <p className="text-xs text-zinc-400 leading-snug">
          Lade Screenshot(s) von Spicas Instagram-Scheinen hoch. Die OCR liest die Picks
          automatisch → sie werden <b>versteckt</b> gespeichert (nie öffentlich) und der
          <b> Master lernt</b> aus ihrem Ergebnis. Bis zu 6 Bilder pro Upload.
        </p>

        <button
          data-testid="scout-upload-btn"
          onClick={() => inputRef.current?.click()}
          disabled={busy}
          className="w-full flex flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-emerald-500/50 bg-emerald-500/5 py-10 text-emerald-300 hover:bg-emerald-500/10 active:scale-[0.99] transition-all disabled:opacity-50">
          {busy ? <Loader2 className="animate-spin" size={26} /> : <Upload size={26} />}
          <span className="text-sm font-bold">{busy ? "OCR liest den Schein…" : "Schein-Screenshot(s) wählen"}</span>
          <span className="text-[11px] text-zinc-500">PNG / JPG · Vision-OCR kann ein paar Sekunden dauern</span>
        </button>
        <input ref={inputRef} type="file" accept="image/*" multiple hidden
          data-testid="scout-file-input"
          onChange={(e) => onFiles(e.target.files)} />

        {last && (
          <div data-testid="scout-last-result" className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-3 py-3 text-sm text-emerald-200">
            <div className="flex items-center gap-2 font-bold"><CheckCircle2 size={16} /> Gespeichert für Master-Lernen</div>
            <div className="text-xs text-emerald-300/80 mt-1">
              {last.match || "Match erkannt"} · {last.market || "Markt erkannt"} · {last.legs} Legs
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
