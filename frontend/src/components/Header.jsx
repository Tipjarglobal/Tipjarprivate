import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Globe, Wallet, User, LogOut, ChevronDown, Plus, Download, Layers, Users, Radio, Sparkles, Brain, Flag, MessageCircle, Star, Target } from "lucide-react";
import { toast } from "sonner";
import NotificationBell from "./NotificationBell";
import Mailbox from "./Mailbox";
import api from "../api";
import { useI18n, LANGUAGES, toLatin } from "../i18n";
import { useAuth } from "../auth";

function InstallAppButton() {
  const { t } = useI18n();
  const [deferred, setDeferred] = useState(null);
  const [hidden, setHidden] = useState(false);
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
  const click = async () => {
    if (deferred) {
      deferred.prompt();
      const res = await deferred.userChoice;
      if (res && res.outcome === "accepted") toast.success(t("install.installing"));
      setDeferred(null);
    } else if (/iphone|ipad|ipod/i.test(navigator.userAgent)) {
      toast(t("install.ios"), { duration: 6000 });
    } else {
      toast(t("install.menu"), { duration: 6000 });
    }
  };
  return (
    <button
      data-testid="download-app-btn"
      onClick={click}
      className="flex items-center gap-1.5 rounded-full border border-volt/50 bg-volt/10 text-volt font-bold text-sm px-2 py-1.5 sm:px-3 sm:py-2 hover:bg-volt/20 active:scale-95 transition-all"
    >
      <Download size={15} className="sm:hidden" /><Download size={16} className="hidden sm:block" /> <span className="hidden sm:inline">{t("nav.download")}</span>
    </button>
  );
}

export default function Header({ onSubmit, onLogin, onSignup, onWallet, onProfile, onViewTips, onViewSystems, onViewMembers, onViewLive, onViewSmart, onViewScorers, onViewSettled, onExpertClick, counts = {}, newCounts = {} }) {
  const { t, lang, setLang } = useI18n();
  const { user, logout } = useAuth();
  const [langOpen, setLangOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const langRef = useRef();
  const menuRef = useRef();

  useEffect(() => {
    const h = (e) => {
      if (langRef.current && !langRef.current.contains(e.target)) setLangOpen(false);
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const cur = LANGUAGES.find((l) => l.code === lang) || LANGUAGES[0];

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

      {/* Expert banner — under the logo, site-wide */}
      <ExpertBanner onExpertClick={onExpertClick} />

      {/* Quick-view green CTAs: stacked on mobile, row on desktop */}
      <div className="border-t border-white/5 px-4 sm:px-6 py-2.5">
        <div className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-7 gap-2">
          <QuickView onClick={onViewTips} icon={Sparkles} label={t("nav.viewtips")} testId="view-tips-btn" count={counts.ai} newCount={newCounts.ai} />
          <QuickView onClick={onViewSmart} icon={Brain} label={t("nav.viewsmart")} testId="view-smart-btn" count={counts.smart} newCount={newCounts.smart} spoiler={t("smart.spoiler")} />
          <QuickView onClick={onViewSystems} icon={Layers} label={t("nav.viewsystems")} testId="view-systems-btn" count={counts.systems} newCount={newCounts.systems} />
          <QuickView onClick={onViewMembers} icon={Users} label={t("nav.viewmembers")} testId="view-members-btn" count={counts.members} newCount={newCounts.members} variant="gold" />
          <QuickView onClick={onViewLive} icon={Radio} label={t("nav.viewlive")} testId="view-live-btn" count={counts.live} newCount={newCounts.live} live variant="blue" />
          <QuickView onClick={onViewSettled} icon={Flag} label={t("nav.viewsettled")} testId="view-settled-btn" count={counts.settled} newCount={newCounts.settled} variant="checkered" />
          <QuickView onClick={onViewScorers} icon={Target} label={t("nav.viewscorers")} testId="view-scorers-btn" variant="pink" />
        </div>
      </div>
    </header>
  );
}

function QuickView({ onClick, icon: Icon, label, testId, count, newCount = 0, live, variant = "green", spoiler }) {
  const variants = {
    green: "bg-[#2ECC57] text-black hover:bg-[#26b64c] shadow-[0_0_16px_rgba(46,204,87,0.3)]",
    pink: "bg-[#F9A8D4] text-black hover:bg-[#f48fc4] shadow-[0_0_16px_rgba(249,168,212,0.4)]",
    gold: "bg-[#FFC02E] text-black hover:bg-[#e6ac1f] shadow-[0_0_16px_rgba(255,192,46,0.4)]",
    blue: "bg-[#2563eb] text-white hover:bg-[#1d4fd8] shadow-[0_0_18px_rgba(37,99,235,0.55)] animate-pulse",
    checkered: "bg-white text-black hover:bg-zinc-200 shadow-[0_0_16px_rgba(255,255,255,0.25)]",
  };
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

function ExpertBanner({ onExpertClick }) {
  const { t } = useI18n();
  const [experts, setExperts] = useState([]);
  useEffect(() => {
    let alive = true;
    api.get("/experts").then((r) => { if (alive) setExperts(r.data.experts || []); }).catch(() => {});
    return () => { alive = false; };
  }, []);
  return (
    <div
      data-testid="expert-banner"
      className="border-t border-white/5 bg-gradient-to-r from-orange-500/15 via-amber-500/5 to-transparent px-4 sm:px-6 py-2.5"
    >
      <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="flex items-center gap-1.5 text-sm font-heading font-black text-orange-400">
          <Star size={15} /> {t("expert.banner.title")}
        </span>
        <span className="text-xs text-zinc-400">{t("expert.banner.sub")}</span>
        <div className="flex items-center gap-2 flex-wrap">
          {experts.length === 0 ? (
            <span className="text-xs text-zinc-600">{t("expert.banner.none")}</span>
          ) : experts.map((e) => (
            <button
              key={e.username}
              type="button"
              data-testid={`expert-chip-${e.username}`}
              onClick={() => onExpertClick?.(e.username)}
              className="flex items-center gap-1.5 rounded-full bg-orange-500/15 border border-orange-500/40 px-2.5 py-1 text-xs font-bold text-orange-300 hover:bg-orange-500/25 active:scale-95 transition-all"
            >
              <span className="w-4 h-4 rounded-full bg-orange-500 text-void flex items-center justify-center text-[9px] font-black">
                {e.username?.[0]?.toUpperCase() || "?"}
              </span>
              {toLatin(e.username)}{e.apex_flame ? " 🔥" : ""}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function MenuItem({ icon: Icon, label, onClick, testId }) {
  return (
    <button data-testid={testId} onClick={onClick} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-300 hover:bg-elevated hover:text-white transition-colors">
      <Icon size={16} /> {label}
    </button>
  );
}
