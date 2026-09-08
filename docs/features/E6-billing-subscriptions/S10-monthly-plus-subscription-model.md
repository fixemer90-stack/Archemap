# Story E6.S10: Monthly Plus subscription model

Status: ⬜ Не начато
Feature: [E6 Billing & subscriptions](./FEATURE.md)
Architecture: [Monthly Plus subscription contract](../../architecture/monthly-plus-subscription-contract.md)

## Context

Astrotype currently has payment-confirmed access and active entitlements, but the long-term SaaS model must be a monthly Plus account subscription with a controlled paid period. A Plus subscription without an expiry date is ambiguous and should not be the target state for SaaS.

## Goal

Define and implement a server-owned monthly Plus plan and subscription data model that records `current_period_start`, `current_period_end`, renewal state and provider identity.

## What to do

1. Add a server-owned plan model/catalog entry for `astrotype_plus_monthly`.
2. Add subscription storage for user, plan, provider, lifecycle status and billing period.
3. Link subscription creation to checkout creation without granting access before payment confirmation.
4. Ensure the first successful payment creates a one-month active period.
5. Record append-only subscription lifecycle events.

## Files expected to change when implemented

| Area | Expected files |
| --- | --- |
| Models/migrations | `backend/app/modules/subscriptions/models.py`, `backend/alembic/versions/*` |
| Catalog | `backend/app/modules/catalog/service.py` |
| Payments orchestration | `backend/app/modules/payments/service.py` |
| Subscription service | `backend/app/modules/subscriptions/service.py` |
| Schemas/API | `backend/app/modules/subscriptions/schemas.py`, `backend/app/modules/subscriptions/router.py` |
| Tests | `backend/tests/unit/test_subscriptions*.py`, `backend/tests/unit/test_payments.py` |

## Acceptance criteria

- [ ] Backend catalog defines `astrotype_plus_monthly` as a monthly plan.
- [ ] Subscription records include `current_period_start` and `current_period_end`.
- [ ] Initial checkout creates a subscription shell but does not activate Plus.
- [ ] Initial succeeded payment activates exactly one monthly period.
- [ ] Subscription lifecycle events are append-only and idempotent.
- [ ] No monthly Plus entitlement is created with `expires_at=NULL`.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_subscriptions.py tests/unit/test_payments.py -q
./.venv/bin/python -m ruff check app/modules/subscriptions app/modules/payments tests/unit/test_subscriptions.py tests/unit/test_payments.py
./.venv/bin/python -m mypy app/modules/subscriptions app/modules/payments tests/unit/test_subscriptions.py tests/unit/test_payments.py
```
