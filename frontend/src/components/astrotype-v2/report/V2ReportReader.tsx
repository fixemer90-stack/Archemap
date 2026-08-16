import type { V2ReportReaderViewModel } from "@/lib/astrotype-v2/report-view-model";
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

        <section
          data-v2-reader-block="calculation_layer"
          className="rounded-[1.75rem] border border-[#D8B45A]/20 bg-[#0F172A] p-6 text-[#F5E9D0] md:p-8"
        >
          <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[#D8B45A]">
            Карта и ключевые показатели
          </div>
          <h2 className="mt-3 text-2xl font-semibold md:text-4xl">
            Расчётный слой будет раскрыт ниже текста
          </h2>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[#BFC6D8]">
            Данные уже приходят из canonical V2 API contract. Следующий slice
            заменит этот placeholder на таблицы положений, балансы, дома, сеть
            аспектов и расчётную матрицу из эталонного HTML.
          </p>
        </section>
      </div>
    </main>
  );
}
