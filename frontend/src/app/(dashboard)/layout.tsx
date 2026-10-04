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
  const isStandaloneReport =
    pathname.startsWith("/report/v2/") ||
    pathname === "/products/career" ||
    pathname.startsWith("/products/career/report/");

  if (isStandaloneReport) {
    return (
      <DashboardAuthGuard>
        <div className="min-h-screen">{children}</div>
      </DashboardAuthGuard>
    );
  }

  return (
    <DashboardAuthGuard>
      <div className="flex min-h-screen min-w-0">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header />
          <main className="min-w-0 flex-1 p-4 sm:p-6">{children}</main>
        </div>
      </div>
    </DashboardAuthGuard>
  );
}
