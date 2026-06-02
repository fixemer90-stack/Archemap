import { NatalChart } from "@/components/chart/natal-chart";
import { SocionicsResult } from "@/components/chart/socionics-result";
import { TermHelp } from "@/components/glossary/term-help";
import type { ReportViewModel } from "@/lib/report/view-model";

export function TechnicalDetailsAccordion({ data }: { data: ReportViewModel }) {
  return (
    <details className="rounded-lg border bg-card text-card-foreground shadow-sm">
      <summary className="min-h-14 cursor-pointer p-6 text-xl font-semibold">
        Технические детали расчёта
      </summary>
      <div className="space-y-6 border-t p-6">
        <div className="rounded-lg bg-muted p-4 text-sm leading-6 text-muted-foreground">
          Здесь оставлены full chart wheel, таблицы, function radar,{" "}
          <TermHelp term="Model A" />, числовые показатели,{" "}
          <TermHelp term="Уверенность" /> и{" "}
          <TermHelp term="Цепочка доказательств" />. Это нужно для проверки
          расчёта, но не должно мешать первому чтению.
        </div>

        <section>
          <h3 className="mb-2 text-lg font-semibold">Как читать графики</h3>
          <p className="text-sm leading-6 text-muted-foreground">
            Графики ниже — не отдельный диагноз, а визуальная проверка исходных
            факторов. Сначала читайте смысловые блоки выше, а сюда
            возвращайтесь, если хотите сверить планеты, дома, аспекты, function
            strengths и числовые показатели.
          </p>
        </section>

        <section>
          <h3 className="mb-3 text-lg font-semibold">Полная натальная карта</h3>
          <NatalChart chart={data.chart} />
        </section>

        <section>
          <h3 className="mb-3 text-lg font-semibold">
            Полная соционическая детализация
          </h3>
          <p className="mb-3 text-sm leading-6 text-muted-foreground">
            Здесь находятся Top-3, function radar и Model A. В основном потоке
            они скрыты, чтобы не превращать отчёт в debug view.
          </p>
          <SocionicsResult data={data.socionics} />
        </section>
      </div>
    </details>
  );
}
