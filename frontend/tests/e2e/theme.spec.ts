import AxeBuilder from "@axe-core/playwright";

import { mockSettingsApi } from "./support/mock-settings";
import { expect, test } from "./support/test";

const themeButton = (page: import("@playwright/test").Page, name: string) =>
  page.getByRole("button", { name });

test("light, dark, and system preferences persist without resetting settings state", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.addInitScript(() => {
    if (localStorage.getItem("astrotype-theme") === null) {
      localStorage.setItem("astrotype-theme", "light");
    }
  });
  await mockSettingsApi(page);

  const hydrationErrors: string[] = [];
  page.on("console", (message) => {
    if (
      message.type() === "error" &&
      /hydration|did not match/i.test(message.text())
    ) {
      hydrationErrors.push(message.text());
    }
  });

  await page.goto("/settings?section=appearance", {
    waitUntil: "domcontentloaded",
  });

  await expect(page.locator("html")).toHaveClass(/light/);
  await expect(themeButton(page, "Светлая")).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  const name = page.getByLabel("Имя");
  await name.fill("Алина — несохранённое изменение");

  await themeButton(page, "Тёмная").focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveClass(/dark/);
  await expect(themeButton(page, "Тёмная")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(name).toHaveValue("Алина — несохранённое изменение");
  expect(new URL(page.url()).searchParams.get("section")).toBe("appearance");
  expect(
    await page.evaluate(() => localStorage.getItem("astrotype-theme")),
  ).toBe("dark");

  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator("html")).toHaveClass(/dark/);
  await expect(themeButton(page, "Тёмная")).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  await themeButton(page, "Как в системе").click();
  await expect(themeButton(page, "Как в системе")).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(
    await page.evaluate(() => localStorage.getItem("astrotype-theme")),
  ).toBe("system");

  await page.emulateMedia({ colorScheme: "light" });
  await expect(page.locator("html")).toHaveClass(/light/);
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.locator("html")).toHaveClass(/dark/);

  expect(hydrationErrors).toEqual([]);
  const accessibility = await new AxeBuilder({ page }).analyze();
  expect(
    accessibility.violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact ?? ""),
    ),
  ).toEqual([]);
});
