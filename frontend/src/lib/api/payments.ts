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
  | "cancel_scheduled"
  | "past_due"
  | "payment_failed"
  | "plus_inactive"
  | "plus_expired"
  | "plus_suspended";

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

export type BillingSubscriptionSummary = {
  id: string;
  plan_code: string;
  status: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  next_billing_at: string | null;
  grace_until: string | null;
};

export type BillingAccessResponse = {
  account_tier: "free" | "plus" | string;
  access_state: BillingAccessState;
  subscription: BillingSubscriptionSummary | null;
  entitlements: BillingEntitlementSummary[];
  latest_payment: BillingPaymentSummary | null;
};

type CreatePaymentRequest = {
  product_id: string;
  return_url?: string;
};

type SubscriptionCheckoutRequest = {
  plan_code: string;
  return_url?: string;
};

type SubscriptionCheckoutResponse = {
  subscription_id: string;
  payment_id: string;
  status: string;
  confirmation_url: string;
  current_period_start: string | null;
  current_period_end: string | null;
};

export function createPayment(
  request: CreatePaymentRequest,
): Promise<PaymentResponse> {
  return api.post<PaymentResponse>("/api/v1/payments", request);
}

export function getBillingAccess(): Promise<BillingAccessResponse> {
  return api.get<BillingAccessResponse>("/api/v1/billing/access");
}

export function createSubscriptionCheckout(
  request: SubscriptionCheckoutRequest,
): Promise<SubscriptionCheckoutResponse> {
  return api.post<SubscriptionCheckoutResponse>(
    "/api/v1/subscriptions/checkout",
    request,
  );
}

export function cancelSubscription(
  subscriptionId: string,
  reason = "user_request",
): Promise<BillingSubscriptionSummary> {
  return api.post<BillingSubscriptionSummary>(
    `/api/v1/subscriptions/${subscriptionId}/cancel`,
    { reason },
  );
}

export function resumeSubscription(
  subscriptionId: string,
): Promise<BillingSubscriptionSummary> {
  return api.post<BillingSubscriptionSummary>(
    `/api/v1/subscriptions/${subscriptionId}/resume`,
    {},
  );
}
