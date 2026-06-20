"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { bootstrapSession } from "@/lib/auth-session";

export function DashboardAuthGuard({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [isCheckingSession, setIsCheckingSession] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function verifySession() {
      const user = await bootstrapSession();
      if (!isMounted) {
        return;
      }
      if (!user) {
        router.replace(`/login?next=${encodeURIComponent(pathname)}`);
        return;
      }
      setIsCheckingSession(false);
    }

    verifySession();

    return () => {
      isMounted = false;
    };
  }, [pathname, router]);

  if (isCheckingSession) {
    return (
      <main className="flex flex-1 items-center justify-center p-6">
        <div className="text-sm text-muted-foreground">Проверяем сессию...</div>
      </main>
    );
  }

  return <>{children}</>;
}
