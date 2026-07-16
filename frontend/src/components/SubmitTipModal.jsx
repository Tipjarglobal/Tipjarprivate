import React, { useState, useRef } from "react";
import Modal, { Field, inputCls, btnPrimary } from "./Modal";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, Sparkles, GraduationCap, ArrowRight, RefreshCw, HelpCircle } from "lucide-react";
import api, { apiErr } from "../api";
import StarRating from "./StarRating";
import { useI18n, formatSelection } from "../i18n";
import { useAuth } from "../auth";
import { toast } from "sonner";

async function compressImage(file, maxDim = 1600, quality = 0.85) {
  if (!file || !file.type?.startsWith("image/")) return file;
  try {
    const dataUrl = await new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res(r.result);
      r.onerror = rej;
      r.readAsDataURL(file);
    });
    const img = await new Promise((res, rej) => {
      const im = new Image();
      im.onload = () => res(im);
      im.onerror = rej;
      im.src = dataUrl;
    });
    const longest = Math.max(img.width, img.height);
    if (longest <= maxDim && file.size < 900000) return file;
    const scale = Math.min(1, maxDim / longest);
    const w = Math.round(img.width * scale);
    const h = Math.round(img.height * scale);
    const canvas = document.createElement("canvas");
    canvas.width = w;
    canvas.height = h;
    canvas.getContext("2d").drawImage(img, 0, 0, w, h);
    const blob = await new Promise((res) => canvas.toBlob(res, "image/jpeg", quality));
    if (!blob) return file;
    const name = (file.name || "slip").replace(/\.[^.]+$/, "") + ".jpg";
    return new File([blob], name, { type: "image/jpeg" });
  } catch {
    return file;
  }
}

const TUTORIAL = [
  { key: "bad", odds: "1.20", tone: "#FF1E56" },
  { key: "banker", odds: "1.45", tone: "#00FF94" },
  { key: "live", odds: "1.85", tone: "#E1FF00" },
];

