import type { Page, Route } from "@playwright/test";

const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });

export async function mockSettingsApi(
  page: Page,
  options: {
    canRefine?: boolean;
    finalStatus?: "deterministic_ready" | "failed";
  } = {},
) {
  let revisionReads = 0;
  let refinementWrites = 0;

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === "/api/v1/users/me") {
      return json(route, {
        id: "user-1",
        email: "alina@example.com",
        name: "Алина",
        is_active: true,
      });
    }
    if (path === "/api/v1/billing/access") {
      return json(route, {
        account_tier: "plus",
        access_state: "plus_active",
        entitlements: [],
      });
    }
    if (path === "/api/v1/profiles" && request.method() === "GET") {
      return json(route, {
        total: 2,
        items: [
          {
            id: "profile-1",
            user_id: "user-1",
            name: "Алина",
            birth_date: "1990-05-17",
            birth_time: "08:35:00",
            birth_time_accuracy: "exact",
            birth_place: "Москва, Россия",
            latitude: 55.7558,
            longitude: 37.6176,
            timezone: "Europe/Moscow",
          },
          {
            id: "profile-2",
            user_id: "user-1",
            name: "Мария",
            birth_date: "1992-02-03",
            birth_time: null,
            birth_time_accuracy: "unknown",
            birth_place: "Казань, Россия",
            latitude: 55.7961,
            longitude: 49.1064,
            timezone: "Europe/Moscow",
          },
        ],
      });
    }
    if (path.endsWith("/birth-data-refinement-status")) {
      return json(route, {
        profile_id: path.split("/")[4],
        can_refine: options.canRefine ?? true,
        last_refined_at:
          options.canRefine === false ? "2026-10-04T12:00:00Z" : null,
        next_available_at:
          options.canRefine === false ? "2026-10-05T12:00:00Z" : null,
        retry_after_seconds: options.canRefine === false ? 86400 : 0,
      });
    }
    if (path === "/api/v1/profiles/geocode") {
      return json(route, {
        items: [
          {
            display_name: "Берлин, Германия",
            latitude: 52.52,
            longitude: 13.405,
            city: "Берлин",
            country: "Германия",
            timezone: "Europe/Berlin",
            selection_token: "signed-place",
          },
        ],
      });
    }
    if (
      path.endsWith("/birth-data-refinements") &&
      request.method() === "POST"
    ) {
      refinementWrites += 1;
      return json(
        route,
        {
          revision_id: "revision-1",
          profile_id: "profile-1",
          changed_fields: ["birth_place", "timezone"],
          status: "queued",
          next_available_at: "2026-10-05T12:00:00Z",
        },
        202,
      );
    }
    if (path.endsWith("/birth-data-refinements/revision-1")) {
      revisionReads += 1;
      const status =
        revisionReads > 1
          ? (options.finalStatus ?? "deterministic_ready")
          : "processing";
      return json(route, {
        revision_id: "revision-1",
        profile_id: "profile-1",
        changed_fields: ["birth_place", "timezone"],
        status,
        chart_id: status === "deterministic_ready" ? "chart-2" : null,
        report_id: status === "deterministic_ready" ? "report-2" : null,
        error_code: status === "failed" ? "report_generation_failed" : null,
        created_at: "2026-10-04T12:00:00Z",
        updated_at: "2026-10-04T12:00:03Z",
      });
    }
    if (path === "/api/v1/auth/refresh") return json(route, {}, 401);
    return json(
      route,
      { detail: `Unhandled mock route: ${request.method()} ${path}` },
      404,
    );
  });

  return {
    get refinementWrites() {
      return refinementWrites;
    },
  };
}
