import { mockThemeMatrixApi, setStoredTheme } from "./support/mock-theme";
import { expect, test } from "./support/test";

const surfaces = [
  { key: "homepage", path: "/", ready: "body" },
  { key: "auth-login", path: "/login", ready: "body" },
  { key: "dashboard-shell", path: "/dashboard", ready: "main" },
  { key: "settings", path: "/settings", ready: "main" },
  { key: "billing", path: "/billing", ready: "main" },
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
