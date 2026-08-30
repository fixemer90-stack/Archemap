"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api-client";
import {
  fetchAstrotypeV2GenerationStatus,
  fetchAstrotypeV2Report,
  generateAstrotypeV2Report,
  type AstrotypeV2GenerationStatusResponse,
  type AstrotypeV2ProgressResponse,
  type AstrotypeV2ReportResponse,
} from "@/lib/api/astrotype-v2";

const POLL_INTERVAL_MS = 5_000;
const MAX_POLL_ATTEMPTS = 120;
const TERMINAL_GENERATION_STATUSES = new Set([
  "complete",
  "partial",
  "narrative_failed",
  "failed",
  "already_exists",
]);
const VISIBLE_REPORT_STATUSES = new Set([
  "deterministic_ready",
  "narrative_generating",
  "partial",
  "complete",
  "ready",
  "narrative_failed",
]);

export type V2ReportGenerationState =
  | "idle"
  | "loading"
  | "queued"
  | "polling"
  | "ready"
  | "failed"
  | "regenerating";

export interface UseV2ReportGenerationResult {
  state: V2ReportGenerationState;
  generationId: string | null;
  reportId: string | null;
  report: AstrotypeV2ReportResponse | null;
  generationStatus: AstrotypeV2GenerationStatusResponse | null;
  progress: AstrotypeV2ProgressResponse | null;
  message: string;
  error: string | null;
  isRegenerating: boolean;
  canRetry: boolean;
  start: () => void;
  regenerate: () => void;
  retry: () => void;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Не удалось загрузить отчёт";
}

function isTerminalGenerationStatus(status: string): boolean {
  return TERMINAL_GENERATION_STATUSES.has(status);
}

function isVisibleReportStatus(status: string): boolean {
  return VISIBLE_REPORT_STATUSES.has(status);
}

