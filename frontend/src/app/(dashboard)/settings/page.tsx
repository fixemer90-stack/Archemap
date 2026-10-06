"use client";

import { useState } from "react";

import { BirthDataSettings } from "@/components/settings/BirthDataSettings";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth-store";

const birthDataRefinementEnabled =
  process.env.NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED === "true";

export default function SettingsPage() {
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  const [nameDraft, setNameDraft] = useState<string | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState("");
  const name = nameDraft ?? user?.name ?? "";

  async function handleUpdateProfile(event: React.FormEvent) {
    event.preventDefault();
    setProfileLoading(true);
    setProfileError("");
    setProfileSuccess(false);
    try {
      const response = await fetch("/api/v1/users/me", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name: name.trim() }),
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Ошибка обновления профиля",
        );
      }
      setUser(await response.json());
      setNameDraft(null);
      setProfileSuccess(true);
    } catch (error) {
      setProfileError(
        error instanceof Error ? error.message : "Что-то пошло не так",
      );
    } finally {
      setProfileLoading(false);
    }
  }

  async function handleChangePassword(event: React.FormEvent) {
    event.preventDefault();
    setPasswordLoading(true);
    setPasswordError("");
    setPasswordSuccess(false);
    if (newPassword.length < 8) {
      setPasswordError("Пароль должен быть не менее 8 символов");
      setPasswordLoading(false);
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError("Пароли не совпадают");
      setPasswordLoading(false);
      return;
    }
    try {
      const response = await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Ошибка смены пароля",
        );
      }
      setPasswordSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error) {
      setPasswordError(
        error instanceof Error ? error.message : "Что-то пошло не так",
      );
    } finally {
      setPasswordLoading(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-6xl space-y-8 overflow-x-clip px-1 pb-16 sm:px-3">
      <header className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[#D7B466]">
          Личные настройки
        </p>
        <h1 className="mt-2 font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-[#F6F1E8] sm:text-5xl">
          Настройки
        </h1>
        <p className="mt-3 text-base leading-7 text-[#C8D0DE]">
          Проверьте исходные данные расчёта, имя профиля и параметры
          безопасности.
        </p>
      </header>

      {birthDataRefinementEnabled && <BirthDataSettings />}

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-[24px] border border-white/10 bg-[#111927]/85 p-5 sm:p-7">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#AEB8C8]">
            Профиль
          </p>
          <h2 className="mt-2 font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-[#F6F1E8]">
            Как к вам обращаться
          </h2>
          <form onSubmit={handleUpdateProfile} className="mt-6 space-y-5">
            {profileError && (
              <p role="alert" className="text-base text-red-300">
                {profileError}
              </p>
            )}
            {profileSuccess && (
              <p aria-live="polite" className="text-base text-emerald-200">
                Профиль обновлён
              </p>
            )}
            <div className="space-y-2">
              <label
                htmlFor="settings-name"
                className="text-base font-medium text-[#F6F1E8]"
              >
                Имя
              </label>
              <Input
                id="settings-name"
                value={name}
                onChange={(event) => setNameDraft(event.target.value)}
                placeholder="Ваше имя"
                maxLength={120}
                className="min-h-11"
              />
            </div>
            <div className="space-y-2">
              <label
                htmlFor="settings-email"
                className="text-base font-medium text-[#D8DCE8]"
              >
                Email
              </label>
              <Input
                id="settings-email"
                value={user?.email || ""}
                disabled
                className="min-h-11 opacity-70"
              />
              <p className="text-sm leading-6 text-[#9FAABC]">
                Email нельзя изменить здесь.
              </p>
            </div>
            <Button
              type="submit"
              disabled={profileLoading}
              className="min-h-11"
            >
              {profileLoading ? "Сохранение…" : "Сохранить имя"}
            </Button>
          </form>
        </section>

        <section className="rounded-[24px] border border-white/10 bg-[#111927]/85 p-5 sm:p-7">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[#AEB8C8]">
            Безопасность
          </p>
          <h2 className="mt-2 font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-[#F6F1E8]">
            Смена пароля
          </h2>
          <form onSubmit={handleChangePassword} className="mt-6 space-y-5">
            {passwordError && (
              <p role="alert" className="text-base text-red-300">
                {passwordError}
              </p>
            )}
            {passwordSuccess && (
              <p aria-live="polite" className="text-base text-emerald-200">
                Пароль изменён
              </p>
            )}
            <PasswordField
              id="current-password"
              label="Текущий пароль"
              value={currentPassword}
              onChange={setCurrentPassword}
              placeholder="Введите текущий пароль"
            />
            <PasswordField
              id="new-password"
              label="Новый пароль"
              value={newPassword}
              onChange={setNewPassword}
              placeholder="Минимум 8 символов"
              minLength={8}
            />
            <PasswordField
              id="confirm-password"
              label="Подтвердите новый пароль"
              value={confirmPassword}
              onChange={setConfirmPassword}
              placeholder="Повторите пароль"
            />
            <Button
              type="submit"
              disabled={passwordLoading}
              className="min-h-11"
            >
              {passwordLoading ? "Смена пароля…" : "Сменить пароль"}
            </Button>
          </form>
        </section>
      </div>
    </main>
  );
}

function PasswordField({
  id,
  label,
  value,
  onChange,
  placeholder,
  minLength,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  minLength?: number;
}) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="text-base font-medium text-[#F6F1E8]">
        {label}
      </label>
      <Input
        id={id}
        type="password"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        minLength={minLength}
        className="min-h-11"
      />
    </div>
  );
}
