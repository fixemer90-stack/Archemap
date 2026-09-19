import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const pagePath = path.join(
  root,
  "src/app/(dashboard)/products/career/report/[reportId]/page.tsx",
);
const vmPath = path.join(root, "src/lib/career/report-view-model.ts");
const apiPath = path.join(root, "src/lib/api/career.ts");
const page = fs.readFileSync(pagePath, "utf8");
const vm = fs.readFileSync(vmPath, "utf8");
const api = fs.readFileSync(apiPath, "utf8");

function expect(condition, message) {
  if (!condition) throw new Error(message);
}

expect(
  !page.includes("generated_report"),
  "Career reader must not use legacy generated_report",
);
expect(
  api.includes("/api/v1/career/reports/"),
  "Career reader must use the progressive Career report endpoint",
);
expect(
  api.includes("/pdf"),
  "Career PDF must use the Career report PDF endpoint",
);
expect(
  vm.includes("professional_summary"),
  "Reader view model must preserve canonical section order",
);
expect(
  vm.includes("career_paths"),
  "Reader view model must include career paths",
);
expect(
  vm.includes("не оценка"),
  "Scores must be explained without good/bad ranking",
);
expect(
  vm.includes("Возможный пример"),
  "Profession examples must remain conditional",
);
expect(
  vm.includes("context_constraints"),
  "Context constraints must survive view-model mapping",
);
expect(
  page.includes("narrative_failed"),
  "Reader must preserve deterministic content on narrative failure",
);
expect(
  page.includes("data-career-term"),
  "Reader must render whole-word Career tooltips",
);
expect(
  page.includes("@media print") || page.includes("print:"),
  "Reader must define a print presentation",
);

console.log("Career report reader contract checks passed");
