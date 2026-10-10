"use client";

import Link from "next/link";
import { Bell, Menu } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useUIStore } from "@/stores/ui-store";

export function Header() {
  const toggleMobileSidebar = useUIStore((state) => state.toggleMobileSidebar);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-white/10 bg-[#0B0D14]/72 px-3 backdrop-blur-2xl sm:px-5 md:px-6">
      <div className="flex min-w-0 items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleMobileSidebar}
          className="md:hidden"
          aria-label="Открыть меню"
          title="Открыть меню"
        >
          <Menu className="h-5 w-5" />
        </Button>
        <Link
          href="/dashboard"
          className="truncate font-[family-name:var(--font-cormorant)] text-xl font-semibold tracking-[0.04em] text-[#F6F1E8] md:hidden"
        >
          Astrotype
        </Link>
        <p className="hidden text-xs font-semibold uppercase tracking-[0.18em] text-[#AEB8C8] md:block">
          Личный кабинет
        </p>
      </div>

      <div className="flex items-center gap-1 sm:gap-2">
        <Button variant="ghost" size="icon" aria-label="Уведомления">
          <Bell className="h-5 w-5" />
        </Button>

        <div
          className="ml-1 h-8 w-8 rounded-full border border-[#D8B45A]/30 bg-[radial-gradient(circle_at_35%_30%,rgba(216,180,90,0.32),rgba(91,63,214,0.28)_58%,rgba(255,255,255,0.04))] sm:ml-2"
          aria-hidden="true"
        />
      </div>
    </header>
  );
}
