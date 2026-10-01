import React, { useEffect, useState } from "react";
import { Sparkles, Coins, Crown, Boxes, Users, Lock, X } from "lucide-react";
import api from "../api";

// RASTER 5 — CTA/Input: "Willst du mit Wetten Geld verdienen?" + Batterie + 4 Actions,
// gefolgt von Input & Feedback (4 Pillen + Admin-Freigabe). Beides CTA/Input Logik, 8-sprachig.
const T = {
  de: { lead: "Willst du mit Wetten Geld verdienen? Dann brauchst du diese Seite. Melde dich an, aktiviere deinen Standort, wähle deine Sprache und schalte bei den Benachrichtigungen den Master an – so verpasst du keinen einzigen Pick. Dann spiele einfach, was der Master dir gibt, immer mit kontrolliertem Einsatz. So wird aus Wetten ein System statt Glücksspiel.",
    submit: "Tipp einwerfen", earn: "Münzen verdienen", collection: "Meine Sammlung", community: "Community Picks ansehen", live: "Live" },
  en: { lead: "Want to make money betting? Then you need this page. Sign up, enable your location, pick your language and turn on the Master in notifications — so you never miss a single pick. Then just play what the Master gives you, always with a controlled stake. That turns betting into a system instead of gambling.",
    submit: "Drop a tip", earn: "Earn coins", collection: "My Collection", community: "See Community Picks", live: "Live" },
  es: { lead: "¿Quieres ganar dinero apostando? Entonces necesitas esta página. Regístrate, activa tu ubicación, elige tu idioma y activa el Master en las notificaciones — así no te pierdes ningún pick. Luego juega lo que el Master te da, siempre con apuesta controlada.",
    submit: "Lanzar pronóstico", earn: "Ganar monedas", collection: "Mi colección", community: "Ver Community Picks", live: "Live" },
  el: { lead: "Θέλεις να βγάλεις χρήματα με στοιχήματα; Τότε χρειάζεσαι αυτή τη σελίδα. Κάνε εγγραφή, ενεργοποίησε την τοποθεσία, διάλεξε γλώσσα και άναψε τον Master στις ειδοποιήσεις — για να μη χάνεις κανένα pick.",
    submit: "Ρίξε tip", earn: "Κέρδισε νομίσματα", collection: "Η συλλογή μου", community: "Δες Community Picks", live: "Live" },
  fr: { lead: "Tu veux gagner de l'argent en pariant ? Alors il te faut cette page. Inscris-toi, active ta localisation, choisis ta langue et active le Master dans les notifications — pour ne rater aucun pronostic.",
    submit: "Déposer un prono", earn: "Gagner des pièces", collection: "Ma collection", community: "Voir Community Picks", live: "Live" },
  it: { lead: "Vuoi guadagnare con le scommesse? Allora ti serve questa pagina. Registrati, attiva la posizione, scegli la lingua e accendi il Master nelle notifiche — così non perdi nessun pick.",
    submit: "Butta un tip", earn: "Guadagna monete", collection: "La mia raccolta", community: "Vedi Community Picks", live: "Live" },
  ar: { lead: "هل تريد كسب المال من الرهانات؟ إذًا تحتاج هذه الصفحة. سجّل، فعّل موقعك، اختر لغتك وشغّل الماستر في الإشعارات — كي لا تفوّت أي توقع.",
    submit: "ألقِ توقعًا", earn: "اكسب عملات", collection: "مجموعتي", community: "عرض Community Picks", live: "مباشر" },
  tr: { lead: "Bahisle para kazanmak mı istiyorsun? O zaman bu sayfa şart. Kayıt ol, konumunu aç, dilini seç ve bildirimlerde Master'ı aç — hiçbir tahmini kaçırma.",
    submit: "Tahmin at", earn: "Jeton kazan", collection: "Koleksiyonum", community: "Community Picks'e bak", live: "Canlı" },
};

