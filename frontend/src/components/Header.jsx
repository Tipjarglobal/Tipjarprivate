import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Globe, Wallet, User, LogOut, ChevronDown, Plus, Download } from "lucide-react";
import { toast } from "sonner";
import NotificationBell from "./NotificationBell";
import { useI18n, LANGUAGES } from "../i18n";
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
      className="flex items-center gap-1.5 rounded-full border border-volt/50 bg-volt/10 text-volt font-bold text-sm px-3 py-2 hover:bg-volt/20 active:scale-95 transition-all"
    >
      <Download size={16} /> <span className="hidden sm:inline">{t("nav.download")}</span>
    </button>
  );
}

export default function Header({ onSubmit, onLogin, onSignup, onWallet, onProfile }) {
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
        <a href="#top" className="flex items-center gap-2 shrink-0" data-testid="logo">
          <div className="w-8 h-9 rounded-b-xl rounded-t-sm border-2 border-volt/60 flex items-end justify-center pb-1" style={{ boxShadow: "inset 0 0 12px rgba(225,255,0,0.25)" }}>
            <div className="w-2 h-2 rounded-full bg-volt" />
          </div>
          <span className="font-heading font-black text-xl tracking-tighter text-white">Tip<span className="text-volt">Jar</span></span>
        </a>

        <nav className="hidden lg:flex items-center gap-6 text-sm font-semibold text-zinc-300">
          <a href="#ratewall" className="hover:text-volt transition-colors" data-testid="nav-ratewall">{t("nav.ratewall")}</a>
          <a href="#leaderboard" className="hover:text-volt transition-colors" data-testid="nav-leaderboard">{t("nav.leaderboard")}</a>
          <a href="#how" className="hover:text-volt transition-colors" data-testid="nav-how">{t("nav.how")}</a>
          <a href="#invite" className="hover:text-volt transition-colors" data-testid="nav-invite">{t("nav.invite")}</a>
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <InstallAppButton />
          <NotificationBell />

          {/* language switcher */}
          <div className="relative" ref={langRef}>
            <button data-testid="language-switcher" onClick={() => setLangOpen(!langOpen)}
              className="flex items-center gap-1.5 rounded-full border border-elevated px-2.5 py-2 text-sm text-zinc-300 hover:border-volt/50 transition-colors">
              <Globe size={16} /> <span className="hidden sm:inline">{cur.flag}</span> <ChevronDown size={14} />
            </button>
            <AnimatePresence>
              {langOpen && (
                <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                  className="absolute right-0 mt-2 w-40 rounded-xl bg-surface border border-elevated p-1 shadow-2xl">
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
                className="flex items-center gap-1.5 rounded-full bg-volt/10 border border-volt/30 px-3 py-2 hover:bg-volt/20 transition-colors">
                <Wallet size={15} className="text-volt" />
                <span className="font-mono font-bold text-volt text-sm" data-testid="header-credits">{user.credits}</span>
              </button>
              <div className="relative" ref={menuRef}>
                <button data-testid="user-menu" onClick={() => setMenuOpen(!menuOpen)}
                  className="w-9 h-9 rounded-full bg-elevated border border-zinc-600 flex items-center justify-center font-bold text-white hover:border-volt transition-colors">
                  {user.username?.[0]?.toUpperCase() || "U"}
                </button>
                <AnimatePresence>
                  {menuOpen && (
                    <motion.div initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}
                      className="absolute right-0 mt-2 w-52 rounded-xl bg-surface border border-elevated p-1 shadow-2xl">
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
            className="flex items-center gap-1.5 rounded-full border border-volt/40 text-volt font-bold text-sm px-3 py-2 hover:bg-volt/10 active:scale-95 transition-all">
            <Plus size={16} /> <span className="hidden md:inline">{t("nav.submit")}</span>
          </button>
        </div>
      </div>
    </header>
  );
}

function MenuItem({ icon: Icon, label, onClick, testId }) {
  return (
    <button data-testid={testId} onClick={onClick} className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-300 hover:bg-elevated hover:text-white transition-colors">
      <Icon size={16} /> {label}
    </button>
  );
}
