import { SectionCard } from "@/components/report/section-card";
import type { ReportViewModel } from "@/lib/report/view-model";

export function ReportExecutiveSummary({
  summary,
}: {
  summary: ReportViewModel["summary"];
}) {
  return (
    <SectionCard
      title="Главное о вас"
      description="Сначала — смысл, а не схемы и проценты. Это короткая выжимка отчёта простым языком."
    >
      <div className="grid gap-4">
        <div className="rounded-xl border bg-primary/5 p-5 leading-7">
          <div className="text-sm font-medium text-primary">Главная тема</div>
          <p className="mt-2">{summary.main_theme}</p>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg bg-muted p-4 leading-7">
            <div className="font-medium">Сила</div>
            <p className="mt-2 text-sm text-muted-foreground">
              {summary.strength}
            </p>
          </div>
          <div className="rounded-lg bg-muted p-4 leading-7">
            <div className="font-medium">Зона внимания</div>
            <p className="mt-2 text-sm text-muted-foreground">
              {summary.attention}
            </p>
          </div>
        </div>
        <ul className="grid gap-3">
          {summary.bullets.map((item) => (
            <li key={item} className="rounded-lg border p-4 leading-7">
              {item}
            </li>
          ))}
        </ul>
      </div>
    </SectionCard>
  );
}
