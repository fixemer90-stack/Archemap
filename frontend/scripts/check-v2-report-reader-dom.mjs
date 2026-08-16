#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const read = (path) => readFileSync(join(root, path), "utf8");

const reader = read("src/components/astrotype-v2/report/V2ReportReader.tsx");
const hero = read("src/components/astrotype-v2/report/V2ReportHero.tsx");
const section = read(
  "src/components/astrotype-v2/report/V2NarrativeSectionCard.tsx",
);
const calculation = read(
  "src/components/astrotype-v2/report/V2CalculationLayer.tsx",
);
const componentSources = [
  reader,
  hero,
  section,
  calculation,
  read("src/components/astrotype-v2/report/V2KeyIndicators.tsx"),
  read("src/components/astrotype-v2/report/V2PlanetPositionsTable.tsx"),
  read("src/components/astrotype-v2/report/V2BalanceBars.tsx"),
  read("src/components/astrotype-v2/report/V2HouseEmphasis.tsx"),
  read("src/components/astrotype-v2/report/V2AspectNetwork.tsx"),
  read("src/components/astrotype-v2/report/V2KeyAspectsTable.tsx"),
  read("src/components/astrotype-v2/report/V2CalculationMatrix.tsx"),
].join("\n");

assert.match(reader, /data-v2-reader="canonical"/);
assert(
  reader.indexOf('data-v2-reader-block="hero"') <
    reader.indexOf('data-v2-reader-block="narrative"'),
);
assert(
  reader.indexOf('data-v2-reader-block="narrative"') <
    reader.indexOf("<V2CalculationLayer"),
);
assert.match(hero, /Astrotype v2 · натальный отчёт|hero\.eyebrow/);
assert.match(section, /data-v2-reader-block="narrative-section"/);
assert.match(calculation, /data-v2-reader-block="calculation_layer"/);

for (const marker of [
  "Карта и ключевые показатели",
  "Положения планет",
  "Баланс стихий",
  "Баланс модальностей",
  "Акцент домов",
  "Сеть ключевых аспектов",
  "Ключевые аспекты",
  "Расчётные акценты карты",
]) {
  assert.match(
    componentSources,
    new RegExp(marker),
    `missing canonical marker: ${marker}`,
  );
}

for (const block of [
  "key_indicators",
  "planet_positions",
  "balance_bars",
  "house_emphasis",
  "aspect_network",
  "key_aspects",
  "calculation_matrix",
]) {
  assert.match(
    componentSources,
    new RegExp(`data-v2-calculation-block=\"${block}\"`),
  );
}

for (const forbidden of [
  "socionics",
  "Соционика",
  "Model A",
  "function_strengths",
  "MBTI",
  "TechnicalDetailsAccordion",
  "factual_basis_dashboard",
]) {
  assert.equal(
    componentSources.includes(forbidden),
    false,
    `forbidden v2 UI marker: ${forbidden}`,
  );
}

console.log("V2 report reader DOM markers OK");