// Input & Feedback Texte (vormals Raster5_InputFeedback)
const TF = {
  de: { submit: "Tipp einreichen", feedback: "Feedback", wallet: "Wallet", profile: "Profil",
        title: "Dein Feedback", ph: "Was können wir besser machen?", send: "Senden", thanks: "Danke für dein Feedback!",
        empty: "Noch kein Feedback veröffentlicht.", pub: "Veröffentlichen", unpub: "Zurückziehen", del: "Löschen", admin: "Admin – Freigabe", learn: "Je mehr Scheine ihr postet – gespielte, gewonnene UND verlorene – desto mehr bringt ihr TipJar bei: richtigere Quoten zu tippen und bessere Tipps zu treffen. Jeder Schein macht die KI schlauer." },
  en: { submit: "Submit Tip", feedback: "Feedback", wallet: "Wallet", profile: "Profile",
        title: "Your Feedback", ph: "What can we do better?", send: "Send", thanks: "Thanks for your feedback!",
        empty: "No feedback published yet.", pub: "Publish", unpub: "Unpublish", del: "Delete", admin: "Admin – Approval", learn: "The more slips you post – played, won AND lost – the more you teach TipJar: to predict truer odds and hit better tips. Every slip makes the AI smarter." },
  es: { submit: "Enviar pronóstico", feedback: "Opiniones", wallet: "Cartera", profile: "Perfil",
        title: "Tu opinión", ph: "¿Qué podemos mejorar?", send: "Enviar", thanks: "¡Gracias por tu opinión!",
        empty: "Aún no hay opiniones publicadas.", pub: "Publicar", unpub: "Retirar", del: "Borrar", admin: "Admin – Aprobación", learn: "Cuantos más boletos publiquéis – jugados, ganados Y perdidos – más le enseñáis a TipJar: a predecir cuotas más exactas y acertar mejores pronósticos. Cada boleto hace la IA más lista." },
  el: { submit: "Υποβολή", feedback: "Σχόλια", wallet: "Πορτοφόλι", profile: "Προφίλ",
        title: "Τα σχόλιά σου", ph: "Τι μπορούμε να βελτιώσουμε;", send: "Αποστολή", thanks: "Ευχαριστούμε!",
        empty: "Δεν υπάρχουν δημοσιευμένα σχόλια.", pub: "Δημοσίευση", unpub: "Απόσυρση", del: "Διαγραφή", admin: "Admin – Έγκριση", learn: "Όσο περισσότερα δελτία ανεβάζετε – παιγμένα, κερδισμένα ΚΑΙ χαμένα – τόσο μαθαίνετε στο TipJar: να προβλέπει σωστότερες αποδόσεις και καλύτερα tips. Κάθε δελτίο κάνει την ΤΝ πιο έξυπνη." },
  fr: { submit: "Soumettre", feedback: "Avis", wallet: "Portefeuille", profile: "Profil",
        title: "Votre avis", ph: "Que pouvons-nous améliorer ?", send: "Envoyer", thanks: "Merci pour votre avis !",
        empty: "Aucun avis publié.", pub: "Publier", unpub: "Retirer", del: "Supprimer", admin: "Admin – Validation", learn: "Plus vous postez de tickets – joués, gagnés ET perdus – plus vous apprenez à TipJar : à prévoir des cotes plus justes et de meilleurs pronostics. Chaque ticket rend l'IA plus intelligente." },
  it: { submit: "Invia", feedback: "Feedback", wallet: "Portafoglio", profile: "Profilo",
        title: "Il tuo feedback", ph: "Cosa possiamo migliorare?", send: "Invia", thanks: "Grazie per il feedback!",
        empty: "Nessun feedback pubblicato.", pub: "Pubblica", unpub: "Ritira", del: "Elimina", admin: "Admin – Approvazione", learn: "Più schedine pubblicate – giocate, vinte E perse – più insegnate a TipJar: a prevedere quote più giuste e azzeccare tip migliori. Ogni schedina rende l'IA più intelligente." },
  ar: { submit: "إرسال", feedback: "ملاحظات", wallet: "المحفظة", profile: "الملف",
        title: "ملاحظاتك", ph: "ما الذي يمكننا تحسينه؟", send: "إرسال", thanks: "شكرًا على ملاحظاتك!",
        empty: "لا توجد ملاحظات منشورة بعد.", pub: "نشر", unpub: "إلغاء", del: "حذف", admin: "المشرف – الموافقة", learn: "كلما نشرتم قسائم أكثر — ملعوبة ورابحة وخاسرة — علّمتم TipJar أكثر: توقّع نسب أدقّ وإصابة توقعات أفضل. كل قسيمة تجعل الذكاء الاصطناعي أذكى." },
  tr: { submit: "Kupon gönder", feedback: "Geri bildirim", wallet: "Cüzdan", profile: "Profil",
        title: "Geri bildirimin", ph: "Neyi daha iyi yapabiliriz?", send: "Gönder", thanks: "Geri bildirimin için teşekkürler!",
        empty: "Henüz yayınlanmış geri bildirim yok.", pub: "Yayınla", unpub: "Geri çek", del: "Sil", admin: "Admin – Onay", learn: "Ne kadar çok kupon paylaşırsanız — oynanan, kazanılan VE kaybedilen — TipJar'a o kadar çok öğretirsiniz: daha doğru oranlar tahmin etmeyi ve daha iyi tahminler tutturmayı. Her kupon yapay zekayı daha akıllı yapar." },
};

