# Story E6.S13: Cancellation, grace period and plan expiry UX states

Status: ⬜ Не начато
Feature: [E6 Billing & subscriptions](./FEATURE.md)
Architecture: [Monthly Plus subscription contract](../../architecture/monthly-plus-subscription-contract.md)

## Context

A SaaS user must be able to stop future billing and still keep access through the paid period. Failed renewals and grace period must be explicit, not hidden inside a generic inactive state.

## Goal

Document and implement cancellation/resume behavior, plus optional grace-period state if product policy enables it.

## What to do

1. Add cancel-at-period-end behavior.
2. Add resume-before-expiry behavior.
3. Decide whether `past_due` grants temporary access; default is no access unless `grace_until` is set.
4. Make refund/chargeback/suspension able to override normal period access.
5. Return safe user-facing state and copy hints from billing access API.

## Acceptance criteria

- [ ] User can cancel renewal without losing already-paid access before `current_period_end`.
- [ ] `cancel_at_period_end=true` is visible in billing API and UI.
- [ ] User can resume renewal before expiry when provider supports it.
- [ ] Past-due state is explicit and never silently extends access.
- [ ] Grace access, if introduced, has `grace_until` and tests.
- [ ] Refund/chargeback/suspension can deactivate Plus before natural expiry when required.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_subscriptions_cancellation.py tests/unit/test_billing_access.py -q
cd ../frontend
npx tsc --noEmit --pretty false
npx eslint src/app/\(dashboard\)/billing/page.tsx src/lib/api/payments.ts
```
