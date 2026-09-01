# S01: Server-owned checkout creation

## Status

✅ Реализовано

## Context

The checkout request must not allow frontend to decide price, currency or commercial grants. The backend must derive all commercial values from the server catalog.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `backend/app/modules/payments/service.py`
- `backend/app/modules/payments/router.py`
- `backend/app/modules/payments/models.py`
- `backend/app/modules/catalog/service.py`
- `frontend/src/lib/api/payments.ts`
- `frontend/src/components/billing/billing-checkout-button.tsx`

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [x] Frontend sends `product_id` and `return_url` only.
- [x] Backend loads product/catalog data server-side.
- [x] Backend creates a local pending payment before provider checkout.
- [x] Backend stores YooKassa provider id and confirmation URL.
- [x] Tests prove frontend cannot set amount/currency/commercial metadata.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

Add narrower or broader checks in the implementation PR when this story touches additional modules.
