import type { Metadata } from "next";
import Link from "next/link";
import { Check } from "lucide-react";

import { BillingCheckoutButton } from "@/components/billing/billing-checkout-button";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = {
  title: "Оплата",
};

const freeFeatures = [
  "Расчёт натальной карты",
  "Базовый тип и архетип",
  "Краткое описание личности",
  "3 сильные стороны",
  "1–2 зоны риска",
  "Teaser платного отчёта",
];

const plusFeatures = [
  "Полный личностный отчёт",
  "Сильные стороны мышления и поведения",
  "Слабые зоны и точки роста",
  "Профессиональный профиль",
  "Отношения и типичные сценарии близости",
  "Совместимость с другими людьми",
  "20 персональных вопросов к карте в месяц",
  "Сохранение нескольких профилей",
  "Обновление отчёта после ответов на вопросы",
];

const principles = [
  [
    "Доступ, а не витрина",
    "Free остаётся входом в систему, Plus — рабочим пространством для собственной карты.",
  ],
  [
    "Один сильный выбор",
    "Без лестницы мелких пакетов: пользователь понимает, что именно открывает подписка.",
  ],
  [
    "Ценность растёт со временем",
    "Отчёт можно уточнять вопросами, сохранять профили и возвращаться к обновлённой версии.",
  ],
];

