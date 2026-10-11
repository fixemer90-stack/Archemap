import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const read = (path) => readFileSync(resolve(path), "utf8");

const dashboard = read("src/app/(dashboard)/dashboard/page.tsx");
const billing = read("src/app/(dashboard)/billing/page.tsx");
const api = read("src/lib/api/astrotype-v2.ts");
const generation = read("src/lib/astrotype-v2/use-v2-report-generation.ts");
const reportPage = read("src/app/(dashboard)/report/v2/[profileId]/page.tsx");
const apiClient = read("src/lib/api-client.ts");
const careerPage = read("src/app/(dashboard)/products/career/page.tsx");

for (const marker of [
  'accessClass: "basic"',
  'accessClass: "plus_only"',
  "Доступно на любом уровне аккаунта",
  "Доступно с Plus",
  "Базовый отчёт доступен на любом уровне аккаунта",
  "Специализированные отчёты",
]) {
  if (!`${dashboard}\n${billing}`.includes(marker)) {
    throw new Error(`Missing account-level report UX marker: ${marker}`);
  }
}

for (const forbidden of [
  "Полный личный отчёт откроется после подтверждения оплаты",
  "полный личный отчёт открыт",
  "Полный личный отчёт",
]) {
  if (`${dashboard}\n${billing}`.includes(forbidden)) {
    throw new Error(
      `Basic report must not be described as Plus-only: ${forbidden}`,
    );
  }
}

for (const source of [api, generation, reportPage]) {
  for (const forbidden of [
    "AstrotypeV2LockedReportResponse",
    "isLockedAstrotypeV2Report",
    "lockedAccess",
    'state === "locked"',
    '"locked";',
    "LockedReportAccess",
  ]) {
    if (source.includes(forbidden)) {
      throw new Error(
        `Basic-report locked state must be removed: ${forbidden}`,
      );
    }
  }
}

if (
  !billing.includes('checkout === "return"') ||
  !billing.includes("getBillingAccess()")
) {
  throw new Error(
    "Checkout return must refresh backend access instead of activating Plus from query params",
  );
}

if (!dashboard.includes("sm:grid-cols-2 xl:grid-cols-4")) {
  throw new Error(
    "Report access matrix must use the same responsive card source",
  );
}

for (const marker of [
  "function extractApiErrorMessage",
  'typeof detail === "string"',
]) {
  if (!apiClient.includes(marker)) {
    throw new Error(
      `API client must safely normalize structured errors: ${marker}`,
    );
  }
}

for (const marker of [
  "loadError.status === 402",
  "setLocked(true);",
  "return;",
]) {
  if (!careerPage.includes(marker)) {
    throw new Error(
      `Career must render the Plus lock without leaking error payloads: ${marker}`,
    );
  }
}

console.log("Account-level report access UX check passed");
