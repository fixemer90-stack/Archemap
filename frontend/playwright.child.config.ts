import { defineConfig, devices } from "@playwright/test";

const baseURL = "http://127.0.0.1:3313";
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /e22-child.*\.spec\.ts/,
  workers: 1,
  timeout: 60000,
  expect: { timeout: 10000 },
  use: { baseURL, reducedMotion: "reduce", trace: "retain-on-failure" },
  projects: [
    {
      name: "child-desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "child-tablet",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 820, height: 1180 },
      },
    },
    {
      name: "child-mobile",
      use: { ...devices["Pixel 7"], viewport: { width: 390, height: 844 } },
    },
  ],
  webServer: {
    command: "npm run dev -- --hostname 127.0.0.1 --port 3313",
    url: baseURL,
    reuseExistingServer: false,
    timeout: 300000,
  },
});
