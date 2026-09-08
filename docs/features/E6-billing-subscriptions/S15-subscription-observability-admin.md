# Story E6.S15: Subscription observability, admin repair and audit trail

Status: ⬜ Не начато
Feature: [E6 Billing & subscriptions](./FEATURE.md)
Architecture: [Monthly Plus subscription contract](../../architecture/monthly-plus-subscription-contract.md)

## Context

Recurring billing failures are operational problems, not only user-facing UX states. Support must be able to answer: who has Plus, until when, why it changed, and which provider event caused the change.

## Goal

Add observability and admin/support contracts for monthly Plus lifecycle without relying on unsafe manual database edits.

## What to do

1. Add structured logs for subscription state transitions.
2. Add append-only `subscription_events` audit records.
3. Add safe admin/support read queries or endpoint contracts.
4. Add repair commands/runbooks for webhook replay and provider reconciliation.
5. Add alerts for webhook failure, renewal failure spikes and subscriptions near unexpected expiry.

## Acceptance criteria

- [ ] Every subscription state change has a subscription event row.
- [ ] Events are idempotent by provider event/payment id where possible.
- [ ] Support can see plan, status, current period, next billing and latest payment.
- [ ] Manual repairs require an explicit reason recorded in audit metadata.
- [ ] Webhook/reconciliation failures are observable in logs/metrics.
- [ ] Runbook covers replaying provider events and reconciling one user by email.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_subscription_events.py tests/unit/test_reconciliation.py -q
./.venv/bin/python -m ruff check app/modules/subscriptions app/modules/reconciliation tests/unit
./.venv/bin/python -m mypy app/modules/subscriptions app/modules/reconciliation tests/unit
```
