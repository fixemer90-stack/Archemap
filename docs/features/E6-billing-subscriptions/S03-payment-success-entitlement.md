# S03: Payment success state and entitlement grant

## Status

✅ Реализовано

## Context

Successful payment must change durable backend state and grant product access exactly once.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `backend/app/modules/payments/service.py`
- `backend/app/modules/payments/models.py`
- `backend/app/modules/authorization/models.py`
- `backend/app/modules/authorization/service.py`
- `backend/tests/unit/test_payments.py`

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [x] Success requires `status == "succeeded"`.
- [x] Success also requires `paid == true`.
- [x] Local payment gets `status='succeeded'` and `paid_at`.
- [x] Active entitlement is granted for the product metadata.
- [x] Replayed webhook does not duplicate entitlement.
- [x] Mismatch and `succeeded` without `paid=true` do not grant access.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

Add narrower or broader checks in the implementation PR when this story touches additional modules.
