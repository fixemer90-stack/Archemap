import { Button } from "@/components/ui/button";
import type { V2ReportHeroViewModel } from "@/lib/astrotype-v2/report-view-model";

interface V2ReportHeroProps {
  hero: V2ReportHeroViewModel;
  isDownloadingPdf: boolean;
  onDownloadPdf: () => void;
}

export function V2ReportHero({
  hero,
  isDownloadingPdf,
  onDownloadPdf,
}: V2ReportHeroProps) {
  return (
    <section
      data-v2-reader-block="hero"
      className="overflow-hidden rounded-[2rem] border border-[#D8B45A]/25 bg-[#101626] shadow-2xl shadow-black/30"
    >
      <div className="space-y-8 bg-[radial-gradient(circle_at_top_left,rgba(216,180,90,0.20),transparent_36%),linear-gradient(135deg,rgba(16,22,38,0.98),rgba(6,10,19,0.98))] p-6 text-[#F5E9D0] md:p-10">
        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex rounded-full border border-[#D8B45A]/45 bg-[#D8B45A]/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.32em] text-[#E9C86C] shadow-[0_0_36px_rgba(216,180,90,0.18)]">
            {hero.eyebrow}
          </div>
          <div className="inline-flex rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 text-[11px] font-medium uppercase tracking-[0.24em] text-[#D8DCE8]">
            Натальный портрет
          </div>
        </div>
        <div className="max-w-4xl space-y-5">
          <h1 className="text-4xl font-semibold tracking-tight md:text-6xl">
            {hero.title}
          </h1>
          <p className="text-lg leading-8 text-[#E6D9B8] md:text-xl">
            {hero.greeting}. Вот ваша натальная карта, собранная по вашим данным
            рождения.
          </p>
          <p className="max-w-3xl text-sm leading-7 text-[#BFC6D8] md:text-base">
            {hero.intro}
          </p>
        </div>
        {hero.birthDataItems.length > 0 && (
          <div className="rounded-3xl border border-white/12 bg-white/[0.04] p-5">
            <div className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-[#D8B45A]">
              Ваши данные рождения
            </div>
            <dl className="grid gap-4 md:grid-cols-2">
              {hero.birthDataItems.map((item) => (
                <div key={item.label} className="space-y-1">
                  <dt className="text-xs uppercase tracking-[0.14em] text-[#8E99B4]">
                    {item.label}
                  </dt>
                  <dd className="text-base font-medium text-[#F5E9D0]">
                    {item.value}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        )}
        <div className="flex flex-wrap gap-3 text-sm">
          <Button
            type="button"
            variant="outline"
            onClick={onDownloadPdf}
            disabled={isDownloadingPdf}
            className="rounded-full border-white/20 bg-transparent text-[#F5E9D0] hover:bg-white/10"
          >
            {isDownloadingPdf ? "Готовим PDF..." : hero.pdfLabel}
          </Button>
        </div>
      </div>
    </section>
  );
}
