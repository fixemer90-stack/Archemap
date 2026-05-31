"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";

function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);

  useEffect(() => {
    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");
    const needsProfile = searchParams.get("needs_profile");
    const birthDate = searchParams.get("birth_date");
    const email = searchParams.get("email");

    if (!accessToken || !refreshToken) {
      router.push("/login?error=missing_tokens");
      return;
    }

    setTokens(accessToken, refreshToken);

    // If user needs to complete profile, redirect to register step 2
    if (needsProfile === "true") {
      let registerUrl = "/register?step=2";
      if (birthDate) {
        registerUrl += `&birth_date=${encodeURIComponent(birthDate)}`;
      }
      if (email) {
        registerUrl += `&email=${encodeURIComponent(email)}`;
      }
      router.push(registerUrl);
      return;
    }

    // Otherwise, fetch user and go to dashboard
    fetch("/api/v1/users/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((res) => res.json())
      .then((user) => {
        useAuthStore.getState().setUser(user);
        router.push("/dashboard");
      })
      .catch(() => {
        router.push("/dashboard");
      });
  }, [searchParams, router, setTokens]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center space-y-4">
        <div className="mx-auto h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        <p className="text-muted-foreground">Завершение входа...</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">Загрузка...</p>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
