import React, { useState, useEffect, useCallback, useRef } from "react";
import "./App.css";
import { BrowserRouter, Routes, Route, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Toaster, toast } from "sonner";
import { Sparkles, Loader2, CheckCircle2, MailWarning, X, Coins } from "lucide-react";

import { I18nProvider, useI18n } from "./i18n";
import { AuthProvider, useAuth } from "./auth";
import api from "./api";

import Header from "./components/Header";
import PromoBanner from "./components/PromoBanner";
import AnimatedJar from "./components/AnimatedJar";
import RateWall from "./components/RateWall";
import StatisticsView from "./components/StatisticsView";
import ExpertsShowcase from "./components/ExpertsShowcase";
import NotificationPrompt from "./components/NotificationPrompt";
import AuthModal from "./components/AuthModal";
import SubmitTipModal from "./components/SubmitTipModal";
import WalletModal from "./components/WalletModal";
import ProfileModal from "./components/ProfileModal";
import PublicProfileModal from "./components/PublicProfileModal";
import InviteSection from "./components/InviteSection";
import HallOfFame from "./components/HallOfFame";
import WinClaimModal from "./components/WinClaimModal";
import SplashScreen from "./components/SplashScreen";
import { Disclaimer, DisclaimerBar } from "./components/Disclaimer";
import LegalModal from "./components/LegalModal";
import SecretInsights from "./components/SecretInsights";

const HERO_BG = "https://images.pexels.com/photos/35898730/pexels-photo-35898730.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=1080&w=1920";

// Small black & white checkered "finish flag" marker for the Settled area.
function CheckeredFlag({ size = 14 }) {
  return (
    <span
      aria-hidden
      style={{
        width: size, height: size, display: "inline-block", borderRadius: 3,
        border: "1px solid rgba(0,0,0,0.35)",
        background: "conic-gradient(#000 0 25%, #fff 0 50%, #000 0 75%, #fff 0) 0 0 / 7px 7px",
      }}
    />
  );
}

