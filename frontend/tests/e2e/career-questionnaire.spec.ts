import AxeBuilder from "@axe-core/playwright";

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

test("questionnaire is keyboard-accessible, responsive, and reaches deterministic-ready", async ({
  page,
}) => {
  const state = await mockCareerApi(page);
  await page.goto("/products/career?profileId=profile-1", {
    waitUntil: "domcontentloaded",
  });

  await expect(
    page.getByRole("heading", { name: "Профессиональный контекст" }),
  ).toBeVisible();
  const progress = page.getByRole("progressbar", { name: "Прогресс опроса" });
  await expect(progress).toHaveAttribute("aria-valuemin", "1");
  await expect(progress).toHaveAttribute("aria-valuemax", "10");
  await expect(progress).toHaveAttribute("aria-valuenow", "1");

  await page.getByRole("button", { name: "Далее" }).click();
  await expect(
    page.getByText("Ответьте на обязательный вопрос, чтобы продолжить."),
  ).toBeVisible();

  for (let step = 0; step < 3; step += 1) {
    await page.getByRole("button", { name: "5", exact: true }).focus();
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Далее" }).click();
  }
  await page
    .getByRole("button", { name: "Баланс устойчивости и эксперимента" })
    .click();
  await page.getByRole("button", { name: "Далее" }).click();
  await page.getByRole("button", { name: "Экспертный путь" }).click();
  await page.getByRole("button", { name: "Далее" }).click();
  await page
    .getByLabel("Чем вы занимаетесь сейчас?")
    .fill("Руководитель продукта");
  await page.getByRole("button", { name: "Далее" }).click();
  await page.getByLabel("Сколько лет релевантного опыта у вас есть?").fill("8");
  await page.getByRole("button", { name: "Далее" }).click();
  await page
    .getByLabel("Что вы хотите изменить в работе?")
    .fill("Больше системных задач");
  await page.getByRole("button", { name: "Далее" }).click();
  await page.getByRole("button", { name: "4", exact: true }).click();
  await page.getByRole("button", { name: "Далее" }).click();
  await page
    .getByLabel("Какие ограничения важно учитывать?")
    .fill("Не готова к переезду");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Создать отчёт" }).click();

  await expect(page.getByRole("link", { name: "Открыть отчёт" })).toBeVisible();
  expect(state.answerWrites).toBeGreaterThanOrEqual(9);
  expect(state.completions).toBe(1);
  expect(state.reportCreates).toBe(1);
  expect(state.completionKeys[0]).toMatch(/^career-questionnaire:/);
  expect(state.reportKeys[0]).toMatch(/^career-report:/);

  await expectNoHorizontalOverflow(page);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(
    accessibility.violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact ?? ""),
    ),
  ).toEqual([]);
  await expect(page).toHaveScreenshot("career-questionnaire.png", {
    fullPage: true,
    animations: "disabled",
    maxDiffPixels: 100,
  });
});
