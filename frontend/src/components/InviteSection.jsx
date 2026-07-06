import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { UserPlus, Copy, Check, Users } from "lucide-react";
import { FaWhatsapp, FaTelegram, FaXTwitter } from "react-icons/fa6";
import api from "../api";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";
import { toast } from "sonner";

export default function InviteSection() {
  const { t } = useI18n();
  const { user } = useAuth();
  const [stats, setStats] = useState({ members: 0, goal: 1000 });
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.get("/stats").then((r) => setStats(r.data)).catch(() => {});
  }, []);

  const inviteUrl = `${window.location.origin}${user ? `?ref=${encodeURIComponent(user.username)}` : ""}`;
  const shareText = `${t("invite.msg")} ${inviteUrl}`;
  const pct = Math.min(100, Math.round((stats.members / (stats.goal || 1000)) * 100));

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setCopied(true);
      toast.success(t("invite.copied"));
      setTimeout(() => setCopied(false), 2200);
    } catch {
      toast.error("Copy failed — long-press the link to copy.");
    }
  };

  const shares = [
    { icon: FaWhatsapp, label: "WhatsApp", href: `https://wa.me/?text=${encodeURIComponent(shareText)}`, color: "#25D366", testId: "share-whatsapp" },
    { icon: FaTelegram, label: "Telegram", href: `https://t.me/share/url?url=${encodeURIComponent(inviteUrl)}&text=${encodeURIComponent(t("invite.msg"))}`, color: "#229ED9", testId: "share-telegram" },
    { icon: FaXTwitter, label: "X", href: `https://twitter.com/intent/tweet?text=${encodeURIComponent(shareText)}`, color: "#ffffff", testId: "share-x" },
  ];

  const nativeShare = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: "TipJar", text: t("invite.msg"), url: inviteUrl }); } catch { /* cancelled */ }
    } else {
      copy();
    }
  };

  return (
    <section id="invite" className="max-w-5xl mx-auto px-4 sm:px-6 py-16 scroll-mt-20">
      <motion.div
        initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
        data-testid="invite-section"
        className="relative overflow-hidden rounded-3xl border border-volt/30 p-8 md:p-12"
        style={{ background: "radial-gradient(120% 120% at 0% 0%, rgba(225,255,0,0.10), transparent 55%), #18181B" }}
      >
        <div className="grid lg:grid-cols-2 gap-8 items-center">
          <div>
            <span className="inline-flex items-center gap-2 rounded-full border border-volt/40 bg-volt/10 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-volt">
              <Users size={13} /> {t("invite.badge")}
            </span>
            <h2 className="font-heading text-3xl md:text-5xl font-black text-white tracking-tighter mt-4">{t("invite.title")}</h2>
            <p className="text-zinc-400 mt-3 leading-relaxed max-w-md">{t("invite.subtitle")}</p>

            {/* progress */}
            <div className="mt-6">
              <div className="flex items-end justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-widest text-zinc-500">{t("invite.goal")}</span>
                <span className="font-mono font-bold text-white"><span className="text-volt" data-testid="member-count">{stats.members}</span> / {stats.goal}</span>
              </div>
              <div className="h-3 rounded-full bg-void border border-elevated overflow-hidden">
                <motion.div initial={{ width: 0 }} whileInView={{ width: `${pct}%` }} viewport={{ once: true }} transition={{ duration: 1 }}
                  className="h-full rounded-full" style={{ background: "linear-gradient(90deg,#00FF94,#E1FF00)" }} />
              </div>
              <p className="text-xs text-zinc-500 mt-1.5 font-mono">{pct}% · {Math.max(0, stats.goal - stats.members)} {t("invite.members")} to go</p>
            </div>
          </div>

          <div className="rounded-2xl bg-void border border-elevated p-5">
            <label className="text-[10px] uppercase tracking-widest text-zinc-500">{t("invite.copy")}</label>
            <div className="flex gap-2 mt-2">
              <input readOnly value={inviteUrl} data-testid="invite-link"
                className="flex-1 bg-surface border border-elevated rounded-lg px-3 py-2.5 text-sm text-white font-mono truncate focus:outline-none" />
              <button data-testid="copy-invite" onClick={copy}
                className="shrink-0 rounded-lg bg-volt text-void font-bold px-4 hover:bg-volt-hover active:scale-95 transition-all flex items-center gap-1.5">
                {copied ? <Check size={16} /> : <Copy size={16} />}
              </button>
            </div>

            <p className="text-[10px] uppercase tracking-widest text-zinc-500 mt-5 mb-2">{t("invite.share")}</p>
            <div className="flex gap-2">
              {shares.map((s) => (
                <a key={s.label} href={s.href} target="_blank" rel="noopener noreferrer" data-testid={s.testId}
                  className="flex-1 flex items-center justify-center gap-2 rounded-lg border border-elevated py-3 text-sm font-semibold text-white hover:border-volt/60 hover:-translate-y-0.5 transition-all">
                  <s.icon size={18} style={{ color: s.color }} /> <span className="hidden sm:inline">{s.label}</span>
                </a>
              ))}
            </div>

            <button data-testid="invite-native-share" onClick={nativeShare}
              className="w-full mt-3 flex items-center justify-center gap-2 rounded-lg bg-volt/10 border border-volt/30 text-volt font-bold py-3 hover:bg-volt/20 active:scale-95 transition-all">
              <UserPlus size={18} /> {t("invite.title")}
            </button>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
