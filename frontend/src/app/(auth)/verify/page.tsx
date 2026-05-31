"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";

function VerifyContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState<
    "loading" | "success" | "error" | "no-token"
  >(token ? "loading" : "no-token");
  const [message, setMessage] = useState("");

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
            <Button variant="outline" asChild>
              <Link href="/login">Вернуться к входу</Link>
            </Button>
          </>
        )}

        {status === "no-token" && (
          <>
            <h1 className="text-2xl font-bold">Проверьте email</h1>
            <p className="text-muted-foreground">
              Мы отправили ссылку для подтверждения на ваш email. Перейдите по
              ней, чтобы активировать аккаунт.
            </p>
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
