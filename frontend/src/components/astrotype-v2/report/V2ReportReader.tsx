import Link from "next/link";

import { Button } from "@/components/ui/button";
import type { V2ReportReaderViewModel } from "@/lib/astrotype-v2/report-view-model";
import { V2CalculationLayer } from "./V2CalculationLayer";
import { V2NarrativeSectionCard } from "./V2NarrativeSectionCard";
import { V2ReportHero } from "./V2ReportHero";

interface V2ReportReaderProps {
  viewModel: V2ReportReaderViewModel;
  isDownloadingPdf: boolean;
  onDownloadPdf: () => void;
  pdfError?: string | null;
}

export function V2ReportReader({
  viewModel,
  isDownloadingPdf,
  onDownloadPdf,
  pdfError,
}: V2ReportReaderProps) {
  return (
    <main
      data-v2-reader="canonical"
      className="min-h-screen bg-[radial-gradient(circle_at_16%_0%,#26304a_0%,#0b0d13_45%,#07080c_100%)] px-3 py-6 md:px-6 md:py-8"
    >
      <div className="mx-auto w-[min(96vw,1840px)] space-y-[18px]">
        <div className="flex justify-start">
          <Button variant="outline" asChild>
            <Link href="/dashboard">В кабинет</Link>
          </Button>
        </div>

        <V2ReportHero
          hero={viewModel.hero}
          isDownloadingPdf={isDownloadingPdf}
          onDownloadPdf={onDownloadPdf}
        />

        {pdfError && (
          <div className="rounded-2xl border border-red-300/30 bg-red-950/30 px-4 py-3 text-sm text-red-100">
            {pdfError}
          </div>
        )}

        <section data-v2-reader-block="narrative" className="space-y-[18px]">
          {viewModel.sections.map((section) => (
            <V2NarrativeSectionCard key={section.id} section={section} />
          ))}
        </section>

        <V2CalculationLayer layer={viewModel.calculationLayer} />
      </div>
    </main>
  );
}
