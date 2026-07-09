import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const pagePath = resolve("src/app/(dashboard)/report/[profileId]/page.tsx");
const page = readFileSync(pagePath, "utf8");
const reportApi = readFileSync(resolve("src/lib/api/report.ts"), "utf8");
const progressComponent = readFileSync(
  resolve("src/components/report/report-generation-progress.tsx"),
  "utf8",
);
const narrativePagePath = resolve(
  "src/components/report/report-narrative-page.tsx",
);
const narrativeSectionPath = resolve(
  "src/components/report/narrative-section.tsx",
);
const houseScenariosPath = resolve(
  "src/components/report/house-scenarios-section.tsx",
);
const careerCtaPath = resolve("src/components/report/career-cta.tsx");
const calculationParametersPath = resolve(
  "src/components/report/calculation-parameters.tsx",
);
const evidenceNotesPath = resolve("src/components/report/evidence-notes.tsx");
const narrativePage = existsSync(narrativePagePath)
  ? readFileSync(narrativePagePath, "utf8")
  : "";
const narrativeSection = existsSync(narrativeSectionPath)
  ? readFileSync(narrativeSectionPath, "utf8")
  : "";
const houseScenarios = existsSync(houseScenariosPath)
  ? readFileSync(houseScenariosPath, "utf8")
  : "";
const careerCta = existsSync(careerCtaPath)
  ? readFileSync(careerCtaPath, "utf8")
  : "";
const calculationParameters = existsSync(calculationParametersPath)
  ? readFileSync(calculationParametersPath, "utf8")
  : "";
const evidenceNotes = existsSync(evidenceNotesPath)
  ? readFileSync(evidenceNotesPath, "utf8")
  : "";
const dashboardPage = readFileSync(
  resolve("src/app/(dashboard)/dashboard/page.tsx"),
  "utf8",
);
const selfProductPage = readFileSync(
  resolve("src/app/(dashboard)/products/self/page.tsx"),
  "utf8",
);
const careerProductPage = readFileSync(
  resolve("src/app/(dashboard)/products/career/page.tsx"),
  "utf8",
);
const registerPage = readFileSync(
  resolve("src/app/(auth)/register/page.tsx"),
  "utf8",
);
const sidebar = readFileSync(
  resolve("src/components/layout/sidebar.tsx"),
  "utf8",
);

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
  "src/components/report/report-generation-progress.tsx",
  "src/components/report/deterministic-report-fallback.tsx",
  "src/components/report/report-narrative-page.tsx",
  "src/components/report/report-pdf-actions.tsx",
  "src/components/report/calculation-parameters.tsx",
  "src/components/report/narrative-section.tsx",
  "src/components/report/career-cta.tsx",
  "src/components/report/house-scenarios-section.tsx",
  "src/components/report/calibration-questions-section.tsx",
  "src/components/report/pattern-tensions-section.tsx",
  "src/components/report/evidence-notes.tsx",
  "src/lib/glossary/report-glossary.ts",
  "src/lib/report/score-labels.ts",
  "src/lib/report/view-model.ts",
  "src/lib/astrology/labels.ts",
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
const reportNarrativeSource = `${narrativePage}\n${narrativeSection}\n${houseScenarios}\n${careerCta}\n${calculationParameters}\n${evidenceNotes}`;
const allUiSource = `${page}\n${componentSources}`;
const adapter = readFileSync(resolve("src/lib/report/view-model.ts"), "utf8");

for (const marker of [
  "snapshot.socionics ?? snapshot.chart_data.socionics",
  "generatedReport?.report_data.socionics",
  "generatedReport?.report_data.function_strengths",
]) {
  if (!adapter.includes(marker)) {
    throw new Error(`Missing socionics report-data fallback marker: ${marker}`);
  }
}

if (!page.includes("<ReportNarrativePage")) {
  throw new Error("Ready Self report must render through ReportNarrativePage");
}

