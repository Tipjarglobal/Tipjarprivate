import React, { useState, useEffect, useCallback } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Toaster } from "sonner";
import { Sparkles, Star, Loader2, CheckCircle2, MailWarning } from "lucide-react";

import { I18nProvider, useI18n } from "./i18n";
import { AuthProvider, useAuth } from "./auth";
import api from "./api";

import Header from "./components/Header";
import AnimatedJar from "./components/AnimatedJar";
import RateWall from "./components/RateWall";
import Leaderboard from "./components/Leaderboard";
import AuthModal from "./components/AuthModal";
import SubmitTipModal from "./components/SubmitTipModal";
import WalletModal from "./components/WalletModal";
import ProfileModal from "./components/ProfileModal";
import InviteSection from "./components/InviteSection";

const HERO_BG = "https://images.pexels.com/photos/35898730/pexels-photo-35898730.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=1080&w=1920";

function Home() {
  const { t, setLang } = useI18n();
  const { user } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [submitOpen, setSubmitOpen] = useState(false);
  const [walletOpen, setWalletOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => { if (user?.language) setLang(user.language); }, [user, setLang]);

  useEffect(() => {
    const ref = new URLSearchParams(window.location.search).get("ref");
    if (ref) localStorage.setItem("tj_ref", ref);
  }, []);

  const openAuth = (mode) => { setAuthMode(mode); setAuthOpen(true); };
  const requireLogin = useCallback(() => openAuth("login"), []);
  const onPublished = () => setRefreshKey((k) => k + 1);

  return (
    <div className="App grain min-h-screen" id="top">
      <Header
        onSubmit={() => setSubmitOpen(true)}
        onLogin={() => openAuth("login")}
        onSignup={() => openAuth("signup")}
        onWallet={() => setWalletOpen(true)}
        onProfile={() => setProfileOpen(true)}
      />
      {user && !user.email_verified && <VerifyBanner />}

      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img src={HERO_BG} alt="" className="w-full h-full object-cover opacity-20" />
          <div className="absolute inset-0 bg-gradient-to-b from-void/70 via-void/85 to-void" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-20 grid lg:grid-cols-2 gap-10 items-center">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <span className="inline-flex items-center gap-2 rounded-full border border-volt/30 bg-volt/5 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-volt">
              <Sparkles size={13} /> {t("hero.badge")}
            </span>
            <h1 className="font-heading text-5xl md:text-7xl font-black tracking-tighter leading-[0.95] text-white mt-5">
              {t("hero.title")}
            </h1>
            <p className="text-lg text-zinc-400 mt-5 max-w-xl leading-relaxed">{t("hero.subtitle")}</p>
            <div className="flex flex-wrap gap-3 mt-8">
              <button data-testid="hero-submit-btn" onClick={() => setSubmitOpen(true)}
                className="flex items-center gap-2 rounded-full bg-volt text-void font-bold px-6 py-3.5 hover:bg-volt-hover active:scale-95 transition-all shadow-[0_0_30px_rgba(225,255,0,0.3)]">
                <Sparkles size={18} /> {t("hero.cta.submit")}
              </button>
              <a href="#ratewall" data-testid="hero-rate-btn"
                className="flex items-center gap-2 rounded-full border border-elevated text-white font-bold px-6 py-3.5 hover:border-volt/60 hover:bg-white/5 active:scale-95 transition-all">
                <Star size={18} /> {t("hero.cta.rate")}
              </a>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.15 }} className="flex justify-center">
            <AnimatedJar />
          </motion.div>
        </div>
      </section>

      {/* STORY */}
      <section id="how" className="relative max-w-4xl mx-auto px-4 sm:px-6 py-16 scroll-mt-20">
        <div className="rounded-3xl bg-surface border border-elevated p-8 md:p-12">
          <h2 className="font-heading text-3xl md:text-4xl font-black text-white tracking-tighter">{t("hero.story.title")}</h2>
          <p className="text-zinc-400 mt-5 text-lg leading-relaxed">{t("hero.story")}</p>
        </div>
      </section>

      <RateWall refreshKey={refreshKey} requireLogin={requireLogin} />
      <InviteSection />
      <Leaderboard refreshKey={refreshKey} />

      <footer className="border-t border-elevated py-10 text-center">
        <div className="font-heading font-black text-xl text-white">Tip<span className="text-volt">Jar</span></div>
        <p className="text-xs text-zinc-600 mt-2">Post it. Rate it. Cash it. · 18+ · Play responsibly</p>
      </footer>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} initialMode={authMode} />
      <SubmitTipModal open={submitOpen} onClose={() => setSubmitOpen(false)} onPublished={onPublished} requireLogin={() => { setSubmitOpen(false); requireLogin(); }} />
      <WalletModal open={walletOpen} onClose={() => setWalletOpen(false)} />
      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} />
    </div>
  );
}

