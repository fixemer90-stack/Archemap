import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./support/test";
import {
  mockLegacyCareer,
  legacyReport,
  savedCareerText,
  unsafeArchiveRequests,
} from "./support/mock-e20-legacy-career";

const archiveUrl = "/report/profile-1?product=career";

test("historical notice, exact saved prose, native PDF and keyboard target CTA", async ({
  page,
}, testInfo) => {
  const requests = await mockLegacyCareer(page);
  await page.goto(archiveUrl);
  await expect(
    page.getByRole("heading", { name: "Исторический карьерный отчёт" }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Только чтение. Сохранённый отчёт не пересчитывается и не обновляется.",
    ),
  ).toBeVisible();
  await expect(page.getByText(savedCareerText, { exact: true })).toBeVisible();
  const cta = page.getByRole("link", { name: "Перейти в новый Career" });
  await expect(cta).toHaveAttribute(
    "href",
    "/products/career?profileId=profile-1",
  );
  await cta.focus();
  await expect(cta).toBeFocused();
  await page.screenshot({
    path: testInfo.outputPath("archive.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(
    accessibility.violations.filter((item) =>
      ["serious", "critical"].includes(item.impact ?? ""),
    ),
  ).toEqual([]);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Скачать PDF", exact: true }).click();
  expect((await download).suggestedFilename()).toBe(
    "report-legacy-career-1.pdf",
  );
  expect(requests.filter((item) => item.endsWith("/pdf"))).toEqual([
    "GET /api/v1/reports/legacy-career-1/pdf",
  ]);
  expect(unsafeArchiveRequests(requests)).toEqual([]);
  await cta.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/products\/career\?profileId=profile-1$/);
  expect(unsafeArchiveRequests(requests)).toEqual([]);
});

test("archive read has no chart mutation", async ({ page }) => {
  const requests = await mockLegacyCareer(page);
  const query = page.waitForRequest(
    (request) => new URL(request.url()).pathname === "/api/v1/reports",
  );
  await page.goto(archiveUrl);
  const requestUrl = new URL((await query).url());
  expect(requestUrl.searchParams.get("product")).toBe("career");
  expect(requestUrl.searchParams.get("profile_id")).toBe("profile-1");
  await expect(page.getByText(savedCareerText, { exact: true })).toBeVisible();
  expect(unsafeArchiveRequests(requests)).toEqual([]);
});

for (const status of [
  "deterministic_ready",
  "generating_narrative",
  "pending",
  "narrative_failed",
]) {
  test(`historical ${status} never polls, generates or retries`, async ({
    page,
  }) => {
    const requests = await mockLegacyCareer(page, { status });
    await page.goto(archiveUrl);
    await expect(
      page.getByText(savedCareerText, { exact: true }),
    ).toBeVisible();
    const initialReads = requests.filter(
      (request) => request === "GET /api/v1/reports/legacy-career-1",
    ).length;
    await page.waitForTimeout(5500);
    expect(
      requests.filter(
        (request) => request === "GET /api/v1/reports/legacy-career-1",
      ),
    ).toHaveLength(initialReads);
    await expect(
      page.getByRole("button", { name: /Повторить|Обновить/ }),
    ).toHaveCount(0);
    await expect(
      page.getByText("Сохранённый статус:", { exact: false }),
    ).toHaveCount(0);
    expect(unsafeArchiveRequests(requests)).toEqual([]);
  });
}

test("missing archive offers target Career without creating either report", async ({
  page,
}, testInfo) => {
  const requests = await mockLegacyCareer(page, { missing: true });
  await page.goto(archiveUrl);
  await expect(
    page.getByText("Сохранённый карьерный отчёт не найден.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Перейти в новый Career" }),
  ).toHaveAttribute("href", "/products/career?profileId=profile-1");
  await page.screenshot({
    path: testInfo.outputPath("missing.png"),
    fullPage: true,
  });
  expect(unsafeArchiveRequests(requests)).toEqual([]);
});

