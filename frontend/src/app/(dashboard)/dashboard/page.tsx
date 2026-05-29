import type { Metadata } from "next";
import { CreditCard, DollarSign, Calendar, TrendingDown } from "lucide-react";

export const metadata: Metadata = {
  title: "Dashboard",
};

const stats = [
  {
    label: "Active Subscriptions",
    value: "12",
    icon: CreditCard,
    change: "+2 this month",
  },
  {
    label: "Monthly Spend",
    value: "$148.50",
    icon: DollarSign,
    change: "-$12 from last month",
  },
  {
    label: "Next Renewal",
    value: "Jun 3",
    icon: Calendar,
    change: "Netflix — $15.99",
  },
  {
    label: "Total Saved",
    value: "$89.00",
    icon: TrendingDown,
    change: "Via cancellation alerts",
  },
];

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Here&apos;s an overview of your subscriptions.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-lg border bg-card p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-muted-foreground">
                {stat.label}
              </p>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="mt-2 text-2xl font-bold">{stat.value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{stat.change}</p>
          </div>
        ))}
      </div>

      {/* Recent Activity */}
      <div className="rounded-lg border bg-card">
        <div className="border-b p-4">
          <h2 className="text-sm font-semibold">Recent Activity</h2>
        </div>
        <div className="divide-y">
          {[
            { name: "Netflix", amount: "$15.99", date: "May 28", status: "Paid" },
            { name: "Spotify", amount: "$9.99", date: "May 25", status: "Paid" },
            { name: "AWS", amount: "$42.30", date: "May 22", status: "Paid" },
          ].map((item) => (
            <div key={item.name} className="flex items-center justify-between p-4">
              <div>
                <p className="text-sm font-medium">{item.name}</p>
                <p className="text-xs text-muted-foreground">{item.date}</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-medium">{item.amount}</p>
                <p className="text-xs text-muted-foreground">{item.status}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
