import { mockThemeMatrixApi, v2ReadyReport } from "./support/mock-theme";
import { expect, test } from "./support/test";

test("saved shuffled planet DTO displays the classical main ten before points", async ({
  page,
}) => {
  await mockThemeMatrixApi(page);
  const payload = structuredClone(v2ReadyReport);
  const bodies = [
    "Vertex",
    "Pluto",
    "Ascendant",
    "Sun",
    "Neptune",
    "Moon",
    "MC",
    "Uranus",
    "Mercury",
    "Saturn",
    "Venus",
    "Jupiter",
    "Mars",
    "Unknown Z",
    "Chiron",
    "North Node",
    "Lilith",
    "South Node",
    "Part of Fortune",
    "Unknown A",
  ];
  const template = payload.infographic.calculation_layer.planet_positions[0];
  payload.infographic.calculation_layer.planet_positions = bodies.map(
    (body, index) => ({
      ...template,
      body,
      sign_degree: index + 0.25,
      degree_label: `${index}°15′`,
    }),
  );
  await page.route("**/api/v1/astrotype-v2/reports/v2-report-1", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payload),
    }),
  );
  await page.goto("/report/v2/profile-1", { waitUntil: "domcontentloaded" });
  const rows = page.locator(
    '[data-v2-calculation-block="planet_positions"] tbody tr',
  );
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
    "Chiron",
    "Северный узел",
    "South Node",
    "Лилит",
    "Part of Fortune",
    "Vertex",
    "Асцендент",
    "MC",
    "Unknown Z",
    "Unknown A",
  ]);
  await expect(rows.nth(0).locator("td").nth(3)).toHaveText("3°15′");
  await expect(rows.nth(9).locator("td").nth(3)).toHaveText("1°15′");
});
