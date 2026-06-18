"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { ArchetypeProfileSummary } from "@/components/report/archetype-profile-summary";
import { AstrologyOverview } from "@/components/report/astrology-overview";
import { DeterministicReportFallback } from "@/components/report/deterministic-report-fallback";
import { LifeManifestations } from "@/components/report/life-manifestations";
import { PracticalRecommendations } from "@/components/report/practical-recommendations";
import { ReportExecutiveSummary } from "@/components/report/report-executive-summary";
import { ReportGenerationProgress } from "@/components/report/report-generation-progress";
import { ReportHeader } from "@/components/report/report-header";
import { ReportNarrativePage } from "@/components/report/report-narrative-page";
import { ReportPdfActions } from "@/components/report/report-pdf-actions";
import { SocionicsProfileSimple } from "@/components/report/socionics-profile-simple";
import { TechnicalDetailsAccordion } from "@/components/report/technical-details-accordion";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { apiFetch, ApiError } from "@/lib/api-client";
import {
  fetchReportApiData,
  fetchReportById,
  generateReportForProfile,
  regenerateReportNarrative,
  type GeneratedReportApiResponse,
} from "@/lib/api/report";
import {
  toReportViewModel,
  type ReportApiData,
  type ReportViewModel as ReportData,
} from "@/lib/report/view-model";
import { useAuthStore } from "@/stores/auth-store";

const NARRATIVE_TIMEOUT_MS = 90_000;
const POLL_INTERVAL_MS = 5_000;

function ReportSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-40 rounded-lg bg-muted" />
      <div className="h-48 rounded-lg bg-muted" />
      <div className="h-64 rounded-lg bg-muted" />
    </div>
  );
}

function ReportContent({
  data,
  isDownloadingPdf,
  onDownloadPdf,
  profileId,
}: {
  data: ReportData;
  isDownloadingPdf: boolean;
  onDownloadPdf: () => void | Promise<void>;
  profileId: string;
}) {
  if (data.product === "self" && data.narrative) {
    return (
      <ReportNarrativePage
        data={data}
        isDownloadingPdf={isDownloadingPdf}
        onDownloadPdf={onDownloadPdf}
        profileId={profileId}
      />
    );
  }

  if (data.product === "career" && data.generated_report) {
    return <CareerReportContent data={data} />;
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <ReportHeader profile={data.profile} />
      <ReportExecutiveSummary summary={data.summary} />
      <AstrologyOverview astrology={data.astrology} />
      <LifeManifestations items={data.manifestations} />
      <PracticalRecommendations recommendations={data.recommendations} />
      <ArchetypeProfileSummary archetype={data.archetype} />
      <SocionicsProfileSimple data={data.socionics_summary} />
      {data.product === "self" && (
        <ReportPdfActions
          isDownloading={isDownloadingPdf}
          onDownload={onDownloadPdf}
        />
      )}
      <TechnicalDetailsAccordion data={data} />
    </div>
  );
}

