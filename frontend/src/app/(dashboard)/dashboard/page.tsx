"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Baby,
  Briefcase,
  CalendarDays,
  Crown,
  Heart,
  MapPin,
  PlusCircle,
  User,
} from "lucide-react";

import {
  ProductSurfaceCard,
  ProductSurfaceHero,
  SurfaceActionRow,
  SurfaceEyebrow,
} from "@/components/product-surface";
import { Button } from "@/components/ui/button";
import { useBillingAccess } from "@/hooks/use-billing-access";
import { bootstrapSession } from "@/lib/auth-session";
import { useAuthStore } from "@/stores/auth-store";

interface Profile {
  id: string;
  name: string;
  birth_date: string;
  birth_place: string;
}

const products = [
  {
    id: "self",
    title: "Личный отчёт",
    description:
      "Главный личный отчёт: карта рождения, внутренний ритм, сильные опоры и зоны роста.",
    icon: User,
    color: "var(--chart-series-2)",
    status: "available",
    href: "/products/self",
  },
  {
    id: "love",
    title: "Отношения",
    description:
      "Будущее направление про близость, притяжение, границы и повторяющиеся сценарии в паре.",
    icon: Heart,
    color: "var(--product-love)",
    status: "coming_soon",
    href: "/products/love",
  },
  {
    id: "child",
    title: "Ребёнок",
    description:
      "Будущее направление для родителя: темперамент ребёнка, поддержка и бережная среда развития.",
    icon: Baby,
    color: "var(--chart-series-3)",
    status: "coming_soon",
    href: "/products/child",
  },
  {
    id: "career",
    title: "Карьера",
    description:
      "Рабочие сценарии: где легче проявляться, какой темп подходит и какие роли не забирают ресурс.",
    icon: Briefcase,
    color: "var(--product-career)",
    status: "available",
    href: "/products/career",
  },
];

