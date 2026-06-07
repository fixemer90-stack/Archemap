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
  "Free",
  "Бесплатный вход",
  "Расчёт натальной карты",
  "базовый тип",
  "3 сильные стороны",
  "Teaser платного отчёта",
  "Plus",
  "699–999 ₽",
  "€7.99–€9.99",
  "Полный личностный отчёт",
  "Профессиональный профиль",
  "Отношения и стиль привязанности",
  "Совместимость с другими людьми",
  "10–30 персональных AI-вопросов",
  "Сохранение нескольких профилей",
  "Frontend подготовлен",
]) {
  if (!billingPage.includes(marker)) {
    throw new Error(`Billing page missing marker: ${marker}`);
  }
}

for (const forbidden of [
  "/api/v1/payments",
  "createPayment",
  "product_id",
  "amount:",
  "fetch(",
]) {
  if (billingPage.includes(forbidden)) {
    throw new Error(
      `Billing page must stay frontend-only for now; found: ${forbidden}`,
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
