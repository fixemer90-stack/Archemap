"use client";

import { DashboardAuthGuard } from "@/components/layout/dashboard-auth-guard";
import { Header } from "@/components/layout/header";
import { Sidebar } from "@/components/layout/sidebar";
import { usePathname } from "next/navigation";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isStandaloneV2Report = pathname.startsWith("/report/v2/");

  if (isStandaloneV2Report) {
    return (
      <DashboardAuthGuard>
        <div className="min-h-screen">{children}</div>
      </DashboardAuthGuard>
    );
  }

  return (
    <DashboardAuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex flex-1 flex-col">
          <Header />
          <main className="flex-1 p-6">{children}</main>
        </div>
      </div>
    </DashboardAuthGuard>
  );
}