function FeatureList({
  items,
  accent = "gold",
}: {
  items: string[];
  accent?: "gold" | "blue";
}) {
  const iconColor = accent === "gold" ? "text-[#D8B45A]" : "text-[#8DA8FF]";

  return (
    <ul className="space-y-3.5">
      {items.map((item) => (
        <li
          key={item}
          className="flex gap-3 text-sm leading-relaxed text-[#D8DCE8]"
        >
          <Check className={`mt-0.5 h-4 w-4 shrink-0 ${iconColor}`} />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function BillingPage() {
  return (
    <div className="mx-auto max-w-7xl space-y-10">
      <section className="relative overflow-hidden rounded-[32px] border border-[rgba(216,220,232,0.14)] bg-[linear-gradient(135deg,rgba(18,15,36,0.96)_0%,rgba(35,26,72,0.92)_47%,rgba(23,20,42,0.98)_100%)] px-7 py-10 shadow-2xl shadow-black/30 md:px-12 md:py-14">
        <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-[rgba(216,180,90,0.65)] to-transparent" />
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-[rgba(91,63,214,0.30)] blur-3xl" />
        <div className="absolute -bottom-28 left-16 h-64 w-64 rounded-full bg-[rgba(216,180,90,0.13)] blur-3xl" />

        <div className="relative grid gap-10 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-end">
          <div className="max-w-3xl space-y-7">
            <p className="text-xs font-medium uppercase tracking-[0.34em] text-[#D8B45A]">
              Astrotype Membership
            </p>
            <div className="space-y-5">
              <h1 className="font-[family-name:var(--font-cormorant)] text-5xl font-semibold leading-[0.95] tracking-tight text-[#F6F1E8] md:text-6xl">
                Откройте полную карту своей личности
              </h1>
              <p className="max-w-2xl text-base leading-8 text-[rgba(246,241,232,0.78)] md:text-lg">
                Free даёт первый точный срез. Plus открывает полный отчёт,
                профессиональный слой, отношения и совместимость, вопросы для
                уточнения и сохранение нескольких профилей.
              </p>
            </div>
          </div>

          <div className="rounded-[24px] border border-[rgba(246,241,232,0.16)] bg-[rgba(246,241,232,0.07)] p-6 backdrop-blur-xl">
            <p className="text-xs uppercase tracking-[0.28em] text-[#D8DCE8]">
              Цена Plus
            </p>
            <div className="mt-4 flex items-end gap-2">
              <span className="text-6xl font-semibold tracking-tight text-[#F6F1E8]">
                999 ₽
              </span>
              <span className="pb-2 text-sm text-[#D8DCE8]">/ месяц</span>
            </div>
            <p className="mt-5 text-sm leading-6 text-[rgba(216,220,232,0.78)]">
              Создаём оплату через YooKassa: цена и продукт берутся из
              backend-каталога, после подтверждения доступ активируется
              webhook’ом.
            </p>
          </div>
        </div>
      </section>

      <section className="grid gap-5 lg:grid-cols-[360px_minmax(0,1fr)]">
        <article className="self-start rounded-[28px] border border-[rgba(216,220,232,0.12)] bg-[rgba(255,255,255,0.035)] p-7 md:p-8">
          <div className="flex items-start justify-between gap-6 border-b border-[rgba(216,220,232,0.10)] pb-7">
            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-[0.30em] text-[#8DA8FF]">
                Free
              </p>
              <h2 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
                Бесплатный вход
              </h2>
              <p className="max-w-md text-sm leading-6 text-[#D8DCE8]">
                Первый контакт с системой: карта, базовый тип и достаточно
                смысла, чтобы понять точность сервиса.
              </p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-semibold text-[#F6F1E8]">0 ₽</div>
              <div className="mt-1 text-xs text-[#D8DCE8]">навсегда</div>
            </div>
          </div>

          <div className="pt-7">
            <FeatureList items={freeFeatures} accent="blue" />
          </div>

          <div className="mt-8 rounded-[20px] border border-[rgba(141,168,255,0.18)] bg-[rgba(141,168,255,0.06)] p-5 text-sm leading-6 text-[#D8DCE8]">
            Free должен доказать: “это не случайная генерация — здесь есть
            узнаваемый паттерн”.
          </div>

          <Button asChild variant="outline" className="mt-8 w-full">
            <Link href="/register">Начать бесплатно</Link>
          </Button>
        </article>

        <article
          id="plus"
          className="relative overflow-hidden rounded-[32px] border border-[rgba(216,180,90,0.32)] bg-[rgba(255,255,255,0.055)] p-7 shadow-2xl shadow-black/20 md:p-8"
        >
          <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-[#D8B45A] to-transparent" />
          <div className="absolute right-0 top-0 h-40 w-40 bg-[rgba(216,180,90,0.10)] blur-3xl" />

          <div className="relative space-y-8">
            <div className="grid gap-7 border-b border-[rgba(216,220,232,0.10)] pb-7 xl:grid-cols-[minmax(0,1fr)_260px] xl:items-start">
              <div className="space-y-3">
                <p className="text-xs font-medium uppercase tracking-[0.30em] text-[#D8B45A]">
                  Plus
                </p>
                <h2 className="max-w-xl font-[family-name:var(--font-cormorant)] text-4xl font-semibold leading-[1.04] text-[#F6F1E8]">
                  Полный доступ к персональной карте
                </h2>
                <p className="max-w-2xl text-sm leading-6 text-[#D8DCE8]">
                  Не “подписка на гороскоп”, а полный профиль личности,
                  отношений и карьеры с персональными уточнениями по вашей
                  карте.
                </p>
              </div>

              <aside className="rounded-[24px] border border-[rgba(216,180,90,0.22)] bg-[rgba(23,20,42,0.56)] p-6">
                <p className="text-xs uppercase tracking-[0.26em] text-[#D8B45A]">
                  Подписка
                </p>
                <div className="mt-5 space-y-1">
                  <div className="text-5xl font-semibold tracking-tight text-[#F6F1E8]">
                    999 ₽
                  </div>
                  <div className="text-sm text-[#D8DCE8]">в месяц</div>
                </div>
                <div className="my-6 h-px bg-[rgba(216,220,232,0.12)]" />
                <p className="text-sm leading-6 text-[#D8DCE8]">
                  Free — вход в систему. Plus — полная карта личности, отношений
                  и карьеры.
                </p>
                <BillingCheckoutButton />
                <p className="mt-4 text-xs leading-5 text-[rgba(216,220,232,0.62)]">
                  Оплата открывается на стороне YooKassa. Доступ включается
                  после подтверждения платежа, а не по факту возврата на сайт.
                </p>
              </aside>
            </div>

            <FeatureList items={plusFeatures} />
          </div>
        </article>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {principles.map(([title, description]) => (
          <div
            key={title}
            className="rounded-[24px] border border-[rgba(216,220,232,0.10)] bg-[rgba(255,255,255,0.03)] p-6"
          >
            <h3 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-[#F6F1E8]">
              {title}
            </h3>
            <p className="mt-3 text-sm leading-6 text-[#D8DCE8]">
              {description}
            </p>
          </div>
        ))}
      </section>
    </div>
  );
}
