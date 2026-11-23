import AxeBuilder from "@axe-core/playwright";
import type { Page } from "@playwright/test";
import {
  incompleteWindowOverview,
  observedOverview,
  staleOverview,
  unavailableOverview,
  unknownReceiptsOverview,
} from "./support/admin-business-fixtures";
import { expect, test } from "./support/test";

const pagePath = "/admin/business";
const overviewPath = "/api/v1/admin/business/overview";

const metric = (page: Page, label: string) =>
  page.getByText(label, { exact: true }).locator("..").locator("dd");

const widthMatrix = [320, 820, 1440];

test("report KPIs describe generation, not delivery or reading", async ({
  page,
}) => {
  await page.route(`**${overviewPath}`, (route) =>
    route.fulfill({ json: observedOverview }),
  );
  await page.goto(pagePath);

  await expect(page.getByText(/доставка отч[её]тов/i)).toHaveCount(0);
  await expect(
    page.getByText("Регистрации, активация, платежи и формирование отчётов."),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Формирование отчётов", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Запросы и результаты учитываются по дате каждого события. Доставка и прочтение отчётов не отслеживаются в этом обзоре.",
    ),
  ).toBeVisible();
  await expect(metric(page, "Принятые запросы")).toHaveText("12");
  await expect(metric(page, "Готовые отчёты")).toHaveText("8");
  await expect(metric(page, "Частично готовые отчёты")).toHaveText("3");
  await expect(metric(page, "Ошибки формирования")).toHaveText("1");
});

for (const theme of ["light", "dark"] as const) {
  test(`observed amounts and responsive layout (${theme})`, async ({
    page,
  }, info) => {
    test.skip(
      info.project.name === "chromium-mobile",
      "desktop project runs the complete viewport matrix",
    );
    await page.addInitScript((storedTheme) => {
      localStorage.setItem("astrotype-theme", storedTheme);
    }, theme);
    await page.route("**/api/**", async (route) => {
      const request = route.request();
      expect(request.method()).toBe("GET");
      expect(new URL(request.url()).pathname).toBe(overviewPath);
      await route.fulfill({ json: observedOverview });
    });
    await page.goto(pagePath);
    await expect(page.locator("html")).toHaveClass(
      new RegExp(`\\b${theme}\\b`),
    );
    await expect(
      page.getByText("Данные наблюдаются", { exact: true }),
    ).toBeVisible();
    await expect(metric(page, "Доля активации")).toHaveText(/37,5\s*%/);
    await expect(metric(page, "Способ неизвестен")).toHaveText("0");
    await expect(metric(page, "Тестовые платежи")).toHaveText("2");
    await expect(metric(page, "Начатые оплаты")).toHaveText("13");
    await expect(metric(page, "Ожидают завершения")).toHaveText("4");
    await expect(metric(page, "Не завершились оплатой")).toHaveText("3");
    await expect(metric(page, "Оплата подтверждена")).toHaveText("5");
    await expect(metric(page, "Исход неизвестен")).toHaveText("1");
    await expect(metric(page, "Режим неизвестен")).toHaveText("0");
    await expect(metric(page, "Получено").getByRole("listitem")).toHaveText([
      "9007199254740993.01 RUB",
      "59.20 USD",
    ]);
    await expect(metric(page, "Подтверждённые возвраты")).toHaveText(
      "Нет данных",
    );
    await expect(metric(page, "Активные платные доступы")).toHaveText("3");
    await expect(metric(page, "Подтверждённый минимум")).toHaveCount(0);
    await expect(
      metric(page, "Ежемесячная регулярная выручка (MRR)"),
    ).toHaveText("Не подтверждена");
    await expect(
      metric(page, "Период · Europe/Moscow").locator("time").first(),
    ).toHaveText(/24 окт\. 2026.*00:00/);
    for (const width of widthMatrix) {
      await page.setViewportSize({ width, height: 920 });
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth),
      ).toBeLessThanOrEqual(width);
      expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
      await page.screenshot({
        fullPage: true,
        path: info.outputPath(`observed-${theme}-${width}.png`),
      });
    }
  });

  test(`unavailable overview is keyboard-retryable (${theme})`, async ({
    page,
  }) => {
    await page.addInitScript((storedTheme) => {
      localStorage.setItem("astrotype-theme", storedTheme);
    }, theme);
    const requests: string[] = [];
    await page.route("**/api/**", async (route) => {
      const request = route.request();
      const path = new URL(request.url()).pathname;
      requests.push(`${request.method()} ${path}`);
      if (path === "/api/v1/users/me") {
        await route.fulfill({
          json: {
            id: "operator-fixture",
            name: "Оператор",
            email: "operator@example.com",
            is_active: true,
          },
        });
        return;
      }
      await route.fulfill({
        status: 503,
        json: { detail: "internal diagnostic" },
      });
    });
    await page.goto(pagePath);
    await expect(
      page.getByRole("heading", { name: "Бизнес-обзор" }),
    ).toBeVisible();
    await expect(page.getByRole("main").getByRole("alert")).toContainText(
      "Данные недоступны",
    );
    await expect(page.getByText("internal diagnostic")).toHaveCount(0);
    await expect(
      page.getByRole("heading", { name: "Платежи и возвраты" }),
    ).toHaveCount(0);
    await expect(page.locator("html")).toHaveClass(
      new RegExp(`\\b${theme}\\b`),
    );

    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("link", { name: "В личный кабинет" }),
    ).toBeFocused();
    await page.keyboard.press("Tab");
    const retry = page.getByRole("button", { name: "Повторить запрос" });
    await expect(retry).toBeFocused();
    expect(
      await retry.evaluate((element) => getComputedStyle(element).outlineStyle),
    ).not.toBe("none");
    await page.keyboard.press("Enter");
    await expect
      .poll(() => requests)
      .toEqual([`GET ${overviewPath}`, `GET ${overviewPath}`]);
    await expect(page.getByRole("main").getByRole("alert")).toContainText(
      "Данные недоступны",
    );
    await expect(retry).toBeFocused();
    expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
    await page.keyboard.press("Shift+Tab");
    await expect(
      page.getByRole("link", { name: "В личный кабинет" }),
    ).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/dashboard$/);
    await expect(
      page.getByRole("heading", { name: "Оператор, ваша карта рядом" }),
    ).toBeVisible();
  });
}

