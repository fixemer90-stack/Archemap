"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { cn } from "@/lib/utils";

const options = [
  { value: "light", label: "Светлая", icon: Sun },
  { value: "dark", label: "Тёмная", icon: Moon },
  { value: "system", label: "Как в системе", icon: Monitor },
] as const;

const subscribeToHydration = () => () => undefined;

export function ThemeSelector() {
  const { theme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    subscribeToHydration,
    () => true,
    () => false,
  );

  return (
    <fieldset className="rounded-[24px] border border-border-default bg-surface p-5 shadow-soft sm:p-7">
      <legend className="px-2 text-sm font-semibold uppercase tracking-[0.16em] text-text-muted">
        Оформление
      </legend>
      <div className="mt-1">
        <h2 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-text-primary">
          Тема интерфейса
        </h2>
        <p className="mt-2 text-sm leading-6 text-text-secondary">
          Выберите постоянную тему или синхронизацию с настройкой устройства.
        </p>
      </div>
      <div
        className="mt-5 grid gap-2 sm:grid-cols-3"
        aria-label="Тема интерфейса"
      >
        {options.map(({ value, label, icon: Icon }) => {
          const selected = mounted && theme === value;
          return (
            <button
              key={value}
              type="button"
              aria-pressed={selected}
              disabled={!mounted}
              onClick={() => setTheme(value)}
              className={cn(
                "flex min-h-12 items-center justify-center gap-2 rounded-2xl border px-4 py-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-wait disabled:opacity-70",
                selected
                  ? "border-control bg-accent-violet-soft text-text-primary shadow-soft"
                  : "border-border-default bg-surface-subtle text-text-secondary hover:border-border-strong hover:text-text-primary",
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {label}
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}
