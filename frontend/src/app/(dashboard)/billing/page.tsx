"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Check, Clock3, Crown, Loader2, ShieldCheck } from "lucide-react";
import { useSearchParams } from "next/navigation";

import { BillingCheckoutButton } from "@/components/billing/billing-checkout-button";
import {
  ProductSurfaceCard,
  ProductSurfaceHero,
  SurfaceEyebrow,
} from "@/components/product-surface";
import { Button } from "@/components/ui/button";
import { useBillingAccess } from "@/hooks/use-billing-access";
import {
  getBillingAccess,
  type BillingAccessResponse,
  type BillingAccessState,
} from "@/lib/api/payments";

const freeFeatures = [
  "первый вход в кабинет",
  "создание профиля рождения",
  "расчёт карты и базовые пояснения",
  "сохранение результата в аккаунте",
];

const plusFeatures = [
  "полный личный отчёт",
  "подробные разделы о реакциях, мотивах и опорах",
  "возврат к отчёту из кабинета",
  "PDF и дальнейшие обновления продукта",
];

const trustSteps = [
  {
    title: "Оплата открывается в YooKassa",
    text: "Вы переходите на защищённую страницу платёжного сервиса. Astrotype не хранит данные карты.",
  },
  {
    title: "Мы ждём подтверждение",
    text: "Возврат на сайт сам по себе не считается успешной оплатой. Статус меняется только после проверки платёжной системой.",
  },
  {
    title: "Доступ привязывается к аккаунту",
    text: "Когда подтверждение получено, в аккаунте появляется Плюс и активный доступ к полному отчёту.",
  },
];

const returnStatusCopy: Record<
  BillingAccessState,
  {
    title: string;
    description: string;
    tone: "neutral" | "success" | "warning";
  }
> = {
  free: {
    title: "Статус аккаунта ещё базовый",
    description:
      "Если вы только что вернулись из YooKassa, подтверждение может прийти не сразу. Мы обновляем статус по данным платёжной системы.",
    tone: "neutral",
  },
  checkout_pending: {
    title: "Проверяем оплату",
    description:
      "Это может занять немного времени: доступ включается только после подтверждения YooKassa и серверной проверки платежа.",
    tone: "neutral",
  },
  plus_active: {
    title: "Плюс активен",
    description:
      "Оплата подтверждена, полный доступ привязан к вашему аккаунту.",
    tone: "success",
  },
  payment_failed: {
    title: "Оплата не завершена",
    description:
      "Похоже, платёж был отменён или не подтвердился. Можно спокойно попробовать ещё раз.",
    tone: "warning",
  },
  plus_inactive: {
    title: "Плюс сейчас не активен",
    description:
      "В аккаунте есть прошлый доступ, но сейчас он не действует. Можно обновить оплату и снова открыть полный отчёт.",
    tone: "warning",
  },
};

function BillingReturnStatus() {
  const searchParams = useSearchParams();
  const checkout = searchParams.get("checkout");
  const [access, setAccess] = useState<BillingAccessResponse | null>(null);
  const [isLoading, setIsLoading] = useState(checkout === "return");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (checkout !== "return") {
      return;
    }

    let cancelled = false;

    async function refreshAccess() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        const nextAccess = await getBillingAccess();
        if (!cancelled) {
          setAccess(nextAccess);
        }
      } catch {
        if (!cancelled) {
          setErrorMessage(
            "Не удалось обновить статус оплаты. Попробуйте открыть страницу ещё раз через минуту.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void refreshAccess();

    return () => {
      cancelled = true;
    };
  }, [checkout]);

  if (checkout !== "return") {
    return null;
  }

  const copy = access
    ? returnStatusCopy[access.access_state]
    : returnStatusCopy.checkout_pending;
  const toneClass =
    copy.tone === "success"
      ? "border-[rgba(74,222,128,0.34)] bg-[rgba(74,222,128,0.08)] text-[#BFF5CF]"
      : copy.tone === "warning"
        ? "border-[rgba(255,180,168,0.30)] bg-[rgba(255,180,168,0.08)] text-[#FFD1CA]"
        : "border-[rgba(216,180,90,0.28)] bg-[rgba(216,180,90,0.08)] text-[#F6F1E8]";

  return (
    <section className={`rounded-[24px] border p-5 ${toneClass}`} role="status">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="space-y-2">
          <p className="flex items-center gap-2 text-sm font-semibold">
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {copy.title}
          </p>
          <p className="max-w-3xl text-sm leading-6 text-[rgba(246,241,232,0.78)]">
            {errorMessage ?? copy.description}
          </p>
        </div>
        {access?.access_state === "payment_failed" ||
        access?.access_state === "plus_inactive" ? (
          <button
            type="button"
            className="text-left text-sm font-medium text-[#F6F1E8] underline underline-offset-4"
            onClick={() =>
              document
                .getElementById("plus")
                ?.scrollIntoView({ behavior: "smooth" })
            }
          >
            Попробовать ещё раз
          </button>
        ) : null}
      </div>
    </section>
  );
}

