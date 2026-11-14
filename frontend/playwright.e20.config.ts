import { defineConfig, devices } from "@playwright/test";

const baseURL = "http://127.0.0.1:3314";
export default defineConfig({
  testDir: "./tests/e2e",
  outputDir: "./test-results/e20",
  workers: 1,
  timeout: 60000,
  expect: { timeout: 10000 },
  use: { baseURL, reducedMotion: "reduce", trace: "retain-on-failure" },
  projects: [
    {
      name: "e20-desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1440, height: 1000 },
      },
    },
    {
      name: "e20-tablet",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 820, height: 1180 },
      },
    },
    {
      name: "e20-mobile",
      use: { ...devices["Pixel 7"], viewport: { width: 390, height: 844 } },
    },
  ],
  webServer: {
    command: "npm run dev -- --webpack --hostname 127.0.0.1 --port 3314",
    url: baseURL,
    reuseExistingServer: false,
    timeout: 300000,
  },
});
