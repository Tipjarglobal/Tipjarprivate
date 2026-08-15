import React, { useState } from "react";
import Modal, { Field, inputCls, btnPrimary } from "./Modal";
import api, { apiErr } from "../api";
import { useI18n, LANGUAGES } from "../i18n";
import { useAuth } from "../auth";
import { toast } from "sonner";
import MemberJarWall from "./MemberJarWall";
import { Flame } from "lucide-react";

const TIMEZONES = [
  "UTC", "Europe/London", "Europe/Berlin", "Europe/Athens", "Europe/Madrid",
  "Europe/Paris", "America/New_York", "America/Sao_Paulo", "Africa/Lagos",
  "Asia/Dubai", "Asia/Kolkata", "Asia/Tokyo", "Australia/Sydney",
];

export default function ProfileModal({ open, onClose }) {
  const { t, setLang } = useI18n();
  const { user, setUser } = useAuth();
  const [username, setUsername] = useState(user?.username || "");
  const [email, setEmail] = useState(user?.email || "");
  const [timezone, setTimezone] = useState(user?.timezone || "UTC");
  const [language, setLanguage] = useState(user?.language || "en");
  const [busy, setBusy] = useState(false);

  React.useEffect(() => {
    if (open && user) {
      setUsername(user.username); setEmail(user.email || ""); setTimezone(user.timezone); setLanguage(user.language);
    }
  }, [open, user]);

  const save = async () => {
    setBusy(true);
    try {
      const { data } = await api.put("/auth/profile", { username, email, timezone, language });
      setUser(data.user);
      setLang(language);
      toast.success(t("profile.saved"));
      onClose();
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={t("profile.title")} testId="profile-modal">
      {user?.apex_flame && (
        <div data-testid="own-apex-flame" className="mb-4 flex items-center gap-2 rounded-xl bg-bell/15 border border-bell/40 px-3 py-2 text-sm font-black text-bell">
          <Flame size={16} /> {t("profile.apexFlame")}
        </div>
      )}
      <Field label={t("profile.username")}>
        <input data-testid="profile-username" className={inputCls} value={username} onChange={(e) => setUsername(e.target.value)} minLength={2} maxLength={24} />
      </Field>
      <Field label={t("profile.email")}>
        <input data-testid="profile-email" type="email" className={inputCls} value={email} onChange={(e) => setEmail(e.target.value)} placeholder="kontakt@example.com" />
      </Field>
      <div className="grid grid-cols-2 gap-3">
        <Field label={t("auth.timezone")}>
          <select data-testid="profile-timezone" className={inputCls} value={timezone} onChange={(e) => setTimezone(e.target.value)}>
            {TIMEZONES.map((tz) => <option key={tz} value={tz}>{tz}</option>)}
          </select>
        </Field>
        <Field label={t("auth.language")}>
          <select data-testid="profile-language" className={inputCls} value={language} onChange={(e) => setLanguage(e.target.value)}>
            {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
        </Field>
      </div>
      <button data-testid="profile-save" onClick={save} disabled={busy} className={btnPrimary}>
        {busy ? t("common.loading") : t("profile.save")}
      </button>
      <MemberJarWall />
    </Modal>
  );
}
