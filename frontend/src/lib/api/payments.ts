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

type CreatePaymentRequest = {
  product_id: string;
  return_url?: string;
};

export function createPayment(
  request: CreatePaymentRequest,
): Promise<PaymentResponse> {
  return api.post<PaymentResponse>("/api/v1/payments", request);
}
