"use client";

import Link from "next/link";
import { useTheme } from "next-themes";
import { Moon, Sun, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";

export function Header() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const activeTheme = theme === "system" ? resolvedTheme : theme;
  const isDark = activeTheme !== "light";
  const nextTheme = isDark ? "light" : "dark";

  return (
    <header className="flex h-16 items-center justify-between border-b px-6">
      <div className="flex items-center gap-4">
        <Link href="/dashboard" className="text-lg font-bold">
          Astrotype
        </Link>
      </div>

      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setTheme(nextTheme)}
          aria-label={isDark ? "Включить светлую тему" : "Включить тёмную тему"}
          title={isDark ? "Светлая тема" : "Тёмная тема"}
          suppressHydrationWarning
        >
          <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        </Button>

        <Button variant="ghost" size="icon" aria-label="Уведомления">
          <Bell className="h-5 w-5" />
        </Button>

        <div className="ml-2 flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-muted" />
        </div>
      </div>
    </header>
  );
}
