import React, { useState } from "react";
import { X, FileText, Shield, ScrollText } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

const CONTACT_EMAIL = "kontakt@tipjarglobal.com";
const SITE = "tipjarglobal.com";

const TABS = [
  ["impressum", "Impressum", FileText],
  ["datenschutz", "Datenschutz", Shield],
  ["agb", "AGB", ScrollText],
];

const Para = ({ children }) => (
  <p className="text-[13px] text-zinc-300 leading-relaxed mb-3">{children}</p>
);
const H = ({ children }) => (
  <h3 className="font-heading font-bold text-white text-sm uppercase tracking-wide mt-5 mb-2">{children}</h3>
);

// German-first legal content. Impressum-specific operator data is marked with [ ]
// placeholders — replace them with the real provider details (§5 DDG / §18 MStV).
const CONTENT = {
  impressum: (
    <div data-testid="legal-impressum">
      <H>Angaben gemäß § 5 DDG</H>
      <Para>
        [Betreiber-Name / Firma]<br />
        [Straße und Hausnummer]<br />
        [PLZ und Ort]<br />
        [Land]
      </Para>
      <H>Vertreten durch</H>
      <Para>[Name des Vertretungsberechtigten]</Para>
      <H>Kontakt</H>
      <Para>
        E-Mail: <a href={`mailto:${CONTACT_EMAIL}`} className="text-volt hover:underline">{CONTACT_EMAIL}</a><br />
        Web: {SITE}
      </Para>
      <H>Umsatzsteuer-ID</H>
      <Para>[USt-IdNr. gemäß § 27a UStG, falls vorhanden]</Para>
      <H>Verantwortlich für den Inhalt nach § 18 Abs. 2 MStV</H>
      <Para>[Name], [Anschrift wie oben]</Para>
      <H>Haftungshinweis</H>
      <Para>
        TipJar ist kein Buchmacher und kein Wettanbieter. Alle Inhalte dienen ausschließlich
        Informations- und Unterhaltungszwecken. Trotz sorgfältiger Prüfung übernehmen wir keine
        Haftung für die Inhalte externer Links; für deren Inhalt sind ausschließlich deren
        Betreiber verantwortlich. Nur für Personen ab 18 Jahren. Glücksspiel kann süchtig machen.
      </Para>
      <H>EU-Streitschlichtung</H>
      <Para>
        Die Europäische Kommission stellt eine Plattform zur Online-Streitbeilegung (OS) bereit:{" "}
        <a href="https://ec.europa.eu/consumers/odr/" target="_blank" rel="noreferrer" className="text-volt hover:underline">ec.europa.eu/consumers/odr</a>.
        Wir sind nicht verpflichtet und nicht bereit, an Streitbeilegungsverfahren vor einer
        Verbraucherschlichtungsstelle teilzunehmen.
      </Para>
    </div>
  ),
  datenschutz: (
    <div data-testid="legal-datenschutz">
      <H>1. Verantwortlicher</H>
      <Para>
        Verantwortlich für die Datenverarbeitung auf dieser Website ist der im Impressum genannte
        Betreiber. Kontakt: <a href={`mailto:${CONTACT_EMAIL}`} className="text-volt hover:underline">{CONTACT_EMAIL}</a>.
      </Para>
      <H>2. Welche Daten wir verarbeiten</H>
      <Para>
        • Kontodaten (E-Mail, Benutzername) bei Registrierung.<br />
        • Von dir eingereichte Tipps, Bewertungen und hochgeladene Wettschein-Bilder.<br />
        • Technische Daten (IP-Adresse, Gerät/Browser) zur Bereitstellung und Sicherheit.<br />
        • Push-Abonnement-Daten, sofern du Benachrichtigungen aktivierst.
      </Para>
      <H>3. Zwecke & Rechtsgrundlagen</H>
      <Para>
        Wir verarbeiten Daten zur Bereitstellung des Dienstes (Art. 6 Abs. 1 lit. b DSGVO), zur
        Wahrung berechtigter Interessen wie Sicherheit und Missbrauchsvermeidung (lit. f) sowie auf
        Grundlage deiner Einwilligung, z. B. für Push-Benachrichtigungen (lit. a).
      </Para>
      <H>4. Push-Benachrichtigungen</H>
      <Para>
        Aktivierst du Benachrichtigungen, speichern wir dein Web-Push-Abonnement, um dir Hinweise zu
        neuen Tipps zu senden. Du kannst dies jederzeit in den Alarm-Einstellungen oder in deinem
        Browser widerrufen.
      </Para>
      <H>5. Weitergabe & Dienstleister</H>
      <Para>
        Zur Bereitstellung setzen wir technische Dienstleister (Hosting, Datenbank, Sport-Daten-APIs)
        als Auftragsverarbeiter ein. Eine Weitergabe zu Werbezwecken an Dritte erfolgt nicht.
      </Para>
      <H>6. Speicherdauer</H>
      <Para>
        Wir speichern Daten nur so lange, wie es für die genannten Zwecke erforderlich ist bzw.
        gesetzliche Aufbewahrungsfristen bestehen. Konto- und Inhaltsdaten werden auf Wunsch gelöscht.
      </Para>
      <H>7. Deine Rechte</H>
      <Para>
        Du hast das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung, Datenübertragbarkeit
        und Widerspruch sowie ein Beschwerderecht bei einer Aufsichtsbehörde. Anfragen richte bitte an{" "}
        <a href={`mailto:${CONTACT_EMAIL}`} className="text-volt hover:underline">{CONTACT_EMAIL}</a>.
      </Para>
    </div>
  ),
  agb: (
    <div data-testid="legal-agb">
      <H>1. Geltungsbereich</H>
      <Para>
        Diese Allgemeinen Geschäftsbedingungen gelten für die Nutzung von TipJar ({SITE}), einer
        Community-Plattform für Fußball-Tipps.
      </Para>
      <H>2. Kein Wettanbieter</H>
      <Para>
        TipJar ist kein Buchmacher und vermittelt keine Wetten. Sämtliche Tipps, Bewertungen und
        Analysen dienen ausschließlich Informations- und Unterhaltungszwecken und stellen keine
        Aufforderung zum Wetten dar. Es besteht keine Gewinngarantie. Wetten erfolgen auf eigenes
        Risiko bei lizenzierten Drittanbietern.
      </Para>
      <H>3. Nutzung & Mindestalter</H>
      <Para>
        Die Nutzung ist Personen ab 18 Jahren gestattet. Du bist für die Richtigkeit deiner Angaben
        und für die von dir eingestellten Inhalte selbst verantwortlich.
      </Para>
      <H>4. Inhalte der Nutzer</H>
      <Para>
        Für eingereichte Tipps und Bilder räumst du uns das Recht ein, diese im Rahmen des Dienstes
        anzuzeigen. Rechtswidrige, beleidigende oder irreführende Inhalte sind untersagt und können
        entfernt werden.
      </Para>
      <H>5. Münzen & virtuelle Punkte</H>
      <Para>
        Innerhalb der Plattform erworbene oder erhaltene Münzen stellen keinen Geldwert dar und sind
        außerhalb der vorgesehenen Funktionen nicht übertragbar oder auszahlbar, sofern nicht
        ausdrücklich anders angegeben.
      </Para>
      <H>6. Haftung</H>
      <Para>
        Wir haften nicht für finanzielle Verluste aus Wetten oder aus dem Vertrauen auf Tipps. Im
        Übrigen haften wir nur bei Vorsatz und grober Fahrlässigkeit sowie bei Verletzung wesentlicher
        Vertragspflichten.
      </Para>
      <H>7. Verantwortungsvolles Spielen</H>
      <Para>
        Glücksspiel kann süchtig machen. Hilfe: BZgA · check-dein-spiel.de · kostenlose Sucht-Hotline
        0800 1 37 27 00.
      </Para>
      <H>8. Schlussbestimmungen</H>
      <Para>
        Es gilt deutsches Recht. Sollten einzelne Bestimmungen unwirksam sein, bleibt die Wirksamkeit
        der übrigen unberührt.
      </Para>
    </div>
  ),
};

