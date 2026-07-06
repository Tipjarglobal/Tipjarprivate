import React, { useState } from "react";
import Modal, { Field, inputCls, btnPrimary } from "./Modal";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";
import { apiErr } from "../api";
import { toast } from "sonner";

const TIMEZONES = [
  "UTC", "Europe/London", "Europe/Berlin", "Europe/Athens", "Europe/Madrid",
  "Europe/Paris", "America/New_York", "America/Sao_Paulo", "Africa/Lagos",
  "Asia/Dubai", "Asia/Kolkata", "Asia/Tokyo", "Australia/Sydney",
];

export default function AuthModal({ open, onClose, initialMode = "login" }) {
  const { t, setLang } = useI18n();
  const { login, register } = useAuth();
  const [mode, setMode] = useState(initialMode);
  const [form, setForm] = useState({
    email: "", password: "", username: "", timezone: "UTC", language: "en",
  });
  const [loading, setLoading] = useState(false);

  React.useEffect(() => setMode(initialMode), [initialMode, open]);

  const upd = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (mode === "login") {
        const u = await login(form.email, form.password);
        if (u.language) setLang(u.language);
        toast.success("👋 " + (u.username || ""));
      } else {
        const data = await register(form);
        setLang(form.language);
        localStorage.removeItem("tj_ref");
        toast.success(t("auth.checkEmail"));
        if (data.verify_link) toast.message("Dev verify link: " + data.verify_link, { duration: 12000 });
      }
      onClose();
    } catch (err) {
      toast.error(apiErr(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={mode === "login" ? t("auth.login") : t("auth.signup")} testId="auth-modal">
      <form onSubmit={submit}>
        {mode === "signup" && (
          <Field label={t("auth.username")}>
            <input data-testid="auth-username" className={inputCls} value={form.username} onChange={upd("username")} required minLength={2} />
          </Field>
        )}
        <Field label={t("auth.email")}>
          <input data-testid="auth-email" type="email" className={inputCls} value={form.email} onChange={upd("email")} required />
        </Field>
        <Field label={t("auth.password")}>
          <input data-testid="auth-password" type="password" className={inputCls} value={form.password} onChange={upd("password")} required minLength={6} />
        </Field>
        {mode === "signup" && (
          <div className="grid grid-cols-2 gap-3">
            <Field label={t("auth.timezone")}>
              <select data-testid="auth-timezone" className={inputCls} value={form.timezone} onChange={upd("timezone")}>
                {TIMEZONES.map((tz) => <option key={tz} value={tz}>{tz}</option>)}
              </select>
            </Field>
            <Field label={t("auth.language")}>
              <select data-testid="auth-language" className={inputCls} value={form.language} onChange={upd("language")}>
                <option value="en">English</option>
                <option value="de">Deutsch</option>
                <option value="el">Ελληνικά</option>
              </select>
            </Field>
          </div>
        )}
        <button data-testid="auth-submit" type="submit" disabled={loading} className={btnPrimary}>
          {loading ? t("common.loading") : mode === "login" ? t("auth.loginBtn") : t("auth.signupBtn")}
        </button>
      </form>
      <button
        data-testid="auth-switch-mode"
        onClick={() => setMode(mode === "login" ? "signup" : "login")}
        className="mt-4 w-full text-center text-sm text-zinc-400 hover:text-volt transition-colors"
      >
        {mode === "login" ? t("auth.no") : t("auth.have")}
      </button>
    </Modal>
  );
}
