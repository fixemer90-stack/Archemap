import { api } from "@/lib/api-client";

export type PaymentStatus =
  "pending" | "waiting_for_capture" | "succeeded" | "canceled" | "failed";

export type PaymentResponse = {
  id: string;
  provider: string;
  provider_payment_id: string | null;
  amount: number;
  currency: string;
  status: PaymentStatus | string;
  description: string | null;
  confirmation_url: string | null;
  payment_method_type: string | null;
  paid_at: string | null;
  created_at: string;
};

export type BillingAccessState =
  | "free"
  | "checkout_pending"
  | "plus_active"
  | "payment_failed"
  | "plus_inactive";

export type BillingEntitlementSummary = {
  product: string;
  status: string;
  starts_at: string | null;
  expires_at: string | null;
};

export type BillingPaymentSummary = {
  id: string;
  product_id: string | null;
  product: string | null;
  status: string;
  created_at: string;
  paid_at: string | null;
};

export type BillingAccessResponse = {
  account_tier: "free" | "plus" | string;
  access_state: BillingAccessState;
  entitlements: BillingEntitlementSummary[];
  latest_payment: BillingPaymentSummary | null;
};

type CreatePaymentRequest = {
  product_id: string;
  return_url?: string;
};

export function createPayment(
  request: CreatePaymentRequest,
): Promise<PaymentResponse> {
  return api.post<PaymentResponse>("/api/v1/payments", request);
}

export function getBillingAccess(): Promise<BillingAccessResponse> {
  return api.get<BillingAccessResponse>("/api/v1/billing/access");
}
