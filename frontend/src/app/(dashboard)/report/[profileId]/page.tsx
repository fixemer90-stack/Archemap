"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { NatalChart } from "@/components/chart/natal-chart";
import { SocionicsResult } from "@/components/chart/socionics-result";
import { ApiError } from "@/lib/api-client";
import { fetchReportApiData } from "@/lib/api/report";
import {
  toReportViewModel,
  type ReportViewModel as ReportData,
} from "@/lib/report/view-model";
import { useAuthStore } from "@/stores/auth-store";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// ── Glossary ───────────────────────────────────────────────────────
interface GlossaryEntry {
  title: string;
  description: string;
  example: string;
}

const GLOSSARY: Record<string, GlossaryEntry> = {
  "Натальная карта": {
    title: "Натальная карта",
    description:
      "Снимок положения планет в момент и месте рождения. Это исходные данные, из которых строится интерпретация.",
    example:
      "Если карта показывает сильную землю, мы объясняем это как потребность в структуре, практике и проверяемых результатах.",
  },
  Аспект: {
    title: "Аспект",
    description:
      "Связь между двумя планетами. Она показывает, где разные качества поддерживают или напрягают друг друга.",
    example:
      "Напряжённый аспект может описывать внутренний конфликт, а гармоничный — естественную опору.",
  },
  Орб: {
    title: "Орб",
    description:
      "Насколько точно две планеты образуют аспект. Чем меньше орб, тем сильнее связь.",
    example:
      "Орб 0.8° обычно важнее, чем орб 6°, поэтому такие факторы поднимаются выше в evidence.",
  },
  "Model A": {
    title: "Model A",
    description:
      "Соционическая модель расположения функций. Она нужна для проверки типологической гипотезы, но не обязательна для чтения отчёта.",
    example:
      "Если вам не интересна типология, можно читать только практические выводы и пропустить технический блок.",
  },
  Confidence: {
    title: "Confidence",
    description:
      "Уверенность системы в выводе. Это не истина в процентах, а качество совпадения признаков.",
    example:
      "Средняя уверенность означает, что вывод полезен как гипотеза, но его стоит читать мягче.",
  },
};

