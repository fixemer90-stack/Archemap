# Story E8.S02: Backend report access policy

Status: ⬜ Не начато
Feature: [E8 Account-level report access](./FEATURE.md)
Architecture: [Account levels and report access policy](../../architecture/account-levels-report-access-policy.md)

## Context

Frontend labels cannot protect report data. One backend policy must grant the basic report to any authenticated account and require active Plus for every other report.

## What to do

1. Implement a named report-access policy that consumes authenticated user, report type and backend-owned Plus state.
2. Grant `basic` after authentication without a paid entitlement.
3. Require active, unexpired Plus access for `plus_only`.
4. Keep `account_tier` as display/cache state, not sufficient proof.
5. Return safe locked metadata for denied Plus-only access.

## Acceptance criteria

- [ ] Free and Plus users both pass the basic-report policy.
- [ ] Free users fail Plus-only checks with `required_level=plus`.
- [ ] Active Plus users pass Plus-only checks.
- [ ] Expired Plus and tier-only Plus fail Plus-only checks but retain basic access.
- [ ] Locked decisions contain no protected report payload.
- [ ] Policy behavior is covered at exact subscription expiry boundaries.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_report_access_policy*.py tests/unit/test_subscriptions*.py -q
./.venv/bin/python -m ruff check app/modules/authorization app/modules/subscriptions tests/unit
./.venv/bin/python -m mypy app/modules/authorization app/modules/subscriptions
```
