import React from "react";
import { Sparkles, Coins, Crown } from "lucide-react";
import CoinBattery from "./CoinBattery";

// RASTER 4 — "Willst du mit Wetten Geld verdienen?" + Community-Section + Münz-Batterie + 2 Buttons.
const T = {
  de: { lead: "Willst du mit Wetten Geld verdienen? Dann brauchst du diese Seite. Melde dich an, aktiviere deinen Standort, wähle deine Sprache und schalte bei den Benachrichtigungen den Master an – so verpasst du keinen einzigen Pick. Dann spiele einfach, was der Master dir gibt, immer mit kontrolliertem Einsatz. So wird aus Wetten ein System statt Glücksspiel.",
    badge: "DIE GLOBALE TIPP-COMMUNITY", head: "Posten. Bewerten. Kassieren.",
    body: "Wirf deine Fußballtipps in den Jar. Unsere KI bewertet jeden Schein sofort, die Community bewertet mit – und erfolgreiche Tipper verwandeln Münzen in echtes Geld.",
    info: "Hier gibt's NUR spielbare Tipps – niemals Gewinn-Benachrichtigungen. Einfach reinschauen & nachspielen, immer mit kontrolliertem Einsatz.",
    submit: "Tipp einwerfen", earn: "Münzen verdienen" },
  en: { lead: "Want to make money betting? Then you need this page. Sign up, enable your location, pick your language and turn on the Master in notifications — so you never miss a single pick. Then just play what the Master gives you, always with a controlled stake. That turns betting into a system instead of gambling.",
    badge: "THE GLOBAL TIP COMMUNITY", head: "Post. Rate. Cash in.",
    body: "Drop your football tips into the jar. Our AI rates every slip instantly, the community rates too — and successful tipsters turn coins into real money.",
    info: "Only playable tips here — never win notifications. Just check in & replay, always with a controlled stake.",
    submit: "Drop a tip", earn: "Earn coins" },
  es: { lead: "¿Quieres ganar dinero apostando? Entonces necesitas esta página. Regístrate, activa tu ubicación, elige tu idioma y activa el Master en las notificaciones — así no te pierdes ningún pick. Luego juega lo que el Master te da, siempre con apuesta controlada. Así apostar se vuelve un sistema, no azar.",
    badge: "LA COMUNIDAD GLOBAL DE PRONÓSTICOS", head: "Publica. Valora. Cobra.",
    body: "Lanza tus pronósticos de fútbol al jar. Nuestra IA valora cada boleto al instante, la comunidad también — y los tipsters exitosos convierten monedas en dinero real.",
    info: "Aquí solo hay pronósticos jugables — nunca avisos de ganancias. Solo mira y repite, siempre con apuesta controlada.",
    submit: "Lanzar pronóstico", earn: "Ganar monedas" },
  el: { lead: "Θέλεις να βγάλεις χρήματα με στοιχήματα; Τότε χρειάζεσαι αυτή τη σελίδα. Κάνε εγγραφή, ενεργοποίησε την τοποθεσία, διάλεξε γλώσσα και άναψε τον Master στις ειδοποιήσεις — για να μη χάνεις κανένα pick. Μετά παίξε ό,τι σου δίνει ο Master, πάντα με ελεγχόμενο ποντάρισμα.",
    badge: "Η ΠΑΓΚΟΣΜΙΑ ΚΟΙΝΟΤΗΤΑ TIP", head: "Πόσταρε. Βαθμολόγησε. Εισέπραξε.",
    body: "Ρίξε τα ποδοσφαιρικά σου tips στο jar. Η ΤΝ βαθμολογεί κάθε δελτίο αμέσως, η κοινότητα επίσης — και οι επιτυχημένοι μετατρέπουν νομίσματα σε πραγματικά χρήματα.",
    info: "Εδώ μόνο παίξιμα tips — ποτέ ειδοποιήσεις κέρδους. Απλά δες & ξαναπαίξε, πάντα με ελεγχόμενο ποντάρισμα.",
    submit: "Ρίξε tip", earn: "Κέρδισε νομίσματα" },
  fr: { lead: "Tu veux gagner de l'argent en pariant ? Alors il te faut cette page. Inscris-toi, active ta localisation, choisis ta langue et active le Master dans les notifications — pour ne rater aucun pronostic. Ensuite joue ce que le Master te donne, toujours avec une mise contrôlée.",
    badge: "LA COMMUNAUTÉ MONDIALE DE PRONOS", head: "Poste. Note. Encaisse.",
    body: "Dépose tes pronos foot dans le jar. Notre IA note chaque ticket instantanément, la communauté aussi — et les tipsters gagnants transforment les pièces en argent réel.",
    info: "Ici uniquement des pronos jouables — jamais de notifs de gains. Regarde & rejoue, toujours avec une mise contrôlée.",
    submit: "Déposer un prono", earn: "Gagner des pièces" },
  it: { lead: "Vuoi guadagnare con le scommesse? Allora ti serve questa pagina. Registrati, attiva la posizione, scegli la lingua e accendi il Master nelle notifiche — così non perdi nessun pick. Poi gioca ciò che il Master ti dà, sempre con puntata controllata.",
    badge: "LA COMMUNITY GLOBALE DEI TIP", head: "Pubblica. Valuta. Incassa.",
    body: "Butta i tuoi pronostici di calcio nel jar. La nostra IA valuta ogni schedina subito, la community pure — e i tipster vincenti trasformano le monete in denaro vero.",
    info: "Qui solo tip giocabili — mai notifiche di vincita. Guarda & rigioca, sempre con puntata controllata.",
    submit: "Butta un tip", earn: "Guadagna monete" },
  ar: { lead: "هل تريد كسب المال من الرهانات؟ إذًا تحتاج هذه الصفحة. سجّل، فعّل موقعك، اختر لغتك وشغّل الماستر في الإشعارات — كي لا تفوّت أي توقع. ثم العب ما يعطيك الماستر، دائمًا برهان محكوم.",
    badge: "مجتمع التوقعات العالمي", head: "انشر. قيّم. اقبض.",
    body: "ألقِ توقعاتك الكروية في الجرة. يقيّم الذكاء الاصطناعي كل قسيمة فورًا، والمجتمع أيضًا — والمتوقعون الناجحون يحوّلون العملات إلى مال حقيقي.",
    info: "هنا توقعات قابلة للعب فقط — لا إشعارات أرباح أبدًا. فقط اطّلع وأعِد اللعب برهان محكوم.",
    submit: "ألقِ توقعًا", earn: "اكسب عملات" },
  tr: { lead: "Bahisle para kazanmak mı istiyorsun? O zaman bu sayfa şart. Kayıt ol, konumunu aç, dilini seç ve bildirimlerde Master'ı aç — hiçbir tahmini kaçırma. Sonra Master ne verirse onu oyna, hep kontrollü bahisle. Böylece bahis kumar değil sistem olur.",
    badge: "KÜRESEL TAHMİN TOPLULUĞU", head: "Paylaş. Puanla. Kazan.",
    body: "Futbol tahminlerini jar'a at. Yapay zekamız her kuponu anında puanlar, topluluk da puanlar — ve başarılı tahminciler jetonları gerçek paraya çevirir.",
    info: "Burada sadece oynanabilir tahminler — asla kazanç bildirimi yok. Sadece bak & tekrar oyna, hep kontrollü bahisle.",
    submit: "Tahmin at", earn: "Jeton kazan" },
};