test("minimal historical payload remains read-only and offers PDF", async ({
  page,
}) => {
  const requests = await mockLegacyCareer(page, { minimal: true });
  await page.goto(archiveUrl);
  await expect(
    page.getByRole("heading", { name: "Исторический карьерный отчёт" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Скачать PDF", exact: true }),
  ).toBeEnabled();
  await expect(
    page.getByText("Параметры расчёта", { exact: true }),
  ).toHaveCount(0);
  expect(unsafeArchiveRequests(requests)).toEqual([]);
});

test("late Self response cannot generate or overwrite Career after product navigation", async ({
  page,
}) => {
  const requests = await mockLegacyCareer(page);
  let release!: () => void;
  const held = new Promise<void>((resolve) => {
    release = resolve;
  });
  let selfStarted = false;
  await page.route(
    "**/api/v1/reports?product=self&limit=100",
    async (route) => {
      selfStarted = true;
      await held;
      await route.fulfill({ json: { items: [] } });
    },
  );
  await page.goto("/report/profile-1?product=self", {
    waitUntil: "domcontentloaded",
  });
  await expect.poll(() => selfStarted).toBe(true);
  await page.evaluate(() =>
    window.history.pushState(null, "", "/report/profile-1?product=career"),
  );
  await expect(page.getByText(savedCareerText, { exact: true })).toBeVisible();
  release();
  await page.waitForTimeout(500);
  await expect(page.getByText(savedCareerText, { exact: true })).toBeVisible();
  expect(
    requests.filter((request) =>
      /POST .*\/(?:generate|regenerate)$/.test(request),
    ),
  ).toEqual([]);
});

test("encoded profile context cannot inject query parameters", async ({
  page,
}) => {
  const profileId = "profile&next=/billing?x=1";
  const requests = await mockLegacyCareer(page, { profileId, missing: true });
  await page.goto(`/report/${encodeURIComponent(profileId)}?product=career`);
  await expect(
    page.getByText("Сохранённый карьерный отчёт не найден.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Перейти в новый Career" }),
  ).toHaveAttribute(
    "href",
    `/products/career?profileId=${encodeURIComponent(profileId)}`,
  );
  expect(unsafeArchiveRequests(requests)).toEqual([]);
});

for (const mismatch of [
  { profile_id: "foreign-profile" },
  { product: "self" },
]) {
  test(`unrelated list rows are never loaded ${JSON.stringify(mismatch)}`, async ({
    page,
  }) => {
    const requests = await mockLegacyCareer(page);
    await page.route("**/api/v1/reports?**", (route) =>
      route.fulfill({ json: { items: [{ ...legacyReport, ...mismatch }] } }),
    );
    await page.goto(archiveUrl);
    await expect(
      page.getByText("Сохранённый карьерный отчёт не найден.", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText(savedCareerText, { exact: true })).toHaveCount(
      0,
    );
    expect(requests).not.toContain("GET /api/v1/reports/legacy-career-1");
    expect(unsafeArchiveRequests(requests)).toEqual([]);
  });
}

for (const mismatch of [
  { profile_id: "foreign-profile" },
  { product: "self" },
]) {
  test(`mismatched saved row is not rendered ${JSON.stringify(mismatch)}`, async ({
    page,
  }) => {
    const requests = await mockLegacyCareer(page);
    await page.route("**/api/v1/reports/legacy-career-1", (route) =>
      route.fulfill({ json: { ...legacyReport, ...mismatch } }),
    );
    await page.goto(archiveUrl);
    await expect(
      page.getByText("Сохранённый отчёт недоступен или не найден.", {
        exact: true,
      }),
    ).toBeVisible();
    await expect(page.getByText(savedCareerText, { exact: true })).toHaveCount(
      0,
    );
    expect(unsafeArchiveRequests(requests)).toEqual([]);
  });
}

test("ordinary Self still auto-generates, polls and retries narrative", async ({
  page,
}) => {
  const requests = await mockLegacyCareer(page);
  const selfReport = {
    ...legacyReport,
    product: "self",
    status: "generating_narrative",
    report_data: {},
  };
  let generated = false;
  let retried = false;
  await page.route("**/api/v1/reports**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    requests.push(`${request.method()} ${path}`);
    if (path === "/api/v1/reports")
      return route.fulfill({ json: { items: [] } });
    if (path.endsWith("/generate")) {
      expect(request.postDataJSON().product).toBe("self");
      generated = true;
      return route.fulfill({ json: selfReport });
    }
    if (path.endsWith("/narrative/regenerate")) {
      retried = true;
      return route.fulfill({ json: selfReport });
    }
    return route.fulfill({
      json: { ...selfReport, status: "narrative_failed" },
    });
  });
  await page.goto("/report/profile-1?product=self");
  await expect.poll(() => generated).toBe(true);
  await expect(
    page.getByRole("button", { name: "Повторить генерацию", exact: true }),
  ).toBeVisible({ timeout: 15000 });
  await page
    .getByRole("button", { name: "Повторить генерацию", exact: true })
    .click();
  await expect.poll(() => retried).toBe(true);
  expect(requests).toContain("POST /api/v1/profiles/profile-1/chart");
  expect(requests).toContain("POST /api/v1/reports/generate");
  expect(requests).toContain("GET /api/v1/reports/legacy-career-1");
  expect(requests).toContain(
    "POST /api/v1/reports/legacy-career-1/narrative/regenerate",
  );
});

for (const denied of [401, 402, 404]) {
  test(`archive ${denied} is safe and does not expose content or diagnostics`, async ({
    page,
  }) => {
    const requests = await mockLegacyCareer(page, { denied });
    await page.goto(archiveUrl);
    await expect(
      page.getByText("Не удалось загрузить отчёт", { exact: true }),
    ).toBeVisible();
    await expect(page.getByText("SECRET backend diagnostic")).toHaveCount(0);
    await expect(page.getByText(savedCareerText, { exact: true })).toHaveCount(
      0,
    );
    await expect(
      page.getByRole("button", { name: "Скачать PDF", exact: true }),
    ).toHaveCount(0);
    expect(unsafeArchiveRequests(requests)).toEqual([]);
  });
}
