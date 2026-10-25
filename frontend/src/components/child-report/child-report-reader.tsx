"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/lib/api-client";
import {
  childPdfUrl,
  childTerminal,
  getChild,
  getChildGeneration,
  getChildReport,
  newChildKey,
  retryChildReport,
  updateChildAge,
} from "@/lib/api/child";
import type { ChildGeneration, ChildRecord, ChildReport } from "@/types/child";
import {
  ChildError,
  ChildGenerationCopy,
} from "@/components/child/child-shared";
import "@/components/child/child.css";

export function ChildReportReader({ reportId }: { reportId: string }) {
  const [report, setReport] = useState<ChildReport | null>(null);
  const [child, setChild] = useState<ChildRecord | null>(null);
  const [generation, setGeneration] = useState<ChildGeneration | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [operation, setOperation] = useState<"retry" | "age" | null>(null);
  const [paused, setPaused] = useState(false);
  const [loading, setLoading] = useState(true);
  const retryKey = useRef<string | null>(null);
  const ageKey = useRef<string | null>(null);
  const pollCount = useRef(0);
  const content = report?.presentation;
  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const loaded = await getChildReport(reportId);
        const selected = await getChild(loaded.child_id);
        if (active) {
          setReport(loaded);
          setChild(selected);
          setGeneration({
            generation_id: loaded.generation_id,
            report_id: loaded.report_id,
            status: loaded.status,
          });
        }
      } catch (e) {
        if (active) setError(e);
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [reportId]);
  useEffect(() => {
    if (!generation || childTerminal(generation.status) || paused) return;
    let active = true;
    const timer = setTimeout(
      async () => {
        try {
          const next = await getChildGeneration(generation.generation_id);
          const fresh = await getChildReport(reportId);
          if (!active) return;
          if (fresh.child_id !== report?.child_id)
            throw new Error("Report lineage changed");
          setReport(fresh);
          setGeneration(next);
          pollCount.current++;
          if (pollCount.current >= 120) setPaused(true);
        } catch (e) {
          if (!active) return;
          setError(e);
          setPaused(true);
          if (e instanceof ApiError && [402, 403, 404].includes(e.status)) {
            setReport(null);
            setChild(null);
          }
        }
      },
      Math.max(500, generation.poll_after_ms ?? 2000),
    );
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [generation, paused, reportId, report?.child_id]);
  useEffect(() => {
    if (generation && childTerminal(generation.status)) {
      // A terminal response proves this attempt finished. A deliberate next click
      // is new work; transport failures without that proof keep their original key.
      retryKey.current = null;
      ageKey.current = null;
    }
  }, [generation]);
  async function act(operation: "retry" | "age") {
    if (!content || busy) return;
    setBusy(true);
    setOperation(operation);
    setError(null);
    try {
      let accepted: ChildGeneration;
      if (operation === "retry") {
        retryKey.current ??= newChildKey("retry");
        accepted = await retryChildReport(reportId, retryKey.current);
      } else {
        ageKey.current ??= newChildKey("age");
        accepted = await updateChildAge(
          reportId,
          content.metadata.core_report_version,
          ageKey.current,
        );
      }
      // The returned generation, not the child ID, owns progress.
      const confirmed = await getChildGeneration(accepted.generation_id);
      const refreshed = await getChildReport(reportId);
      if (refreshed.child_id !== child?.id)
        throw new Error("Report lineage changed");
      setReport(refreshed);
      setGeneration(confirmed);
      setPaused(false);
      pollCount.current = 0;
    } catch (e) {
      setError(e);
      setPaused(true);
      if (e instanceof ApiError && [402, 403, 404].includes(e.status)) {
        setReport(null);
        setChild(null);
      }
    } finally {
      setBusy(false);
    }
  }
  return (
    <article
      className="child-surface"
      aria-label="Отчёт о взаимодействии с ребёнком"
    >
      <div className="child-actions child-no-print">
        <Link className="child-secondary" href="/products/child">
          К списку детей
        </Link>
        {content && (
          <a
            className="child-secondary"
            href={childPdfUrl(reportId, content.metadata.age_snapshot_id)}
          >
            Скачать PDF
          </a>
        )}
      </div>
      {loading && <p role="status">Загружаем сохранённый отчёт…</p>}
      {error != null && <ChildError error={error} />}
      {content && child && (
        <>
          <header className="child-hero">
            <p className="child-eyebrow">Ребёнок: {child.display_name}</p>
            <h1>{content.title}</h1>
            <p>{content.introduction}</p>
          </header>
          <div className="child-notice">
            <ChildGenerationCopy status={report.status} />
            {operation && generation && !childTerminal(generation.status) && (
              <p role="status">
                {operation === "age"
                  ? "Обновляем возрастной блок"
                  : "Подготавливаем недоступные пояснения"}
                : {child.display_name}. Сохранённые разделы остаются доступны.
              </p>
            )}
            {["narrative_failed", "child_narrative_disabled"].includes(
              report.status,
            ) && (
              <button
                className="child-secondary child-no-print"
                disabled={
                  busy ||
                  error != null ||
                  (!!generation && !childTerminal(generation.status))
                }
                onClick={() => void act("retry")}
              >
                Повторить недоступные пояснения: {child.display_name}
              </button>
            )}
          </div>
          {paused && (
            <div className="child-notice child-no-print">
              <p>
                Автоматическая проверка приостановлена. Сохранённая часть
                остаётся доступна.
              </p>
              <button
                className="child-secondary"
                onClick={() => {
                  setError(null);
                  setPaused(false);
                  pollCount.current = 0;
                }}
              >
                Проверить состояние снова
              </button>
            </div>
          )}
          <details className="child-no-print">
            <summary>Содержание отчёта</summary>
            <nav aria-label="Разделы отчёта" className="child-report-nav">
              {content.sections.map((section, index) => (
                <a key={section.key} href={`#child-section-${section.key}`}>
                  {index + 1}. {section.title}
                </a>
              ))}
            </nav>
          </details>
          {content.sections.map((section, index) => (
            <section
              className="child-panel child-report-section"
              data-child-section={section.key}
              id={`child-section-${section.key}`}
              key={section.key}
              aria-labelledby={`child-heading-${section.key}`}
            >
              <p className="child-eyebrow">
                {String(index + 1).padStart(2, "0")} · {child.display_name}
              </p>
              <h2 id={`child-heading-${section.key}`}>{section.title}</h2>
              {section.key === "current_age" && (
                <div className="child-stack">
                  <p className="child-muted">
                    Возраст на дату {content.age.as_of_date}
                  </p>
                  <p>
                    {content.age.age_years} лет · {content.age.age_months} мес.
                    · {content.age.age_days} дн.
                  </p>
                  {content.age.stale && (
                    <div className="child-notice">
                      <p>
                        Возрастной блок сохранён на прошлую дату. Основная часть
                        отчёта не меняется при обновлении возраста.
                      </p>
                      <button
                        className="child-secondary child-no-print"
                        disabled={
                          busy ||
                          error != null ||
                          (!!generation && !childTerminal(generation.status))
                        }
                        onClick={() => void act("age")}
                      >
                        Обновить возрастной блок: {child.display_name}
                      </button>
                    </div>
                  )}
                </div>
              )}
              {section.body ? (
                <p className="child-report-body">{section.body}</p>
              ) : (
                <p className="child-muted">
                  {section.status === "not_applicable"
                    ? "Для отдельного пояснения пока недостаточно устойчивых оснований."
                    : "Подробное пояснение пока недоступно. Ниже — сохранённые ориентиры для действий взрослого."}
                </p>
              )}
              {section.actions.length > 0 && (
                <div>
                  <h3>Что можно попробовать</h3>
                  <ul className="list-disc space-y-2 pl-5">
                    {section.actions.map((action, i) => (
                      <li key={i}>{action}</li>
                    ))}
                  </ul>
                </div>
              )}
              <details>
                <summary>Насколько уверенно это применять</summary>
                <p className="child-muted">{section.confidence_note}</p>
              </details>
            </section>
          ))}
          <section className="child-panel">
            <details>
              <summary>Основания и ограничения</summary>
              <div className="child-stack">
                <p>{content.technical_basis.note}</p>
                <p>
                  {child.birth_time_confidence === "unknown"
                    ? "В текущих данных ребёнка время рождения неизвестно. Уточнение данных не меняет уже сохранённый отчёт."
                    : child.birth_time_confidence === "approximate"
                      ? "В текущих данных ребёнка время рождения приблизительное. Уточнение данных не меняет уже сохранённый отчёт."
                      : "В текущих данных ребёнка время рождения указано как точное. Уточнение данных не меняет уже сохранённый отчёт."}
                </p>
                {content.technical_basis.confidence_markers.length > 0 && (
                  <p>
                    Часть оснований имеет ограниченную уверенность.
                    Воспринимайте рекомендации как варианты для наблюдения, а не
                    как свойства ребёнка.
                  </p>
                )}
                <dl className="child-review">
                  <div>
                    <dt>Версия основной части</dt>
                    <dd>{content.metadata.core_report_version}</dd>
                  </div>
                  <div>
                    <dt>Возрастной снимок для этого PDF</dt>
                    <dd>{content.metadata.age_snapshot_id}</dd>
                  </div>
                  <div>
                    <dt>Дата возрастного блока</dt>
                    <dd>{content.metadata.as_of_date}</dd>
                  </div>
                </dl>
              </div>
            </details>
          </section>
        </>
      )}
    </article>
  );
}
