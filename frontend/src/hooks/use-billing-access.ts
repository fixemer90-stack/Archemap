"use client";

import { useEffect, useState } from "react";

import {
  getBillingAccess,
  type BillingAccessResponse,
} from "@/lib/api/payments";

export function useBillingAccess() {
  const [access, setAccess] = useState<BillingAccessResponse | null>(null);
  const [isLoadingAccess, setIsLoadingAccess] = useState(true);
  const [accessError, setAccessError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetchAccess() {
      setIsLoadingAccess(true);
      setAccessError(false);

      try {
        const nextAccess = await getBillingAccess();
        if (!cancelled) {
          setAccess(nextAccess);
        }
      } catch {
        if (!cancelled) {
          setAccessError(true);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingAccess(false);
        }
      }
    }

    void fetchAccess();

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    access,
    isLoadingAccess,
    accessError,
    isPlusActive: access?.access_state === "plus_active",
  };
}
