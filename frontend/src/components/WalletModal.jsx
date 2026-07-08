import React, { useState, useEffect } from "react";
import Modal, { Field, inputCls, btnPrimary } from "./Modal";
import { CreditCard, Gift, Banknote, Check, AlertTriangle } from "lucide-react";
import api, { apiErr } from "../api";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";
import { toast } from "sonner";

const REDEEM_THRESHOLD = 10000;

export default function WalletModal({ open, onClose, initialTab, initialGiftTo }) {
  const { t } = useI18n();
  const { user, setUser } = useAuth();
  const [tab, setTab] = useState("buy");
  const [packages, setPackages] = useState({});
  const [giftTo, setGiftTo] = useState("");
  const [giftAmt, setGiftAmt] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      api.get("/credits/packages").then((r) => setPackages(r.data)).catch(() => {});
      setTab(initialTab || "buy");
      if (initialGiftTo) setGiftTo(initialGiftTo);
    }
  }, [open, initialTab, initialGiftTo]);

  const buy = async (pkgId) => {
    setBusy(true);
    try {
      toast.message(t("wallet.buying"));
      const { data } = await api.post("/credits/checkout", { package_id: pkgId, origin_url: window.location.origin });
      window.location.href = data.url;
    } catch (err) {
      toast.error(apiErr(err));
      setBusy(false);
    }
  };

  const gift = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/credits/gift", { to_username: giftTo.trim(), amount: parseInt(giftAmt, 10) });
      setUser(data.user);
      toast.success(`${t("wallet.gifted")} (${data.received} ${t("wallet.credits")})`);
      setGiftTo(""); setGiftAmt("");
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setBusy(false);
    }
  };

  const redeem = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/credits/redeem");
      setUser(data.user);
      toast.success(`${t("wallet.redeemOk")} (€${data.redemption.amount_eur})`);
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setBusy(false);
    }
  };

  const rc = user?.received_credits || 0;
  const pct = Math.min(100, (rc / REDEEM_THRESHOLD) * 100);

  return (
    <Modal open={open} onClose={onClose} title={t("wallet.title")} testId="wallet-modal">
      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="rounded-xl bg-void border border-elevated p-4">
          <p className="text-[10px] uppercase tracking-widest text-zinc-500">{t("wallet.balance")}</p>
          <p className="font-mono font-black text-3xl text-volt text-glow-volt" data-testid="wallet-balance">{user?.credits ?? 0}</p>
        </div>
        <div className="rounded-xl bg-void border border-elevated p-4">
          <p className="text-[10px] uppercase tracking-widest text-zinc-500">{t("wallet.received")}</p>
          <p className="font-mono font-black text-3xl text-won" data-testid="wallet-received">{rc}</p>
        </div>
      </div>

      <div className="flex gap-2 mb-5 p-1 bg-void rounded-xl border border-elevated">
        {[["buy", CreditCard, t("wallet.buy")], ["gift", Gift, t("wallet.gift")], ["redeem", Banknote, t("wallet.redeem")]].map(([k, Icon, label]) => (
          <button key={k} data-testid={`wallet-tab-${k}`} onClick={() => setTab(k)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-colors ${tab === k ? "bg-volt text-void" : "text-zinc-400 hover:text-white"}`}>
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      {tab === "buy" && (
        <div className="space-y-3" data-testid="buy-panel">
          {Object.entries(packages).map(([id, p]) => (
            <button key={id} data-testid={`buy-${id}`} onClick={() => buy(id)} disabled
              className="w-full flex items-center justify-between rounded-xl border border-elevated bg-void p-4 opacity-60 cursor-not-allowed transition-all">
              <div className="text-left">
                <p className="font-heading font-bold text-white text-lg">{p.label}</p>
                <p className="font-mono text-volt font-bold">{p.credits} {t("wallet.credits")}</p>
              </div>
              <span className="font-mono font-black text-xl text-white">€{p.price.toFixed(2)}</span>
            </button>
          ))}
          <div data-testid="buy-disabled-notice"
            className="flex items-start gap-2.5 rounded-xl border border-lost/50 bg-lost/10 p-4 text-lost">
            <AlertTriangle size={18} className="shrink-0 mt-0.5" />
            <p className="text-sm font-semibold leading-snug">{t("wallet.buyDisabled")}</p>
          </div>
          <div data-testid="credits-purpose-notice"
            className="flex items-start gap-2.5 rounded-xl border border-elevated bg-void p-4 text-zinc-400">
            <Gift size={18} className="shrink-0 mt-0.5 text-volt" />
            <p className="text-sm leading-snug">{t("wallet.creditsPurpose")}</p>
          </div>
        </div>
      )}

      {tab === "gift" && (
        <div data-testid="gift-panel">
          <Field label={t("wallet.giftTo")}>
            <input data-testid="gift-to" className={inputCls} value={giftTo} onChange={(e) => setGiftTo(e.target.value)} />
          </Field>
          <Field label={t("wallet.amount")}>
            <input data-testid="gift-amount" type="number" min="1" className={inputCls} value={giftAmt} onChange={(e) => setGiftAmt(e.target.value)} />
          </Field>
          <p className="text-xs text-zinc-500 mb-4">{t("wallet.fee")}</p>
          <button data-testid="gift-send" onClick={gift} disabled={busy || !giftTo || !giftAmt} className={btnPrimary}>{t("wallet.send")}</button>
        </div>
      )}

      {tab === "redeem" && (
        <div data-testid="redeem-panel">
          <p className="text-sm text-zinc-400 mb-3">{t("wallet.redeemInfo")}</p>
          <div className="h-3 rounded-full bg-void border border-elevated overflow-hidden mb-2">
            <div className="h-full bg-gradient-to-r from-won to-volt transition-all" style={{ width: `${pct}%` }} />
          </div>
          <p className="font-mono text-sm text-white mb-4">{rc} / {REDEEM_THRESHOLD}</p>
          <button data-testid="redeem-btn" onClick={redeem} disabled={busy || rc < REDEEM_THRESHOLD} className={btnPrimary + " flex items-center justify-center gap-2"}>
            <Check size={18} /> {rc >= REDEEM_THRESHOLD ? t("wallet.redeemBtn") : t("wallet.notenough")}
          </button>
        </div>
      )}
    </Modal>
  );
}
