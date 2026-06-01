import { SectionCard } from "@/components/report/section-card";
import type { ReportViewModel } from "@/lib/report/view-model";

function RecommendationColumn({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  return (
    <div className="rounded-lg border p-4">
      <h3 className="font-semibold">{title}</h3>
      <ul className="mt-3 grid gap-2 text-sm leading-6 text-muted-foreground">
        {items.map((item) => (
          <li key={item}>• {item}</li>
        ))}
      </ul>
    </div>
  );
}

export function PracticalRecommendations({
  recommendations,
}: {
  recommendations: ReportViewModel["recommendations"];
}) {
  return (
    <SectionCard
      title="Практические рекомендации"
      description="Эта часть важнее процентов: что реально можно попробовать и применить."
    >
      <div className="grid gap-4 md:grid-cols-2">
        <RecommendationColumn
          title="Что усилить"
          items={recommendations.strengthen}
        />
        <RecommendationColumn
          title="Что беречь"
          items={recommendations.protect}
        />
        <RecommendationColumn
          title="Что не делать через силу"
          items={recommendations.do_not_force}
        />
        <RecommendationColumn
          title="Среда, ритм, коммуникация"
          items={recommendations.environment}
        />
      </div>

      <div className="mt-5 rounded-xl bg-primary/5 p-5">
        <h3 className="font-semibold">Мини-чеклист на неделю</h3>
        <ol className="mt-3 grid gap-3">
          {recommendations.weekly_checklist.map((item, index) => (
            <li
              key={item}
              className="flex gap-3 rounded-lg bg-background/70 p-3 text-sm leading-6"
            >
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
                {index + 1}
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ol>
      </div>
    </SectionCard>
  );
}
