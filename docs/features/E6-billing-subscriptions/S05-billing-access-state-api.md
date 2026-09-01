# S05: Billing access-state API

## Status

✅ Реализовано

## Context

Frontend needs one backend-owned state endpoint so billing UI can render Free, pending, active and failed states without guessing from URL params.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `backend/app/modules/payments/*`
- `backend/app/modules/authorization/*`
- `backend/app/modules/users/*`
- `backend/app/api/*` router registration
- backend unit/API tests

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [x] Add authenticated `GET /api/v1/billing/access` or equivalent.
- [x] Endpoint returns `access_state` from backend state.
- [x] Endpoint includes safe latest payment summary when useful.
- [x] Endpoint includes current entitlements/grants without exposing provider secrets.
- [x] Return states include `free`, `checkout_pending`, `plus_active`, `payment_failed`, `plus_inactive`.
- [x] Tests cover users with no payment, pending payment, succeeded payment, failed/cancelled payment.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
./backend/.venv/bin/ruff check backend/app/modules/payments backend/app/modules/billing backend/tests/unit/test_payments.py
./backend/.venv/bin/python -m mypy backend/app/modules/payments backend/app/modules/billing --ignore-missing-imports
```

Latest verification for this story:

```text
backend/tests/unit/test_payments.py: 14 passed
ruff: All checks passed!
mypy: Success: no issues found in 13 source files
```

Implemented files:

- `backend/app/modules/billing/router.py`
- `backend/app/modules/payments/service.py`
- `backend/app/modules/payments/schemas.py`
- `backend/tests/unit/test_payments.py`
