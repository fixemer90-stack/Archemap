"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useId, useMemo, useState } from "react";
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
      ["ready", "partial_failure", "narrative_failed", "failed"].includes(
        payload.status,
      )
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
        className="flex min-h-[50vh] items-center justify-center text-text-secondary"
        aria-live="polite"
      >
        <Loader2 className="mr-3 h-5 w-5 animate-spin text-accent-gold" />{" "}
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
    <article className="career-reader mx-auto max-w-5xl space-y-10 bg-transparent px-4 pb-20 text-text-primary sm:px-6 print:max-w-none print:bg-surface-elevated print:px-0 print:pb-0 print:text-text-secondary">
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

      <header className="relative grid overflow-hidden rounded-[28px] border border-border-default/25 bg-[var(--hero-background)] p-7 shadow-2xl sm:p-12 lg:grid-cols-[minmax(0,1fr)_18rem] lg:gap-12">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-accent-gold">
            Astrotype Career
          </p>
          <h1 className="mt-4 max-w-3xl font-[family-name:var(--font-cormorant)] text-4xl font-semibold leading-tight sm:text-6xl">
            Профессиональная механика без готовых ярлыков
          </h1>
          <p className="mt-5 max-w-2xl text-sm leading-7 text-text-secondary">
            Этот отчёт помогает увидеть рабочий ритм, способы принимать решения,
            условия эффективности и несколько возможных направлений. Он не
            назначает профессию.
          </p>
          <div className="mt-7 flex flex-wrap gap-2 text-xs text-text-secondary">
            <span className="rounded-full border border-border-default px-3 py-1.5">
              Расчёт сохранён
            </span>
            <span className="rounded-full border border-border-default px-3 py-1.5">
              {
                report.sections.filter((section) => section.status === "ready")
                  .length
              }{" "}
              из {report.sections.length} пояснений готовы
            </span>
          </div>
        </div>
        <aside className="grid content-end gap-3" aria-label="Краткий профиль">
          <div className="rounded-2xl border border-border-default bg-scrim p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
              Ведущий профиль
            </p>
            <p className="mt-2 text-lg font-semibold text-text-primary">
              {report.dimensions[0]?.label ?? "Профессиональная механика"}
            </p>
          </div>
          <div className="rounded-2xl border border-border-default bg-scrim p-4">
            <p className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
              Рабочий вектор
            </p>
            <p className="mt-2 text-lg font-semibold capitalize text-text-primary">
              {report.roles[0]?.title ?? "Контекстный выбор"}
            </p>
          </div>
        </aside>
      </header>

      <nav
        aria-label="Разделы отчёта"
        className="grid overflow-hidden rounded-2xl border border-border-default bg-surface-subtle sm:grid-cols-2 lg:grid-cols-5 print:hidden"
      >
        {report.sections.map((section, index) => (
          <a
            key={section.key}
            href={`#${section.key}`}
            className="border-border-default p-4 text-sm text-text-secondary transition hover:bg-surface-elevated/[0.04] hover:text-text-primary sm:border-r sm:border-b"
          >
            <span className="block text-xs font-semibold text-accent-gold">
              {String(index + 1).padStart(2, "0")}
            </span>
            <span className="mt-1 block">{section.title}</span>
          </a>
        ))}
      </nav>

      {report.notice && (
        <aside
          className="rounded-2xl border border-amber-300/25 bg-amber-300/5 p-5 text-sm leading-6 text-amber-50"
          aria-live="polite"
          data-report-notice={report.notice.kind}
        >
          <strong>{report.notice.title}</strong> {report.notice.body}
        </aside>
      )}

      <section className="space-y-8" aria-label="Основные разделы отчёта">
        {report.sections.map((section, index) => (
          <section
            key={section.key}
            id={section.key}
            data-presentation-key={section.key}
            data-section-status={section.status}
            className="scroll-mt-8 rounded-[24px] border border-border-default bg-surface-subtle/85 p-6 shadow-elevated sm:p-9"
          >
            <p className="text-xs font-semibold tracking-[0.22em] text-accent-gold">
              {String(index + 1).padStart(2, "0")}
            </p>
            <h2 className="mt-2 font-[family-name:var(--font-cormorant)] text-3xl font-semibold">
              {section.title}
            </h2>
            {section.body ? (
              <div className="mt-5 space-y-4 text-[15px] leading-8 text-text-secondary">
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

      <section
        data-presentation-key="dimensions"
        className="rounded-[24px] border border-border-default/20 bg-surface-subtle p-6 sm:p-9"
      >
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-[0.22em] text-accent-gold">
            Практические акценты
          </p>
          <h2 className="mt-2 font-[family-name:var(--font-cormorant)] text-3xl font-semibold">
            Выраженные рабочие тенденции
          </h2>
          <p className="mt-3 text-sm leading-6 text-text-secondary">
            <CareerTerm term="Выраженность" /> показывает силу темы, но не делит
            качества на хорошие и плохие.
          </p>
        </div>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {report.dimensions.map((dimension) => (
            <article
              key={dimension.key}
              className="rounded-2xl border border-border-default bg-surface-elevated/[0.03] p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <h3 className="font-medium">{dimension.label}</h3>
                <strong className="text-2xl text-accent-gold">
                  {Math.round(dimension.score)}
                </strong>
              </div>
              {dimension.confidence !== null && (
                <p className="mt-3 text-xs text-text-muted">
                  <CareerTerm term="Уверенность" />:{" "}
                  {dimension.confidence_label.toLocaleLowerCase("ru-RU")}
                </p>
              )}
            </article>
          ))}
        </div>
      </section>

      {(report.contradictions.length > 0 || report.context.length > 0) && (
        <section className="grid gap-5 md:grid-cols-2">
          {report.contradictions.length > 0 && (
            <div
              data-presentation-key="contradictions"
              className="rounded-[22px] border border-border-default bg-surface-subtle p-6"
            >
              <h2 className="font-[family-name:var(--font-cormorant)] text-2xl">
                Полезные развилки
              </h2>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-text-secondary">
                {report.contradictions.map((item) => (
                  <li key={item.key}>
                    — {item.label}
                    {(item.capability_score !== null ||
                      item.motivation_score !== null) && (
                      <span className="block text-xs text-text-muted">
                        {item.capability_score !== null &&
                          `Способность: ${item.capability_score}`}
                        {item.capability_score !== null &&
                          item.motivation_score !== null &&
                          " · "}
                        {item.motivation_score !== null &&
                          `Мотивация: ${item.motivation_score}`}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.context.length > 0 && (
            <div
              data-presentation-key="context"
              className="rounded-[22px] border border-border-default bg-surface-subtle p-6"
            >
              <h2 className="font-[family-name:var(--font-cormorant)] text-2xl">
                Учтённый контекст
              </h2>
              <ul className="mt-4 space-y-3 text-sm leading-6 text-text-secondary">
                {report.context.map((item) => (
                  <li key={item.key}>— {item.label}</li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      {report.roles.length > 0 && (
        <section className="space-y-5" data-presentation-key="roles">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-accent-gold">
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
                className="rounded-[22px] border border-border-default bg-surface-subtle p-6"
              >
                <span className="rounded-full border border-border-default/25 px-3 py-1 text-xs text-accent-gold">
                  {role.category}
                </span>
                <h3 className="mt-4 text-xl capitalize">{role.title}</h3>
                {role.examples.length > 0 && (
                  <p className="mt-4 text-sm leading-6 text-text-secondary">
                    <strong>{role.example_label}:</strong>{" "}
                    {role.examples.join(", ")}.
                  </p>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

      <details
        data-presentation-key="technical_basis"
        className="rounded-2xl border border-border-default bg-surface-subtle p-5 text-sm text-text-secondary"
      >
        <summary className="cursor-pointer font-medium text-text-primary">
          {report.technicalBasis.title}
        </summary>
        <p className="mt-4 leading-6">{report.technicalBasis.body}</p>
      </details>
      <style jsx global>{`
        @media print {
          html,
          body {
            background: var(--print-canvas) !important;
            color: var(--print-text) !important;
          }

          .career-reader {
            background: var(--print-canvas) !important;
            color: var(--print-text) !important;
          }

          .career-reader header,
          .career-reader section,
          .career-reader article,
          .career-reader details {
            break-inside: avoid;
            border-color: var(--print-border) !important;
            background: var(--print-canvas) !important;
            box-shadow: none !important;
            color: var(--print-text) !important;
          }

          .career-reader div {
            background-color: transparent !important;
          }

          .career-reader p,
          .career-reader h1,
          .career-reader h2,
          .career-reader h3,
          .career-reader li,
          .career-reader strong,
          .career-reader summary,
          .career-reader span {
            color: var(--print-text) !important;
          }

          .career-reader [role="tooltip"] {
            display: none !important;
          }
        }
      `}</style>
    </article>
  );
}

function SectionPlaceholder({ status }: { status: string }) {
  return (
    <div className="mt-5 rounded-xl border border-dashed border-border-default p-5 text-sm leading-6 text-text-secondary">
      {status === "failed"
        ? "Пояснение не удалось получить. Расчёт и остальные разделы сохранены."
        : "Пояснение готовится. Базовые показатели уже доступны ниже."}
    </div>
  );
}

function CareerTerm({ term }: { term: keyof typeof TERM_HELP }) {
  const tooltipId = `career-term-${useId().replaceAll(":", "")}`;
  return (
    <span
      className="group relative inline-flex whitespace-nowrap border-b border-dotted border-border-default text-accent-gold"
      tabIndex={0}
      data-career-term={term}
      aria-describedby={tooltipId}
    >
      {term}
      <span
        id={tooltipId}
        role="tooltip"
        className="pointer-events-none absolute left-0 top-full z-20 mt-2 hidden w-[min(18rem,calc(100vw-2rem))] whitespace-normal rounded-xl border border-border-default/25 bg-surface-subtle p-3 text-left text-xs font-normal leading-5 text-text-secondary shadow-xl group-hover:block group-focus:block"
      >
        {TERM_HELP[term]}
      </span>
    </span>
  );
}
