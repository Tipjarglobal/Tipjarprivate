import React, { useState, useEffect } from "react";
import Modal, { Field, inputCls, btnPrimary } from "./Modal";
import { CreditCard, Gift, Banknote, Check, AlertTriangle, Coins, Zap, Crown, Star } from "lucide-react";
import api, { apiErr } from "../api";
import { useI18n } from "../i18n";
import { useAuth } from "../auth";
import { toast } from "sonner";

const REDEEM_THRESHOLD = 10000; // 10.000 Coins = 50€ = 0.5 Cent pro Coin - NO GLITCH

// NO MONEY GLITCH PACKAGES - Sale price always > payout (0.5c)
const FIXED_PACKAGES = {
  starter: { coins: 50, bonus: 0, price: 9.99, label: "Starter • 50" },
  fan: { coins: 120, bonus: 10, price: 19.99, label: "Fan • 130", popular: true },
  supporter: { coins: 400, bonus: 20, price: 49.99, label: "Supporter • 420" },
  pro: { coins: 800, bonus: 50, price: 79.99, label: "Pro • 850", bestValue: true },
  whale: { coins: 1300, bonus: 100, price: 109.99, label: "Whale • 1400", bestDeal: true },
};

const TEXTS = {
  en: { title: "Your Coins", available: "AVAILABLE", balance: "BALANCE", buy: "Top Up", gift: "Gift", redeem: "Cash Out", credits: "Coins", buying: "Redirecting to payment...", gifted: "Gifted", redeemOk: "Payout requested", redeemBtn: "Withdraw €50", notenough: "Not enough for payout", redeemInfo: "Collect 10,000 to withdraw €50. That's €0.005 per coin. Sale price always > payout - no loss possible.", buyDisabled: "", creditsPurpose: "Coins are for gifting other members. Posting and rating is free. Battery max 2500.", giftTo: "Username", amount: "Amount", fee: "Gift fee: 0 coins. 100% arrives.", send: "Send", popular: "POPULAR", bestValue: "BEST VALUE", bestDeal: "BEST DEAL -61%", bonus: "+{n} Bonus" },
  de: { title: "Deine Münzen", available: "VERFÜGBAR", balance: "GUTHABEN", buy: "Aufladen", gift: "Verschenken", redeem: "Auszahlen", credits: "Münzen", buying: "Weiter zur Zahlung...", gifted: "Verschenkt", redeemOk: "Auszahlung angefordert", redeemBtn: "50€ auszahlen", notenough: "Noch nicht genug für Auszahlung", redeemInfo: "Sammle 10.000 für 50€ Auszahlung. 0,5 Cent pro Münze. Verkauf immer teurer als Auszahlung - kein Verlust möglich.", buyDisabled: "", creditsPurpose: "Münzen sind zum Verschenken. Posten & Bewerten ist kostenlos. Batterie max 2500.", giftTo: "Benutzername", amount: "Anzahl", fee: "Gebühr: 0 Münzen. 100% kommt an.", send: "Senden", popular: "BELIEBT", bestValue: "BESTER WERT", bestDeal: "BEST DEAL -61%", bonus: "+{n} Bonus" },
  es: { title: "Tus Monedas", available: "DISPONIBLE", balance: "SALDO", buy: "Recargar", gift: "Regalar", redeem: "Retirar", credits: "Monedas", buying: "Redirigiendo al pago...", gifted: "Regalado", redeemOk: "Retiro solicitado", redeemBtn: "Retirar 50€", notenough: "Aún no suficiente", redeemInfo: "Junta 10.000 para retirar 50€. 0,005€ por moneda.", buyDisabled: "", creditsPurpose: "Monedas para regalar. Publicar es gratis.", giftTo: "Usuario", amount: "Cantidad", fee: "Sin comisión.", send: "Enviar", popular: "POPULAR", bestValue: "MEJOR VALOR", bestDeal: "MEJOR OFERTA -61%", bonus: "+{n} Bonus" },
  el: { title: "Τα Νομίσματά σου", available: "ΔΙΑΘΕΣΙΜΟ", balance: "ΥΠΟΛΟΙΠΟ", buy: "Φόρτιση", gift: "Δώρισε", redeem: "Ανάληψη", credits: "Νομίσματα", buying: "Μεταφορά στην πληρωμή...", gifted: "Δωρίστηκε", redeemOk: "Αίτηση ανάληψης", redeemBtn: "Ανάληψη 50€", notenough: "Όχι ακόμα αρκετά", redeemInfo: "Μάζεψε 10.000 για ανάληψη 50€. 0,005€ ανά νόμισμα.", buyDisabled: "", creditsPurpose: "Νομίσματα για δώρο. Δημοσίευση δωρεάν.", giftTo: "Όνομα χρήστη", amount: "Ποσό", fee: "Χωρίς χρέωση.", send: "Αποστολή", popular: "ΔΗΜΟΦΙΛΕΣ", bestValue: "ΚΑΛΥΤΕΡΗ ΑΞΙΑ", bestDeal: "ΚΑΛΥΤΕΡΗ ΠΡΟΣΦΟΡΑ -61%", bonus: "+{n} Bonus" },
  fr: { title: "Tes Pièces", available: "DISPONIBLE", balance: "SOLDE", buy: "Recharger", gift: "Offrir", redeem: "Retirer", credits: "Pièces", buying: "Redirection paiement...", gifted: "Offert", redeemOk: "Retrait demandé", redeemBtn: "Retirer 50€", notenough: "Pas encore assez", redeemInfo: "Collectez 10.000 pour retirer 50€. 0,005€ par pièce.", buyDisabled: "", creditsPurpose: "Pièces pour offrir. Poster gratuit.", giftTo: "Nom d'utilisateur", amount: "Montant", fee: "Frais: 0.", send: "Envoyer", popular: "POPULAIRE", bestValue: "MEILLEURE VALEUR", bestDeal: "MEILLEURE OFFRE -61%", bonus: "+{n} Bonus" },
  it: { title: "Le Tue Monete", available: "DISPONIBILE", balance: "SALDO", buy: "Ricarica", gift: "Regala", redeem: "Preleva", credits: "Monete", buying: "Reindirizzamento al pagamento...", gifted: "Regalato", redeemOk: "Prelievo richiesto", redeemBtn: "Preleva 50€", notenough: "Non ancora abbastanza", redeemInfo: "Raccogli 10.000 per prelevare 50€. 0,005€ per moneta.", buyDisabled: "", creditsPurpose: "Monete per regalare. Postare gratis.", giftTo: "Username", amount: "Importo", fee: "Nessuna commissione.", send: "Invia", popular: "POPOLARE", bestValue: "MIGLIOR VALORE", bestDeal: "MIGLIORE OFFERTA -61%", bonus: "+{n} Bonus" },
  ar: { title: "عملاتك", available: "متاح", balance: "الرصيد", buy: "شحن", gift: "إهداء", redeem: "سحب", credits: "عملات", buying: "جاري التحويل للدفع...", gifted: "تم الإهداء", redeemOk: "تم طلب السحب", redeemBtn: "سحب 50€", notenough: "ليس كافيًا بعد", redeemInfo: "اجمع 10.000 لتسحب 50€. 0.005€ لكل عملة.", buyDisabled: "", creditsPurpose: "العملات للإهداء. النشر مجاني.", giftTo: "اسم المستخدم", amount: "العدد", fee: "بدون رسوم.", send: "إرسال", popular: "شائع", bestValue: "أفضل قيمة", bestDeal: "أفضل صفقة -61%", bonus: "+{n} إضافي" },
  tr: { title: "Paraların", available: "MEVCUT", balance: "BAKİYE", buy: "Yükle", gift: "Hediye et", redeem: "Çek", credits: "Para", buying: "Ödemeye yönlendiriliyor...", gifted: "Hediye edildi", redeemOk: "Çekim talebi alındı", redeemBtn: "50€ çek", notenough: "Henüz yeterli değil", redeemInfo: "50€ çekmek için 10.000 biriktir. 0,005€ coin başına.", buyDisabled: "", creditsPurpose: "Paralar hediye içindir. Paylaşmak ücretsiz.", giftTo: "Kullanıcı adı", amount: "Miktar", fee: "Ücret: 0.", send: "Gönder", popular: "POPÜLER", bestValue: "EN İYİ DEĞER", bestDeal: "EN İYİ FIRSAT -61%", bonus: "+{n} Bonus" },
};

