import type { AdminBusinessOverview } from "../../../src/lib/api/admin-business";

export const observedOverview = {
  as_of: "2026-11-22T00:00:00Z",
  window_from: "2026-10-23T21:00:00Z",
  window_to: "2026-11-22T00:00:00Z",
  timezone: "Europe/Moscow",
  coverage: {
    status: "observed",
    latest_recorded_at: "2026-11-21T23:59:00Z",
    since: "2026-10-01T12:00:00Z",
    window_complete: true,
  },
  registrations: { email: 16, oauth: 7, unknown: 0 },
  verified: 14,
  activation_d7: {
    cohort_from: "2026-10-16",
    cohort_to: "2026-11-15",
    mature_count: 8,
    immature_count: 0,
    activated_count: 3,
    rate: "0.375",
    status: "available",
  },
  checkouts: 13,
  checkout_outcomes: { pending: 4, failed: 3, confirmed: 5, unknown: 1 },
  payments: { live: 4, test: 2, unknown: 0 },
  live_cash_received: [
    { currency: "RUB", amount: "9007199254740993.01" },
    { currency: "USD", amount: "59.20" },
  ],
  live_refunds: null,
  paid_plus: {
    active: 3,
    proven_active: 3,
    status: "observed",
    mrr_status: "not_certified",
  },
  reports: { requested: 12, ready: 8, partial: 3, failed: 1 },
} satisfies AdminBusinessOverview;

export const unavailableOverview = {
  as_of: "2026-11-23T00:00:00Z",
  window_from: "2026-11-21T21:00:00Z",
  window_to: "2026-11-22T21:00:00Z",
  timezone: "Europe/Moscow",
  coverage: {
    status: "unavailable",
    latest_recorded_at: null,
    since: null,
    window_complete: false,
  },
  registrations: { email: null, oauth: null, unknown: null },
  verified: null,
  activation_d7: {
    cohort_from: "2026-11-14",
    cohort_to: "2026-11-15",
    mature_count: null,
    immature_count: null,
    activated_count: null,
    rate: null,
    status: "unavailable",
  },
  checkouts: null,
  checkout_outcomes: {
    pending: null,
    failed: null,
    confirmed: null,
    unknown: null,
  },
  payments: { live: null, test: null, unknown: null },
  live_cash_received: null,
  live_refunds: null,
  paid_plus: {
    active: null,
    proven_active: null,
    status: "unavailable",
    mrr_status: "not_certified",
  },
  reports: { requested: null, ready: null, partial: null, failed: null },
} satisfies AdminBusinessOverview;

export const staleOverview = {
  ...observedOverview,
  coverage: {
    ...observedOverview.coverage,
    status: "stale",
    latest_recorded_at: "2026-11-21T19:30:00Z",
  },
  activation_d7: {
    cohort_from: "2026-11-18",
    cohort_to: "2026-11-19",
    mature_count: 0,
    immature_count: 4,
    activated_count: 0,
    rate: null,
    status: "insufficient_history",
  },
  checkouts: 3,
  checkout_outcomes: { pending: 0, failed: 0, confirmed: 3, unknown: 0 },
  payments: { live: 0, test: 3, unknown: 0 },
  live_cash_received: [],
  paid_plus: { ...observedOverview.paid_plus, active: 0, proven_active: 0 },
} satisfies AdminBusinessOverview;

export const unknownReceiptsOverview = {
  ...observedOverview,
  payments: { ...observedOverview.payments, unknown: 2 },
  live_cash_received: null,
  paid_plus: {
    ...observedOverview.paid_plus,
    active: null,
    status: "partial",
  },
} satisfies AdminBusinessOverview;

export const incompleteWindowOverview = {
  ...observedOverview,
  coverage: {
    ...observedOverview.coverage,
    since: "2026-10-26T12:00:00Z",
    window_complete: false,
  },
  activation_d7: {
    ...unavailableOverview.activation_d7,
    cohort_from: observedOverview.activation_d7.cohort_from,
    cohort_to: observedOverview.activation_d7.cohort_to,
  },
  live_cash_received: null,
  paid_plus: {
    ...unknownReceiptsOverview.paid_plus,
    proven_active: 0,
  },
} satisfies AdminBusinessOverview;
