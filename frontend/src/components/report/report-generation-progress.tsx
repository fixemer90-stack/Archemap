import { Clock3, RefreshCw, Sparkles, TimerReset } from "lucide-react";
import type {
  NarrativeStageArtifactApiResponse,
  NarrativeStageProgressApiResponse,
} from "@/lib/api/report";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ReportGenerationProgressProps {
  timedOut: boolean;
  elapsedSeconds: number;
  stageProgress?: NarrativeStageProgressApiResponse | null;
  stageArtifacts?: NarrativeStageArtifactApiResponse[];
  onRefresh: () => void;
  onRetry: () => void;
}

function stageLabel(
  stageId: NarrativeStageProgressApiResponse["running_stage"],
): string | null {
  switch (stageId) {
    case "plan":
      return "План структуры";
    case "identity":
      return "Главная формула личности";
    case "emotional":
      return "Эмоции и коммуникация";
    case "relationships":
      return "Отношения и близость";
    case "development":
      return "Развитие и зрелость";
    case "house_scenarios":
      return "Жизненные сценарии домов";
    case "assembly":
      return "Финальная сборка";
    default:
      return null;
  }
}

function runningStageStatus(
  stageId: NarrativeStageProgressApiResponse["running_stage"],
): string | null {
  const label = stageLabel(stageId);
  return label ? `Сейчас собираем: ${label.toLowerCase()}` : null;
}

export function ReportGenerationProgress({
  timedOut,
  elapsedSeconds,
  stageProgress,
  stageArtifacts = [],
  onRefresh,
  onRetry,
}: ReportGenerationProgressProps) {
  const runningStageLabel = runningStageStatus(
    stageProgress?.current_stage ?? stageProgress?.running_stage ?? null,
  );
  const failedStageLabel =
    stageLabel(stageProgress?.failed_stage ?? null) ??
    stageLabel(
      stageArtifacts.find((artifact) => artifact.status === "failed")?.stage_id ??
        stageProgress?.stages?.find((artifact) => artifact.status === "failed")
          ?.stage_id ??
        null,
    );
  const completedStageLabels = Array.from(
    new Set(
      [...stageArtifacts, ...(stageProgress?.stages ?? [])]
        .filter((artifact) => artifact.status === "ready")
        .map((artifact) => stageLabel(artifact.stage_id))
        .filter((label): label is string => Boolean(label)),
    ),
  );
  return (
    <Card className="mx-auto max-w-3xl border-[#5B3FD6]/30 bg-[rgba(23,20,42,0.92)]">
      <CardHeader className="space-y-4 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#5B3FD6]/20 text-[#D8B45A]">
          {timedOut ? (
            <TimerReset className="h-7 w-7" />
          ) : (
            <Sparkles className="h-7 w-7 animate-pulse" />
          )}
        </div>
        <div className="space-y-2">
          <CardTitle className="font-[family-name:var(--font-cormorant)] text-3xl text-[#F6F1E8]">
            {timedOut
              ? "Текстовый отчёт ещё собирается"
              : "Собираем ваш текстовый отчёт"}
          </CardTitle>
          <p className="text-sm leading-6 text-[#D8DCE8]">
            {timedOut
              ? "Полный текст пока не собрался. Можно обновить статус или повторить генерацию, но сокращённую техническую версию здесь не показываем."
              : "Сначала готовим полный повествовательный отчёт. Пока он не готов, промежуточную техническую подмену не показываем."}
          </p>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="rounded-2xl border border-[#D8B45A]/20 bg-[#F6F1E8]/5 p-4 text-sm text-[#F6F1E8]">
          <div className="mb-3 flex items-center gap-2 text-[#D8B45A]">
            <Clock3 className="h-4 w-4" />
            <span>Прошло около {elapsedSeconds} сек.</span>
          </div>
          {runningStageLabel && (
            <p className="mb-3 text-sm text-[#D8DCE8]">{runningStageLabel}.</p>
          )}
          {failedStageLabel && (
            <p className="mb-3 text-sm text-amber-200">
              Требует повтора: {failedStageLabel.toLowerCase()}.
            </p>
          )}
          {stageProgress && (
            <p className="mb-3 text-xs text-[#D8DCE8]">
              Готово этапов: {stageProgress.completed_stages}/{stageProgress.total_stages}
            </p>
          )}
          {completedStageLabels.length > 0 && (
            <div className="mb-3 space-y-2">
              <p className="text-xs uppercase tracking-wide text-[#D8B45A]">
                Уже готовы
              </p>
              <div className="flex flex-wrap gap-2">
                {completedStageLabels.map((label) => (
                  <span
                    key={label}
                    className="rounded-full border border-[#D8B45A]/25 bg-[#F6F1E8]/5 px-2 py-1 text-xs text-[#F6F1E8]"
                  >
                    {label}
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="h-2 overflow-hidden rounded-full bg-[#F6F1E8]/10">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#5B3FD6] via-[#8DA8FF] to-[#D8B45A] transition-all"
              style={{
                width: `${Math.min(100, Math.max(12, (elapsedSeconds / 90) * 100))}%`,
              }}
            />
          </div>
        </div>

        <div className="flex flex-col justify-center gap-3 sm:flex-row">
          <Button
            onClick={onRefresh}
            variant={timedOut ? "default" : "outline"}
          >
            <RefreshCw className="h-4 w-4" />
            Обновить
          </Button>
          {timedOut && (
            <Button onClick={onRetry} variant="outline">
              Повторить генерацию
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