for (const marker of [
  'product === "self" &&',
  "!loadedApiData.generatedReport",
  "const autoGenerateStorageKey = `self-report-autogen:${autoGenerateKey}`",
  "window.sessionStorage.getItem(autoGenerateStorageKey)",
  "Date.now() - autoGenerateRequestedAt < 2 * 60 * 1000",
  "window.sessionStorage.setItem(",
  "String(Date.now())",
  "window.sessionStorage.removeItem(autoGenerateStorageKey)",
  "clearSelfReportAutoGenerateThrottle(",
  "autoGenerateAttemptedRef.current.add(autoGenerateKey)",
  "generateReportForProfile(",
  'product !== "self" && !loadedApiData.generatedReport',
]) {
  if (!page.includes(marker)) {
    throw new Error(`Missing self-report auto-generation marker: ${marker}`);
  }
}

const narrativeOrder = [
  "<NarrativeHero",
  "<HouseScenariosSection",
  "<PatternTensionsSection",
  "main_formula",
  "world_perception",
  "emotions_and_communication",
  "strengths",
  "vulnerabilities",
  "relationships",
  "sexuality",
  "development",
  "<CareerCTA",
  "<FinalSummary",
  "<ReportPdfActions",
  "<CalculationParameters",
  "<TechnicalDetailsAccordion",
];
let previousNarrativeIndex = -1;
for (const marker of narrativeOrder) {
  const index = reportNarrativeSource.indexOf(marker);
  if (index === -1) {
    throw new Error(`Missing narrative-first marker: ${marker}`);
  }
  if (index <= previousNarrativeIndex) {
    throw new Error(`Narrative marker is out of order: ${marker}`);
  }
  previousNarrativeIndex = index;
}

for (const marker of [
  "stage_summary",
  "StagedPipelineSummary",
  "Этот текст собран поэтапно",
  "completed_stage_labels",
  "completed_stages",
  "total_stages",
  "narrative_progress",
  "narrative_stage_artifacts",
  "current_stage",
  "stageProgress?.current_stage",
  "currentReport?.narrative_progress",
  "currentReport?.narrative_stage_artifacts",
]) {
  if (
    !adapter.includes(marker) &&
    !reportNarrativeSource.includes(marker) &&
    !allUiSource.includes(marker) &&
    !reportApi.includes(marker)
  ) {
    throw new Error(`Missing staged narrative marker: ${marker}`);
  }
}

for (const marker of [
  "allowedSelfSectionIds",
  "unknownSectionIds",
  "console.warn",
  "narrative.hero",
  "narrative.sections",
  "narrative.final_summary",
  "house_scenarios",
  "calibration_questions",
  "contradictions",
  "failure_modes",
  "maturity_levels",
]) {
  if (!adapter.includes(marker) && !reportNarrativeSource.includes(marker)) {
    throw new Error(`Missing narrative normalizer/rendering marker: ${marker}`);
  }
}

if (
  !evidenceNotes.includes("<details") ||
  !evidenceNotes.includes("<summary")
) {
  throw new Error("Evidence notes must render as a collapsed disclosure");
}

for (const marker of [
  "renderNarrativeParagraphs",
  "body_paragraphs",
  "final_summary_paragraphs",
]) {
  if (!reportNarrativeSource.includes(marker) && !adapter.includes(marker)) {
    throw new Error(`Missing paragraph-preserving narrative marker: ${marker}`);
  }
}

for (const flattenedBodyMarker of [
  "<p>{hero.body}</p>",
  "<p>{section.body}</p>",
]) {
  if (narrativeSection.includes(flattenedBodyMarker)) {
    throw new Error(
      `Narrative body must not be flattened into one paragraph: ${flattenedBodyMarker}`,
    );
  }
}

const heroIndex = reportNarrativeSource.indexOf("<NarrativeHero");
const pdfActionIndex = reportNarrativeSource.indexOf("<ReportPdfActions");
const firstEvidenceIndex = reportNarrativeSource.indexOf("<EvidenceNotes");
if (pdfActionIndex !== -1 && pdfActionIndex < heroIndex) {
  throw new Error(
    "Self PDF action must stay below the first meaningful narrative flow",
  );
}
if (firstEvidenceIndex !== -1 && firstEvidenceIndex < heroIndex) {
  throw new Error(
    "Evidence notes must not interrupt the recognition-first hero flow",
  );
}

for (const requiredEvidenceTrace of [
  "interpretation",
  "limitation",
  "limitation_fact_ids",
  "Ограничение",
]) {
  if (
    !evidenceNotes.includes(requiredEvidenceTrace) &&
    !adapter.includes(requiredEvidenceTrace)
  ) {
    throw new Error(
      `Missing evidence trace UI/adapter marker: ${requiredEvidenceTrace}`,
    );
  }
}

