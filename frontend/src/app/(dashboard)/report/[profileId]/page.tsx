"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
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
  const profileId = params.profileId as string;
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
        const apiData = await fetchReportApiData(profileId, token || undefined);
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
  }, [profileId, token]);

  return (
    <div className="container mx-auto px-4 py-8">
      {isLoading && <ReportSkeleton />}
      {!isLoading && error && <ReportError message={error} />}
      {!isLoading && !error && data && <ReportContent data={data} />}
    </div>
  );
}
