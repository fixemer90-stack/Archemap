"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Baby,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  CreditCard,
  Crown,
  Heart,
  LayoutDashboard,
  LogOut,
  Settings,
  Sparkles,
  User,
  X,
  type LucideIcon,
} from "lucide-react";

import { useBillingAccess } from "@/hooks/use-billing-access";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";
import { useUIStore } from "@/stores/ui-store";

const navItems = [
  { title: "Главная", href: "/dashboard", icon: LayoutDashboard },
];

const productItems = [
  {
    title: "Self",
    href: "/products/self",
    icon: User,
    color: "#8DA8FF",
  },
  {
    title: "Love",
    href: "/products/love",
    icon: Heart,
    color: "#D77A98",
    disabled: true,
  },
  {
    title: "Child",
    href: "/products/child",
    icon: Baby,
    color: "#7DC5D1",
    disabled: true,
  },
  {
    title: "Career",
    href: "/products/career",
    icon: Briefcase,
    color: "#D8B45A",
  },
];

const settingsItems = [
  { title: "Оплата", href: "/billing", icon: CreditCard },
  { title: "Настройки", href: "/settings", icon: Settings },
];

type NavigationItem = {
  title: string;
  href: string;
  icon: LucideIcon;
  color?: string;
  disabled?: boolean;
};

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const mobileSidebarOpen = useUIStore((state) => state.mobileSidebarOpen);
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);
  const setMobileSidebarOpen = useUIStore(
    (state) => state.setMobileSidebarOpen,
  );
  const logout = useAuthStore((state) => state.logout);
  const { access, isPlusActive, isLoadingAccess } = useBillingAccess();

  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [pathname, setMobileSidebarOpen]);

  useEffect(() => {
    if (!mobileSidebarOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMobileSidebarOpen(false);
    };
    window.addEventListener("keydown", closeOnEscape);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [mobileSidebarOpen, setMobileSidebarOpen]);

  const activeUntil = access?.subscription?.current_period_end
    ? new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "short",
      }).format(new Date(access.subscription.current_period_end))
    : null;

  async function handleLogout() {
    try {
      await fetch("/api/v1/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Proceed with local logout even if API fails.
    }
    logout();
    router.push("/login");
  }

  const sharedPanelProps = {
    pathname,
    isPlusActive,
    isLoadingAccess,
    activeUntil,
    handleLogout,
  };

  return (
    <>
      <aside
        className={cn(
          "sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-white/10 bg-[#0B0D14]/90 shadow-[20px_0_60px_rgba(3,5,12,0.22)] backdrop-blur-2xl transition-[width] duration-300 motion-reduce:transition-none md:flex md:w-[4.75rem]",
          sidebarOpen && "xl:w-[17.5rem]",
        )}
      >
        <SidebarPanel expanded={sidebarOpen} {...sharedPanelProps} />
        <button
          type="button"
          onClick={toggleSidebar}
          className="absolute -right-3 top-[5.15rem] hidden h-7 w-7 items-center justify-center rounded-full border border-white/15 bg-[#171426] text-[#D8DCE8] shadow-lg transition hover:border-[#D8B45A]/40 hover:text-[#F6F1E8] motion-reduce:transition-none xl:flex"
          aria-label={sidebarOpen ? "Свернуть меню" : "Развернуть меню"}
          title={sidebarOpen ? "Свернуть меню" : "Развернуть меню"}
        >
          {sidebarOpen ? (
            <ChevronLeft className="h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
        </button>
      </aside>

      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-50 md:hidden" role="presentation">
          <button
            type="button"
            className="absolute inset-0 bg-[#05070C]/78 backdrop-blur-sm"
            onClick={() => setMobileSidebarOpen(false)}
            aria-label="Закрыть меню"
          />
          <aside
            role="dialog"
            aria-modal="true"
            aria-label="Навигация"
            className="relative flex h-dvh w-[88vw] max-w-[21rem] flex-col border-r border-white/12 bg-[#0B0D14]/98 shadow-[24px_0_80px_rgba(0,0,0,0.48)]"
          >
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(false)}
              className="absolute right-3 top-3 z-10 flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-[#D8DCE8] transition hover:bg-white/[0.08] hover:text-[#F6F1E8] motion-reduce:transition-none"
              aria-label="Закрыть меню"
              title="Закрыть меню"
            >
              <X className="h-5 w-5" />
            </button>
            <SidebarPanel mobile expanded {...sharedPanelProps} />
          </aside>
        </div>
      )}
    </>
  );
}

