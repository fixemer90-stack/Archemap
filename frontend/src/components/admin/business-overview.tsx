"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { ApiError } from "@/lib/api-client";
import {
  getAdminBusinessOverview,
  type AdminBusinessOverview,
} from "@/lib/api/admin-business";
import styles from "./business-overview.module.css";

type OverviewState =
  | { kind: "loading" | "unauthenticated" | "denied" | "error" }
  | { kind: "ready"; overview: AdminBusinessOverview };

type Money = AdminBusinessOverview["live_cash_received"];

const number = new Intl.NumberFormat("ru-RU");
const percent = new Intl.NumberFormat("ru-RU", {
  style: "percent",
  maximumFractionDigits: 2,
});
const coverageLabels = {
  unavailable: "Покрытие недоступно",
  stale: "Данные устарели",
  observed: "Данные наблюдаются",
};
const activationLabels = {
  available: "Нет данных",
  insufficient_history: "7 дней наблюдения ещё не прошли",
  no_data: "Нет регистраций в когорте",
  unavailable: "Нет данных",
};
const plusLabels = {
  unavailable: "Нет данных",
  partial: "Неполное покрытие платных периодов",
  observed: "Подтверждённые платные периоды",
};

function count(value: number | null) {
  return value === null ? "Нет данных" : number.format(value);
}

function activationRate({
  rate,
  status,
}: AdminBusinessOverview["activation_d7"]) {
  if (status !== "available" || rate === null) return activationLabels[status];
  const share = Number(rate);
  if (share > 0 && share < 0.0001) return "< 0,01 %";
  if (share < 1 && share > 0.9999) return "> 99,99 %";
  return percent.format(share);
}

function money(buckets: Money, emptyLabel: string) {
  if (buckets === null) return "Нет данных";
  if (buckets.length === 0) return emptyLabel;
  return (
    <ul className={styles.amounts} role="list">
      {buckets.map(({ currency, amount }) => (
        <li key={currency}>
          {amount} {currency}
        </li>
      ))}
    </ul>
  );
}