export default function Raster4_Money({ lang = "de", batteryCoins = 0, onSubmit, onEarn }) {
  const t = T[lang] || T.de;
  const rtl = lang === "ar";
  return (
    <section className="px-4 py-4" dir={rtl ? "rtl" : "ltr"} data-testid="raster4-money">
      <div className="max-w-5xl mx-auto rounded-2xl border border-elevated bg-surface p-5">
        <div className="flex items-start gap-2.5 mb-5">
          <Crown size={18} className="text-[#E11D2A] shrink-0 mt-0.5" />
          <p className="text-sm text-zinc-300 leading-relaxed">{t.lead}</p>
        </div>

        <span className="inline-block bg-volt text-void text-[10px] font-black uppercase tracking-[0.15em] px-3 py-1 rounded-full" data-testid="r4-community-badge">{t.badge}</span>
        <h2 className="font-heading text-2xl sm:text-3xl font-black text-white tracking-tight mt-3">{t.head}</h2>
        <p className="text-sm text-zinc-400 leading-relaxed mt-2">{t.body}</p>
        <div className="mt-4 rounded-xl border border-volt/40 bg-volt/10 px-4 py-3">
          <p className="text-xs sm:text-sm font-semibold text-white leading-snug">{t.info}</p>
        </div>

        <div className="mt-5">
          <CoinBattery current={batteryCoins} max={2500} />
        </div>

        <div className="flex flex-wrap gap-3 mt-4">
          <button onClick={onSubmit} data-testid="r4-submit-btn"
            className="flex items-center gap-2 rounded-full bg-volt text-void font-bold px-6 py-3.5 hover:bg-volt-hover active:scale-95 transition-all shadow-[0_0_30px_rgba(225,255,0,0.3)]">
            <Sparkles size={18} /> {t.submit}
          </button>
          <button onClick={onEarn} data-testid="r4-earn-btn"
            className="flex items-center gap-2 rounded-full border border-volt/40 bg-volt/10 text-volt font-bold px-6 py-3.5 hover:bg-volt/20 active:scale-95 transition-all">
            <Coins size={18} /> {t.earn}
          </button>
        </div>
      </div>
    </section>
  );
}
