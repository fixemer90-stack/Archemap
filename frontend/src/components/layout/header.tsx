"use client";

import Link from "next/link";
import { Menu } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useUIStore } from "@/stores/ui-store";

export function Header() {
  const toggleMobileSidebar = useUIStore((state) => state.toggleMobileSidebar);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center border-b border-border-default bg-surface/90 px-3 backdrop-blur-2xl sm:px-5 md:px-6">
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
          className="truncate font-[family-name:var(--font-cormorant)] text-xl font-semibold tracking-[0.04em] text-text-primary md:hidden"
        >
          Astrotype
        </Link>
        <p className="hidden text-xs font-semibold uppercase tracking-[0.18em] text-text-muted md:block">
          Личный кабинет
        </p>
      </div>
    </header>
  );
}
