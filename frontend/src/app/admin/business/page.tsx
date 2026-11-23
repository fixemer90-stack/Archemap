import type { Metadata } from "next";

import { BusinessOverview } from "@/components/admin/business-overview";

export const metadata: Metadata = {
  title: "Бизнес-обзор",
  robots: { index: false, follow: false },
};

export default function AdminBusinessPage() {
  return <BusinessOverview />;
}
