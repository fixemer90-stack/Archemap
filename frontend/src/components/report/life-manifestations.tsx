import { SectionCard } from "@/components/report/section-card";
import type { ReportViewModel } from "@/lib/report/view-model";

export function LifeManifestations({
  items,
}: {
  items: ReportViewModel["manifestations"];
}) {
  return (
    <SectionCard
      title="Как это проявляется"
      description="Переводим карту в жизненные ситуации: мышление, эмоции, общение и работа."
    >
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <article key={item.title} className="rounded-lg border p-4">
            <h3 className="font-semibold">{item.title}</h3>
            <div className="mt-3 grid gap-3 text-sm leading-6">
              <p>
                <span className="font-medium">Как проявляется: </span>
                <span className="text-muted-foreground">
                  {item.manifestation}
                </span>
              </p>
              <p className="rounded-md bg-primary/5 p-3">
                <span className="font-medium">Что помогает: </span>
                {item.support}
              </p>
              {item.risk && (
                <p className="rounded-md bg-muted p-3">
                  <span className="font-medium">Риск: </span>
                  {item.risk}
                </p>
              )}
            </div>
          </article>
        ))}
      </div>
    </SectionCard>
  );
}
