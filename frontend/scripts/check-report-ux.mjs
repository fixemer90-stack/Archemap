import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const pagePath = resolve("src/app/(dashboard)/report/[profileId]/page.tsx");
const page = readFileSync(pagePath, "utf8");

const requiredFiles = [
  "src/components/report/report-header.tsx",
  "src/components/report/report-executive-summary.tsx",
  "src/components/report/astrology-overview.tsx",
  "src/components/report/life-manifestations.tsx",
  "src/components/report/practical-recommendations.tsx",
  "src/components/report/archetype-profile-summary.tsx",
  "src/components/report/socionics-profile-simple.tsx",
  "src/components/report/technical-details-accordion.tsx",
  "src/components/glossary/term-help.tsx",
  "src/components/glossary/glossary-modal.tsx",
  "src/lib/glossary/report-glossary.ts",
  "src/lib/report/score-labels.ts",
  "src/lib/report/view-model.ts",
];

for (const file of requiredFiles) {
  if (!existsSync(resolve(file))) {
    throw new Error(`Missing report UX file: ${file}`);
  }
}

const orderedComponents = [
  "<ReportExecutiveSummary",
  "<AstrologyOverview",
  "<LifeManifestations",
  "<PracticalRecommendations",
  "<ArchetypeProfileSummary",
  "<SocionicsProfileSimple",
  "<TechnicalDetailsAccordion",
];

let previousIndex = -1;
for (const component of orderedComponents) {
  const index = page.indexOf(component);
  if (index === -1) {
    throw new Error(`Missing report section component: ${component}`);
  }
  if (index <= previousIndex) {
    throw new Error(`Report section component is out of order: ${component}`);
  }
  previousIndex = index;
}

const componentSources = requiredFiles
  .filter((file) => file.endsWith(".tsx"))
  .map((file) => readFileSync(resolve(file), "utf8"))
  .join("\n");
const allUiSource = `${page}\n${componentSources}`;

for (const heading of [
  "Главное о вас",
  "Астрологическая основа",
  "Как это проявляется",
  "Практические рекомендации",
  "Архетипический профиль",
  "Соционический профиль",
  "Технические детали расчёта",
]) {
  if (!allUiSource.includes(heading)) {
    throw new Error(`Missing report section heading: ${heading}`);
  }
}

for (const term of [
  "Натальная карта",
  "Солнце",
  "Луна",
  "Асцендент",
  "Дом",
  "Аспект",
  "Орб",
  "Стихия",
  "Модальность",
  "Архетип",
  "Соционический тип",
  "Model A",
  "Confidence",
  "Evidence trail",
]) {
  if (!allUiSource.includes(`term="${term}"`)) {
    throw new Error(`Missing glossary help for term: ${term}`);
  }
}

const glossary = readFileSync(
  resolve("src/lib/glossary/report-glossary.ts"),
  "utf8",
);
for (const requiredField of ["definition", "reportMeaning", "example"]) {
  if (!glossary.includes(requiredField)) {
    throw new Error(`Glossary entries must include ${requiredField}`);
  }
}

if (!allUiSource.includes("<details") || !allUiSource.includes("<summary")) {
  throw new Error(
    "Technical details must be hidden behind a native disclosure control",
  );
}

const detailsIndex = allUiSource.indexOf("Технические детали расчёта");
for (const marker of [
  "<NatalChart",
  "<SocionicsResult",
  "Model A",
  "raw scores",
  "Evidence trail",
]) {
  const index = allUiSource.indexOf(marker);
  if (index === -1) {
    throw new Error(`Missing advanced marker: ${marker}`);
  }
  if (marker.startsWith("<") && index < detailsIndex) {
    throw new Error(
      `${marker} must only appear inside the advanced technical details section`,
    );
  }
}

for (const forbidden of [
  "grid grid-cols-1 lg:grid-cols-2 gap-6",
  "placeholderData",
  "ReportContent data={placeholderData}",
]) {
  if (page.includes(forbidden)) {
    throw new Error(
      `Forbidden old report layout/runtime marker found: ${forbidden}`,
    );
  }
}

if (
  !page.includes("toReportViewModel") ||
  !page.includes("@/lib/report/view-model")
) {
  throw new Error("Report page must use the typed report view-model adapter");
}

const adapter = readFileSync(resolve("src/lib/report/view-model.ts"), "utf8");
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

const scoreLabels = readFileSync(
  resolve("src/lib/report/score-labels.ts"),
  "utf8",
);
for (const label of [
  "высокая уверенность",
  "средняя уверенность",
  "низкая уверенность",
]) {
  if (!scoreLabels.includes(label)) {
    throw new Error(`Missing score confidence label: ${label}`);
  }
}

console.log("Report UX structure check passed");
