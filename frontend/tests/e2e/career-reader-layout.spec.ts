import { mockCareerApi } from "./support/mock-career";
import { setStoredTheme } from "./support/mock-theme";
import { expect, test } from "./support/test";

for (const theme of ["dark", "light"] as const) {
  for (const width of [320, 390, 768, 1024, 1440]) {
    test(`reader hero keeps full content inside its bounds: ${theme} ${width}px`, async ({
      page,
    }) => {
      await page.setViewportSize({ width, height: 1000 });
      await setStoredTheme(page, theme);
      await mockCareerApi(page);
      await page.goto("/products/career/report/report-1", {
        waitUntil: "domcontentloaded",
      });
      const heading = page.getByRole("heading", {
        name: "Профессиональная механика без готовых ярлыков",
        exact: true,
      });
      await expect(heading).toBeVisible();
      await page.evaluate(() => document.fonts.ready.then(() => undefined));
      const hero = page.locator("article.career-reader > header");
      await expect(hero.getByLabel("Краткий профиль")).toBeVisible();
      await expect(
        hero.getByText("Расчёт сохранён", { exact: true }),
      ).toBeVisible();
      await expect(hero).toContainText("Он не назначает профессию.");
      const geometry = await hero.evaluate((element) => {
        const bounds = element.getBoundingClientRect();
        const escaped = Array.from(
          element.querySelectorAll<HTMLElement>("h1,p,span,aside,aside > div"),
        ).flatMap((child) => {
          const box = child.getBoundingClientRect();
          const range = document.createRange();
          range.selectNodeContents(child);
          const clippedText = Array.from(range.getClientRects()).some(
            (rect) =>
              rect.left < bounds.left - 1 ||
              rect.right > bounds.right + 1 ||
              rect.top < bounds.top - 1 ||
              rect.bottom > bounds.bottom + 1,
          );
          return box.left < bounds.left - 1 ||
            box.right > bounds.right + 1 ||
            child.scrollWidth > child.clientWidth + 1 ||
            child.scrollHeight > child.clientHeight + 1 ||
            clippedText
            ? [child.textContent?.trim()]
            : [];
        });
        const heading = element.querySelector("h1")!;
        const firstWord = document.createRange();
        firstWord.setStart(heading.firstChild!, 0);
        firstWord.setEnd(
          heading.firstChild!,
          heading.textContent!.indexOf(" "),
        );
        return {
          headingFirstWordLines: firstWord.getClientRects().length,
          escaped,
          heroOverflow: element.scrollWidth > element.clientWidth + 1,
          documentOverflow:
            document.documentElement.scrollWidth >
            document.documentElement.clientWidth,
        };
      });
      expect(geometry).toEqual({
        headingFirstWordLines: 1,
        escaped: [],
        heroOverflow: false,
        documentOverflow: false,
      });
    });
  }
}
