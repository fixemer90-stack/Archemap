# S08: Frontend billing return and status UX

## Status

⬜ Не начато

## Context

After YooKassa redirects the user back, the billing page must ask the backend what happened. It must not show success merely because `checkout=return` is present.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `frontend/src/app/(dashboard)/billing/page.tsx`
- `frontend/src/components/billing/billing-checkout-button.tsx`
- `frontend/src/lib/api/payments.ts`
- billing/access frontend query hook
- `frontend/scripts/check-billing-ux.mjs`

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [ ] `/billing?checkout=return` fetches backend access state.
- [ ] Pending state says payment is being checked.
- [ ] Active state says Plus is active.
- [ ] Failed/cancelled state offers retry without blaming the user.
- [ ] Success is never inferred only from URL/query params.
- [ ] UX copy explains that confirmation can take a moment.
- [ ] Frontend regression script covers pending/active/failure copy markers.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

Add narrower or broader checks in the implementation PR when this story touches additional modules.
