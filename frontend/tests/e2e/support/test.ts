import { chromium, expect, test as base } from "@playwright/test";

export const test = base.extend({
  browser: async ({ playwright }, provideBrowser) => {
    const endpoint = process.env.PLAYWRIGHT_CDP_ENDPOINT;
    const browser = endpoint
      ? await chromium.connectOverCDP(endpoint)
      : await playwright.chromium.launch({ headless: true });
    await provideBrowser(browser);
    await browser.close();
  },
});

export { expect };
