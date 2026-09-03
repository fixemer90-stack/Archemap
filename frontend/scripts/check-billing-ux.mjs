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
  'data-product-surface-page="billing"',
  "Бесплатный / Плюс",
  "Статус аккаунта и доступ к полному отчёту",
  "Оплата открывается в YooKassa",
  "Цена Плюс",
  "999 ₽",
  "Базовый статус",
  "Полный личный отчёт",
  "Как подтверждается оплата",
  "Сначала подтверждение, потом доступ",
  "Возврат на сайт сам по себе не считается успешной оплатой",
  "доступ включается только после подтверждения",
  "возврат не равен успеху оплаты",
  "Бесплатный статус и Плюс сейчас не режут продукт",
  "Текущий статус аккаунта",
  "Plus активен",
  "Plus не активен",
  "Аккаунт Plus",
  "полный отчёт открыт",
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
  "Базовый тип и архетип",
  "Teaser платного отчёта",
  "backend-каталога",
  "webhook’ом",
  "Статус аккаунта ещё Free",
  "в аккаунте появляется Plus",
]) {
  if (billingPage.includes(forbidden)) {
    throw new Error(
      `Billing page must avoid stale pricing/technical copy; found: ${forbidden}`,
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
  "useBillingAccess",
  "Аккаунт Plus активен",
  "Plus не активен",
  "Статус аккаунта",
]) {
  if (!sidebar.includes(marker)) {
    throw new Error(`Sidebar missing explicit Plus status marker: ${marker}`);
  }
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
  "useSearchParams",
  'checkout === "return"',
  "getBillingAccess()",
  "Проверяем оплату",
  "Это может занять немного времени",
  "Плюс активен",
  "Оплата не завершена",
  "Попробовать ещё раз",
]) {
  if (!billingPage.includes(marker)) {
    throw new Error(`Billing return status UX missing marker: ${marker}`);
  }
}

if (
  billingPage.includes('checkout === "return"') &&
  !billingPage.includes("getBillingAccess()")
) {
  throw new Error(
    "Billing page must fetch backend access state after checkout return",
  );
}

for (const forbidden of [
  "Оплата прошла",
  "успешно оплачено",
  "checkout=return значит",
]) {
  if (billingPage.includes(forbidden)) {
    throw new Error(
      `Billing page must not infer success from query params: ${forbidden}`,
    );
  }
}

for (const marker of [
  "type CreatePaymentRequest",
  "product_id: string",
  "return_url?: string",
  "type BillingAccessResponse",
  "access_state: BillingAccessState",
  'api.post<PaymentResponse>("/api/v1/payments", request)',
  'api.get<BillingAccessResponse>("/api/v1/billing/access")',
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
