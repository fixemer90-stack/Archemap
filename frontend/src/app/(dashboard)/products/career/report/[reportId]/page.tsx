"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowLeft, Download, Loader2, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  getCareerReport,
  getCareerReportPdfUrl,
  type CareerReportPayload,
} from "@/lib/api/career";
import { ApiError } from "@/lib/api-client";
import { buildCareerReportViewModel } from "@/lib/career/report-view-model";

const TERM_HELP: Record<string, string> = {
  Выраженность:
    "Показывает силу рабочей тенденции в текущей модели. Это не оценка личности и не прогноз успеха.",
  Уверенность:
    "Показывает, насколько разнообразны и согласованы основания вывода. Низкая уверенность требует осторожной проверки на опыте.",
  "Семейство ролей":
    "Группа задач и способов приносить результат, а не конкретная должность или обязательная профессия.",
};

function getErrorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 402)
    return "Для чтения Career-отчёта нужен активный Plus или сохранённый legacy-доступ.";
  return error instanceof Error ? error.message : "Не удалось загрузить отчёт";
}

export default function CareerReportPage() {
  const params = useParams<{ reportId: string }>();
  const reportId = params.reportId;
  const [payload, setPayload] = useState<CareerReportPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const next = await getCareerReport(reportId);
      setPayload(next);
      setError(null);
    } catch (loadError) {
      setError(getErrorMessage(loadError));
    } finally {
      setLoading(false);
    }
  }, [reportId]);

  useEffect(() => {
    let cancelled = false;
    getCareerReport(reportId)
      .then((next) => {
        if (!cancelled) {
          setPayload(next);
          setError(null);
        }
      })
      .catch((loadError: unknown) => {
        if (!cancelled) setError(getErrorMessage(loadError));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [reportId]);

  useEffect(() => {
    if (
      !payload ||
      ["ready", "narrative_failed", "failed"].includes(payload.status)
    )
      return;
    const timer = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(timer);
  }, [load, payload]);

  const report = useMemo(
    () => (payload ? buildCareerReportViewModel(payload) : null),
    [payload],
  );

  if (loading)
    return (
      <div
        className="flex min-h-[50vh] items-center justify-center text-[#D8DCE8]"
        aria-live="polite"
      >
        <Loader2 className="mr-3 h-5 w-5 animate-spin text-[#D7B466]" />{" "}
        Загружаем профессиональный профиль…
      </div>
    );

  if (error || !payload || !report)
    return (
      <div className="mx-auto max-w-2xl space-y-5 py-16">
        <div
          role="alert"
          className="rounded-2xl border border-red-400/30 bg-red-500/10 p-5 text-red-100"
        >
          {error ?? "Отчёт не найден"}
        </div>
        <Button asChild variant="outline">
          <Link href="/products/career">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Вернуться в Career
          </Link>
        </Button>
      </div>
    );

  return (
    <article className="career-reader mx-auto max-w-5xl space-y-10 pb-20 text-[#F6F1E8]">
      <nav
        className="flex flex-wrap items-center justify-between gap-3 print:hidden"
        aria-label="Действия с отчётом"
      >
        <Button asChild variant="outline">
          <Link href="/products/career">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Назад
          </Link>
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => void load()}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Обновить
          </Button>
          <Button asChild>
            <a href={getCareerReportPdfUrl(reportId)} download>
              <Download className="mr-2 h-4 w-4" />
              Скачать PDF
            </a>
          </Button>
        </div>
      </nav>

      <header className="relative overflow-hidden rounded-[28px] border border-[#D7B466]/25 bg-[radial-gradient(circle_at_top_right,rgba(215,180,102,0.18),transparent_40%),linear-gradient(145deg,#151c2a,#0d131f)] p-7 shadow-2xl sm:p-12">
        <p className="text-xs uppercase tracking-[0.28em] text-[#D7B466]">
          Astrotype Career · версия {payload.version}
        </p>
        <h1 className="mt-4 max-w-3xl font-[family-name:var(--font-cormorant)] text-4xl font-semibold leading-tight sm:text-6xl">
          Профессиональная механика без готовых ярлыков
        </h1>
        <p className="mt-5 max-w-2xl text-sm leading-7 text-[#C8D0DE]">
          Этот отчёт помогает увидеть рабочий ритм, способы принимать решения,
          условия эффективности и несколько возможных направлений. Он не
          назначает профессию.
        </p>
        <div className="mt-7 flex flex-wrap gap-2 text-xs text-[#D8DCE8]">
          <span className="rounded-full border border-white/10 px-3 py-1.5">
            Расчёт сохранён
          </span>
          <span className="rounded-full border border-white/10 px-3 py-1.5">
            {
              report.sections.filter((section) => section.status === "ready")
                .length
            }{" "}
            из {report.sections.length} пояснений готовы
          </span>
        </div>
      </header>

      {payload.status === "narrative_failed" && (
        <aside
          className="rounded-2xl border border-amber-300/25 bg-amber-300/5 p-5 text-sm leading-6 text-amber-50"
          aria-live="polite"
        >
          <strong>Часть пояснений временно недоступна.</strong> Базовый профиль,
          показатели и уже готовые разделы остаются доступными.
        </aside>
      )}

      <section className="space-y-8" aria-label="Основные разделы отчёта">
        {report.sections.map((section, index) => (
          <section
            key={section.key}
            id={section.key}
            className="scroll-mt-8 rounded-[24px] border border-white/10 bg-[#111927]/85 p-6 shadow-[0_20px_60px_rgba(0,0,0,0.18)] sm:p-9"
          >
            <p className="text-xs font-semibold tracking-[0.22em] text-[#D7B466]">
              {String(index + 1).padStart(2, "0")}
            </p>
            <h2 className="mt-2 font-[family-name:var(--font-cormorant)] text-3xl font-semibold">
              {section.title}
            </h2>
            {section.body ? (
              <div className="mt-5 space-y-4 text-[15px] leading-8 text-[#D8DCE8]">
                {section.body.split("\n\n").map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            ) : (
              <SectionPlaceholder status={section.status} />
            )}
          </section>
        ))}
      </section>

      <section className="rounded-[24px] border border-[#D7B466]/20 bg-[#0e1623] p-6 sm:p-9">
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-[0.22em] text-[#D7B466]">
            Практические акценты
          </p>
          <h2 className="mt-2 font-[family-name:var(--font-cormorant)] text-3xl font-semibold">
            Выраженные рабочие тенденции
          </h2>
          <p className="mt-3 text-sm leading-6 text-[#B9C3D3]">
            <CareerTerm term="Выраженность" /> показывает силу темы, но не делит
            качества на хорошие и плохие.
          </p>
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {report.dimensions.map((dimension) => (
            <article
              key={dimension.key}
              className="rounded-2xl border border-white/10 bg-white/[0.03] p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-medium">{dimension.label}</h3>
                <strong className="text-2xl text-[#E2C27A]">
                  {Math.round(dimension.score)}
                </strong>
              </div>
              <p className="mt-3 text-xs leading-5 text-[#AEB9CA]">
                {dimension.explanation}
              </p>
              {dimension.confidence !== null && (
                <p className="mt-3 text-xs text-[#8795AA]">
                  <CareerTerm term="Уверенность" />:{" "}
                  {dimension.confidence >= 0.75
                    ? "основания согласованы"
                    : "лучше проверить на опыте"}
                </p>
              )}
            </article>
          ))}
        </div>
      </section>

      {(report.contradictions.length > 0 || report.context.length > 0) && (
        <section className="grid gap-5 md:grid-cols-2">
          <div className="rounded-[22px] border border-white/10 bg-[#111927] p-6">
            <h2 className="font-[family-name:var(--font-cormorant)] text-2xl">
              Полезные развилки
            </h2>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-[#C8D0DE]">
              {report.contradictions.map((item) => (
                <li key={item}>— {item}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-[22px] border border-white/10 bg-[#111927] p-6">
            <h2 className="font-[family-name:var(--font-cormorant)] text-2xl">
              Учтённый контекст
            </h2>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-[#C8D0DE]">
              {report.context.map((item) => (
                <li key={item}>— {item}</li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {report.roles.length > 0 && (
        <section className="space-y-5">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-[#D7B466]">
              Направления
            </p>
            <h2 className="mt-2 font-[family-name:var(--font-cormorant)] text-3xl">
              <CareerTerm term="Семейство ролей" />
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {report.roles.map((role) => (
              <article
                key={role.key}
                className="rounded-[22px] border border-white/10 bg-[#111927] p-6"
              >
                <span className="rounded-full border border-[#D7B466]/25 px-3 py-1 text-xs text-[#E2C27A]">
                  {role.category}
                </span>
                <h3 className="mt-4 text-xl capitalize">{role.title}</h3>
                {role.examples.length > 0 && (
                  <p className="mt-4 text-sm leading-6 text-[#C8D0DE]">
                    <strong>{role.exampleLabel}:</strong>{" "}
                    {role.examples.join(", ")}.
                  </p>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

      <details className="rounded-2xl border border-white/10 bg-[#0d1420] p-5 text-sm text-[#B9C3D3]">
        <summary className="cursor-pointer font-medium text-[#F6F1E8]">
          Основа интерпретации
        </summary>
        <p className="mt-4 leading-6">
          Отчёт собран из сохранённых расчётов, ответов и версий правил. Этот
          слой нужен для проверяемости и не заменяет профессиональную
          консультацию или ваш реальный опыт.
        </p>
      </details>
    </article>
  );
}

function SectionPlaceholder({ status }: { status: string }) {
  return (
    <div className="mt-5 rounded-xl border border-dashed border-white/15 p-5 text-sm leading-6 text-[#AEB9CA]">
      {status === "failed"
        ? "Пояснение не удалось получить. Расчёт и остальные разделы сохранены."
        : "Пояснение готовится. Базовые показатели уже доступны ниже."}
    </div>
  );
}

function CareerTerm({ term }: { term: keyof typeof TERM_HELP }) {
  return (
    <span
      className="group relative inline-flex whitespace-nowrap border-b border-dotted border-[#D7B466] text-[#E5C97F]"
      tabIndex={0}
      data-career-term={term}
    >
      {term}
      <span
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-full z-20 mt-2 hidden w-72 -translate-x-1/2 whitespace-normal rounded-xl border border-[#D7B466]/25 bg-[#09101a] p-3 text-left text-xs font-normal leading-5 text-[#D8DCE8] shadow-xl group-hover:block group-focus:block"
      >
        {TERM_HELP[term]}
      </span>
    </span>
  );
}
