import Link from "next/link";
import { ArrowRight, CreditCard, BarChart3, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";

const features = [
  {
    icon: CreditCard,
    title: "Track Everything",
    description:
      "Monitor all your subscriptions in a single, unified dashboard. See what you're paying for and when.",
  },
  {
    icon: BarChart3,
    title: "Smart Insights",
    description:
      "Get detailed analytics and spending breakdowns by category. Identify savings opportunities.",
  },
  {
    icon: Bell,
    title: "Billing Alerts",
    description:
      "Never miss a renewal with smart notifications and reminders before charges hit.",
  },
];

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <span className="text-xl font-bold">Archemap</span>
          <nav className="flex items-center gap-3">
            <Button variant="ghost" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
            <Button asChild>
              <Link href="/login">Get Started</Link>
            </Button>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1">
        <section className="container mx-auto flex flex-col items-center justify-center gap-6 px-4 py-20 text-center md:py-28">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Manage your subscriptions
            <br />
            with Archemap
          </h1>
          <p className="max-w-xl text-lg text-muted-foreground">
            Track, manage, and optimize all your subscriptions in one place. Get
            insights into your spending and never miss a renewal.
          </p>
          <div className="flex gap-3">
            <Button size="lg" asChild>
              <Link href="/login">
                Get Started
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" asChild>
              <Link href="/dashboard">View Dashboard</Link>
            </Button>
          </div>
        </section>

        {/* Features */}
        <section className="border-t bg-muted/30 py-20">
          <div className="container mx-auto grid gap-6 px-4 sm:grid-cols-2 md:grid-cols-3">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="rounded-lg border bg-card p-6"
              >
                <feature.icon className="h-8 w-8 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-semibold">{feature.title}</h3>
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
