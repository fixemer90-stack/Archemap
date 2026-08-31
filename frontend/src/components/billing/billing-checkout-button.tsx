"use client";

import { useState } from "react";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { createPayment } from "@/lib/api/payments";

const PLUS_PRODUCT_ID = "self_full";

function getBillingReturnUrl(): string {
  const url = new URL("/billing", window.location.origin);
  url.searchParams.set("checkout", "return");
  return url.toString();
}

function getCheckoutErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return "Чтобы оформить Plus, войдите в аккаунт.";
    }
    return error.message || "Не удалось создать оплату.";
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "Не удалось создать оплату.";
}

export function BillingCheckoutButton() {
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleCheckout() {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const payment = await createPayment({
        product_id: PLUS_PRODUCT_ID,
        return_url: getBillingReturnUrl(),
      });

      if (!payment.confirmation_url) {
        throw new Error("Платёж создан, но YooKassa не вернула ссылку оплаты.");
      }

      window.location.assign(payment.confirmation_url);
    } catch (error) {
      setErrorMessage(getCheckoutErrorMessage(error));
      setIsLoading(false);
    }
  }

  return (
    <div className="mt-7 space-y-3">
      <Button
        className="w-full"
        type="button"
        onClick={handleCheckout}
        disabled={isLoading}
        aria-busy={isLoading}
      >
        {isLoading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Открываем оплату…
          </>
        ) : (
          "Оформить Plus"
        )}
      </Button>
      {errorMessage ? (
        <p className="text-xs leading-5 text-[#FFB4A8]" role="alert">
          {errorMessage}
        </p>
      ) : null}
    </div>
  );
}
