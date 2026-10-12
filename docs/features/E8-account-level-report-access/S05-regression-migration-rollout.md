# Story E8.S05: Regression, migration and rollout proof

Status: ✅ Готово
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
- [x] Free basic report succeeds end-to-end.
- [x] Free Plus-only direct access is denied without payload leakage.
- [x] Active Plus Plus-only flow succeeds end-to-end.
- [x] Expiry keeps basic access and removes Plus-only access at the boundary.
- [x] Existing report/profile/artifact counts and identifiers are preserved.
- [x] Read-after-expiry policy is no longer open.
- [x] Live smoke results and deployed revision are recorded before closing E8.

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
- Astrotype v2, Career and mounted legacy `/reports` executable route inventories cover create/generate/list/status/read/calculation/segments/regenerate/versions/PDF operations.
- Subscription boundary tests and the consolidated report matrix prove exact-expiry and tier-only denial.
- Direct grandfathered grants require `starts_at <= now < expires_at` when bounded; subscription-backed grants do not receive direct-purchase grandfathering or `past_due` grace.
- Billing access now returns backend-computed `accessible_products`: canonical active monthly Plus exposes all plan products, while a grandfathered product grant exposes only that product and never masquerades as account-wide Plus.
- The PostgreSQL Career route matrix proves active Plus success, Free/expired `402`, foreign-owner `404`, grandfathered Career success, and preservation of the same profile/questionnaire/generation/report identifiers after access transitions.
- The PostgreSQL legacy-report matrix proves Free can read/list basic `self` data while a persisted `love` payload is denied with safe `402` metadata and omitted from list results.

## Verification evidence

```text
backend unit suite
  -> 709 passed
backend PostgreSQL integration suite
  -> 24 passed
focused PostgreSQL Career access/preservation matrix after final assertions
  -> 1 passed
focused PostgreSQL legacy /reports access matrix
  -> 1 passed
ruff check / ruff format --check
  -> passed; 377 files formatted
mypy .
  -> success across 376 source files
frontend npm test
  -> all 15 contract scripts passed
frontend Playwright visual matrix
  -> 6 passed (desktop/tablet/mobile, light/dark)
frontend lint
  -> 0 errors; 2 pre-existing auth-navigation warnings
frontend production build
  -> compiled; TypeScript passed; 17/17 static pages generated
```

## Staging rollout evidence — 2026-10-12

- Exact green code revision: `67e439b8ac6d69cce1cb7f8171b2c4df5656d316`; GitHub Actions CI run `38280767131` completed successfully across all seven jobs.
- Staging deploy marker was written and read back as `67e439b8ac6d69cce1cb7f8171b2c4df5656d316` with scope `release:main-full`; production marker remained `7160dffc3217e041d6a9afa5af294c84601c8d66`.
- PostgreSQL revision remained `f1a2b3c4d5e6`; no E8 migration was introduced.
- A non-empty pre-rollout PostgreSQL dump was created and checksum-verified before extraction.
- Pre/post snapshots matched byte-for-byte: users `7`, profiles `7`, legacy reports `0`, Career reports `13`, entitlements `8`; identifier-set hashes were unchanged for every table.
- Authenticated backend smoke returned `200` for a Free-owned basic Astrotype v2 report, Free legacy report listing, a direct-grandfathered Career report, an active-Plus Career report and both billing-access reads.
- Direct-grandfathered billing remained `account_tier=free` and exposed only `career`; active canonical Plus exposed `self`, `career`, `love` and `child`.
- The live OpenAPI document contained the canonical Astrotype v2/Career routes and mounted legacy `/api/v1/reports` create/list/read/PDF/version routes.
- Public boundary smoke: staging without Basic Auth `401`, authenticated staging health `200`, app-protected billing without app session `401`, production health/root `200`, and staging `noindex` header present.
- Backend health, worker ping, logs and service readiness passed; temporary build swap and uploaded rollout scripts/archive were removed after acceptance.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_report_access_policy*.py tests/unit/test_astrotype_v2 tests/integration -q
cd ../frontend
npm test
npm run build
```
