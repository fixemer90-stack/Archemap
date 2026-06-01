import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const pagePath = resolve("src/app/(dashboard)/report/[profileId]/page.tsx");
const page = readFileSync(pagePath, "utf8");

const orderedHeadings = [
  "Главное о вас",
  "Астрологическая основа",
  "Как это проявляется",
  "Практические рекомендации",
  "Архетипический профиль",
  "Соционический профиль",
  "Технические детали расчёта",
];

let previousIndex = -1;
for (const heading of orderedHeadings) {
  const index = page.indexOf(heading);
  if (index === -1) {
    throw new Error(`Missing report section heading: ${heading}`);
  }
  if (index <= previousIndex) {
    throw new Error(`Report section is out of order: ${heading}`);
  }
  previousIndex = index;
}

for (const term of [
  "Натальная карта",
  "Аспект",
  "Орб",
  "Model A",
  "Confidence",
]) {
  if (!page.includes(`term="${term}"`)) {
    throw new Error(`Missing glossary help for term: ${term}`);
  }
}

if (!page.includes("<details") || !page.includes("<summary")) {
  throw new Error(
    "Technical details must be hidden behind a native disclosure control",
  );
}

const detailsIndex = page.indexOf("Технические детали расчёта");
const natalChartIndex = page.indexOf("<NatalChart");
const socionicsResultIndex = page.indexOf("<SocionicsResult");
if (natalChartIndex === -1 || natalChartIndex < detailsIndex) {
  throw new Error(
    "NatalChart must only appear inside the advanced technical details section",
  );
}
if (socionicsResultIndex === -1 || socionicsResultIndex < detailsIndex) {
  throw new Error(
    "SocionicsResult must only appear inside the advanced technical details section",
  );
}

if (page.includes("grid grid-cols-1 lg:grid-cols-2 gap-6")) {
  throw new Error("Old two-column chart-vs-socionics layout must be removed");
}

if (
  page.includes("placeholderData") ||
  page.includes("ReportContent data={placeholderData}")
) {
  throw new Error("Report page must not use runtime placeholder data");
}

if (
  !page.includes("toReportViewModel") ||
  !page.includes("@/lib/report/view-model")
) {
  throw new Error("Report page must use the typed report view-model adapter");
}

const adapterPath = resolve("src/lib/report/view-model.ts");
const adapter = readFileSync(adapterPath, "utf8");
for (const requiredExport of [
  "export interface ReportViewModel",
  "export interface ReportApiData",
  "export function toReportViewModel",
  "emptyFunctionStrengths",
]) {
  if (!adapter.includes(requiredExport)) {
    throw new Error(`Missing report adapter export: ${requiredExport}`);
  }
}

console.log("Report UX structure check passed");
