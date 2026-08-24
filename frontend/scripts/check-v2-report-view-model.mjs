#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const source = readFileSync(
  join(root, "src/lib/astrotype-v2/report-view-model.ts"),
  "utf8",
);

for (const marker of [
  "export function buildV2ReportReaderViewModel",
  "CANONICAL_V2_SECTION_ORDER",
  "core_pattern",
  "perception_and_mind",
  "emotional_regulation",
  "agency_and_desire",
  "relationships_and_intimacy",
  "growth_vector",
  "layoutOrder",
  "toHeroViewModel",
  "toNarrativeSections",
  "bodyText",
  "paragraphCount",
  "toCalculationLayer",
  "keyIndicators",
  "planetPositions",
  "balanceBars",
  "houseEmphasis",
  "aspectNetwork",
  "keyAspects",
  "calculationMatrix",
  "sampledAspects",
  "houseMode",
  "hemispheres",
  "quadrants",
  "aspectProfile",
]) {
  assert.match(
    source,
    new RegExp(marker),
    `missing view-model marker: ${marker}`,
  );
}

const order = [
  "core_pattern",
  "perception_and_mind",
  "emotional_regulation",
  "agency_and_desire",
  "relationships_and_intimacy",
  "growth_vector",
];
for (let index = 1; index < order.length; index += 1) {
  assert(
    source.indexOf(`"${order[index - 1]}"`) <
      source.indexOf(`"${order[index]}"`),
    `canonical section order broken around ${order[index]}`,
  );
}

assert.match(source, /const bodyText = stringValue\(section\.body\)/);
assert.match(source, /paragraphCount: sectionParagraphs\.length/);
assert.equal(
  source.includes("slice(0"),
  false,
  "view model must not truncate narrative body text",
);

for (const forbidden of [
  "socionics",
  "model a",
  "function_strengths",
  "mbti",
]) {
  assert.equal(
    source.toLowerCase().includes(forbidden),
    false,
    `forbidden marker leaked: ${forbidden}`,
  );
}

console.log("V2 report view-model contract OK");
