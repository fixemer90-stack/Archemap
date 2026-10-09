# Story E6.S14: Billing UI for monthly Plus period and management

Status: ✅ Реализовано локально
Feature: [E6 Billing & subscriptions](./FEATURE.md)
Architecture: [Monthly Plus subscription contract](../../architecture/monthly-plus-subscription-contract.md)

## Context

For SaaS, the user must see the current Plus period, next billing date and cancellation state. A billing page that only says “Plus активен” is not enough.

## Goal

Update billing/account UI contracts so every Plus state explains the paid period and next action.

## What to do

1. Render current plan: `Astrotype Plus`, monthly interval and price.
2. Render `current_period_end` as “Plus активен до …”.
3. Render `next_billing_at` when renewal is enabled.
4. Render `cancel_at_period_end` as “автопродление отключено”.
5. Render past-due/expired states with clear retry/reactivation CTA.
6. Add cancel/resume/manage controls only after backend endpoints exist.
7. Add UI regression checks for all access states.

## Required UI state copy

| API state          | User-facing copy direction                                  |
| ------------------ | ----------------------------------------------------------- |
| `free`             | `Plus не активен. Доступ открывается по месячной подписке.` |
| `checkout_pending` | `Проверяем оплату. Plus включится после подтверждения.`     |
| `plus_active`      | `Plus активен до <date>. Следующее списание — <date>.`      |
| `cancel_scheduled` | `Plus активен до <date>. Автопродление отключено.`          |
| `past_due`         | `Не удалось продлить Plus. Обновите оплату.`                |
| `plus_expired`     | `Срок Plus истёк. Можно оформить подписку заново.`          |

## Acceptance criteria

- [x] No UI surface shows active monthly Plus without an end date.
- [x] Billing page shows current period end and next billing date.
- [x] Dashboard/sidebar can show compact active-until or inactive state.
- [x] Cancellation scheduled state is clear and not presented as an error.
- [x] Expired/past-due states offer retry/reactivation.
- [x] Frontend does not invent period dates; it renders backend values only.

## Local evidence

- checkout uses `POST /api/v1/subscriptions/checkout` with the server-owned
  `astrotype_plus_monthly` plan code;
- billing access renders `current_period_end`, `next_billing_at`,
  `cancel_at_period_end`, `past_due`, `plus_expired` and `plus_suspended` from
  the backend response;
- cancellation and resume controls call the authenticated subscription
  lifecycle endpoints and refresh backend access state;
- dashboard and sidebar render the backend-provided active-until date.

Verified with:

```bash
cd frontend
node scripts/check-billing-ux.mjs
npx eslint 'src/app/(dashboard)/billing/page.tsx' 'src/app/(dashboard)/dashboard/page.tsx' src/components/layout/sidebar.tsx src/components/billing/billing-checkout-button.tsx src/hooks/use-billing-access.ts src/lib/api/payments.ts
npx tsc --noEmit --pretty false
```

## Verification target

```bash
cd frontend
node scripts/check-billing-ux.mjs
npx eslint src/app/\(dashboard\)/billing/page.tsx src/app/\(dashboard\)/dashboard/page.tsx src/components/layout/sidebar.tsx src/lib/api/payments.ts
npx tsc --noEmit --pretty false
```
