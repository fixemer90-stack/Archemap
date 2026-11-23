import { expect, test } from "./support/test";

const enabled = process.env.ANALYTICS_TEST_ENABLED === "true";
const version = "test-only-v1";
const consentKey = "astrotype.analytics.consent";
const snapshotKey = "astrotype.analytics.attribution";
const receipt = "r".repeat(43);
const attribution = "**/api/v1/analytics/attribution/";
const vendorUrl = "https://mc.yandex.ru/metrika/tag.js";
const allow = "Разрешить аналитику";
const revoke = "Отозвать согласие";
const owner = {
  id: "synthetic",
  name: "Fixture",
  email: "synthetic@example.test",
  is_active: true,
  is_verified: true,
};

test.beforeEach(async ({ context }) => {
  await context.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (!["127.0.0.1", "localhost"].includes(url.hostname))
      return route.abort();
    if (url.pathname.startsWith("/api/")) {
      return route.fulfill({
        status: 401,
        json: { detail: "Unauthenticated fixture" },
      });
    }
    return route.continue();
  });
});

test("default-off landing and full-document private navigation send no referrer", async ({
  page,
}) => {
  const response = await page.goto("/?token=PRIVATE_SENTINEL#DOB_SENTINEL");
  expect(response?.headers()["referrer-policy"]).toBe("no-referrer");
  await expect(
    page.getByRole("heading", {
      name: "Не гороскоп. Личный отчёт по вашей карте рождения.",
    }),
  ).toBeVisible();
  if (!enabled)
    await expect(page.getByRole("button", { name: allow })).toHaveCount(0);
  await page.evaluate(() => {
    Reflect.set(window, "documentSentinel", true);
  });
  await page.getByRole("link", { name: "Регистрация", exact: true }).click();
  await expect(page).toHaveURL(/\/register$/);
  expect(
    await page.evaluate(() => Reflect.get(window, "documentSentinel")),
  ).toBeUndefined();
  expect(await page.evaluate(() => document.referrer)).toBe("");
  expect(
    await page.evaluate(
      () =>
        document.documentElement.scrollWidth <=
        document.documentElement.clientWidth,
    ),
  ).toBe(true);
});

test("private documents never attempt a vendor load", async ({ page }) => {
  const vendorRequests: string[] = [];
  page.on("request", (request) => {
    if (/mc\.yandex|metrika/.test(request.url()))
      vendorRequests.push(request.url());
  });
  for (const path of [
    "/login",
    "/register",
    "/dashboard",
    "/admin",
    "/products/self",
    "/profiles",
    "/report/PRIVATE_SENTINEL",
  ]) {
    const response = await page.goto(path);
    expect(response?.headers()["referrer-policy"]).toBe("no-referrer");
    await expect(page.locator('script[src*="metrika"]')).toHaveCount(0);
  }
  expect(vendorRequests).toEqual([]);
});

test("storage sentinels stay intact and vendor code cannot load even with opt-in and all legacy flags", async ({
  page,
  baseURL,
}) => {
  test.skip(
    !enabled,
    "synthetic approval; run with all legacy external input flags set",
  );
  const attempts: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.origin !== new URL(baseURL!).origin) attempts.push(url.href);
  });
  // If someone restores the loader, this fixture executes in the app origin
  // and demonstrates the exact access we must prevent. It cannot dial Yandex.
  await page.route(vendorUrl, (route) =>
    route.fulfill({
      contentType: "application/javascript",
      body: "window.storageRead = [localStorage.getItem('astrotype-auth'), sessionStorage.getItem('report-storage-sentinel')];",
    }),
  );
  const captures: unknown[] = [];
  await page.route(`${attribution}capture`, async (route) => {
    const headers = await route.request().allHeaders();
    expect(headers.origin).toBe(new URL(baseURL!).origin);
    expect(headers["x-analytics-request"]).toBe("1");
    expect(headers.referer).toBeUndefined();
    captures.push(route.request().postDataJSON());
    await route.fulfill({ status: 201, json: { receipt } });
  });
  const auth = JSON.stringify({
    state: {
      user: {
        name: "PRIVATE_NAME_SENTINEL",
        email: "PRIVATE_EMAIL@example.test",
      },
    },
    version: 0,
  });
  await page.goto("/");
  await page.evaluate((auth) => {
    localStorage.setItem("astrotype-auth", auth);
    sessionStorage.setItem("report-storage-sentinel", "PRIVATE_REPORT_ID");
  }, auth);
  await expect(page.getByRole("button", { name: allow })).toBeEnabled();
  expect(attempts).toEqual([]);
  expect(captures).toEqual([]);
  await page.getByRole("button", { name: allow }).click();
  await expect
    .poll(() =>
      page.evaluate((key) => sessionStorage.getItem(key), snapshotKey),
    )
    .toContain(receipt);
  expect(captures).toEqual([
    { granted: true, client_id: null, policy_version: version },
  ]);
  expect(
    await page.evaluate(() => Reflect.get(window, "storageRead")),
  ).toBeUndefined();
  await expect(page.locator('script[src*="metrika"]')).toHaveCount(0);
  expect(attempts).toEqual([]);
  expect(
    await page.evaluate(() => [
      localStorage.getItem("astrotype-auth"),
      sessionStorage.getItem("report-storage-sentinel"),
    ]),
  ).toEqual([auth, "PRIVATE_REPORT_ID"]);
});

