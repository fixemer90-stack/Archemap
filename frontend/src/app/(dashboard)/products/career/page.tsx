"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Briefcase, ArrowRight, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

const GENERATE_TIMEOUT_MS = 30_000;

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Не удалось построить Career-отчёт";
}

interface Profile {
  id: string;
  name: string;
  birth_date: string;
  birth_place: string;
}

export default function CareerProductPage() {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProfiles() {
      try {
        const res = await fetch("/api/v1/profiles", {
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          setProfiles(data.items || []);
        }
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    }
    fetchProfiles();
  }, []);

  const generateReport = async (profileId: string) => {
    setGenerating(profileId);
    setError(null);

    const controller = new AbortController();
    const timeoutId = window.setTimeout(
      () => controller.abort(),
      GENERATE_TIMEOUT_MS,
    );

    try {
      const res = await fetch("/api/v1/reports/generate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        credentials: "include",
        body: JSON.stringify({
          profile_id: profileId,
          product: "career",
          mode: "full",
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const data = (await res.json().catch(() => null)) as {
          detail?: string;
        } | null;
        throw new Error(data?.detail || `Backend вернул HTTP ${res.status}`);
      }

      const report = (await res.json()) as {
        product?: string;
        status?: string;
      };
      if (report.product !== "career" || report.status !== "ready") {
        throw new Error("Backend не вернул готовый Career-отчёт.");
      }

      window.location.assign(`/report/${profileId}?product=career`);
    } catch (generateError) {
      const message =
        generateError instanceof DOMException &&
        generateError.name === "AbortError"
          ? "Генерация Career-отчёта не ответила за 30 секунд. Попробуйте ещё раз."
          : getErrorMessage(generateError);
      setError(message);
    } finally {
      window.clearTimeout(timeoutId);
      setGenerating(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
          Astrotype Career
        </h1>
        <p className="text-sm text-[#D8DCE8] mt-1">
          Карьерные сценарии: роли, рабочая среда, сильные профессиональные
          стороны.
        </p>
      </div>

      {/* What you get */}
      <div className="glass p-6 space-y-4">
        <h2 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
          Что входит в отчёт
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            "Карьерные архетипы: Лидер, Аналитик, Креатор, Дипломат, Исполнитель",
            "Профессиональные роли: топ-5 подходящих позиций",
            "Рабочая среда: где вы раскрываетесь сильнее",
            "Стиль принятия решений и коммуникации",
            "Anti-patterns: что мешает развитию",
            "Карта роста: сильные стороны и зоны развития",
          ].map((item) => (
            <div key={item} className="flex items-start gap-2">
              <span className="text-[#C28A2E] mt-0.5 text-xs">✦</span>
              <span className="text-sm text-[#D8DCE8]">{item}</span>
            </div>
          ))}
        </div>
      </div>

      {/* My reports */}
      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-100">
          {error}
        </div>
      )}

      {profiles.length > 0 && (
        <div className="space-y-4">
          <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
            Мои отчёты Career
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {profiles.map((profile) => (
              <div
                key={profile.id}
                className="glass p-5 space-y-3 hover:border-[rgba(194,138,46,0.40)] transition-all"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-[#F6F1E8]">
                    {profile.name || "Без имени"}
                  </span>
                  <Briefcase className="h-4 w-4 text-[#C28A2E]" />
                </div>
                <p className="text-xs text-[rgba(216,220,232,0.50)]">
                  {profile.birth_date} · {profile.birth_place}
                </p>
                <Button
                  size="sm"
                  className="w-full bg-[#C28A2E] hover:bg-[#A07325]"
                  onClick={() => generateReport(profile.id)}
                  disabled={generating === profile.id}
                >
                  {generating === profile.id
                    ? "Генерация..."
                    : "Построить отчёт"}
                  <ArrowRight className="h-3 w-3 ml-1" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {!loading && profiles.length === 0 && (
        <div className="glass p-8 text-center space-y-4">
          <p className="text-[#D8DCE8]">
            У вас пока нет профилей. Введите данные рождения и получите
            карьерный отчёт.
          </p>
          <Button asChild>
            <Link href="/register">
              Построить карту
              <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
          </Button>
        </div>
      )}

      <Button variant="outline" asChild>
        <Link href="/dashboard">
          <ArrowLeft className="h-4 w-4 mr-1" />
          Назад
        </Link>
      </Button>
    </div>
  );
}
