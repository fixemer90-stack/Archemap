# Story E6.S15: Subscription observability, admin repair and audit trail

Status: ✅ Реализовано локально; live alert delivery не проверена
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

- [x] Every subscription state change has a subscription event row.
- [x] Events are idempotent by provider event/payment id where possible.
- [x] Support can see plan, status, current period, next billing and latest payment.
- [x] Manual repairs require an explicit reason recorded in audit metadata.
- [x] Webhook/reconciliation failures are observable in logs/metrics.
- [x] Runbook covers replaying provider events and reconciling one user by email.

## Implemented support surface

Both endpoints require an active verified `is_superuser` account.

```http
GET /api/v1/admin/subscriptions/support?email=user@example.com
POST /api/v1/admin/subscriptions/reconcile
```

The support read returns the monthly plan, subscription state, paid period,
next billing date, latest payment status and up to 100 lifecycle events. The
repair endpoint accepts only:

```json
{
  "email": "user@example.com",
  "reason": "support ticket BILL-42"
}
```

Before reconciliation it appends a `manual_reconciliation_requested` event
with the reason and operator user id. It never edits period or entitlement
rows directly.

## Observability

Low-cardinality OTEL instruments:

- `subscription_state_transitions` with bounded `event_type`, `old_status` and
  `new_status` attributes;
- `subscription_operation_failures` with bounded `code` values for renewal,
  webhook and provider reconciliation failures.

Staging Prometheus loads `deploy/prometheus-subscriptions.rules.yaml`. Static
rules cover renewal failure spikes, webhook/reconciliation failures, and
unexpected expiry/suspension transitions. Rule delivery and notification
routing remain a live staging/production check, not local evidence.

## Operator runbook

### Inspect one user by email

1. Authenticate as a verified superuser through the normal admin session.
2. Call `GET /api/v1/admin/subscriptions/support?email=<url-encoded-email>`.
3. Record `subscription_id`, `status`, `current_period_end`,
   `latest_payment_status` and the newest event before any repair.
4. Do not repair an already-active subscription or manually extend dates.

### Reconcile one user

1. Create or reference a support ticket with the reason for the action.
2. Call `POST /api/v1/admin/subscriptions/reconcile` with the user email and
   explicit reason.
3. Re-read the support endpoint and confirm a
   `manual_reconciliation_requested` event exists.
4. Confirm the latest pending provider payment was reconciled server-to-server.
5. If access changed, confirm the corresponding provider-backed lifecycle event
   and bounded transition metric; never treat the manual audit event itself as
   payment proof.

### Replay a YooKassa event

1. Identify the provider payment id and local payment id from the support and
   payment audit trail without copying raw secrets into a ticket.
2. Ask YooKassa to redeliver the notification, or replay the saved notification
   payload to `POST /api/v1/payments/webhooks/yookassa` from the protected
   operator environment.
3. The webhook handler must fetch the canonical YooKassa object again; the
   saved payload alone is not trusted.
4. Re-read support state and verify event idempotency. Repeated delivery must
   not extend the period twice.
5. If canonical fetch or immutable payment validation fails, stop and inspect
   `subscription_operation_failures` plus structured logs; do not edit the DB.

## Local evidence

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_subscription_events.py tests/unit/test_reconciliation.py tests/unit/test_subscription_observability_config.py -q
./.venv/bin/python -m pytest tests/unit/test_subscriptions.py tests/unit/test_subscriptions_access.py tests/unit/test_subscriptions_renewal.py tests/unit/test_subscriptions_cancellation.py tests/unit/test_payments.py -q
./.venv/bin/python -m ruff check app/modules/subscriptions app/modules/admin app/modules/payments/service.py app/dependencies.py tests/unit/test_subscription_events.py tests/unit/test_reconciliation.py tests/unit/test_subscription_observability_config.py
./.venv/bin/python -m mypy app/modules/subscriptions app/modules/admin app/modules/payments/service.py app/dependencies.py tests/unit/test_subscription_events.py tests/unit/test_reconciliation.py tests/unit/test_subscription_observability_config.py
```

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_subscription_events.py tests/unit/test_reconciliation.py -q
./.venv/bin/python -m ruff check app/modules/subscriptions app/modules/reconciliation tests/unit
./.venv/bin/python -m mypy app/modules/subscriptions app/modules/reconciliation tests/unit
```
