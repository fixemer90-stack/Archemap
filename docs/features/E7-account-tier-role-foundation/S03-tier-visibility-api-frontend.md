# S03: Tier visibility in APIs and frontend status

## Status

✅ Реализовано в main; production deploy pending

## Context

Frontend needs to show the account/access state after checkout without inventing payment success from the URL.

## Source architecture

- `../../architecture/account-tier-role-foundation.md`
- Parent feature: `./FEATURE.md`
- Related story: `../E6-billing-subscriptions/S08-frontend-billing-return-status-ux.md`

## Files affected

- `backend/app/modules/users/router.py`
- `backend/app/modules/auth/schemas.py`
- `backend/app/modules/billing/router.py`
- `backend/app/modules/payments/schemas.py`
- `backend/app/modules/payments/service.py`
- `frontend/src/lib/api/payments.ts`
- `frontend/src/app/(dashboard)/billing/page.tsx`
- `frontend/scripts/check-billing-ux.mjs`

## Implemented behavior

- Current-user/billing responses expose `account_tier`.
- `GET /api/v1/billing/access` returns backend-owned access state.
- `/billing?checkout=return` refreshes backend access state.
- Frontend copy distinguishes pending, active, failed and inactive states.
- Frontend does not infer success from `checkout=return`.

## Acceptance criteria

- [x] API exposes `account_tier` in a safe current-user/access response.
- [x] Billing access response includes `free`, `checkout_pending`, `plus_active`, `payment_failed`, `plus_inactive` states.
- [x] Frontend calls backend after payment return.
- [x] Frontend can display status without unlocking content purely by tier.
- [x] Regression script checks billing state copy markers.
- [x] Production backend exposes the deployed endpoint after release; unauthenticated smoke returns auth error instead of 404.

## Verification

```bash
cd frontend
node scripts/check-billing-ux.mjs
npx eslint src/app/\(dashboard\)/billing/page.tsx src/lib/api/payments.ts scripts/check-billing-ux.mjs
npx tsc --noEmit --pretty false
```
