"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { Button } from "@/components/ui/button";
import {
  captureLandingAttribution,
  discardPendingAttribution,
  revokeLandingAttribution,
} from "@/lib/analytics/first-party";
import {
  CONSENT_KEY,
  REVOKE_PENDING_KEY,
  hasConsent,
  safeContext,
} from "@/lib/analytics/privacy";

// No vendor adapter in the app origin: it could read persisted auth data and
// report identifiers even from a clean public document after opt-in.
const configuredVersion = process.env.NEXT_PUBLIC_ANALYTICS_POLICY_VERSION;
const policyVersion =
  process.env.NEXT_PUBLIC_ANALYTICS_ENABLED === "true" &&
  process.env.NEXT_PUBLIC_ANALYTICS_POLICY_APPROVED === "true" &&
  configuredVersion &&
  /^[a-zA-Z0-9._-]{1,64}(?![\s\S])/.test(configuredVersion)
    ? configuredVersion
    : null;
const consentEvent = "astrotype:analytics-consent";

let revokedInDocument = false;

function needsAccountRevoke() {
  try {
    return sessionStorage.getItem(REVOKE_PENDING_KEY) === "1";
  } catch {
    return false;
  }
}

function granted() {
  try {
    return (
      !revokedInDocument &&
      !needsAccountRevoke() &&
      policyVersion !== null &&
      hasConsent(localStorage.getItem(CONSENT_KEY), policyVersion)
    );
  } catch {
    return false;
  }
}

function subscribe(callback: () => void) {
  window.addEventListener("storage", callback);
  window.addEventListener(consentEvent, callback);
  return () => {
    window.removeEventListener("storage", callback);
    window.removeEventListener(consentEvent, callback);
  };
}

function safeDocument() {
  const clean = safeContext(location.href, document.referrer);
  return (
    clean?.href === location.href &&
    performance.getEntriesByType("navigation")[0]?.name === clean.href
  );
}

export function PublicAnalytics() {
  const consent = useSyncExternalStore(subscribe, granted, () => false);
  const revokePending = useSyncExternalStore(
    subscribe,
    needsAccountRevoke,
    () => false,
  );
  const hydrated = useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
  const [revoking, setRevoking] = useState(false);
  const [notice, setNotice] = useState<"confirmed" | "retry" | null>(null);

  useEffect(() => {
    if (!consent || policyVersion === null || !safeDocument()) return;
    let active = true;
    const allowed = () => active && granted() && safeDocument();
    const stop = () => {
      active = false;
    };
    const restore = (event: PageTransitionEvent) => {
      if (event.persisted && !granted()) void discardPendingAttribution();
    };
    const storageChanged = (event: StorageEvent) => {
      if ((event.key === CONSENT_KEY || event.key === null) && !granted()) {
        stop();
        void discardPendingAttribution();
      }
    };
    window.addEventListener("storage", storageChanged);
    window.addEventListener("pagehide", stop);
    window.addEventListener("pageshow", restore);
    void captureLandingAttribution(null, policyVersion, allowed);
    return () => {
      stop();
      window.removeEventListener("storage", storageChanged);
      window.removeEventListener("pagehide", stop);
      window.removeEventListener("pageshow", restore);
    };
  }, [consent]);

  const accept = () => {
    if (policyVersion === null || revokePending || revoking) return;
    try {
      localStorage.setItem(
        CONSENT_KEY,
        JSON.stringify({ version: policyVersion, granted: true }),
      );
      revokedInDocument = false;
      setNotice(null);
    } catch {
      /* Consent cannot be assumed when storage fails. */
    }
    window.dispatchEvent(new Event(consentEvent));
  };

  const revoke = async () => {
    if (revoking) return;
    revokedInDocument = true;
    setRevoking(true);
    setNotice(null);
    try {
      localStorage.removeItem(CONSENT_KEY);
    } catch {
      /* Local runtime already stopped. */
    }
    try {
      sessionStorage.setItem(REVOKE_PENDING_KEY, "1");
    } catch {
      /* Notice also kept in the document. */
    }
    window.dispatchEvent(new Event(consentEvent));
    const revoked = await revokeLandingAttribution();
    if (revoked) {
      try {
        sessionStorage.removeItem(REVOKE_PENDING_KEY);
      } catch {
        /* Storage is optional. */
      }
    }
    setNotice(revoked ? "confirmed" : "retry");
    setRevoking(false);
    window.dispatchEvent(new Event(consentEvent));
  };

  const retry = revokePending || notice === "retry";
  return (
    <aside
      aria-label="Необязательная аналитика"
      className="mt-7 space-y-3 text-sm text-text-secondary"
    >
      {policyVersion !== null && (
        <p>
          Необязательная аналитика: при входе согласие может быть привязано к
          аккаунту. Версия согласия: {policyVersion}.
        </p>
      )}
      {!revoking && retry && (
        <p role="status">
          Аналитика в браузере отключена. Если отзыв в аккаунте не подтверждён,
          войдите и повторите отзыв.
        </p>
      )}
      {notice === "confirmed" && (
        <p role="status">Согласие отозвано в браузере и в аккаунте.</p>
      )}
      <div className="flex flex-wrap gap-3">
        {policyVersion !== null && !consent && !retry && (
          <Button disabled={!hydrated || revoking} onClick={accept}>
            Разрешить аналитику
          </Button>
        )}
        <Button
          variant="ghost"
          disabled={!hydrated || revoking}
          onClick={() => void revoke()}
        >
          {retry && !revoking ? "Повторить отзыв" : "Отозвать согласие"}
        </Button>
      </div>
    </aside>
  );
}
