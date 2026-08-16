"use client";

import { useParams } from "next/navigation";
import { RefreshCw } from "lucide-react";
import { V2ReportReader } from "@/components/astrotype-v2/report/V2ReportReader";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import type { AstrotypeV2ReportResponse } from "@/lib/api/astrotype-v2";
import { buildV2ReportReaderViewModel } from "@/lib/astrotype-v2/report-view-model";
import { useV2ReportGeneration } from "@/lib/astrotype-v2/use-v2-report-generation";

function ReportReady({
  report,
  onRegenerate,
  isRegenerating,
}: {
  report: AstrotypeV2ReportResponse;
  onRegenerate: () => void;
  isRegenerating: boolean;
}) {
  const viewModel = buildV2ReportReaderViewModel(report);
  return (
    <V2ReportReader
      viewModel={viewModel}
      onRegenerate={onRegenerate}
      isRegenerating={isRegenerating}
    />
  );
}

export default function AstrotypeV2ReportPage() {
  const params = useParams();
  const profileId = params.profileId as string;
  const generation = useV2ReportGeneration(profileId);

  if (generation.state === "ready" && generation.report) {
    return (
      <ReportReady
        report={generation.report}
        onRegenerate={generation.regenerate}
        isRegenerating={generation.isRegenerating}
      />
    );
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
          {generation.canRetry && (
            <Button onClick={generation.retry}>
              <RefreshCw className="h-4 w-4" />
              Перегенерировать V2 отчёт
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
