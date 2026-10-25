"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "@/lib/api-client";
import { listChildren } from "@/lib/api/child";
import type { ChildRecord } from "@/types/child";
import { ChildError, timeLabels } from "@/components/child/child-shared";
import { ChildForm } from "@/components/child/child-form";
import { ChildQuestionnairePanel } from "@/components/child/child-questionnaire";
import "@/components/child/child.css";

export default function ChildProductPage() {
  const [children, setChildren] = useState<ChildRecord[]>([]);
  const [selected, setSelected] = useState<ChildRecord | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(true);
  const [resumeGeneration, setResumeGeneration] = useState<
    string | undefined
  >();
  const [form, setForm] = useState<"create" | "edit" | null>(null);
  const [readOnly, setReadOnly] = useState(false);
  const onProblem = useCallback((e: unknown) => {
    if (e instanceof ApiError && e.status === 401) setReadOnly(true);
    if (e instanceof ApiError && [402, 403, 404].includes(e.status)) {
      setError(e);
      setChildren([]);
      setSelected(null);
    }
  }, []);
  const [busy, setBusy] = useState(false);
  const onBusy = useCallback((value: boolean) => setBusy(value), []);
  useEffect(() => {
    let active = true;
    listChildren()
      .then((data) => {
        if (active) {
          setChildren(data.children);
          const params = new URLSearchParams(window.location.search);
          const initial = data.children.find(
            (c) => c.id === params.get("child_id"),
          );
          if (initial) {
            setSelected(initial);
            setResumeGeneration(params.get("generation_id") ?? undefined);
          }
        }
      })
      .catch((e) => {
        if (active) setError(e);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  return (
    <div className="child-surface">
      <header className="child-hero">
        <p className="child-eyebrow">Astrotype · Родитель и ребёнок</p>
        <h1>
          Ближе к ребёнку,
          <br />
          бережнее к себе
        </h1>
        <p>
          Не «какой мой ребёнок», а «как мне лучше быть рядом». Замечайте, что
          помогает контакту, и пробуйте небольшие изменения в своих действиях.
        </p>
      </header>
      <aside className="child-notice">
        Отчёт не определяет характер, способности или будущее ребёнка и не
        заменяет помощь специалиста. Используйте имя или псевдоним — отдельный
        аккаунт ребёнку не нужен.
      </aside>
      {error != null && <ChildError error={error} />}
      {loading && <p role="status">Загружаем ваш список…</p>}
      {!loading && error == null && (
        <section aria-labelledby="child-list-title" className="child-stack">
          <div className="child-section-heading">
            <h2 id="child-list-title">Для кого подготовим отчёт?</h2>
            <button
              className="child-secondary"
              disabled={busy || readOnly}
              onClick={() => setForm("create")}
            >
              Добавить ребёнка
            </button>
          </div>
          <div className="child-grid">
            {children.map((child) => (
              <button
                className="child-person"
                key={child.id}
                disabled={busy || readOnly || form !== null}
                aria-pressed={selected?.id === child.id}
                aria-label={`Выбрать ${child.display_name}`}
                onClick={() => {
                  setSelected(child);
                  setResumeGeneration(undefined);
                }}
              >
                <span className="child-person-mark" aria-hidden="true">
                  {child.display_name.slice(0, 1)}
                </span>
                <strong>{child.display_name}</strong>
                <span>{timeLabels[child.birth_time_confidence]}</span>
                <span className="child-muted">
                  {child.age.age_years} лет {child.age.age_months} мес. ·{" "}
                  {child.age.as_of_date}
                </span>
                {selected?.id === child.id && (
                  <span className="child-selected">Выбран ребёнок</span>
                )}
              </button>
            ))}
          </div>
          {children.length === 0 && (
            <p>
              Пока нет сохранённых данных. Начните с имени или псевдонима и даты
              рождения.
            </p>
          )}
        </section>
      )}
      {form && (
        <ChildForm
          key={`${form}:${selected?.id ?? "new"}`}
          child={form === "edit" ? (selected ?? undefined) : undefined}
          onCancel={() => setForm(null)}
          onSaved={(saved) => {
            setChildren((current) =>
              current.some((c) => c.id === saved.id)
                ? current.map((c) => (c.id === saved.id ? saved : c))
                : [...current, saved],
            );
            setSelected(saved);
            setForm(null);
          }}
        />
      )}
      {selected && !form && (
        <>
          <div className="child-actions">
            <p>
              Выбран ребёнок: <strong>{selected.display_name}</strong>
            </p>
            <button
              className="child-secondary"
              disabled={busy || readOnly}
              onClick={() => setForm("edit")}
            >
              Изменить данные: {selected.display_name}
            </button>
          </div>
          <ChildQuestionnairePanel
            key={`${selected.id}:${selected.birth_time_confidence}`}
            child={selected}
            onBusy={onBusy}
            resumeGenerationId={resumeGeneration}
            onProblem={onProblem}
          />
        </>
      )}
    </div>
  );
}
