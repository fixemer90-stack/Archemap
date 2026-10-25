import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./support/test";
import { mockE22Child } from "./support/mock-e22-child";

test("unknown birth time is a complete creation path and edits explain immutable history", async ({
  page,
}) => {
  const state = await mockE22Child(page);
  await page.goto("/products/child");
  await page.getByRole("button", { name: "Добавить ребёнка" }).click();
  await page.getByLabel("Имя или псевдоним").fill("Лисёнок");
  await page.getByLabel("Дата рождения").fill("2021-05-12");
  await expect(
    page.getByLabel("Время неизвестно", { exact: true }),
  ).toBeChecked();
  await expect(
    page.getByText("Не нужно угадывать время.", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Место рождения").fill("Москва");
  await page.getByRole("button", { name: "Москва, Россия" }).click();
  await page.screenshot({
    path: test.info().outputPath("child-create-populated.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Сохранить ребёнка" }).click();
  await expect(
    page.getByRole("heading", { name: "Ваши наблюдения: Лисёнок" }),
  ).toBeVisible();
  expect(state.lastCreate?.birth_time).toBeNull();
  expect(state.lastCreate?.birth_time_confidence).toBe("unknown");
  await page.getByRole("button", { name: "Изменить данные: Лисёнок" }).click();
  await expect(page.getByText(/новую версию карты/)).toBeVisible();
  await page.getByLabel("Приблизительное время", { exact: true }).check();
  await expect(page.getByText(/устойчивые во временном окне/)).toBeVisible();
  await page.getByLabel("Время рождения", { exact: true }).fill("12:30");
  await page
    .getByRole("button", { name: "Сохранить изменения: Лисёнок" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Ваши наблюдения: Лисёнок" }),
  ).toBeVisible();
  expect(state.unhandled).toEqual([]);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
});

test("expired session preserves saved observations read-only", async ({
  page,
}) => {
  const state = await mockE22Child(page);
  await page.goto("/products/child");
  await page.getByRole("button", { name: "Выбрать Миша" }).click();
  await page.getByRole("radio", { name: "Спокойная пауза рядом" }).check();
  await expect(
    page.getByRole("status").filter({ hasText: "Сохранено" }),
  ).toBeVisible();
  state.expire = true;
  await page.getByRole("radio", { name: "Обсуждаем заранее" }).check();
  await expect(
    page.getByRole("link", { name: "Войти снова" }).first(),
  ).toBeVisible();
  await expect(
    page.getByRole("radio", { name: "Спокойная пауза рядом" }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Изменить данные: Миша" }),
  ).toBeDisabled();
  expect(state.drafts["child-a"]).toEqual({ support: "pause" });
});

test("session expiry at confirmation disables repeat submission and preserves review", async ({
  page,
}) => {
  const state = await mockE22Child(page);
  await page.goto("/products/child");
  await page.getByRole("button", { name: "Выбрать Миша" }).click();
  await page.getByRole("radio", { name: "Спокойная пауза рядом" }).check();
  await page.getByRole("radio", { name: "Обсуждаем заранее" }).check();
  await page.getByRole("button", { name: "Проверить ответы" }).click();
  await page.getByRole("checkbox", { name: /Подтверждаю/ }).check();
  state.expire = true;
  await page
    .getByRole("button", { name: "Подтвердить и создать отчёт" })
    .click();
  await expect(page.getByRole("link", { name: "Войти снова" })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Подтвердить и создать отчёт" }),
  ).toBeDisabled();
  expect(state.creates).toEqual([]);
});

test("generation link resumes the server-owned job for the selected child", async ({
  page,
}) => {
  const state = await mockE22Child(page);
  await page.goto(
    "/products/child?child_id=child-a&generation_id=generation-a",
  );
  await expect(
    page.getByRole("heading", { name: "Ваши наблюдения: Миша" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Читать готовую часть" }),
  ).toBeVisible();
  expect(state.completions).toBe(0);
  expect(state.creates).toEqual([]);
});

test("child drafts resume independently and require review before completion", async ({
  page,
}) => {
  const state = await mockE22Child(page);
  await page.goto("/products/child");
  await expect(
    page.getByRole("heading", { name: "Ближе к ребёнку, бережнее к себе" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Выбрать Миша" }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("heading", { name: "Ваши наблюдения: Миша" }),
  ).toBeVisible();
  await page.getByRole("radio", { name: "Спокойная пауза рядом" }).focus();
  await page.keyboard.press("Space");
  await expect(
    page.getByRole("status").filter({ hasText: "Сохранено" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Выбрать Саша" }).click();
  await expect(
    page.getByRole("radio", { name: "Короткий разговор" }),
  ).toBeChecked();
  await page.getByRole("button", { name: "Выбрать Миша" }).click();
  await expect(
    page.getByRole("radio", { name: "Спокойная пауза рядом" }),
  ).toBeChecked();
  await page.getByRole("radio", { name: "Обсуждаем заранее" }).check();
  await expect(
    page.getByRole("status").filter({ hasText: "Сохранено" }),
  ).toBeVisible();
  await page.screenshot({
    path: test.info().outputPath("child-questionnaire-populated.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Проверить ответы" }).click();
  await expect(
    page.getByRole("heading", { name: "Проверьте перед отправкой: Миша" }),
  ).toBeVisible();
  expect(state.completions).toBe(0);
  await page.getByRole("checkbox", { name: /Подтверждаю/ }).check();
  await page
    .getByRole("button", { name: "Подтвердить и создать отчёт" })
    .click();
  await expect(
    page.getByRole("link", { name: "Читать готовую часть" }),
  ).toBeVisible();
  expect(state.creates).toEqual([
    {
      child_profile_id: "child-a",
      questionnaire_session_id: "session-child-a",
    },
  ]);
  expect(state.drafts["child-b"]).toEqual({ support: "talk" });
  expect(state.keys.every(Boolean)).toBe(true);
  expect(state.unhandled).toEqual([]);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
  const a11y = await new AxeBuilder({ page }).analyze();
  expect(
    a11y.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    ),
  ).toEqual([]);
  await page.screenshot({
    path: test.info().outputPath("child-product.png"),
    fullPage: true,
  });
});
