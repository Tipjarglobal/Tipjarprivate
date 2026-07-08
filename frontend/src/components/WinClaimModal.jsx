import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Upload, Trophy, Coins, Radio, Users, Loader2, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import api, { apiErr } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";

const TYPES = [
  { key: "played", icon: Users, tid: "win-type-played" },
  { key: "posted", icon: Trophy, tid: "win-type-posted" },
  { key: "live", icon: Radio, tid: "win-type-live" },
];

export default function WinClaimModal({ open, onClose, requireLogin, onClaimed, onViewBestWins }) {
  const { t } = useI18n();
  const { user, setUser } = useAuth();
  const [type, setType] = useState("played");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [liveFiles, setLiveFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [mine, setMine] = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open && user) {
      api.get("/wins/mine").then(({ data }) => setMine(data)).catch(() => setMine({ claims: [], total_credits: 0 }));
    }
  }, [open, user]);

  if (!open) return null;
  if (!user) {
    requireLogin?.();
    return null;
  }

  const refreshMine = () => api.get("/wins/mine").then(({ data }) => setMine(data)).catch(() => {});

  const pick = (f) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  const pickLive = (fileList) => {
    const arr = Array.from(fileList || []).slice(0, 4);
    setLiveFiles(arr);
  };

  const submit = async () => {
    const isLive = type === "live";
    if (isLive ? liveFiles.length === 0 : !file) {
      toast.error(t("win.needfile"));
      return;
    }
    setLoading(true);
    try {
      const fd = new FormData();
      if (isLive) {
        liveFiles.forEach((f) => fd.append("files", f));
      } else {
        fd.append("file", file);
      }
      fd.append("type", type);
      const { data } = await api.post("/wins/claim", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (data.user) setUser(data.user);
      toast.success(`${t("win.success")} +${data.credits_awarded} ${t("wallet.credits")} 🎉`);
      onClaimed?.();
      refreshMine();
      setFile(null);
      setPreview(null);
      setLiveFiles([]);
    } catch (e) {
      toast.error(apiErr(e, t("win.failed")));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
        className="fixed inset-0 z-[110] bg-black/80 backdrop-blur-sm flex items-center justify-center p-4"
        onClick={onClose}
        data-testid="win-claim-modal"
      >
        <motion.div
          initial={{ scale: 0.94, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.94, y: 20 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-lg rounded-3xl bg-surface border border-elevated p-6 sm:p-8 max-h-[92vh] overflow-y-auto"
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="inline-flex items-center gap-2 text-volt font-bold text-xs uppercase tracking-[0.15em]">
                <Coins size={14} /> {t("win.earn")}
              </div>
              <h3 className="font-heading text-2xl font-black text-white mt-2">{t("win.title")}</h3>
              <p className="text-sm text-zinc-400 mt-1">{t("win.subtitle")}</p>
            </div>
            <button onClick={onClose} data-testid="win-claim-close"
              className="rounded-full p-2 text-zinc-400 hover:text-white hover:bg-elevated active:scale-90 transition-all">
              <X size={20} />
            </button>
          </div>

          <div className="grid grid-cols-3 gap-2 mt-6">
            {TYPES.map(({ key, icon: Icon, tid }) => (
              <button
                key={key} data-testid={tid} onClick={() => setType(key)}
                className={`flex flex-col items-center gap-1.5 rounded-2xl border px-2 py-3 text-center transition-all ${
                  type === key ? "border-volt bg-volt/10 text-white" : "border-elevated text-zinc-400 hover:text-white"
                }`}
              >
                <Icon size={18} className={type === key ? "text-volt" : ""} />
                <span className="text-xs font-bold leading-tight">{t(`win.type.${key}`)}</span>
              </button>
            ))}
          </div>
          <p className="text-xs text-zinc-500 mt-2 leading-snug" data-testid="win-type-desc">
            {t(`win.type.${type}.desc`)}
          </p>

          {type === "live" && (
            <p className="text-xs text-cyan-300 mt-2 leading-snug" data-testid="win-live-hint">
              {t("win.live.multi")}
            </p>
          )}

          {type === "live" ? (
            <>
              <input ref={inputRef} type="file" accept="image/*" multiple className="hidden"
                data-testid="win-file-input-live"
                onChange={(e) => pickLive(e.target.files)} />
              <button
                onClick={() => inputRef.current?.click()}
                data-testid="win-upload-btn"
                className="mt-4 w-full rounded-2xl border-2 border-dashed border-elevated hover:border-volt/60 transition-colors p-6 flex flex-col items-center gap-2 text-zinc-400"
              >
                {liveFiles.length > 0 ? (
                  <div className="grid grid-cols-2 gap-2">
                    {liveFiles.map((f, i) => (
                      <img key={i} src={URL.createObjectURL(f)} alt={`live-${i}`} className="max-h-24 rounded-lg object-contain" />
                    ))}
                  </div>
                ) : (
                  <>
                    <Upload size={26} className="text-volt" />
                    <span className="text-sm font-semibold">{t("win.upload")}</span>
                    <span className="text-xs text-zinc-600">{t("submit.dropHint")}</span>
                  </>
                )}
              </button>
              {liveFiles.length > 0 && (
                <p className="text-xs text-zinc-500 mt-1 text-center">{liveFiles.length}/4</p>
              )}
            </>
          ) : (
            <>
              <input ref={inputRef} type="file" accept="image/*" className="hidden"
                data-testid="win-file-input"
                onChange={(e) => pick(e.target.files?.[0])} />
              <button
                onClick={() => inputRef.current?.click()}
                data-testid="win-upload-btn"
                className="mt-4 w-full rounded-2xl border-2 border-dashed border-elevated hover:border-volt/60 transition-colors p-6 flex flex-col items-center gap-2 text-zinc-400"
              >
                {preview ? (
                  <img src={preview} alt="slip" className="max-h-52 rounded-xl object-contain" />
                ) : (
                  <>
                    <Upload size={26} className="text-volt" />
                    <span className="text-sm font-semibold">{t("win.upload")}</span>
                    <span className="text-xs text-zinc-600">{t("submit.dropHint")}</span>
                  </>
                )}
              </button>
            </>
          )}

          <button
            onClick={submit} disabled={loading || (type === "live" ? liveFiles.length === 0 : !file)}
            data-testid="win-submit-btn"
            className="mt-5 w-full flex items-center justify-center gap-2 rounded-full bg-volt text-void font-bold px-6 py-3.5 hover:bg-volt-hover active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? <><Loader2 size={18} className="animate-spin" /> {t("submit.analyzing")}</> : <><Coins size={18} /> {t("win.submit")}</>}
          </button>
          <p className="text-[11px] text-zinc-600 mt-3 text-center leading-snug">{t("win.rules")}</p>

          <button
            onClick={() => { onViewBestWins?.(); onClose?.(); }}
            data-testid="win-bestwins-btn"
            className="mt-4 w-full flex items-center justify-center gap-2 rounded-full border border-volt/40 text-volt font-bold px-6 py-3 hover:bg-volt/10 active:scale-95 transition-all"
          >
            <Trophy size={16} /> {t("win.bestwins")}
          </button>
          <p className="text-[11px] text-zinc-500 mt-2 text-center leading-snug">{t("win.stored")}</p>

          {mine && mine.claims && mine.claims.length > 0 && (
            <div className="mt-6 border-t border-elevated pt-4" data-testid="win-mine-list">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-bold text-white">{t("win.mine")}</h4>
                <span className="text-xs text-volt font-bold">+{mine.total_credits} {t("win.mine.credits")}</span>
              </div>
              <div className="space-y-2">
                {mine.claims.map((c) => (
                  <div key={c.id} className="flex items-center justify-between rounded-xl bg-void border border-elevated px-3 py-2 text-sm">
                    <span className="inline-flex items-center gap-1.5 text-emerald-400 font-semibold">
                      <CheckCircle2 size={14} /> {t(`win.type.${c.type}`)}
                    </span>
                    <span className="text-zinc-400 text-xs">{c.legs_count} Legs · @{c.total_odds?.toFixed(2)}</span>
                    <span className="text-volt font-bold">+{c.credits}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
