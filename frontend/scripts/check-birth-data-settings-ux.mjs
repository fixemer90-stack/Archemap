import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const settingsPath = path.join(root, "src/app/(dashboard)/settings/page.tsx");
const componentPath = path.join(
  root,
  "src/components/settings/BirthDataSettings.tsx",
);
const apiPath = path.join(root, "src/lib/api/birth-data-refinement.ts");

const settings = fs.readFileSync(settingsPath, "utf8");
const component = fs.readFileSync(componentPath, "utf8");
const api = fs.readFileSync(apiPath, "utf8");

for (const token of ["Профиль", "Безопасность", "BirthDataSettings"]) {
  if (!settings.includes(token))
    throw new Error(`settings page misses ${token}`);
}

for (const token of [
  "Уточнить данные",
  "Проверить изменения",
  "Было",
  "Стало",
  "birth-data-refinement-status",
  "birth-data-refinements",
  "visibilitychange",
  "motion-reduce",
  "min-h-11",
  "aria-live",
  "Открыть текущий отчёт",
  "Открыть обновлённый отчёт",
]) {
  if (!component.includes(token) && !api.includes(token)) {
    throw new Error(`birth-data settings contract misses ${token}`);
  }
}

if (component.includes("generation_id") || component.includes("input_hash")) {
  throw new Error("internal generation vocabulary leaked into settings UI");
}

console.log("birth-data settings UX contract passed");