function formatProfileDate(value: string) {
  if (!value) return "Дата не указана";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

function getAccessStatusCopy({
  isPlusActive,
  isLoadingAccess,
  accessError,
  currentPeriodEnd,
}: {
  isPlusActive: boolean;
  isLoadingAccess: boolean;
  accessError: boolean;
  currentPeriodEnd: string | null;
}) {
  if (isLoadingAccess) {
    return {
      eyebrow: "Проверяем доступ",
      title: "Статус аккаунта обновляется",
      text: "Сейчас сверяем данные оплаты с сервером.",
      cta: "Оплата и доступ",
      href: "/billing",
    };
  }

  if (isPlusActive) {
    const activeUntil = currentPeriodEnd
      ? new Intl.DateTimeFormat("ru-RU", {
          day: "numeric",
          month: "long",
          year: "numeric",
        }).format(new Date(currentPeriodEnd))
      : null;
    return {
      eyebrow: "Аккаунт Plus",
      title: activeUntil ? `Plus активен до ${activeUntil}` : "Plus активен",
      text: "Полный личный отчёт открыт и привязан к этому аккаунту.",
      cta: "Управлять доступом",
      href: "/billing",
    };
  }

  return {
    eyebrow: accessError ? "Статус недоступен" : "Базовый аккаунт",
    title: accessError ? "Не удалось проверить Plus" : "Plus не активен",
    text: accessError
      ? "Откройте оплату, чтобы повторить проверку статуса."
      : "Полный личный отчёт откроется после подтверждения оплаты.",
    cta: "Открыть Plus",
    href: "/billing",
  };
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
  const { access, isPlusActive, isLoadingAccess, accessError } =
    useBillingAccess();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchUser() {
      if (user) return;
      try {
        const data = await bootstrapSession();
        if (data) {
          setUser(data);
        }
      } catch {
        // Session bootstrap is best-effort; the guard owns redirect behavior.
      }
    }
    fetchUser();
  }, [user, setUser]);

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
        // Keep dashboard shell visible if profile loading fails.
      } finally {
        setLoading(false);
      }
    }
    fetchProfiles();
  }, []);

  const primaryProfile = useMemo(() => profiles[0], [profiles]);
  const greetingName = user?.name?.trim() || user?.email?.split("@")[0];
  const accessStatus = getAccessStatusCopy({
    isPlusActive,
    isLoadingAccess,
    accessError,
    currentPeriodEnd: access?.subscription?.current_period_end ?? null,
  });

  return (
    <div
      data-product-surface-page="dashboard"
      className="mx-auto w-[min(100%,1500px)] space-y-7"
    >
      <ProductSurfaceHero
        eyebrow="Личный кабинет Astrotype"
        title={
          <>
            {greetingName
              ? `${greetingName}, ваша карта рядом`
              : "Ваше пространство отчётов"}
          </>
        }
        lead={
          primaryProfile ? (
            <>
              Продолжите с последнего личного портрета или откройте другой
              профиль. Кабинет хранит путь от данных рождения к готовому отчёту.
            </>
          ) : (
            <>
              Начните с первой карты рождения: один понятный шаг создаст профиль
              и откроет путь к личному отчёту.
            </>
          )
        }
        aside={
          <ProductSurfaceCard className="space-y-5 border-accent-gold bg-surface-subtle">
            <SurfaceEyebrow>
              {primaryProfile ? "Последний отчёт" : "Первый шаг"}
            </SurfaceEyebrow>
            {primaryProfile ? (
              <>
                <h2 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-text-primary">
                  {primaryProfile.name || "Без имени"}
                </h2>
                <div className="space-y-2 text-sm text-text-secondary">
                  <p className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4 text-accent-gold" />
                    {formatProfileDate(primaryProfile.birth_date)}
                  </p>
                  <p className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-accent-gold" />
                    {primaryProfile.birth_place || "Место не указано"}
                  </p>
                </div>
                <Button asChild className="w-full">
                  <Link href={`/report/v2/${primaryProfile.id}`}>
                    Открыть отчёт
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </>
            ) : (
              <>
                <h2 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-text-primary">
                  Постройте первую карту
                </h2>
                <p className="text-sm leading-6 text-text-secondary">
                  Достаточно даты, времени и места рождения. Всё остальное
                  появится в отчёте после расчёта.
                </p>
                <Button asChild className="w-full">
                  <Link href="/products/self">
                    Начать с личного отчёта
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              </>
            )}
          </ProductSurfaceCard>
        }
      >
        <SurfaceActionRow>
          {primaryProfile ? (
            <Button asChild size="lg">
              <Link href={`/report/v2/${primaryProfile.id}`}>
                Продолжить чтение
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
          ) : (
            <Button asChild size="lg">
              <Link href="/products/self">
                Создать первый профиль
                <PlusCircle className="h-4 w-4" />
              </Link>
            </Button>
          )}
          <Button variant="outline" asChild size="lg">
            <Link href="/billing">Оплата и доступ</Link>
          </Button>
        </SurfaceActionRow>
      </ProductSurfaceHero>

      <section
        className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]"
        aria-label="Статус Plus"
      >
        <ProductSurfaceCard className="border-accent-gold bg-[var(--hero-background)]">
          <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
            <div className="flex items-start gap-4">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-accent-gold bg-accent-gold-soft text-accent-gold">
                <Crown className="h-5 w-5" />
              </span>
              <div className="space-y-2">
                <SurfaceEyebrow>{accessStatus.eyebrow}</SurfaceEyebrow>
                <h2 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-text-primary">
                  {accessStatus.title}
                </h2>
                <p className="max-w-2xl text-sm leading-6 text-text-secondary">
                  {accessStatus.text}
                </p>
              </div>
            </div>
            <Button asChild variant={isPlusActive ? "outline" : "default"}>
              <Link href={accessStatus.href}>{accessStatus.cta}</Link>
            </Button>
          </div>
        </ProductSurfaceCard>

        <ProductSurfaceCard className="space-y-3 text-sm leading-6 text-text-secondary">
          <SurfaceEyebrow>Где это видно</SurfaceEyebrow>
          <p>
            Статус Plus теперь вынесен в кабинет, левую панель и страницу
            оплаты, чтобы не приходилось искать подтверждение доступа внутри
            отчёта.
          </p>
        </ProductSurfaceCard>
      </section>

      <section className="space-y-4" aria-labelledby="reports-heading">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <SurfaceEyebrow>Мои отчёты</SurfaceEyebrow>
            <h2
              id="reports-heading"
              className="mt-2 font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-text-primary"
            >
              Личные карты и портреты
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-text-secondary">
            Сначала отчёт, потом дополнительные направления. Главный путь всегда
            остаётся на виду.
          </p>
        </div>

        {profiles.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {profiles.map((profile, index) => (
              <Link
                key={profile.id}
                href={`/report/v2/${profile.id}`}
                className="group rounded-[28px] border border-border-default bg-surface-subtle p-6 shadow-xl shadow-black/10 transition hover:border-accent-gold hover:bg-surface-subtle"
              >
                <div className="flex items-start justify-between gap-5">
                  <div className="space-y-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-link">
                      {index === 0 ? "Основной путь" : "Сохранённый профиль"}
                    </p>
                    <h3 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-text-primary">
                      {profile.name || "Без имени"}
                    </h3>
                    <div className="space-y-2 text-sm text-text-secondary">
                      <p>{formatProfileDate(profile.birth_date)}</p>
                      <p>{profile.birth_place || "Место не указано"}</p>
                    </div>
                  </div>
                  <span className="rounded-full border border-accent-gold px-4 py-2 text-sm text-text-primary transition group-hover:border-accent-gold">
                    Открыть
                  </span>
                </div>
              </Link>
            ))}
          </div>
        ) : !loading ? (
          <ProductSurfaceCard className="grid gap-6 text-center md:grid-cols-[1fr_auto] md:items-center md:text-left">
            <div className="space-y-3">
              <SurfaceEyebrow>Пока пусто</SurfaceEyebrow>
              <h3 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-text-primary">
                Создайте первую карту рождения
              </h3>
              <p className="text-sm leading-6 text-text-secondary">
                Кабинет станет рабочим пространством после первого профиля:
                появится отчёт, дата рождения и быстрый возврат к чтению.
              </p>
            </div>
            <Button asChild size="lg">
              <Link href="/products/self">Начать</Link>
            </Button>
          </ProductSurfaceCard>
        ) : (
          <ProductSurfaceCard className="text-sm text-text-secondary">
            Загружаем ваши отчёты…
          </ProductSurfaceCard>
        )}
      </section>

      <section className="space-y-4" aria-labelledby="products-heading">
        <div>
          <SurfaceEyebrow>Направления</SurfaceEyebrow>
          <h2
            id="products-heading"
            className="mt-2 font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-text-primary"
          >
            Что можно открыть из кабинета
          </h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {products.map((product) => (
            <ProductSurfaceCard
              key={product.id}
              className={product.status === "coming_soon" ? "opacity-62" : ""}
            >
              <div className="space-y-5">
                <div
                  className="flex h-11 w-11 items-center justify-center rounded-2xl"
                  style={{ background: `${product.color}22` }}
                >
                  <product.icon
                    className="h-5 w-5"
                    style={{ color: product.color }}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <h3 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-text-primary">
                      {product.title}
                    </h3>
                    {product.status === "coming_soon" ? (
                      <span className="rounded-full border border-border-default px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-text-muted">
                        позже
                      </span>
                    ) : null}
                  </div>
                  <p className="text-sm leading-6 text-text-secondary">
                    {product.description}
                  </p>
                </div>
                {product.status === "available" ? (
                  <Button asChild variant="outline" size="sm">
                    <Link href={product.href}>Открыть</Link>
                  </Button>
                ) : (
                  <Button variant="outline" size="sm" disabled>
                    В планах
                  </Button>
                )}
              </div>
            </ProductSurfaceCard>
          ))}
        </div>
      </section>
    </div>
  );
}