test("overview denial renders no aggregate or server diagnostic", async ({
  page,
}) => {
  await page.route(`**${overviewPath}`, (route) =>
    route.fulfill({ status: 403, json: { detail: "internal diagnostic" } }),
  );
  await page.goto(pagePath);
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Нет доступа",
  );
  await expect(page.getByText("internal diagnostic")).toHaveCount(0);
  await expect(
    page.getByRole("heading", { name: "Платежи и возвраты" }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Повторить запрос" }),
  ).toHaveCount(0);
});

test("server coverage and cohort states stay distinct from observed zero", async ({
  page,
}) => {
  let release = () => {};
  const holdResponse = new Promise<void>((resolve) => {
    release = resolve;
  });
  let requests = 0;
  await page.route(`**${overviewPath}`, async (route) => {
    requests += 1;
    if (requests === 1) {
      await holdResponse;
      await route.fulfill({ json: staleOverview });
    } else {
      await route.fulfill({ json: unavailableOverview });
    }
  });
  await page.goto(pagePath);
  try {
    await expect(
      page
        .getByRole("status")
        .filter({ hasText: "Загружаем бизнес-показатели" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Платежи и возвраты" }),
    ).toHaveCount(0);
  } finally {
    release();
  }
  await expect(
    page.getByText("Данные устарели", { exact: true }),
  ).toBeVisible();
  await expect(metric(page, "Доля активации")).toHaveText(
    "7 дней наблюдения ещё не прошли",
  );
  await expect(metric(page, "Реальные платежи")).toHaveText("0");
  await expect(metric(page, "Ожидают завершения")).toHaveText("0");
  await expect(metric(page, "Активные платные доступы")).toHaveText("0");
  await expect(metric(page, "Получено")).toHaveText("Нет реальных поступлений");

  await page.getByRole("button", { name: "Обновить данные" }).click();
  await expect(
    page.getByText("Покрытие недоступно", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText(/Покрытие периода неполное/)).toBeVisible();
  await expect(metric(page, "Доля активации")).toHaveText("Нет данных");
  await expect(metric(page, "Реальные платежи")).toHaveText("Нет данных");
  await expect(metric(page, "Ожидают завершения")).toHaveText("Нет данных");
  await expect(metric(page, "Не завершились оплатой")).toHaveText("Нет данных");
  await expect(metric(page, "Оплата подтверждена")).toHaveText("Нет данных");
  await expect(metric(page, "Исход неизвестен")).toHaveText("Нет данных");
  await expect(metric(page, "Получено")).toHaveText("Нет данных");
  await expect(metric(page, "Активные платные доступы")).toHaveText(
    "Нет данных",
  );
  await expect(metric(page, "Подтверждённый минимум")).toHaveCount(0);
  await expect(
    page.getByText("Оценочные затраты не входят в этот обзор."),
  ).toBeVisible();
});

for (const { title, overview, minimum, cashReason } of [
  {
    title: "unclassified receipts",
    overview: unknownReceiptsOverview,
    minimum: "3",
    cashReason: "Есть платежи с неизвестным режимом.",
  },
  {
    title: "an incomplete window",
    overview: incompleteWindowOverview,
    minimum: "0",
    cashReason: "Неполное покрытие периода.",
  },
]) {
  test(`cash is unavailable for ${title} and partial Plus shows only a lower bound`, async ({
    page,
  }) => {
    await page.route(`**${overviewPath}`, (route) =>
      route.fulfill({ json: overview }),
    );
    await page.goto(pagePath);
    await expect(metric(page, "Получено")).toHaveText(
      `Нет данных ${cashReason}`,
    );
    await expect(metric(page, "Получено").getByRole("listitem")).toHaveCount(0);
    await expect(metric(page, "Реальные платежи")).toHaveText("4");
    await expect(metric(page, "Режим неизвестен")).toHaveText(
      String(overview.payments.unknown),
    );
    await expect(metric(page, "Активные платные доступы")).toHaveText(
      "Нет данных",
    );
    await expect(metric(page, "Подтверждённый минимум")).toHaveText(minimum);
    await expect(
      page.getByText("Неполное покрытие платных периодов"),
    ).toBeVisible();
  });
}

test("malformed money is rejected rather than silently rounded or zero-filled", async ({
  page,
}) => {
  await page.route(`**${overviewPath}`, (route) =>
    route.fulfill({
      json: {
        ...observedOverview,
        live_cash_received: [{ currency: "RUB", amount: 123.45 }],
      },
    }),
  );
  await page.goto(pagePath);
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Данные недоступны",
  );
  await expect(
    page.getByRole("heading", { name: "Платежи и возвраты" }),
  ).toHaveCount(0);
});

test("missing session offers sign-in without rendering the overview", async ({
  page,
}) => {
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    expect(`${request.method()} ${path}`).toMatch(
      /^(GET \/api\/v1\/admin\/business\/overview|POST \/api\/v1\/auth\/refresh)$/,
    );
    await route.fulfill({
      status: 401,
      json: { detail: "unauthenticated fixture" },
    });
  });
  await page.goto(pagePath);
  await expect(page.getByRole("main").getByRole("alert")).toContainText(
    "Войдите, чтобы открыть бизнес-обзор",
  );
  await expect(page.getByRole("link", { name: "Войти" })).toHaveAttribute(
    "href",
    "/login?next=%2Fadmin%2Fbusiness",
  );
  await expect(
    page.getByRole("heading", { name: "Платежи и возвраты" }),
  ).toHaveCount(0);
});