function FeatureList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-3.5">
      {items.map((item) => (
        <li
          key={item}
          className="flex gap-3 text-sm leading-relaxed text-[#D8DCE8]"
        >
          <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#D8B45A]" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function BillingAccountStatus() {
  const { access, isLoadingAccess, accessError, isPlusActive } =
    useBillingAccess();
  const latestPaymentStatus = access?.latest_payment?.status;
  const activeEntitlement = access?.entitlements.find(
    (entitlement) => entitlement.status === "active",
  );

  return (
    <ProductSurfaceCard className="border-[rgba(216,180,90,0.26)] bg-[linear-gradient(135deg,rgba(216,180,90,0.11),rgba(255,255,255,0.045))]">
      <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-[rgba(216,180,90,0.34)] bg-[rgba(216,180,90,0.14)] text-[#D8B45A]">
            <Crown className="h-5 w-5" />
          </span>
          <div className="space-y-2">
            <SurfaceEyebrow>Текущий статус аккаунта</SurfaceEyebrow>
            <h2 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-[#F6F1E8]">
              {isLoadingAccess
                ? "Проверяем Plus"
                : isPlusActive
                  ? "Plus активен"
                  : "Plus не активен"}
            </h2>
            <p className="max-w-3xl text-sm leading-6 text-[#D8DCE8]">
              {accessError
                ? "Не удалось получить статус доступа. Попробуйте обновить страницу или повторить проверку позже."
                : isPlusActive
                  ? "Оплата подтверждена сервером: полный личный отчёт открыт для этого аккаунта."
                  : "Сейчас аккаунт в базовом статусе. Plus появится здесь после подтверждения оплаты YooKassa."}
            </p>
          </div>
        </div>
        <span
          className={
            isPlusActive
              ? "rounded-full border border-[rgba(124,242,154,0.34)] bg-[rgba(124,242,154,0.10)] px-4 py-2 text-sm font-semibold text-[#BFF5CF]"
              : "rounded-full border border-[rgba(216,220,232,0.16)] bg-[rgba(255,255,255,0.045)] px-4 py-2 text-sm font-semibold text-[#D8DCE8]"
          }
        >
          {isPlusActive ? "Аккаунт Plus" : "Базовый аккаунт"}
        </span>
      </div>
      <dl className="mt-6 grid gap-3 text-sm sm:grid-cols-3">
        <div className="rounded-2xl border border-[rgba(216,220,232,0.12)] bg-[rgba(255,255,255,0.04)] p-4">
          <dt className="text-[rgba(216,220,232,0.58)]">Доступ</dt>
          <dd className="mt-1 font-medium text-[#F6F1E8]">
            {isPlusActive ? "полный отчёт открыт" : "полный отчёт закрыт"}
          </dd>
        </div>
        <div className="rounded-2xl border border-[rgba(216,220,232,0.12)] bg-[rgba(255,255,255,0.04)] p-4">
          <dt className="text-[rgba(216,220,232,0.58)]">Последняя оплата</dt>
          <dd className="mt-1 font-medium text-[#F6F1E8]">
            {latestPaymentStatus ?? "нет подтверждённой оплаты"}
          </dd>
        </div>
        <div className="rounded-2xl border border-[rgba(216,220,232,0.12)] bg-[rgba(255,255,255,0.04)] p-4">
          <dt className="text-[rgba(216,220,232,0.58)]">Привязка</dt>
          <dd className="mt-1 font-medium text-[#F6F1E8]">
            {activeEntitlement
              ? "есть активный доступ"
              : "активного доступа нет"}
          </dd>
        </div>
      </dl>
    </ProductSurfaceCard>
  );
}

export default function BillingPage() {
  return (
    <div
      data-product-surface-page="billing"
      className="mx-auto max-w-7xl space-y-7"
    >
      <BillingReturnStatus />

      <BillingAccountStatus />

      <ProductSurfaceHero
        eyebrow="Бесплатный / Плюс"
        title="Статус аккаунта и доступ к полному отчёту"
        lead="Страница оплаты в Astrotype — не витрина с мелкими пакетами, а спокойное объяснение: что открывает Плюс, как проходит оплата и почему доступ включается только после подтверждения."
        aside={
          <ProductSurfaceCard className="space-y-5 border-[rgba(216,180,90,0.24)] bg-[rgba(255,255,255,0.06)]">
            <p className="text-xs uppercase tracking-[0.28em] text-[#D8DCE8]">
              Цена Плюс
            </p>
            <div className="flex items-end gap-2">
              <span className="text-6xl font-semibold tracking-tight text-[#F6F1E8]">
                999 ₽
              </span>
              <span className="pb-2 text-sm text-[#D8DCE8]">/ месяц</span>
            </div>
            <p className="text-sm leading-6 text-[rgba(216,220,232,0.78)]">
              Оплата открывается в YooKassa. После подтверждения статус аккаунта
              обновится автоматически.
            </p>
            <div id="plus">
              <BillingCheckoutButton />
            </div>
          </ProductSurfaceCard>
        }
      >
        <div className="grid gap-3 pt-2 text-sm text-[#D8DCE8] sm:grid-cols-3">
          {[
            "без данных карты в Astrotype",
            "возврат не равен успеху оплаты",
            "доступ включается после проверки",
          ].map((item) => (
            <div
              key={item}
              className="rounded-2xl border border-[rgba(216,220,232,0.12)] bg-[rgba(255,255,255,0.045)] px-4 py-3"
            >
              {item}
            </div>
          ))}
        </div>
      </ProductSurfaceHero>

      <section className="grid gap-5 lg:grid-cols-2">
        <ProductSurfaceCard className="space-y-6">
          <div className="space-y-2">
            <SurfaceEyebrow>Бесплатный</SurfaceEyebrow>
            <h2 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-[#F6F1E8]">
              Базовый статус
            </h2>
            <p className="text-sm leading-6 text-[#D8DCE8]">
              Подходит, чтобы войти в продукт, создать профиль и увидеть первый
              слой карты без ощущения закрытой двери.
            </p>
          </div>
          <FeatureList items={freeFeatures} />
          <Button variant="outline" asChild>
            <Link href="/dashboard">Вернуться в кабинет</Link>
          </Button>
        </ProductSurfaceCard>

        <ProductSurfaceCard className="space-y-6 border-[rgba(216,180,90,0.28)] bg-[rgba(216,180,90,0.055)]">
          <div className="space-y-2">
            <SurfaceEyebrow>Плюс</SurfaceEyebrow>
            <h2 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-[#F6F1E8]">
              Полный личный отчёт
            </h2>
            <p className="text-sm leading-6 text-[#D8DCE8]">
              Плюс открывает подробный личный отчёт и сохраняет доступ в вашем
              аккаунте после подтверждения оплаты.
            </p>
          </div>
          <FeatureList items={plusFeatures} />
          <BillingCheckoutButton />
        </ProductSurfaceCard>
      </section>

      <section className="grid gap-5 lg:grid-cols-[0.8fr_1.2fr]">
        <ProductSurfaceCard className="space-y-4">
          <SurfaceEyebrow>Как подтверждается оплата</SurfaceEyebrow>
          <h2 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-[#F6F1E8]">
            Сначала подтверждение, потом доступ
          </h2>
          <p className="text-sm leading-7 text-[#D8DCE8]">
            Эта страница может показать, что вы вернулись из YooKassa, но не
            делает вывод об оплате сама. Astrotype ждёт проверенный статус и
            только потом меняет доступ.
          </p>
        </ProductSurfaceCard>

        <div className="grid gap-4">
          {trustSteps.map((step, index) => (
            <ProductSurfaceCard key={step.title} className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[rgba(216,180,90,0.16)] text-sm font-semibold text-[#D8B45A]">
                {index + 1}
              </div>
              <div className="space-y-2">
                <h3 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-[#F6F1E8]">
                  {step.title}
                </h3>
                <p className="text-sm leading-6 text-[#D8DCE8]">{step.text}</p>
              </div>
            </ProductSurfaceCard>
          ))}
        </div>
      </section>

      <section className="rounded-[28px] border border-[rgba(141,168,255,0.22)] bg-[rgba(141,168,255,0.06)] p-6 md:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <p className="flex items-center gap-2 text-sm font-semibold text-[#F6F1E8]">
              <ShieldCheck className="h-4 w-4 text-[#8DA8FF]" />
              Бесплатный статус и Плюс сейчас не режут продукт по скрытым
              правилам
            </p>
            <p className="max-w-3xl text-sm leading-6 text-[#D8DCE8]">
              Статус виден в аккаунте, а доступ к платным материалам проверяется
              на стороне сервиса. Так пользователь не зависит от случайного
              состояния страницы после оплаты.
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-[#D8DCE8]">
            <Clock3 className="h-4 w-4 text-[#D8B45A]" />
            Проверка обычно занимает меньше минуты
          </div>
        </div>
      </section>
    </div>
  );
}
