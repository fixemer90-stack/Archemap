/** External enablement and legal approval are independent, explicit gates.
 * No defaults constitute policy approval; versions must be owner-approved.
 */
export function readConfig(input: Record<string, unknown>) {
  const counterId =
    typeof input.counterId === "string" &&
    /^[1-9][0-9]{0,14}(?![\s\S])/.test(input.counterId)
      ? Number(input.counterId)
      : null;
  const policyVersion =
    typeof input.policyVersion === "string" &&
    /^[a-zA-Z0-9._-]{1,64}(?![\s\S])/.test(input.policyVersion)
      ? input.policyVersion
      : null;
  return {
    enabled:
      input.enabled === "true" &&
      input.externalEnabled === "true" &&
      input.settingsVerified === "true" &&
      input.policyApproved === "true" &&
      counterId !== null &&
      policyVersion !== null,
    counterId,
    policyVersion,
  };
}
export type PrivacyConfig = ReturnType<typeof readConfig>;
export function isPublicPath(path: string): boolean {
  return path === "/";
}
/** Identify canonical public context. The actual SDK admission also requires
 * current and original document URLs to already equal the clean value. */
export function safeContext(
  href: string,
  referrer: string,
): { href: string; referrer: string } | null {
  try {
    const url = new URL(href);
    if (
      !isPublicPath(url.pathname) ||
      !["https:", "http:"].includes(url.protocol) ||
      url.username ||
      url.password
    )
      return null;
    const clean = `${url.origin}/`;
    if (referrer && referrer !== clean) return null;
    return { href: clean, referrer };
  } catch {
    return null;
  }
}
export function hasConsent(raw: string | null, version: string): boolean {
  try {
    const value: unknown = JSON.parse(raw ?? "null");
    return (
      typeof value === "object" &&
      value !== null &&
      "version" in value &&
      value.version === version &&
      "granted" in value &&
      value.granted === true
    );
  } catch {
    return false;
  }
}
export const CONSENT_KEY = "astrotype.analytics.consent";
export const ATTRIBUTION_KEY = "astrotype.analytics.attribution";
export const REVOKE_PENDING_KEY = "astrotype.analytics.revoke-pending";
export const GOALS = [
  "landing_view",
  "signup_cta_click",
  "plus_interest_click",
] as const;
export type Goal = (typeof GOALS)[number];
export function safeGoal(value: unknown): Goal | null {
  return GOALS.find((goal) => goal === value) ?? null;
}
/** No arbitrary UTM, referrer, URL, account IDs or financial facts. Campaign
 * allowlist intentionally empty until reviewed codes are approved. */
export function attribution(
  clientId: unknown,
  version: string,
  campaign?: unknown,
) {
  void campaign;
  return {
    version,
    clientId:
      typeof clientId === "string" && /^[0-9]{1,32}(?![\s\S])/.test(clientId)
        ? clientId
        : null,
    campaign: null,
  };
}
