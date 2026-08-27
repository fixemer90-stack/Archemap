#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const read = (path) => readFileSync(join(root, path), "utf8");

const reader = read("src/components/astrotype-v2/report/V2ReportReader.tsx");
const hero = read("src/components/astrotype-v2/report/V2ReportHero.tsx");
const viewModel = read("src/lib/astrotype-v2/report-view-model.ts");
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
  read("src/components/astrotype-v2/report/V2GlossaryText.tsx"),
  read("src/components/glossary/term-help.tsx"),
].join("\n");

assert.match(reader, /data-v2-reader="canonical"/);
assert(
  reader.indexOf('data-v2-reader-block="hero"') <
    reader.indexOf("<V2GlossaryHelpStrip"),
);
assert(
  reader.indexOf("<V2GlossaryHelpStrip") <
    reader.indexOf('data-v2-reader-block="narrative"'),
);
assert(
  reader.indexOf('data-v2-reader-block="narrative"') <
    reader.indexOf("<V2CalculationLayer"),
);
assert.match(hero, /Astrotype Signature|hero\.eyebrow/);
assert.match(hero, /Премиальный натальный портрет/);
assert.equal(viewModel.includes("Astrotype v2 · натальный отчёт"), false);
assert.match(viewModel, /Здравствуйте/);
assert.match(hero, /ваша натальная карта/i);
assert.match(viewModel, /Ваша натальная карта готова/);
assert.match(hero, /Ваши данные рождения/);
assert.match(hero, /hero\.birthDataItems/);

assert.match(hero, /onClick=\{onDownloadPdf\}/);
assert.match(hero, /disabled=\{isDownloadingPdf\}/);
assert.match(hero, /Готовим PDF/);
assert.match(reader, /onDownloadPdf=\{onDownloadPdf\}/);
assert.match(reader, /pdfError/);
assert.equal(hero.includes("Перегенерировать"), false);
assert.equal(hero.includes("onRegenerate"), false);
assert.equal(reader.includes("onRegenerate"), false);
assert.equal(hero.includes("Это не dashboard"), false);
assert.equal(hero.includes("технических карточек"), false);
assert.equal(hero.includes("progressLabel"), false);
assert.match(section, /data-v2-reader-block="narrative-section"/);
assert.match(section, /data-v2-paragraph-count=\{section\.paragraphCount\}/);
assert.match(section, /key=\{`\$\{section\.id\}-\$\{index\}`\}/);
assert.match(calculation, /data-v2-reader-block="calculation_layer"/);

for (const marker of [
  "Карта и ключевые показатели",
  "Положения планет",
  "Баланс стихий",
  "Баланс модальностей",
  "Запускает движение",
  "Удерживает форму",
  "Адаптирует процесс",
  "Акцент домов",
  "Сеть ключевых аспектов",
  "Ключевые аспекты",
  "Расчётные акценты карты",
  "Словарь терминов",
  "data-glossary-term",
  'role="tooltip"',
]) {
  assert.match(
    componentSources,
    new RegExp(marker),
    `missing canonical marker: ${marker}`,
  );
}

assert.match(
  componentSources,
  /\(\?<!\[\\\\p\{L\}\\\\p\{N\}_\]\)/,
  "glossary terms must not match inside words like рядом/поводом",
);
assert.match(
  componentSources,
  /\(\?!\[\\\\p\{L\}\\\\p\{N\}_\]\)/,
  "glossary terms must not match inside words like рядом/поводом",
);

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

const aspectNetwork = read(
  "src/components/astrotype-v2/report/V2AspectNetwork.tsx",
);
for (const marker of [
  'viewBox="0 0 420 420"',
  "asp-tension",
  "asp-resource",
  "<line",
  "<g",
  "network.nodes.slice",
]) {
  assert.match(
    aspectNetwork,
    new RegExp(marker),
    `missing aspect SVG marker: ${marker}`,
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