function Home() {
  const { t, setLang } = useI18n();
  const { user } = useAuth();
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState("login");
  const [submitOpen, setSubmitOpen] = useState(false);
  const [walletOpen, setWalletOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [winOpen, setWinOpen] = useState(false);
  const [legal, setLegal] = useState({ open: false, tab: "impressum" });
  const [tipsOpen, setTipsOpen] = useState(false);
  const [tipsView, setTipsView] = useState("ai");
  const [giftTarget, setGiftTarget] = useState("");
  const [profileUser, setProfileUser] = useState("");
  const [counts, setCounts] = useState({});
  const [seenCounts, setSeenCounts] = useState(() => {
    try { return JSON.parse(localStorage.getItem("tj_seen_counts")) || {}; } catch { return {}; }
  });
  const [refreshKey, setRefreshKey] = useState(0);
  const NAV_KEYS = ["ai", "smart", "systems", "members", "live", "settled"];
  const newCounts = {};
  NAV_KEYS.forEach((k) => { newCounts[k] = Math.max(0, (counts[k] || 0) - (seenCounts[k] || 0)); });

  // ── AI button bundled red count = sum of NEW picks across Banker/Value/Risk ──
  // Uses the SAME seen store (tj_cat_seen_ids) as the per-category tab badges so the
  // main button and the tabs stay perfectly in sync.
  const CAT_SEEN_KEY = "tj_cat_seen_ids";
  const aiIdsRef = useRef({ banker: [], value: [], risk: [] });
  const [aiUnread, setAiUnread] = useState(0);
  const catBucketOf = (tp) => (tp.category === "risk" ? "risk" : tp.category === "banker" ? "banker" : "value");
  const readCatSeen = () => {
    try { return JSON.parse(localStorage.getItem(CAT_SEEN_KEY) || "{}"); } catch { return {}; }
  };
  const computeAiUnread = useCallback(async () => {
    try {
      const { data } = await api.get("/tips", { params: { source: "ai", status: "pending", limit: 300 } });
      const seen = readCatSeen();
      const byCat = { banker: [], value: [], risk: [] };
      let unread = 0;
      data.forEach((tp) => {
        const c = catBucketOf(tp);
        byCat[c].push(tp.id);
        if (!(seen[c] || []).includes(tp.id)) unread += 1;
      });
      aiIdsRef.current = byCat;
      setAiUnread(unread);
    } catch { /* ignore */ }
  }, []);
  useEffect(() => {
    computeAiUnread();
    const iv = setInterval(computeAiUnread, 20000);
    const onSeen = () => computeAiUnread();
    window.addEventListener("tj-cat-seen", onSeen);
    return () => { clearInterval(iv); window.removeEventListener("tj-cat-seen", onSeen); };
  }, [computeAiUnread, refreshKey]);
  newCounts.ai = aiUnread;

  useEffect(() => { if (user?.language) setLang(user.language); }, [user, setLang]);

  useEffect(() => {
    const ref = new URLSearchParams(window.location.search).get("ref");
    if (ref) localStorage.setItem("tj_ref", ref);
  }, []);

  useEffect(() => {
    const openTips = () => setTipsOpen(true);
    window.addEventListener("tj-open-tips", openTips);
    return () => window.removeEventListener("tj-open-tips", openTips);
  }, []);

  useEffect(() => {
    const loadCounts = async () => {
      try {
        const { data } = await api.get("/tips/counts");
        setCounts(data);
        // first ever load → treat everything as already seen (no badges on fresh visit)
        if (!localStorage.getItem("tj_seen_counts")) {
          localStorage.setItem("tj_seen_counts", JSON.stringify(data));
          setSeenCounts(data);
        }
      } catch { /* ignore */ }
    };
    loadCounts();
    const iv = setInterval(loadCounts, 20000);
    return () => clearInterval(iv);
  }, [refreshKey]);

  const openAuth = (mode) => { setAuthMode(mode); setAuthOpen(true); };
  const requireLogin = useCallback(() => openAuth("login"), []);
  const onPublished = () => setRefreshKey((k) => k + 1);

  const openGiftTo = useCallback((username) => {
    if (!username) return;
    if (!user) { requireLogin(); return; }
    if (username === user.username) return;
    setGiftTarget(username);
    setWalletOpen(true);
  }, [user, requireLogin]);

  const openProfile = useCallback((username) => {
    if (username) setProfileUser(username);
  }, []);

  const openTipsView = (view) => {
    setTipsView(view);
    setTipsOpen(true);
    window.dispatchEvent(new Event("tj-viewed-pick"));
    // mark this section's tips as seen → clears its red "new" badge
    setSeenCounts((prev) => {
      const next = { ...prev, [view]: counts[view] || 0 };
      localStorage.setItem("tj_seen_counts", JSON.stringify(next));
      return next;
    });
    // Opening the AI picks marks all Banker/Value/Risk as seen → clears the bundled
    // main-button count AND the per-category tab badges (kept in sync).
    if (view === "ai") {
      const seen = readCatSeen();
      ["banker", "value", "risk"].forEach((c) => { seen[c] = aiIdsRef.current[c] || []; });
      localStorage.setItem(CAT_SEEN_KEY, JSON.stringify(seen));
      setAiUnread(0);
      window.dispatchEvent(new Event("tj-cat-seen"));
    }
    if (view === "systems") {
      let tries = 0;
      const tick = () => {
        const el = document.getElementById("systeme");
        if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
        else if (tries++ < 25) setTimeout(tick, 120);
      };
      setTimeout(tick, 180);
    } else {
      setTimeout(() => document.querySelector('[data-testid="tips-window"]')?.scrollTo({ top: 0 }), 60);
    }
  };

  useEffect(() => {
    const h = (e) => openTipsView(e.detail || "ai");
    window.addEventListener("tj-open-view", h);
    return () => window.removeEventListener("tj-open-view", h);
  }, []);

  // Deep-link from a push notification: /?pick=<id>&area=<area> → open that area and
  // scroll straight to the pick (tapping an alert ports directly onto the pick).
  const jumpToPick = useCallback((area, pick) => {
    if (!pick) return;
    openTipsView(area || "ai");
    let tries = 0;
    const tick = () => {
      const el = document.getElementById(`pick-${pick}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.style.transition = "box-shadow 0.3s ease";
        el.style.boxShadow = "0 0 0 3px rgba(198,255,0,0.85)";
        setTimeout(() => { el.style.boxShadow = ""; }, 3200);
      } else if (tries++ < 40) {
        setTimeout(tick, 150);
      }
    };
    setTimeout(tick, 450);
  }, []);

  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const pick = sp.get("pick");
    const area = sp.get("area");
    if (pick) {
      jumpToPick(area || "ai", pick);
      window.history.replaceState({}, "", window.location.pathname);
    } else if (area) {
      openTipsView(area === "live_ai" ? "live" : area);
      window.history.replaceState({}, "", window.location.pathname);
    }
    const h = (e) => jumpToPick(e.detail?.area, e.detail?.id);
    window.addEventListener("tj-open-pick", h);
    return () => window.removeEventListener("tj-open-pick", h);
  }, [jumpToPick]);

  return (
    <div className="App grain min-h-screen overflow-x-hidden" id="top">
      <SplashScreen />
      <NotificationPrompt />
      <PromoBanner />
      <Header
        onSubmit={() => setSubmitOpen(true)}
        onLogin={() => openAuth("login")}
        onSignup={() => openAuth("signup")}
        onWallet={() => setWalletOpen(true)}
        onProfile={() => setProfileOpen(true)}
        onViewTips={() => openTipsView("ai")}
        onViewSystems={() => openTipsView("systems")}
        onViewMembers={() => openTipsView("members")}
        onViewLive={() => openTipsView("live")}
        onViewSmart={() => openTipsView("smart")}
        onViewScorers={() => openTipsView("scorers")}
        onViewSettled={() => openTipsView("settled")}
        onExpertClick={openProfile}
        counts={counts}
        newCounts={newCounts}
      />
      {user && !user.email_verified && <VerifyBanner />}

      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0">
          <img src={HERO_BG} alt="" className="w-full h-full object-cover opacity-20" />
          <div className="absolute inset-0 bg-gradient-to-b from-void/70 via-void/85 to-void" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 pt-16 pb-20 grid lg:grid-cols-2 gap-10 items-center">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="min-w-0">
            <span className="inline-flex items-center gap-2 rounded-full border border-volt/30 bg-volt/5 px-3 py-1.5 text-xs font-bold uppercase tracking-[0.15em] text-volt">
              <Sparkles size={13} /> {t("hero.badge")}
            </span>
            <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-black tracking-tighter leading-[1.08] text-white mt-5 pb-1 break-words">
              {t("hero.title")}
            </h1>
            <p className="text-lg text-zinc-400 mt-5 max-w-xl leading-relaxed">{t("hero.subtitle")}</p>
            <div className="flex flex-wrap gap-3 mt-8">
              <button data-testid="hero-submit-btn" onClick={() => setSubmitOpen(true)}
                className="flex items-center gap-2 rounded-full bg-volt text-void font-bold px-6 py-3.5 hover:bg-volt-hover active:scale-95 transition-all shadow-[0_0_30px_rgba(225,255,0,0.3)]">
                <Sparkles size={18} /> {t("hero.cta.submit")}
              </button>
              <button data-testid="hero-earn-btn" onClick={() => setWinOpen(true)}
                className="flex items-center gap-2 rounded-full border border-volt/40 bg-volt/10 text-volt font-bold px-6 py-3.5 hover:bg-volt/20 active:scale-95 transition-all">
                <Coins size={18} /> {t("win.earn")}
              </button>
            </div>
          </motion.div>

          <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.15 }} className="flex flex-col items-center gap-3">
            <AnimatedJar />
            <a
              href="https://tipjarglobal.com"
              data-testid="hero-logo-url"
              className="font-heading font-black text-lg sm:text-xl tracking-tight text-volt hover:text-volt-hover transition-colors drop-shadow-[0_0_12px_rgba(225,255,0,0.45)]"
            >
              Tipjarglobal.com
            </a>
          </motion.div>
        </div>
      </section>

      {/* EXPERTS — prominently at the top of the home page */}
      <ExpertsShowcase onExpertClick={openProfile} />

      {/* INTRO VIDEO — right under the logo / Tipjarglobal.com */}
      <section className="relative max-w-3xl mx-auto px-4 sm:px-6 pt-2 pb-10" data-testid="intro-video-section">
        <div className="rounded-3xl overflow-hidden border border-volt/25 bg-black shadow-[0_0_40px_rgba(225,255,0,0.12)]">
          <video
            data-testid="intro-video"
            src="/tipjar-intro.mp4"
            poster="/tipjar-crest.png"
            controls
            playsInline
            preload="metadata"
            className="w-full h-auto block"
          />
        </div>
      </section>

      {/* STORY */}
      <section id="how" className="relative max-w-4xl mx-auto px-4 sm:px-6 py-16 scroll-mt-20">
        <div className="rounded-3xl bg-surface border border-elevated p-8 md:p-12">
          <h2 className="font-heading text-3xl md:text-4xl font-black text-white tracking-tighter">{t("hero.story.title")}</h2>
          <p className="text-zinc-400 mt-5 text-lg leading-relaxed">{t("hero.story")}</p>

          <div className="mt-8 pt-8 border-t border-elevated">
            <span className="inline-flex items-center gap-2 text-volt font-bold text-xs uppercase tracking-[0.2em]" data-testid="story-why-label">{t("story.why.label")}</span>
            <h3 className="font-heading text-2xl md:text-3xl font-black text-white tracking-tight mt-3" data-testid="story-why-title">{t("story.why.title")}</h3>
            <p className="text-zinc-400 mt-4 text-base md:text-lg leading-relaxed" data-testid="story-why-body">{t("story.why.body")}</p>
            <div className="mt-5 rounded-xl bg-volt/5 border-l-2 border-volt pl-4 py-3">
              <p className="text-base md:text-lg leading-relaxed text-zinc-200" data-testid="story-advantage">{t("story.why.advantage")}</p>
            </div>
            <p className="mt-6 text-sm text-zinc-500 leading-relaxed border border-dashed border-elevated rounded-xl px-4 py-3" data-testid="story-not">{t("story.not")}</p>
            <p className="mt-8 text-lg md:text-xl font-heading font-bold text-white leading-snug" data-testid="story-cta">{t("story.cta")}</p>
          </div>
        </div>
      </section>

      <InviteSection />
      <div id="best-wins">
        <HallOfFame refreshKey={refreshKey} onEarn={() => setWinOpen(true)} onUserClick={openProfile} />
      </div>

      <footer className="border-t border-elevated py-10 text-center px-4">
        <div className="inline-flex flex-col items-center leading-none" data-testid="footer-logo">
          <span className="font-heading font-black text-xl text-white">Tip<span className="text-volt">Jar</span></span>
          <span className="font-heading font-black text-[0.6rem] uppercase tracking-[0.25em] text-orange-500 -mt-0.5">global</span>
        </div>
        <p className="text-xs text-zinc-600 mt-2 mb-6">Post it. Rate it. Cash it.</p>
        <div className="flex items-center justify-center gap-4 mb-6 text-xs" data-testid="footer-legal-links">
          <button onClick={() => setLegal({ open: true, tab: "impressum" })} data-testid="footer-impressum" className="text-zinc-400 hover:text-volt transition-colors">Impressum</button>
          <span className="text-zinc-700">·</span>
          <button onClick={() => setLegal({ open: true, tab: "datenschutz" })} data-testid="footer-datenschutz" className="text-zinc-400 hover:text-volt transition-colors">Datenschutz</button>
          <span className="text-zinc-700">·</span>
          <button onClick={() => setLegal({ open: true, tab: "agb" })} data-testid="footer-agb" className="text-zinc-400 hover:text-volt transition-colors">AGB</button>
        </div>
        <Disclaimer />
      </footer>

      {tipsOpen && (
        <div className="fixed inset-0 z-[100] bg-void grain overflow-y-auto" data-testid="tips-window">
          <div className="sticky top-0 z-10 flex flex-col gap-2 px-4 sm:px-6 py-3 bg-black/85 backdrop-blur-xl border-b border-white/10">
            <div className="flex items-center justify-between">
              <span className="font-heading font-black text-lg sm:text-xl text-white truncate">
                Tip<span className="text-volt">Jar</span>
              </span>
              <button
                onClick={() => setTipsOpen(false)}
                data-testid="tips-window-close"
                className="rounded-full p-2 text-zinc-400 hover:text-white hover:bg-elevated active:scale-90 transition-all shrink-0"
                aria-label={t("common.close")}
              >
                <X size={22} />
              </button>
            </div>
            <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
              {[["ai", "nav.viewtips"], ["smart", "nav.viewsmart"], ["systems", "nav.viewsystems"], ["members", "nav.viewmembers"], ["live", "nav.viewlive"], ["settled", "nav.viewsettled"], ["scorers", "nav.viewscorers"]].map(([v, lbl]) => {
                const active = tipsView === v;
                let cls;
                if (v === "members") {
                  cls = active ? "bg-[#FFC02E] text-black shadow-[0_0_14px_rgba(255,192,46,0.45)]" : "bg-[#FFC02E]/15 border border-[#FFC02E]/40 text-[#FFC02E] hover:bg-[#FFC02E]/25";
                } else if (v === "live") {
                  cls = `animate-pulse ${active ? "bg-[#2563eb] text-white shadow-[0_0_16px_rgba(37,99,235,0.55)]" : "bg-[#2563eb]/15 border border-[#2563eb]/50 text-blue-300 hover:bg-[#2563eb]/25"}`;
                } else if (v === "scorers") {
                  cls = active ? "bg-[#F9A8D4] text-black shadow-[0_0_14px_rgba(249,168,212,0.45)]" : "bg-[#F9A8D4]/15 border border-[#F9A8D4]/40 text-[#F9A8D4] hover:bg-[#F9A8D4]/25";
                } else if (v === "settled") {
                  cls = active ? "bg-white text-black shadow-[0_0_14px_rgba(255,255,255,0.35)]" : "bg-surface border border-white/40 text-white hover:bg-white/10";
                } else {
                  cls = active ? "bg-[#2ECC57] text-black" : "bg-surface border border-elevated text-zinc-300 hover:text-white";
                }
                return (
                <button
                  key={v}
                  data-testid={`tabview-${v}`}
                  onClick={() => openTipsView(v)}
                  className={`whitespace-nowrap flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-bold transition-colors ${cls}`}
                >
                  {v === "live" && <span className={`w-1.5 h-1.5 rounded-full ${active ? "bg-white" : "bg-blue-400"} ${(counts.live || 0) > 0 ? "animate-pulse" : ""}`} />}
                  {v === "settled" && <CheckeredFlag />}
                  {t(lbl)}
                  {counts[v] != null && (
                    <span className={`text-[10px] font-mono rounded-full px-1.5 ${active ? "bg-black/20" : "bg-void/60 text-zinc-400"}`}>{counts[v]}</span>
                  )}
                </button>
                );
              })}
            </div>
          </div>
          <DisclaimerBar />
          {tipsView === "scorers" ? (
            <StatisticsView />
          ) : (
            <RateWall refreshKey={refreshKey} requireLogin={requireLogin} view={tipsView} onUserClick={openProfile} />
          )}
        </div>
      )}

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} initialMode={authMode} />
      <SubmitTipModal open={submitOpen} onClose={() => setSubmitOpen(false)} onPublished={onPublished} requireLogin={() => { setSubmitOpen(false); requireLogin(); }} />
      <WalletModal open={walletOpen} onClose={() => { setWalletOpen(false); setGiftTarget(""); }}
        initialTab={giftTarget ? "gift" : "buy"} initialGiftTo={giftTarget} />
      <PublicProfileModal
        open={!!profileUser}
        username={profileUser}
        onClose={() => setProfileUser("")}
        onGift={(u) => { setProfileUser(""); openGiftTo(u); }}
      />
      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)} />
      <WinClaimModal open={winOpen} onClose={() => setWinOpen(false)}
        requireLogin={() => { setWinOpen(false); requireLogin(); }} onClaimed={onPublished}
        onViewBestWins={() => document.getElementById("best-wins")?.scrollIntoView({ behavior: "smooth" })} />
      <LegalModal open={legal.open} initialTab={legal.tab} onClose={() => setLegal({ open: false, tab: legal.tab })} />
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
  useEffect(() => {
    try {
      let vid = localStorage.getItem("tj_vid");
      if (!vid) {
        vid = (window.crypto && window.crypto.randomUUID)
          ? window.crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        localStorage.setItem("tj_vid", vid);
      }
      if (!sessionStorage.getItem("tj_visit_sent")) {
        api.post("/track/visit", { visitor_id: vid, path: window.location.pathname }).catch(() => {});
        sessionStorage.setItem("tj_visit_sent", "1");
      }
    } catch { /* ignore */ }
  }, []);

  return (
    <I18nProvider>
      <AuthProvider>
        <Toaster theme="dark" position="top-center" richColors toastOptions={{ style: { background: "#18181b", border: "1px solid #27272a", color: "#fff" } }} />
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/credits/success" element={<CreditsSuccess />} />
            <Route path="/verify" element={<VerifyEmail />} />
            <Route path="/insights" element={<SecretInsights />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </I18nProvider>
  );
}

export default App;
