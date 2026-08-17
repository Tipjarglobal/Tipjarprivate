import React, { useEffect, useState } from "react";
import api from "../api";

// RASTER 5 — Input & Feedback: 4 gleich große Pillen, Feedback mit dynamischem Badge,
// Admin-Control für Veröffentlichung. 8-sprachig (EN/DE/ES/EL/FR/IT/AR/TR).
const T = {
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

export default function Raster5_InputFeedback({ lang = "de", isAdmin = false, onSubmit, onWallet, onProfile }) {
  const t = T[lang] || T.de;
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
    <section className="px-4 py-4" dir={lang === "ar" ? "rtl" : "ltr"} data-testid="raster5-input-feedback">
      <div className="max-w-5xl mx-auto mb-3 flex items-start gap-2.5 rounded-2xl border border-volt/30 bg-gradient-to-r from-volt/10 to-transparent px-4 py-3" data-testid="r5-learn-hint">
        <span className="text-lg leading-none mt-0.5">💡</span>
        <p className="text-xs sm:text-sm text-zinc-200 leading-relaxed">{t.learn}</p>
      </div>
      <div className="max-w-5xl mx-auto grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Pill label={t.submit} onClick={onSubmit} testid="r5-submit" />
        <Pill label={t.feedback} onClick={openPanel} badge={count} testid="r5-feedback" />
        <Pill label={t.wallet} onClick={onWallet} testid="r5-wallet" />
        <Pill label={t.profile} onClick={onProfile} testid="r5-profile" />
      </div>

      {open && (
        <div className="max-w-5xl mx-auto mt-4 rounded-2xl border border-elevated bg-surface p-4" data-testid="feedback-panel">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-black text-white">{t.title}</p>
            <button onClick={() => setOpen(false)} className="text-zinc-500 hover:text-white text-lg leading-none" data-testid="feedback-close">×</button>
          </div>
          {sent ? (
            <p className="text-won text-sm font-semibold py-2" data-testid="feedback-thanks">{t.thanks}</p>
          ) : (
            <div className="flex flex-col gap-2">
              <textarea value={msg} onChange={(e) => setMsg(e.target.value)} placeholder={t.ph} rows={3}
                className="w-full bg-void border border-elevated rounded-xl px-3 py-2 text-sm text-white placeholder-zinc-600 outline-none focus:border-volt/50" data-testid="feedback-input" />
              <button onClick={send} className="self-end bg-volt text-black font-black text-xs px-5 py-2 rounded-xl" data-testid="feedback-send">{t.send}</button>
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
          ) : (!sent && <p className="mt-4 text-xs text-zinc-500">{t.empty}</p>)}

          {isAdmin && (
            <div className="mt-5 border-t border-elevated pt-3">
              <p className="text-[10px] uppercase tracking-widest text-volt mb-2" data-testid="feedback-admin">{t.admin}</p>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {adminList.map((f) => (
                  <div key={f.id} className="rounded-xl border border-elevated bg-void/40 p-3 flex items-start justify-between gap-2" data-testid={`admin-fb-${f.id}`}>
                    <div className="min-w-0">
                      <p className="text-[11px] text-zinc-400 font-semibold">{f.name} {f.published ? "· ✓" : "· ⏳"}</p>
                      <p className="text-sm text-white break-words">{f.message}</p>
                    </div>
                    <div className="flex flex-col gap-1 shrink-0">
                      <button onClick={() => publish(f, !f.published)} className="text-[9px] font-bold px-2 py-1 rounded bg-volt/20 text-volt" data-testid={`fb-pub-${f.id}`}>{f.published ? t.unpub : t.pub}</button>
                      <button onClick={() => del(f)} className="text-[9px] font-bold px-2 py-1 rounded bg-lost/20 text-lost" data-testid={`fb-del-${f.id}`}>{t.del}</button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