if (!reportNarrativeSource.includes("grid-cols-1")) {
  throw new Error(
    "Narrative report must keep a mobile-first single-column layout",
  );
}

for (const forbiddenEvidenceMarker of ["debug", "Raw", "JSON.stringify"]) {
  if (evidenceNotes.includes(forbiddenEvidenceMarker)) {
    throw new Error(
      `Evidence notes must not look like debug output: ${forbiddenEvidenceMarker}`,
    );
  }
}

for (const forbiddenSectionId of [
  "career",
  "technical",
  "model_a",
  "raw_scores",
]) {
  if (reportNarrativeSource.includes(`id === "${forbiddenSectionId}"`)) {
    throw new Error(
      `Self narrative must not explicitly render ${forbiddenSectionId}`,
    );
  }
}

for (const requiredExport of [
  "export interface ReportNarrativeViewModel",
  "export interface NarrativeEvidenceNote",
  "export const allowedSelfSectionIds",
]) {
  if (!adapter.includes(requiredExport)) {
    throw new Error(`Missing narrative adapter export: ${requiredExport}`);
  }
}

for (const requiredNarrativeText of [
  "Карьерный отчёт",
  "Почему так видно",
  "Финальное резюме",
  "Жизненные сценарии домов",
  "Тень / риск",
  "Зрелая форма",
  "Калибровочные вопросы",
  "Главные внутренние противоречия",
  "Где система даёт сбой",
  "Уровни зрелости паттерна",
  "Сохранить этот разбор",
]) {
  if (!allUiSource.includes(requiredNarrativeText)) {
    throw new Error(`Missing narrative UI text: ${requiredNarrativeText}`);
  }
}

if (!page.includes('data.product === "career"')) {
  throw new Error("Top PDF action must remain a Career-only header action");
}

for (const marker of ["<ReportPdfActions", "Сохранить PDF"]) {
  if (!allUiSource.includes(marker)) {
    throw new Error(`Missing PDF action marker: ${marker}`);
  }
}

