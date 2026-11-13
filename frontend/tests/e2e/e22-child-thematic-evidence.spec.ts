import { expect, test } from "./support/test";
import { mockE22Child } from "./support/mock-e22-child";

test("missing thematic inputs use the saved reason instead of the legacy blanket omission", async ({
  page,
}) => {
  const evidenceNote =
    "Для этой темы нет сохранённых исходных показателей или наблюдений.";
  const state = await mockE22Child(page, {
    readerStatus: "ready",
    readerQuality: "limited",
    sectionOverrides: {
      conflict_cycle: {
        status: "not_applicable",
        body: null,
        actions: [],
        evidence_state: "missing_data",
        evidence_note: evidenceNote,
      },
    },
  });
  await page.goto("/reports/child/report-a");
  const section = page.locator('[data-child-section="conflict_cycle"]');
  await expect(section).toContainText(evidenceNote);
  await expect(section).not.toContainText("недостаточно устойчивых оснований");
  await expect(
    section.getByRole("heading", { name: "Что можно попробовать" }),
  ).toHaveCount(0);
  expect(state.creates).toEqual([]);
  expect(state.retryKeys).toEqual([]);
  expect(state.unhandled).toEqual([]);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: test.info().outputPath("child-missing-topic.png"),
    fullPage: true,
  });
});

test("moderate and mixed thematic prose remains visible without an invented conflict cycle", async ({
  page,
}) => {
  // Synthetic presentation fixture: backend provenance/persistence is verified separately.
  const bodies = {
    natural_contact:
      "По сохранённому показателю эмоциональной согласованности нет выраженного перекоса: оценка 52 из 100. Это не отсутствие данных и не обещание лёгкого контакта.",
    friction_zones:
      "В наблюдении за границами ответы расходятся с расчётным ожиданием. Сигналы неоднозначны: по этой теме нельзя уверенно назвать устойчивую зону трения.",
    conflict_cycle:
      "По показателю конфликтного взаимодействия оценка 48 из 100. Конкретная последовательность ссоры в наблюдениях не описана; по этим данным её нельзя восстановить.",
    not_personal:
      "Показатель баланса самостоятельности и помощи не устанавливает намерения ребёнка. Отсутствие выраженного перекоса не означает желание обидеть или отвергнуть взрослого.",
  };
  const state = await mockE22Child(page, {
    readerStatus: "ready",
    sectionOverrides: Object.fromEntries(
      Object.entries(bodies).map(([key, body]) => [
        key,
        { body, actions: [], status: "ready" },
      ]),
    ),
  });
  await page.goto("/reports/child/report-a");
  for (const [key, body] of Object.entries(bodies)) {
    const section = page.locator(`[data-child-section="${key}"]`);
    await expect(section.locator(".child-report-body")).toHaveText(body);
    await expect(section).not.toContainText(
      "недостаточно устойчивых оснований",
    );
  }
  await expect(page.getByRole("link", { name: "Скачать PDF" })).toHaveAttribute(
    "href",
    "/api/v1/child/reports/report-a/pdf?age_snapshot_id=age-pinned-a",
  );
  expect(state.creates).toEqual([]);
  expect(state.retryKeys).toEqual([]);
  expect(state.unhandled).toEqual([]);
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: test.info().outputPath("child-moderate-topics.png"),
    fullPage: true,
  });
});

test("failed prose is not misreported as absent thematic evidence", async ({
  page,
}) => {
  const evidenceNote =
    "В данных нет выраженного перекоса к опоре или напряжению.";
  const state = await mockE22Child(page, {
    readerStatus: "ready",
    readerQuality: "limited",
    sectionOverrides: {
      natural_contact: {
        status: "failed",
        body: null,
        actions: [],
        evidence_state: "no_pronounced_skew",
        evidence_note: evidenceNote,
      },
    },
  });
  await page.goto("/reports/child/report-a");
  const section = page.locator('[data-child-section="natural_contact"]');
  await expect(section).toContainText("Подробное пояснение пока недоступно.");
  await expect(section).not.toContainText(evidenceNote);
  await expect(section).not.toContainText("недостаточно устойчивых оснований");
  expect(state.creates).toEqual([]);
  expect(state.retryKeys).toEqual([]);
  expect(state.unhandled).toEqual([]);
});
