"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { RefreshCw } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import {
  fetchAstrotypeV2Report,
  generateAstrotypeV2Report,
  type AstrotypeV2ReportResponse,
} from "@/lib/api/astrotype-v2";

const POLL_INTERVAL_MS = 5_000;

type LoadState = "loading" | "queued" | "ready" | "error";

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Не удалось загрузить отчёт";
}

function extractTitle(report: AstrotypeV2ReportResponse): string {
  const assembled = report.report.assembled_payload;
  if (assembled && typeof assembled.title === "string") {
    return assembled.title;
  }
  return "Astrotype V2 natal report";
}

function extractSections(report: AstrotypeV2ReportResponse) {
  const narrative = report.report.narrative_payload;
  const sections = narrative?.sections;
  return Array.isArray(sections) ? sections : [];
}

function textFromValue(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.filter((item) => typeof item === "string").join("\n\n");
  }
  return "";
}

function ReportReady({
  report,
  onRegenerate,
  isRegenerating,
}: {
  report: AstrotypeV2ReportResponse;
  onRegenerate: () => void;
  isRegenerating: boolean;
}) {
  const sections = extractSections(report);
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Card className="border-[#D8B45A]/30 bg-[#D8B45A]/5">
        <CardHeader>
          <CardDescription>Astrotype V2 · natal-only</CardDescription>
          <CardTitle className="text-3xl">{extractTitle(report)}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-6 text-[#D8DCE8]">
          <p>Статус: {report.progress.status}</p>
          <p>
            Сегменты: {report.progress.ready_segments}/
            {report.progress.total_segments || report.segments.length}
          </p>
          <Button onClick={onRegenerate} disabled={isRegenerating}>
            <RefreshCw className="h-4 w-4" />
            {isRegenerating ? "Перегенерируем..." : "Перегенерировать V2 отчёт"}
          </Button>
        </CardContent>
      </Card>

      {sections.length > 0 ? (
        sections.map((section, index) => {
          if (!section || typeof section !== "object") {
            return null;
          }
          const item = section as Record<string, unknown>;
          const title = textFromValue(item.title) || `Раздел ${index + 1}`;
          const body =
            textFromValue(item.body) ||
            textFromValue(item.content) ||
            textFromValue(item.paragraphs);
          return (
            <Card key={`${title}-${index}`}>
              <CardHeader>
                <CardTitle>{title}</CardTitle>
              </CardHeader>
              {body && (
                <CardContent className="whitespace-pre-line text-sm leading-7 text-[#D8DCE8]">
                  {body}
                </CardContent>
              )}
            </Card>
          );
        })
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Данные V2 готовы</CardTitle>
            <CardDescription>
              Полная сборка отчёта сохранена в API. Интерфейс V2 подключён к
              новому natal-only runtime и не использует legacy Self-report.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </div>
  );
}

export default function AstrotypeV2ReportPage() {
  const params = useParams();
  const profileId = params.profileId as string;
  const [state, setState] = useState<LoadState>("loading");
  const [reportId, setReportId] = useState<string | null>(null);
  const [report, setReport] = useState<AstrotypeV2ReportResponse | null>(null);
  const [message, setMessage] = useState("Готовим V2 natal-only отчёт...");
  const [error, setError] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const pollTimerRef = useRef<number | null>(null);

  const clearPollTimer = useCallback(() => {
    if (pollTimerRef.current) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const loadReport = useCallback(async (id: string) => {
    const data = await fetchAstrotypeV2Report(id);
    setReport(data);
    setReportId(data.report.id);
    if (data.progress.status === "ready") {
      setState("ready");
      setMessage("V2 отчёт готов.");
      return true;
    }
    setState("queued");
    setMessage(`V2 отчёт в работе: ${data.progress.status}`);
    return false;
  }, []);

  const schedulePoll = useCallback(
    (id: string) => {
      clearPollTimer();
      pollTimerRef.current = window.setTimeout(async () => {
        try {
          await loadReport(id);
        } catch (err) {
          setState("error");
          setError(getErrorMessage(err));
        }
      }, POLL_INTERVAL_MS);
    },
    [clearPollTimer, loadReport],
  );

  const start = useCallback(
    async (force = false) => {
      setIsRegenerating(force);
      setState("loading");
      setError(null);
      setMessage("Запрашиваем V2 отчёт...");
      clearPollTimer();
      try {
        const generation = await generateAstrotypeV2Report(profileId, force);
        if (generation.report_id) {
          const ready = await loadReport(generation.report_id);
          if (!ready) {
            schedulePoll(generation.report_id);
          }
          setIsRegenerating(false);
          return;
        }
        setState("queued");
        setMessage("V2 отчёт поставлен в очередь. Проверяем готовность...");
        clearPollTimer();
        pollTimerRef.current = window.setTimeout(async () => {
          try {
            const retryGeneration = await generateAstrotypeV2Report(
              profileId,
              false,
            );
            if (retryGeneration.report_id) {
              const ready = await loadReport(retryGeneration.report_id);
              if (!ready) {
                schedulePoll(retryGeneration.report_id);
              }
            }
          } catch (retryError) {
            setState("error");
            setError(getErrorMessage(retryError));
            setIsRegenerating(false);
          }
        }, POLL_INTERVAL_MS);
      } catch (err) {
        setState("error");
        setError(getErrorMessage(err));
        setIsRegenerating(false);
      }
    },
    [clearPollTimer, loadReport, profileId, schedulePoll],
  );

  useEffect(() => {
    void Promise.resolve().then(() => start(false));
    return clearPollTimer;
  }, [clearPollTimer, start]);

  useEffect(() => {
    if (state === "queued" && reportId) {
      schedulePoll(reportId);
    }
    return clearPollTimer;
  }, [clearPollTimer, reportId, schedulePoll, state]);

  const canRetry = useMemo(
    () => state === "error" || state === "queued",
    [state],
  );

  if (state === "ready" && report) {
    return (
      <ReportReady
        report={report}
        onRegenerate={() => void start(true)}
        isRegenerating={isRegenerating}
      />
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Card>
        <CardHeader>
          <CardDescription>Astrotype V2 · natal-only</CardDescription>
          <CardTitle>Ваш V2 отчёт</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm leading-6 text-[#D8DCE8]">
          <p>{error || message}</p>
          {reportId && (
            <p className="text-xs text-muted-foreground">
              report_id: {reportId}
            </p>
          )}
          {canRetry && (
            <Button onClick={() => start(true)}>
              <RefreshCw className="h-4 w-4" />
              Перегенерировать V2 отчёт
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
