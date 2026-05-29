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
    title: "Dashboard",
    href: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    title: "Subscriptions",
    href: "/subscriptions",
    icon: CreditCard,
  },
  {
    title: "Billing",
    href: "/billing",
    icon: Receipt,
  },
  {
    title: "Settings",
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
        "flex h-screen flex-col border-r bg-card transition-all duration-300",
        sidebarOpen ? "w-64" : "w-16",
      )}
    >
      <div className="flex h-16 items-center border-b px-4">
        {sidebarOpen && (
          <span className="text-lg font-bold">Archemap</span>
        )}
        {!sidebarOpen && <span className="mx-auto text-lg font-bold">A</span>}
      </div>

      <nav className="flex-1 space-y-1 p-2" aria-label="Main navigation">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
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

      <div className="border-t p-2">
        <button
          onClick={handleLogout}
          className={cn(
            "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
            !sidebarOpen && "justify-center",
          )}
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut className="h-5 w-5 shrink-0" />
          {sidebarOpen && <span>Sign out</span>}
        </button>
      </div>
    </aside>
  );
}
