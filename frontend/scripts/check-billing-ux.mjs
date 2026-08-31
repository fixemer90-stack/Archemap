import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const billingPath = resolve("src/app/(dashboard)/billing/page.tsx");
const checkoutButtonPath = resolve(
  "src/components/billing/billing-checkout-button.tsx",
);
const paymentsApiPath = resolve("src/lib/api/payments.ts");
const sidebarPath = resolve("src/components/layout/sidebar.tsx");

if (!existsSync(billingPath)) {
  throw new Error("Missing billing page");
}
if (!existsSync(checkoutButtonPath)) {
  throw new Error("Missing billing checkout button");
}
if (!existsSync(paymentsApiPath)) {
  throw new Error("Missing payments API client");
}

const billingPage = readFileSync(billingPath, "utf8");
const checkoutButton = readFileSync(checkoutButtonPath, "utf8");
const paymentsApi = readFileSync(paymentsApiPath, "utf8");
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
  "Создаём оплату через YooKassa",
  "Оплата открывается на стороне YooKassa",
  "Доступ включается",
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
  "Frontend-only",
  'aria-disabled="true"',
  'href="#plus"',
  "amount:",
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

for (const marker of [
  'PLUS_PRODUCT_ID = "self_full"',
  "createPayment({",
  "product_id: PLUS_PRODUCT_ID",
  "return_url: getBillingReturnUrl()",
  "window.location.assign(payment.confirmation_url)",
]) {
  if (!checkoutButton.includes(marker)) {
    throw new Error(`Checkout button missing marker: ${marker}`);
  }
}

for (const marker of [
  "type CreatePaymentRequest",
  "product_id: string",
  "return_url?: string",
  'api.post<PaymentResponse>("/api/v1/payments", request)',
]) {
  if (!paymentsApi.includes(marker)) {
    throw new Error(`Payments API client missing marker: ${marker}`);
  }
}

for (const forbidden of ["amount:", "currency:", "description:"]) {
  if (checkoutButton.includes(forbidden)) {
    throw new Error(
      `Checkout button must not send commercial fields: ${forbidden}`,
    );
  }
}

console.log("Billing UX structure check passed");
