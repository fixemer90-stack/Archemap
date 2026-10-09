"use client";

import { useCallback, useEffect, useState } from "react";

import {
  getBillingAccess,
  type BillingAccessResponse,
} from "@/lib/api/payments";

export function useBillingAccess() {
  const [access, setAccess] = useState<BillingAccessResponse | null>(null);
  const [isLoadingAccess, setIsLoadingAccess] = useState(true);
  const [accessError, setAccessError] = useState(false);

  const refreshAccess = useCallback(async () => {
    setIsLoadingAccess(true);
    setAccessError(false);

    try {
      const nextAccess = await getBillingAccess();
      setAccess(nextAccess);
    } catch {
      setAccessError(true);
    } finally {
      setIsLoadingAccess(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchInitialAccess() {
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

    void fetchInitialAccess();
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    access,
    isLoadingAccess,
    accessError,
    isPlusActive:
      access?.access_state === "plus_active" ||
      access?.access_state === "cancel_scheduled",
    refreshAccess,
  };
}
