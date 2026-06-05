import { AlertTriangle, RefreshCw } from "lucide-react";
import { type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface DeterministicReportFallbackProps {
  reason: "timeout" | "failed" | "deterministic_ready";
  errorMessage?: string | null;
  isRetrying?: boolean;
  onRetry: () => void;
  children: ReactNode;
}

const REASON_COPY: Record<
  DeterministicReportFallbackProps["reason"],
  { title: string; description: string }
> = {
  timeout: {
    title: "Технический отчёт",
    description:
      "Текстовый LLM-отчёт ещё собирается. Ниже доступна deterministic-версия: карта, типология и правила уже рассчитаны.",
  },
  failed: {
    title: "LLM-текст пока недоступен",
    description:
      "Показываем технический отчёт без ожидания. Можно повторить генерацию narrative-слоя отдельно, без пересчёта карты.",
  },
  deterministic_ready: {
    title: "Технический отчёт",
    description:
      "Deterministic-отчёт готов, а narrative-слой ещё не перешёл в финальный статус. Можно читать техническую версию или повторить генерацию текста.",
  },
};

export function DeterministicReportFallback({
  reason,
  errorMessage,
  isRetrying = false,
  onRetry,
  children,
}: DeterministicReportFallbackProps) {
  const copy = REASON_COPY[reason];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Card className="border-[#D8B45A]/30 bg-[#D8B45A]/10">
        <CardHeader className="space-y-3">
          <div className="flex items-center gap-3 text-[#D8B45A]">
            <AlertTriangle className="h-5 w-5" />
            <CardTitle>{copy.title}</CardTitle>
          </div>
          <p className="text-sm leading-6 text-muted-foreground">
            {copy.description}
          </p>
          {errorMessage && (
            <p className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {errorMessage}
            </p>
          )}
        </CardHeader>
        <CardContent>
          <Button onClick={onRetry} disabled={isRetrying} variant="outline">
            <RefreshCw
              className={isRetrying ? "h-4 w-4 animate-spin" : "h-4 w-4"}
            />
            Повторить генерацию
          </Button>
        </CardContent>
      </Card>
      {children}
    </div>
  );
}
