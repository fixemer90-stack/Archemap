import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Billing",
};

export default function BillingPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Billing</h1>
        <p className="text-muted-foreground">
          View your payment history and manage billing settings.
        </p>
      </div>

      <div className="rounded-lg border bg-card p-8 text-center shadow-sm">
        <p className="text-muted-foreground">
          Billing features coming soon. Connect a payment method to get started.
        </p>
      </div>
    </div>
  );
}
