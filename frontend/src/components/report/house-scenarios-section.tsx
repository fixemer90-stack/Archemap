import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { HouseScenarioViewModel } from "@/lib/report/view-model";

interface HouseScenariosSectionProps {
  scenarios: HouseScenarioViewModel[];
}

export function HouseScenariosSection({
  scenarios,
}: HouseScenariosSectionProps) {
  if (scenarios.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Жизненные сценарии домов</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 text-sm leading-6 text-muted-foreground">
        {scenarios.map((scenario) => (
          <article key={scenario.id} className="rounded-lg border p-4">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              {scenario.placement}
            </p>
            <h3 className="mt-1 font-medium text-foreground">
              {scenario.title}
            </h3>
            <dl className="mt-3 grid gap-2">
              <div>
                <dt className="font-medium text-foreground">Потребность</dt>
                <dd>{scenario.need}</dd>
              </div>
              <div>
                <dt className="font-medium text-foreground">
                  Как это видно в жизни
                </dt>
                <dd>{scenario.manifestation}</dd>
              </div>
              <div>
                <dt className="font-medium text-foreground">Тень / риск</dt>
                <dd>{scenario.shadow}</dd>
              </div>
              <div>
                <dt className="font-medium text-foreground">Зрелая форма</dt>
                <dd>{scenario.mature_expression}</dd>
              </div>
            </dl>
            <p className="mt-3 text-xs text-muted-foreground">
              Основания: {scenario.evidence_ids.join(", ")}
            </p>
          </article>
        ))}
      </CardContent>
    </Card>
  );
}
