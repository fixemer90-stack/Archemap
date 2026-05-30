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

    if (!accessToken || !refreshToken) {
      router.push("/login?error=missing_tokens");
      return;
    }

    setTokens(accessToken, refreshToken);

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
        <p className="text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
