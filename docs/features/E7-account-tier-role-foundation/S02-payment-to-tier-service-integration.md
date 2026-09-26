# S02: Payment-to-tier service integration

## Status

🟡 Implemented; replay regression evidence missing

## Context

Tier changes must happen only after backend-confirmed payment success. Browser return, frontend state and raw webhook payload alone are not enough.

## Source architecture

- `../../architecture/account-tier-role-foundation.md`
- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `backend/app/modules/authorization/service.py`
- `backend/app/modules/payments/service.py`
- `backend/tests/unit/test_payments.py`

## Implemented behavior

- `AccountTierService.upgrade_to_plus()` is the named service boundary.
- YooKassa webhook path calls tier upgrade only after canonical provider reconciliation proves `status == succeeded` and `paid == true`.
- Failed/cancelled/mismatched/unpaid events leave tier unchanged.
- Replayed webhook remains idempotent.

## Acceptance criteria

- [x] Payment handling does not mutate user tier inline without a named service.
- [x] Successful YooKassa reconciliation upgrades tier to `plus`.
- [x] `succeeded` without `paid=true` does not upgrade tier.
- [x] Metadata mismatch does not upgrade tier.
- [x] Provider reconciliation failure does not upgrade tier.
- [x] Duplicate/replayed success is safe.
- [ ] A regression test executes the same successful webhook twice and proves one effective entitlement/tier outcome.
- [ ] A direct service test proves repeated `AccountTierService.upgrade_to_plus()` calls remain safe.

## Audit note — 2026-09-26

The service and entitlement upsert paths are idempotent by code inspection. Existing tests cover success, metadata mismatch, unpaid success and provider failure, but they do not execute the exact replay or repeated direct-service scenarios required by the architecture test contract. See `./AUDIT-discrepancies.md`.

## Verification

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_payments.py -q
./.venv/bin/ruff check app/modules/payments app/modules/authorization tests/unit/test_payments.py
```
