import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function ProductSurfaceShell({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <main
      data-product-surface="shell"
      className={cn(
        "relative min-h-screen overflow-hidden bg-[var(--surface-background)] text-[var(--surface-text)]",
        className,
      )}
    >
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 opacity-[0.055]"
        style={{
          backgroundImage:
            "radial-gradient(circle, #D8DCE8 1px, transparent 1px)",
          backgroundSize: "52px 52px",
        }}
      />
      <div className="relative z-10 mx-auto w-[min(94vw,1500px)] py-8 md:py-12">
        {children}
      </div>
    </main>
  );
}

export function ProductSurfaceHero({
  eyebrow,
  title,
  lead,
  children,
  aside,
  className,
}: {
  eyebrow: string;
  title: ReactNode;
  lead: ReactNode;
  children?: ReactNode;
  aside?: ReactNode;
  className?: string;
}) {
  return (
    <section
      data-product-surface="hero"
      className={cn(
        "relative overflow-hidden rounded-[34px] border border-border-default bg-[var(--hero-background)] px-6 py-9 shadow-2xl shadow-black/30 md:px-10 md:py-12 lg:px-12",
        className,
      )}
    >
      <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-accent-gold to-transparent" />
      <div className="absolute -right-28 -top-28 h-80 w-80 rounded-full bg-accent-violet-soft blur-3xl" />
      <div className="absolute -bottom-32 left-12 h-72 w-72 rounded-full bg-accent-gold-soft blur-3xl" />
      <div className="relative grid gap-9 lg:grid-cols-[minmax(0,1fr)_420px] lg:items-end">
        <div className="max-w-4xl space-y-6">
          <SurfaceEyebrow>{eyebrow}</SurfaceEyebrow>
          <h1 className="font-[family-name:var(--font-cormorant)] text-5xl font-semibold leading-[0.95] tracking-tight text-text-primary md:text-6xl xl:text-7xl">
            {title}
          </h1>
          <p className="max-w-3xl text-base leading-8 text-text-secondary md:text-lg">
            {lead}
          </p>
          {children}
        </div>
        {aside ? <div className="relative">{aside}</div> : null}
      </div>
    </section>
  );
}

export function ProductSurfaceCard({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <article
      data-product-surface="card"
      className={cn(
        "rounded-[28px] border border-border-default bg-surface-subtle p-6 shadow-xl shadow-black/10 backdrop-blur-xl md:p-7",
        className,
      )}
    >
      {children}
    </article>
  );
}

export function SurfaceEyebrow({ children }: { children: ReactNode }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-[0.32em] text-accent-gold">
      {children}
    </p>
  );
}

export function SurfaceActionRow({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:items-center">
      {children}
    </div>
  );
}