function TermHelp({ term }: { term: keyof typeof GLOSSARY }) {
  const [isOpen, setIsOpen] = useState(false);
  const entry = GLOSSARY[term];

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-1 border-b border-dotted border-primary/70 text-primary underline-offset-4 hover:text-primary/80"
        aria-label={`Пояснить термин: ${term}`}
      >
        {term}
        <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border text-[10px] leading-none">
          ?
        </span>
      </button>
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-end bg-black/50 p-0 sm:items-center sm:justify-center sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-labelledby={`glossary-${term}`}
        >
          <div className="w-full rounded-t-2xl border bg-background p-6 shadow-lg sm:max-w-lg sm:rounded-2xl">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id={`glossary-${term}`} className="text-xl font-semibold">
                  {entry.title}
                </h2>
                <p className="mt-3 text-sm leading-6 text-muted-foreground">
                  {entry.description}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="rounded-md border px-3 py-1 text-sm hover:bg-muted"
              >
                Закрыть
              </button>
            </div>
            <div className="mt-4 rounded-lg bg-muted p-4 text-sm leading-6">
              <span className="font-medium">Пример: </span>
              {entry.example}
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ── Report Header ──────────────────────────────────────────────────
function ReportHeader({ profile }: { profile: ReportData["profile"] }) {
  const timeLabel =
    profile.birth_time_accuracy === "exact"
      ? "точное время"
      : profile.birth_time_accuracy === "approximate"
        ? "приблизительное время"
        : "время неизвестно";

  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader>
        <CardDescription>Self-report</CardDescription>
        <CardTitle className="text-3xl">{profile.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground">Дата рождения</dt>
            <dd className="font-medium">{profile.birth_date}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Время</dt>
            <dd className="font-medium">
              {profile.birth_time || "Не указано"} · {timeLabel}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Место</dt>
            <dd className="font-medium">{profile.birth_place}</dd>
          </div>
        </dl>
        {profile.birth_time_accuracy !== "exact" && (
          <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm leading-6">
            Время рождения влияет на дома и часть выводов. Если время неточное,
            интерпретация по домам и Асценденту читается как гипотеза.
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function ExecutiveSummary({ summary }: { summary: string[] }) {
  return (
    <SectionCard
      title="Главное о вас"
      description="Сначала — смысл, а не схемы и проценты. Это короткая выжимка отчёта простым языком."
    >
      <div className="grid gap-3">
        {summary.map((item) => (
          <div key={item} className="rounded-lg bg-muted p-4 leading-7">
            {item}
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

function AstrologyFoundation({
  astrology,
}: {
  astrology: ReportData["astrology"];
}) {
  return (
    <SectionCard
      title="Астрологическая основа"
      description="Сначала разбираем карту: из каких факторов появляются выводы. Архетипы и соционика идут позже."
    >
      <div className="mb-5 leading-7 text-muted-foreground">
        <TermHelp term="Натальная карта" /> — это база расчёта. Ниже не весь
        технический список, а только главные факторы, которые помогают понять
        логику отчёта.
      </div>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Солнце</div>
          <div className="mt-2 font-medium">{astrology.sun}</div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Луна</div>
          <div className="mt-2 font-medium">{astrology.moon}</div>
        </div>
        <div className="rounded-lg border p-4">
          <div className="text-sm text-muted-foreground">Асцендент</div>
          <div className="mt-2 font-medium">{astrology.ascendant}</div>
        </div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="rounded-lg bg-muted p-4 leading-7">
          <div className="font-medium">Стихии</div>
          <p className="mt-2 text-sm text-muted-foreground">
            {astrology.dominant_elements}
          </p>
        </div>
        <div className="rounded-lg bg-muted p-4 leading-7">
          <div className="font-medium">Модальности</div>
          <p className="mt-2 text-sm text-muted-foreground">
            {astrology.modalities}
          </p>
        </div>
      </div>
      <div className="mt-5">
        <div className="font-medium">Ключевые связи карты</div>
        <div className="mt-2 text-sm leading-6 text-muted-foreground">
          <TermHelp term="Аспект" /> показывает связь между факторами, а{" "}
          <TermHelp term="Орб" /> — насколько эта связь точная.
        </div>
        <ul className="mt-3 grid gap-2">
          {astrology.key_aspects.map((aspect) => (
            <li
              key={aspect}
              className="rounded-md border p-3 text-sm leading-6"
            >
              {aspect}
            </li>
          ))}
        </ul>
      </div>
    </SectionCard>
  );
}

function Manifestations({ items }: { items: ReportData["manifestations"] }) {
  return (
    <SectionCard
      title="Как это проявляется"
      description="Переводим карту в жизненные ситуации: мышление, эмоции, общение и работа."
    >
      <div className="grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <div key={item.title} className="rounded-lg border p-4">
            <h3 className="font-semibold">{item.title}</h3>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {item.text}
            </p>
            <div className="mt-3 rounded-md bg-primary/5 p-3 text-sm leading-6">
              <span className="font-medium">Что помогает: </span>
              {item.advice}
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  );
}

function PracticalRecommendations({ items }: { items: string[] }) {
  return (
    <SectionCard
      title="Практические рекомендации"
      description="Эта часть важнее процентов: что реально можно попробовать и применить."
    >
      <ol className="grid gap-3">
        {items.map((item, index) => (
          <li
            key={item}
            className="flex gap-3 rounded-lg bg-muted p-4 leading-7"
          >
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
              {index + 1}
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ol>
    </SectionCard>
  );
}

function ArchetypeProfile({
  archetype,
}: {
  archetype: ReportData["archetype"];
}) {
  return (
    <SectionCard
      title="Архетипический профиль"
      description="Архетип — это запоминающаяся модель поведения, а не диагноз и не жёсткий ярлык."
    >
      <div className="rounded-lg border p-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <div className="text-sm text-muted-foreground">
              Основной архетип
            </div>
            <h3 className="mt-1 text-2xl font-semibold">{archetype.name}</h3>
          </div>
          <div className="rounded-full bg-primary/10 px-3 py-1 text-sm text-primary">
            {archetype.confidence_label}
          </div>
        </div>
        <p className="mt-4 leading-7 text-muted-foreground">{archetype.text}</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-lg bg-muted p-4">
            <div className="font-medium">Сильная сторона</div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {archetype.light}
            </p>
          </div>
          <div className="rounded-lg bg-muted p-4">
            <div className="font-medium">Тень</div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              {archetype.shadow}
            </p>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

function SocionicsProfileSimple({ data }: { data: ReportData["socionics"] }) {
  const primary = data.top3[0];

  if (!primary) {
    return (
      <SectionCard
        title="Соционический профиль"
        description="Соционика — дополнительная типологическая линза. Её лучше читать после астрологической основы и практических выводов."
      >
        <p className="leading-7 text-muted-foreground">
          Соционический слой пока не пришёл из API для этого отчёта. Вместо
          mock-данных показываем честный fallback: технический блок ниже
          остаётся доступен, а страница не падает.
        </p>
      </SectionCard>
    );
  }

  return (
    <SectionCard
      title="Соционический профиль"
      description="Соционика — дополнительная типологическая линза. Её лучше читать после астрологической основы и практических выводов."
    >
      <p className="leading-7 text-muted-foreground">
        Вероятный тип:{" "}
        <span className="font-semibold text-foreground">{primary.type}</span> (
        {primary.name}). В простом чтении это гипотеза о том, как человек
        обрабатывает информацию, принимает решения и взаимодействует с людьми.
      </p>
      <div className="mt-4 rounded-lg bg-muted p-4 text-sm leading-6">
        <TermHelp term="Model A" /> и <TermHelp term="Confidence" /> не
        обязательны для первого чтения отчёта. Подробности оставлены в
        техническом блоке ниже.
      </div>
    </SectionCard>
  );
}

function TechnicalDetails({ data }: { data: ReportData }) {
  return (
    <details className="rounded-lg border bg-card text-card-foreground shadow-sm">
      <summary className="cursor-pointer p-6 text-xl font-semibold">
        Технические детали расчёта
      </summary>
      <div className="space-y-6 border-t p-6">
        <div className="rounded-lg bg-muted p-4 text-sm leading-6 text-muted-foreground">
          Здесь оставлены полная карта, таблицы, radar, проценты и evidence-like
          детали. Это нужно для проверки расчёта, но не должно мешать первому
          чтению.
        </div>
        <div>
          <h3 className="mb-3 text-lg font-semibold">Полная натальная карта</h3>
          <NatalChart chart={data.chart} />
        </div>
        <div>
          <h3 className="mb-3 text-lg font-semibold">
            Полная соционическая детализация
          </h3>
          <SocionicsResult data={data.socionics} />
        </div>
      </div>
    </details>
  );
}

// ── Loading Skeleton ───────────────────────────────────────────────
function ReportSkeleton() {
  return (
    <div className="space-y-4 animate-pulse">
      <div className="h-40 rounded-lg bg-muted" />
      <div className="h-48 rounded-lg bg-muted" />
      <div className="h-64 rounded-lg bg-muted" />
    </div>
  );
}

// ── Report Content ─────────────────────────────────────────────────
function ReportContent({ data }: { data: ReportData }) {
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <ReportHeader profile={data.profile} />
      <ExecutiveSummary summary={data.summary} />
      <AstrologyFoundation astrology={data.astrology} />
      <Manifestations items={data.manifestations} />
      <PracticalRecommendations items={data.recommendations} />
      <ArchetypeProfile archetype={data.archetype} />
      <SocionicsProfileSimple data={data.socionics} />
      <TechnicalDetails data={data} />
    </div>
  );
}

// ── Error State ────────────────────────────────────────────────────
function ReportError({ message }: { message: string }) {
  return (
    <Card className="border-destructive/30">
      <CardHeader>
        <CardTitle>Не удалось загрузить отчёт</CardTitle>
        <CardDescription>{message}</CardDescription>
      </CardHeader>
    </Card>
  );
}

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Неизвестная ошибка загрузки";
}

// ── Report Page ────────────────────────────────────────────────────
export default function ReportPage() {
  const params = useParams();
  const profileId = params.profileId as string;
  const token = useAuthStore((state) => state.token);
  const [data, setData] = useState<ReportData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadReport() {
      try {
        setIsLoading(true);
        setError(null);
        const apiData = await fetchReportApiData(profileId, token || undefined);
        if (isMounted) {
          setData(toReportViewModel(apiData));
        }
      } catch (loadError) {
        if (isMounted) {
          setError(getErrorMessage(loadError));
          setData(null);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    if (profileId) {
      loadReport();
    }

    return () => {
      isMounted = false;
    };
  }, [profileId, token]);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mx-auto mb-6 max-w-5xl">
        <p className="text-sm text-muted-foreground">Профиль: {profileId}</p>
        <h1 className="mt-2 text-3xl font-bold">Ваш отчёт</h1>
      </div>
      {isLoading ? <ReportSkeleton /> : null}
      {!isLoading && error ? <ReportError message={error} /> : null}
      {!isLoading && data ? <ReportContent data={data} /> : null}
    </div>
  );
}
