# Story E8.S02: Backend report access policy

Status: ✅ Готово
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

- [x] Free and Plus users both pass the basic-report policy.
- [x] Free users fail Plus-only checks with `required_level=plus`.
- [x] Active Plus users pass Plus-only checks.
- [x] Expired Plus and tier-only Plus fail Plus-only checks but retain basic access.
- [x] Locked decisions contain no protected report payload.
- [x] Policy behavior is covered at exact subscription expiry boundaries.

## Implementation evidence

- `ReportAccessPolicy` returns one typed, payload-safe decision for canonical and legacy report identifiers.
- `EntitlementsService.has_active_plus_access()` requires the monthly Plus plan, an allowed status and the inclusive-start/exclusive-end paid period; direct historical `self_full` access is not treated as account-wide Plus.
- Multiple entitlement rows are evaluated safely instead of relying on `scalar_one_or_none()` cardinality.
- Career uses strict monthly Plus proof while retaining its explicit grandfathered `career` entitlement path.
- Verification: `tests/unit/test_report_access_policy.py`, `tests/unit/test_subscriptions_access.py` and the Career access contract tests.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_report_access_policy*.py tests/unit/test_subscriptions*.py -q
./.venv/bin/python -m ruff check app/modules/authorization app/modules/subscriptions tests/unit
./.venv/bin/python -m mypy app/modules/authorization app/modules/subscriptions
```
