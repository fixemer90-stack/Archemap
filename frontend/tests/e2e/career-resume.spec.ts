import type { CareerGenerationStatus } from "../../src/lib/api/career";
import { mockCareerApi } from "./support/mock-career";
import { expect, test } from "./support/test";

const entry = "/products/career?profileId=profile-1";
const saved: CareerGenerationStatus = {
  contract_version: "career_generation_status_v1",
  generation_id: "generation-1",
  report_id: "report-1",
  status: "ready",
  deterministic_status: "ready",
  narrative_status: "ready",
  progress: { total: 10, ready: 10, failed: 0, running: 0 },
  sections: [],
};

for (const status of [
  "queued",
  "deterministic_ready",
  "generating_narrative",
]) {
  test(`existing ${status} resumes progress after entry and reload without mutations`, async ({
    page,
  }) => {
    const state = await mockCareerApi(page, {
      currentGeneration: {
        ...saved,
        status,
        narrative_status: "generating",
        progress: { total: 10, ready: 3, failed: 0, running: 1 },
      },
    });
    for (let visit = 0; visit < 2; visit += 1) {
      await page.goto(entry);
      await expect(
        page.getByRole("heading", { name: "Отчёт собирается по разделам" }),
      ).toBeVisible();
      await page.reload();
      await expect(
        page.getByRole("heading", { name: "Отчёт собирается по разделам" }),
      ).toBeVisible();
    }
    await expect
      .poll(
        () =>
          state.requests.filter((r) => r.includes("/generations/generation-1"))
            .length,
      )
      .toBeGreaterThan(0);
    expectReadOnly(state.requests);
  });
}

for (const status of ["partial_failure", "narrative_failed", "failed"]) {
  test(`saved ${status} opens the existing reader without mutations`, async ({
    page,
  }) => {
    const state = await mockCareerApi(page, {
      currentGeneration: { ...saved, status, narrative_status: "failed" },
      reportStatus: "narrative_failed",
    });
    await page.goto(entry);
    await expect(page).toHaveURL(/\/products\/career\/report\/report-1$/);
    expectReadOnly(state.requests);
  });
}

test("failed generation without a report is honest and never restarts", async ({
  page,
}) => {
  const state = await mockCareerApi(page, {
    currentGeneration: {
      ...saved,
      report_id: null,
      status: "failed",
      deterministic_status: "failed",
      narrative_status: "failed",
    },
  });
  await page.goto(entry);
  await expect(
    page.getByRole("alert").filter({ hasText: "Не удалось создать отчёт" }),
  ).toContainText("Не удалось создать отчёт");
  await expect(
    page.getByRole("heading", { name: "Отчёт собирается по разделам" }),
  ).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Создать отчёт" })).toHaveCount(
    0,
  );
  expectReadOnly(state.requests);
});

test("late current lookup cannot overwrite a newly selected deep-linked profile", async ({
  page,
}) => {
  const state = await mockCareerApi(page);
  await page.route("**/api/v1/profiles", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            id: "profile-1",
            name: "Алина",
            birth_date: "1990-05-17",
            birth_place: "Москва",
          },
          {
            id: "profile-2",
            name: "Борис",
            birth_date: "1991-05-17",
            birth_place: "Москва",
          },
        ],
      },
    }),
  );
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let started = false;
  await page.route(
    "**/api/v1/career/reports/current?profile_id=profile-1",
    async (route) => {
      started = true;
      await held;
      await route.fulfill({ json: saved });
    },
  );
  await page.goto(entry);
  await expect.poll(() => started).toBe(true);
  await page.evaluate(() =>
    window.history.pushState(null, "", "/products/career?profileId=profile-2"),
  );
  await expect(page.getByText("Профиль: Борис", { exact: true })).toBeVisible();
  release();
  await page.waitForTimeout(500);
  await expect(page).toHaveURL(/profileId=profile-2$/);
  await expect(page.getByText("Профиль: Борис", { exact: true })).toBeVisible();
  expect(
    state.requests.filter((r) => /^(POST|PUT).*\/career\//.test(r)),
  ).toEqual([]);
});

