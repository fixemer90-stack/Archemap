import { expect, test } from "./support/test";
import { mockE22Child } from "./support/mock-e22-child";

test("enabled Child is reachable from dashboard card and desktop/mobile menu", async ({
  page,
}) => {
  await mockE22Child(page);
  await page.route("**/api/v1/profiles", (route) =>
    route.fulfill({ json: { items: [] } }),
  );
  await page.route("**/api/v1/billing/access", (route) =>
    route.fulfill({
      json: {
        account_tier: "plus",
        access_state: "plus_active",
        child_enabled: true,
        accessible_products: ["self", "child"],
        subscription: null,
        entitlements: [],
        latest_payment: null,
      },
    }),
  );
  await page.goto("/dashboard");
  const card = page.locator('[data-product-surface="card"]').filter({
    has: page.getByRole("heading", { name: "Ребёнок", exact: true }),
  });
  await expect(
    card.getByRole("link", { name: "Открыть", exact: true }),
  ).toBeVisible();
  await expect(card.getByText("позже", { exact: true })).toHaveCount(0);
  await card.getByRole("link", { name: "Открыть", exact: true }).click();
  await expect(page).toHaveURL(/\/products\/child$/);
  await expect(
    page.getByRole("heading", { name: "Ближе к ребёнку, бережнее к себе" }),
  ).toBeVisible();
  await page.goto("/dashboard");
  if ((page.viewportSize()?.width ?? 1440) < 768)
    await page
      .getByRole("button", { name: "Открыть меню", exact: true })
      .click();
  const menu = page
    .getByRole("navigation", { name: "Продукты", exact: true })
    .getByRole("link", { name: "Child", exact: true });
  await expect(menu).toHaveAttribute("href", "/products/child");
  await expect(menu).not.toHaveAttribute("aria-disabled", "true");
  await menu.click();
  await expect(page).toHaveURL(/\/products\/child$/);
  await expect(
    page.getByRole("heading", { name: "Ближе к ребёнку, бережнее к себе" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
});

for (const availability of [false, undefined, "unavailable"] as const) {
  test(`Child stays unavailable for disabled, legacy or failed metadata: ${availability}`, async ({
    page,
  }) => {
    await mockE22Child(page);
    await page.route("**/api/v1/profiles", (route) =>
      route.fulfill({ json: { items: [] } }),
    );
    await page.route("**/api/v1/billing/access", (route) =>
      availability === "unavailable"
        ? route.fulfill({ status: 503, json: { detail: "Unavailable" } })
        : route.fulfill({
            json: {
              account_tier: "plus",
              access_state: "plus_active",
              child_enabled: availability,
              accessible_products: ["self", "child"],
              subscription: null,
              entitlements: [],
              latest_payment: null,
            },
          }),
    );
    await page.goto("/dashboard");
    const card = page.locator('[data-product-surface="card"]').filter({
      has: page.getByRole("heading", { name: "Ребёнок", exact: true }),
    });
    await expect(
      card.getByRole("button", { name: "В планах", exact: true }),
    ).toBeDisabled();
    await expect(
      card.getByRole("link", { name: "Открыть", exact: true }),
    ).toHaveCount(0);
    if ((page.viewportSize()?.width ?? 1440) < 768)
      await page
        .getByRole("button", { name: "Открыть меню", exact: true })
        .click();
    const menu = page
      .getByRole("navigation", { name: "Продукты", exact: true })
      .getByRole("link", { name: "Child", exact: true });
    await expect(menu).toHaveAttribute("aria-disabled", "true");
    await expect(menu).toHaveAttribute("href", "#");
  });
}

test("Child availability does not bypass paid product access", async ({
  page,
}) => {
  await mockE22Child(page);
  await page.route("**/api/v1/profiles", (route) =>
    route.fulfill({ json: { items: [] } }),
  );
  await page.route("**/api/v1/billing/access", (route) =>
    route.fulfill({
      json: {
        account_tier: "free",
        access_state: "plus_inactive",
        child_enabled: true,
        accessible_products: ["self"],
        subscription: null,
        entitlements: [],
        latest_payment: null,
      },
    }),
  );
  await page.goto("/dashboard");
  const card = page.locator('[data-product-surface="card"]').filter({
    has: page.getByRole("heading", { name: "Ребёнок", exact: true }),
  });
  await expect(
    card.getByRole("link", { name: "Открыть Plus", exact: true }),
  ).toHaveAttribute("href", "/billing");
  await expect(
    card.getByRole("link", { name: "Открыть", exact: true }),
  ).toHaveCount(0);
  if ((page.viewportSize()?.width ?? 1440) < 768)
    await page
      .getByRole("button", { name: "Открыть меню", exact: true })
      .click();
  const menu = page
    .getByRole("navigation", { name: "Продукты", exact: true })
    .getByRole("link", { name: "Child", exact: true });
  await expect(menu).toHaveAttribute("href", "/products/child");
  await expect(menu).not.toHaveAttribute("aria-disabled", "true");
});
