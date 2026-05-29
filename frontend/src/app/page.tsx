import Link from "next/link";
import { ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <span className="text-xl font-bold">Archemap</span>
          <nav className="flex items-center gap-4">
            <Link
              href="/login"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Sign in
            </Link>
            <Link
              href="/login"
              className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Get Started
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1">
        <section className="container mx-auto flex flex-col items-center justify-center gap-6 px-4 py-24 text-center md:py-32">
          <div className="rounded-full border bg-muted px-4 py-1.5 text-sm">
            Subscription management, simplified
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
            Manage your subscriptions
            <br />
            <span className="text-primary">with Archemap</span>
          </h1>
          <p className="max-w-2xl text-lg text-muted-foreground">
            Track, manage, and optimize all your subscriptions in one place.
            Get insights into your spending and never miss a renewal.
          </p>
          <div className="flex gap-4">
            <Link
              href="/login"
              className="inline-flex h-11 items-center gap-2 rounded-md bg-primary px-6 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              Get Started
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/dashboard"
              className="inline-flex h-11 items-center rounded-md border bg-background px-6 text-sm font-medium hover:bg-accent transition-colors"
            >
              View Dashboard
            </Link>
          </div>
        </section>

        {/* Features */}
        <section className="border-t bg-muted/50 py-24">
          <div className="container mx-auto grid gap-8 px-4 md:grid-cols-3">
            {[
              {
                title: "Track Everything",
                description:
                  "Monitor all your subscriptions in a single, unified dashboard.",
              },
              {
                title: "Smart Insights",
                description:
                  "Get detailed analytics and spending breakdowns by category.",
              },
              {
                title: "Billing Alerts",
                description:
                  "Never miss a renewal with smart notifications and reminders.",
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="rounded-lg border bg-card p-6 shadow-sm"
              >
                <h3 className="text-lg font-semibold">{feature.title}</h3>
                <p className="mt-2 text-sm text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          &copy; {new Date().getFullYear()} Archemap. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
