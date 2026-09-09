# Story E8.S05: Regression, migration and rollout proof

Status: ⬜ Не начато
Feature: [E8 Account-level report access](./FEATURE.md)
Architecture: [Account levels and report access policy](../../architecture/account-levels-report-access-policy.md)

## Context

Changing the basic report from paid-gated to account-wide access touches commercial policy, existing identifiers and every report route. Rollout must prove access without deleting historical content.

## What to do

1. Add an access-matrix test suite for Free, active Plus, expired Plus and tier-only Plus.
2. Verify all report operations and direct routes.
3. Migrate/alias current `self` / `self_full` identifiers safely.
4. Decide and document read-after-expiry behavior for already generated Plus-only reports.
5. Run staging/production smoke with one Free and one active Plus account.
6. Record pre/post counts for reports, profiles and artifacts; do not delete generated content.

## Acceptance criteria

- [ ] Matrix tests cover every current report type and operation.
- [ ] Free basic report succeeds end-to-end.
- [ ] Free Plus-only direct access is denied without payload leakage.
- [ ] Active Plus Plus-only flow succeeds end-to-end.
- [ ] Expiry keeps basic access and removes Plus-only access at the boundary.
- [ ] Existing report/profile/artifact counts and identifiers are preserved.
- [ ] Read-after-expiry policy is no longer open.
- [ ] Live smoke results and deployed revision are recorded before closing E8.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_report_access_policy*.py tests/unit/test_astrotype_v2 tests/integration -q
cd ../frontend
npm test
npm run build
```
