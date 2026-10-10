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
  cancelSubscription,
  getBillingAccess,
  resumeSubscription,
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

function formatBillingDate(value: string | null): string {
  if (!value) return "дата не указана";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  }).format(date);
}

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
  cancel_scheduled: {
    title: "Автопродление отключено",
    description:
      "Plus остаётся активным до конца уже оплаченного периода. Нового списания не будет.",
    tone: "success",
  },
  past_due: {
    title: "Не удалось продлить Plus",
    description:
      "Платёж за следующий период не подтвердился. Оформите подписку заново, чтобы восстановить доступ.",
    tone: "warning",
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
  plus_expired: {
    title: "Срок Plus истёк",
    description:
      "Оплаченный период завершился. Оформите месячную подписку заново, чтобы открыть полный отчёт.",
    tone: "warning",
  },
  plus_suspended: {
    title: "Plus приостановлен",
    description:
      "Доступ временно остановлен из-за платёжного или юридического статуса. Обратитесь в поддержку перед новой оплатой.",
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
      ? "border-success bg-success/10 text-success"
      : copy.tone === "warning"
        ? "border-error bg-error/10 text-error"
        : "border-accent-gold bg-accent-gold-soft text-text-primary";

  return (
    <section className={`rounded-[24px] border p-5 ${toneClass}`} role="status">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="space-y-2">
          <p className="flex items-center gap-2 text-sm font-semibold">
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {copy.title}
          </p>
          <p className="max-w-3xl text-sm leading-6 text-text-secondary">
            {errorMessage ?? copy.description}
          </p>
        </div>
        {access?.access_state === "payment_failed" ||
        access?.access_state === "plus_inactive" ||
        access?.access_state === "past_due" ||
        access?.access_state === "plus_expired" ? (
          <button
            type="button"
            className="text-left text-sm font-medium text-text-primary underline underline-offset-4"
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
          className="flex gap-3 text-sm leading-relaxed text-text-secondary"
        >
          <Check className="mt-0.5 h-4 w-4 shrink-0 text-accent-gold" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

function BillingAccountStatus() {
  const { access, isLoadingAccess, accessError, isPlusActive, refreshAccess } =
    useBillingAccess();
  const [isUpdating, setIsUpdating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const subscription = access?.subscription;
  const canCancel =
    subscription !== null &&
    subscription !== undefined &&
    access?.access_state === "plus_active" &&
    !subscription.cancel_at_period_end;
  const canResume =
    subscription !== null &&
    subscription !== undefined &&
    access?.access_state === "cancel_scheduled";

  async function updateRenewal(action: "cancel" | "resume") {
    if (!subscription) return;
    setIsUpdating(true);
    setActionError(null);
    try {
      if (action === "cancel") {
        await cancelSubscription(subscription.id);
      } else {
        await resumeSubscription(subscription.id);
      }
      await refreshAccess();
    } catch {
      setActionError(
        action === "cancel"
          ? "Не удалось отключить автопродление. Попробуйте позже."
          : "Не удалось возобновить автопродление. Попробуйте позже.",
      );
    } finally {
      setIsUpdating(false);
    }
  }

  const statusDescription = accessError
    ? "Не удалось получить статус доступа. Попробуйте обновить страницу или повторить проверку позже."
    : access?.access_state === "past_due"
      ? "Не удалось продлить Plus. Оформите подписку заново, чтобы восстановить доступ."
      : access?.access_state === "plus_expired"
        ? "Срок Plus истёк. Можно оформить подписку заново."
        : access?.access_state === "plus_suspended"
          ? "Plus приостановлен. Обратитесь в поддержку, чтобы уточнить дальнейшие действия."
          : access?.access_state === "cancel_scheduled"
            ? "Автопродление отключено, но полный отчёт открыт до конца оплаченного периода."
            : isPlusActive
              ? "Оплата подтверждена сервером: полный личный отчёт открыт для этого аккаунта."
              : "Plus не активен. Доступ открывается по месячной подписке.";

  return (
    <ProductSurfaceCard className="border-accent-gold bg-[var(--hero-background)]">
      <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
        <div className="flex items-start gap-4">
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-accent-gold bg-accent-gold-soft text-accent-gold">
            <Crown className="h-5 w-5" />
          </span>
          <div className="space-y-2">
            <SurfaceEyebrow>Текущий статус аккаунта</SurfaceEyebrow>
            <h2 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-text-primary">
              {isLoadingAccess
                ? "Проверяем Plus"
                : isPlusActive
                  ? "Plus активен"
                  : "Plus не активен"}
            </h2>
            <p className="max-w-3xl text-sm leading-6 text-text-secondary">
              {statusDescription}
            </p>
          </div>
        </div>
        <span
          className={
            isPlusActive
              ? "rounded-full border border-success bg-success/10 px-4 py-2 text-sm font-semibold text-success"
              : "rounded-full border border-border-default bg-surface-subtle px-4 py-2 text-sm font-semibold text-text-secondary"
          }
        >
          {isPlusActive ? "Аккаунт Plus" : "Базовый аккаунт"}
        </span>
      </div>
      <dl className="mt-6 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-2xl border border-border-default bg-surface-subtle p-4">
          <dt className="text-text-muted">План</dt>
          <dd className="mt-1 font-medium text-text-primary">
            Astrotype Plus · 999 ₽ / месяц
          </dd>
        </div>
        <div className="rounded-2xl border border-border-default bg-surface-subtle p-4">
          <dt className="text-text-muted">Plus активен до</dt>
          <dd className="mt-1 font-medium text-text-primary">
            {formatBillingDate(subscription?.current_period_end ?? null)}
          </dd>
        </div>
        <div className="rounded-2xl border border-border-default bg-surface-subtle p-4">
          <dt className="text-text-muted">Следующее списание</dt>
          <dd className="mt-1 font-medium text-text-primary">
            {subscription?.cancel_at_period_end
              ? "Автопродление отключено"
              : formatBillingDate(subscription?.next_billing_at ?? null)}
          </dd>
        </div>
      </dl>
      {canCancel || canResume ? (
        <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button
            type="button"
            variant="outline"
            disabled={isUpdating}
            onClick={() => void updateRenewal(canCancel ? "cancel" : "resume")}
          >
            {isUpdating
              ? "Обновляем…"
              : canCancel
                ? "Отменить автопродление"
                : "Возобновить автопродление"}
          </Button>
          <p className="text-xs leading-5 text-text-muted">
            Отключение автопродления не сокращает уже оплаченный период.
          </p>
        </div>
      ) : null}
      {actionError ? (
        <p className="mt-3 text-sm text-error" role="alert">
          {actionError}
        </p>
      ) : null}
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
          <ProductSurfaceCard className="space-y-5 border-accent-gold bg-surface-subtle">
            <p className="text-xs uppercase tracking-[0.28em] text-text-secondary">
              Цена Плюс
            </p>
            <div className="flex items-end gap-2">
              <span className="text-6xl font-semibold tracking-tight text-text-primary">
                999 ₽
              </span>
              <span className="pb-2 text-sm text-text-secondary">/ месяц</span>
            </div>
            <p className="text-sm leading-6 text-text-secondary">
              Оплата открывается в YooKassa. После подтверждения статус аккаунта
              обновится автоматически.
            </p>
            <div id="plus">
              <BillingCheckoutButton />
            </div>
          </ProductSurfaceCard>
        }
      >
        <div className="grid gap-3 pt-2 text-sm text-text-secondary sm:grid-cols-3">
          {[
            "без данных карты в Astrotype",
            "возврат не равен успеху оплаты",
            "доступ включается после проверки",
          ].map((item) => (
            <div
              key={item}
              className="rounded-2xl border border-border-default bg-surface-subtle px-4 py-3"
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
            <h2 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-text-primary">
              Базовый статус
            </h2>
            <p className="text-sm leading-6 text-text-secondary">
              Подходит, чтобы войти в продукт, создать профиль и увидеть первый
              слой карты без ощущения закрытой двери.
            </p>
          </div>
          <FeatureList items={freeFeatures} />
          <Button variant="outline" asChild>
            <Link href="/dashboard">Вернуться в кабинет</Link>
          </Button>
        </ProductSurfaceCard>

        <ProductSurfaceCard className="space-y-6 border-accent-gold bg-accent-gold-soft">
          <div className="space-y-2">
            <SurfaceEyebrow>Плюс</SurfaceEyebrow>
            <h2 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-text-primary">
              Полный личный отчёт
            </h2>
            <p className="text-sm leading-6 text-text-secondary">
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
          <h2 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-text-primary">
            Сначала подтверждение, потом доступ
          </h2>
          <p className="text-sm leading-7 text-text-secondary">
            Эта страница может показать, что вы вернулись из YooKassa, но не
            делает вывод об оплате сама. Astrotype ждёт проверенный статус и
            только потом меняет доступ.
          </p>
        </ProductSurfaceCard>

        <div className="grid gap-4">
          {trustSteps.map((step, index) => (
            <ProductSurfaceCard key={step.title} className="flex gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accent-gold-soft text-sm font-semibold text-accent-gold">
                {index + 1}
              </div>
              <div className="space-y-2">
                <h3 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-text-primary">
                  {step.title}
                </h3>
                <p className="text-sm leading-6 text-text-secondary">
                  {step.text}
                </p>
              </div>
            </ProductSurfaceCard>
          ))}
        </div>
      </section>

      <section className="rounded-[28px] border border-info bg-info/10 p-6 md:p-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2">
            <p className="flex items-center gap-2 text-sm font-semibold text-text-primary">
              <ShieldCheck className="h-4 w-4 text-link" />
              Бесплатный статус и Плюс сейчас не режут продукт по скрытым
              правилам
            </p>
            <p className="max-w-3xl text-sm leading-6 text-text-secondary">
              Статус виден в аккаунте, а доступ к платным материалам проверяется
              на стороне сервиса. Так пользователь не зависит от случайного
              состояния страницы после оплаты.
            </p>
          </div>
          <div className="flex items-center gap-2 text-sm text-text-secondary">
            <Clock3 className="h-4 w-4 text-accent-gold" />
            Проверка обычно занимает меньше минуты
          </div>
        </div>
      </section>
    </div>
  );
}
