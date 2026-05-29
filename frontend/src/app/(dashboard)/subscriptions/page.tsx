import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Subscriptions",
};

export default function SubscriptionsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Subscriptions</h1>
          <p className="text-muted-foreground">
            Manage and track all your subscriptions.
          </p>
        </div>
        <button className="inline-flex h-10 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90 transition-colors">
          Add Subscription
        </button>
      </div>

      <div className="rounded-lg border bg-card p-8 text-center shadow-sm">
        <p className="text-muted-foreground">
          No subscriptions yet. Add your first subscription to get started.
        </p>
      </div>
    </div>
  );
}
