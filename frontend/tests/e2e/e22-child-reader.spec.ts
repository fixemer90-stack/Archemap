import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./support/test";
import { mockE22Child, childSectionManifest } from "./support/mock-e22-child";

test("age update refreshes an immediately completed job without replacing immutable core", async ({
  page,
}) => {
  const state = await mockE22Child(page);
  await page.goto("/reports/child/report-a");
  await page
    .getByRole("button", { name: "Обновить возрастной блок: Миша" })
    .click();
  await expect(
    page.getByText("Возраст на дату 2026-10-24", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Обновляем возрастной блок:/)).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Повторить недоступные пояснения: Миша" }),
  ).toBeEnabled();
  expect(state.ageRequests).toEqual([{ expected_core_report_version: 1 }]);
  await expect(page.getByRole("link", { name: "Скачать PDF" })).toHaveAttribute(
    "href",
    "/api/v1/child/reports/report-a/pdf?age_snapshot_id=age-updated-a",
  );
  await expect(
    page.getByText(
      "Начните с наблюдения за контактом. Попробуйте спокойную паузу рядом.",
    ),
  ).toBeVisible();
  await expect(page.getByText(/Часть пояснений недоступна/)).toBeVisible();
  await expect(page.getByText("Отчёт готов.", { exact: true })).toHaveCount(0);
});

test("asynchronous failed age update stops polling and keeps pinned content retryable", async ({
  page,
}) => {
  const state = await mockE22Child(page, { ageFailure: true });
  await page.goto("/reports/child/report-a");
  const update = page.getByRole("button", {
    name: "Обновить возрастной блок: Миша",
  });
  await update.click();
  await expect(update).toBeDisabled();
  await expect.poll(() => state.ageGenerationReads).toBe(2);
  await expect(update).toBeEnabled();
  await expect(page.getByText(/Обновляем возрастной блок:/)).toHaveCount(0);
  await expect(page.locator("[data-child-section]")).toHaveCount(15);
  await expect(page.getByRole("link", { name: "Скачать PDF" })).toHaveAttribute(
    "href",
    "/api/v1/child/reports/report-a/pdf?age_snapshot_id=age-pinned-a",
  );
  await page.waitForTimeout(2300);
  expect(state.ageGenerationReads).toBe(2);
});

test("retry key survives ambiguous transport but rotates after confirmed terminal failure", async ({
  page,
}) => {
  const state = await mockE22Child(page);
  await page.goto("/reports/child/report-a");
  const retry = page.getByRole("button", {
    name: "Повторить недоступные пояснения: Миша",
  });
  await expect(retry).toBeEnabled();
  state.retryTransportFail = true;
  await retry.click();
  await page.getByRole("button", { name: "Проверить состояние снова" }).click();
  await expect(retry).toBeEnabled();
  await retry.click();
  await expect.poll(() => state.retryKeys.length).toBe(2);
  expect(state.retryKeys[1]).toBe(state.retryKeys[0]);
  await expect(retry).toBeEnabled();
  await retry.click();
  await expect.poll(() => state.retryKeys.length).toBe(3);
  expect(state.retryKeys[2]).not.toBe(state.retryKeys[1]);
});

test("ready reader renders every persisted section without an unavailable narrative message", async ({
  page,
}) => {
  await mockE22Child(page, { readerStatus: "ready" });
  await page.goto("/reports/child/report-a");
  await expect(page.getByText("Отчёт готов.", { exact: true })).toBeVisible();
  await expect(page.locator("[data-child-section]")).toHaveCount(15);
  await expect(
    page.getByText(/Подробное пояснение пока недоступно/),
  ).toHaveCount(0);
  await page.screenshot({
    path: test.info().outputPath("child-reader-ready.png"),
    fullPage: true,
  });
});

test("reader keeps persisted guidance through narrative failure and pins dated PDF", async ({
  page,
}) => {
  const state = await mockE22Child(page, { poll: true });
  await page.goto("/reports/child/report-a");
  await expect(
    page.getByRole("heading", { name: "Как поддерживать контакт с ребёнком" }),
  ).toBeVisible();
  await expect(page.getByText("Ребёнок: Миша", { exact: true })).toBeVisible();
  await expect(page.getByText(/Часть пояснений недоступна/)).toBeVisible();
  await expect(
    page.getByText(
      "Начните с наблюдения за контактом. Попробуйте спокойную паузу рядом.",
    ),
  ).toBeVisible();
  const sections = page.locator("[data-child-section]");
  await expect(sections).toHaveCount(15);
  expect(
    await sections.evaluateAll((items) =>
      items.map((item) => item.getAttribute("data-child-section")),
    ),
  ).toEqual(childSectionManifest.map((section) => section.key));
  await expect(
    page.getByText("Возраст на дату 2026-10-14", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(/Возрастной блок сохранён на прошлую дату/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Обновить возрастной блок: Миша" }),
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Скачать PDF" })).toHaveAttribute(
    "href",
    "/api/v1/child/reports/report-a/pdf?age_snapshot_id=age-pinned-a",
  );
  const details = page.getByText("Основания и ограничения", { exact: true });
  await details.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText(
      "В текущих данных ребёнка время рождения неизвестно. Уточнение данных не меняет уже сохранённый отчёт.",
    ),
  ).toBeVisible();
  expect(state.generationReads).toBeGreaterThan(0);
  state.expire = true;
  await page
    .getByRole("button", { name: "Повторить недоступные пояснения: Миша" })
    .click();
  await expect(page.getByRole("link", { name: "Войти снова" })).toBeVisible();
  await expect(sections).toHaveCount(15);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
  const axe = await new AxeBuilder({ page }).analyze();
  expect(
    axe.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    ),
  ).toEqual([]);
  await page.screenshot({
    path: test.info().outputPath("child-reader.png"),
    fullPage: true,
  });
  await page.emulateMedia({ media: "print" });
  await expect(sections.first()).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Обновить возрастной/ }),
  ).toBeHidden();
  expect(state.unhandled).toEqual([]);
});

for (const access of [401, 402, 404, 503]) {
  test(`access ${access} never exposes child report data`, async ({ page }) => {
    // Next's route announcer can coexist with the product's own alert. Keep
    // that framework condition deterministic instead of relying on CI timing.
    await page.addInitScript(() => {
      window.addEventListener("DOMContentLoaded", () => {
        const announcer = document.createElement("div");
        announcer.setAttribute("role", "alert");
        announcer.textContent = "Framework route announcement";
        document.body.append(announcer);
      });
    });
    await mockE22Child(page, { access });
    await page.goto("/reports/child/report-a");
    await expect(
      page.locator(".child-surface").getByRole("alert"),
    ).toBeVisible();
    await expect(page.locator("[data-child-section]")).toHaveCount(0);
    await expect(page.getByText("Миша", { exact: true })).toHaveCount(0);
    if (access === 402)
      await expect(
        page.getByRole("link", { name: "Посмотреть Plus" }),
      ).toBeVisible();
    await page.goto("/products/child");
    await expect(
      page.locator(".child-surface").getByRole("alert"),
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Выбрать Миша" }),
    ).toHaveCount(0);
  });
}
