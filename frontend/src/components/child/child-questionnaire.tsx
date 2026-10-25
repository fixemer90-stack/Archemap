"use client";

import Link from "next/link";
import { ApiError } from "@/lib/api-client";
import { useEffect, useRef, useState } from "react";
import type {
  ChildGeneration,
  ChildQuestionnaire,
  ChildRecord,
} from "@/types/child";
import {
  childTerminal,
  completeChildQuestionnaire,
  createChildReport,
  getChildGeneration,
  getChildQuestionnaire,
  newChildKey,
  saveChildAnswers,
} from "@/lib/api/child";
import { ChildError, ChildGenerationCopy, timeLabels } from "./child-shared";

export function ChildQuestionnairePanel({
  child,
  onBusy,
  resumeGenerationId,
  onProblem,
}: {
  child: ChildRecord;
  onBusy: (busy: boolean) => void;
  resumeGenerationId?: string;
  onProblem: (error: unknown) => void;
}) {
  const [draft, setDraft] = useState<ChildQuestionnaire | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [error, setError] = useState<unknown>(null);
  const [saving, setSaving] = useState(false);
  const [review, setReview] = useState(false);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [generation, setGeneration] = useState<ChildGeneration | null>(null);
  const [pollPaused, setPollPaused] = useState(false);
  const completeKey = useRef<string | null>(null);
  const reportKey = useRef<string | null>(null);
  const alive = useRef(true);
  const reviewHeading = useRef<HTMLHeadingElement>(null);
  const saveQueue = useRef<Promise<unknown>>(Promise.resolve());
  const revision = useRef(0);
  const savedAnswers = useRef<Record<string, string>>({});
  const readOnly = error instanceof ApiError && error.status === 401;

  useEffect(() => {
    alive.current = true;
    let active = true;
    getChildQuestionnaire(child.id)
      .then((data) => {
        if (active) {
          setDraft(data);
          const loaded = Object.fromEntries(
            data.answers.map((answer) => [answer.question_key, answer.option]),
          );
          savedAnswers.current = loaded;
          setAnswers(loaded);
        }
      })
      .catch((e) => {
        if (active) {
          setError(e);
          onProblem(e);
        }
      });
    return () => {
      active = false;
      alive.current = false;
    };
  }, [child.id, onProblem]);
  useEffect(() => {
    if (!resumeGenerationId) return;
    let active = true;
    getChildGeneration(resumeGenerationId)
      .then((data) => {
        if (!active) return;
        if (data.child_id !== child.id) throw new ApiError(404, "Unavailable");
        setGeneration(data);
      })
      .catch((e) => {
        if (active) {
          setError(e);
          onProblem(e);
        }
      });
    return () => {
      active = false;
    };
  }, [resumeGenerationId, child.id, onProblem]);
  useEffect(() => {
    if (review) reviewHeading.current?.focus();
  }, [review]);
  useEffect(() => {
    if (!generation || childTerminal(generation.status) || pollPaused) return;
    let active = true;
    const timer = window.setTimeout(
      () => {
        getChildGeneration(generation.generation_id)
          .then((next) => {
            if (active) setGeneration(next);
          })
          .catch((e) => {
            if (active) {
              setError(e);
              onProblem(e);
              setPollPaused(true);
            }
          });
      },
      Math.max(500, generation.poll_after_ms ?? 2000),
    );
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [generation, pollPaused, onProblem]);

  function answer(key: string, value: string) {
    if (!draft) return;
    const next = { ...answers, [key]: value };
    setAnswers(next);
    setError(null);
    setSaving(true);
    onBusy(true);
    const currentRevision = ++revision.current;
    // Serialize writes so a slower earlier request cannot overwrite a later answer.
    saveQueue.current = saveQueue.current
      .catch(() => undefined)
      .then(() => saveChildAnswers(draft.session_id, next))
      .then((saved) => {
        savedAnswers.current = Object.fromEntries(
          saved.answers.map((answer) => [answer.question_key, answer.option]),
        );
        if (alive.current && currentRevision === revision.current) {
          setDraft(saved);
          setSaving(false);
          onBusy(false);
        }
      })
      .catch((e) => {
        if (alive.current && currentRevision === revision.current) {
          setError(e);
          setAnswers(savedAnswers.current);
          setSaving(false);
          onBusy(false);
          onProblem(e);
        }
        throw e;
      });
    void saveQueue.current.catch(() => undefined);
  }
  async function finish() {
    if (!draft || !consent || submitting || readOnly) return;
    setSubmitting(true);
    onBusy(true);
    setError(null);
    try {
      await saveQueue.current;
      let complete = draft;
      if (draft.status !== "completed") {
        completeKey.current ??= newChildKey("complete");
        complete = await completeChildQuestionnaire(
          draft.session_id,
          completeKey.current,
        );
        setDraft(complete);
      }
      reportKey.current ??= newChildKey("report");
      const accepted = await createChildReport(
        child.id,
        complete.session_id,
        reportKey.current,
      );
      setGeneration(accepted);
    } catch (e) {
      setError(e);
      onProblem(e);
    } finally {
      setSubmitting(false);
      onBusy(false);
    }
  }

  const missing =
    draft?.required_question_ids.filter((key) => !answers[key]) ?? [];
  return (
    <section className="child-panel" aria-labelledby="child-questions-heading">
      <div className="child-eyebrow">Выбран ребёнок: {child.display_name}</div>
      <h2 id="child-questions-heading">
        Ваши наблюдения: {child.display_name}
      </h2>
      <p className="child-muted">
        {timeLabels[child.birth_time_confidence]} · {child.age.age_years} лет{" "}
        {child.age.age_months} мес. · На дату {child.age.as_of_date}
      </p>
      {error != null && <ChildError error={error} />}
      {!draft && error == null && (
        <p role="status">Загружаем сохранённые ответы…</p>
      )}
      {generation ? (
        <div className="child-stack">
          <ChildGenerationCopy status={generation.status} />
          {generation.report_id && (
            <Link
              className="child-primary"
              href={`/reports/child/${encodeURIComponent(generation.report_id)}`}
            >
              Читать готовую часть
            </Link>
          )}
          <p className="child-muted">
            Сохраните ссылку на ход подготовки:{" "}
            <Link
              href={`/products/child?child_id=${encodeURIComponent(child.id)}&generation_id=${encodeURIComponent(generation.generation_id)}`}
            >
              Вернуться к подготовке
            </Link>
          </p>
          {pollPaused && (
            <button
              className="child-secondary"
              onClick={() => {
                setPollPaused(false);
                setError(null);
              }}
            >
              Проверить состояние снова
            </button>
          )}
        </div>
      ) : (
        draft && (
          <>
            <p>
              Здесь нет правильных ответов. Опишите то, что замечаете сейчас.
              Вопросы подобраны с учётом возраста на сервере; вы можете
              вернуться к сохранённому черновику.
            </p>
            {review || draft.status === "completed" ? (
              <div className="child-stack">
                <h3 ref={reviewHeading} tabIndex={-1}>
                  Проверьте перед отправкой: {child.display_name}
                </h3>
                <p className="child-muted">
                  После подтверждения ответы сохранятся отдельной неизменяемой
                  версией для этого отчёта.
                </p>
                <dl className="child-review">
                  {draft.questions.map((q) => (
                    <div key={q.key}>
                      <dt>{q.prompt}</dt>
                      <dd>
                        {q.options.find((o) => o.code === answers[q.key])
                          ?.label ?? "Ответ не указан"}
                      </dd>
                    </div>
                  ))}
                </dl>
                <label className="child-choice">
                  <input
                    type="checkbox"
                    checked={consent}
                    disabled={readOnly || submitting}
                    onChange={(e) => setConsent(e.target.checked)}
                  />
                  <span>
                    Подтверждаю ответы для ребёнка {child.display_name} и
                    понимаю, что отчёт помогает наблюдать за взаимодействием, а
                    не определяет личность ребёнка.
                  </span>
                </label>
                <div className="child-actions">
                  {draft.status !== "completed" && (
                    <button
                      className="child-secondary"
                      onClick={() => {
                        setReview(false);
                        setConsent(false);
                      }}
                    >
                      Изменить ответы
                    </button>
                  )}
                  <button
                    className="child-primary"
                    disabled={!consent || submitting || readOnly}
                    onClick={() => void finish()}
                  >
                    {submitting
                      ? "Сохраняем и начинаем…"
                      : "Подтвердить и создать отчёт"}
                  </button>
                </div>
              </div>
            ) : (
              <div className="child-stack">
                <div role="status" className="child-muted">
                  {saving
                    ? "Сохраняем…"
                    : error
                      ? "Не все изменения сохранены"
                      : "Сохранено"}
                </div>
                <p className="child-muted">
                  Отвечено:{" "}
                  {draft.questions.filter((q) => answers[q.key]).length} из{" "}
                  {draft.questions.length}
                </p>
                {draft.questions.map((q) => (
                  <fieldset
                    className="child-fieldset"
                    key={q.key}
                    disabled={readOnly}
                  >
                    <legend>
                      {q.prompt}
                      {q.required ? " *" : ""}
                    </legend>
                    {q.options.map((option) => (
                      <label className="child-choice" key={option.code}>
                        <input
                          type="radio"
                          name={`${draft.session_id}-${q.key}`}
                          value={option.code}
                          checked={answers[q.key] === option.code}
                          onChange={() => answer(q.key, option.code)}
                        />
                        <span>{option.label}</span>
                      </label>
                    ))}
                  </fieldset>
                ))}
                <p className="child-muted">
                  * Обязательный вопрос. Отправка начнётся только после проверки
                  ответов.
                </p>
                <button
                  className="child-primary"
                  disabled={saving || missing.length > 0 || error != null}
                  onClick={() => setReview(true)}
                >
                  Проверить ответы
                </button>
              </div>
            )}
          </>
        )
      )}
    </section>
  );
}
