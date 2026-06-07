import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const billingPath = resolve("src/app/(dashboard)/billing/page.tsx");
const sidebarPath = resolve("src/components/layout/sidebar.tsx");

if (!existsSync(billingPath)) {
  throw new Error("Missing billing page");
}

const billingPage = readFileSync(billingPath, "utf8");
const sidebar = readFileSync(sidebarPath, "utf8");

for (const marker of [
  "Astrotype Membership",
  "Откройте полную карту своей личности",
  "Free",
  "Бесплатный вход",
  "Расчёт натальной карты",
  "Базовый тип и архетип",
  "3 сильные стороны",
  "Teaser платного отчёта",
  "Plus",
  "999 ₽",
  "Полный доступ к персональной карте",
  "Полный личностный отчёт",
  "Сильные стороны мышления и поведения",
  "Профессиональный профиль",
  "Отношения и типичные сценарии близости",
  "Совместимость с другими людьми",
  "20 персональных вопросов к карте",
  "Сохранение нескольких профилей",
  "Free — вход в систему. Plus — полная карта личности, отношений",
  "и карьеры.",
  "Frontend-only",
]) {
  if (!billingPage.includes(marker)) {
    throw new Error(`Billing page missing marker: ${marker}`);
  }
}

for (const forbidden of [
  "699–999 ₽",
  "€7.99–€9.99",
  "закрытый доступ к себе",
  "relational-слой",
  "стиль привязанности",
  "Сила функций и архетипов",
  "10–30 персональных AI-вопросов",
  "/api/v1/payments",
  "createPayment",
  "product_id",
  "amount:",
  "fetch(",
]) {
  if (billingPage.includes(forbidden)) {
    throw new Error(
      `Billing page must stay fixed-price frontend-only for now; found: ${forbidden}`,
    );
  }
}

if (
  !sidebar.includes('title: "Оплата"') ||
  !sidebar.includes('href: "/billing"')
) {
  throw new Error("Sidebar must expose billing page as Оплата");
}

console.log("Billing UX structure check passed");
