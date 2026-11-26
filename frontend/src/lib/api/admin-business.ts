import { z } from "zod";

import { apiClient } from "@/lib/api-client";

const count = z.int().nonnegative().nullable();
const instant = z.iso.datetime({ offset: true });
const decimal = z.string().regex(/^-?\d+(\.\d+)?$/);
const money = z.array(
  z.object({ currency: z.string().regex(/^[A-Z]{3}$/), amount: decimal }),
);

const overviewSchema = z.object({
  as_of: instant,
  window_from: instant,
  window_to: instant,
  timezone: z.enum(["Europe/Moscow", "UTC"]),
  coverage: z.object({
    status: z.enum(["unavailable", "stale", "observed"]),
    latest_recorded_at: instant.nullable(),
    since: instant.nullable(),
    window_complete: z.boolean(),
  }),
  registrations: z.object({ email: count, oauth: count, unknown: count }),
  landing_documents: z
    .object({
      through_date: z.iso.date(),
      observed: z.int().positive().nullable(),
    })
    .nullish(),
  verified: count,
  activation_d7: z.object({
    cohort_from: z.iso.date(),
    cohort_to: z.iso.date(),
    mature_count: count,
    immature_count: count,
    activated_count: count,
    rate: z
      .string()
      .regex(/^\d+(\.\d+)?([eE][+-]?\d+)?$/)
      .refine((value) => Number(value) >= 0 && Number(value) <= 1)
      .nullable(),
    status: z.enum([
      "available",
      "insufficient_history",
      "no_data",
      "unavailable",
    ]),
  }),
  checkouts: count,
  checkout_outcomes: z.object({
    pending: count,
    failed: count,
    confirmed: count,
    unknown: count,
  }),
  payments: z.object({ live: count, test: count, unknown: count }),
  live_cash_received: money.nullable(),
  live_refunds: z.null(),
  paid_plus: z.object({
    active: count,
    proven_active: count,
    status: z.enum(["observed", "partial", "unavailable"]),
    mrr_status: z.literal("not_certified"),
  }),
  reports: z.object({
    requested: count,
    ready: count,
    partial: count,
    failed: count,
  }),
});

export type AdminBusinessOverview = z.infer<typeof overviewSchema>;

export async function getAdminBusinessOverview(): Promise<AdminBusinessOverview> {
  const payload = await apiClient<unknown>("/api/v1/admin/business/overview");
  return overviewSchema.parse(payload);
}
