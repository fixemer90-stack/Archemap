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
  const suggestion = page.getByRole("button", { name: "Берлин, Германия" });
  await suggestion.focus();
  await page.keyboard.press("Enter");
  const review = page.getByRole("button", { name: "Проверить изменения" });
  await review.focus();
  await page.keyboard.press("Enter");

  await expect(page.getByText("Было", { exact: true })).toBeVisible();
  await expect(page.getByText("Стало", { exact: true })).toBeVisible();
  const submit = page.getByRole("button", {
    name: "Сохранить и обновить расчёт",
  });
  await submit.focus();
  await page.keyboard.press("Enter");

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

test("profile switching updates the displayed birth-data snapshot", async ({
  page,
}) => {
  await mockSettingsApi(page);
  await page.goto("/settings", { waitUntil: "domcontentloaded" });

  await page.getByLabel("Чьи данные показаны").selectOption("profile-2");

  await expect(page.getByText("Казань, Россия", { exact: true })).toBeVisible();
  await expect(
    page.getByText("Время не указано", { exact: true }),
  ).toBeVisible();
});

test("manual place text cannot advance without a geocoder selection", async ({
  page,
}) => {
  await mockSettingsApi(page);
  await page.goto("/settings", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Уточнить данные" }).click();

  await page
    .getByLabel("Начните вводить город и выберите подсказку")
    .fill("Произвольное место");

  await expect(
    page.getByRole("button", { name: "Проверить изменения" }),
  ).toBeDisabled();
});

test("a real 429 response synchronizes the server cooldown", async ({
  page,
}) => {
  await mockSettingsApi(page, { rejectPostWithCooldown: true });
  await page.goto("/settings", { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "Уточнить данные" }).click();
  await page.getByLabel("Время", { exact: true }).fill("09:10");
  await page.getByRole("button", { name: "Проверить изменения" }).click();
  await page
    .getByRole("button", { name: "Сохранить и обновить расчёт" })
    .click();

  await expect(
    page.getByText(/Следующее уточнение будет доступно/),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Уточнить данные" }),
  ).toBeDisabled();
});

for (const width of [320, 768]) {
  test(`settings remain width-safe at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockSettingsApi(page);
    await page.goto("/settings", { waitUntil: "domcontentloaded" });

    expect(
      await page.evaluate(
        () =>
          document.documentElement.scrollWidth <=
          document.documentElement.clientWidth,
      ),
    ).toBe(true);
  });
}
