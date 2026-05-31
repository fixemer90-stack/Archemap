"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { NatalChart } from "@/components/chart/natal-chart";
import { SocionicsResult } from "@/components/chart/socionics-result";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth-store";

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

interface ArchetypeClaim {
  archetype: string;
  score: number;
  confidence: { value: number; label: string; reason_codes: string[] };
  message: string;
  basis: {
    rule_id: string;
    feature: string;
    value: number;
    contribution: number;
  }[];
  counter_evidence: {
    rule_id: string;
    feature: string;
    value: number;
    contribution: number;
  }[];
}

interface InterpretationData {
  product: string;
  primary_archetype: string;
  primary_score: number;
  primary_confidence: { value: number; label: string; reason_codes: string[] };
  claims: ArchetypeClaim[];
  all_archetype_scores: Record<string, number>;
  quality_warning: string | null;
  provenance: Record<string, string>;
}

interface ProfileData {
  id: string;
  name: string;
  birth_date: string;
  birth_time: string | null;
  birth_time_accuracy: string;
  birth_place: string;
}

interface ChartSnapshot {
  id: string;
  profile_id: string;
  chart_data: ChartData;
  socionics: SocionicsData;
}

// ── Confidence Badge ───────────────────────────────────────────────
function ConfidenceBadge({ value, label }: { value: number; label: string }) {
  const color =
    value >= 0.7
      ? "text-[#6BAFBD] border-[rgba(107,175,189,0.30)]"
      : value >= 0.5
        ? "text-[#D8B45A] border-[rgba(216,180,90,0.30)]"
        : "text-[#D8DCE8] border-[rgba(216,220,232,0.20)]";

  return (
    <span
      className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${color}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {label} ({Math.round(value * 100)}%)
    </span>
  );
}

// ── Score Bar ──────────────────────────────────────────────────────
function ScoreBar({ score, label }: { score: number; label: string }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-[#D8DCE8]">{label}</span>
        <span className="text-[#F6F1E8] font-mono">
          {Math.round(score * 100)}%
        </span>
      </div>
      <div className="h-2 rounded-full bg-[rgba(216,220,232,0.08)] overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-[#5B3FD6] to-[#D8B45A] transition-all"
          style={{ width: `${score * 100}%` }}
        />
      </div>
    </div>
  );
}

// ── Loading ────────────────────────────────────────────────────────
function ReportSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <div className="h-28 rounded-[20px] bg-[rgba(255,255,255,0.04)]" />
      <div className="h-72 rounded-[20px] bg-[rgba(255,255,255,0.04)]" />
      <div className="h-52 rounded-[20px] bg-[rgba(255,255,255,0.04)]" />
    </div>
  );
}