function CreditsSuccess() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [state, setState] = useState("checking");
  const [credits, setCredits] = useState(0);

  useEffect(() => {
    const sid = params.get("session_id");
    if (!sid) { navigate("/"); return; }
    let attempts = 0;
    const poll = async () => {
      try {
        const { data } = await api.get(`/credits/checkout/status/${sid}`);
        if (data.payment_status === "paid") {
          setState("done"); setUser(data.user); setCredits(data.user.credits);
          return;
        }
        if (data.status === "expired" || attempts >= 6) { setState("failed"); return; }
        attempts += 1;
        setTimeout(poll, 2000);
      } catch { setState("failed"); }
    };
    poll();
  }, [params, navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-void grain px-4">
      <div className="text-center max-w-md">
        {state === "checking" && (<><Loader2 className="mx-auto text-volt animate-spin mb-4" size={48} /><p className="text-white text-lg">Confirming your payment…</p></>)}
        {state === "done" && (<>
          <CheckCircle2 className="mx-auto text-won mb-4" size={56} />
          <h2 className="font-heading text-3xl font-black text-white">Credits added! 🎉</h2>
          <p className="text-zinc-400 mt-2">Your balance is now <span className="font-mono font-bold text-volt">{credits}</span> credits.</p>
          <button onClick={() => navigate("/")} className="mt-6 rounded-full bg-volt text-void font-bold px-6 py-3 hover:bg-volt-hover transition-colors" data-testid="success-home">Back to TipJar</button>
        </>)}
        {state === "failed" && (<>
          <p className="text-lost text-lg mb-3">We couldn't confirm the payment.</p>
          <button onClick={() => navigate("/")} className="rounded-full border border-elevated text-white font-bold px-6 py-3 hover:border-volt transition-colors">Back to TipJar</button>
        </>)}
      </div>
    </div>
  );
}

function VerifyBanner() {
  const { t } = useI18n();
  const [sending, setSending] = useState(false);
  const resend = async () => {
    setSending(true);
    try {
      const { data } = await api.post("/auth/resend-verification", { origin_url: window.location.origin });
      toast.success(t("banner.resent"));
      if (data.verify_link) toast.message("Dev verify link: " + data.verify_link, { duration: 12000 });
    } catch { /* ignore */ } finally { setSending(false); }
  };
  return (
    <div data-testid="verify-banner" className="bg-bell/15 border-b border-bell/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-center gap-3 text-sm">
        <MailWarning size={16} className="text-bell shrink-0" />
        <span className="text-white">{t("banner.verify")}</span>
        <button data-testid="resend-verification" onClick={resend} disabled={sending}
          className="font-bold text-bell hover:underline disabled:opacity-50">{t("banner.resend")}</button>
      </div>
    </div>
  );
}

function VerifyEmail() {
  const { t } = useI18n();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const [state, setState] = useState("checking");
  const [reward, setReward] = useState(false);

  useEffect(() => {
    const token = params.get("token");
    if (!token) { setState("fail"); return; }
    api.post("/auth/verify-email", { token })
      .then(async (r) => {
        setState("success");
        setReward(r.data.referral_reward_granted);
        try { const me = await api.get("/auth/me"); setUser(me.data.user); } catch { /* not logged in */ }
      })
      .catch(() => setState("fail"));
  }, [params, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-void grain px-4">
      <div className="text-center max-w-md" data-testid="verify-page">
        {state === "checking" && (<><Loader2 className="mx-auto text-volt animate-spin mb-4" size={48} /><p className="text-white text-lg">{t("verify.checking")}</p></>)}
        {state === "success" && (<>
          <CheckCircle2 className="mx-auto text-won mb-4" size={56} />
          <h2 className="font-heading text-3xl font-black text-white">{t("verify.success")}</h2>
          <p className="text-zinc-400 mt-2">{reward ? t("verify.reward") : t("verify.done")}</p>
          <button onClick={() => navigate("/")} className="mt-6 rounded-full bg-volt text-void font-bold px-6 py-3 hover:bg-volt-hover transition-colors" data-testid="verify-home">{t("verify.home")}</button>
        </>)}
        {state === "fail" && (<>
          <MailWarning className="mx-auto text-lost mb-4" size={56} />
          <p className="text-lost text-lg mb-4">{t("verify.fail")}</p>
          <button onClick={() => navigate("/")} className="rounded-full border border-elevated text-white font-bold px-6 py-3 hover:border-volt transition-colors" data-testid="verify-home">{t("verify.home")}</button>
        </>)}
      </div>
    </div>
  );
}

function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <Toaster theme="dark" position="top-center" richColors toastOptions={{ style: { background: "#18181b", border: "1px solid #27272a", color: "#fff" } }} />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/credits/success" element={<CreditsSuccess />} />
            <Route path="/verify" element={<VerifyEmail />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </I18nProvider>
  );
}

export default App;
