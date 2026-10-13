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
const calculationMatrix = read(
  "src/components/astrotype-v2/report/V2CalculationMatrix.tsx",
);
const globals = read("src/app/globals.css");
const format = read("src/components/astrotype-v2/report/format.ts");
const balance = read("src/components/astrotype-v2/report/V2BalanceBars.tsx");
const houseEmphasis = read(
  "src/components/astrotype-v2/report/V2HouseEmphasis.tsx",
);
const aspectTable = read(
  "src/components/astrotype-v2/report/V2KeyAspectsTable.tsx",
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
  calculationMatrix,
  read("src/components/astrotype-v2/report/V2GlossaryText.tsx"),
  read("src/components/glossary/term-help.tsx"),
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
assert.match(hero, /Astrotype Signature|hero\.eyebrow/);
assert.match(hero, /Натальный портрет/);
assert.equal(hero.includes("Премиальный натальный портрет"), false);
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
assert.equal(reader.includes("V2GlossaryHelpStrip"), false);
assert.equal(reader.includes("Словарь терминов"), false);
assert.match(section, /data-v2-reader-block="narrative-section"/);
assert.match(section, /data-v2-paragraph-count=\{section\.paragraphCount\}/);
assert.match(section, /key=\{`\$\{section\.id\}-\$\{index\}`\}/);
assert.match(calculation, /data-v2-reader-block="calculation_layer"/);
assert(
  calculationMatrix.indexOf('term="Тип домов"') <
    calculationMatrix.indexOf('term="Квадрант"'),
);
assert(
  calculationMatrix.indexOf('term="Квадрант"') <
    calculationMatrix.indexOf('term="Ориентация карты"'),
);
assert(
  calculationMatrix.indexOf('term="Ориентация карты"') <
    calculationMatrix.indexOf('term="Профиль аспектов"'),
);

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
  "Типы домов показывают",
  "То, что сразу заметно",
  "То, что закрепляет результат",
  "То, что осмысляет и перестраивает опыт",
  "Это не оценка характера",
  "Акцент на внешней реализации",
  "Больше инициативы от себя",
  "Больше отклика на других",
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
  "data-aspect-legend",
  "data-aspect-edge",
  "tabIndex={0}",
  "<title>",
]) {
  assert.match(
    aspectNetwork,
    new RegExp(marker),
    `missing aspect SVG marker: ${marker}`,
  );
}

for (const token of [
  "--chart-fill-track",
  "--chart-fill-bar-start",
  "--chart-fill-bar-end",
  "--chart-fill-node",
  "--chart-fill-resource",
  "--chart-fill-tension",
]) {
  assert.match(globals, new RegExp(token), `missing chart token: ${token}`);
}

assert.match(format, /export function normalizePercent/);
assert.match(format, /export function formatPercent/);
assert.match(balance, /formatPercent\(row\.value\)/);
assert.match(balance, /backgroundImage.*chart-fill-bar-start/s);
assert.equal(balance.includes("formatValue(row.value)"), false);
assert.equal(houseEmphasis.includes("min-h-[28px]"), false);
assert.equal(houseEmphasis.includes("min-h-[600px]"), false);
assert.match(houseEmphasis, /data-house-fill/);
assert.match(houseEmphasis, /data-house-label/);
assert.equal(aspectNetwork.includes("network.nodes.slice"), false);
assert.equal(aspectNetwork.includes("min-h-[600px]"), false);
assert.equal(aspectNetwork.includes("min-h-[500px]"), false);
assert.match(aspectTable, /<details/);
assert.match(aspectTable, /<summary/);
assert.match(aspectTable, /remainingAspects/);
assert.match(calculation, /selectedAspects=\{layer\.selectedAspects\}/);
assert.match(calculation, /remainingAspects=\{layer\.remainingAspects\}/);
assert.equal(calculation.includes("items-stretch"), false);
assert.equal(calculation.includes('className="flex'), false);
assert.equal(calculationMatrix.includes("orb{"), false);

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