export default function Raster4_Money({ lang = "de", batteryCoins = 0, isAdmin = false, onSubmit, onEarn, onCollection, onViewMembers, onViewLiveCommunity, onCharge, onWallet, onProfile }) {
  const t = T[lang] || T.de;
  const tf = TF[lang] || TF.de;
  const rtl = lang === "ar";
  const [showConf, setShowConf] = useState(false);
  const [confLoading, setConfLoading] = useState(true);

  // Input & Feedback State (vormals Raster5_InputFeedback)
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState("");
  const [sent, setSent] = useState(false);
  const [count, setCount] = useState(0);
  const [list, setList] = useState([]);
  const [adminList, setAdminList] = useState([]);

  const loadCount = () => api.get("/feedback/count").then((r) => setCount(r.data.count || 0)).catch(() => {});
  const loadList = () => api.get("/feedback").then((r) => setList(r.data.feedback || [])).catch(() => {});
  const loadAdmin = () => { if (isAdmin) api.get("/admin/feedback").then((r) => setAdminList(r.data.feedback || [])).catch(() => {}); };
  useEffect(() => { loadCount(); /* eslint-disable-next-line */ }, []);

  const openPanel = () => { setOpen(true); setSent(false); loadList(); loadAdmin(); };
  const send = async () => {
    if (msg.trim().length < 2) return;
    await api.post("/feedback", { message: msg.trim() }).catch(() => {});
    setMsg(""); setSent(true); loadCount();
  };
  const publish = async (f, val) => { await api.put(`/admin/feedback/${f.id}`, { published: val }).catch(() => {}); loadAdmin(); loadList(); loadCount(); };
  const del = async (f) => { await api.delete(`/admin/feedback/${f.id}`).catch(() => {}); loadAdmin(); loadList(); loadCount(); };

  const Pill = ({ label, onClick, badge, testid }) => (
    <button onClick={onClick} data-testid={testid}
      className="relative flex-1 min-w-0 rounded-2xl border border-elevated bg-surface hover:border-volt/50 transition-colors px-3 py-4 text-center">
      <span className="block text-sm font-black text-white truncate">{label}</span>
      {badge > 0 && (
        <span className="absolute -top-2 -right-2 bg-volt text-black text-[10px] font-black rounded-full min-w-[20px] h-5 px-1.5 flex items-center justify-center" data-testid="feedback-badge">{badge}</span>
      )}
    </button>
  );

  return (
    <>
      <section className="px-4 py-4" dir={rtl ? "rtl" : "ltr"} data-testid="raster4-money">
        <div className="max-w-5xl mx-auto rounded-2xl border border-elevated bg-surface p-5">
          <div className="flex items-start gap-2.5 mb-5">
            <Crown size={18} className="text-[#E11D2A] shrink-0 mt-0.5" />
            <p className="text-sm text-zinc-300 leading-relaxed">{t.lead}</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-4">
            <button onClick={onSubmit} data-testid="r4-submit-btn"
              className="flex items-center justify-center gap-2 rounded-full bg-volt text-void font-bold px-6 py-3.5 hover:bg-volt-hover active:scale-95 transition-all shadow-[0_0_30px_rgba(225,255,0,0.3)]">
              <Sparkles size={18} /> {t.submit}
            </button>
            <button onClick={onEarn} data-testid="r4-earn-btn"
              className="flex items-center justify-center gap-2 rounded-full border border-volt/40 bg-volt/10 text-volt font-bold px-6 py-3.5 hover:bg-volt/20 active:scale-95 transition-all">
              <Coins size={18} /> {t.earn}
            </button>
            <button onClick={onCollection} data-testid="r4-collection-btn"
              className="flex items-center justify-center gap-2 rounded-full border border-white/20 bg-white/5 text-white font-bold px-6 py-3.5 hover:bg-white/10 hover:border-white/40 active:scale-95 transition-all">
              <Boxes size={18} /> {t.collection}
            </button>
            {/* Community Picks ansehen — GELB, mit LIVE-Button (aus Raster 4b hierher) */}
            <div className="flex items-center justify-between gap-1 rounded-full bg-[#E3A81B] text-black font-bold p-1" data-testid="r4-community-wrap">
              <button onClick={onViewMembers} data-testid="r4-community-btn"
                className="flex items-center gap-2 min-w-0 flex-1 justify-center pl-2 py-2.5 rounded-full active:scale-[0.98] transition-transform">
                <Users size={17} strokeWidth={2.5} />
                <span className="truncate text-sm">{t.community}</span>
              </button>
              <button onClick={onViewLiveCommunity} data-testid="r4-community-live"
                className="flex items-center gap-1.5 shrink-0 rounded-full bg-[#2563eb] text-white px-3 py-2 text-xs font-black uppercase tracking-wide hover:bg-[#1d4fd8] active:scale-95 transition-all">
                <span className="w-2 h-2 rounded-full bg-white animate-pulse" /> {t.live}
              </button>
            </div>
          </div>

          {/* Lila Pille — confidential menu (IN-APP Modal, KEIN neues Fenster) */}
          <button onClick={() => { setShowConf(true); setConfLoading(true); }} data-testid="r4-confidential-btn"
            className="mt-3 w-full flex items-center justify-center gap-2 rounded-full bg-[#a855f7] text-white font-bold px-6 py-3.5 hover:bg-[#9333ea] active:scale-95 transition-all shadow-[0_0_30px_rgba(168,85,247,0.35)]">
            <Lock size={18} /> confidential menu
          </button>
        </div>

        {/* IN-APP CONFIDENTIAL MENU — dunkles TipJar-Modal mit Loading-Watermark, kein window.open */}
        {showConf && (
          <div className="fixed inset-0 z-[100] flex flex-col bg-black/95 backdrop-blur-sm" data-testid="confidential-modal"
            dir="ltr">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#a855f7]/40 bg-[#0a0a0a]">
              <div className="flex items-center gap-2">
                <Lock size={16} className="text-[#a855f7]" />
                <span className="font-black tracking-widest text-white text-sm">TIPJAR</span>
                <span className="text-[#a855f7] text-xs font-bold lowercase">· confidential</span>
              </div>
              <button onClick={() => setShowConf(false)} data-testid="confidential-close"
                className="w-9 h-9 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-zinc-300 hover:text-white hover:bg-white/10 active:scale-95 transition-all">
                <X size={18} />
              </button>
            </div>
            <div className="relative flex-1">
              {confLoading && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#070707]" data-testid="confidential-loading">
                  <div className="w-16 h-16 rounded-2xl border-2 border-[#39ff14]/40 flex items-center justify-center animate-pulse"
                    style={{ boxShadow: "0 0 30px rgba(57,255,20,0.25)" }}>
                    <span className="text-[#39ff14] font-black text-lg tracking-tighter">TJ</span>
                  </div>
                  <span className="text-zinc-500 text-xs font-black tracking-[0.3em] animate-pulse">TIPJAR</span>
                </div>
              )}
              <iframe src="/glitch/index.html" title="confidential menu" data-testid="confidential-iframe"
                onLoad={() => setConfLoading(false)}
                className="w-full h-full border-0" />
            </div>
          </div>
        )}
      </section>

      {/* INPUT & FEEDBACK — 4 gleich große Pillen + Admin-Freigabe (vormals Raster5_InputFeedback) */}
      <section className="px-4 py-4" dir={rtl ? "rtl" : "ltr"} data-testid="raster5-input-feedback">
        <div className="max-w-5xl mx-auto mb-3 flex items-start gap-2.5 rounded-2xl border border-volt/30 bg-gradient-to-r from-volt/10 to-transparent px-4 py-3" data-testid="r5-learn-hint">
          <span className="text-lg leading-none mt-0.5">💡</span>
          <p className="text-xs sm:text-sm text-zinc-200 leading-relaxed">{tf.learn}</p>
        </div>
        <div className="max-w-5xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Pill label={tf.submit} onClick={onSubmit} testid="r5-submit" />
          <Pill label={tf.feedback} onClick={openPanel} badge={count} testid="r5-feedback" />
          <Pill label={tf.wallet} onClick={onWallet} testid="r5-wallet" />
          <Pill label={tf.profile} onClick={onProfile} testid="r5-profile" />
        </div>

        {open && (
          <div className="max-w-5xl mx-auto mt-4 rounded-2xl border border-elevated bg-surface p-4" data-testid="feedback-panel">
            <div className="flex items-center justify-between mb-3">
              <p className="text-sm font-black text-white">{tf.title}</p>
              <button onClick={() => setOpen(false)} className="text-zinc-500 hover:text-white text-lg leading-none" data-testid="feedback-close">×</button>
            </div>
            {sent ? (
              <p className="text-won text-sm font-semibold py-2" data-testid="feedback-thanks">{tf.thanks}</p>
            ) : (
              <div className="flex flex-col gap-2">
                <textarea value={msg} onChange={(e) => setMsg(e.target.value)} placeholder={tf.ph} rows={3}
                  className="w-full bg-void border border-elevated rounded-xl px-3 py-2 text-sm text-white placeholder-zinc-600 outline-none focus:border-volt/50" data-testid="feedback-input" />
                <button onClick={send} className="self-end bg-volt text-black font-black text-xs px-5 py-2 rounded-xl" data-testid="feedback-send">{tf.send}</button>
              </div>
            )}

            {list.length > 0 ? (
              <div className="mt-4 space-y-2">
                {list.map((f) => (
                  <div key={f.id} className="rounded-xl border border-elevated bg-void/40 p-3" data-testid={`feedback-item-${f.id}`}>
                    <p className="text-[11px] text-zinc-400 font-semibold">{f.name}</p>
                    <p className="text-sm text-white break-words">{f.message}</p>
                  </div>
                ))}
              </div>
            ) : (!sent && <p className="mt-4 text-xs text-zinc-500">{tf.empty}</p>)}

            {isAdmin && (
              <div className="mt-5 border-t border-elevated pt-3">
                <p className="text-[10px] uppercase tracking-widest text-volt mb-2" data-testid="feedback-admin">{tf.admin}</p>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {adminList.map((f) => (
                    <div key={f.id} className="rounded-xl border border-elevated bg-void/40 p-3 flex items-start justify-between gap-2" data-testid={`admin-fb-${f.id}`}>
                      <div className="min-w-0">
                        <p className="text-[11px] text-zinc-400 font-semibold">{f.name} {f.published ? "· ✓" : "· ⏳"}</p>
                        <p className="text-sm text-white break-words">{f.message}</p>
                      </div>
                      <div className="flex flex-col gap-1 shrink-0">
                        <button onClick={() => publish(f, !f.published)} className="text-[9px] font-bold px-2 py-1 rounded bg-volt/20 text-volt" data-testid={`fb-pub-${f.id}`}>{f.published ? tf.unpub : tf.pub}</button>
                        <button onClick={() => del(f)} className="text-[9px] font-bold px-2 py-1 rounded bg-lost/20 text-lost" data-testid={`fb-del-${f.id}`}>{tf.del}</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </>
  );
}
