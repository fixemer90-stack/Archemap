"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api-client";
import {
  fetchAstrotypeV2Report,
  generateAstrotypeV2Report,
  type AstrotypeV2ProgressResponse,
  type AstrotypeV2ReportResponse,
} from "@/lib/api/astrotype-v2";

const POLL_INTERVAL_MS = 5_000;
const MAX_POLL_ATTEMPTS = 120;

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
  reportId: string | null;
  report: AstrotypeV2ReportResponse | null;
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

export function useV2ReportGeneration(
  profileId: string,
): UseV2ReportGenerationResult {
  const [state, setState] = useState<V2ReportGenerationState>("idle");
  const [reportId, setReportId] = useState<string | null>(null);
  const [report, setReport] = useState<AstrotypeV2ReportResponse | null>(null);
  const [progress, setProgress] = useState<AstrotypeV2ProgressResponse | null>(
    null,
  );
  const [message, setMessage] = useState("Готовим V2 natal-only отчёт...");
  const [error, setError] = useState<string | null>(null);
  const pollTimerRef = useRef<number | null>(null);
  const pollAttemptsRef = useRef(0);
  const inFlightRef = useRef(false);

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
    setReport(data);
    setProgress(data.progress);
    setReportId(data.report.id);
    if (data.progress.status === "ready") {
      setState("ready");
      setMessage("V2 отчёт готов.");
      inFlightRef.current = false;
      return true;
    }
    setState("queued");
    setMessage(`V2 отчёт в работе: ${data.progress.status}`);
    return false;
  }, []);

  const schedulePoll = useCallback(
    (id: string) => {
      clearPollTimer();
      if (pollAttemptsRef.current >= MAX_POLL_ATTEMPTS) {
        fail(new Error("V2 отчёт слишком долго остаётся в очереди"));
        return;
      }
      pollAttemptsRef.current += 1;
      setState("polling");
      pollTimerRef.current = window.setTimeout(async () => {
        pollTimerRef.current = null;
        try {
          await loadReport(id);
        } catch (err) {
          fail(err);
        }
      }, POLL_INTERVAL_MS);
    },
    [clearPollTimer, fail, loadReport],
  );

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
      setMessage(
        force ? "Перегенерируем V2 отчёт..." : "Запрашиваем V2 отчёт...",
      );
      try {
        const generation = await generateAstrotypeV2Report(profileId, force);
        if (generation.report_id) {
          const ready = await loadReport(generation.report_id);
          if (!ready) {
            schedulePoll(generation.report_id);
          }
          return;
        }
        setState("queued");
        setMessage("V2 отчёт поставлен в очередь. Проверяем готовность...");
        if (generation.links?.report) {
          const id = generation.links.report.split("/").filter(Boolean).at(-1);
          if (id) {
            setReportId(id);
            schedulePoll(id);
          }
        }
        inFlightRef.current = false;
      } catch (err) {
        fail(err);
      }
    },
    [clearPollTimer, fail, loadReport, profileId, schedulePoll],
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
      reportId &&
      pollTimerRef.current === null
    ) {
      void Promise.resolve().then(() => schedulePoll(reportId));
    }
    return undefined;
  }, [reportId, schedulePoll, state]);

  return {
    state,
    reportId,
    report,
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
