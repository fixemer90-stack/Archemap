import {
  ATTRIBUTION_KEY,
  CONSENT_KEY,
  REVOKE_PENDING_KEY,
  hasConsent,
} from "./privacy";

const RECEIPT = /^[A-Za-z0-9_-]{43}(?![\s\S])/;
const RECEIPT_TTL_MS = 30 * 60 * 1000;
type Snapshot = {
  receipt: string;
  version: string;
  known: boolean;
  sourceCounterId?: string;
  expiresAt: number;
};
type AttachResult = "attached" | "gone" | "retry";
let attaching: { receipt: string; result: Promise<AttachResult> } | null = null;

async function write(path: string, body: Record<string, unknown>) {
  try {
    return await fetch(`/api/v1/analytics/attribution/${path}`, {
      method: "POST",
      credentials: "same-origin",
      mode: "same-origin",
      redirect: "error",
      cache: "no-store",
      referrerPolicy: "no-referrer",
      headers: {
        "Content-Type": "application/json",
        "X-Analytics-Request": "1",
      },
      body: JSON.stringify(body),
      keepalive: true,
      signal: AbortSignal.timeout(2000),
    });
  } catch {
    return null;
  }
}

function takeSnapshot(): Snapshot | null {
  try {
    const item: unknown = JSON.parse(
      sessionStorage.getItem(ATTRIBUTION_KEY) ?? "null",
    );
    if (
      typeof item !== "object" ||
      item === null ||
      !("receipt" in item) ||
      typeof item.receipt !== "string" ||
      !RECEIPT.test(item.receipt) ||
      !("version" in item) ||
      typeof item.version !== "string"
    )
      return null;
    return {
      receipt: item.receipt,
      version: item.version,
      known: "known" in item && item.known === true,
      sourceCounterId:
        "sourceCounterId" in item && typeof item.sourceCounterId === "string"
          ? item.sourceCounterId
          : undefined,
      // Receipts written before this fix have no local clock; the server is authoritative.
      expiresAt:
        "expiresAt" in item && typeof item.expiresAt === "number"
          ? item.expiresAt
          : 0,
    };
  } catch {
    return null;
  }
}

export async function captureLandingAttribution(
  clientId: string | null,
  version: string,
  stillAllowed: () => boolean,
  sourceCounterId?: string,
) {
  // A future isolated adapter must supply the actual counter used for getClientID.
  const source = clientId === null ? undefined : sourceCounterId;
  if (
    !stillAllowed() ||
    (clientId !== null && !/^[1-9][0-9]{0,18}(?![\s\S])/.test(source ?? ""))
  )
    return;
  const previous = takeSnapshot();
  if (
    previous?.version === version &&
    (previous.expiresAt === 0 || Date.now() < previous.expiresAt) &&
    (clientId === null ||
      (previous.known && previous.sourceCounterId === source))
  ) {
    if ((await attach(previous)) !== "gone" || !stillAllowed()) return;
  }
  const expiresAt = Date.now() + RECEIPT_TTL_MS;
  const response = await write("capture", {
    granted: true,
    policy_version: version,
    client_id: clientId,
    ...(source === undefined ? {} : { source_counter_id: source }),
  });
  if (!response?.ok) return;
  try {
    const data: unknown = await response.json();
    if (
      typeof data !== "object" ||
      data === null ||
      !("receipt" in data) ||
      typeof data.receipt !== "string" ||
      !RECEIPT.test(data.receipt)
    )
      return;
    const receipt = data.receipt;
    if (!stillAllowed()) {
      void write("discard", { receipt });
      return;
    }
    try {
      sessionStorage.setItem(
        ATTRIBUTION_KEY,
        JSON.stringify({
          receipt,
          version,
          known: clientId !== null,
          sourceCounterId: source,
          expiresAt,
        } satisfies Snapshot),
      );
    } catch {
      void write("discard", { receipt });
      return;
    }
    if (previous) void write("discard", { receipt: previous.receipt });
    await attachPendingAttribution();
  } catch {
    // No analytics error interrupts the landing page or auth flow.
  }
}

/** First-party only. No SDK imports and no snapshot means no request. */
export async function attachPendingAttribution() {
  const snapshot = takeSnapshot();
  if (snapshot) await attach(snapshot);
}

async function attach(snapshot: Snapshot): Promise<AttachResult> {
  const { receipt } = snapshot;
  if (attaching?.receipt === receipt) return attaching.result;
  const result = sendAttach(snapshot);
  attaching = { receipt, result };
  try {
    return await result;
  } finally {
    if (attaching?.result === result) attaching = null;
  }
}

async function sendAttach({
  receipt,
  version,
}: Snapshot): Promise<AttachResult> {
  try {
    if (
      sessionStorage.getItem(REVOKE_PENDING_KEY) === "1" ||
      !hasConsent(localStorage.getItem(CONSENT_KEY), version)
    )
      return "retry";
    const response = await write("attach", { receipt });
    const result = response?.ok
      ? "attached"
      : response?.status === 404
        ? "gone"
        : "retry";
    if (result !== "retry" && takeSnapshot()?.receipt === receipt)
      sessionStorage.removeItem(ATTRIBUTION_KEY);
    return result;
  } catch {
    // Storage disabled: ordinary auth stays available.
    return "retry";
  }
}

export async function discardPendingAttribution() {
  const pending = takeSnapshot();
  try {
    sessionStorage.removeItem(ATTRIBUTION_KEY);
  } catch {
    /* TTL still applies */
  }
  if (pending) await write("discard", { receipt: pending.receipt });
}

/** Browser revocation is immediate. The signed-in owner write is independent. */
export async function revokeLandingAttribution() {
  try {
    localStorage.removeItem("astrotype.analytics.captured-version"); // Legacy latch; never read.
  } catch {
    /* local consent still stops */
  }
  void discardPendingAttribution();
  return (await write("revoke", {}))?.ok === true;
}
