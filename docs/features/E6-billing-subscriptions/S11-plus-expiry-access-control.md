# Story E6.S11: Plus expiry and access control

Status: ⬜ Не начато
Feature: [E6 Billing & subscriptions](./FEATURE.md)
Architecture: [Monthly Plus subscription contract](../../architecture/monthly-plus-subscription-contract.md)

## Context

A SaaS Plus account is active only inside its paid period. `users.account_tier='plus'` is not enough; access must be computed from subscription period and status.

## Goal

Make backend access decisions derive from active, unexpired monthly Plus subscription state and expose expiry information to clients.

## What to do

1. Implement a subscription access policy:
   `status in active states AND current_period_start <= now < current_period_end`.
2. Make `EntitlementsService.has_active_product_access()` honor subscription-derived `expires_at`.
3. Keep `account_tier` synchronized as display/status cache, not as authorization source.
4. Ensure paid report APIs deny access after expiry.
5. Add tests for boundary times: before start, inside period, exact expiry, after expiry.

## Acceptance criteria

- [ ] Plus access is false when `current_period_end <= now`.
- [ ] Plus access is true inside an active paid period.
- [ ] `account_tier='plus'` alone cannot unlock paid APIs after expiry.
- [ ] `GET /api/v1/billing/access` returns period start/end and computed state.
- [ ] Direct v2 paid APIs return locked/402 after expiry.
- [ ] Expiry boundary behavior is covered by time-frozen tests.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_authorization*.py tests/unit/test_subscriptions*.py tests/unit/test_astrotype_v2/test_api_runtime.py -q
./.venv/bin/python -m ruff check app/modules/authorization app/modules/subscriptions app/modules/astrotype_v2 tests/unit
./.venv/bin/python -m mypy app/modules/authorization app/modules/subscriptions app/modules/astrotype_v2 tests/unit
```