export default function SubmitTipModal({ open, onClose, onPublished, requireLogin }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const [tab, setTab] = useState("upload");
  const [tutStep, setTutStep] = useState(0);
  const [files, setFiles] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [text, setText] = useState("");
  const [scanning, setScanning] = useState(false);
  const [detected, setDetected] = useState(null);
  const [selfStars, setSelfStars] = useState(0);
  const [publishing, setPublishing] = useState(false);
  const [clarify, setClarify] = useState(null);
  const inputRef = useRef();

  const reset = () => {
    setFiles([]); setPreviews([]); setText(""); setDetected(null); setSelfStars(0);
    setScanning(false); setPublishing(false); setTutStep(0); setTab("upload"); setClarify(null);
  };
  const close = () => { reset(); onClose(); };

  const pick = async (list) => {
    const incoming = Array.from(list || []);
    if (!incoming.length) return;
    const room = Math.max(0, 4 - files.length);
    const chosen = incoming.slice(0, room);
    if (!chosen.length) { toast.error("Maximal 4 Bilder."); return; }
    const optimized = await Promise.all(chosen.map((f) => compressImage(f)));
    setFiles((f) => [...f, ...optimized].slice(0, 4));
    setPreviews((p) => [...p, ...optimized.map((f) => URL.createObjectURL(f))].slice(0, 4));
    setDetected(null);
  };
  const removeAt = (i) => {
    setFiles((f) => f.filter((_, x) => x !== i));
    setPreviews((p) => p.filter((_, x) => x !== i));
    setDetected(null);
  };

  const scan = async () => {
    if (!user) { requireLogin(); return; }
    if (!files.length && !text.trim()) { toast.error("Add a screenshot or write your tip."); return; }
    setScanning(true);
    try {
      const fd = new FormData();
      files.forEach((f) => fd.append("files", f));
      fd.append("text", text);
      const { data } = await api.post("/tips/analyze", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setDetected(data);
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setScanning(false);
    }
  };

  const publish = async () => {
    if (!user) { requireLogin(); return; }
    if (!selfStars) { toast.error(t("submit.needStars")); return; }
    setPublishing(true);
    try {
      const { data } = await api.post("/tips", {
        raw_text: text,
        image_path: detected.image_path,
        image_paths: detected.image_paths,
        home_team: detected.home_team, away_team: detected.away_team,
        match_time: detected.match_time, country: detected.country,
        league: detected.league, market: detected.market, odds: detected.odds,
        ai_rating: detected.rating, ai_analysis: detected.analysis,
        legs: detected.legs, is_parlay: detected.is_parlay,
        stake: detected.stake, potential_return: detected.potential_return,
        self_rating: selfStars,
      });
      toast.success(t("submit.published"));
      onPublished && onPublished(data);
      if (data.needs_clarification) {
        toast.message(t("clarify.toast"));
        setClarify({ tipId: data.id, fields: data.clarification_fields || [] });
      } else {
        close();
      }
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setPublishing(false);
    }
  };

  const saveClarify = async (values) => {
    if (!clarify) return;
    setPublishing(true);
    try {
      await api.post(`/tips/${clarify.tipId}/clarify`, values);
      toast.success(t("clarify.saved"));
      onPublished && onPublished({});
      close();
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setPublishing(false);
    }
  };
  const skipClarify = () => close();

  const ex = TUTORIAL[tutStep];

  return (
    <Modal open={open} onClose={close} title={t("submit.title")} maxWidth="max-w-xl" testId="submit-modal">
      {clarify ? (
        <ClarifyPanel fields={clarify.fields} onSave={saveClarify} onSkip={skipClarify} saving={publishing} t={t} />
      ) : (
      <>
      {/* tabs */}
      <div className="flex gap-2 mb-5 p-1 bg-void rounded-xl border border-elevated">
        <button
          data-testid="submit-tab-upload"
          onClick={() => setTab("upload")}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-semibold transition-colors ${tab === "upload" ? "bg-volt text-void" : "text-zinc-400 hover:text-white"}`}
        >
          <Upload size={16} /> {t("submit.tab.upload")}
        </button>
        <button
          data-testid="submit-tab-tutorial"
          onClick={() => setTab("tutorial")}
          className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-sm font-semibold transition-colors ${tab === "tutorial" ? "bg-volt text-void" : "text-zinc-400 hover:text-white"}`}
        >
          <GraduationCap size={16} /> {t("submit.tab.tutorial")}
        </button>
      </div>

      {tab === "tutorial" ? (
        <div data-testid="tutorial-panel">
          <p className="text-sm text-zinc-400 mb-4">{t("submit.tut.intro")}</p>
          <AnimatePresence mode="wait">
            <motion.div
              key={tutStep}
              initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}
              className="rounded-xl border border-elevated bg-void p-5"
            >
              <span className="text-xs font-bold uppercase tracking-[0.2em]" style={{ color: ex.tone }}>{t(`submit.tut.${ex.key}.tag`)}</span>
              <h4 className="font-heading text-2xl font-black text-white mt-2">{t(`submit.tut.${ex.key}.title`)}</h4>
              <div className="flex items-center justify-between mt-3 rounded-lg bg-surface px-4 py-3">
                <span className="text-white font-semibold">{t(`submit.tut.${ex.key}.market`)}</span>
                <span className="font-mono font-bold text-lg text-volt">{ex.odds}</span>
              </div>
              <p className="text-sm text-zinc-400 mt-3 leading-relaxed">{t(`submit.tut.${ex.key}.note`)}</p>
            </motion.div>
          </AnimatePresence>
          <div className="flex items-center justify-between mt-4">
            <div className="flex gap-1.5">
              {TUTORIAL.map((_, i) => (
                <div key={i} className={`h-1.5 rounded-full transition-all ${i === tutStep ? "w-6 bg-volt" : "w-1.5 bg-elevated"}`} />
              ))}
            </div>
            {tutStep < TUTORIAL.length - 1 ? (
              <button data-testid="tutorial-next" onClick={() => setTutStep(tutStep + 1)} className="flex items-center gap-1.5 text-sm font-semibold text-white hover:text-volt transition-colors">
                {t("submit.tut.next")} <ArrowRight size={16} />
              </button>
            ) : (
              <button data-testid="tutorial-start" onClick={() => setTab("upload")} className="bg-volt text-void font-bold text-sm rounded-lg px-4 py-2 hover:bg-volt-hover active:scale-95 transition-all">
                {t("submit.tut.start")}
              </button>
            )}
          </div>
        </div>
      ) : (
        <div>
          {!detected && (
            <>
              <div
                data-testid="upload-dropzone"
                onClick={() => inputRef.current?.click()}
                onDragOver={(e) => e.preventDefault()}
                onDrop={(e) => { e.preventDefault(); pick(e.dataTransfer.files); }}
                className="relative cursor-pointer rounded-xl border-2 border-dashed border-elevated hover:border-volt/60 transition-colors bg-void p-6 text-center overflow-hidden"
              >
                {previews.length ? (
                  <div className="relative">
                    <div className="grid grid-cols-2 gap-2">
                      {previews.map((src, i) => (
                        <div key={i} className="relative rounded-lg overflow-hidden border border-elevated">
                          <img src={src} alt={`slip-${i}`} className="w-full h-28 object-cover" />
                          <button
                            type="button"
                            data-testid={`remove-image-${i}`}
                            onClick={(e) => { e.stopPropagation(); removeAt(i); }}
                            className="absolute top-1 right-1 bg-black/70 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs hover:bg-lost"
                          >✕</button>
                        </div>
                      ))}
                    </div>
                    <p className="text-[11px] text-zinc-500 mt-2">{previews.length}/4 {t("submit.imagesHint")}</p>
                    <AnimatePresence>
                      {scanning && (
                        <motion.div
                          initial={{ y: "-100%" }} animate={{ y: "100%" }}
                          transition={{ repeat: Infinity, duration: 1.3, ease: "linear" }}
                          className="absolute inset-x-0 h-1/3 pointer-events-none"
                          style={{ background: "linear-gradient(180deg, transparent, rgba(225,255,0,0.35), transparent)" }}
                        />
                      )}
                    </AnimatePresence>
                  </div>
                ) : (
                  <div className="py-6">
                    <Upload className="mx-auto text-zinc-500 mb-3" size={34} />
                    <p className="text-white font-semibold">{t("submit.drop")}</p>
                    <p className="text-xs text-zinc-500 mt-1">{t("submit.dropHint")}</p>
                    <p className="text-[11px] text-volt/70 mt-1">{t("submit.imagesHint")}</p>
                  </div>
                )}
                <input ref={inputRef} type="file" accept="image/*" multiple className="hidden" onChange={(e) => pick(e.target.files)} data-testid="upload-input" />
              </div>

              <Field label={t("submit.text")}>
                <textarea data-testid="tip-text" className={inputCls + " resize-none h-20"} placeholder={t("submit.textPh")} value={text} onChange={(e) => setText(e.target.value)} />
              </Field>

              <button data-testid="scan-button" onClick={scan} disabled={scanning} className={btnPrimary + " flex items-center justify-center gap-2"}>
                <Sparkles size={18} /> {scanning ? t("submit.analyzing") : t("submit.analyze")}
              </button>
            </>
          )}

          {detected && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} data-testid="detected-panel">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles size={16} className="text-volt" />
                <span className="text-xs font-bold uppercase tracking-[0.2em] text-volt">{t("submit.detected")}</span>
              </div>
              <div className="rounded-xl border border-elevated bg-void p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-zinc-500">{t("submit.teams")}</p>
                    <p className="text-white font-heading font-bold text-lg">
                      {detected.home_team || "—"} <span className="text-zinc-600">vs</span> {detected.away_team || "—"}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] uppercase tracking-widest text-zinc-500">{t("submit.airating")}</p>
                    <p className="font-mono font-black text-2xl text-volt text-glow-volt">{detected.rating}<span className="text-sm text-zinc-500">/10</span></p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <Detail label={t("submit.kickoff")} value={detected.match_time} />
                  <Detail label={t("submit.odds")} value={detected.odds} mono />
                  <Detail label={t("submit.country")} value={detected.country} />
                  <Detail label={t("submit.league")} value={detected.league} />
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-widest text-zinc-500">{t("submit.market")}</p>
                  <p className="text-white font-semibold">{detected.market || "—"}</p>
                </div>
                {detected.legs && detected.legs.length > 0 && (
                  <div className="space-y-2">
                    {detected.legs.map((leg, li) => (
                      <div key={li} className="rounded-lg bg-surface px-3 py-2">
                        <div className="flex items-center justify-between">
                          <span className="text-white font-semibold text-sm">{leg.match}</span>
                          {leg.kickoff && <span className="text-[10px] text-zinc-500 font-mono">{leg.kickoff}</span>}
                        </div>
                        {leg.league && <span className="text-[10px] text-volt/80 font-semibold uppercase tracking-wider">{leg.league}</span>}
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          {(leg.selections || []).map((s, si) => (
                            <span key={si} className="text-[11px] text-zinc-200 bg-elevated rounded px-2 py-0.5">{formatSelection(s, t)}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
                {detected.analysis && (
                  <div className="rounded-lg bg-surface px-3 py-2 text-sm text-zinc-300 border-l-2 border-volt">{detected.analysis}</div>
                )}
              </div>

              <div className="mt-4 rounded-xl border border-volt/30 bg-volt/5 p-4" data-testid="self-rating-block">
                <p className="text-sm font-bold text-white">{t("submit.rateTitle")}</p>
                <p className="text-xs text-zinc-400 mb-3">{t("submit.rateHint")}</p>
                <StarRating value={selfStars} onRate={setSelfStars} size={26} />
                {!selfStars && <p className="text-[11px] text-lost mt-2" data-testid="stars-required">{t("submit.needStars")}</p>}
              </div>

              <div className="flex gap-3 mt-4">
                <button data-testid="rescan-button" onClick={() => setDetected(null)} className="flex items-center justify-center gap-1.5 rounded-lg border border-elevated px-4 py-3 text-sm font-semibold text-zinc-300 hover:text-white hover:border-zinc-500 transition-colors">
                  <RefreshCw size={15} />
                </button>
                <button data-testid="publish-button" onClick={publish} disabled={publishing || !selfStars} className={btnPrimary + (!selfStars ? " opacity-50 cursor-not-allowed" : "")}>
                  {publishing ? t("common.loading") : t("submit.publish")}
                </button>
              </div>
            </motion.div>
          )}
        </div>
      )}
      </>
      )}
    </Modal>
  );
}

function ClarifyPanel({ fields, onSave, onSkip, saving, t }) {
  const [league, setLeague] = useState("");
  const [matchTime, setMatchTime] = useState("");
  const [home, setHome] = useState("");
  const [away, setAway] = useState("");
  const need = (k) => (fields || []).includes(k);
  return (
    <div data-testid="clarify-panel" className="space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-full bg-volt/15 flex items-center justify-center shrink-0">
          <HelpCircle size={18} className="text-volt" />
        </div>
        <div>
          <h4 className="font-heading font-black text-white text-lg">{t("clarify.title")}</h4>
          <p className="text-sm text-zinc-400">{t("clarify.intro")}</p>
        </div>
      </div>
      {need("teams") && (
        <div className="grid grid-cols-2 gap-3">
          <Field label={t("clarify.home")}>
            <input data-testid="clarify-home" value={home} onChange={(e) => setHome(e.target.value)} className={inputCls} placeholder="Blumenau SC" />
          </Field>
          <Field label={t("clarify.away")}>
            <input data-testid="clarify-away" value={away} onChange={(e) => setAway(e.target.value)} className={inputCls} placeholder="Metropolitano" />
          </Field>
        </div>
      )}
      {need("league") && (
        <Field label={t("clarify.league")}>
          <input data-testid="clarify-league" value={league} onChange={(e) => setLeague(e.target.value)} className={inputCls} placeholder="Brasileiro Série C" />
        </Field>
      )}
      {need("datetime") && (
        <Field label={t("clarify.datetime")}>
          <input data-testid="clarify-datetime" value={matchTime} onChange={(e) => setMatchTime(e.target.value)} className={inputCls} placeholder="TT/MM/JJJJ HH:MM" />
        </Field>
      )}
      <div className="flex gap-3 pt-1">
        <button data-testid="clarify-skip" onClick={onSkip} className="rounded-lg border border-elevated px-4 py-3 text-sm font-semibold text-zinc-400 hover:text-white transition-colors">
          {t("clarify.skip")}
        </button>
        <button
          data-testid="clarify-save"
          onClick={() => onSave({ league, match_time: matchTime, home_team: home, away_team: away })}
          disabled={saving}
          className={btnPrimary}
        >
          {saving ? t("common.loading") : t("clarify.save")}
        </button>
      </div>
    </div>
  );
}

function Detail({ label, value, mono }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-widest text-zinc-500">{label}</p>
      <p className={`text-white ${mono ? "font-mono text-volt" : "font-medium"}`}>{value || "—"}</p>
    </div>
  );
}
