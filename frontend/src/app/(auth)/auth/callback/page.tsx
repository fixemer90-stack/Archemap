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

    // Store tokens
    setTokens(accessToken, refreshToken);

    // If user needs to complete profile → register step 2
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

    // Existing user with profile → fetch user info → dashboard
    fetch("/api/v1/users/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((res) => {
        if (res.ok) return res.json();
        throw new Error("Failed to fetch user");
      })
      .then((user) => {
        useAuthStore.getState().setUser(user);
        router.push("/dashboard");
      })
      .catch(() => {
        // Token is valid but user fetch failed — still go to dashboard
        router.push("/dashboard");
      });
  }, [searchParams, router, setTokens]);

  return (
    <div className="w-full max-w-sm space-y-6 text-center">
      <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[#5B3FD6] border-t-[#D8B45A]" />
      <p className="text-[#D8DCE8]">Завершение входа через Яндекс...</p>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="w-full max-w-sm space-y-6 text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-2 border-[#5B3FD6] border-t-[#D8B45A]" />
          <p className="text-[#D8DCE8]">Загрузка...</p>
        </div>
      }
    >
      <CallbackContent />
    </Suspense>
  );
}
