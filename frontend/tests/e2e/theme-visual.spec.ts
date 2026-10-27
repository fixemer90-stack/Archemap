import type { Page } from "@playwright/test";

import { mockThemeMatrixApi, setStoredTheme } from "./support/mock-theme";
import { expect, test } from "./support/test";

const surfaces = [
  { key: "homepage", path: "/", ready: "body" },
  { key: "auth-login", path: "/login", ready: "body" },
  {
    key: "dashboard-shell",
    path: "/dashboard",
    ready: "main",
    quickThemeSwitch: true,
  },
  {
    key: "settings",
    path: "/settings",
    ready: "main",
    quickThemeSwitch: true,
  },
  {
    key: "billing",
    path: "/billing",
    ready: "main",
    quickThemeSwitch: true,
  },
  {
    key: "career-product",
    path: "/products/career?profileId=profile-1",
    ready: "body",
  },
  {
    key: "v2-report",
    path: "/report/v2/profile-1",
    ready: "main",
  },
  {
    key: "v2-report-loading",
    path: "/report/v2/profile-loading",
    ready: "main",
  },
  {
    key: "v2-report-error",
    path: "/report/v2/profile-error",
    ready: "main",
  },
  {
    key: "career-report",
    path: "/products/career/report/report-1",
    ready: "article.career-reader",
  },
] as const;

for (const theme of ["light", "dark"] as const) {
  test(`visual theme matrix: ${theme}`, async ({ page }) => {
    await setStoredTheme(page, theme);
    await mockThemeMatrixApi(page);

    for (const surface of surfaces) {
      await page.goto(surface.path, { waitUntil: "domcontentloaded" });
      await expect(page.locator("html")).toHaveClass(new RegExp(theme));
      await expect(page.locator(surface.ready).first()).toBeVisible();
      await expect(
        page.getByText("Проверяем сессию...", { exact: true }),
      ).toHaveCount(0);
      if ("quickThemeSwitch" in surface && surface.quickThemeSwitch) {
        const quickThemeSwitch = page.locator('[data-theme-toggle="quick"]');
        await expect(quickThemeSwitch).toBeVisible();
        await expect(quickThemeSwitch).toBeEnabled();
      }
      if (surface.key === "v2-report") {
        await assertV2ChartRendering(page);
      }
      await expect(page.getByText(/Unhandled mock route/)).toHaveCount(0);
      await expect(page).toHaveScreenshot(`${surface.key}-${theme}.png`, {
        animations: "disabled",
        caret: "initial",
        maxDiffPixels: 150,
      });
    }

    await page.goto("/products/career/report/report-1", {
      waitUntil: "domcontentloaded",
    });
    const tooltipTrigger = page
      .locator('[data-career-term="Выраженность"]')
      .first();
    await tooltipTrigger.focus();
    const tooltipId = await tooltipTrigger.getAttribute("aria-describedby");
    expect(tooltipId).toBeTruthy();
    await expect(page.locator(`#${tooltipId}`)).toBeVisible();
    await expect(page).toHaveScreenshot(`tooltip-${theme}.png`, {
      animations: "disabled",
      caret: "initial",
      maxDiffPixels: 150,
    });
  });
}

async function assertV2ChartRendering(page: Page) {
  const fills = page.locator("[data-chart-fill]");
  await expect(fills.first()).toBeVisible();
  const fillStyles = await fills.evaluateAll((elements) =>
    elements.map((element) => {
      const styles = getComputedStyle(element);
      return {
        backgroundImage: styles.backgroundImage,
        backgroundColor: styles.backgroundColor,
      };
    }),
  );
  expect(fillStyles.length).toBeGreaterThan(0);
  for (const fill of fillStyles) {
    expect(
      fill.backgroundImage !== "none" ||
        fill.backgroundColor !== "rgba(0, 0, 0, 0)",
    ).toBe(true);
  }

  const fireRow = page.locator('[data-balance-key="elements:fire"]');
  await expect(fireRow.locator('[data-balance-value="fire"]')).toHaveText(
    "50%",
  );
  const balanceGeometry = await fireRow.evaluate((element) => {
    const fill = element.querySelector<HTMLElement>(
      '[data-chart-fill="balance"]',
    );
    const track = fill?.parentElement;
    if (!fill || !track) return null;
    return (
      fill.getBoundingClientRect().width / track.getBoundingClientRect().width
    );
  });
  expect(balanceGeometry).not.toBeNull();
  expect(balanceGeometry ?? 0).toBeGreaterThan(0.48);
  expect(balanceGeometry ?? 1).toBeLessThan(0.52);

  await expect(page.locator('[data-house-fill="4"]')).toHaveCSS(
    "height",
    "0px",
  );
  await expect(page.locator('[data-house-label="4"]')).toBeVisible();

  const networkKeys = await page
    .locator("[data-aspect-edge]")
    .evaluateAll((elements) =>
      elements
        .map((element) => element.getAttribute("data-aspect-edge"))
        .sort(),
    );
  const tableKeys = await page
    .locator(
      '[data-v2-calculation-block="key_aspects"] > div [data-aspect-row]',
    )
    .evaluateAll((elements) =>
      elements.map((element) => element.getAttribute("data-aspect-row")).sort(),
    );
  expect(tableKeys).toEqual(networkKeys);

  const details = page.locator(
    '[data-v2-calculation-block="key_aspects"] details',
  );
  const summary = details.locator("summary");
  await expect(details).not.toHaveAttribute("open", "");
  await summary.focus();
  await expect(summary).toBeFocused();
  await summary.press("Enter");
  await expect(details).toHaveAttribute("open", "");
  await summary.press("Enter");
  await expect(details).not.toHaveAttribute("open", "");
  await page.evaluate(() =>
    (document.activeElement as HTMLElement | null)?.blur(),
  );

  await expect(page.locator("body")).toContainText("Водолей");
  await expect(page.locator("body")).toContainText("Стрелец");
  await expect(page.locator("body")).toContainText("Северный узел");
  await expect(page.locator("body")).not.toContainText("Aquarius");
  await expect(page.locator("body")).not.toContainText("Sagittarius");
  await expect(page.locator("body")).not.toContainText("North Node");
  await expect(page.locator("body")).not.toContainText("orb");
}
