import { Button } from "@/components/ui/button";
import type { V2ReportHeroViewModel } from "@/lib/astrotype-v2/report-view-model";

interface V2ReportHeroProps {
  hero: V2ReportHeroViewModel;
  progressLabel: string;
  isRegenerating: boolean;
  onRegenerate: () => void;
}

export function V2ReportHero({
  hero,
  progressLabel,
  isRegenerating,
  onRegenerate,
}: V2ReportHeroProps) {
  return (
    <section
      data-v2-reader-block="hero"
      className="overflow-hidden rounded-[2rem] border border-[#D8B45A]/25 bg-[#101626] shadow-2xl shadow-black/30"
    >
      <div className="space-y-8 bg-[radial-gradient(circle_at_top_left,rgba(216,180,90,0.20),transparent_36%),linear-gradient(135deg,rgba(16,22,38,0.98),rgba(6,10,19,0.98))] p-6 text-[#F5E9D0] md:p-10">
        <div className="inline-flex rounded-full border border-[#D8B45A]/40 px-4 py-2 text-xs font-semibold uppercase tracking-[0.26em] text-[#D8B45A]">
          {hero.eyebrow}
        </div>
        <div className="max-w-4xl space-y-5">
          <h1 className="text-4xl font-semibold tracking-tight md:text-6xl">
            {hero.title}
          </h1>
          <p className="text-lg leading-8 text-[#E6D9B8] md:text-xl">
            Это не dashboard и не набор технических карточек: перед вами цельный
            натальный портрет, где сначала идёт мягкое повествование, а
            расчётная основа вынесена ниже.
          </p>
          <p className="max-w-3xl text-sm leading-7 text-[#BFC6D8] md:text-base">
            Верхняя часть написана как связный отчёт о личности. Нижний слой
            показывает, какие положения, балансы домов и аспекты поддерживают
            интерпретацию.
          </p>
        </div>
        <div className="flex flex-wrap gap-3 text-sm">
          <span className="rounded-full bg-[#D8B45A] px-4 py-2 font-semibold text-[#111827]">
            {hero.statusLabel}
          </span>
          <span className="rounded-full border border-white/15 px-4 py-2 text-[#E6D9B8]">
            {hero.calculationLabel}
          </span>
          <span className="rounded-full border border-white/15 px-4 py-2 text-[#E6D9B8]">
            {progressLabel}
          </span>
          <Button
            type="button"
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="rounded-full bg-white text-[#111827] hover:bg-[#F5E9D0]"
          >
            {isRegenerating ? "Перегенерируем..." : "Перегенерировать"}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="rounded-full border-white/20 bg-transparent text-[#F5E9D0] hover:bg-white/10"
          >
            {hero.pdfLabel}
          </Button>
        </div>
      </div>
    </section>
  );
}
