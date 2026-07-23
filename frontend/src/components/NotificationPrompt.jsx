import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BellRing, X, Zap } from "lucide-react";
import { toast } from "sonner";
import { useI18n } from "../i18n";
import { enablePushFull, supportsWebPush, isIos, isStandalonePwa } from "../pushClient";
import { playCoin } from "../coinSound";

const SNOOZE_KEY = "tj_push_prompt_snooze"; // hide until this timestamp (ms)
const SNOOZE_LATER = 2 * 24 * 3600 * 1000;  // "later" → nudge again in 2 days
const SNOOZE_CLOSE = 7 * 24 * 3600 * 1000;  // "X"     → nudge again in 7 days

// Subtle nudge to lift the push opt-in rate. Shows after the user looks at their
// first pick, or (fallback) after ~25s on the page. "Later"/close only SNOOZE it
// (it returns later) instead of killing it forever — much better for conversion.
// Never shown if push is already on, the device can't do it, or permission is denied.
export default function NotificationPrompt() {
  const { t } = useI18n();
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let shownThisSession = false;
    const eligible = () =>
      supportsWebPush() &&
      !(isIos() && !isStandalonePwa()) &&
      localStorage.getItem("tj_bell") !== "1" &&
      (!window.Notification || Notification.permission !== "denied") &&
      Date.now() > (Number(localStorage.getItem(SNOOZE_KEY)) || 0);

    const reveal = () => {
      if (shownThisSession || !eligible()) return;
      shownThisSession = true;
      setShow(true);
      playCoin();
      try { navigator.vibrate && navigator.vibrate([30, 40, 30]); } catch { /* ignore */ }
    };

    let t1 = null;
    const onViewed = () => { t1 = setTimeout(reveal, 2500); window.removeEventListener("tj-viewed-pick", onViewed); };
    window.addEventListener("tj-viewed-pick", onViewed);
    // Fallback: even visitors who never open a pick get one gentle nudge.
    const t2 = setTimeout(reveal, 25000);
    const onEnabled = () => setShow(false);
    window.addEventListener("tj-push-enabled", onEnabled);
    return () => {
      window.removeEventListener("tj-viewed-pick", onViewed);
      window.removeEventListener("tj-push-enabled", onEnabled);
      if (t1) clearTimeout(t1);
      clearTimeout(t2);
    };
  }, []);

  const snooze = (ms) => {
    localStorage.setItem(SNOOZE_KEY, String(Date.now() + ms));
    setShow(false);
  };
  const dismiss = () => snooze(SNOOZE_CLOSE);

  const enable = async () => {
    setBusy(true);
    try {
      const res = await enablePushFull();
      if (res.ok) {
        toast.success(t("push.prompt.done"));
        localStorage.setItem("tj_bell", "1");
        setShow(false);
      } else if (res.reason === "denied") {
        toast.error(t("bell.denied"));
        snooze(SNOOZE_CLOSE);
      } else {
        snooze(SNOOZE_LATER);
      }
    } catch {
      snooze(SNOOZE_LATER);
    } finally {
      setBusy(false);
    }
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          data-testid="push-prompt"
          initial={{ opacity: 0, y: 60 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 60 }}
          transition={{ type: "spring", stiffness: 320, damping: 28 }}
          className="fixed bottom-4 left-4 right-4 z-[60] mx-auto max-w-md rounded-2xl border border-bell/40 bg-surface/95 backdrop-blur-xl p-4 shadow-2xl"
        >
          <button
            onClick={dismiss}
            data-testid="push-prompt-dismiss"
            aria-label="close"
            className="absolute right-2.5 top-2.5 text-zinc-500 hover:text-white transition-colors"
          >
            <X size={16} />
          </button>
          <div className="flex items-start gap-3 pr-5">
            <div className="mt-0.5 shrink-0 rounded-full bg-bell/15 p-2">
              <BellRing size={18} className="text-bell" />
            </div>
            <div className="min-w-0">
              <p className="font-heading font-black text-sm text-white">{t("push.prompt.title")}</p>
              <p className="text-xs text-zinc-400 mt-0.5 leading-snug">{t("push.prompt.body")}</p>
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={enable}
                  disabled={busy}
                  data-testid="push-prompt-enable"
                  className="inline-flex items-center gap-1.5 rounded-full bg-bell px-4 py-2 text-xs font-bold text-white shadow-[0_0_20px_rgba(255,30,86,0.45)] transition-transform active:scale-95 disabled:opacity-60"
                >
                  <Zap size={13} /> {busy ? "…" : t("push.prompt.cta")}
                </button>
                <button
                  onClick={dismiss}
                  data-testid="push-prompt-later"
                  className="rounded-full px-3 py-2 text-xs font-semibold text-zinc-400 hover:text-white transition-colors"
                >
                  {t("push.prompt.later")}
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
