"use client";

import Link from "next/link";
import { useState } from "react";
import { useParams } from "next/navigation";
import { V2ReportReader } from "@/components/astrotype-v2/report/V2ReportReader";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  downloadAstrotypeV2ReportPdf,
  type AstrotypeV2FullReportResponse,
  type AstrotypeV2LockedReportResponse,
} from "@/lib/api/astrotype-v2";
import { buildV2ReportReaderViewModel } from "@/lib/astrotype-v2/report-view-model";
import { useV2ReportGeneration } from "@/lib/astrotype-v2/use-v2-report-generation";

function ReportReady({ report }: { report: AstrotypeV2FullReportResponse }) {
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState<string | null>(null);

  async function handleDownloadPdf() {
    setIsDownloadingPdf(true);
    setPdfError(null);
    try {
      await downloadAstrotypeV2ReportPdf(report.report.id);
    } catch (error) {
      setPdfError(
        error instanceof Error ? error.message : "Не удалось скачать PDF.",
      );
    } finally {
      setIsDownloadingPdf(false);
    }
  }
  const viewModel = buildV2ReportReaderViewModel(report);
  return (
    <V2ReportReader
      viewModel={viewModel}
      isDownloadingPdf={isDownloadingPdf}
      onDownloadPdf={handleDownloadPdf}
      pdfError={pdfError}
    />
  );
}

function LockedReportAccess({
  locked,
}: {
  locked: AstrotypeV2LockedReportResponse;
}) {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card className="border-[rgba(216,180,90,0.30)] bg-[rgba(216,180,90,0.06)]">
        <CardHeader>
          <CardDescription>Доступ к отчёту</CardDescription>
          <CardTitle>{locked.upgrade.title}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm leading-6 text-[#D8DCE8]">
          <p>{locked.upgrade.description}</p>
          <Button asChild>
            <Link href={locked.upgrade.href}>Открыть оплату</Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default function AstrotypeV2ReportPage() {
  const params = useParams();
  const profileId = params.profileId as string;
  const generation = useV2ReportGeneration(profileId);

  if (generation.report) {
    return <ReportReady report={generation.report} />;
  }

  if (generation.lockedAccess) {
    return <LockedReportAccess locked={generation.lockedAccess} />;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card>
        <CardHeader>
          <CardDescription>Astrotype V2 · natal-only</CardDescription>
          <CardTitle>Ваш V2 отчёт</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm leading-6 text-[#D8DCE8]">
          <p>{generation.error || generation.message}</p>
          <p className="text-xs text-muted-foreground">
            state: {generation.state}
          </p>
          {generation.generationId && (
            <p className="text-xs text-muted-foreground">
              generation_id: {generation.generationId}
            </p>
          )}
          {generation.reportId && (
            <p className="text-xs text-muted-foreground">
              report_id: {generation.reportId}
            </p>
          )}
          {generation.progress && (
            <p className="text-xs text-muted-foreground">
              segments: {generation.progress.ready_segments}/
              {generation.progress.total_segments}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
