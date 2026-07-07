import React from "react";
import { AlertTriangle, ShieldAlert } from "lucide-react";
import { useI18n } from "../i18n";

const TEXTS = {
  de: {
    title: "Wichtiger Hinweis",
    body:
      "TipJar ist kein Buchmacher und kein Wettanbieter. Alle Tipps, Bewertungen und Analysen dienen ausschließlich Informations- und Unterhaltungszwecken und stellen keine Aufforderung zum Wetten dar. Es besteht keine Garantie auf Gewinne — Wetten erfolgen auf eigenes Risiko bei lizenzierten Drittanbietern.",
    age: "Nur für Personen ab 18 Jahren. Glücksspiel kann süchtig machen.",
    help: "Hilfe & Beratung: BZgA · check-dein-spiel.de · kostenlose Sucht-Hotline 0800 1 37 27 00",
    contact: "Kontakt",
    bar: "18+ · TipJar ist kein Wettanbieter · Tipps ohne Gewinngarantie, nur zur Unterhaltung · Glücksspiel kann süchtig machen",
  },
  en: {
    title: "Important notice",
    body:
      "TipJar is not a bookmaker or betting operator. All tips, ratings and analysis are provided for information and entertainment purposes only and are not an invitation to bet. There is no guarantee of winnings — betting is at your own risk with licensed third-party operators.",
    age: "For persons aged 18 and over only. Gambling can be addictive.",
    help: "Help & support: BeGambleAware.org · free national helpline",
    contact: "Contact",
    bar: "18+ · TipJar is not a betting operator · Tips carry no guarantee, for entertainment only · Gambling can be addictive",
  },
};

const CONTACT_EMAIL = "kontakt@tipjarglobal.com";

const pick = (lang) => TEXTS[lang] || TEXTS.en;

export const DisclaimerBar = () => {
  const { lang } = useI18n();
  const x = pick(lang);
  return (
    <div
      data-testid="disclaimer-bar"
      className="flex items-center gap-2 px-4 sm:px-6 py-2 bg-bell/10 border-b border-bell/20 text-[11px] sm:text-xs text-bell/90"
    >
      <ShieldAlert size={14} className="shrink-0" />
      <span className="leading-tight">{x.bar}</span>
    </div>
  );
};

export const Disclaimer = () => {
  const { lang } = useI18n();
  const x = pick(lang);
  return (
    <div
      data-testid="disclaimer-block"
      className="max-w-3xl mx-auto rounded-2xl border border-bell/25 bg-bell/5 p-5 text-left"
    >
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle size={16} className="text-bell shrink-0" />
        <span className="font-bold text-bell text-sm uppercase tracking-wide">{x.title}</span>
      </div>
      <p className="text-xs text-zinc-400 leading-relaxed">{x.body}</p>
      <p className="text-xs text-zinc-300 font-semibold mt-2">{x.age}</p>
      <p className="text-xs text-zinc-500 mt-2">{x.help}</p>
      <p className="text-xs text-zinc-400 mt-3" data-testid="disclaimer-contact">
        {x.contact}:{" "}
        <a href={`mailto:${CONTACT_EMAIL}`} className="text-volt hover:underline font-medium">
          {CONTACT_EMAIL}
        </a>
      </p>
    </div>
  );
};
