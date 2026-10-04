import AxeBuilder from "@axe-core/playwright";

import { mockSettingsApi } from "./support/mock-settings";
import { expect, test } from "./support/test";

test("birth-data settings are responsive, keyboard-accessible, and preserve the current report", async ({
  page,
}) => {
  const state = await mockSettingsApi(page);
  await page.goto("/settings", { waitUntil: "domcontentloaded" });

  await expect(
    page.getByRole("heading", { name: "Данные рождения" }),
  ).toBeVisible();
  await expect(page.getByText("08:35", { exact: true })).toBeVisible();
  await expect(page.getByText("Точное", { exact: true })).toBeVisible();
  await expect(page.getByText("Москва, Россия", { exact: true })).toBeVisible();
  await expect(page.getByLabel("Чьи данные показаны")).toBeVisible();

  const edit = page.getByRole("button", { name: "Уточнить данные" });
  await edit.focus();
  await page.keyboard.press("Enter");
  await page
    .getByLabel("Начните вводить город и выберите подсказку")
    .fill("Берлин");
  await page.getByRole("button", { name: "Берлин, Германия" }).click();
  await page.getByRole("button", { name: "Проверить изменения" }).click();

  await expect(page.getByText("Было", { exact: true })).toBeVisible();
  await expect(page.getByText("Стало", { exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Сохранить и обновить расчёт" })
    .click();

  await expect(
    page.getByRole("link", { name: "Открыть текущий отчёт" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Обновлённый отчёт уже доступен" }),
  ).toBeVisible({
    timeout: 12_000,
  });
  await expect(
    page.getByRole("link", { name: "Открыть обновлённый отчёт" }),
  ).toBeVisible();
  expect(state.refinementWrites).toBe(1);

  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(
    accessibility.violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact ?? ""),
    ),
  ).toEqual([]);
});

test("cooldown keeps profile and security settings available", async ({
  page,
}) => {
  await mockSettingsApi(page, { canRefine: false });
  await page.goto("/settings", { waitUntil: "domcontentloaded" });

  await expect(
    page.getByRole("button", { name: "Уточнить данные" }),
  ).toBeDisabled();
  await expect(
    page.getByText(/Следующее уточнение будет доступно/),
  ).toBeVisible();
  await expect(page.getByLabel("Имя")).toBeEnabled();
  await expect(page.getByLabel("Текущий пароль")).toBeEnabled();
});

test("failed regeneration preserves the saved report without payment copy", async ({
  page,
}) => {
  await mockSettingsApi(page, { finalStatus: "failed" });
  await page.goto("/settings", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Уточнить данные" }).click();
  await page.getByLabel("Время", { exact: true }).fill("09:10");
  await page.getByRole("button", { name: "Проверить изменения" }).click();
  await page
    .getByRole("button", { name: "Сохранить и обновить расчёт" })
    .click();

  await expect(
    page.getByRole("heading", { name: "Не удалось завершить обновление" }),
  ).toBeVisible({
    timeout: 12_000,
  });
  await expect(
    page.getByRole("link", { name: "Открыть текущий отчёт" }),
  ).toBeVisible();
  await expect(page.getByText(/Повторная оплата не нужна/)).toBeVisible();
});
