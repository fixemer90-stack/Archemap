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
assert.match(hook, /fetchAstrotypeV2GenerationStatus/);
assert.match(hook, /fetchAstrotypeV2Report/);
assert.match(hook, /regenerate/);
assert.match(hook, /retry/);
assert.match(hook, /generationId/);
assert.match(hook, /scheduleGenerationPoll/);
assert.match(hook, /pollGenerationStatus/);
assert.match(hook, /TERMINAL_GENERATION_STATUSES/);
assert.match(hook, /VISIBLE_REPORT_STATUSES/);
assert.match(hook, /deterministic_ready/);
assert.match(hook, /narrative_generating/);
assert.match(hook, /partial/);
assert.match(hook, /complete/);

assert.match(page, /useV2ReportGeneration/);
assert.match(page, /if \(generation\.report\)/);
assert.doesNotMatch(
  page,
  /generation\.state === "ready" && generation\.report/,
  "page must render deterministic-ready reports before final ready state",
);
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
  "AstrotypeV2GenerationStatusResponse",
  "fetchAstrotypeV2GenerationStatus",
  "/api/v1/astrotype-v2/reports/generations/${generationId}",
  "narrative_failed",
  "failed",
]) {
  assert.equal(
    apiSource.includes(marker),
    true,
    `missing generation status marker: ${marker}`,
  );
}
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
