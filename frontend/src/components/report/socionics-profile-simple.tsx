import { TermHelp } from "@/components/glossary/term-help";
import { SectionCard } from "@/components/report/section-card";
import type { ReportViewModel } from "@/lib/report/view-model";

export function SocionicsProfileSimple({
  data,
}: {
  data: ReportViewModel["socionics_summary"];
}) {
  return (
    <SectionCard
      title="Соционический профиль"
      description="Соционика — дополнительная типологическая линза. Её лучше читать после астрологической основы и практических выводов."
    >
      <div className="rounded-lg border p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="text-sm text-muted-foreground">
              Вероятный <TermHelp term="Соционический тип" />
            </div>
            <h3 className="mt-1 text-2xl font-semibold">
              {data.name} · {data.type}
            </h3>
          </div>
          <div className="rounded-full bg-primary/10 px-3 py-1 text-sm text-primary">
            {data.confidence_label}
          </div>
        </div>

        <p className="mt-4 leading-7 text-muted-foreground">
          {data.explanation}
        </p>
        <ul className="mt-5 grid gap-2 text-sm leading-6 text-muted-foreground">
          {data.insights.map((item) => (
            <li key={item} className="rounded-md bg-muted p-3">
              {item}
            </li>
          ))}
        </ul>

        <div className="mt-4 rounded-lg bg-muted p-4 text-sm leading-6">
          <TermHelp term="Уверенность" /> показан словами, без числовых
          значений. Полная типологическая механика скрыта в технических деталях
          ниже.
        </div>
      </div>
    </SectionCard>
  );
}
