"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth-store";

export default function LoginPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showResend, setShowResend] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setShowResend(false);
    setResendSuccess(false);
    setLoading(true);

    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const data = await res.json();
        const errorMsg = Array.isArray(data.detail)
          ? data.detail.map((e: { msg: string }) => e.msg).join(", ")
          : typeof data.detail === "string"
            ? data.detail
            : "Ошибка входа";

        // Show resend button if email not verified
        if (
          errorMsg.includes("not verified") ||
          errorMsg.includes("не подтверждён")
        ) {
          setShowResend(true);
        }

        throw new Error(errorMsg);
      }

      const tokens = await res.json();
      setTokens(tokens.access_token, tokens.refresh_token);

      // Fetch user profile
      const userRes = await fetch("/api/v1/users/me", {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });
      if (userRes.ok) {
        const user = await userRes.json();
        useAuthStore.getState().setUser(user);
      }

      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Что-то пошло не так");
    } finally {
      setLoading(false);
    }
  }

  async function handleResendVerification() {
    setResendLoading(true);
    setResendSuccess(false);

    try {
      await fetch("/api/v1/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      // Always show success to prevent email enumeration
      setResendSuccess(true);
      setShowResend(false);
    } catch {
      setResendSuccess(true);
    } finally {
      setResendLoading(false);
    }
  }

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">Вход</h1>
        <p className="text-sm text-muted-foreground">Войдите в свой аккаунт</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="space-y-2">
            <p className="text-sm text-red-500 text-center">{error}</p>
            {showResend && (
              <div className="text-center">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleResendVerification}
                  disabled={resendLoading}
                >
                  {resendLoading ? "Отправка..." : "Отправить письмо повторно"}
                </Button>
              </div>
            )}
          </div>
        )}

        {resendSuccess && (
          <p className="text-sm text-green-500 text-center">
            Письмо отправлено. Проверьте почту.
          </p>
        )}

        <div className="space-y-2">
          <label htmlFor="email" className="text-sm font-medium">
            Email
          </label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="password" className="text-sm font-medium">
            Пароль
          </label>
          <Input
            id="password"
            type="password"
            placeholder="Введите пароль"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? "Вход..." : "Войти"}
        </Button>

        <p className="text-center text-sm">
          <Link
            href="/forgot-password"
            className="text-[#8DA8FF] hover:underline"
          >
            Забыли пароль?
          </Link>
        </p>
      </form>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">Или</span>
        </div>
      </div>

      <Button
        variant="outline"
        className="w-full"
        onClick={() =>
          (window.location.href = "/api/v1/auth/oauth/yandex/start")
        }
      >
        <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
          <path d="M22.42 0H1.58C.71 0 0 .71 0 1.58v20.84C0 23.29.71 24 1.58 24h20.84c.87 0 1.58-.71 1.58-1.58V1.58C24 .71 23.29 0 22.42 0z" />
        </svg>
        Войти через Яндекс
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Нет аккаунта?{" "}
        <Link href="/register" className="text-[#8DA8FF] hover:underline">
          Зарегистрироваться
        </Link>
      </p>
    </div>
  );
}
