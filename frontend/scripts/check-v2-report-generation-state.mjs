#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const hookPath = "src/lib/astrotype-v2/use-v2-report-generation.ts";
const pagePath = "src/app/(dashboard)/report/v2/[profileId]/page.tsx";
const hook = readFileSync(join(root, hookPath), "utf8");
const page = readFileSync(join(root, pagePath), "utf8");

for (const state of [
  "idle",
  "loading",
  "queued",
  "polling",
  "ready",
  "failed",
  "regenerating",
]) {
  assert.match(hook, new RegExp(`\\b${state}\\b`), `missing state: ${state}`);
}

assert.match(hook, /MAX_POLL_ATTEMPTS/);
assert.match(hook, /clearPollTimer/);
assert.match(hook, /generateAstrotypeV2Report/);
assert.match(hook, /fetchAstrotypeV2Report/);
assert.match(hook, /regenerate/);
assert.match(hook, /retry/);

assert.match(page, /useV2ReportGeneration/);
assert.equal(
  page.includes("window.setTimeout"),
  false,
  "page must not own polling timer",
);
assert.equal(
  page.includes("pollTimerRef"),
  false,
  "page must not own poll ref",
);
assert.equal(
  page.includes("generateAstrotypeV2Report"),
  false,
  "page must not call generation API directly",
);

console.log("V2 generation state machine markers OK");

const apiSource = readFileSync(
  join(root, "src/lib/api/astrotype-v2.ts"),
  "utf8",
);
const pageSource = readFileSync(join(root, pagePath), "utf8");
for (const marker of [
  "downloadAstrotypeV2ReportPdf",
  "/api/v1/astrotype-v2/reports/${reportId}/pdf",
  "application/pdf",
  "blob.size === 0",
  "createObjectURL",
  "setTimeout",
  "revokeObjectURL",
  "astrotype-v2-report-${reportId}.pdf",
]) {
  assert.equal(
    apiSource.includes(marker),
    true,
    `missing PDF download marker: ${marker}`,
  );
}
assert.match(pageSource, /downloadAstrotypeV2ReportPdf\(report\.report\.id\)/);
assert.match(pageSource, /isDownloadingPdf/);
