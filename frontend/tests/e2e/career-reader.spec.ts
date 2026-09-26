import AxeBuilder from "@axe-core/playwright";

import { sectionKeys } from "./fixtures/career";
import { mockCareerApi } from "./support/mock-career";
import { expect, test } from "./support/test";

async function expectNoHorizontalOverflow(
  page: import("@playwright/test").Page,
) {
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
}

test("reader is standalone, accessible, responsive, and keeps whole-word tooltips", async ({
  page,
}) => {
  await mockCareerApi(page);
  await page.goto("/products/career/report/report-1", {
    waitUntil: "domcontentloaded",
  });

  const reader = page.locator("article.career-reader");
  await expect(reader).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Главная навигация" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Astrotype", exact: true }),
  ).toHaveCount(0);

  await expect(
    page.getByRole("navigation", { name: "Разделы отчёта" }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Разделы отчёта" }).getByRole("link"),
  ).toHaveCount(10);
  await expect(
    page.getByText("Ведущий профиль", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Рабочий вектор", { exact: true })).toBeVisible();

  const renderedOrder = await reader
    .locator("section[id]")
    .evaluateAll((sections) => sections.map((section) => section.id));
  expect(renderedOrder).toEqual(sectionKeys);

  for (const term of [
    "Выраженность",
    "Уверенность",
    "Семейство ролей",
  ] as const) {
    const trigger = page.locator(`[data-career-term="${term}"]`).first();
    expect(
      await trigger.evaluate((element) =>
        Array.from(element.childNodes)
          .filter((node) => node.nodeType === Node.TEXT_NODE)
          .map((node) => node.textContent?.trim())
          .filter(Boolean),
      ),
    ).toEqual([term]);
    const tooltipId = await trigger.getAttribute("aria-describedby");
    expect(tooltipId).toBeTruthy();
    await trigger.focus();
    const tooltip = page.locator(`#${tooltipId}`);
    await expect(tooltip).toBeVisible();
    const box = await tooltip.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      expect(box.x).toBeGreaterThanOrEqual(0);
      expect(box.x + box.width).toBeLessThanOrEqual(
        await page.evaluate(() => window.innerWidth),
      );
    }
  }

  await expectNoHorizontalOverflow(page);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(
    accessibility.violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact ?? ""),
    ),
  ).toEqual([]);
  await expect(page).toHaveScreenshot("career-reader.png", {
    fullPage: true,
    animations: "disabled",
    maxDiffPixels: 100,
  });
});

test("reader has a readable print layout and produces a browser PDF", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "chromium-desktop",
    "print evidence is desktop-only",
  );
  await mockCareerApi(page);
  await page.goto("/products/career/report/report-1", {
    waitUntil: "domcontentloaded",
  });
  await expect(page.locator("article.career-reader")).toBeVisible();

  await page.emulateMedia({ media: "print" });
  await expect(
    page.getByRole("navigation", { name: "Действия с отчётом" }),
  ).toBeHidden();
  await expect(
    page.getByRole("navigation", { name: "Главная навигация" }),
  ).toHaveCount(0);
  await expectNoHorizontalOverflow(page);
  const colors = await page
    .locator("article.career-reader")
    .evaluate((element) => {
      const style = getComputedStyle(element);
      return { color: style.color, backgroundColor: style.backgroundColor };
    });
  expect(colors.color).toBe("rgb(17, 24, 39)");
  expect(colors.backgroundColor).toBe("rgb(255, 255, 255)");

  await expect(page).toHaveScreenshot("career-reader-print.png", {
    fullPage: true,
    animations: "disabled",
    maxDiffPixels: 100,
  });
  const pdf = await page.pdf({ format: "A4", printBackground: true });
  expect(pdf.subarray(0, 4).toString()).toBe("%PDF");
  expect(pdf.length).toBeGreaterThan(10_000);
});