test("submission reconciles a report created elsewhere before any questionnaire mutation", async ({
  page,
}) => {
  const state = await mockCareerApi(page);
  let lookups = 0;
  await page.route("**/api/v1/career/reports/current?**", (route) =>
    route.fulfill({ json: ++lookups === 1 ? null : saved }),
  );
  await page.route("**/api/v1/career/questionnaires/current?**", (route) =>
    route.fulfill({
      json: {
        contract_version: "career_questionnaire_v1",
        session_id: "session-1",
        career_profile_id: "career-profile-1",
        status: "draft",
        questions: [
          {
            key: "leadership_responsibility",
            domain: "leadership",
            answer_type: "scale_1_5",
            required: true,
          },
        ],
        answers: { leadership_responsibility: 5 },
        missing_required: [],
      },
    }),
  );
  await page.goto(entry);
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Создать отчёт" }).click();
  await expect(page).toHaveURL(/\/products\/career\/report\/report-1$/);
  expect(state.answerWrites).toBe(0);
  expect(state.completions).toBe(0);
  expect(state.reportCreates).toBe(0);
});

for (const status of [401, 402, 404, 503, "network"] as const) {
  test(`current lookup ${status} never falls back to questionnaire or creation`, async ({
    page,
  }) => {
    const state = await mockCareerApi(page);
    let attempts = 0;
    await page.route("**/api/v1/career/reports/current?**", async (route) => {
      attempts += 1;
      if (status === "network") return route.abort("failed");
      return route.fulfill({
        status,
        json: { detail: "Сохранённый Career недоступен" },
      });
    });
    await page.goto(entry);
    if (status === 402) {
      await expect(
        page.getByRole("heading", { name: "Career входит в Plus" }),
      ).toBeVisible();
    } else {
      await expect(
        page.getByRole("alert").filter({
          hasText:
            /Сессия завершилась|Сохранённый Career|Профиль или натальная карта|fetch/i,
        }),
      ).toBeVisible();
    }
    expect(attempts).toBeGreaterThan(0);
    await expect(
      page.getByRole("heading", { name: "Профессиональный контекст" }),
    ).toHaveCount(0);
    expectReadOnly(state.requests);
  });
}

test("late draft save cannot advance the new profile questionnaire", async ({
  page,
}) => {
  await mockCareerApi(page);
  await page.route("**/api/v1/profiles", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            id: "profile-1",
            name: "Алина",
            birth_date: "1990-05-17",
            birth_place: "Москва",
          },
          {
            id: "profile-2",
            name: "Борис",
            birth_date: "1991-05-17",
            birth_place: "Москва",
          },
        ],
      },
    }),
  );
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let saving = false;
  await page.route(
    "**/api/v1/career/questionnaires/session-1/answers",
    async (route) => {
      saving = true;
      await held;
      await route.fulfill({
        json: { answers: { leadership_responsibility: 5 } },
      });
    },
  );
  await page.goto(entry);
  await page.getByRole("button", { name: "5", exact: true }).click();
  await page.getByRole("button", { name: "Далее" }).click();
  await expect.poll(() => saving).toBe(true);
  await page.evaluate(() =>
    window.history.pushState(null, "", "/products/career?profileId=profile-2"),
  );
  await expect(page.getByText("Профиль: Борис", { exact: true })).toBeVisible();
  release();
  await page.waitForTimeout(500);
  await expect(
    page.getByRole("progressbar", { name: "Прогресс опроса" }),
  ).toHaveAttribute("aria-valuenow", "1");
});

function expectReadOnly(requests: string[]) {
  expect(
    requests.filter((request) =>
      /^(POST|PUT|PATCH|DELETE) .*\/career\//.test(request),
    ),
  ).toEqual([]);
  expect(
    requests.filter((request) => request.includes("/questionnaires/")),
  ).toEqual([]);
}

test("ready saved report opens automatically on re-entry and reload without mutations", async ({
  page,
}) => {
  const state = await mockCareerApi(page, { currentGeneration: saved });
  for (let visit = 0; visit < 2; visit += 1) {
    await page.goto(entry);
    await expect(page).toHaveURL(/\/products\/career\/report\/report-1$/);
    await page.reload();
    await expect(page).toHaveURL(/\/products\/career\/report\/report-1$/);
  }
  expectReadOnly(state.requests);
  expect(state.requests).toContain(
    "GET /api/v1/career/reports/current?profile_id=profile-1",
  );
});
