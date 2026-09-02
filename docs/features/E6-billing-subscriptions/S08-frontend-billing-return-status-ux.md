# S08: Frontend billing return and status UX

## Status

✅ Реализовано

## Context

After YooKassa redirects the user back, the billing page asks the backend what happened. It does not show success merely because `checkout=return` is present.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `frontend/src/app/(dashboard)/billing/page.tsx`
- `frontend/src/components/billing/billing-checkout-button.tsx`
- `frontend/src/lib/api/payments.ts`
- `frontend/scripts/check-billing-ux.mjs`

## Implemented behavior

- `/billing?checkout=return` reads `GET /api/v1/billing/access` through `getBillingAccess()`.
- Pending state says the system is checking the payment and confirmation can take a moment.
- Active state says Plus is active only after backend state says so.
- Failed/inactive states offer retry without blaming the user.
- The billing page copy continues to state that access is enabled after YooKassa/backend confirmation, not after browser return.

## Acceptance criteria

- [x] `/billing?checkout=return` fetches backend access state.
- [x] Pending state says payment is being checked.
- [x] Active state says Plus is active.
- [x] Failed/cancelled state offers retry without blaming the user.
- [x] Success is never inferred only from URL/query params.
- [x] UX copy explains that confirmation can take a moment.
- [x] Frontend regression script covers pending/active/failure copy markers.

## Verification

```bash
cd frontend
node scripts/check-billing-ux.mjs
npx eslint src/app/\(dashboard\)/billing/page.tsx src/lib/api/payments.ts scripts/check-billing-ux.mjs
npx tsc --noEmit --pretty false
```

Latest local result:

```text
Billing UX structure check passed
eslint: passed
TypeScript: passed
```
