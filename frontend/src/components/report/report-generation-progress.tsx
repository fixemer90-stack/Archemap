import { Clock3, RefreshCw, Sparkles, TimerReset } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ReportGenerationProgressProps {
  timedOut: boolean;
  elapsedSeconds: number;
  onRefresh: () => void;
  onShowFallback: () => void;
}

export function ReportGenerationProgress({
  timedOut,
  elapsedSeconds,
  onRefresh,
  onShowFallback,
}: ReportGenerationProgressProps) {
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
              ? "Астрологическая и типологическая база уже рассчитана. Можно обновить статус или открыть технический отчёт, не теряя данные."
              : "Сначала готовим мягкое повествовательное чтение, а технические детали откроем ниже только при необходимости."}
          </p>
        </div>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="rounded-2xl border border-[#D8B45A]/20 bg-[#F6F1E8]/5 p-4 text-sm text-[#F6F1E8]">
          <div className="mb-3 flex items-center gap-2 text-[#D8B45A]">
            <Clock3 className="h-4 w-4" />
            <span>Прошло около {elapsedSeconds} сек.</span>
          </div>
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
            <Button onClick={onShowFallback} variant="outline">
              Показать технический отчёт
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
