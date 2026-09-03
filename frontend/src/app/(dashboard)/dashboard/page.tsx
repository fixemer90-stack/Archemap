"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Baby,
  Briefcase,
  CalendarDays,
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
    color: "#D8B45A",
    status: "available",
    href: "/products/self",
  },
  {
    id: "love",
    title: "Отношения",
    description:
      "Будущее направление про близость, притяжение, границы и повторяющиеся сценарии в паре.",
    icon: Heart,
    color: "#B84A6B",
    status: "coming_soon",
    href: "/products/love",
  },
  {
    id: "child",
    title: "Ребёнок",
    description:
      "Будущее направление для родителя: темперамент ребёнка, поддержка и бережная среда развития.",
    icon: Baby,
    color: "#6BAFBD",
    status: "coming_soon",
    href: "/products/child",
  },
  {
    id: "career",
    title: "Карьера",
    description:
      "Рабочие сценарии: где легче проявляться, какой темп подходит и какие роли не забирают ресурс.",
    icon: Briefcase,
    color: "#C28A2E",
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

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const setUser = useAuthStore((s) => s.setUser);
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
          <ProductSurfaceCard className="space-y-5 border-[rgba(216,180,90,0.22)] bg-[rgba(255,255,255,0.06)]">
            <SurfaceEyebrow>
              {primaryProfile ? "Последний отчёт" : "Первый шаг"}
            </SurfaceEyebrow>
            {primaryProfile ? (
              <>
                <h2 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
                  {primaryProfile.name || "Без имени"}
                </h2>
                <div className="space-y-2 text-sm text-[#D8DCE8]">
                  <p className="flex items-center gap-2">
                    <CalendarDays className="h-4 w-4 text-[#D8B45A]" />
                    {formatProfileDate(primaryProfile.birth_date)}
                  </p>
                  <p className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-[#D8B45A]" />
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
                <h2 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
                  Постройте первую карту
                </h2>
                <p className="text-sm leading-6 text-[#D8DCE8]">
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

      <section className="space-y-4" aria-labelledby="reports-heading">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <SurfaceEyebrow>Мои отчёты</SurfaceEyebrow>
            <h2
              id="reports-heading"
              className="mt-2 font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-[#F6F1E8]"
            >
              Личные карты и портреты
            </h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-[rgba(216,220,232,0.70)]">
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
                className="group rounded-[28px] border border-[rgba(216,220,232,0.13)] bg-[rgba(255,255,255,0.045)] p-6 shadow-xl shadow-black/10 transition hover:border-[rgba(216,180,90,0.42)] hover:bg-[rgba(255,255,255,0.07)]"
              >
                <div className="flex items-start justify-between gap-5">
                  <div className="space-y-4">
                    <p className="text-xs uppercase tracking-[0.28em] text-[#8DA8FF]">
                      {index === 0 ? "Основной путь" : "Сохранённый профиль"}
                    </p>
                    <h3 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
                      {profile.name || "Без имени"}
                    </h3>
                    <div className="space-y-2 text-sm text-[#D8DCE8]">
                      <p>{formatProfileDate(profile.birth_date)}</p>
                      <p>{profile.birth_place || "Место не указано"}</p>
                    </div>
                  </div>
                  <span className="rounded-full border border-[rgba(216,180,90,0.28)] px-4 py-2 text-sm text-[#F6F1E8] transition group-hover:border-[#D8B45A]">
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
              <h3 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
                Создайте первую карту рождения
              </h3>
              <p className="text-sm leading-6 text-[#D8DCE8]">
                Кабинет станет рабочим пространством после первого профиля:
                появится отчёт, дата рождения и быстрый возврат к чтению.
              </p>
            </div>
            <Button asChild size="lg">
              <Link href="/products/self">Начать</Link>
            </Button>
          </ProductSurfaceCard>
        ) : (
          <ProductSurfaceCard className="text-sm text-[#D8DCE8]">
            Загружаем ваши отчёты…
          </ProductSurfaceCard>
        )}
      </section>

      <section className="space-y-4" aria-labelledby="products-heading">
        <div>
          <SurfaceEyebrow>Направления</SurfaceEyebrow>
          <h2
            id="products-heading"
            className="mt-2 font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-[#F6F1E8]"
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
                    <h3 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-[#F6F1E8]">
                      {product.title}
                    </h3>
                    {product.status === "coming_soon" ? (
                      <span className="rounded-full border border-[rgba(216,220,232,0.16)] px-2 py-0.5 text-[10px] uppercase tracking-[0.18em] text-[rgba(216,220,232,0.54)]">
                        позже
                      </span>
                    ) : null}
                  </div>
                  <p className="text-sm leading-6 text-[#D8DCE8]">
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
