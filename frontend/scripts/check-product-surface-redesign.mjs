#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname;
const read = (path) => readFileSync(join(root, path), "utf8");

const homepage = read("src/app/page.tsx");
const dashboard = read("src/app/(dashboard)/dashboard/page.tsx");
const billing = read("src/app/(dashboard)/billing/page.tsx");
const surface = read("src/components/product-surface/product-surface.tsx");
const reportPage = read("src/app/(dashboard)/report/v2/[profileId]/page.tsx");
const legacyReportPage = read(
  "src/app/(dashboard)/report/[profileId]/page.tsx",
);
const reportReader = read(
  "src/components/astrotype-v2/report/V2ReportReader.tsx",
);

function assertMarkers(name, source, markers) {
  for (const marker of markers) {
    assert.match(source, new RegExp(marker), `${name}: missing ${marker}`);
  }
}

assertMarkers("surface", surface, [
  'data-product-surface="shell"',
  'data-product-surface="hero"',
  'data-product-surface="card"',
  "ProductSurfaceShell",
  "ProductSurfaceHero",
  "ProductSurfaceCard",
]);

assertMarkers("homepage", homepage, [
  'data-product-surface-preview="illustrative"',
  "Не гороскоп",
  "данные рождения",
  "Расчёт карты",
  "Личный отчёт",
  'href="/register"',
  "демонстрационный фрагмент",
  "не готовый отчёт конкретного",
  "Построить свой отчёт",
]);

assertMarkers("dashboard", dashboard, [
  'data-product-surface-page="dashboard"',
  "Личный кабинет Astrotype",
  "Последний отчёт",
  "Постройте первую карту",
  "Мои отчёты",
  "Личные карты и портреты",
  "Создайте первую карту рождения",
  "Оплата и доступ",
]);
assert.equal(
  dashboard.includes("href={`/report/v2/${primaryProfile.id}`}"),
  true,
  "dashboard: missing primary report link",
);
assert.equal(
  dashboard.includes("href={`/report/v2/${profile.id}`}"),
  true,
  "dashboard: missing profile card report links",
);

assertMarkers("billing", billing, [
  'data-product-surface-page="billing"',
  "Бесплатный / Плюс",
  "Оплата открывается в YooKassa",
  "Возврат на сайт сам по себе не считается успешной оплатой",
  "Проверяем оплату",
  "Плюс активен",
  "Оплата не завершена",
  "getBillingAccess",
  "BillingCheckoutButton",
  "возврат не равен успеху оплаты",
]);

assertMarkers("report return", reportPage + reportReader + legacyReportPage, [
  'href="/dashboard"',
  "В кабинет",
]);
assert.equal(
  read("src/app/(dashboard)/layout.tsx").includes(
    'pathname.startsWith("/report/v2/")',
  ),
  true,
  "report route must remain standalone in dashboard layout",
);

for (const [name, source] of Object.entries({ homepage, dashboard, billing })) {
  for (const forbidden of [
    "Model A",
    "MBTI",
    "function_strengths",
    "socionics",
    "Соционика",
    "v2/json",
    "evidence ids",
    "Evidence-first",
    "backend-каталога",
    "webhook",
    "Teaser",
    "teaser",
    "базовый тип и архетип",
    "Статус аккаунта ещё Free",
    "в аккаунте появляется Plus",
  ]) {
    assert.equal(
      source.includes(forbidden),
      false,
      `${name}: forbidden ${forbidden}`,
    );
  }
}

console.log("Product surface redesign check passed");
