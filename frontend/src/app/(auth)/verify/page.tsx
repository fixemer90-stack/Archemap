"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

function VerifyContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const emailParam = searchParams.get("email");

  const [status, setStatus] = useState<
    "loading" | "success" | "error" | "no-token"
  >(token ? "loading" : "no-token");
  const [message, setMessage] = useState("");
  const [email, setEmail] = useState(emailParam || "");
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);

  useEffect(() => {
    if (!token) return;

    async function verify() {
      try {
        const res = await fetch("/api/v1/auth/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token }),
        });

        const data = await res.json();

        if (res.ok) {
          setStatus("success");
          setMessage(data.message);
        } else {
          setStatus("error");
          const errorMsg = Array.isArray(data.detail)
            ? data.detail.map((e: { msg: string }) => e.msg).join(", ")
            : typeof data.detail === "string"
              ? data.detail
              : "Ошибка верификации";
          setMessage(errorMsg);
        }
      } catch {
        setStatus("error");
        setMessage("Что-то пошло не так");
      }
    }

    verify();
  }, [token]);

  async function handleResend() {
    if (!email) return;
    setResendLoading(true);
    setResendSuccess(false);

    try {
      await fetch("/api/v1/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      setResendSuccess(true);
    } catch {
      setResendSuccess(true);
    } finally {
      setResendLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="w-full max-w-sm space-y-6 text-center">
        {status === "loading" && (
          <>
            <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <p className="text-muted-foreground">Подтверждение email...</p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-green-100 text-green-600">
              ✓
            </div>
            <h1 className="text-2xl font-bold">Email подтверждён</h1>
            <p className="text-muted-foreground">{message}</p>
            <Button asChild>
              <Link href="/login">Войти</Link>
            </Button>
          </>
        )}

        {status === "error" && (
          <>
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600">
              ✕
            </div>
            <h1 className="text-2xl font-bold">Ошибка верификации</h1>
            <p className="text-muted-foreground">{message}</p>

            {message.includes("expired") || message.includes("истёк") ? (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Срок действия ссылки истёк. Запросите новую.
                </p>
                <div className="space-y-2">
                  <Input
                    type="email"
                    placeholder="Ваш email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <Button
                    onClick={handleResend}
                    disabled={resendLoading || !email}
                    className="w-full"
                  >
                    {resendLoading
                      ? "Отправка..."
                      : "Отправить новую ссылку"}
                  </Button>
                </div>
                {resendSuccess && (
                  <p className="text-sm text-green-500">
                    Письмо отправлено. Проверьте почту.
                  </p>
                )}
              </div>
            ) : (
              <Button variant="outline" asChild>
                <Link href="/login">Вернуться к входу</Link>
              </Button>
            )}
          </>
        )}

        {status === "no-token" && (
          <>
            <h1 className="text-2xl font-bold">Проверьте email</h1>
            <p className="text-muted-foreground">
              Мы отправили ссылку для подтверждения на ваш email. Перейдите по
              ней, чтобы активировать аккаунт.
            </p>
            <div className="space-y-3">
              <div className="space-y-2">
                <Input
                  type="email"
                  placeholder="Ваш email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
                <Button
                  onClick={handleResend}
                  disabled={resendLoading || !email}
                  variant="outline"
                  className="w-full"
                >
                  {resendLoading
                    ? "Отправка..."
                    : "Отправить письмо повторно"}
                </Button>
              </div>
              {resendSuccess && (
                <p className="text-sm text-green-500">
                  Письмо отправлено. Проверьте почту.
                </p>
              )}
            </div>
            <Button variant="outline" asChild>
              <Link href="/login">Вернуться к входу</Link>
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

export default function VerifyPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">Загрузка...</p>
        </div>
      }
    >
      <VerifyContent />
    </Suspense>
  );
}
