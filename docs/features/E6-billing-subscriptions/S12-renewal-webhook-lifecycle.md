# Story E6.S12: Renewal webhook lifecycle

Status: ⬜ Не начато
Feature: [E6 Billing & subscriptions](./FEATURE.md)
Architecture: [Monthly Plus subscription contract](../../architecture/monthly-plus-subscription-contract.md)

## Context

Monthly SaaS is not finished after the first payment. Every renewal must be confirmed server-to-server and must extend the paid period only when the provider confirms successful paid renewal.

## Goal

Define and implement renewal handling for monthly Plus: renewal pending, succeeded, failed/past-due and expired transitions.

## What to do

1. Verify the exact YooKassa recurring/autopayment mechanism available to the merchant account.
2. Store provider recurring identifiers required for renewal reconciliation.
3. Process renewal success events idempotently.
4. Extend `current_period_end` by one month only after successful paid renewal.
5. Record failed renewal without extending access.
6. Expire or past-due subscriptions when renewal failure crosses the policy boundary.

## Acceptance criteria

- [ ] Provider renewal event is stored before processing.
- [ ] Renewal success is reconciled against canonical YooKassa payment object.
- [ ] Renewal success extends current period by exactly one billing interval.
- [ ] Duplicate renewal events do not double-extend the period.
- [ ] Renewal failure does not extend period.
- [ ] Past-due/expired transitions are explicit and visible in billing access state.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_subscriptions_renewal.py tests/unit/test_payments.py -q
./.venv/bin/python -m ruff check app/modules/subscriptions app/modules/payments tests/unit/test_subscriptions_renewal.py
./.venv/bin/python -m mypy app/modules/subscriptions app/modules/payments tests/unit/test_subscriptions_renewal.py
```