function CareerReportContent({ data }: { data: ReportData }) {
  const report = data.generated_report;
  if (!report) {
    return null;
  }

  const scores = Object.entries(report.all_archetype_scores)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Card className="border-[#C28A2E]/30 bg-[#C28A2E]/5">
        <CardHeader>
          <CardDescription>
            Career-report · профессиональный профиль
          </CardDescription>
          <CardTitle className="text-3xl">{data.profile.name}</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Дата рождения</dt>
              <dd className="font-medium">{data.profile.birth_date}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Время</dt>
              <dd className="font-medium">
                {data.profile.birth_time || "Не указано"} ·{" "}
                {data.profile.quality_label}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Место</dt>
              <dd className="font-medium">{data.profile.birth_place}</dd>
            </div>
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardDescription>Главный карьерный архетип</CardDescription>
          <CardTitle>{report.archetype}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm leading-6 text-muted-foreground">
          <p>
            Показатель: {report.score.toFixed(2)} · Уверенность:{" "}
            {report.confidence_label}
          </p>
          {report.quality_warning && (
            <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
              {report.quality_warning}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Карьерные выводы</CardTitle>
          <CardDescription>
            Утверждения из rules/career, а не обычный Self-report.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {report.claims.map((claim) => (
            <article key={claim.claim_id} className="rounded-lg border p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <span>{claim.section}</span>
                <span>·</span>
                <span>{claim.archetype}</span>
                <span>·</span>
                <span>score {claim.score.toFixed(2)}</span>
                <span>·</span>
                <span>{claim.confidence.label}</span>
              </div>
              <p className="text-sm leading-6">{claim.message}</p>
            </article>
          ))}
        </CardContent>
      </Card>

      {scores.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Рейтинг карьерных архетипов</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {scores.map(([name, score]) => (
              <div key={name} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>{name}</span>
                  <span className="text-muted-foreground">
                    {score.toFixed(2)}
                  </span>
                </div>
                <div className="h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-[#C28A2E]"
                    style={{
                      width: `${Math.max(4, Math.min(100, score * 100))}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <TechnicalDetailsAccordion data={data} />
    </div>
  );
}

function ReportError({ message }: { message: string }) {
  return (
    <Card className="border-destructive/30">
      <CardHeader>
        <CardTitle>Не удалось загрузить отчёт</CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
    </Card>
  );
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Сессия истекла. Войдите снова.";
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неизвестная ошибка загрузки";
}

async function downloadReportPdf(
  reportId: string,
  token?: string,
): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await apiFetch(`/api/v1/reports/${reportId}/pdf`, {
    method: "GET",
    headers,
    token,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = (await response.json()) as { detail?: string };
      detail = data.detail || detail;
    } catch {
      // Keep non-JSON error message as status text.
    }
    throw new ApiError(response.status, detail);
  }

  const blob = await response.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = `report-${reportId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(objectUrl);
}

export default function ReportPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const profileId = params.profileId as string;
  const product = searchParams.get("product") ?? "self";
  const token = useAuthStore((state) => state.token);
  const [apiData, setApiData] = useState<ReportApiData | null>(null);
  const [data, setData] = useState<ReportData | null>(null);
  const [currentReport, setCurrentReport] =
    useState<GeneratedReportApiResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isTimedOut, setIsTimedOut] = useState(false);
  const [showFallback, setShowFallback] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);
  const generationStartedAtRef = useRef<number | null>(null);
  const autoGenerateAttemptedRef = useRef<Set<string>>(new Set());
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  const clearSelfReportAutoGenerateThrottle = useCallback(
    (profileIdToClear: string, productToClear: string) => {
      if (productToClear !== "self") {
        return;
      }
      window.sessionStorage.removeItem(
        `self-report-autogen:${profileIdToClear}:${productToClear}`,
      );
    },
    [],
  );

  const applyReportUpdate = useCallback(
    (
      baseData: ReportApiData,
      report: GeneratedReportApiResponse | undefined,
    ) => {
      if (report) {
        clearSelfReportAutoGenerateThrottle(report.profile_id, report.product);
      }
      const nextApiData = { ...baseData, generatedReport: report };
      setApiData(nextApiData);
      setCurrentReport(report ?? null);
      setData(toReportViewModel(nextApiData));
    },
    [clearSelfReportAutoGenerateThrottle],
  );

  async function refreshCurrentReport() {
    if (!apiData || !currentReport) {
      return;
    }
    const report = await fetchReportById(currentReport.id, token || undefined);
    applyReportUpdate(apiData, report);
  }

  async function retryNarrativeGeneration() {
    if (!apiData || !currentReport) {
      return;
    }
    try {
      setIsRetrying(true);
      setError(null);
      const report = await regenerateReportNarrative(
        currentReport.id,
        token || undefined,
      );
      setShowFallback(false);
      setIsTimedOut(false);
      generationStartedAtRef.current = Date.now();
      setElapsedSeconds(0);
      applyReportUpdate(apiData, report);
    } catch (retryError) {
      setError(getErrorMessage(retryError));
    } finally {
      setIsRetrying(false);
    }
  }

  useEffect(() => {
    let isMounted = true;

    async function loadReport() {
      try {
        setIsLoading(true);
        setError(null);
        setIsTimedOut(false);
        setShowFallback(false);
        generationStartedAtRef.current = null;
        setElapsedSeconds(0);
        const loadedApiData = await fetchReportApiData(
          profileId,
          token || undefined,
          product,
        );
        const autoGenerateKey = `${profileId}:${product}`;
        const autoGenerateStorageKey = `self-report-autogen:${autoGenerateKey}`;
        const autoGenerateRequestedAt = Number.parseInt(
          window.sessionStorage.getItem(autoGenerateStorageKey) ?? "",
          10,
        );
        const autoGenerateRecentlyRequested = Number.isFinite(
          autoGenerateRequestedAt,
        )
          ? Date.now() - autoGenerateRequestedAt < 2 * 60 * 1000
          : false;
        const autoGenerateAlreadyRequested =
          autoGenerateAttemptedRef.current.has(autoGenerateKey) ||
          autoGenerateRecentlyRequested;
        if (
          product === "self" &&
          !loadedApiData.generatedReport &&
          !autoGenerateAlreadyRequested
        ) {
          autoGenerateAttemptedRef.current.add(autoGenerateKey);
          window.sessionStorage.setItem(
            autoGenerateStorageKey,
            String(Date.now()),
          );
          try {
            const generatedReport = await generateReportForProfile(
              profileId,
              token || undefined,
              "self",
            );
            loadedApiData.generatedReport = generatedReport;
          } catch (generateError) {
            autoGenerateAttemptedRef.current.delete(autoGenerateKey);
            window.sessionStorage.removeItem(autoGenerateStorageKey);
            throw generateError;
          }
        }
        if (product !== "self" && !loadedApiData.generatedReport) {
          throw new Error(
            "Карьерный отчёт для этого профиля ещё не найден. " +
              "Вернитесь в раздел Career и нажмите «Построить отчёт».",
          );
        }
        if (isMounted) {
          setApiData(loadedApiData);
          setCurrentReport(loadedApiData.generatedReport ?? null);
          setData(toReportViewModel(loadedApiData));
          if (loadedApiData.generatedReport) {
            clearSelfReportAutoGenerateThrottle(
              loadedApiData.generatedReport.profile_id,
              loadedApiData.generatedReport.product,
            );
          }
          if (
            loadedApiData.generatedReport?.status === "generating_narrative"
          ) {
            generationStartedAtRef.current = Date.now();
          }
        }
      } catch (loadError) {
        if (isMounted) {
          setError(getErrorMessage(loadError));
          setApiData(null);
          setCurrentReport(null);
          setData(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    if (profileId) {
      loadReport();
    }

    return () => {
      isMounted = false;
    };
  }, [
    applyReportUpdate,
    clearSelfReportAutoGenerateThrottle,
    profileId,
    product,
    token,
  ]);

  useEffect(() => {
    if (currentReport?.status !== "generating_narrative" || !apiData) {
      return;
    }

    const startedAt = generationStartedAtRef.current ?? Date.now();
    generationStartedAtRef.current = startedAt;

    const updateElapsed = () => {
      const elapsed = Date.now() - startedAt;
      setElapsedSeconds(Math.floor(elapsed / 1000));
      if (elapsed >= NARRATIVE_TIMEOUT_MS) {
        setIsTimedOut(true);
      }
    };

    updateElapsed();
    const timerId = window.setInterval(updateElapsed, 1_000);
    const pollId = window.setInterval(() => {
      fetchReportById(currentReport.id, token || undefined)
        .then((report) => {
          applyReportUpdate(apiData, report);
          if (report.status !== "generating_narrative") {
            generationStartedAtRef.current = null;
            setIsTimedOut(false);
          }
        })
        .catch((pollError: unknown) => {
          if (pollError instanceof ApiError && pollError.status === 401) {
            setApiData(null);
            setCurrentReport(null);
            setData(null);
            generationStartedAtRef.current = null;
            setShowFallback(false);
            setIsTimedOut(false);
          }
          setError(getErrorMessage(pollError));
        });
    }, POLL_INTERVAL_MS);
    const timeoutId = window.setTimeout(() => {
      setIsTimedOut(true);
    }, NARRATIVE_TIMEOUT_MS);

    return () => {
      window.clearInterval(timerId);
      window.clearInterval(pollId);
      window.clearTimeout(timeoutId);
    };
  }, [apiData, applyReportUpdate, currentReport, token]);

  const reportStatus = currentReport?.status;
  const shouldShowProgress =
    reportStatus === "generating_narrative" && !showFallback;
  const shouldShowFallback = Boolean(
    data &&
    currentReport &&
    (showFallback ||
      reportStatus === "narrative_failed" ||
      reportStatus === "deterministic_ready"),
  );

  async function handleDownloadPdf() {
    if (!currentReport) {
      return;
    }
    try {
      setIsDownloadingPdf(true);
      setError(null);
      await downloadReportPdf(currentReport.id, token || undefined);
    } catch (downloadError) {
      setError(getErrorMessage(downloadError));
    } finally {
      setIsDownloadingPdf(false);
    }
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {!isLoading && data && currentReport && data.product === "career" && (
        <div className="mb-6 flex items-center justify-between gap-4 rounded-lg border bg-card p-4">
          <div>
            <div className="text-sm font-medium">{data.profile.name}</div>
            <div className="text-xs text-muted-foreground">
              PDF собирается на лету из JSON в базе
            </div>
          </div>
          <Button onClick={handleDownloadPdf} disabled={isDownloadingPdf}>
            {isDownloadingPdf ? "Собираем PDF..." : "Скачать PDF"}
          </Button>
        </div>
      )}
      {isLoading && <ReportSkeleton />}
      {!isLoading && error && !data && <ReportError message={error} />}
      {!isLoading && !error && shouldShowProgress && (
        <ReportGenerationProgress
          elapsedSeconds={elapsedSeconds}
          onRefresh={refreshCurrentReport}
          onShowFallback={() => setShowFallback(true)}
          timedOut={isTimedOut}
        />
      )}
      {!isLoading && shouldShowFallback && data && currentReport && (
        <DeterministicReportFallback
          errorMessage={currentReport.error_message ?? error}
          isRetrying={isRetrying}
          onRetry={retryNarrativeGeneration}
          reason={
            reportStatus === "narrative_failed"
              ? "failed"
              : reportStatus === "deterministic_ready"
                ? "deterministic_ready"
                : "timeout"
          }
        >
          <ReportContent
            data={data}
            isDownloadingPdf={isDownloadingPdf}
            onDownloadPdf={handleDownloadPdf}
            profileId={profileId}
          />
        </DeterministicReportFallback>
      )}
      {!isLoading &&
        !error &&
        data &&
        !shouldShowProgress &&
        !shouldShowFallback && (
          <ReportContent
            data={data}
            isDownloadingPdf={isDownloadingPdf}
            onDownloadPdf={handleDownloadPdf}
            profileId={profileId}
          />
        )}
    </div>
  );
}
