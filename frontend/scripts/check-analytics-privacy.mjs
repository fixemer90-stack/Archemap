import assert from "node:assert/strict";
import { existsSync, readFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { createRequire } from "node:module";
import ts from "typescript";

const source = resolve("src/lib/analytics/privacy.ts");
assert.ok(existsSync(source), "public-only privacy primitives must exist");
const directory = mkdtempSync(join(tmpdir(), "analytics-contract-"));
try {
  const output = ts.transpileModule(readFileSync(source, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  }).outputText;
  const { writeFileSync } = await import("node:fs");
  const target = join(directory, "privacy.cjs");
  writeFileSync(target, output);
  const p = createRequire(import.meta.url)(target);
  assert.equal(p.readConfig({}).enabled, false);
  for (const value of ["false", "1", "TRUE", true]) {
    assert.equal(
      p.readConfig({
        enabled: value,
        externalEnabled: "true",
        policyApproved: "true",
        policyVersion: "v1",
        counterId: "123",
      }).enabled,
      false,
    );
  }
  assert.equal(
    p.readConfig({
      enabled: "true",
      externalEnabled: "true",
      policyApproved: "true",
      policyVersion: "v1",
      counterId: "123",
    }).enabled,
    false,
    "unknown counter-side automatic-goal settings must block SDK",
  );
  const config = p.readConfig({
    settingsVerified: "true",
    enabled: "true",
    externalEnabled: "true",
    policyApproved: "true",
    policyVersion: "v1",
    counterId: "123",
  });
  assert.equal(config.enabled, true);

  for (const path of [
    "/login",
    "/register",
    "/dashboard",
    "/admin",
    "/report/secret",
    "/products/self",
    "/profiles",
    "/?token=secret",
    "//evil.test/",
  ])
    assert.equal(p.isPublicPath(path), false);
  assert.equal(p.isPublicPath("/"), true);
  assert.deepEqual(
    p.safeContext("https://example.test/?token=SECRET#DOB", ""),
    { href: "https://example.test/", referrer: "" },
  );
  for (const ref of [
    "https://example.test/report/SECRET",
    "https://example.test/?token=SECRET",
    "https://external.test/",
    "broken",
  ])
    assert.equal(p.safeContext("https://example.test/", ref), null);
  assert.equal(p.safeContext("https://example.test/login", ""), null);
  assert.equal(p.hasConsent(null, "v1"), false);
  assert.equal(p.hasConsent('{"version":"v0","granted":true}', "v1"), false);
  assert.equal(p.hasConsent('{"version":"v1","granted":true}', "v1"), true);
  assert.equal(p.safeGoal("payment_confirmed"), null);
  assert.equal(p.safeGoal("signup_cta_click"), "signup_cta_click");
  assert.deepEqual(p.attribution("12345", "v1"), {
    version: "v1",
    clientId: "12345",
    campaign: null,
  });
  assert.equal(p.attribution("email@example.test", "v1").clientId, null);
  assert.equal(p.attribution("123\n", "v1").clientId, null);
  assert.equal(p.attribution("123", "v1", "token=secret").campaign, null);
  const runtimeSource = resolve("src/lib/analytics/runtime.ts");
  assert.ok(
    existsSync(runtimeSource),
    "consent-aware cancellable runtime must exist",
  );
  writeFileSync(join(directory, "privacy.js"), output);
  writeFileSync(
    join(directory, "runtime.cjs"),
    ts.transpileModule(readFileSync(runtimeSource, "utf8"), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
      },
    }).outputText,
  );
  const { createRuntime } = createRequire(import.meta.url)(
    join(directory, "runtime.cjs"),
  );
  const calls = [];
  let release;
  let location = "https://example.test/?token=SECRET";
  let consent = false;
  const port = {
    href: () => location,
    referrer: () => "",
    consent: () => consent,
    normalize: (url) => {
      location = url;
    },
    load: () =>
      new Promise((resolve) => {
        release = resolve;
      }),
    call: (...args) => {
      calls.push(args);
      if (args[1] === "getClientID") args[2]("12345");
    },
  };
  const runtime = createRuntime(config, port);
  await runtime.start();
  assert.equal(release, undefined);
  consent = true;
  const pending = runtime.start();
  assert.equal(location, "https://example.test/");
  runtime.stop();
  release();
  await pending;
  assert.equal(calls.length, 0, "unmount while SDK pending cannot initialize");
  const changedUrl = createRuntime(config, port);
  const awaitingLoad = changedUrl.start();
  location = "https://example.test/?token=PRIVATE_AFTER_LOAD";
  release();
  await awaitingLoad;
  assert.equal(calls.length, 0, "dirty current URL must prevent late init");
  location = "https://example.test/";
  const active = createRuntime(config, { ...port, load: async () => {} });
  await Promise.all([active.start(), active.start()]);
  assert.equal(calls.filter((x) => x[1] === "init").length, 1);
  const options = calls.find((x) => x[1] === "init")[2];
  assert.equal(options.defer, true);
  for (const flag of [
    "webvisor",
    "clickmap",
    "trackLinks",
    "accurateTrackBounce",
    "trackHash",
    "ecommerce",
    "triggerEvent",
    "childIframe",
  ])
    assert.equal(options[flag], false, flag);
  assert.equal(await active.clientId(), "12345");
  active.goal("payment_confirmed");
  assert.equal(
    calls.some((x) => x.includes("payment_confirmed")),
    false,
  );
  location = "https://example.test/register";
  active.goal("signup_cta_click");
  assert.equal(await active.clientId(), null);
  active.stop();
  assert.equal(calls.at(-1)[1], "destruct");
  const blocked = createRuntime(config, {
    ...port,
    href: () => "https://example.test/",
    referrer: () => "https://example.test/report/SECRET",
    load: async () => {
      throw Error("must not load");
    },
  });
  await blocked.start();
  for (const failure of ["throw", "timeout", "load"]) {
    const failed = createRuntime(config, {
      ...port,
      href: () => "https://example.test/",
      load: async () => {
        if (failure === "load") throw new Error("PRIVATE_TOKEN");
      },
      call: () => {
        if (failure === "throw") throw new Error("PRIVATE_TOKEN");
      },
    });
    await failed.start();
    assert.equal(await failed.clientId(1), null);
    failed.goal("signup_cta_click");
    failed.stop();
  }
  writeFileSync(
    join(directory, "first-party.cjs"),
    ts.transpileModule(
      readFileSync(resolve("src/lib/analytics/first-party.ts"), "utf8"),
      {
        compilerOptions: {
          module: ts.ModuleKind.CommonJS,
          target: ts.ScriptTarget.ES2022,
        },
      },
    ).outputText,
  );
  const { captureLandingAttribution, attachPendingAttribution } = createRequire(
    import.meta.url,
  )(join(directory, "first-party.cjs"));
  const storage = () => {
    const items = new Map();
    return {
      getItem: (key) => items.get(key) ?? null,
      setItem: (key, value) => items.set(key, value),
      removeItem: (key) => items.delete(key),
    };
  };
  globalThis.sessionStorage = storage();
  globalThis.localStorage = storage();
  localStorage.setItem(p.CONSENT_KEY, '{"granted":true,"version":"v1"}');
  const captures = [];
  const receipts = new Set();
  let attachStatus = 401;
  globalThis.fetch = async (url, { body }) => {
    const input = JSON.parse(body);
    if (url.endsWith("/capture")) {
      const receipt = String(captures.length + 1).repeat(43);
      receipts.add(receipt);
      assert.equal(
        input.source_counter_id,
        input.client_id === null ? undefined : "123",
      );
      captures.push(input.client_id);
      return Response.json({ receipt }, { status: 201 });
    }
    if (url.endsWith("/attach"))
      return new Response(null, {
        status:
          attachStatus === 204 && !receipts.delete(input.receipt)
            ? 404
            : attachStatus,
      });
    assert.ok(url.endsWith("/discard"));
    receipts.delete(input.receipt);
    return new Response(null, { status: 204 });
  };
  await captureLandingAttribution(null, "v1", () => true);
  const expired = JSON.parse(sessionStorage.getItem(p.ATTRIBUTION_KEY)).receipt;
  receipts.delete(expired);
  attachStatus = 204;
  await attachPendingAttribution();
  assert.equal(sessionStorage.getItem(p.ATTRIBUTION_KEY), null);
  await captureLandingAttribution(null, "v1", () => true);
  assert.deepEqual(
    captures,
    [null, null],
    "expired receipt cannot permanently latch capture",
  );
  attachStatus = 401;
  await captureLandingAttribution(null, "v1", () => true);
  const superseded = JSON.parse(
    sessionStorage.getItem(p.ATTRIBUTION_KEY),
  ).receipt;
  await captureLandingAttribution("98765", "v1", () => true);
  assert.equal(
    captures.at(-1),
    null,
    "known observation must name its source counter",
  );
  await captureLandingAttribution("12345", "v1", () => true, "123");
  assert.equal(
    captures.at(-1),
    "12345",
    "a pending null must not suppress a known observation",
  );
  assert.equal(
    receipts.has(superseded),
    false,
    "superseded null receipt is discarded",
  );
  assert.doesNotMatch(sessionStorage.getItem(p.ATTRIBUTION_KEY), /12345/);
  assert.doesNotMatch(
    readFileSync(
      resolve("src/components/analytics/public-analytics.tsx"),
      "utf8",
    ),
    /mc\.yandex|createElement\(["']script|window as SdkWindow/,
    "the app-origin landing must not have a vendor loader, even with all flags set",
  );
  console.log("Analytics privacy primitive + lifecycle contracts passed");
} finally {
  rmSync(directory, { recursive: true, force: true });
}
