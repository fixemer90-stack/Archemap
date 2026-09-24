"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Briefcase, Check, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  completeCareerQuestionnaire,
  createCareerReport,
  getCareerGeneration,
  getCurrentCareerQuestionnaire,
  saveCareerQuestionnaire,
  type CareerAnswers,
  type CareerGenerationStatus,
  type CareerQuestion,
  type CareerQuestionnaire,
} from "@/lib/api/career";
import { ApiError } from "@/lib/api-client";

interface Profile {
  id: string;
  name: string;
  birth_date: string;
  birth_place: string;
}

const QUESTION_LABELS: Record<string, string> = {
  leadership_responsibility:
    "Насколько вам близка ответственность за направление работы?",
  people_management_motivation:
    "Насколько вам хочется регулярно управлять людьми?",
  autonomy_importance: "Насколько важна самостоятельность в решениях?",
  risk_preference: "Какой уровень профессионального риска для вас комфортен?",
  preferred_track: "Какой вектор развития сейчас ближе?",
  current_activity: "Чем вы занимаетесь сейчас?",
  experience_years: "Сколько лет релевантного опыта у вас есть?",
  change_goal: "Что вы хотите изменить в работе?",
  collaboration_preference: "Насколько вам важна постоянная работа с командой?",
  current_constraints: "Какие ограничения важно учитывать?",
};

const CHOICES: Record<string, Array<{ value: string; label: string }>> = {
  risk_preference: [
    { value: "stable", label: "Стабильность и предсказуемость" },
    { value: "balanced", label: "Баланс устойчивости и эксперимента" },
    { value: "high", label: "Готовность к высокой неопределённости" },
  ],
  preferred_track: [
    { value: "expert", label: "Экспертный путь" },
    { value: "manager", label: "Управленческий путь" },
    { value: "entrepreneur", label: "Предпринимательский путь" },
    { value: "unknown", label: "Пока хочу исследовать варианты" },
  ],
};

function newIdempotencyKey(prefix: string) {
  return `${prefix}:${crypto.randomUUID()}`;
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    return "Сессия завершилась. Войдите снова — сохранённые ответы останутся в профиле.";
  }
  if (error instanceof ApiError && typeof error.message === "string")
    return error.message;
  return error instanceof Error
    ? error.message
    : "Не удалось продолжить. Попробуйте ещё раз.";
}

