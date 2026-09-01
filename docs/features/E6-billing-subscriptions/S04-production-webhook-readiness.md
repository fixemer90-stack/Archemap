# S04: Production webhook readiness

## Status

⬜ Не начато

## Context

The code path is not production-ready until YooKassa can reach the live webhook URL and operators can verify payment-to-entitlement activation from logs/database state.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- deployment environment configuration
- YooKassa merchant cabinet settings
- backend logs
- database inspection runbook
- `docs/architecture/current-payment-confirmation-flow.md`

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [ ] Production `YOOKASSA_SHOP_ID` and `YOOKASSA_SECRET_KEY` are configured.
- [ ] YooKassa webhook URL is registered for the production/staging backend.
- [ ] Webhook URL is externally reachable over HTTPS.
- [ ] Test payment produces a stored webhook event.
- [ ] Test payment produces `payments.status='succeeded'` and non-null `paid_at`.
- [ ] Test payment produces an active entitlement.
- [ ] Failure/cancelled payment does not produce active access.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

Add narrower or broader checks in the implementation PR when this story touches additional modules.
