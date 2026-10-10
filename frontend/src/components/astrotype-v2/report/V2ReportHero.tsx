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
      className="overflow-hidden rounded-[2rem] border border-border-default/25 bg-surface-subtle shadow-2xl shadow-black/30"
    >
      <div className="space-y-8 bg-[var(--hero-background)] p-6 text-text-primary md:p-10">
        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex rounded-full border border-border-default/45 bg-surface-subtle/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.32em] text-accent-gold shadow-elevated">
            {hero.eyebrow}
          </div>
          <div className="inline-flex rounded-full border border-border-default bg-surface-elevated/[0.06] px-4 py-2 text-[11px] font-medium uppercase tracking-[0.24em] text-text-secondary">
            Натальный портрет
          </div>
        </div>
        <div className="max-w-4xl space-y-5">
          <h1 className="text-4xl font-semibold tracking-tight md:text-6xl">
            {hero.title}
          </h1>
          <p className="text-lg leading-8 text-text-secondary md:text-xl">
            {hero.greeting}. Вот ваша натальная карта, собранная по вашим данным
            рождения.
          </p>
          <p className="max-w-3xl text-sm leading-7 text-text-secondary md:text-base">
            {hero.intro}
          </p>
        </div>
        {hero.birthDataItems.length > 0 && (
          <div className="rounded-3xl border border-border-default bg-surface-elevated/[0.04] p-5">
            <div className="mb-4 text-sm font-semibold uppercase tracking-[0.18em] text-accent-gold">
              Ваши данные рождения
            </div>
            <dl className="grid gap-4 md:grid-cols-2">
              {hero.birthDataItems.map((item) => (
                <div key={item.label} className="space-y-1">
                  <dt className="text-xs uppercase tracking-[0.14em] text-text-muted">
                    {item.label}
                  </dt>
                  <dd className="text-base font-medium text-text-primary">
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
            className="rounded-full border-border-default bg-transparent text-text-primary hover:bg-surface-elevated"
          >
            {isDownloadingPdf ? "Готовим PDF..." : hero.pdfLabel}
          </Button>
        </div>
      </div>
    </section>
  );
}
