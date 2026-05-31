"use client";

import { Suspense } from "react";
import { NatalChart } from "@/components/chart/natal-chart";
import { SocionicsResult } from "@/components/chart/socionics-result";

// ── Types ──────────────────────────────────────────────────────────
interface Planet {
  name: string;
  sign: string;
  degree: number;
  house: number | null;
  is_retrograde: boolean;
}

interface House {
  number: number;
  sign: string;
  longitude: number;
}

interface Aspect {
  planet_a: string;
  aspect_type: string;
  planet_b: string;
  orb: number;
  is_applying: boolean;
}

interface ChartData {
  planets: Planet[];
  houses: House[];
  aspects: Aspect[];
}

interface SocionicsType {
  type: string;
  name: string;
  score: number;
  confidence: number;
  functions: string;
  model_a: number;
}

interface FunctionStrengths {
  Se: number;
  Si: number;
  Ne: number;
  Ni: number;
  Fe: number;
  Fi: number;
  Te: number;
  Ti: number;
}

interface SocionicsData {
  top3: SocionicsType[];
  function_strengths: FunctionStrengths;
}

interface ReportData {
  chart: ChartData;
  socionics: SocionicsData;
  profile: {
    name: string;
    birth_date: string;
    birth_time: string | null;
    birth_time_accuracy: string;
    birth_place: string;
  };
}

// ── Report Header ──────────────────────────────────────────────────
function ReportHeader({ profile }: { profile: ReportData["profile"] }) {
  return (
    <div className="rounded-lg border p-4">
      <h2 className="text-xl font-bold">{profile.name}</h2>
      <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
        <div className="text-muted-foreground">Дата рождения:</div>
        <div>{profile.birth_date}</div>

        <div className="text-muted-foreground">Время:</div>
        <div>
          {profile.birth_time || "Неизвестно"}
          {profile.birth_time_accuracy !== "unknown" && (
            <span className="text-xs text-muted-foreground ml-1">
              (
              {profile.birth_time_accuracy === "exact"
                ? "точное"
                : "приблизительное"}
              )
            </span>
          )}
        </div>

        <div className="text-muted-foreground">Место:</div>
        <div>{profile.birth_place}</div>
      </div>
    </div>
  );
}

// ── Loading Skeleton ───────────────────────────────────────────────
function ReportSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-24 rounded-lg bg-muted" />
      <div className="h-64 rounded-lg bg-muted" />
      <div className="h-48 rounded-lg bg-muted" />
    </div>
  );
}

// ── Report Content ─────────────────────────────────────────────────
function ReportContent({ data }: { data: ReportData }) {
  return (
    <div className="space-y-6">
      <ReportHeader profile={data.profile} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h2 className="text-lg font-semibold mb-4">Натальная карта</h2>
          <NatalChart chart={data.chart} />
        </div>
        <div>
          <h2 className="text-lg font-semibold mb-4">Соционический тип</h2>
          <SocionicsResult data={data.socionics} />
        </div>
      </div>
    </div>
  );
}

// ── Report Page ────────────────────────────────────────────────────
export default function ReportPage({
  params,
}: {
  params: { profileId: string };
}) {
  // In real implementation, fetch data from API
  // For now, show placeholder
  const placeholderData: ReportData = {
    chart: {
      planets: [],
      houses: [],
      aspects: [],
    },
    socionics: {
      top3: [],
      function_strengths: {
        Se: 0,
        Si: 0,
        Ne: 0,
        Ni: 0,
        Fe: 0,
        Fi: 0,
        Te: 0,
        Ti: 0,
      },
    },
    profile: {
      name: "Загрузка...",
      birth_date: "",
      birth_time: null,
      birth_time_accuracy: "unknown",
      birth_place: "",
    },
  };

  return (
    <div className="container mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Ваш отчёт</h1>
      <Suspense fallback={<ReportSkeleton />}>
        <ReportContent data={placeholderData} />
      </Suspense>
    </div>
  );
}