function MetricGroup({
  title,
  note,
  metrics,
}: {
  title: string;
  note?: string;
  metrics: (readonly [label: string, value: ReactNode])[];
}) {
  return (
    <section className={styles.card}>
      <h2>{title}</h2>
      {note && <p className={styles.muted}>{note}</p>}
      <dl className={styles.metrics}>
        {metrics.map(([label, value]) => (
          <div className={styles.metric} key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function OverviewDetails({ overview }: { overview: AdminBusinessOverview }) {
  const {
    timezone,
    coverage,
    registrations,
    activation_d7: activation,
    checkout_outcomes: outcomes,
    payments,
    paid_plus: plus,
    reports,
  } = overview;
  const dateTime = new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: timezone,
  });
  const cohortDate = new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "medium",
    timeZone: "UTC",
  });
  const time = (value: string | null) =>
    value === null ? (
      "Нет данных"
    ) : (
      <time dateTime={value}>{dateTime.format(new Date(value))}</time>
    );
  const cohortTime = (value: string) => (
    <time dateTime={value}>{cohortDate.format(new Date(value))}</time>
  );
  const cash = overview.live_cash_received;
  const cashNotes = [
    coverage.status !== "unavailable" && !coverage.window_complete
      ? "Неполное покрытие периода."
      : null,
    payments.unknown !== null && payments.unknown > 0
      ? "Есть платежи с неизвестным режимом."
      : null,
  ].filter(Boolean);

  return (
    <>
      <section className={styles.coverage} aria-labelledby="overview-coverage">
        <div>
          <h2 id="overview-coverage">Период и покрытие</h2>
          <p className={styles.badge} data-status={coverage.status}>
            {coverageLabels[coverage.status]}
          </p>
          {!coverage.window_complete && (
            <p className={styles.muted}>
              Покрытие периода неполное. Отсутствие данных не означает ноль.
            </p>
          )}
        </div>
        <dl className={styles.period}>
          <div>
            <dt>Период · {timezone}</dt>
            <dd>
              {time(overview.window_from)} — {time(overview.window_to)}{" "}
              <span className={styles.muted}>(конец не включён)</span>
            </dd>
          </div>
          <div>
            <dt>Срез на</dt>
            <dd>{time(overview.as_of)}</dd>
          </div>
          <div>
            <dt>Последняя запись</dt>
            <dd>{time(coverage.latest_recorded_at)}</dd>
          </div>
          <div>
            <dt>Начало покрытия</dt>
            <dd>{time(coverage.since)}</dd>
          </div>
        </dl>
      </section>
      <div className={styles.grid}>
        <div className={styles.column}>
          <MetricGroup
            title="Регистрации"
            metrics={[
              ["По email", count(registrations.email)],
              ["Через внешний аккаунт", count(registrations.oauth)],
              ["Способ неизвестен", count(registrations.unknown)],
              ["Подтверждения email", count(overview.verified)],
            ]}
          />
          <MetricGroup
            title="Активация за 7 дней"
            note="Доля зарегистрированных, получивших рабочий базовый расчёт в первые 7 дней. Доля доступна после окончания наблюдения для всей когорты."
            metrics={[
              [
                "Даты регистрации",
                <>
                  {cohortTime(activation.cohort_from)} —{" "}
                  {cohortTime(activation.cohort_to)} (конец не включён)
                </>,
              ],
              ["Доля активации", activationRate(activation)],
              ["Завершено наблюдение", count(activation.mature_count)],
              ["Ещё наблюдаются", count(activation.immature_count)],
              [
                "Активировались среди завершивших наблюдение",
                count(activation.activated_count),
              ],
            ]}
          />
          <MetricGroup
            title="Формирование отчётов"
            note="Запросы и результаты учитываются по дате каждого события. Доставка и прочтение отчётов не отслеживаются в этом обзоре."
            metrics={[
              ["Принятые запросы", count(reports.requested)],
              ["Готовые отчёты", count(reports.ready)],
              ["Частично готовые отчёты", count(reports.partial)],
              ["Ошибки формирования", count(reports.failed)],
            ]}
          />
        </div>
        <div className={styles.column}>
          <MetricGroup
            title="Исходы начатых оплат"
            note="Текущий статус оплат, начатых за выбранный период. Подтверждение здесь не означает реальное денежное поступление."
            metrics={[
              ["Начатые оплаты", count(overview.checkouts)],
              ["Ожидают завершения", count(outcomes.pending)],
              ["Не завершились оплатой", count(outcomes.failed)],
              ["Оплата подтверждена", count(outcomes.confirmed)],
              ["Исход неизвестен", count(outcomes.unknown)],
            ]}
          />
          <MetricGroup
            title="Платежи и возвраты"
            note="Суммы отражают только реальные поступления, отдельно по валютам. Тестовые платежи не учитываются в суммах."
            metrics={[
              ["Реальные платежи", count(payments.live)],
              ["Тестовые платежи", count(payments.test)],
              ["Режим неизвестен", count(payments.unknown)],
              [
                "Получено",
                <>
                  {money(cash, "Нет реальных поступлений")}
                  {cash === null && cashNotes.length > 0 && (
                    <>
                      {" "}
                      <span className={styles.muted}>
                        {cashNotes.join(" ")}
                      </span>
                    </>
                  )}
                </>,
              ],
              [
                "Подтверждённые возвраты",
                money(overview.live_refunds, "Нет подтверждённых возвратов"),
              ],
            ]}
          />
          <MetricGroup
            title="Платный Plus"
            note="Действующие оплаченные периоды на дату среза, а не количество платежей за период."
            metrics={[
              ["Активные платные доступы", count(plus.active)],
              ...(plus.status === "partial"
                ? [
                    [
                      "Подтверждённый минимум",
                      count(plus.proven_active),
                    ] as const,
                  ]
                : []),
              ["Покрытие", plusLabels[plus.status]],
              ["Ежемесячная регулярная выручка (MRR)", "Не подтверждена"],
            ]}
          />
        </div>
      </div>
      <p className={styles.footnote}>
        Оценочные затраты не входят в этот обзор.
      </p>
    </>
  );
}

export function BusinessOverview() {
  const [state, setState] = useState<OverviewState>({ kind: "loading" });
  const [request, setRequest] = useState(0);
  const inFlight = useRef<{
    attempt: number;
    result: Promise<AdminBusinessOverview>;
  } | null>(null);

  useEffect(() => {
    let current = true;
    if (inFlight.current?.attempt !== request) {
      inFlight.current = {
        attempt: request,
        result: getAdminBusinessOverview(),
      };
    }
    inFlight.current.result.then(
      (overview) => {
        if (current) setState({ kind: "ready", overview });
      },
      (error: unknown) => {
        if (!current) return;
        if (error instanceof ApiError && error.status === 401) {
          setState({ kind: "unauthenticated" });
        } else if (error instanceof ApiError && error.status === 403) {
          setState({ kind: "denied" });
        } else {
          setState({ kind: "error" });
        }
      },
    );
    return () => {
      current = false;
    };
  }, [request]);

  const busy = state.kind === "loading";
  const canReload =
    state.kind === "error" || state.kind === "ready" || (busy && request > 0);

  return (
    <div className={styles.shell}>
      <main className={styles.page}>
        <Link className={styles.link} href="/dashboard" prefetch={false}>
          В личный кабинет
        </Link>
        <header className={styles.header}>
          <div>
            <p className={styles.eyebrow}>Администрирование</p>
            <h1>Бизнес-обзор</h1>
            <p className={styles.muted}>
              Регистрации, активация, платежи и формирование отчётов.
            </p>
          </div>
          {canReload && (
            <button
              type="button"
              className={styles.button}
              aria-disabled={busy}
              onClick={() => {
                if (busy) return;
                setState({ kind: "loading" });
                setRequest((previous) => previous + 1);
              }}
            >
              {busy
                ? "Загружаем…"
                : state.kind === "ready"
                  ? "Обновить данные"
                  : "Повторить запрос"}
            </button>
          )}
        </header>
        {busy && (
          <p role="status" className={styles.notice}>
            Загружаем бизнес-показатели…
          </p>
        )}
        {state.kind === "unauthenticated" && (
          <div className={styles.notice}>
            <p role="alert">Войдите, чтобы открыть бизнес-обзор.</p>
            <Link
              className={styles.link}
              href="/login?next=%2Fadmin%2Fbusiness"
              prefetch={false}
            >
              Войти
            </Link>
          </div>
        )}
        {state.kind === "denied" && (
          <p role="alert" className={styles.notice}>
            Нет доступа. Бизнес-обзор доступен только администраторам.
          </p>
        )}
        {state.kind === "error" && (
          <p role="alert" className={styles.notice}>
            Данные недоступны. Повторите запрос позже.
          </p>
        )}
        {state.kind === "ready" && (
          <OverviewDetails overview={state.overview} />
        )}
      </main>
    </div>
  );
}
