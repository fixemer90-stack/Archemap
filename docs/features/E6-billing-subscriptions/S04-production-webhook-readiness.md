# S04: Production webhook readiness

## Status

🟡 Runbook готов; live YooKassa smoke не выполнен в этой среде

## Context

The code path is not production-ready until YooKassa can reach the live webhook URL and operators can verify payment-to-entitlement activation from logs/database state.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`
- Production smoke runbook: `../../implementation/payment-confirmation-production-smoke.md`

## Files affected

- deployment environment configuration
- YooKassa merchant cabinet settings
- backend logs
- database inspection runbook
- `docs/implementation/payment-confirmation-production-smoke.md`
- `docs/architecture/current-payment-confirmation-flow.md`

## Implemented readiness assets

- Backend webhook endpoint exists at `POST /api/v1/payments/webhooks/yookassa`.
- Webhook processing stores raw events before reconciliation.
- Reconciliation fetches YooKassa canonical payment server-to-server.
- Production smoke runbook records exact HTTPS, UI, database and log checks.

## Acceptance criteria

- [ ] Production `YOOKASSA_SHOP_ID` and `YOOKASSA_SECRET_KEY` are configured in the deployed runtime.
- [ ] YooKassa webhook URL is registered for the production/staging backend.
- [ ] Webhook URL is externally reachable over HTTPS.
- [ ] Test payment produces a stored webhook event.
- [ ] Test payment produces `payments.status='succeeded'` and non-null `paid_at`.
- [ ] Test payment produces an active entitlement.
- [ ] Failure/cancelled payment does not produce active access.
- [x] Operator runbook exists with exact database/log checks for the criteria above.

## Verification

Local regression command:

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_payments.py -q
```

Production smoke command/checklist:

```text
docs/implementation/payment-confirmation-production-smoke.md
```

Live merchant-cabinet registration and deployed HTTPS webhook delivery require environment access outside this local repo checkout.
