# Story E8.S05: Regression, migration and rollout proof

Status: 🟡 В процессе
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

- [x] Matrix tests cover every current report type and operation.
- [ ] Free basic report succeeds end-to-end.
- [x] Free Plus-only direct access is denied without payload leakage.
- [x] Active Plus Plus-only flow succeeds end-to-end.
- [x] Expiry keeps basic access and removes Plus-only access at the boundary.
- [ ] Existing report/profile/artifact counts and identifiers are preserved.
- [x] Read-after-expiry policy is no longer open.
- [ ] Live smoke results and deployed revision are recorded before closing E8.

## Read-after-expiry decision

Previously generated Plus-only reports remain stored but are locked on every protected read, download and regeneration operation after Plus expires. Renewal or an applicable grandfathered product-specific grant restores access to the same stored identifiers; expiry never deletes or rewrites the report.

## Migration strategy

E8 uses catalog aliases rather than a destructive data migration:

- persisted `self` report storage identifiers resolve to canonical `basic_natal`;
- commercial SKU `self_full` resolves to `basic_natal` for policy lookup;
- `self_full` is retired for new direct checkout so an account cannot be charged for access that is now basic;
- persisted `career` rows and `career_full` commercial history remain unchanged;
- no E8 Alembic migration rewrites report, profile or artifact identifiers.

## Local regression evidence

- `test_report_access_matrix.py` covers Free and active Plus decisions for every current catalog report, legacy basic aliases, the legacy Career SKU and safe locked metadata.
- Astrotype v2 and Career executable route inventories cover create/generate/status/read/calculation/segments/regenerate/versions/PDF operations.
- Subscription boundary tests and the consolidated report matrix prove exact-expiry and tier-only denial.
- Billing access now returns backend-computed `accessible_products`: canonical active monthly Plus exposes all plan products, while a grandfathered product grant exposes only that product and never masquerades as account-wide Plus.
- The PostgreSQL Career route matrix proves active Plus success, Free/expired `402`, foreign-owner `404`, grandfathered Career success, and preservation of the same profile/questionnaire/generation/report identifiers after access transitions.

## Verification evidence

```text
backend unit suite
  -> 699 passed
backend PostgreSQL integration suite
  -> 23 passed
focused PostgreSQL Career access/preservation matrix after final assertions
  -> 1 passed
ruff check / ruff format --check
  -> passed; 374 files formatted
mypy .
  -> success across 373 source files
frontend npm test
  -> all 15 contract scripts passed
frontend Playwright visual matrix
  -> 6 passed (desktop/tablet/mobile, light/dark)
frontend lint
  -> 0 errors; 2 pre-existing auth-navigation warnings
frontend production build
  -> compiled; TypeScript passed; 17/17 static pages generated
```

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_report_access_policy*.py tests/unit/test_astrotype_v2 tests/integration -q
cd ../frontend
npm test
npm run build
```
