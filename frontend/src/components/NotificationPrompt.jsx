import React, { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BellRing, X, Zap } from "lucide-react";
import { toast } from "sonner";
import { useI18n } from "../i18n";
import { enablePushFull, supportsWebPush, isIos, isStandalonePwa } from "../pushClient";

const DISMISS_KEY = "tj_push_prompt_dismissed";

// Subtle, one-time nudge that slides up after the user has looked at their first
// picks — designed to lift the (currently low) push opt-in rate. Never shown if
// push is already on, if the user dismissed it before, or if the device can't do it.
export default function NotificationPrompt() {
  const { t } = useI18n();
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const eligible = () =>
      supportsWebPush() &&
      !(isIos() && !isStandalonePwa()) &&
      localStorage.getItem("tj_bell") !== "1" &&
      localStorage.getItem(DISMISS_KEY) !== "1" &&
      (!window.Notification || Notification.permission !== "denied");

    let timer = null;
    const onViewed = () => {
      if (!eligible()) return;
      timer = setTimeout(() => { if (eligible()) setShow(true); }, 2500);
      window.removeEventListener("tj-viewed-pick", onViewed);
    };
    window.addEventListener("tj-viewed-pick", onViewed);
    const onEnabled = () => setShow(false);
    window.addEventListener("tj-push-enabled", onEnabled);
    return () => {
      window.removeEventListener("tj-viewed-pick", onViewed);
      window.removeEventListener("tj-push-enabled", onEnabled);
      if (timer) clearTimeout(timer);
    };
  }, []);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, "1");
    setShow(false);
  };

  const enable = async () => {
    setBusy(true);
    try {
      const res = await enablePushFull();
      if (res.ok) {
        toast.success(t("push.prompt.done"));
        localStorage.setItem(DISMISS_KEY, "1");
        setShow(false);
      } else if (res.reason === "denied") {
        toast.error(t("bell.denied"));
        dismiss();
      } else {
        dismiss();
      }
    } catch {
      dismiss();
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
