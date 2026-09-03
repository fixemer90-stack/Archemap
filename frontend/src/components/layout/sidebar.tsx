"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  User,
  Heart,
  Baby,
  Briefcase,
  CreditCard,
  Crown,
  Settings,
  LogOut,
} from "lucide-react";
import { useBillingAccess } from "@/hooks/use-billing-access";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useUIStore } from "@/stores/ui-store";

const navItems = [
  {
    title: "Главная",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
];

const productItems = [
  {
    title: "Self",
    href: "/products/self",
    icon: User,
    color: "#5B3FD6",
    description: "Архетипический профиль",
  },
  {
    title: "Love",
    href: "/products/love",
    icon: Heart,
    color: "#B84A6B",
    description: "Совместимость пары",
    disabled: true,
  },
  {
    title: "Child",
    href: "/products/child",
    icon: Baby,
    color: "#6BAFBD",
    description: "Профиль ребёнка",
    disabled: true,
  },
  {
    title: "Career",
    href: "/products/career",
    icon: Briefcase,
    color: "#C28A2E",
    description: "Карьерные сценарии",
  },
];

const settingsItems = [
  {
    title: "Оплата",
    href: "/billing",
    icon: CreditCard,
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
  const { isPlusActive, isLoadingAccess } = useBillingAccess();

  async function handleLogout() {
    try {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Proceed with local logout even if API fails
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
          <Link
            href="/dashboard"
            className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]"
          >
            Astrotype
          </Link>
        )}
        {!sidebarOpen && (
          <Link
            href="/dashboard"
            className="mx-auto font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#D8B45A]"
          >
            A
          </Link>
        )}
      </div>

      <div className="px-2 pb-2">
        <Link
          href="/billing"
          className={cn(
            "flex items-center gap-3 rounded-2xl border px-3 py-3 text-sm transition-all",
            isPlusActive
              ? "border-[rgba(216,180,90,0.36)] bg-[rgba(216,180,90,0.12)] text-[#F6F1E8]"
              : "border-[rgba(216,220,232,0.12)] bg-[rgba(255,255,255,0.045)] text-[#D8DCE8] hover:border-[rgba(216,180,90,0.28)] hover:text-[#F6F1E8]",
            !sidebarOpen && "justify-center px-2",
          )}
          aria-label={isPlusActive ? "Аккаунт Plus активен" : "Plus не активен"}
          title={isPlusActive ? "Аккаунт Plus активен" : "Plus не активен"}
        >
          <span className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[rgba(216,180,90,0.14)] text-[#D8B45A]">
            <Crown className="h-4 w-4" />
            {isPlusActive ? (
              <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-[#7CF29A] ring-2 ring-[#171426]" />
            ) : null}
          </span>
          {sidebarOpen && (
            <span className="min-w-0">
              <span className="block font-semibold">
                {isLoadingAccess
                  ? "Проверяем Plus"
                  : isPlusActive
                    ? "Plus активен"
                    : "Plus не активен"}
              </span>
              <span className="block text-xs text-[rgba(216,220,232,0.62)]">
                Статус аккаунта
              </span>
            </span>
          )}
        </Link>
      </div>

      {/* Main nav */}
      <nav className="space-y-1 p-2" aria-label="Главная навигация">
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

      {/* Products */}
      <div className="flex-1 space-y-1 p-2">
        {sidebarOpen && (
          <p className="px-3 py-1 text-xs text-[rgba(216,220,232,0.30)] uppercase tracking-wider">
            Продукты
          </p>
        )}
        {productItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.disabled ? "#" : item.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-all",
                item.disabled
                  ? "text-[rgba(216,220,232,0.25)] cursor-not-allowed"
                  : isActive
                    ? "bg-gradient-to-br from-[rgba(91,63,214,0.30)] to-[rgba(216,180,90,0.10)] text-[#F6F1E8] border border-[rgba(91,63,214,0.30)]"
                    : "text-[#D8DCE8] hover:bg-[rgba(255,255,255,0.05)] hover:text-[#F6F1E8]",
                !sidebarOpen && "justify-center",
              )}
              aria-label={item.title}
              title={item.disabled ? `${item.title} — скоро` : item.title}
              aria-current={isActive ? "page" : undefined}
              onClick={item.disabled ? (e) => e.preventDefault() : undefined}
            >
              <item.icon
                className="h-5 w-5 shrink-0"
                style={{ color: item.disabled ? undefined : item.color }}
              />
              {sidebarOpen && (
                <div className="flex-1 min-w-0">
                  <span>{item.title}</span>
                  {item.disabled && (
                    <span className="ml-2 text-[10px] text-[rgba(216,220,232,0.30)]">
                      скоро
                    </span>
                  )}
                </div>
              )}
            </Link>
          );
        })}
      </div>

      {/* Settings */}
      <nav
        className="space-y-1 p-2 border-t border-[rgba(216,220,232,0.10)]"
        aria-label="Настройки"
      >
        {settingsItems.map((item) => {
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
            >
              <item.icon className="h-5 w-5 shrink-0" />
              {sidebarOpen && <span>{item.title}</span>}
            </Link>
          );
        })}

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
      </nav>
    </aside>
  );
}
