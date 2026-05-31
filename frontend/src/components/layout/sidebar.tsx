"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  CreditCard,
  Receipt,
  Settings,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useUIStore } from "@/stores/ui-store";
import { getAccessToken } from "@/lib/cookies";

const navItems = [
  {
    title: "Главная",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Подписки",
    href: "/subscriptions",
    icon: CreditCard,
  },
  {
    title: "Оплата",
    href: "/billing",
    icon: Receipt,
  },
  {
    title: "Настройки",
    href: "/settings",
    icon: Settings,
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const sidebarOpen = useUIStore((s) => s.sidebarOpen);
  const logout = useAuthStore((s) => s.logout);

  async function handleLogout() {
    const token = getAccessToken();
    if (token) {
      try {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        });
      } catch {
        // Proceed with local logout even if API fails
      }
    }
    logout();
    router.push("/login");
  }

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-[rgba(216,220,232,0.10)] bg-[rgba(255,255,255,0.03)] backdrop-blur-xl transition-all duration-300",
        sidebarOpen ? "w-64" : "w-16",
      )}
    >
      <div className="flex h-16 items-center border-b border-[rgba(216,220,232,0.10)] px-4">
        {sidebarOpen && (
          <span className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
            Archemap
          </span>
        )}
        {!sidebarOpen && (
          <span className="mx-auto font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#D8B45A]">
            A
          </span>
        )}
      </div>

      <nav className="flex-1 space-y-1 p-2" aria-label="Главная навигация">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all",
                isActive
                  ? "bg-gradient-to-br from-[rgba(91,63,214,0.30)] to-[rgba(216,180,90,0.10)] text-[#F6F1E8] border border-[rgba(91,63,214,0.30)]"
                  : "text-[#D8DCE8] hover:bg-[rgba(255,255,255,0.05)] hover:text-[#F6F1E8]",
                !sidebarOpen && "justify-center",
              )}
              aria-label={item.title}
              title={item.title}
              aria-current={isActive ? "page" : undefined}
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {sidebarOpen && <span>{item.title}</span>}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[rgba(216,220,232,0.10)] p-2">
        <button
          onClick={handleLogout}
          className={cn(
            "flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-[#D8DCE8] transition-all hover:bg-[rgba(255,255,255,0.05)] hover:text-[#F6F1E8]",
            !sidebarOpen && "justify-center",
          )}
          aria-label="Выйти"
          title="Выйти"
        >
          <LogOut className="h-5 w-5 shrink-0" />
          {sidebarOpen && <span>Выйти</span>}
        </button>
      </div>
    </aside>
  );
}
