import AxeBuilder from "@axe-core/playwright";

import { mockThemeMatrixApi, setStoredTheme } from "./support/mock-theme";
import { expect, test } from "./support/test";

const routes = [
  "/",
  "/login",
  "/dashboard",
  "/settings",
  "/billing",
  "/products/career?profileId=profile-1",
  "/report/v2/profile-1",
  "/report/v2/profile-loading",
  "/report/v2/profile-error",
  "/products/career/report/report-1",
] as const;

for (const theme of ["light", "dark"] as const) {
  test(`accessibility and overflow theme matrix: ${theme}`, async ({
    page,
  }, testInfo) => {
    await setStoredTheme(page, theme);
    await mockThemeMatrixApi(page);

    for (const path of routes) {
      await page.goto(path, { waitUntil: "domcontentloaded" });
      await expect(page.locator("html")).toHaveClass(new RegExp(theme));
      expect(
        await page.evaluate(
          () =>
            document.documentElement.scrollWidth <=
            document.documentElement.clientWidth,
        ),
        `${path} overflows at ${testInfo.project.name} in ${theme}`,
      ).toBe(true);

      if (testInfo.project.name === "chromium-desktop") {
        const accessibility = await new AxeBuilder({ page }).analyze();
        expect(
          accessibility.violations.filter((violation) =>
            ["serious", "critical"].includes(violation.impact ?? ""),
          ),
          `${path} has serious/critical axe violations in ${theme}`,
        ).toEqual([]);
      }
    }

    await page.goto("/settings", { waitUntil: "domcontentloaded" });
    const selector = page.getByRole("button", { name: "Как в системе" });
    await selector.focus();
    await expect(selector).toBeFocused();
    const focusStyles = await selector.evaluate((element) => {
      const styles = getComputedStyle(element);
      return `${styles.outlineStyle}|${styles.boxShadow}`;
    });
    expect(focusStyles).not.toBe("none|none");
  });
}
