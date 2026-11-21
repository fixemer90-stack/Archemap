import type { CareerGenerationStatus } from "../../src/lib/api/career";
import { mockCareerApi } from "./support/mock-career";
import { expect, test } from "./support/test";

const cases = [
  "profiles",
  "loading",
  "empty",
  "profile-error",
  "questionnaire",
  "locked",
  "generation",
  "lookup-error",
] as const;

for (const state of cases) {
  test(`Career has an above-fold keyboard exit to the dashboard: ${state}`, async ({
    page,
  }) => {
    const pending: CareerGenerationStatus = {
      contract_version: "career_generation_status_v1",
      generation_id: "generation-1",
      report_id: null,
      status: "queued",
      deterministic_status: "pending",
      narrative_status: "pending",
      progress: { total: 10, ready: 0, failed: 0, running: 0 },
      sections: [],
    };
    const api = await mockCareerApi(page, {
      currentGeneration: state === "generation" ? pending : null,
    });
    let releaseProfiles: (() => void) | undefined;
    if (state === "loading") {
      const gate = new Promise<void>((resolve) => {
        releaseProfiles = resolve;
      });
      await page.route("**/api/v1/profiles", async (route) => {
        await gate;
        await route.fulfill({ json: { items: [] } });
      });
    } else if (state === "empty" || state === "profile-error") {
      await page.route("**/api/v1/profiles", (route) =>
        route.fulfill({
          status: state === "profile-error" ? 500 : 200,
          json: { items: [] },
        }),
      );
    }
    if (state === "locked" || state === "lookup-error") {
      await page.route("**/api/v1/career/reports/current?**", (route) =>
        route.fulfill({
          status: state === "locked" ? 402 : 500,
          json: { detail: "Career lookup unavailable" },
        }),
      );
    }
    const hasProfile = [
      "questionnaire",
      "locked",
      "generation",
      "lookup-error",
    ].includes(state);
    try {
      // Direct entry has no meaningful prior in-app history.
      await page.goto(
        "/products/career" + (hasProfile ? "?profileId=profile-1" : ""),
      );
      if (state === "loading") {
        await expect(page.getByText("Загружаем профили…")).toBeVisible();
      } else if (state === "empty") {
        await expect(
          page.getByRole("link", { name: "Создать профиль" }),
        ).toBeVisible();
      } else if (state === "profile-error" || state === "lookup-error") {
        await expect(page.getByRole("alert")).toBeVisible();
      } else if (state === "questionnaire") {
        await expect(
          page.getByRole("heading", { name: "Профессиональный контекст" }),
        ).toBeVisible();
      } else if (state === "locked") {
        await expect(
          page.getByRole("heading", { name: "Career входит в Plus" }),
        ).toBeVisible();
      } else if (state === "generation") {
        await expect(
          page.getByRole("heading", { name: "Отчёт собирается по разделам" }),
        ).toBeVisible();
      } else {
        await expect(
          page.getByRole("button").filter({ hasText: "Продолжить" }),
        ).toBeVisible();
      }
      const back = page
        .getByRole("navigation", { name: "Навигация Career" })
        .getByRole("link", { name: "В личный кабинет", exact: true });
      await expect(back).toBeVisible();
      await expect(back).toBeInViewport({ ratio: 1 });
      await expect(back).toHaveAttribute("href", "/dashboard");
      await expect(
        page.getByRole("link", { name: "К обзору продуктов" }),
      ).toHaveAttribute("href", "/dashboard");
      await back.focus();
      await expect(back).toBeFocused();
      releaseProfiles?.();
      await page.keyboard.press("Enter");
      await expect(page).toHaveURL(/\/dashboard$/);
      await expect(page.locator("main")).toBeVisible();
      await expect(page.getByText(/Unhandled mock route/)).toHaveCount(0);
      expect(
        api.requests.filter((request) =>
          /^(POST|PUT|PATCH|DELETE) /.test(request),
        ),
      ).toEqual([]);
    } finally {
      releaseProfiles?.();
    }
  });
}
