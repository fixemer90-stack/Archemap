import { mockThemeMatrixApi, v2ReadyReport } from "./support/mock-theme";
import { expect, test } from "./support/test";

for (const width of [360, 390, 768, 1024, 1440]) {
  test(`report keeps wide planet table inside its scroller at ${width}px`, async ({
    page,
  }, testInfo) => {
    await page.setViewportSize({ width, height: 900 });
    await mockThemeMatrixApi(page);
    const payload = structuredClone(v2ReadyReport);
    const bodies = [
      "Sun",
      "Moon",
      "Ascendant",
      "Jupiter",
      "Lilith",
      "MC",
      "Mars",
      "Mercury",
      "Neptune",
      "North Node",
      "Pluto",
      "Saturn",
      "Uranus",
      "Venus",
    ];
    const template = payload.infographic.calculation_layer.planet_positions[0];
    payload.infographic.calculation_layer.planet_positions = bodies.map(
      (body, index) => ({ ...template, body, degree_label: `${index}°15′` }),
    );
    await page.route("**/api/v1/astrotype-v2/reports/v2-report-1", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(payload),
      }),
    );
    await page.goto("/report/v2/profile-1", { waitUntil: "domcontentloaded" });
    const section = page.locator(
      '[data-v2-calculation-block="planet_positions"]',
    );
    const rows = section.locator("tbody tr");
    await expect(rows).toHaveCount(14);
    await expect(rows.locator("td:first-child")).toHaveText([
      "Солнце",
      "Луна",
      "Меркурий",
      "Венера",
      "Марс",
      "Юпитер",
      "Сатурн",
      "Уран",
      "Нептун",
      "Плутон",
      "Северный узел",
      "Лилит",
      "Асцендент",
      "MC",
    ]);
    await expect(rows.nth(0).locator("td").nth(3)).toHaveText("0°15′");
    await expect(rows.nth(9).locator("td").nth(3)).toHaveText("10°15′");
    await page.evaluate(() => document.fonts.ready);
    await expect
      .poll(() =>
        page.evaluate(
          () =>
            document.documentElement.scrollWidth -
            document.documentElement.clientWidth,
        ),
      )
      .toBeLessThanOrEqual(0);
    const scroller = section.locator("table").locator("..");
    const geometry = await scroller.evaluate((element) => {
      const table = element.querySelector("table")!;
      const rect = element.getBoundingClientRect();
      const scrollable = element.scrollWidth > element.clientWidth;
      element.scrollLeft = element.scrollWidth;
      const lastCell = table
        .querySelector("thead th:last-child")!
        .getBoundingClientRect();
      return {
        scrollable,
        scrollLeft: element.scrollLeft,
        tableWidth: table.getBoundingClientRect().width,
        rightmostColumnVisible:
          lastCell.right <= rect.right + 1 && lastCell.left >= rect.left - 1,
        overflowX: getComputedStyle(element).overflowX,
        documentScrollLeft: document.documentElement.scrollLeft,
      };
    });
    expect(geometry.tableWidth).toBeGreaterThanOrEqual(760);
    expect(geometry.overflowX).toBe("auto");
    expect(geometry.rightmostColumnVisible).toBe(true);
    expect(geometry.documentScrollLeft).toBe(0);
    if (width <= 390) expect(geometry.scrollable).toBe(true);
    if (geometry.scrollable) expect(geometry.scrollLeft).toBeGreaterThan(0);
    await scroller.evaluate((element) => {
      element.scrollLeft = 0;
    });
    await section.screenshot({
      path: testInfo.outputPath(`planet-table-${width}.png`),
    });
  });
}
