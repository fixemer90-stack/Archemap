import { TermHelp } from "@/components/glossary/term-help";
import { SectionCard } from "@/components/report/section-card";
import type { ReportViewModel } from "@/lib/report/view-model";

export function ArchetypeProfileSummary({
  archetype,
}: {
  archetype: ReportViewModel["archetype"];
}) {
  return (
    <SectionCard
      title="Архетипический профиль"
      description="Архетип — это запоминающаяся модель поведения, а не диагноз и не жёсткий ярлык."
    >
      <div className="rounded-lg border p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="text-sm text-muted-foreground">
              Основной <TermHelp term="Архетип" />
            </div>
            <h3 className="mt-1 text-2xl font-semibold">{archetype.name}</h3>
          </div>
          <div className="rounded-full bg-primary/10 px-3 py-1 text-sm text-primary">
            {archetype.confidence_label}
          </div>
        </div>
        <p className="mt-4 leading-7 text-muted-foreground">{archetype.text}</p>

        <ul className="mt-5 grid gap-2 text-sm leading-6 text-muted-foreground">
          {archetype.manifestations.map((item) => (
            <li key={item} className="rounded-md bg-muted p-3">
              {item}
            </li>
          ))}
        </ul>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg bg-primary/5 p-4">
            <div className="font-medium">Светлая сторона</div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {archetype.light}
            </p>
          </div>
          <div className="rounded-lg bg-muted p-4">
            <div className="font-medium">Тень</div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {archetype.shadow}
            </p>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
