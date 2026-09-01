# S09: Payment confirmation regression and observability

## Status

🟡 Частично готово

## Context

Payment confirmation is security-sensitive and needs regression tests plus operational visibility. Unit tests already cover the core backend path; broader API/frontend/production smoke coverage remains.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `backend/tests/unit/test_payments.py`
- future backend API tests
- future frontend billing UX tests
- backend logs/metrics
- deployment runbook

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [x] Unit tests cover successful webhook and entitlement grant.
- [x] Unit tests cover metadata mismatch.
- [x] Unit tests cover `succeeded` without `paid=true`.
- [x] Unit tests cover provider reconciliation failure.
- [ ] API tests cover access-state endpoint.
- [ ] Frontend script covers billing return UX.
- [ ] Production smoke runbook records exact database/log checks.
- [ ] Observability distinguishes invalid webhook, provider failure, mismatch, pending and success.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

Add narrower or broader checks in the implementation PR when this story touches additional modules.
