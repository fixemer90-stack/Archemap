# E6: Billing & subscriptions — YooKassa payment confirmation

## Status

🟡 Частично реализовано

## Goal

Turn the audited payment-confirmation architecture in `docs/architecture/current-payment-confirmation-flow.md` into an implementation contract for billing, payment reconciliation, entitlement activation, account access state and frontend payment UX.

This feature answers two billing questions:

1. Current payment confirmation: Astrotype must treat a user as paid only after backend-confirmed YooKassa reconciliation, not after a browser redirect back from checkout.
2. Target SaaS model: Astrotype Plus must become a monthly account subscription with explicit period control (`current_period_start`, `current_period_end`, renewal/cancellation status), not an implicit non-expiring entitlement.

## Source architecture

- Current audit: `../../architecture/current-payment-confirmation-flow.md`
- Target SaaS contract: `../../architecture/monthly-plus-subscription-contract.md`
- Account tier architecture: `../../architecture/account-tier-role-foundation.md`
- Account tier feature: `../E7-account-tier-role-foundation/FEATURE.md`
- SRS: `../../SRS/SRS-E6-billing-subscriptions.md`

## Current implementation baseline

Already implemented and covered by `backend/tests/unit/test_payments.py`:

- server-owned checkout creation through `POST /api/v1/payments`;
- local `payments` row created before YooKassa checkout;
- YooKassa provider adapter can create and fetch provider payments;
- webhook endpoint exists at `POST /api/v1/payments/webhooks/yookassa`;
- webhook body is stored in `payment_webhooks`;
- backend fetches canonical YooKassa payment object before activation;
- reconciliation validates provider payment id, amount, currency and metadata;
- success requires `status == "succeeded"` and `paid == true`;
- successful payment grants an active product entitlement;
- duplicate webhook delivery does not duplicate entitlement.

Still missing or environment-dependent:

- live production/staging YooKassa webhook registration and external HTTPS delivery proof;
- live YooKassa smoke proving deployed webhook -> succeeded payment -> active entitlement;
- target monthly SaaS subscription lifecycle: monthly plan, recurring renewal, explicit period end, cancellation/resume, expiry enforcement and billing UI period management.

Implemented in code/docs:

- access-state API for billing/frontend;
- frontend refresh after `/billing?checkout=return`;
- account-tier `free`/`plus` update after confirmed payment;
- backend v2 report/product gates that use entitlements;
- user-visible billing status tied to backend state.

## Scope

- Checkout creation contract.
- YooKassa webhook reconciliation.
- Payment state transitions.
- Entitlement activation.
- Billing/access-state API.
- Frontend billing return and pending/success/failure states.
- Account-tier status update to `plus` as status-only, without feature restrictions.
- Report/product entitlement checks in later gated slices.
- Regression tests and production smoke checklist.
- Monthly Plus subscription model.
- Subscription period storage and expiry enforcement.
- Renewal success/failure lifecycle.
- Cancellation/resume and optional grace-period states.
- Billing UI period, next-payment and management copy.
- Subscription audit trail and support/admin observability.

## Out of scope

- Changing YooKassa merchant pricing outside the server-owned catalog.
- Trusting return URLs, browser state, query params, or frontend flags as payment proof.
- Allowing frontend to provide amount/currency/description/commercial metadata.
- Introducing Free/Plus feature restrictions before the dedicated gating story.
- Replacing YooKassa with another PSP.
- Storing full payment card data.
- Treating monthly Plus as lifetime access.
- Creating monthly Plus entitlements with `expires_at=NULL`.
- Silently converting historical non-expiring access into an expiring subscription without a product/legal decision.

## Payment proof rule

A client is paid only when the backend has reconciled the canonical YooKassa payment object server-to-server and persisted local success state:

```text
canonical_yookassa.status == "succeeded"
canonical_yookassa.paid == true
payments.status == "succeeded"
payments.paid_at IS NOT NULL
```

For product access, an active entitlement must also exist:

```text
entitlements.user_id = current user
entitlements.product = requested product
entitlements.status = "active"
entitlements.source_payment_id = confirmed payment id
```

The browser return from YooKassa is only a UX signal. It must trigger status refresh, not activation.

## Acceptance criteria

