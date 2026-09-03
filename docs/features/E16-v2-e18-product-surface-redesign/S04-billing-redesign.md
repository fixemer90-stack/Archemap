# S04: Implement billing redesign

## Status

✅ Реализовано

## Context

The billing page should match the report/product visual language and explain payment trust clearly. It should not imply that redirect return from YooKassa is enough to unlock access.

Design direction:

- `docs/design/astrotype-v2-billing-sample.html`
- `docs/architecture/current-payment-confirmation-flow.md`
- `docs/architecture/account-tier-role-foundation.md`

## What to do

1. Update `frontend/src/app/(dashboard)/billing/page.tsx`.
2. Preserve current checkout behavior through `BillingCheckoutButton`.
3. Refresh the page visual hierarchy:
   - large report-style hero;
   - Free/Plus status cards;
   - clear Plus value block;
   - payment confirmation/trust explanation.
4. Update copy to be user-facing:
   - “Оплата открывается в YooKassa”;
   - “Доступ/статус меняется после подтверждения системой”;
   - “Возврат на сайт не равен успешной оплате”.
5. Remove outdated copy:
   - “базовый тип и архетип”;
   - “teaser” wording;
   - backend/webhook jargon in prominent user copy.
6. If account-tier status is already available by implementation time, display Free/Plus status. If not, keep the UI ready but do not fake a live value.
7. Do not add frontend-only paywall behavior.

## Files likely affected

| Path                                                          | Action                                                                  |
| ------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `frontend/src/app/(dashboard)/billing/page.tsx`               | Main implementation                                                     |
| `frontend/src/components/billing/billing-checkout-button.tsx` | Preserve behavior; update copy only if needed                           |
| `frontend/src/lib/api/payments.ts`                            | Preserve create payment contract unless a separate API story changes it |
| `frontend/scripts/check-product-surface-redesign.mjs`         | Add billing checks in S05                                               |

## Acceptance criteria

- [x] `/billing` uses report-style surfaces and no longer reads as a generic pricing page.
- [x] `BillingCheckoutButton` still creates payment for `self_full` and redirects to YooKassa confirmation URL.
- [x] Page clearly says access/status changes only after payment confirmation.
- [x] Page does not claim return from YooKassa equals payment success.
- [x] Page does not add account-tier feature restrictions.
- [x] Outdated archetype/teaser wording is removed.
- [x] User-facing copy avoids forbidden technical/legacy terms.
- [x] Mobile layout keeps price, CTA and confirmation explanation readable.

## Verification

```bash
cd frontend
npx eslint .
npx prettier --check 'src/app/(dashboard)/billing/page.tsx' 'src/components/billing/billing-checkout-button.tsx'
npx tsc --noEmit
```

Runtime smoke when available:

```text
/billing
/billing?checkout=return
```

## Implementation evidence

Implemented and verified with:

```bash
cd frontend
npm test
npx eslint .
npx prettier --check .
npx tsc --noEmit --pretty false
npm run build
```

Result: all commands passed; Next production build completed successfully.
