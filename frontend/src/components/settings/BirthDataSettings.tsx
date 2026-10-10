"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  CalendarDays,
  Check,
  Clock3,
  Loader2,
  MapPin,
  RefreshCw,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ApiError } from "@/lib/api-client";
import {
  createBirthDataRefinement,
  getBirthDataRefinement,
  getBirthProfiles,
  getRefinementAvailability,
  searchBirthPlaces,
  type BirthProfile,
  type GeocodeSuggestion,
  type RefinementAvailability,
  type RefinementProgress,
} from "@/lib/api/birth-data-refinement";

const ACCURACY_LABELS = {
  exact: "Точное",
  approximate: "Примерное",
  unknown: "Неизвестно",
} as const;

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ru-RU", { dateStyle: "long" }).format(
    new Date(`${value}T00:00:00`),
  );
}

function formatMoment(value: string | null) {
  if (!value) return "";
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "long",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatTime(value: string | null) {
  return value ? value.slice(0, 5) : "Время не указано";
}

function errorCopy(error: unknown) {
  if (error instanceof ApiError) {
    const data = error.data as { code?: string } | undefined;
    if (data?.code === "birth_data_unchanged")
      return "Новые данные не отличаются от сохранённых.";
    if (data?.code === "birth_place_not_geocoded")
      return "Выберите место из предложенного списка.";
    return error.message;
  }
  return error instanceof Error
    ? error.message
    : "Не удалось выполнить действие.";
}

export function BirthDataSettings() {
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [availability, setAvailability] =
    useState<RefinementAvailability | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [birthTime, setBirthTime] = useState("");
  const [accuracy, setAccuracy] =
    useState<BirthProfile["birth_time_accuracy"]>("unknown");
  const [placeQuery, setPlaceQuery] = useState("");
  const [selectedPlace, setSelectedPlace] = useState<GeocodeSuggestion | null>(
    null,
  );
  const [suggestions, setSuggestions] = useState<GeocodeSuggestion[]>([]);
  const [searching, setSearching] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [progress, setProgress] = useState<RefinementProgress | null>(null);
  const [error, setError] = useState("");
  const idempotencyKey = useRef("");

  const profile = useMemo(
    () =>
      profiles.find((item) => item.id === selectedId) ?? profiles[0] ?? null,
    [profiles, selectedId],
  );

  useEffect(() => {
    let cancelled = false;
    getBirthProfiles()
      .then((response) => {
        if (cancelled) return;
        setProfiles(response.items);
        if (response.items[0]) setSelectedId(response.items[0].id);
      })
      .catch(
        (loadError: unknown) => !cancelled && setError(errorCopy(loadError)),
      )
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!profile) return;
    void getRefinementAvailability(profile.id)
      .then(setAvailability)
      .catch((loadError) => setError(errorCopy(loadError)));
  }, [profile]);

  useEffect(() => {
    if (!profile) return;
    const refresh = () =>
      void getRefinementAvailability(profile.id)
        .then(setAvailability)
        .catch((loadError) => setError(errorCopy(loadError)));
    const onVisibility = () => {
      if (document.visibilityState === "visible") refresh();
    };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [profile]);

  useEffect(() => {
    if (!profile || !editing) return;
    const queryChanged = placeQuery.trim() !== profile.birth_place;
    if (!queryChanged || placeQuery.trim().length < 2) {
      return;
    }
    const timer = window.setTimeout(() => {
      setSearching(true);
      searchBirthPlaces(placeQuery.trim())
        .then((response) => setSuggestions(response.items))
        .catch(() => setError("Не удалось загрузить подсказки места."))
        .finally(() => setSearching(false));
    }, 350);
    return () => window.clearTimeout(timer);
  }, [editing, placeQuery, profile]);

  useEffect(() => {
    if (
      !profile ||
      !progress ||
      !["queued", "processing"].includes(progress.status)
    )
      return;
    const timer = window.setInterval(() => {
      void getBirthDataRefinement(profile.id, progress.revision_id)
        .then(setProgress)
        .catch((pollError) => setError(errorCopy(pollError)));
    }, 3000);
    return () => window.clearInterval(timer);
  }, [profile, progress]);

  function beginEdit() {
    if (!profile) return;
    setBirthTime(profile.birth_time?.slice(0, 5) ?? "");
    setAccuracy(profile.birth_time_accuracy);
    setPlaceQuery(profile.birth_place);
    setSelectedPlace(null);
    setSuggestions([]);
    setError("");
    setConfirming(false);
    setEditing(true);
    idempotencyKey.current = crypto.randomUUID();
  }

  function cancelEdit() {
    setEditing(false);
    setConfirming(false);
    setError("");
  }

  const placeChanged = Boolean(
    profile && placeQuery.trim() !== profile.birth_place,
  );
  const timeValue = accuracy === "unknown" ? null : birthTime || null;
  const changed = Boolean(
    profile &&
    (timeValue !== (profile.birth_time?.slice(0, 5) ?? null) ||
      accuracy !== profile.birth_time_accuracy ||
      placeChanged),
  );
  const validTime = accuracy === "unknown" ? !birthTime : Boolean(birthTime);
  const validPlace =
    !placeChanged ||
    Boolean(selectedPlace && selectedPlace.display_name === placeQuery.trim());
  const canReview = changed && validTime && validPlace;

  async function submitRefinement() {
    if (!profile || !canReview) return;
    setSubmitting(true);
    setError("");
    const place = selectedPlace ?? {
      display_name: profile.birth_place,
      latitude: profile.latitude,
      longitude: profile.longitude,
      timezone: profile.timezone,
      selection_token: null,
    };
    try {
      const accepted = await createBirthDataRefinement(
        profile.id,
        {
          birth_time: timeValue,
          birth_time_accuracy: accuracy,
          birth_place: place.display_name,
          latitude: place.latitude,
          longitude: place.longitude,
          timezone: place.timezone,
          geocode_selection_token: place.selection_token,
        },
        idempotencyKey.current || crypto.randomUUID(),
      );
      setProfiles((items) =>
        items.map((item) =>
          item.id === profile.id
            ? {
                ...item,
                birth_time: timeValue,
                birth_time_accuracy: accuracy,
                birth_place: place.display_name,
                latitude: place.latitude,
                longitude: place.longitude,
                timezone: place.timezone,
              }
            : item,
        ),
      );
      setAvailability({
        profile_id: profile.id,
        can_refine: false,
        last_refined_at: new Date().toISOString(),
        next_available_at: accepted.next_available_at,
        retry_after_seconds: 86400,
      });
      setProgress({
        revision_id: accepted.revision_id,
        profile_id: accepted.profile_id,
        changed_fields: accepted.changed_fields,
        status: accepted.status,
        chart_id: null,
        report_id: null,
        error_code: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
      setEditing(false);
      setConfirming(false);
    } catch (submitError) {
      if (submitError instanceof ApiError && submitError.status === 429) {
        const data = submitError.data as {
          next_available_at?: string;
          retry_after_seconds?: number;
        };
        setAvailability({
          profile_id: profile.id,
          can_refine: false,
          last_refined_at: null,
          next_available_at: data.next_available_at ?? null,
          retry_after_seconds: data.retry_after_seconds ?? 0,
        });
        setEditing(false);
        setConfirming(false);
      }
      setError(errorCopy(submitError));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <section
        className="rounded-[24px] border border-border-default bg-surface/90 p-6"
        aria-live="polite"
      >
        <Loader2 className="mr-2 inline h-5 w-5 animate-spin text-accent-gold motion-reduce:animate-none" />
        Загружаем данные рождения…
      </section>
    );
  }

  if (!profile) {
    return (
      <section className="rounded-[24px] border border-border-default bg-surface/90 p-6">
        <h2 className="font-[family-name:var(--font-cormorant)] text-2xl text-text-primary">
          Данные рождения
        </h2>
        <p className="mt-3 text-base text-text-secondary">
          Сначала создайте профиль, чтобы управлять исходными данными расчёта.
        </p>
      </section>
    );
  }

  return (
    <section className="overflow-hidden rounded-[28px] border border-accent-gold/25 bg-[radial-gradient(circle_at_top_right,rgba(215,180,102,0.12),transparent_38%),#101724] shadow-elevated">
      <div className="border-b border-border-default p-5 sm:p-8">
        <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-accent-gold">
              Исходные данные расчёта
            </p>
            <h2 className="mt-2 font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-text-primary sm:text-4xl">
              Данные рождения
            </h2>
            <p className="mt-3 text-base leading-7 text-text-secondary">
              Изменение времени или места повлияет на натальную карту и отчёт.
              Текущий отчёт останется доступен, пока новый расчёт готовится.
            </p>
          </div>
          <span className="w-fit rounded-full border border-accent-gold/25 bg-accent-gold/10 px-3 py-2 text-sm text-accent-gold">
            {availability?.can_refine === false
              ? "Изменение временно недоступно"
              : "Можно уточнить"}
          </span>
        </div>

        {profiles.length > 1 && (
          <div className="mt-6 max-w-md">
            <label
              htmlFor="birth-profile"
              className="mb-2 block text-base font-medium text-text-primary"
            >
              Чьи данные показаны
            </label>
            <select
              id="birth-profile"
              value={profile.id}
              onChange={(event) => {
                setSelectedId(event.target.value);
                setEditing(false);
                setProgress(null);
              }}
              className="min-h-11 w-full rounded-xl border border-border-default bg-surface px-4 text-base text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
            >
              {profiles.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="p-5 sm:p-8">
        {error && (
          <div
            role="alert"
            className="mb-5 rounded-xl border border-red-300/30 bg-red-400/10 p-4 text-base text-red-100"
          >
            {error}
          </div>
        )}

        {progress ? (
          <ProgressState profile={profile} progress={progress} />
        ) : editing ? (
          <div className="motion-safe:animate-in motion-safe:fade-in motion-safe:slide-in-from-bottom-2 motion-reduce:transition-none">
            {!confirming ? (
              <div className="space-y-7">
                <fieldset className="space-y-4">
                  <legend className="text-lg font-semibold text-text-primary">
                    Время рождения
                  </legend>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label
                        htmlFor="birth-time"
                        className="mb-2 block text-base text-text-primary"
                      >
                        Время
                      </label>
                      <Input
                        id="birth-time"
                        type="time"
                        value={birthTime}
                        disabled={accuracy === "unknown"}
                        onChange={(event) => setBirthTime(event.target.value)}
                        className="min-h-11"
                      />
                    </div>
                    <div>
                      <label
                        htmlFor="birth-accuracy"
                        className="mb-2 block text-base text-text-primary"
                      >
                        Насколько точно известно время
                      </label>
                      <select
                        id="birth-accuracy"
                        value={accuracy}
                        onChange={(event) => {
                          const next = event.target
                            .value as BirthProfile["birth_time_accuracy"];
                          setAccuracy(next);
                          if (next === "unknown") setBirthTime("");
                        }}
                        className="min-h-11 w-full rounded-xl border border-border-default bg-surface px-4 text-base text-text-primary outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                      >
                        <option value="exact">
                          Точное — известно по документам
                        </option>
                        <option value="approximate">
                          Примерное — возможна небольшая погрешность
                        </option>
                        <option value="unknown">
                          Неизвестно — время не используется как точное
                        </option>
                      </select>
                    </div>
                  </div>
                </fieldset>

                <fieldset className="space-y-3">
                  <legend className="text-lg font-semibold text-text-primary">
                    Место рождения
                  </legend>
                  <label
                    htmlFor="birth-place"
                    className="block text-base text-text-primary"
                  >
                    Начните вводить город и выберите подсказку
                  </label>
                  <div className="relative">
                    <Input
                      id="birth-place"
                      value={placeQuery}
                      onChange={(event) => {
                        setPlaceQuery(event.target.value);
                        setSelectedPlace(null);
                        setSuggestions([]);
                        setSearching(false);
                      }}
                      aria-describedby="birth-place-help"
                      aria-invalid={placeChanged && !validPlace}
                      className="min-h-11"
                    />
                    {searching && (
                      <Loader2 className="absolute right-3 top-3 h-5 w-5 animate-spin text-accent-gold motion-reduce:animate-none" />
                    )}
                  </div>
                  <p
                    id="birth-place-help"
                    className="text-sm leading-6 text-text-muted"
                  >
                    Координаты и часовой пояс определятся автоматически после
                    выбора.
                  </p>
                  {suggestions.length > 0 && (
                    <ul
                      className="max-h-64 overflow-y-auto rounded-xl border border-border-default bg-surface p-2"
                      aria-label="Подсказки места рождения"
                    >
                      {suggestions.map((item) => (
                        <li key={`${item.display_name}-${item.latitude}`}>
                          <button
                            type="button"
                            className="min-h-11 w-full rounded-lg px-3 py-2 text-left text-base text-text-primary hover:bg-surface-elevated focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring"
                            onClick={() => {
                              setSelectedPlace(item);
                              setPlaceQuery(item.display_name);
                              setSuggestions([]);
                            }}
                          >
                            {item.display_name}
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                  {selectedPlace && (
                    <p className="flex items-center gap-2 text-sm text-emerald-200">
                      <Check className="h-4 w-4" /> Место подтверждено
                    </p>
                  )}
                </fieldset>

                <div className="flex flex-col-reverse gap-3 sm:flex-row">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={cancelEdit}
                    className="min-h-11"
                  >
                    Отменить
                  </Button>
                  <Button
                    type="button"
                    disabled={!canReview}
                    onClick={() => setConfirming(true)}
                    className="min-h-11"
                  >
                    Проверить изменения
                  </Button>
                </div>
              </div>
            ) : (
              <ReviewChanges
                profile={profile}
                nextTime={timeValue}
                nextAccuracy={accuracy}
                nextPlace={selectedPlace?.display_name ?? profile.birth_place}
                submitting={submitting}
                onBack={() => setConfirming(false)}
                onSubmit={() => void submitRefinement()}
              />
            )}
          </div>
        ) : (
          <>
            <dl className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              <SummaryItem
                icon={<CalendarDays />}
                label="Дата рождения"
                value={formatDate(profile.birth_date)}
                note="В этом разделе дата не изменяется"
              />
              <SummaryItem
                icon={<Clock3 />}
                label="Время рождения"
                value={formatTime(profile.birth_time)}
              />
              <SummaryItem
                icon={<RefreshCw />}
                label="Точность"
                value={ACCURACY_LABELS[profile.birth_time_accuracy]}
              />
              <SummaryItem
                icon={<MapPin />}
                label="Место рождения"
                value={profile.birth_place}
              />
            </dl>

            {availability?.can_refine === false &&
              availability.next_available_at && (
                <div className="mt-6 rounded-xl border border-sky-300/20 bg-sky-300/5 p-4 text-base leading-7 text-sky-50">
                  Следующее уточнение будет доступно{" "}
                  {formatMoment(availability.next_available_at)}.
                </div>
              )}

            <div className="mt-7 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <p className="max-w-2xl text-base leading-7 text-text-secondary">
                Новый расчёт создаётся без повторной оплаты. Имя и пароль можно
                менять независимо.
              </p>
              <Button
                type="button"
                onClick={beginEdit}
                disabled={availability?.can_refine === false}
                className="min-h-11 shrink-0"
              >
                Уточнить данные
              </Button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}

function SummaryItem({
  icon,
  label,
  value,
  note,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="min-w-0 border-l border-border-default pl-4">
      <div className="mb-2 flex items-center gap-2 text-accent-gold [&_svg]:h-4 [&_svg]:w-4">
        {icon}
        <dt className="text-sm font-medium uppercase tracking-[0.08em]">
          {label}
        </dt>
      </div>
      <dd className="break-words text-base font-medium leading-7 text-text-primary">
        {value}
      </dd>
      {note && <p className="mt-1 text-sm leading-5 text-text-muted">{note}</p>}
    </div>
  );
}

function ReviewChanges({
  profile,
  nextTime,
  nextAccuracy,
  nextPlace,
  submitting,
  onBack,
  onSubmit,
}: {
  profile: BirthProfile;
  nextTime: string | null;
  nextAccuracy: BirthProfile["birth_time_accuracy"];
  nextPlace: string;
  submitting: boolean;
  onBack: () => void;
  onSubmit: () => void;
}) {
  const rows = [
    {
      label: "Время",
      before: formatTime(profile.birth_time),
      after: formatTime(nextTime),
      changed: (profile.birth_time?.slice(0, 5) ?? null) !== nextTime,
    },
    {
      label: "Точность",
      before: ACCURACY_LABELS[profile.birth_time_accuracy],
      after: ACCURACY_LABELS[nextAccuracy],
      changed: profile.birth_time_accuracy !== nextAccuracy,
    },
    {
      label: "Место",
      before: profile.birth_place,
      after: nextPlace,
      changed: profile.birth_place !== nextPlace,
    },
  ].filter((row) => row.changed);
  return (
    <div className="space-y-6" aria-live="polite">
      <div>
        <h3 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-text-primary">
          Проверьте изменения
        </h3>
        <p className="mt-2 text-base leading-7 text-text-secondary">
          После сохранения начнётся новый расчёт. Текущий отчёт останется
          доступен до готовности обновлённого.
        </p>
      </div>
      <div className="overflow-hidden rounded-xl border border-border-default">
        <div className="grid grid-cols-[minmax(5rem,.7fr)_1fr_1fr] bg-surface-elevated px-3 py-3 text-sm text-text-muted">
          <span>Поле</span>
          <span>Было</span>
          <span>Стало</span>
        </div>
        {rows.map((row) => (
          <div
            key={row.label}
            className="grid grid-cols-[minmax(5rem,.7fr)_1fr_1fr] gap-2 border-t border-border-default px-3 py-4 text-sm leading-6"
          >
            <strong className="text-text-primary">{row.label}</strong>
            <span className="break-words text-text-muted">{row.before}</span>
            <span className="break-words text-accent-gold">{row.after}</span>
          </div>
        ))}
      </div>
      <div className="flex flex-col-reverse gap-3 sm:flex-row">
        <Button
          type="button"
          variant="outline"
          onClick={onBack}
          className="min-h-11"
        >
          Назад
        </Button>
        <Button
          type="button"
          onClick={onSubmit}
          disabled={submitting}
          className="min-h-11"
        >
          {submitting && (
            <Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
          )}
          Сохранить и обновить расчёт
        </Button>
      </div>
    </div>
  );
}

function ProgressState({
  profile,
  progress,
}: {
  profile: BirthProfile;
  progress: RefinementProgress;
}) {
  const content = {
    queued: [
      "Данные сохранены",
      "Расчёт поставлен в очередь. Сохранённый отчёт по-прежнему доступен.",
    ],
    processing: [
      "Обновляем натальную карту",
      "Новый расчёт выполняется в фоне. Остальными настройками можно пользоваться.",
    ],
    deterministic_ready: [
      "Обновлённый отчёт уже доступен",
      "Основной расчёт готов, текстовые пояснения могут ещё дополняться.",
    ],
    ready: ["Отчёт обновлён", "Новая версия расчёта и пояснений готова."],
    failed: [
      "Не удалось завершить обновление",
      "Сохранённый ранее отчёт не потерян. Повторная оплата не нужна; при необходимости обратитесь в поддержку.",
    ],
  }[progress.status];
  const updated =
    progress.status === "deterministic_ready" || progress.status === "ready";
  return (
    <div
      className="rounded-2xl border border-border-default bg-scrim p-5 sm:p-6"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        {["queued", "processing"].includes(progress.status) ? (
          <Loader2 className="mt-1 h-5 w-5 shrink-0 animate-spin text-accent-gold motion-reduce:animate-none" />
        ) : (
          <Check className="mt-1 h-5 w-5 shrink-0 text-accent-gold" />
        )}
        <div>
          <h3 className="text-xl font-semibold text-text-primary">
            {content[0]}
          </h3>
          <p className="mt-2 text-base leading-7 text-text-secondary">
            {content[1]}
          </p>
        </div>
      </div>
      <Button asChild className="mt-5 min-h-11">
        <Link href={`/report/v2/${profile.id}`}>
          {updated ? "Открыть обновлённый отчёт" : "Открыть текущий отчёт"}
        </Link>
      </Button>
    </div>
  );
}
