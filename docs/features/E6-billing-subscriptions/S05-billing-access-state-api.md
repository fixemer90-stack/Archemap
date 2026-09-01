# S05: Billing access-state API

## Status

⬜ Не начато

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

- [ ] Add authenticated `GET /api/v1/billing/access` or equivalent.
- [ ] Endpoint returns `access_state` from backend state.
- [ ] Endpoint includes safe latest payment summary when useful.
- [ ] Endpoint includes current entitlements/grants without exposing provider secrets.
- [ ] Return states include `free`, `checkout_pending`, `plus_active`, `payment_failed`, `plus_inactive`.
- [ ] Tests cover users with no payment, pending payment, succeeded payment, failed/cancelled payment.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

Add narrower or broader checks in the implementation PR when this story touches additional modules.