for (const heading of [
  "Главное о вас",
  "Астрологическая основа",
  "Как это проявляется",
  "Практические рекомендации",
  "Архетипический профиль",
  "Соционический профиль",
  "Технические детали расчёта",
  "Расчётные параметры",
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
  "Уверенность",
  "Цепочка доказательств",
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
  "числовые показатели",
  "Цепочка доказательств",
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

const astrologyLabels = readFileSync(
  resolve("src/lib/astrology/labels.ts"),
  "utf8",
);
for (const requiredExport of [
  "export function planetNameRu",
  "export function signNameRu",
  "export function aspectTypeRu",
  "export function formatPlanetPlacementRu",
  "export function formatAspectRu",
]) {
  if (!astrologyLabels.includes(requiredExport)) {
    throw new Error(`Missing astrology i18n helper export: ${requiredExport}`);
  }
}
for (const russianLabel of [
  "Солнце",
  "Луна",
  "Меркурий",
  "Венера",
  "Марс",
  "Юпитер",
  "Сатурн",
  "Уран",
  "Нептун",
  "Плутон",
  "Дева",
  "соединение",
  "квадрат",
]) {
  if (!astrologyLabels.includes(russianLabel)) {
    throw new Error(`Missing Russian astrology label: ${russianLabel}`);
  }
}

if (/\$\{(?:sun|moon)\.sign\}/.test(adapter)) {
  throw new Error("Report prose must not interpolate raw English zodiac signs");
}
if (/\$\{aspect\.(?:planet_a|planet_b|aspect_type)\}/.test(adapter)) {
  throw new Error(
    "Report aspects must not interpolate raw English planet/aspect names",
  );
}
for (const forbiddenRawRender of [
  "{aspect.planet_a}",
  "{aspect.aspect_type}",
  "{aspect.planet_b}",
  "orb: {",
  '"App"',
  '"Sep"',
]) {
  if (
    readFileSync(
      resolve("src/components/chart/natal-chart.tsx"),
      "utf8",
    ).includes(forbiddenRawRender)
  ) {
    throw new Error(
      `Natal chart renders raw English marker: ${forbiddenRawRender}`,
    );
  }
}

if (allUiSource.includes("placeholder")) {
  throw new Error("Report page must not render placeholder report data");
}

for (const requiredStatus of [
  "deterministic_ready",
  "generating_narrative",
  "ready",
  "narrative_failed",
]) {
  if (!reportApi.includes(requiredStatus) || !page.includes(requiredStatus)) {
    throw new Error(
      `Report frontend must handle narrative status: ${requiredStatus}`,
    );
  }
}

for (const requiredApiExport of [
  "export async function fetchReportById",
  "export async function regenerateReportNarrative",
  "/api/v1/reports/${reportId}/narrative/regenerate",
]) {
  if (!reportApi.includes(requiredApiExport)) {
    throw new Error(
      `Missing narrative report API helper: ${requiredApiExport}`,
    );
  }
}

for (const requiredPollingMarker of [
  "ReportGenerationProgress",
  "NarrativeUnavailableState",
  "NARRATIVE_TIMEOUT_MS",
  "POLL_INTERVAL_MS",
  "setTimeout",
  "setInterval",
  "fetchReportById",
  "regenerateReportNarrative",
]) {
  if (!page.includes(requiredPollingMarker)) {
    throw new Error(
      `Missing report polling/fallback marker: ${requiredPollingMarker}`,
    );
  }
}

for (const forbiddenFallbackMarker of [
  "DeterministicReportFallback",
  "setShowFallback",
  "showFallback",
  "Показать технический отчёт",
]) {
  if (
    page.includes(forbiddenFallbackMarker) ||
    progressComponent.includes(forbiddenFallbackMarker)
  ) {
    throw new Error(
      `Legacy technical-fallback marker must be removed: ${forbiddenFallbackMarker}`,
    );
  }
}

for (const requiredProgressText of [
  "Собираем ваш текстовый отчёт",
  "Текстовый отчёт ещё собирается",
  "Повторить генерацию",
]) {
  if (!progressComponent.includes(requiredProgressText)) {
    throw new Error(
      `Missing narrative progress UI text: ${requiredProgressText}`,
    );
  }
}

if (!page.includes("Полный отчёт пока недоступен")) {
  throw new Error("Missing full-report-unavailable state heading");
}

if (!page.includes("Повторить генерацию")) {
  throw new Error("Missing retry action for unavailable full report");
}

for (const requiredCalculationText of [
  "Дата и время рождения",
  "Часовой пояс",
  "UTC-время расчёта",
  "Система домов",
  "Зодиак",
]) {
  if (!calculationParameters.includes(requiredCalculationText)) {
    throw new Error(
      `Missing calculation parameters UI text: ${requiredCalculationText}`,
    );
  }
}

for (const requiredCalculationValue of ["Placidus", "тропический"]) {
  if (!adapter.includes(requiredCalculationValue)) {
    throw new Error(
      `Missing calculation parameters adapter value: ${requiredCalculationValue}`,
    );
  }
}

if (!adapter.includes("utcCalculationTime")) {
  throw new Error("Report adapter must expose UTC calculation time");
}

if (/generating_narrative[\s\S]{0,160}<ReportContent/.test(page)) {
  throw new Error(
    "generating_narrative must show progress UI before deterministic report content",
  );
}

for (const [name, source] of [
  ["dashboard", dashboardPage],
  ["self product", selfProductPage],
  ["career product", careerProductPage],
]) {
  if (source.includes("if (!token) return")) {
    throw new Error(
      `${name} page must fetch through HttpOnly cookie auth when JS token is absent after OAuth`,
    );
  }
}

if (/id: "career"[\s\S]*?status: "coming_soon"/.test(dashboardPage)) {
  throw new Error(
    "Career product must be available on dashboard, not coming_soon",
  );
}

if (/title: "Career"[\s\S]*?disabled: true/.test(sidebar)) {
  throw new Error("Career sidebar navigation must be enabled");
}

if (!registerPage.includes("name: name.trim()")) {
  throw new Error(
    "OAuth complete-profile registration must submit the required display name",
  );
}

if (!registerPage.includes("renderOAuthNameField")) {
  throw new Error(
    "OAuth step 2 must render a required display-name field before birth data",
  );
}

console.log("Report UX structure check passed");