// ── Error ──────────────────────────────────────────────────────────
function ReportError({ message }: { message: string }) {
  return (
    <div className="glass p-8 text-center space-y-4">
      <p className="text-[#E54D4D]">{message}</p>
      <Button variant="outline" asChild>
        <Link href="/dashboard">Вернуться</Link>
      </Button>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────
export default function ReportPage() {
  const params = useParams();
  const profileId = params.profileId as string;

  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [chart, setChart] = useState<ChartData | null>(null);
  const [socionics, setSocionics] = useState<SocionicsData | null>(null);
  const [interpretation, setInterpretation] =
    useState<InterpretationData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchReport() {
      try {
        setLoading(true);

        // Get auth token
        const token = useAuthStore.getState().token;
        const authHeaders: Record<string, string> = {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };

        // 1. Fetch profile
        const profileRes = await fetch(`/api/v1/profiles/${profileId}`, {
          headers: authHeaders,
        });
        if (!profileRes.ok) throw new Error("Профиль не найден");
        const profileData = await profileRes.json();
        setProfile(profileData);

        // 2. Fetch or compute chart
        const chartRes = await fetch(`/api/v1/profiles/${profileId}/chart`, {
          method: "POST",
          headers: authHeaders,
        });
        if (!chartRes.ok) throw new Error("Не удалось построить карту");
        const chartData = await chartRes.json();
        setChart(chartData.chart_data);

        // Parse socionics from chart response
        if (chartData.socionics && chartData.socionics.top3) {
          setSocionics(chartData.socionics);
        } else if (chartData.function_strengths) {
          // Fallback: build socionics from function_strengths
          setSocionics({
            top3: [],
            function_strengths: chartData.function_strengths,
          });
        }

        // 3. Fetch interpretation
        const interpRes = await fetch("/api/v1/rules/interpret", {
          method: "POST",
          headers: authHeaders,
          body: JSON.stringify({
            profile_id: profileId,
            product: "self",
            mode: "full",
          }),
        });
        if (interpRes.ok) {
          const interpData = await interpRes.json();
          setInterpretation(interpData);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка загрузки");
      } finally {
        setLoading(false);
      }
    }

    fetchReport();
  }, [profileId]);

  if (loading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8] mb-8">
          Ваш отчёт
        </h1>
        <ReportSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto py-8 px-4">
        <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8] mb-8">
          Ваш отчёт
        </h1>
        <ReportError message={error} />
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 space-y-8">
      <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
        Ваш отчёт
      </h1>

      {/* Profile Header */}
      {profile && (
        <div className="glass p-6">
          <h2 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-[#F6F1E8]">
            {profile.name || "Без имени"}
          </h2>
          <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
            <div className="text-[#D8DCE8]">Дата рождения:</div>
            <div className="text-[#F6F1E8]">{profile.birth_date}</div>
            <div className="text-[#D8DCE8]">Время:</div>
            <div className="text-[#F6F1E8]">
              {profile.birth_time || "Неизвестно"}
              {profile.birth_time_accuracy !== "unknown" && (
                <span className="text-xs text-[rgba(216,220,232,0.50)] ml-1">
                  (
                  {profile.birth_time_accuracy === "exact"
                    ? "точное"
                    : "приблизительное"}
                  )
                </span>
              )}
            </div>
            <div className="text-[#D8DCE8]">Место:</div>
            <div className="text-[#F6F1E8]">{profile.birth_place}</div>
          </div>
        </div>
      )}

      {/* Archetype Interpretation */}
      {interpretation && (
        <div className="space-y-6">
          <div className="glass p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
                Архетипический профиль
              </h2>
              <span className="text-xs text-[rgba(216,220,232,0.40)]">
                {interpretation.provenance.ruleset_version}
              </span>
            </div>

            {interpretation.quality_warning && (
              <div className="evidence-block">
                <p className="text-sm text-[#D8B45A]">
                  {interpretation.quality_warning}
                </p>
              </div>
            )}

            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-[#F6F1E8]">
                  {interpretation.primary_archetype}
                </span>
                <ConfidenceBadge
                  value={interpretation.primary_confidence.value}
                  label={interpretation.primary_confidence.label}
                />
              </div>
              <ScoreBar
                score={interpretation.primary_score}
                label="Выраженность"
              />
            </div>
          </div>

          {/* All archetype scores */}
          {Object.keys(interpretation.all_archetype_scores).length > 1 && (
            <div className="glass p-6 space-y-3">
              <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
                Все архетипы
              </h3>
              {Object.entries(interpretation.all_archetype_scores).map(
                ([id, score]) => (
                  <ScoreBar key={id} score={score} label={id} />
                ),
              )}
            </div>
          )}

          {/* Claims with evidence */}
          {interpretation.claims.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
                Детали
              </h3>
              {interpretation.claims.map((claim, i) => (
                <div key={i} className="glass p-5 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-[#F6F1E8]">
                      {claim.archetype}
                    </span>
                    <span className="font-mono text-sm text-[#D8B45A]">
                      {Math.round(claim.score * 100)}%
                    </span>
                  </div>
                  <p className="text-sm text-[#D8DCE8]">{claim.message}</p>

                  {claim.basis.length > 0 && (
                    <div className="evidence-block">
                      <p className="text-xs text-[#D8DCE8] mb-1">Основания:</p>
                      {claim.basis.map((b, j) => (
                        <p key={j} className="text-xs text-[#8DA8FF]">
                          {b.feature}: {b.value.toFixed(2)} → вклад{" "}
                          {b.contribution.toFixed(2)}
                        </p>
                      ))}
                    </div>
                  )}

                  {claim.counter_evidence.length > 0 && (
                    <div className="pl-3 border-l border-[rgba(229,77,77,0.30)]">
                      <p className="text-xs text-[rgba(229,77,77,0.70)] mb-1">
                        Контрдоказательства:
                      </p>
                      {claim.counter_evidence.slice(0, 3).map((c, j) => (
                        <p
                          key={j}
                          className="text-xs text-[rgba(229,122,122,0.60)]"
                        >
                          {c.feature}: {c.value.toFixed(2)}
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Natal Chart */}
      {chart && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
              Натальная карта
            </h2>
          </div>
          <NatalChart chart={chart} />
        </div>
      )}

      {/* Socionics */}
      {socionics && (
        <div className="space-y-4">
          <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
            Соционический тип
          </h2>
          <SocionicsResult data={socionics} />
        </div>
      )}
    </div>
  );
}