export default function WalletModal({ open, onClose, initialTab, initialGiftTo }) {
  const { lang } = useI18n();
  const { user, setUser } = useAuth();
  const tLocal = TEXTS[lang] || TEXTS.en;
  const { t: tI18n } = useI18n();
  const [tab, setTab] = useState("buy");
  const [packages, setPackages] = useState(FIXED_PACKAGES);
  const [giftTo, setGiftTo] = useState("");
  const [giftAmt, setGiftAmt] = useState("");
  const [busy, setBusy] = useState(false);

  // Helper to get text with fallback to i18n file
  const tx = (key) => tLocal[key] || tI18n(key) || key;

  useEffect(() => {
    if (open) {
      // Try backend packages, fallback to fixed
      api.get("/credits/packages").then((r) => {
        if (r.data && Object.keys(r.data).length > 0) {
          // If backend still returns old, ignore and use fixed
          const hasNew = Object.values(r.data).some(p => p.coins >= 50);
          if (!hasNew) setPackages(FIXED_PACKAGES);
          else setPackages(r.data);
        }
      }).catch(() => setPackages(FIXED_PACKAGES));
      setTab(initialTab || "buy");
      if (initialGiftTo) setGiftTo(initialGiftTo);
    }
  }, [open, initialTab, initialGiftTo]);

  const buy = async (pkgId) => {
    setBusy(true);
    try {
      toast.message(tx("buying"));
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
      toast.success(`${tx("gifted")} (${data.received} ${tx("credits")})`);
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
      toast.success(`${tx("redeemOk")} (€${data.redemption.amount_eur})`);
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setBusy(false);
    }
  };

  const rc = user?.received_credits || user?.received_coins || 0;
  const available = user?.credits ?? user?.coins ?? 0;
  const pct = Math.min(100, (rc / REDEEM_THRESHOLD) * 100);

  return (
    <Modal open={open} onClose={onClose} title={tx("title")} testId="wallet-modal">
      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="rounded-xl bg-void border border-elevated p-4">
          <p className="text-[10px] uppercase tracking-widest text-zinc-500">{tx("available")}</p>
          <p className="font-mono font-black text-3xl text-volt text-glow-volt flex items-center gap-2" data-testid="wallet-balance">
            <Coins size={22} className="text-volt" /> {available}
          </p>
        </div>
        <div className="rounded-xl bg-void border border-elevated p-4">
          <p className="text-[10px] uppercase tracking-widest text-zinc-500">{tx("balance")}</p>
          <p className="font-mono font-black text-3xl text-won" data-testid="wallet-received">{rc}</p>
          <div className="mt-2 h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
            <div className="h-full bg-yellow-400 transition-all" style={{ width: `${pct}%` }} />
          </div>
          <p className="text-[10px] text-zinc-500 mt-1">{pct}% • {rc} / {REDEEM_THRESHOLD}</p>
        </div>
      </div>

      <div className="flex gap-2 mb-5 p-1 bg-void rounded-xl border border-elevated">
        {[["buy", CreditCard, tx("buy")], ["gift", Gift, tx("gift")], ["redeem", Banknote, tx("redeem")]].map(([k, Icon, label]) => (
          <button key={k} data-testid={`wallet-tab-${k}`} onClick={() => setTab(k)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-colors ${tab === k ? "bg-volt text-void" : "text-zinc-400 hover:text-white"}`}>
            <Icon size={15} /> {label}
          </button>
        ))}
      </div>

      {tab === "buy" && (
        <div className="space-y-2.5" data-testid="buy-panel">
          {Object.entries(packages).map(([id, p]) => {
            const total = (p.coins || p.credits || 0) + (p.bonus || 0);
            const price = p.price;
            const perCoin = (price / total).toFixed(3);
            return (
              <button key={id} data-testid={`buy-${id}`} onClick={() => buy(id)} disabled={busy}
                className={`w-full flex items-center justify-between rounded-xl border p-4 text-left transition-all hover:scale-[1.01] ${id === 'whale' ? 'border-yellow-400 bg-yellow-400/10' : id === 'fan' ? 'border-white/20 bg-void' : 'border-elevated bg-void'}`}>
                <div className="text-left">
                  <p className="font-heading font-bold text-white text-[15px] flex items-center gap-2">
                    {total.toLocaleString()} {tx("credits")}
                    {p.bonus > 0 && <span className="text-[10px] px-2 py-0.5 rounded-full bg-green-500 text-black font-bold">{tx("bonus").replace("{n}", p.bonus)}</span>}
                    {p.popular && <span className="text-[10px] px-2 py-0.5 rounded-full bg-white text-black font-bold flex items-center gap-1"><Star size={10}/>{tx("popular")}</span>}
                    {p.bestDeal && <span className="text-[10px] px-2 py-0.5 rounded-full bg-yellow-400 text-black font-bold flex items-center gap-1"><Crown size={10}/>{tx("bestDeal")}</span>}
                    {p.bestValue && <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500 text-white font-bold">{tx("bestValue")}</span>}
                  </p>
                  <p className="font-mono text-volt font-bold text-xs mt-0.5">${perCoin} {lang==='de'?'pro Münze': lang==='en'?'per coin':'/ coin'}</p>
                </div>
                <span className="font-mono font-black text-xl text-white">€{price.toFixed(2)}</span>
              </button>
            );
          })}
          <div data-testid="credits-purpose-notice"
            className="flex items-start gap-2.5 rounded-xl border border-elevated bg-void p-4 text-zinc-400">
            <Zap size={18} className="shrink-0 mt-0.5 text-volt" />
            <p className="text-[12px] leading-snug">{tx("creditsPurpose")}<br/><span className="text-[10px] text-zinc-600">2500 Max Power • 0.5¢ payout • No glitch • 87% margin</span></p>
          </div>
        </div>
      )}

      {tab === "gift" && (
        <div data-testid="gift-panel">
          <Field label={tx("giftTo")}>
            <input data-testid="gift-to" className={inputCls} value={giftTo} onChange={(e) => setGiftTo(e.target.value)} placeholder="Username" />
          </Field>
          <Field label={tx("amount")}>
            <input data-testid="gift-amount" type="number" min="1" className={inputCls} value={giftAmt} onChange={(e) => setGiftAmt(e.target.value)} />
          </Field>
          <p className="text-xs text-zinc-500 mb-4">{tx("fee")}</p>
          <button data-testid="gift-send" onClick={gift} disabled={busy || !giftTo || !giftAmt} className={btnPrimary}>{tx("send")}</button>
        </div>
      )}

      {tab === "redeem" && (
        <div data-testid="redeem-panel">
          <p className="text-sm text-zinc-400 mb-3">{tx("redeemInfo")}</p>
          <div className="h-3 rounded-full bg-void border border-elevated overflow-hidden mb-2">
            <div className="h-full bg-gradient-to-r from-won to-volt transition-all" style={{ width: `${pct}%` }} />
          </div>
          <p className="font-mono text-sm text-white mb-4">{rc} / {REDEEM_THRESHOLD} ({pct}%)</p>
          <button data-testid="redeem-btn" onClick={redeem} disabled={busy || rc < REDEEM_THRESHOLD} className={btnPrimary + " flex items-center justify-center gap-2"}>
            <Check size={18} /> {rc >= REDEEM_THRESHOLD ? tx("redeemBtn") : tx("notenough")}
          </button>
          <p className="text-[10px] text-zinc-600 mt-3 text-center">2000 Coins payout costs you only €10. You earned ~€145 before. Profit €135 safe.</p>
        </div>
      )}
    </Modal>
  );
}
