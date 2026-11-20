import type { Page, Route } from "@playwright/test";

export const savedCareerText =
  "Сохранённый вывод Career v1: работа с исследовательскими задачами и самостоятельными решениями.";
export const legacyReport = {
  id: "legacy-career-1",
  profile_id: "profile-1",
  product: "career",
  version: 3,
  status: "ready",
  mode: "full",
  archetype: "Исследователь",
  score: 0.73,
  confidence: 0.8,
  narrative: null,
  report_data: {
    claims: [
      {
        claim_id: "historical-claim",
        section: "strengths",
        archetype: "Исследователь",
        score: 0.73,
        confidence: { value: 0.8, label: "Высокая", reason_codes: [] },
        message: savedCareerText,
      },
    ],
  },
};

export async function mockLegacyCareer(
  page: Page,
  options: {
    status?: string;
    missing?: boolean;
    denied?: number;
    minimal?: boolean;
    profileId?: string;
  } = {},
) {
  const requests: string[] = [];
  const profileId = options.profileId ?? "profile-1";
  const report = {
    ...legacyReport,
    profile_id: profileId,
    status: options.status ?? "ready",
    report_data: options.minimal ? {} : legacyReport.report_data,
  };
  const json = (route: Route, body: unknown, status = 200) =>
    route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    requests.push(`${request.method()} ${path}`);
    if (path === "/api/v1/users/me")
      return json(route, {
        id: "user-1",
        email: "alina@example.com",
        name: "Алина",
        is_active: true,
      });
    if (path === "/api/v1/billing/access")
      return json(route, {
        account_tier: "plus",
        access_state: "plus_active",
        accessible_products: ["self", "career"],
        entitlements: [],
        latest_payment: null,
      });
    if (path === "/api/v1/auth/refresh")
      return json(route, { detail: "expired" }, 401);
    if (path === `/api/v1/profiles/${encodeURIComponent(profileId)}`)
      return json(route, {
        id: profileId,
        name: "Алина",
        birth_date: "1990-05-17",
        birth_time: "08:35:00",
        birth_time_accuracy: "exact",
        birth_place: "Москва",
        timezone: "Europe/Moscow",
      });
    if (path === "/api/v1/career/reports/current") return json(route, null);
    if (path === "/api/v1/reports")
      return options.denied
        ? json(route, { detail: "SECRET backend diagnostic" }, options.denied)
        : json(route, { items: options.missing ? [] : [report] });
    if (path === "/api/v1/reports/legacy-career-1") return json(route, report);
    if (path === "/api/v1/reports/legacy-career-1/pdf")
      return route.fulfill({
        contentType: "application/pdf",
        body: "%PDF-1.4\n% Synthetic historical PDF fixture\n%%EOF",
      });
    if (path.endsWith("/chart"))
      return json(route, {
        id: "chart-current",
        profile_id: profileId,
        chart_data: {},
      });
    return json(route, { detail: `Unhandled E20 mock: ${path}` }, 404);
  });
  return requests;
}

export function unsafeArchiveRequests(requests: string[]) {
  return requests.filter((request) =>
    /(?:POST .*\/(?:chart|generate|regenerate)$|POST .*\/career\/reports)/.test(
      request,
    ),
  );
}