export default function LegalModal({ open, initialTab = "impressum", onClose }) {
  const [tab, setTab] = useState(initialTab);
  React.useEffect(() => { if (open) setTab(initialTab); }, [open, initialTab]);
  React.useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[120] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={onClose}
          data-testid="legal-modal"
        >
          <motion.div
            className="w-full max-w-2xl max-h-[85vh] flex flex-col rounded-2xl bg-surface border border-elevated shadow-2xl overflow-hidden"
            initial={{ scale: 0.96, y: 12 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.96, y: 12 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-elevated">
              <span className="font-heading font-black text-white text-sm uppercase tracking-wide">Rechtliches</span>
              <button onClick={onClose} data-testid="legal-close" className="rounded-full p-1.5 text-zinc-400 hover:text-white hover:bg-elevated transition-colors">
                <X size={18} />
              </button>
            </div>
            <div className="flex items-center gap-1 px-3 py-2 border-b border-elevated overflow-x-auto no-scrollbar">
              {TABS.map(([key, label, Icon]) => (
                <button
                  key={key}
                  onClick={() => setTab(key)}
                  data-testid={`legal-tab-${key}`}
                  className={`flex items-center gap-1.5 whitespace-nowrap text-xs font-bold px-3 py-1.5 rounded-full transition-colors ${tab === key ? "bg-volt text-void" : "text-zinc-400 hover:text-white"}`}
                >
                  <Icon size={13} /> {label}
                </button>
              ))}
            </div>
            <div className="overflow-y-auto p-5">{CONTENT[tab]}</div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
