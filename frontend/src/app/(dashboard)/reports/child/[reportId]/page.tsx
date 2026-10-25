import { ChildReportReader } from "@/components/child-report/child-report-reader";

export default async function ChildReportPage({
  params,
}: {
  params: Promise<{ reportId: string }>;
}) {
  const { reportId } = await params;
  return (
    <main className="px-4 sm:px-6">
      <ChildReportReader key={reportId} reportId={reportId} />
    </main>
  );
}
