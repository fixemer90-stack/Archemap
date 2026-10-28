import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./support/test";
import { mockE22Child } from "./support/mock-e22-child";

test("limited report quality qualifies technical completion without inviting a paid retry", async ({
  page,
}) => {
  const state = await mockE22Child(page, {
    readerStatus: "ready",
    readerQuality: "limited",
  });
  await page.goto("/reports/child/report-a");
  const notice = page.getByRole("status", {
    name: "Ограничения содержания отчёта",
  });
  await expect(notice).toBeVisible();
  await expect(notice).toContainText("Содержание отчёта ограничено");
  await expect(notice).toContainText("Сохранённые разделы доступны");
  await expect(page.getByText("Отчёт готов.", { exact: true })).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: /Повторить недоступные пояснения/ }),
  ).toHaveCount(0);
  await expect(page.getByText("cross_section_duplicate_prose")).toHaveCount(0);
  for (const internalSection of [
    "parent_style",
    "how_to_use",
    "child_interaction_needs",
  ]) {
    await expect(page.getByText(internalSection, { exact: true })).toHaveCount(
      0,
    );
  }
  await expect(
    page.getByText(
      "Начните с наблюдения за контактом. Попробуйте спокойную паузу рядом.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(page.locator("[data-child-section]")).toHaveCount(15);
  await expect(page.getByRole("link", { name: "Скачать PDF" })).toHaveAttribute(
    "href",
    "/api/v1/child/reports/report-a/pdf?age_snapshot_id=age-pinned-a",
  );
  expect(state.creates).toEqual([]);
  expect(state.retryKeys).toEqual([]);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: test.info().outputPath("child-quality-limited.png"),
    fullPage: true,
  });
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(
    accessibility.violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact ?? ""),
    ),
  ).toEqual([]);
  await page.setViewportSize({ width: 820, height: 1180 });
  await expect(notice).toBeVisible();
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: test.info().outputPath("child-quality-tablet.png"),
    fullPage: true,
  });
  expect(state.creates).toEqual([]);
  expect(state.retryKeys).toEqual([]);
});

for (const readerQuality of ["ready", undefined] as const) {
  test(`complete or legacy quality ${readerQuality ?? "absent"} preserves the existing reader`, async ({
    page,
  }) => {
    await mockE22Child(page, { readerStatus: "ready", readerQuality });
    await page.goto("/reports/child/report-a");
    await expect(page.getByText("Отчёт готов.", { exact: true })).toBeVisible();
    await expect(
      page.getByRole("status", { name: "Ограничения содержания отчёта" }),
    ).toHaveCount(0);
    await expect(page.locator("[data-child-section]")).toHaveCount(15);
  });
}
