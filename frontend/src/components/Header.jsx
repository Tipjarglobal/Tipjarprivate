import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Globe, Clock, Wallet, User, LogOut, ChevronDown, Plus, Download, Layers, Users, Radio, Sparkles, Brain, Flag, MessageCircle, Target, Crown, Info, Share2, PlusSquare, ScanLine } from "lucide-react";
import { toast } from "sonner";
import NotificationBell from "./NotificationBell";
import Mailbox from "./Mailbox";
import { useI18n, LANGUAGES, TIMEZONES } from "../i18n";
import { useAuth } from "../auth";

function InstallAppButton() {
  const { t } = useI18n();
  const [deferred, setDeferred] = useState(null);
  const [hidden, setHidden] = useState(false);
  const [guide, setGuide] = useState(null); // 'ios' | 'menu' | null
  useEffect(() => {
    const onPrompt = (e) => { e.preventDefault(); setDeferred(e); };
    const onInstalled = () => setHidden(true);
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    const standalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone;
    if (standalone) setHidden(true);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);
  if (hidden) return null;
  // iOS Safari can't be triggered programmatically (no beforeinstallprompt), and iPadOS often
  // reports a desktop UA → also treat touch-Macs as iOS. Show a clear step-by-step dialog.
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  const click = async () => {
    if (deferred) {
      deferred.prompt();
      const res = await deferred.userChoice;
      if (res && res.outcome === "accepted") toast.success(t("install.installing"));
      setDeferred(null);
    } else {
      setGuide(isIOS ? "ios" : "menu");
    }
  };
  return (
    <>
      <button
        data-testid="download-app-btn"
        onClick={click}
        className="flex items-center gap-1.5 rounded-full border border-volt/50 bg-volt/10 text-volt font-bold text-sm px-2 py-1.5 sm:px-3 sm:py-2 hover:bg-volt/20 active:scale-95 transition-all"
      >
        <Download size={15} className="sm:hidden" /><Download size={16} className="hidden sm:block" /> <span className="hidden sm:inline">{t("nav.download")}</span>
      </button>
      <AnimatePresence>
        {guide && (
          <motion.div
            data-testid="install-guide-overlay"
            className="fixed inset-0 z-[120] flex items-end sm:items-center justify-center bg-black/70 backdrop-blur-sm p-4"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={() => setGuide(null)}
          >
            <motion.div
              className="w-full max-w-md rounded-2xl border border-volt/30 bg-[#0d0d0f] p-6 shadow-2xl"
              initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 40, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 28 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-2.5 mb-4">
                <span className="grid place-items-center w-10 h-10 rounded-xl bg-volt/15 text-volt"><Download size={20} /></span>
                <h3 className="font-heading font-black text-lg text-white leading-tight">{t("install.guide.title")}</h3>
              </div>
              {guide === "ios" ? (
                <ol className="space-y-3 text-sm text-zinc-300">
                  <li className="flex gap-3"><span className="shrink-0 grid place-items-center w-6 h-6 rounded-full bg-volt text-void font-black text-xs">1</span>
                    <span>{t("install.ios.step1")} <Share2 size={15} className="inline-block align-text-bottom text-sky-300" /></span></li>
                  <li className="flex gap-3"><span className="shrink-0 grid place-items-center w-6 h-6 rounded-full bg-volt text-void font-black text-xs">2</span>
                    <span>{t("install.ios.step2")} <PlusSquare size={15} className="inline-block align-text-bottom text-sky-300" /></span></li>
                  <li className="flex gap-3"><span className="shrink-0 grid place-items-center w-6 h-6 rounded-full bg-volt text-void font-black text-xs">3</span>
                    <span>{t("install.ios.step3")}</span></li>
                </ol>
              ) : (
                <p className="text-sm text-zinc-300 leading-relaxed">{t("install.menu")}</p>
              )}
              <button
                data-testid="install-guide-close"
                onClick={() => setGuide(null)}
                className="mt-6 w-full rounded-full bg-volt text-void font-black py-2.5 hover:brightness-110 active:scale-95 transition-all"
              >
                {t("common.close")}
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default function Header({ onSubmit, onLogin, onSignup, onWallet, onProfile, onViewTips, onViewMaster, onViewSystems, onViewMembers, onViewLiveCommunity, onViewLive, onViewSmart, onViewScorers, onViewSettled, onViewCodeReading, counts = {}, newCounts = {} }) {
  const { t, lang, setLang, tz, setTz } = useI18n();
  const { user, logout } = useAuth();
  const [langOpen, setLangOpen] = useState(false);
  const [tzOpen, setTzOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const langRef = useRef();
  const tzRef = useRef();
  const menuRef = useRef();

  useEffect(() => {
    const h = (e) => {
      if (langRef.current && !langRef.current.contains(e.target)) setLangOpen(false);
      if (tzRef.current && !tzRef.current.contains(e.target)) setTzOpen(false);
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  // Apply the account's chosen timezone as the default (only if the viewer hasn't
  // already picked one in this browser).
  useEffect(() => {
    if (user && user.timezone) {
      try { if (!localStorage.getItem("tj_tz")) setTz(user.timezone); } catch { /* ignore */ }
    }
  }, [user, setTz]);

  const cur = LANGUAGES.find((l) => l.code === lang) || LANGUAGES[0];
  const curTz = TIMEZONES.find((z) => z.tz === tz);

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-black/60 border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-3">
        <a href="#top" className="flex flex-col shrink-0 leading-none select-none" data-testid="logo">
          <span className="font-heading font-black text-xl tracking-tighter text-white">Tip<span className="text-volt">Jar</span></span>
          <span className="font-heading font-black text-[0.6rem] uppercase tracking-[0.25em] text-orange-500 -mt-0.5 self-start pl-0.5">global</span>
        </a>

        <nav className="hidden lg:flex items-center gap-6 text-sm font-semibold text-zinc-300">
          <button type="button" onClick={onViewTips} className="hover:text-volt transition-colors" data-testid="nav-ratewall">{t("nav.ratewall")}</button>
          <a href="#how" className="hover:text-volt transition-colors" data-testid="nav-how">{t("nav.how")}</a>
          <a href="#invite" className="hover:text-volt transition-colors" data-testid="nav-invite">{t("nav.invite")}</a>
        </nav>

        <div className="flex items-center gap-1 sm:gap-2.5">
          <InstallAppButton />
          <NotificationBell />
          <Mailbox />

          {/* language switcher */}
          <div className="relative" ref={langRef}>
            <button data-testid="language-switcher" onClick={() => setLangOpen(!langOpen)}
              className="flex items-center gap-1 rounded-full border border-elevated px-2 py-1.5 sm:px-2.5 sm:py-2 text-sm text-zinc-300 hover:border-volt/50 transition-colors">
              <Globe size={15} /> <span className="hidden sm:inline">{cur.flag}</span> <ChevronDown size={13} />
            </button>
            <AnimatePresence>
              {langOpen && (
                <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                  className="absolute right-0 mt-2 z-[60] w-40 rounded-xl bg-surface border border-elevated p-1 shadow-2xl">
                  {LANGUAGES.map((l) => (
                    <button key={l.code} data-testid={`lang-${l.code}`} onClick={() => { setLang(l.code); setLangOpen(false); }}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${l.code === lang ? "bg-volt/10 text-volt" : "text-zinc-300 hover:bg-elevated"}`}>
                      <span>{l.flag}</span> {l.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* timezone switcher */}
          <div className="relative hidden sm:block" ref={tzRef}>
            <button data-testid="timezone-switcher" onClick={() => setTzOpen(!tzOpen)}
              className="flex items-center gap-1 rounded-full border border-elevated px-2 py-1.5 sm:px-2.5 sm:py-2 text-sm text-zinc-300 hover:border-volt/50 transition-colors">
              <Clock size={15} /> <span className="hidden md:inline text-xs font-semibold">{curTz ? curTz.label.split(" / ")[0] : tz}</span> <ChevronDown size={13} />
            </button>
            <AnimatePresence>
              {tzOpen && (
                <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                  className="absolute right-0 mt-2 z-[60] w-48 max-h-80 overflow-y-auto rounded-xl bg-surface border border-elevated p-1 shadow-2xl">
                  {TIMEZONES.map((z) => (
                    <button key={z.tz} data-testid={`tz-${z.tz}`} onClick={() => { setTz(z.tz); setTzOpen(false); }}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${z.tz === tz ? "bg-volt/10 text-volt" : "text-zinc-300 hover:bg-elevated"}`}>
                      {z.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {user ? (
            <>
              <button data-testid="wallet-chip" onClick={onWallet}
                className="flex items-center gap-1.5 rounded-full bg-volt/10 border border-volt/30 px-2 py-1.5 sm:px-3 sm:py-2 hover:bg-volt/20 transition-colors">
                <Wallet size={15} className="text-volt" />
                <span className="font-mono font-bold text-volt text-sm" data-testid="header-credits">{user.credits}</span>
              </button>
              <div className="relative" ref={menuRef}>
                <button data-testid="user-menu" onClick={() => setMenuOpen(!menuOpen)}
                  className="w-8 h-8 sm:w-9 sm:h-9 rounded-full bg-elevated border border-zinc-600 flex items-center justify-center font-bold text-sm text-white hover:border-volt transition-colors">
                  {user.username?.[0]?.toUpperCase() || "U"}
                </button>
                <AnimatePresence>
                  {menuOpen && (
                    <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                      className="absolute right-0 mt-2 z-[60] w-52 rounded-xl bg-surface border border-elevated p-1 shadow-2xl">
                      <div className="px-3 py-2 border-b border-elevated mb-1">
                        <p className="font-semibold text-white truncate">{user.username}</p>
                        <p className="text-xs text-zinc-500 truncate">{user.email}</p>
                        {user.role === "admin" && <span className="text-[10px] font-bold text-bell uppercase tracking-widest">Admin</span>}
                      </div>
                      <MenuItem testId="menu-wallet" icon={Wallet} label={t("nav.wallet")} onClick={() => { setMenuOpen(false); onWallet(); }} />
                      <MenuItem testId="menu-profile" icon={User} label={t("nav.profile")} onClick={() => { setMenuOpen(false); onProfile(); }} />
                      <MenuItem testId="menu-logout" icon={LogOut} label={t("nav.logout")} onClick={() => { setMenuOpen(false); logout(); }} />
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </>
          ) : (
            <>
              <button data-testid="login-btn" onClick={onLogin} className="hidden sm:block text-sm font-semibold text-zinc-300 hover:text-volt transition-colors px-2">{t("nav.login")}</button>
              <button data-testid="signup-btn" onClick={onSignup} className="rounded-full bg-volt text-void font-bold text-sm px-4 py-2 hover:bg-volt-hover active:scale-95 transition-all">{t("nav.signup")}</button>
            </>
          )}

          <button data-testid="header-submit-btn" onClick={onSubmit}
            className="flex items-center gap-1.5 rounded-full border border-volt/40 text-volt font-bold text-sm px-2.5 py-1.5 sm:px-3 sm:py-2 hover:bg-volt/10 active:scale-95 transition-all">
            <Plus size={16} /> <span className="hidden md:inline">{t("nav.submit")}</span>
          </button>
        </div>
      </div>

      {/* Quick-view green CTAs: stacked on mobile, row on desktop */}
      <div className="border-t border-white/5 px-4 sm:px-6 py-2.5">
        <div className="max-w-7xl mx-auto">
          <div data-testid="member-guide" className="mb-2.5 rounded-xl border border-[#E11D2A]/40 bg-gradient-to-r from-[#E11D2A]/12 via-[#E11D2A]/5 to-transparent px-4 py-2.5 flex items-start gap-2.5">
            <Crown size={16} className="text-[#E11D2A] shrink-0 mt-0.5" />
            <p className="text-xs sm:text-sm leading-snug">
              <span className="font-heading font-black text-white">{t("master.manual.title")} </span>
              <span className="text-zinc-300">{t("master.manual.body")}</span>
            </p>
          </div>
          <div data-testid="ai-correction-guide" className="mb-2.5 rounded-xl border border-sky-400/40 bg-gradient-to-r from-sky-400/12 via-sky-400/5 to-transparent px-4 py-2.5 flex items-start gap-2.5">
            <Info size={16} className="text-sky-300 shrink-0 mt-0.5" />
            <p className="text-xs sm:text-sm leading-snug">
              <span className="font-heading font-black text-sky-200">{t("ai.correct.guide.title")} </span>
              <span className="text-zinc-300">{t("ai.correct.guide.body")}</span>
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-9 gap-2">
            <QuickView onClick={onViewTips} icon={Sparkles} label={t("nav.viewtips")} testId="view-tips-btn" count={counts.ai} newCount={newCounts.ai} />
            <QuickView onClick={onViewSmart} icon={Brain} label={t("nav.viewsmart")} testId="view-smart-btn" count={counts.smart} newCount={newCounts.smart} spoiler={t("smart.spoiler")} />
            <QuickView onClick={onViewSystems} icon={Layers} label={t("nav.viewsystems")} testId="view-systems-btn" count={counts.systems} newCount={newCounts.systems} />
            <QuickView onClick={onViewMaster} icon={Crown} label={t("nav.viewmaster")} testId="view-master-btn" count={counts.master} newCount={newCounts.master} variant="master" />
            <QuickView onClick={onViewMembers} icon={Users} label={t("nav.viewmembers")} testId="view-members-btn" count={counts.members} newCount={newCounts.members} variant="gold" liveAction={onViewLiveCommunity} liveCount={counts.community_live} />
            <QuickView onClick={onViewLive} icon={Radio} label={t("nav.viewlive")} testId="view-live-btn" count={counts.live} newCount={newCounts.live} live variant="blue" />
            <QuickView onClick={onViewSettled} icon={Flag} label={t("nav.viewsettled")} testId="view-settled-btn" count={counts.settled} newCount={newCounts.settled} variant="checkered" />
            <QuickView onClick={onViewScorers} icon={Target} label={t("nav.viewscorers")} testId="view-scorers-btn" variant="pink" />
            <QuickView onClick={onViewCodeReading} icon={ScanLine} label="Codemining" testId="view-codereading-btn" variant="grey" count={counts.codereading} />
          </div>
        </div>
      </div>
    </header>
  );
}

function QuickView({ onClick, icon: Icon, label, testId, count, newCount = 0, live, variant = "green", spoiler, liveAction, liveCount }) {
  const variants = {
    green: "bg-[#2ECC57] text-black hover:bg-[#26b64c] shadow-[0_0_16px_rgba(46,204,87,0.3)]",
    master: "bg-[#E11D2A] text-white hover:bg-[#c4141f] shadow-[0_0_20px_rgba(225,29,42,0.55)]",
    pink: "bg-[#F9A8D4] text-black hover:bg-[#f48fc4] shadow-[0_0_16px_rgba(249,168,212,0.4)]",
    gold: "bg-[#E3A81B] text-black hover:bg-[#c8920f] shadow-[0_0_16px_rgba(227,168,27,0.45)]",
    blue: "bg-[#2563eb] text-white hover:bg-[#1d4fd8] shadow-[0_0_18px_rgba(37,99,235,0.55)] animate-pulse",
    checkered: "bg-white text-black hover:bg-zinc-200 shadow-[0_0_16px_rgba(255,255,255,0.25)]",
    grey: "bg-zinc-300 text-black hover:bg-zinc-200 shadow-[0_0_16px_rgba(212,212,216,0.3)]",
  };
  // Split button: main label (left) + an independently clickable small blue LIVE button (right).
  if (liveAction) {
    return (
      <div data-testid={`${testId}-wrap`}
        className={`relative flex items-center justify-between gap-1 w-full rounded-full font-heading font-black text-sm p-1 ${variants[variant] || variants.green}`}>
        {newCount > 0 && (
          <span data-testid={`${testId}-newbadge`}
            className="absolute -top-1.5 -right-1.5 z-10 min-w-[20px] h-5 px-1 flex items-center justify-center rounded-full bg-red-600 text-white text-[11px] font-black leading-none border-2 border-void shadow-[0_0_10px_rgba(220,38,38,0.7)] animate-pulse">
            {newCount > 99 ? "99+" : newCount}
          </span>
        )}
        <button type="button" onClick={onClick} data-testid={testId}
          className="flex items-center gap-2 min-w-0 flex-1 justify-start pl-3 pr-1 py-1.5 rounded-full active:scale-[0.98] transition-transform">
          <Icon size={16} strokeWidth={2.5} />
          <span className="truncate">{label}</span>
          {count != null && (
            <span data-testid={`${testId}-count`} className="min-w-[20px] text-center text-[11px] font-mono font-black rounded-full bg-black/25 px-1.5 py-0.5">
              {count}
            </span>
          )}
        </button>
        <button type="button" onClick={liveAction} data-testid={`${testId}-live`}
          className="flex items-center gap-1.5 shrink-0 rounded-full bg-[#2563eb] text-white px-2.5 py-1.5 text-[11px] uppercase tracking-wide hover:bg-[#1d4fd8] active:scale-95 shadow-[0_0_12px_rgba(37,99,235,0.6)] transition-all">
          <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" /> Live
          {liveCount > 0 && (
            <span className="min-w-[16px] text-center text-[10px] font-mono font-black rounded-full bg-black/25 px-1">{liveCount}</span>
          )}
        </button>
      </div>
    );
  }
  const btn = (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      className={`relative flex items-center ${spoiler ? "justify-between pl-4 pr-2" : "justify-center"} gap-2 w-full rounded-full font-heading font-black text-sm py-2.5 active:scale-[0.98] transition-all ${variants[variant] || variants.green}`}
    >
      {newCount > 0 && (
        <span
          data-testid={`${testId}-newbadge`}
          className="absolute -top-1.5 -right-1.5 z-10 min-w-[20px] h-5 px-1 flex items-center justify-center rounded-full bg-red-600 text-white text-[11px] font-black leading-none border-2 border-void shadow-[0_0_10px_rgba(220,38,38,0.7)] animate-pulse"
        >
          {newCount > 99 ? "99+" : newCount}
        </span>
      )}
      <span className="flex items-center gap-2 min-w-0">
        {live && count > 0 ? <span className={`w-2 h-2 rounded-full animate-pulse ${variant === "blue" ? "bg-white" : "bg-red-700"}`} /> : <Icon size={16} strokeWidth={2.5} />}
        <span className="truncate">{label}</span>
        {count != null && (
          <span data-testid={`${testId}-count`} className="min-w-[20px] text-center text-[11px] font-mono font-black rounded-full bg-black/25 px-1.5 py-0.5">
            {count}
          </span>
        )}
      </span>
      {spoiler && (
        <span
          data-testid={`${testId}-spoiler`}
          className="flex items-center gap-1 rounded-full bg-void text-volt border border-volt/60 px-2 py-1 text-[10px] font-bold whitespace-nowrap shrink-0 shadow-[0_0_12px_rgba(225,255,0,0.4)] animate-pulse"
        >
          <MessageCircle size={11} /> {spoiler}
        </span>
      )}
    </button>
  );
  return btn;
}

function MenuItem({ icon: Icon, label, onClick, testId }) {
  return (
    <button data-testid={testId} onClick={onClick} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-300 hover:bg-elevated hover:text-white transition-colors">
      <Icon size={16} /> {label}
    </button>
  );
}