- [x] Checkout API accepts only product identifier and return URL from frontend.
- [x] Backend owns amount, currency, description and commercial metadata.
- [x] Local payment row is created before provider checkout is created.
- [x] YooKassa webhook is stored before processing.
- [x] Webhook processing fetches the canonical provider payment object server-to-server.
- [x] Reconciliation rejects amount/currency/metadata mismatches.
- [x] `succeeded` without `paid=true` does not activate access.
- [x] Confirmed successful payment stores `paid_at` and grants an entitlement.
- [ ] Production webhook URL is configured and verified against live YooKassa delivery.
- [x] Billing/access-state API returns `free`, `checkout_pending`, `plus_active`, `payment_failed`, or `plus_inactive`.
- [x] Frontend refreshes backend billing/access state after returning from YooKassa.
- [x] Backend-confirmed payment upgrades account tier to `plus` as status-only.
- [x] Free/Plus status does not restrict functionality until separate gating is enabled.
- [x] Report/product endpoints use backend entitlement checks where paid access is required.
- [x] Regression tests cover checkout, webhook reconciliation, entitlements, access-state API and frontend status UX.
- [ ] Production smoke proves one test payment creates both a succeeded payment and the expected access record.
- [ ] Monthly Plus plan is defined as a server-owned SaaS subscription plan (`astrotype_plus_monthly`).
- [ ] Subscription records store `current_period_start`, `current_period_end`, renewal/cancellation status and provider identifiers.
- [ ] Plus access is active only inside the paid monthly period.
- [ ] Renewals extend access only after backend-confirmed successful provider payment.
- [ ] Cancellation stops future renewal but preserves access until paid period end.
- [ ] Billing UI shows active-until date, next billing date and cancellation/expired/past-due states.
- [ ] Support/admin observability can answer who has Plus, until when, and why it changed.

## Stories

| ID  | Story                                                                                  | Status             |
| --- | -------------------------------------------------------------------------------------- | ------------------ |
| S01 | [Server-owned checkout creation](./S01-server-owned-checkout-creation.md)              | ✅ Реализовано     |
| S02 | [YooKassa webhook reconciliation](./S02-yookassa-webhook-reconciliation.md)            | ✅ Реализовано     |
| S03 | [Payment success state and entitlement grant](./S03-payment-success-entitlement.md)    | ✅ Реализовано     |
| S04 | [Production webhook readiness](./S04-production-webhook-readiness.md)                  | 🟡 Runbook готов   |
| S05 | [Billing access-state API](./S05-billing-access-state-api.md)                          | ✅ Реализовано     |
| S06 | [Payment-to-account-tier status update](./S06-payment-to-account-tier-status.md)       | ✅ Реализовано     |
| S07 | [Report and product entitlement gates](./S07-report-product-entitlement-gates.md)      | ✅ Реализовано     |
| S08 | [Frontend billing return and status UX](./S08-frontend-billing-return-status-ux.md)    | ✅ Реализовано     |
| S09 | [Payment confirmation regression and observability](./S09-regression-observability.md) | 🟡 Готово локально |
| S10 | [Monthly Plus subscription model](./S10-monthly-plus-subscription-model.md) | ⬜ Не начато |
| S11 | [Plus expiry and access control](./S11-plus-expiry-access-control.md) | ⬜ Не начато |
| S12 | [Renewal webhook lifecycle](./S12-renewal-webhook-lifecycle.md) | ⬜ Не начато |
| S13 | [Cancellation, grace period and plan expiry UX states](./S13-cancellation-grace-period.md) | ⬜ Не начато |
| S14 | [Billing UI for monthly Plus period and management](./S14-billing-ui-expiry-management.md) | ⬜ Не начато |
| S15 | [Subscription observability, admin repair and audit trail](./S15-subscription-observability-admin.md) | ⬜ Не начато |

## Implementation order

```mermaid
flowchart TD
  S01[S01 server-owned checkout] --> S02[S02 webhook reconciliation]
  S02 --> S03[S03 entitlement grant]
  S03 --> S04[S04 production webhook readiness]
  S03 --> S05[S05 access-state API]
  S05 --> S06[S06 account tier status]
  S05 --> S08[S08 frontend billing UX]
  S06 --> S07[S07 product/report gates]
  S07 --> S09[S09 regression and observability]
  S08 --> S09
  S09 --> S10[S10 monthly Plus subscription]
  S10 --> S11[S11 expiry access control]
  S10 --> S12[S12 renewal lifecycle]
  S11 --> S13[S13 cancel grace expiry]
  S12 --> S13
  S13 --> S14[S14 billing UI management]
  S13 --> S15[S15 observability admin]
```

## Verification commands

Current implemented backend slice:

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

When access-state/account-tier/gating stories are implemented, extend verification with targeted tests for the changed modules, for example:

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py backend/tests/unit/test_authorization*.py -q
./backend/.venv/bin/ruff check backend/app/modules/payments backend/app/modules/authorization backend/tests/unit/test_payments.py
```

Frontend billing UX verification:

```bash
cd frontend
node scripts/check-billing-ux.mjs
npx eslint src/app/\(dashboard\)/billing/page.tsx src/components/billing src/lib/api/payments.ts
npx tsc --noEmit --pretty false
```

Production smoke checklist is defined in `S04-production-webhook-readiness.md` and must be run with YooKassa test credentials before live reliance.

Target monthly SaaS implementation must additionally verify:

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_subscriptions*.py tests/unit/test_billing_access.py tests/unit/test_payments.py -q
cd ../frontend
node scripts/check-billing-ux.mjs
npx tsc --noEmit --pretty false
```
