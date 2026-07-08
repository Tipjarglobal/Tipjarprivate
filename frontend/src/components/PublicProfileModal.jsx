import React, { useEffect, useState } from "react";
import Modal from "./Modal";
import api from "../api";
import { useI18n } from "../i18n";
import { toast } from "sonner";
import { Gift, Calendar, Trophy, TrendingUp, Coins, Flame, ShieldCheck } from "lucide-react";

export default function PublicProfileModal({ open, username, onClose, onGift, isAdmin }) {
  const { t } = useI18n();
  const [p, setP] = useState(null);
  const [loading, setLoading] = useState(false);
  const [grantAmt, setGrantAmt] = useState("");
  const [granting, setGranting] = useState(false);

  useEffect(() => {
    if (open && username) {
      setLoading(true);
      setP(null);
      api.get(`/users/public/${encodeURIComponent(username)}`)
        .then((r) => setP(r.data))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [open, username]);

  const since = p?.created_at
    ? new Date(p.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short" })
    : "—";

  const grant = async () => {
    const amt = parseInt(grantAmt, 10);
    if (!amt) return;
    setGranting(true);
    try {
      const { data } = await api.post("/admin/credits/grant", { username, amount: amt });
      toast.success(`+${data.granted} Credits → @${data.username} (neu: ${data.new_balance})`);
      setGrantAmt("");
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Gutschrift fehlgeschlagen");
    } finally {
      setGranting(false);
    }
  };

  const stats = [
    { icon: TrendingUp, label: t("profile.tips"), value: p?.tips_count ?? 0 },
    { icon: Trophy, label: t("profile.wins"), value: p?.wins_count ?? 0 },
    { icon: Coins, label: t("profile.received"), value: p?.received_credits ?? 0 },
  ];

  return (
    <Modal open={open} onClose={onClose} title="" maxWidth="max-w-sm" testId="public-profile-modal">
      <div className="text-center" data-testid="public-profile">
        <div className="w-20 h-20 rounded-full bg-volt text-void flex items-center justify-center text-3xl font-black mx-auto shadow-[0_0_24px_rgba(225,255,0,0.35)]">
          {username?.[0]?.toUpperCase() || "?"}
        </div>
        <h3 className="mt-3 text-xl font-black text-white" data-testid="profile-username">@{username}</h3>
        {p?.apex_flame && (
          <div data-testid="profile-apex-flame" className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-bell/15 border border-bell/40 px-3 py-1 text-xs font-black text-bell">
            <Flame size={14} /> {t("profile.apexFlame")}
          </div>
        )}
        <p className="text-sm text-zinc-400 flex items-center justify-center gap-1.5 mt-1">
          <Calendar size={13} /> {t("profile.memberSince")} {loading ? "…" : since}
        </p>

        <div className="grid grid-cols-3 gap-2 mt-5">
          {stats.map((s, i) => (
            <div key={i} className="rounded-xl bg-void border border-elevated py-3 px-1">
              <s.icon size={15} className="mx-auto text-volt" />
              <p className="font-mono font-black text-lg text-white mt-1">{s.value}</p>
              <p className="text-[9px] uppercase tracking-widest text-zinc-500 leading-tight">{s.label}</p>
            </div>
          ))}
        </div>

        <button
          onClick={() => onGift?.(username)}
          data-testid="profile-gift-btn"
          className="mt-5 w-full flex items-center justify-center gap-2 bg-volt text-void font-bold rounded-lg py-3 hover:bg-volt-hover active:scale-95 transition-all"
        >
          <Gift size={18} /> {t("profile.giftCredits")}
        </button>

        {isAdmin && (
          <div data-testid="admin-grant-block" className="mt-4 rounded-xl border border-volt/30 bg-void p-3 text-left">
            <p className="flex items-center gap-1.5 text-xs font-bold text-volt uppercase tracking-wider mb-2">
              <ShieldCheck size={13} /> Admin: Credits gutschreiben
            </p>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={grantAmt}
                onChange={(e) => setGrantAmt(e.target.value)}
                placeholder="z.B. 3"
                data-testid="admin-grant-input"
                className="flex-1 min-w-0 rounded-lg bg-surface border border-elevated text-white text-sm px-3 py-2 focus:outline-none focus:border-volt"
              />
              <button
                onClick={grant}
                disabled={granting || !parseInt(grantAmt, 10)}
                data-testid="admin-grant-btn"
                className="shrink-0 bg-volt text-void font-bold text-sm rounded-lg px-4 py-2 hover:bg-volt-hover active:scale-95 transition-all disabled:opacity-40"
              >
                {granting ? "…" : "Gutschreiben"}
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
