"use client";

import Link from "next/link";
import { Menu, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { Button } from "@/components/ui/button";
import { useUIStore } from "@/stores/ui-store";

const subscribeToHydration = () => () => undefined;

export function Header() {
  const toggleMobileSidebar = useUIStore((state) => state.toggleMobileSidebar);
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false,
  );
  const nextTheme = resolvedTheme === "dark" ? "light" : "dark";
  const themeToggleLabel =
    nextTheme === "light" ? "Включить светлую тему" : "Включить тёмную тему";

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

      <Button
        variant="ghost"
        size="icon"
        type="button"
        data-theme-toggle="quick"
        disabled={!mounted}
        onClick={() => setTheme(nextTheme)}
        className="ml-auto rounded-full border border-border-default bg-surface-subtle text-text-secondary shadow-soft hover:border-border-strong hover:bg-control-hover hover:text-text-primary disabled:opacity-0"
        aria-label={themeToggleLabel}
        title={themeToggleLabel}
      >
        {resolvedTheme === "dark" ? (
          <Sun className="h-[18px] w-[18px]" aria-hidden="true" />
        ) : (
          <Moon className="h-[18px] w-[18px]" aria-hidden="true" />
        )}
      </Button>
    </header>
  );
}
