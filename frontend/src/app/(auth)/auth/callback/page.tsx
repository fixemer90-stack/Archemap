"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";

function CallbackContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  useEffect(() => {
    const needsProfile = searchParams.get("needs_profile");
    const birthDate = searchParams.get("birth_date");
    const email = searchParams.get("email");

    // Tokens are now in HttpOnly cookies set by backend (CRIT-01)
    // Frontend doesn't need to handle them directly

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

    // Existing user with profile → dashboard
    // Auth state will be fetched from /api/v1/users/me on dashboard load
    router.push("/dashboard");
  }, [searchParams, router]);

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
