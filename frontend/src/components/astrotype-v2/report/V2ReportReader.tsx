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
  return (
    <main
      data-v2-reader="canonical"
      className="min-h-screen bg-[radial-gradient(circle_at_16%_0%,#26304a_0%,#0b0d13_45%,#07080c_100%)] px-3 py-6 md:px-6 md:py-8"
    >
      <div className="mx-auto w-[min(96vw,1840px)] space-y-[18px]">
        <V2ReportHero
          hero={viewModel.hero}
          isRegenerating={isRegenerating}
          onRegenerate={onRegenerate}
        />

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