test("dirty original URL and private referrer do not allow even first-party capture", async ({
  page,
  baseURL,
}) => {
  test.skip(!enabled, "synthetic policy fixture only");
  const requests: unknown[] = [];
  await page.route(`${attribution}capture`, async (route) => {
    requests.push(route.request().postDataJSON());
    await route.fulfill({ status: 201, json: { receipt } });
  });
  await page.goto("/?token=PRIVATE_SENTINEL#DOB_SENTINEL");
  await page.getByRole("button", { name: allow }).click();
  await expect(page.getByRole("button", { name: allow })).toHaveCount(0);
  await page.evaluate(() => history.replaceState(history.state, "", "/"));
  await page.goto("/", {
    referer: new URL("/report/PRIVATE_TOKEN", baseURL).href,
  });
  expect(await page.evaluate(() => document.referrer)).toContain(
    "PRIVATE_TOKEN",
  );
  expect(requests).toEqual([]);
  await page.goto("/");
  await expect
    .poll(() => requests)
    .toEqual([{ granted: true, client_id: null, policy_version: version }]);
});

test("receipt 404 on authenticated entry clears the legacy latch's effect", async ({
  page,
}) => {
  test.skip(!enabled, "synthetic policy fixture only");
  const pending = "x".repeat(43);
  let authenticated = false;
  const attached: unknown[] = [];
  await page.route("**/api/v1/users/me", (route) =>
    route.fulfill({ status: 200, json: owner }),
  );
  await page.route(`${attribution}attach`, async (route) => {
    if (!authenticated) return route.fulfill({ status: 401 });
    const body = route.request().postDataJSON();
    attached.push(body);
    await route.fulfill({ status: body.receipt === pending ? 404 : 204 });
  });
  await page.route(`${attribution}capture`, (route) =>
    route.fulfill({ status: 201, json: { receipt } }),
  );
  // Seed on a document with no landing effect, so delayed hydration of that
  // effect cannot race the deliberately expired authenticated handoff.
  await page.goto("/register");
  await page.evaluate(
    ({ consentKey, snapshotKey, pending, version }) => {
      localStorage.setItem(
        consentKey,
        JSON.stringify({ granted: true, version }),
      );
      localStorage.setItem("astrotype.analytics.captured-version", version);
      sessionStorage.setItem(
        snapshotKey,
        JSON.stringify({ receipt: pending, version }),
      );
    },
    { consentKey, snapshotKey, pending, version },
  );
  authenticated = true;
  await page.goto("/dashboard");
  await expect.poll(() => attached).toEqual([{ receipt: pending }]);
  await expect
    .poll(() =>
      page.evaluate((key) => sessionStorage.getItem(key), snapshotKey),
    )
    .toBeNull();
  await page.goto("/");
  await expect
    .poll(() => attached)
    .toEqual([{ receipt: pending }, { receipt }]);
});

test("account revoke is reachable without SDK, a current policy or a local consent record", async ({
  page,
}) => {
  let revoked = 0;
  await page.route(`${attribution}revoke`, async (route) => {
    expect(route.request().postDataJSON()).toEqual({});
    await route.fulfill({ status: ++revoked === 1 ? 401 : 204 });
  });
  await page.goto("/");
  await page.getByRole("button", { name: revoke }).click();
  await expect(page.getByRole("status")).toContainText(
    "войдите и повторите отзыв",
  );
  await page.reload();
  await page.getByRole("button", { name: "Повторить отзыв" }).click();
  await expect(page.getByRole("status")).toContainText(
    "отозвано в браузере и в аккаунте",
  );
  expect(revoked).toBe(2);
});

test("revoke discards an in-flight capture without attaching a late receipt", async ({
  page,
}) => {
  test.skip(!enabled, "synthetic policy fixture only");
  let release = () => {};
  const pending = new Promise<void>((resolve) => {
    release = resolve;
  });
  const attached: unknown[] = [];
  const discarded: unknown[] = [];
  await page.route(`${attribution}attach`, async (route) => {
    attached.push(route.request().postDataJSON());
    await route.fulfill({ status: 204 });
  });
  await page.route(`${attribution}capture`, async (route) => {
    await pending;
    await route.fulfill({ status: 201, json: { receipt } });
  });
  await page.route(`${attribution}discard`, async (route) => {
    discarded.push(route.request().postDataJSON());
    await route.fulfill({ status: 204 });
  });
  await page.route(`${attribution}revoke`, (route) =>
    route.fulfill({ status: 204 }),
  );
  await page.goto("/");
  const capture = page.waitForRequest((req) =>
    req.url().endsWith("/attribution/capture"),
  );
  await page.getByRole("button", { name: allow }).click();
  await capture;
  try {
    await page.getByRole("button", { name: revoke }).click();
  } finally {
    release();
  }
  await expect.poll(() => discarded).toEqual([{ receipt }]);
  expect(attached).toEqual([]);
  expect(
    await page.evaluate((key) => sessionStorage.getItem(key), snapshotKey),
  ).toBeNull();
  await page.getByRole("link", { name: "Регистрация", exact: true }).click();
  await expect(page).toHaveURL(/\/register$/);
  await page.goBack();
  await expect(page.getByRole("button", { name: allow })).toBeEnabled();
  expect(attached).toEqual([]);
});
