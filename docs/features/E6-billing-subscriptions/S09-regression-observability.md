# S09: Payment confirmation regression and observability

## Status

🟡 Частично готово

## Context

Payment confirmation is security-sensitive and needs regression tests plus operational visibility. Backend and frontend regression checks now cover the implemented slices; live production smoke remains environment-dependent.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`
- Production smoke runbook: `../../implementation/payment-confirmation-production-smoke.md`

## Files affected

- `backend/tests/unit/test_payments.py`
- `frontend/scripts/check-billing-ux.mjs`
- backend payment/authorization logs
- `docs/implementation/payment-confirmation-production-smoke.md`

## Acceptance criteria

- [x] Unit tests cover successful webhook and entitlement grant.
- [x] Unit tests cover metadata mismatch.
- [x] Unit tests cover `succeeded` without `paid=true`.
- [x] Unit tests cover provider reconciliation failure.
- [x] API tests cover access-state endpoint.
- [x] Frontend script covers billing return UX.
- [x] Production smoke runbook records exact database/log checks.
- [x] Observability distinguishes invalid webhook, provider failure, mismatch, pending and success.
- [ ] Live YooKassa staging/production smoke has been executed against the deployed HTTPS webhook.

## Verification

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_payments.py -q
./.venv/bin/ruff check app/modules/payments app/modules/billing app/modules/authorization app/modules/astrotype_v2 tests/unit/test_payments.py
./.venv/bin/python -m mypy .

cd ../frontend
node scripts/check-billing-ux.mjs
npx eslint src/app/\(dashboard\)/billing/page.tsx src/lib/api/payments.ts scripts/check-billing-ux.mjs src/lib/api/astrotype-v2.ts src/lib/astrotype-v2/use-v2-report-generation.ts src/app/\(dashboard\)/report/v2/\[profileId\]/page.tsx src/lib/astrotype-v2/report-view-model.ts
npx tsc --noEmit --pretty false
```

Latest local result:

```text
backend/tests/unit/test_payments.py: 22 passed
ruff: All checks passed!
mypy: Success: no issues found in 291 source files
Billing UX structure check passed
frontend eslint: passed
frontend TypeScript: passed
```
