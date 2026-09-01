# S02: YooKassa webhook reconciliation

## Status

✅ Реализовано

## Context

Webhook delivery is a signal, not a complete source of truth. The backend must fetch the canonical YooKassa payment object before activating anything.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `backend/app/modules/payments/router.py`
- `backend/app/modules/payments/service.py`
- `backend/app/modules/payments/providers/yookassa.py`
- `backend/app/modules/payments/models.py`
- `backend/tests/unit/test_payments.py`

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [x] Webhook endpoint exists at `POST /api/v1/payments/webhooks/yookassa`.
- [x] Raw webhook payload is persisted.
- [x] Backend extracts provider payment id.
- [x] Backend calls YooKassa server-to-server for canonical payment data.
- [x] Processing does not trust browser return state.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

Add narrower or broader checks in the implementation PR when this story touches additional modules.