export default function CareerProductPage() {
  const searchParams = useSearchParams();
  const deepLinkedProfileId = searchParams.get("profileId");
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null);
  const [questionnaire, setQuestionnaire] =
    useState<CareerQuestionnaire | null>(null);
  const [answers, setAnswers] = useState<CareerAnswers>({});
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [consented, setConsented] = useState(false);
  const [locked, setLocked] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generation, setGeneration] = useState<CareerGenerationStatus | null>(
    null,
  );
  const completionKey = useRef<string | null>(null);
  const generationKey = useRef<string | null>(null);
  const pollAttempts = useRef(0);
  const deepLinkOpened = useRef(false);

  const openQuestionnaire = useCallback(async (profile: Profile) => {
    setSelectedProfile(profile);
    setQuestionnaire(null);
    setGeneration(null);
    setLocked(false);
    setError(null);
    setStep(0);
    setConsented(false);
    try {
      const draft = await getCurrentCareerQuestionnaire(profile.id);
      setQuestionnaire(draft);
      setAnswers(draft.answers ?? {});
      setSaved(true);
    } catch (loadError) {
      if (loadError instanceof ApiError && loadError.status === 402)
        setLocked(true);
      setError(
        loadError instanceof ApiError && loadError.status === 404
          ? "Для профиля ещё нет готовой натальной карты. Сначала постройте основной отчёт."
          : errorMessage(loadError),
      );
    }
  }, []);

  useEffect(() => {
    async function loadProfiles() {
      try {
        const response = await fetch("/api/v1/profiles", {
          credentials: "include",
        });
        if (!response.ok) throw new Error("Не удалось загрузить профили");
        const data = (await response.json()) as { items?: Profile[] };
        const loadedProfiles = data.items ?? [];
        setProfiles(loadedProfiles);
        const preselectedProfile = loadedProfiles.find(
          (profile) => profile.id === deepLinkedProfileId,
        );
        if (preselectedProfile && !deepLinkOpened.current) {
          deepLinkOpened.current = true;
          await openQuestionnaire(preselectedProfile);
        }
      } catch (loadError) {
        setError(errorMessage(loadError));
      } finally {
        setLoading(false);
      }
    }
    void loadProfiles();
  }, [deepLinkedProfileId, openQuestionnaire]);

  useEffect(() => {
    if (
      !generation ||
      ["ready", "narrative_failed", "failed"].includes(generation.status)
    )
      return;
    const timer = window.setInterval(async () => {
      try {
        const next = await getCareerGeneration(generation.generation_id);
        setGeneration(next);
        pollAttempts.current += 1;
        if (pollAttempts.current >= 120) {
          window.clearInterval(timer);
          setError(
            "Генерация продолжается дольше обычного. Прогресс сохранён — можно вернуться позже.",
          );
        }
      } catch (pollError) {
        window.clearInterval(timer);
        setError(errorMessage(pollError));
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [generation]);

  const questions = useMemo(
    () => questionnaire?.questions ?? [],
    [questionnaire?.questions],
  );
  const currentQuestion = questions[step];
  const missingRequired = useMemo(
    () =>
      questions
        .filter((question) => question.required)
        .map((question) => question.key)
        .filter(
          (key) =>
            answers[key] === undefined ||
            answers[key] === null ||
            answers[key] === "",
        ),
    [answers, questions],
  );

  async function persistDraft(nextAnswers = answers) {
    if (!questionnaire || questionnaire.status === "completed")
      return questionnaire;
    setSaving(true);
    setSaved(false);
    try {
      const next = await saveCareerQuestionnaire(
        questionnaire.session_id,
        nextAnswers,
      );
      setQuestionnaire({ ...questionnaire, ...next });
      setSaved(true);
      return next;
    } finally {
      setSaving(false);
    }
  }

  function updateAnswer(question: CareerQuestion, value: string | number) {
    setAnswers((current) => ({ ...current, [question.key]: value }));
    setSaved(false);
    setError(null);
  }

  async function move(direction: -1 | 1) {
    if (!currentQuestion) return;
    const value = answers[currentQuestion.key];
    if (
      direction > 0 &&
      currentQuestion.required &&
      (value === undefined || value === null || value === "")
    ) {
      setError("Ответьте на обязательный вопрос, чтобы продолжить.");
      return;
    }
    try {
      await persistDraft();
      setStep((current) =>
        Math.max(0, Math.min(questions.length - 1, current + direction)),
      );
    } catch (saveError) {
      setError(errorMessage(saveError));
    }
  }

  async function finishQuestionnaire() {
    if (!questionnaire || !selectedProfile || submitting) return;
    if (missingRequired.length) {
      const firstMissing = questions.findIndex(
        (question) => question.key === missingRequired[0],
      );
      if (firstMissing >= 0) setStep(firstMissing);
      setError(
        "Заполните все обязательные вопросы. Первый пропущенный вопрос уже открыт.",
      );
      return;
    }
    if (!consented) {
      setError("Подтвердите согласие с использованием ответов для отчёта.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await persistDraft();
      if (questionnaire.status !== "completed") {
        completionKey.current ??= newIdempotencyKey("career-questionnaire");
        await completeCareerQuestionnaire(
          questionnaire.session_id,
          completionKey.current,
        );
      }
      generationKey.current ??= newIdempotencyKey("career-report");
      const accepted = await createCareerReport(
        selectedProfile.id,
        generationKey.current,
      );
      const initial = await getCareerGeneration(accepted.generation_id);
      setGeneration(initial);
      pollAttempts.current = 0;
    } catch (submitError) {
      setError(errorMessage(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8 pb-16">
      <header className="space-y-3">
        <p className="text-xs uppercase tracking-[0.24em] text-[#CFA75A]">
          Astrotype Career
        </p>
        <h1 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-[#F6F1E8]">
          Как вы работаете, выбираете и развиваетесь
        </h1>
        <p className="max-w-3xl text-sm leading-7 text-[#D8DCE8]">
          Отчёт объясняет профессиональную механику и условия, в которых ваши
          склонности раскрываются. Он не назначает профессию и не обещает
          результат вместо вашего решения.
        </p>
      </header>

      <section className="glass grid gap-4 p-6 sm:grid-cols-2">
        {[
          "Практические сильные стороны без рейтинга «хорошо/плохо»",
          "Рабочий ритм, решения, лидерство и способы влияния",
          "Поддерживающая среда и условия, которые снижают эффективность",
          "Несколько семейств ролей и карьерных траекторий — всегда условно",
        ].map((item) => (
          <div
            key={item}
            className="flex gap-3 text-sm leading-6 text-[#D8DCE8]"
          >
            <span className="text-[#CFA75A]">✦</span>
            <span>{item}</span>
          </div>
        ))}
      </section>

      <p className="rounded-xl border border-[#CFA75A]/20 bg-[#CFA75A]/5 p-4 text-sm text-[#E9E1D2]">
        Ответы уточняют, как врождённые склонности применяются в вашем реальном
        контексте. Они не меняют и не «подгоняют» натальную карту.
      </p>

      {error && (
        <div
          role="alert"
          aria-live="assertive"
          className="rounded-xl border border-red-400/30 bg-red-500/10 p-4 text-sm text-red-100"
        >
          {error}
        </div>
      )}

      {!selectedProfile && (
        <section className="space-y-4" aria-labelledby="career-profile-heading">
          <h2
            id="career-profile-heading"
            className="text-xl font-semibold text-[#F6F1E8]"
          >
            Выберите профиль
          </h2>
          {loading ? (
            <p className="text-sm text-[#D8DCE8]">Загружаем профили…</p>
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {profiles.map((profile) => (
                <button
                  key={profile.id}
                  type="button"
                  onClick={() => void openQuestionnaire(profile)}
                  className="glass space-y-3 p-5 text-left transition hover:border-[#CFA75A]/50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#CFA75A]"
                >
                  <div className="flex items-center justify-between">
                    <strong className="text-[#F6F1E8]">
                      {profile.name || "Без имени"}
                    </strong>
                    <Briefcase className="h-4 w-4 text-[#CFA75A]" />
                  </div>
                  <p className="text-xs text-[#AEB4C4]">
                    {profile.birth_date} · {profile.birth_place}
                  </p>
                  <span className="inline-flex items-center text-sm text-[#E6C77D]">
                    Продолжить <ArrowRight className="ml-1 h-4 w-4" />
                  </span>
                </button>
              ))}
            </div>
          )}
          {!loading && profiles.length === 0 && (
            <Button asChild>
              <Link href="/register">Создать профиль</Link>
            </Button>
          )}
        </section>
      )}

      {locked && (
        <section className="glass space-y-4 p-6" aria-live="polite">
          <h2 className="text-xl font-semibold text-[#F6F1E8]">
            Career входит в Plus
          </h2>
          <p className="text-sm leading-6 text-[#D8DCE8]">
            Доступ проверен на сервере. Защищённые расчёты и предварительный
            отчёт не показываются без активного доступа.
          </p>
          <Button asChild>
            <Link href="/subscriptions">Посмотреть Plus</Link>
          </Button>
        </section>
      )}

      {selectedProfile && questionnaire && !generation && currentQuestion && (
        <section
          className="glass space-y-6 p-5 sm:p-8"
          aria-labelledby="questionnaire-heading"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs text-[#AEB4C4]">
                Профиль: {selectedProfile.name}
              </p>
              <h2
                id="questionnaire-heading"
                className="text-xl font-semibold text-[#F6F1E8]"
              >
                Профессиональный контекст
              </h2>
            </div>
            <div className="text-right text-xs text-[#AEB4C4]">
              <p>
                {step + 1} из {questions.length}
              </p>
              <p aria-live="polite">
                {saving
                  ? "Сохраняем…"
                  : saved
                    ? "Сохранено"
                    : "Есть несохранённые изменения"}
              </p>
            </div>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full bg-[#CFA75A] transition-all"
              style={{ width: `${((step + 1) / questions.length) * 100}%` }}
            />
          </div>
          <QuestionField
            question={currentQuestion}
            value={answers[currentQuestion.key]}
            onChange={(value) => updateAnswer(currentQuestion, value)}
          />
          {step === questions.length - 1 && (
            <label className="flex items-start gap-3 rounded-xl border border-white/10 p-4 text-sm leading-6 text-[#D8DCE8]">
              <input
                required
                type="checkbox"
                className="mt-1"
                checked={consented}
                onChange={(event) => setConsented(event.target.checked)}
              />{" "}
              <span>
                Я понимаю, что ответы используются для уточнения
                профессионального контекста и сохраняются вместе с версией
                отчёта.
              </span>
            </label>
          )}
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
            <Button
              variant="outline"
              onClick={() => void move(-1)}
              disabled={step === 0 || saving}
            >
              <ArrowLeft className="mr-1 h-4 w-4" />
              Назад
            </Button>
            {step < questions.length - 1 ? (
              <Button onClick={() => void move(1)} disabled={saving}>
                Далее
                <ArrowRight className="ml-1 h-4 w-4" />
              </Button>
            ) : (
              <Button
                onClick={() => void finishQuestionnaire()}
                disabled={submitting || saving}
              >
                {submitting ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Check className="mr-2 h-4 w-4" />
                )}
                Создать отчёт
              </Button>
            )}
          </div>
        </section>
      )}

      {generation && (
        <section className="glass space-y-5 p-6" aria-live="polite">
          <div className="flex items-center gap-3">
            <Loader2
              className={`h-5 w-5 text-[#CFA75A] ${generation.status === "ready" ? "" : "animate-spin"}`}
            />
            <div>
              <h2 className="text-xl font-semibold text-[#F6F1E8]">
                Отчёт собирается по разделам
              </h2>
              <p className="text-sm text-[#D8DCE8]">
                Расчёт:{" "}
                {generation.deterministic_status === "ready"
                  ? "готов"
                  : "в процессе"}
                . Текст: {generation.progress.ready} из{" "}
                {generation.progress.total || 10} разделов.
              </p>
            </div>
          </div>
          {generation.deterministic_status === "ready" &&
            generation.report_id && (
              <div className="rounded-xl border border-emerald-300/20 bg-emerald-400/5 p-4">
                <p className="text-sm leading-6 text-[#D8DCE8]">
                  Базовый профессиональный профиль уже готов. Можно читать его,
                  пока пояснения продолжают появляться.
                </p>
                <Button className="mt-3" asChild>
                  <Link
                    href={`/products/career/report/${generation.report_id}`}
                  >
                    Открыть отчёт
                  </Link>
                </Button>
              </div>
            )}
          {generation.narrative_status === "partial_failure" && (
            <p className="text-sm text-amber-100">
              Часть пояснений временно недоступна. Расчёт и готовые разделы
              сохранены.
            </p>
          )}
        </section>
      )}

      <Button variant="outline" asChild>
        <Link href="/dashboard">
          <ArrowLeft className="mr-1 h-4 w-4" />К обзору продуктов
        </Link>
      </Button>
    </div>
  );
}

function QuestionField({
  question,
  value,
  onChange,
}: {
  question: CareerQuestion;
  value: string | number | null | undefined;
  onChange: (value: string | number) => void;
}) {
  const label = QUESTION_LABELS[question.key] ?? question.key;
  if (question.answer_type === "scale_1_5")
    return (
      <fieldset className="space-y-4">
        <legend className="text-lg font-medium text-[#F6F1E8]">{label}</legend>
        <div className="grid grid-cols-5 gap-2">
          {[1, 2, 3, 4, 5].map((score) => (
            <button
              key={score}
              type="button"
              aria-pressed={value === score}
              onClick={() => onChange(score)}
              className={`rounded-xl border p-3 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#CFA75A] ${value === score ? "border-[#CFA75A] bg-[#CFA75A]/15 text-[#F6F1E8]" : "border-white/10 text-[#D8DCE8]"}`}
            >
              {score}
            </button>
          ))}
        </div>
        <div className="flex justify-between text-xs text-[#AEB4C4]">
          <span>Совсем не близко</span>
          <span>Очень близко</span>
        </div>
      </fieldset>
    );
  if (question.answer_type === "choice")
    return (
      <fieldset className="space-y-4">
        <legend className="text-lg font-medium text-[#F6F1E8]">{label}</legend>
        <div className="grid gap-3">
          {(CHOICES[question.key] ?? []).map((choice) => (
            <button
              key={choice.value}
              type="button"
              aria-pressed={value === choice.value}
              onClick={() => onChange(choice.value)}
              className={`rounded-xl border p-4 text-left text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#CFA75A] ${value === choice.value ? "border-[#CFA75A] bg-[#CFA75A]/15 text-[#F6F1E8]" : "border-white/10 text-[#D8DCE8]"}`}
            >
              {choice.label}
            </button>
          ))}
        </div>
      </fieldset>
    );
  return (
    <label className="block space-y-3">
      <span className="text-lg font-medium text-[#F6F1E8]">{label}</span>
      <Input
        aria-label={label}
        type={question.answer_type === "integer" ? "number" : "text"}
        min={question.answer_type === "integer" ? 0 : undefined}
        max={question.answer_type === "integer" ? 60 : undefined}
        maxLength={question.answer_type === "bounded_text" ? 500 : undefined}
        value={value ?? ""}
        onChange={(event) =>
          onChange(
            question.answer_type === "integer"
              ? Number(event.target.value)
              : event.target.value,
          )
        }
      />
    </label>
  );
}
