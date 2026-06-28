import { EvidenceNotes } from "@/components/report/evidence-notes";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type {
  ContradictionInsightViewModel,
  FailureModeViewModel,
  MaturityLevelsViewModel,
} from "@/lib/report/view-model";

interface PatternTensionsSectionProps {
  contradictions: ContradictionInsightViewModel[];
  failureModes: FailureModeViewModel[];
  maturityLevels: MaturityLevelsViewModel | null;
}

export function PatternTensionsSection({
  contradictions,
  failureModes,
  maturityLevels,
}: PatternTensionsSectionProps) {
  if (
    contradictions.length === 0 &&
    failureModes.length === 0 &&
    !maturityLevels
  ) {
    return null;
  }

  return (
    <div className="grid grid-cols-1 gap-6">
      {contradictions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Главные внутренние противоречия</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm leading-6 text-muted-foreground">
            {contradictions.map((contradiction) => (
              <article key={contradiction.id} className="rounded-lg border p-4">
                <h3 className="font-medium text-foreground">
                  {contradiction.title}
                </h3>
                <dl className="mt-3 grid gap-2">
                  <div>
                    <dt className="font-medium text-foreground">Напряжение</dt>
                    <dd>{contradiction.tension}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-foreground">
                      Как это проявляется
                    </dt>
                    <dd>{contradiction.manifestation}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-foreground">
                      Зрелая интеграция
                    </dt>
                    <dd>{contradiction.mature_expression}</dd>
                  </div>
                </dl>
                <EvidenceNotes
                  className="mt-3"
                  notes={contradiction.evidence_notes}
                  fallbackFactIds={contradiction.evidence_ids}
                />
              </article>
            ))}
          </CardContent>
        </Card>
      )}

      {failureModes.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Где система даёт сбой</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm leading-6 text-muted-foreground">
            {failureModes.map((failureMode) => (
              <article key={failureMode.id} className="rounded-lg border p-4">
                <h3 className="font-medium text-foreground">
                  {failureMode.title}
                </h3>
                <dl className="mt-3 grid gap-2">
                  <div>
                    <dt className="font-medium text-foreground">Триггер</dt>
                    <dd>{failureMode.trigger}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-foreground">
                      Как выглядит сбой
                    </dt>
                    <dd>{failureMode.manifestation}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-foreground">
                      Поддерживающая рамка
                    </dt>
                    <dd>{failureMode.supportive_reframe}</dd>
                  </div>
                </dl>
                <EvidenceNotes
                  className="mt-3"
                  notes={failureMode.evidence_notes}
                  fallbackFactIds={failureMode.evidence_ids}
                />
              </article>
            ))}
          </CardContent>
        </Card>
      )}

      {maturityLevels && (
        <Card>
          <CardHeader>
            <CardTitle>Уровни зрелости паттерна</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 text-sm leading-6 text-muted-foreground">
            {(
              [
                ["low", maturityLevels.low],
                ["medium", maturityLevels.medium],
                ["high", maturityLevels.high],
              ] as const
            ).map(([bandName, band]) => (
              <article key={bandName} className="rounded-lg border p-4">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  {bandName}
                </p>
                <h3 className="mt-1 font-medium text-foreground">
                  {band.title}
                </h3>
                <p className="mt-2">{band.body}</p>
                <EvidenceNotes
                  className="mt-3"
                  notes={band.evidence_notes}
                  fallbackFactIds={band.evidence_ids}
                />
              </article>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