export function useV2ReportGeneration(
  profileId: string,
): UseV2ReportGenerationResult {
  const [state, setState] = useState<V2ReportGenerationState>("idle");
  const [generationId, setGenerationId] = useState<string | null>(null);
  const [reportId, setReportId] = useState<string | null>(null);
  const [report, setReport] = useState<AstrotypeV2ReportResponse | null>(null);
  const [generationStatus, setGenerationStatus] =
    useState<AstrotypeV2GenerationStatusResponse | null>(null);
  const [progress, setProgress] = useState<AstrotypeV2ProgressResponse | null>(
    null,
  );
  const [message, setMessage] = useState("Готовим натальный отчёт...");
  const [error, setError] = useState<string | null>(null);
  const pollTimerRef = useRef<number | null>(null);
  const pollAttemptsRef = useRef(0);
  const inFlightRef = useRef(false);
  const scheduleGenerationPollRef = useRef<((id: string) => void) | null>(null);

  const clearPollTimer = useCallback(() => {
    if (pollTimerRef.current) {
      window.clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  const fail = useCallback(
    (err: unknown) => {
      clearPollTimer();
      setState("failed");
      setError(getErrorMessage(err));
      inFlightRef.current = false;
    },
    [clearPollTimer],
  );

  const loadReport = useCallback(async (id: string) => {
    const data = await fetchAstrotypeV2Report(id);
    const reportStatus = data.report.status;
    setReport(data);
    setProgress(data.progress);
    setReportId(data.report.id);

    if (reportStatus === "complete" || reportStatus === "partial") {
      setState("ready");
      setMessage("Отчёт готов.");
      inFlightRef.current = false;
      return true;
    }

    if (isVisibleReportStatus(reportStatus)) {
      setState("polling");
      setMessage(
        `Отчёт уже доступен, нарратив ещё обновляется: ${reportStatus}`,
      );
      return false;
    }

    setState("queued");
    setMessage(`Отчёт в работе: ${reportStatus}`);
    return false;
  }, []);

  const pollGenerationStatus = useCallback(
    async (id: string) => {
      const status = await fetchAstrotypeV2GenerationStatus(id);
      setGenerationStatus(status);
      setGenerationId(status.generation_id);
      setMessage(`Статус генерации: ${status.status}`);

      let reportIsTerminal = false;
      if (status.report_id) {
        reportIsTerminal = await loadReport(status.report_id);
      }

      if (reportIsTerminal || isTerminalGenerationStatus(status.status)) {
        if (!status.report_id && status.status !== "already_exists") {
          throw new Error(`Генерация завершилась без отчёта: ${status.status}`);
        }
        inFlightRef.current = false;
        return;
      }
    },
    [loadReport],
  );

  const scheduleGenerationPoll = useCallback(
    (id: string) => {
      clearPollTimer();
      if (pollAttemptsRef.current >= MAX_POLL_ATTEMPTS) {
        fail(new Error("Отчёт слишком долго остаётся в очереди"));
        return;
      }
      pollAttemptsRef.current += 1;
      setState("polling");
      pollTimerRef.current = window.setTimeout(async () => {
        pollTimerRef.current = null;
        try {
          await pollGenerationStatus(id);
          if (inFlightRef.current) {
            scheduleGenerationPollRef.current?.(id);
          }
        } catch (err) {
          fail(err);
        }
      }, POLL_INTERVAL_MS);
    },
    [clearPollTimer, fail, pollGenerationStatus],
  );

  useEffect(() => {
    scheduleGenerationPollRef.current = scheduleGenerationPoll;
  }, [scheduleGenerationPoll]);

  const requestGeneration = useCallback(
    async (force: boolean) => {
      if (inFlightRef.current) {
        return;
      }
      inFlightRef.current = true;
      pollAttemptsRef.current = 0;
      clearPollTimer();
      setState(force ? "regenerating" : "loading");
      setError(null);
      setMessage(force ? "Перегенерируем отчёт..." : "Запрашиваем отчёт...");
      try {
        const generation = await generateAstrotypeV2Report(profileId, force);
        if (generation.generation_id) {
          setGenerationId(generation.generation_id);
        }
        if (generation.report_id) {
          const ready = await loadReport(generation.report_id);
          if (generation.generation_id && !ready) {
            scheduleGenerationPoll(generation.generation_id);
          }
          return;
        }
        if (generation.generation_id) {
          setState("queued");
          setMessage("Отчёт поставлен в очередь. Проверяем готовность...");
          await pollGenerationStatus(generation.generation_id);
          if (inFlightRef.current) {
            scheduleGenerationPoll(generation.generation_id);
          }
          return;
        }
        if (generation.links?.report) {
          const id = generation.links.report.split("/").filter(Boolean).at(-1);
          if (id) {
            const ready = await loadReport(id);
            if (!ready) {
              setState("polling");
            }
          }
          inFlightRef.current = false;
          return;
        }
        throw new Error("Сервер не вернул generation_id или report_id");
      } catch (err) {
        fail(err);
      }
    },
    [
      clearPollTimer,
      fail,
      loadReport,
      pollGenerationStatus,
      profileId,
      scheduleGenerationPoll,
    ],
  );

  const start = useCallback(() => {
    void requestGeneration(false);
  }, [requestGeneration]);

  const regenerate = useCallback(() => {
    void requestGeneration(true);
  }, [requestGeneration]);

  const retry = useCallback(() => {
    void requestGeneration(state === "ready");
  }, [requestGeneration, state]);

  useEffect(() => {
    void Promise.resolve().then(start);
    return clearPollTimer;
  }, [clearPollTimer, start]);

  useEffect(() => {
    if (
      (state === "queued" || state === "polling") &&
      generationId &&
      inFlightRef.current &&
      pollTimerRef.current === null
    ) {
      scheduleGenerationPoll(generationId);
    }
    return undefined;
  }, [generationId, scheduleGenerationPoll, state]);

  return {
    state,
    generationId,
    reportId,
    report,
    generationStatus,
    progress,
    message,
    error,
    isRegenerating: state === "regenerating",
    canRetry: state === "failed" || state === "queued" || state === "polling",
    start,
    regenerate,
    retry,
  };
}
