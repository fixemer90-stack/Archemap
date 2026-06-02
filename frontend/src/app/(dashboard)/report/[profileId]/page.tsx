"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { ArchetypeProfileSummary } from "@/components/report/archetype-profile-summary";
import { AstrologyOverview } from "@/components/report/astrology-overview";
import { LifeManifestations } from "@/components/report/life-manifestations";
import { PracticalRecommendations } from "@/components/report/practical-recommendations";
import { ReportExecutiveSummary } from "@/components/report/report-executive-summary";
import { ReportHeader } from "@/components/report/report-header";
import { SocionicsProfileSimple } from "@/components/report/socionics-profile-simple";
import { TechnicalDetailsAccordion } from "@/components/report/technical-details-accordion";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError } from "@/lib/api-client";
import { fetchReportApiData } from "@/lib/api/report";
import {
  toReportViewModel,
  type ReportViewModel as ReportData,
} from "@/lib/report/view-model";
import { useAuthStore } from "@/stores/auth-store";

function ReportSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-40 rounded-lg bg-muted" />
      <div className="h-48 rounded-lg bg-muted" />
      <div className="h-64 rounded-lg bg-muted" />
    </div>
  );
}

function ReportContent({ data }: { data: ReportData }) {
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
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неизвестная ошибка загрузки";
}

export default function ReportPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const profileId = params.profileId as string;
  const product = searchParams.get("product") ?? "self";
  const token = useAuthStore((state) => state.token);
  const [data, setData] = useState<ReportData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadReport() {
      try {
        setIsLoading(true);
        setError(null);
        const apiData = await fetchReportApiData(
          profileId,
          token || undefined,
          product,
        );
        if (product !== "self" && !apiData.generatedReport) {
          throw new Error(
            "Карьерный отчёт для этого профиля ещё не найден. " +
              "Вернитесь в раздел Career и нажмите «Построить отчёт».",
          );
        }
        if (isMounted) {
          setData(toReportViewModel(apiData));
        }
      } catch (loadError) {
        if (isMounted) {
          setError(getErrorMessage(loadError));
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
  }, [profileId, product, token]);

  return (
    <div className="container mx-auto px-4 py-8">
      {isLoading && <ReportSkeleton />}
      {!isLoading && error && <ReportError message={error} />}
      {!isLoading && !error && data && <ReportContent data={data} />}
    </div>
  );
}