function SidebarPanel({
  pathname,
  expanded,
  mobile = false,
  isPlusActive,
  isLoadingAccess,
  activeUntil,
  handleLogout,
}: {
  pathname: string;
  expanded: boolean;
  mobile?: boolean;
  isPlusActive: boolean;
  isLoadingAccess: boolean;
  activeUntil: string | null;
  handleLogout: () => void;
}) {
  const showFullBrand = mobile || expanded;
  const labelClass = mobile ? "block" : expanded ? "hidden xl:block" : "hidden";
  const itemAlignment = mobile
    ? "justify-start"
    : expanded
      ? "justify-center xl:justify-start"
      : "justify-center";

  return (
    <div className="relative flex min-h-0 flex-1 flex-col overflow-hidden">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-44 bg-[radial-gradient(circle_at_20%_0%,rgba(91,63,214,0.24),transparent_64%)]"
        aria-hidden="true"
      />

      <div
        className={cn(
          "relative flex h-[4.75rem] shrink-0 items-center border-b border-white/10",
          mobile
            ? "px-5 pr-16"
            : "justify-center px-3 xl:justify-start xl:px-5",
        )}
      >
        <Link
          href="/dashboard"
          className="flex min-w-0 items-center gap-3 text-[#F6F1E8]"
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[#D8B45A]/30 bg-[linear-gradient(145deg,rgba(216,180,90,0.18),rgba(91,63,214,0.24))] text-[#E6C66F] shadow-[0_8px_30px_rgba(91,63,214,0.16)]">
            <Sparkles className="h-[18px] w-[18px]" />
          </span>
          {showFullBrand && (
            <span className={cn("min-w-0", labelClass)}>
              <span className="block truncate font-[family-name:var(--font-cormorant)] text-xl font-semibold tracking-[0.04em]">
                Astrotype
              </span>
              <span className="block text-[10px] font-semibold uppercase tracking-[0.18em] text-[#D8B45A]/70">
                карта личности
              </span>
            </span>
          )}
        </Link>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-2.5 py-4 [scrollbar-width:thin] [scrollbar-color:rgba(216,220,232,0.18)_transparent]">
        <Link
          href="/billing"
          className={cn(
            "mb-4 flex min-h-12 items-center gap-3 rounded-2xl border px-2.5 py-2.5 transition motion-reduce:transition-none",
            isPlusActive
              ? "border-[#D8B45A]/35 bg-[linear-gradient(135deg,rgba(216,180,90,0.14),rgba(91,63,214,0.10))] text-[#F6F1E8]"
              : "border-white/10 bg-white/[0.035] text-[#D8DCE8] hover:border-[#D8B45A]/25 hover:bg-white/[0.055]",
            itemAlignment,
          )}
          aria-label={isPlusActive ? "Аккаунт Plus активен" : "Plus не активен"}
          title={isPlusActive ? "Аккаунт Plus активен" : "Plus не активен"}
        >
          <span className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-[#D8B45A]/12 text-[#D8B45A]">
            <Crown className="h-4 w-4" />
            {isPlusActive && (
              <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-[#7CF29A] ring-2 ring-[#171426]" />
            )}
          </span>
          <span className={cn("min-w-0", labelClass)}>
            <span className="block truncate text-sm font-semibold">
              {isLoadingAccess
                ? "Проверяем Plus"
                : isPlusActive
                  ? "Plus активен"
                  : "Plus не активен"}
            </span>
            <span className="block truncate text-[11px] text-[#AEB8C8]">
              {isPlusActive && activeUntil
                ? `активен до ${activeUntil}`
                : "Статус аккаунта"}
            </span>
          </span>
        </Link>

        <nav className="space-y-1" aria-label="Главная навигация">
          {navItems.map((item) => (
            <SidebarLink
              key={item.href}
              item={item}
              active={pathname === item.href}
              labelClass={labelClass}
              itemAlignment={itemAlignment}
            />
          ))}
        </nav>

        <div className="my-4 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

        <nav className="space-y-1" aria-label="Продукты">
          <p
            className={cn(
              "mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#AEB8C8]/55",
              labelClass,
            )}
          >
            Продукты
          </p>
          {productItems.map((item) => (
            <SidebarLink
              key={item.href}
              item={item}
              active={pathname === item.href}
              labelClass={labelClass}
              itemAlignment={itemAlignment}
            />
          ))}
        </nav>
      </div>

      <nav
        className="relative shrink-0 space-y-1 border-t border-white/10 bg-[#0B0D14]/72 p-2.5"
        aria-label="Настройки"
      >
        {settingsItems.map((item) => (
          <SidebarLink
            key={item.href}
            item={item}
            active={pathname === item.href}
            labelClass={labelClass}
            itemAlignment={itemAlignment}
          />
        ))}
        <button
          type="button"
          onClick={handleLogout}
          className={cn(
            "flex min-h-11 w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium text-[#AEB8C8] transition hover:bg-white/[0.05] hover:text-[#F6F1E8] motion-reduce:transition-none",
            itemAlignment,
          )}
          aria-label="Выйти"
          title="Выйти"
        >
          <LogOut className="h-[18px] w-[18px] shrink-0" />
          <span className={labelClass}>Выйти</span>
        </button>
      </nav>
    </div>
  );
}

function SidebarLink({
  item,
  active,
  labelClass,
  itemAlignment,
}: {
  item: NavigationItem;
  active: boolean;
  labelClass: string;
  itemAlignment: string;
}) {
  return (
    <Link
      href={item.disabled ? "#" : item.href}
      className={cn(
        "group relative flex min-h-11 items-center gap-3 overflow-hidden rounded-xl px-3 py-2 text-sm font-medium transition motion-reduce:transition-none",
        item.disabled
          ? "cursor-not-allowed text-[#AEB8C8]/30"
          : active
            ? "border border-[#8DA8FF]/20 bg-[linear-gradient(100deg,rgba(91,63,214,0.24),rgba(141,168,255,0.08))] text-[#F6F1E8] shadow-[inset_3px_0_0_rgba(216,180,90,0.85)]"
            : "text-[#C8D0DE] hover:bg-white/[0.05] hover:text-[#F6F1E8]",
        itemAlignment,
      )}
      aria-label={item.title}
      aria-current={active ? "page" : undefined}
      aria-disabled={item.disabled || undefined}
      title={item.disabled ? `${item.title} — скоро` : item.title}
      onClick={item.disabled ? (event) => event.preventDefault() : undefined}
    >
      <item.icon
        className="h-[18px] w-[18px] shrink-0 transition-transform group-hover:scale-105 motion-reduce:transition-none"
        style={{ color: item.disabled ? undefined : item.color }}
      />
      <span className={cn("min-w-0 flex-1 truncate", labelClass)}>
        {item.title}
      </span>
      {item.disabled && (
        <span
          className={cn(
            "rounded-full border border-white/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-[#AEB8C8]/45",
            labelClass,
          )}
        >
          скоро
        </span>
      )}
    </Link>
  );
}
