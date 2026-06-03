"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth-store";

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const token = useAuthStore((s) => s.token);

  // Profile form
  const [name, setName] = useState(user?.name || "");
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [profileError, setProfileError] = useState("");

  // Password form
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState("");

  useEffect(() => {
    if (user?.name) setName(user.name);
  }, [user]);

  async function handleUpdateProfile(e: React.FormEvent) {
    e.preventDefault();
    setProfileLoading(true);
    setProfileError("");
    setProfileSuccess(false);

    try {
      const res = await fetch("/api/v1/users/me", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name: name.trim() }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Ошибка обновления профиля"
        );
      }

      const updatedUser = await res.json();
      setUser(updatedUser);
      setProfileSuccess(true);
    } catch (err) {
      setProfileError(
        err instanceof Error ? err.message : "Что-то пошло не так"
      );
    } finally {
      setProfileLoading(false);
    }
  }

  async function handleChangePassword(e: React.FormEvent) {
    e.preventDefault();
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
      const res = await fetch("/api/v1/auth/change-password", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Ошибка смены пароля"
        );
      }

      setPasswordSuccess(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(
        err instanceof Error ? err.message : "Что-то пошло не так"
      );
    } finally {
      setPasswordLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
          Настройки
        </h1>
        <p className="text-sm text-[#D8DCE8] mt-1">
          Управление профилем и безопасностью
        </p>
      </div>

      {/* Profile section */}
      <div className="glass p-6 space-y-4">
        <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
          Профиль
        </h2>

        <form onSubmit={handleUpdateProfile} className="space-y-4">
          {profileError && (
            <p className="text-sm text-red-500">{profileError}</p>
          )}
          {profileSuccess && (
            <p className="text-sm text-green-500">Профиль обновлён</p>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium">Имя</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ваше имя"
              maxLength={120}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-muted-foreground">
              Email
            </label>
            <Input
              value={user?.email || ""}
              disabled
              className="opacity-50"
            />
            <p className="text-xs text-muted-foreground">
              Email нельзя изменить
            </p>
          </div>

          <Button type="submit" disabled={profileLoading}>
            {profileLoading ? "Сохранение..." : "Сохранить"}
          </Button>
        </form>
      </div>

      {/* Password section */}
      <div className="glass p-6 space-y-4">
        <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
          Смена пароля
        </h2>

        <form onSubmit={handleChangePassword} className="space-y-4">
          {passwordError && (
            <p className="text-sm text-red-500">{passwordError}</p>
          )}
          {passwordSuccess && (
            <p className="text-sm text-green-500">Пароль изменён</p>
          )}

          <div className="space-y-2">
            <label className="text-sm font-medium">Текущий пароль</label>
            <Input
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Введите текущий пароль"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Новый пароль</label>
            <Input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Минимум 8 символов"
              minLength={8}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">
              Подтвердите новый пароль
            </label>
            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Повторите пароль"
            />
          </div>

          <Button type="submit" disabled={passwordLoading}>
            {passwordLoading ? "Смена пароля..." : "Сменить пароль"}
          </Button>
        </form>
      </div>
    </div>
  );
}
