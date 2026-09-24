import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const pagePath = path.join(
  root,
  "src/app/(dashboard)/products/career/page.tsx",
);
const apiPath = path.join(root, "src/lib/api/career.ts");
const careerCtaPath = path.join(root, "src/components/report/career-cta.tsx");
const page = fs.readFileSync(pagePath, "utf8");
const api = fs.readFileSync(apiPath, "utf8");
const careerCta = fs.readFileSync(careerCtaPath, "utf8");

function expect(condition, message) {
  if (!condition) throw new Error(message);
}

expect(
  !page.includes("/api/v1/reports/generate"),
  "Career page must not call legacy synchronous generation",
);
expect(
  api.includes("/api/v1/career/questionnaires/current"),
  "Career client must load persisted questionnaire draft",
);
expect(
  api.includes("/answers"),
  "Career client must autosave questionnaire answers",
);
expect(
  api.includes("/complete"),
  "Career client must complete the questionnaire explicitly",
);
expect(
  api.includes("/api/v1/career/reports"),
  "Career client must create an async report job",
);
expect(
  api.includes("/api/v1/career/generations/"),
  "Career client must poll by generation id",
);
expect(
  page.includes("missingRequired"),
  "Career UI must expose required-answer validation",
);
expect(
  page.includes("aria-live"),
  "Career progress and errors must be announced accessibly",
);
expect(
  page.includes("Ответы уточняют"),
  "Career UI must explain that answers refine application, not the natal chart",
);
expect(
  page.includes("не назначает профессию"),
  "Career UI must avoid profession promises",
);
expect(
  page.includes("deterministic_status"),
  "Career UI must support deterministic-first progress",
);
expect(
  page.includes("Назад") && page.includes("Далее"),
  "Questionnaire must support keyboard-friendly back/forward flow",
);
expect(
  page.includes("Сохранено"),
  "Questionnaire must communicate persisted draft state",
);
expect(
  careerCta.includes("/products/career?profileId="),
  "Self report Career CTA must use the canonical Career product route",
);
expect(
  !careerCta.includes("/dashboard/products/career"),
  "Self report Career CTA must not use the obsolete dashboard-prefixed route",
);
expect(
  page.includes("useSearchParams") &&
    page.includes('searchParams.get("profileId")'),
  "Career product page must consume the profileId deep link",
);
expect(
  page.includes("openQuestionnaire(preselectedProfile)"),
  "Career product page must open the deep-linked profile questionnaire",
);

console.log("Career product UX contract checks passed");
