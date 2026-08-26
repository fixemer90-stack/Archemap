import type { V2ReportReaderViewModel } from "@/lib/astrotype-v2/report-view-model";
import { V2CalculationLayer } from "./V2CalculationLayer";
import { V2GlossaryTerm } from "./V2GlossaryText";
import { V2NarrativeSectionCard } from "./V2NarrativeSectionCard";
import { V2ReportHero } from "./V2ReportHero";

interface V2ReportReaderProps {
  viewModel: V2ReportReaderViewModel;
  isRegenerating: boolean;
  isDownloadingPdf: boolean;
  onRegenerate: () => void;
  onDownloadPdf: () => void;
  pdfError?: string | null;
}

export function V2ReportReader({
  viewModel,
  isRegenerating,
  isDownloadingPdf,
  onRegenerate,
  onDownloadPdf,
  pdfError,
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
          isDownloadingPdf={isDownloadingPdf}
          onRegenerate={onRegenerate}
          onDownloadPdf={onDownloadPdf}
        />

        {pdfError && (
          <div className="rounded-2xl border border-red-300/30 bg-red-950/30 px-4 py-3 text-sm text-red-100">
            {pdfError}
          </div>
        )}

        <V2GlossaryHelpStrip />

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

function V2GlossaryHelpStrip() {
  return (
    <section
      data-v2-reader-block="glossary"
      className="rounded-[22px] border border-[#D9B86F]/20 bg-[linear-gradient(180deg,rgba(217,184,111,0.10),rgba(255,255,255,0.025))] p-4 text-[13px] leading-[1.5] text-[#DCE4F3] shadow-[0_20px_70px_rgba(0,0,0,0.22)] md:p-5"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <span className="font-semibold uppercase tracking-[0.08em] text-[#D9B86F]">
          Словарь терминов
        </span>
        <span className="text-[#9FB0CC]">Наведи на сложное слово:</span>
        <V2GlossaryTerm term="Натальная карта" />
        <V2GlossaryTerm term="Асцендент" />
        <V2GlossaryTerm term="MC" />
        <V2GlossaryTerm term="Дом" />
        <V2GlossaryTerm term="Аспект" />
        <V2GlossaryTerm term="Орб" />
        <V2GlossaryTerm term="Стихия" />
        <V2GlossaryTerm term="Модальность" />
      </div>
    </section>
  );
}
