import type { V2ReportReaderViewModel } from "@/lib/astrotype-v2/report-view-model";
import { V2CalculationLayer } from "./V2CalculationLayer";
import { V2NarrativeSectionCard } from "./V2NarrativeSectionCard";
import { V2ReportHero } from "./V2ReportHero";

interface V2ReportReaderProps {
  viewModel: V2ReportReaderViewModel;
  isRegenerating: boolean;
  onRegenerate: () => void;
}

export function V2ReportReader({
  viewModel,
  isRegenerating,
  onRegenerate,
}: V2ReportReaderProps) {
  const progressLabel = `Сегменты ${viewModel.progress.ready_segments}/${viewModel.progress.total_segments || viewModel.sections.length}`;

  return (
    <main
      data-v2-reader="canonical"
      className="min-h-screen bg-[#060A13] px-4 py-8 md:px-8 md:py-12"
    >
      <div className="mx-auto max-w-6xl space-y-8">
        <V2ReportHero
          hero={viewModel.hero}
          progressLabel={progressLabel}
          isRegenerating={isRegenerating}
          onRegenerate={onRegenerate}
        />

        <section data-v2-reader-block="narrative" className="space-y-6">
          {viewModel.sections.map((section) => (
            <V2NarrativeSectionCard key={section.id} section={section} />
          ))}
        </section>

        <V2CalculationLayer layer={viewModel.calculationLayer} />
      </div>
    </main>
  );
}
