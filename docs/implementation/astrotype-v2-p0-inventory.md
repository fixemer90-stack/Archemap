# Astrotype v2 P0 inventory

Date: 2026-08-04
Last refreshed: 2026-08-05

Purpose: capture the actual runtime/codebase state before and during the first V2-E2 implementation slices. This document is an implementation preflight/readiness record, not a product spec.

---

## Decision summary

We can start v2 implementation with a separate `astrotype_v2` bounded context.

Do not rewrite platform auth/profile infrastructure. Reuse it.

Do not migrate old v1 product artifacts into v2.

Use the canonical v2 UI sample for report frontend work:

- `docs/design/astrotype-v2-infographic-db-report-sample.html`
- `docs/design/astrotype-v2-canonical-report-ui-contract.md`

The current product report/dashboard design is legacy reference only; it must not define the v2 report reader or calculation-layer layout.

Do not preserve old v1 reports/socionics artifacts as active product data unless a separate archive/export decision says so. They are purge candidates.

Preserve only:

- platform identity/access data: users, auth credentials, OAuth links, sessions/tokens where applicable;
- billing/subscription/entitlement data where applicable;
- current profile ownership and birth input needed by v2: birth date/time/place/timezone/coordinates;
- new v2 source-of-truth artifacts after they are created.

---

## Actual backend entrypoints

### App/router aggregation

- FastAPI app factory: `backend/app/main.py`
- Root API mount: `application.include_router(api_router, prefix="/api/v1")`
- v1 router aggregator: `backend/app/api/v1/__init__.py`

Currently registered under `/api/v1`:

- health
- auth
- users
- authorization
- catalog
- subscriptions
- billing
- payments
- webhooks
- reconciliation
- notifications
- admin
- profiles
- charts
- rules
- reports

V2 module status after first code slice:

- package exists: `backend/app/modules/astrotype_v2/`;
- current implementation includes SQLAlchemy models only;
- no v2 API router is registered yet;
- no frontend v2 route is implemented yet.

V2 router target:

- add a new module/router under `backend/app/modules/astrotype_v2/`;
- register only the v2 router under a clean namespace such as `/api/v1/astrotype-v2`;
- do not expose old `/reports` behavior as a v2 compatibility alias.

### Auth/profile platform layer to preserve

Auth router:

- `backend/app/modules/auth/router.py`
- prefix: `/auth`
- registration endpoint: `POST /api/v1/auth/register`
- OAuth profile completion endpoint: `POST /api/v1/auth/complete-profile`
- login/refresh/logout/password/email verification are already platform concerns.

Auth service:

- `backend/app/modules/auth/service.py`
- currently creates `User` and `PersonProfile` during registration;
- currently computes a chart snapshot and socionics during registration/profile completion.

Profile router:

- `backend/app/modules/profiles/router.py`
- prefix: `/profiles`
- profile CRUD stores `PersonProfile` birth input.

Profile model:

- `backend/app/modules/profiles/models.py`
- table: `person_profiles`
- fields needed by v2: `user_id`, `name`, `birth_date`, `birth_time`, `birth_time_accuracy`, `birth_place`, `latitude`, `longitude`, `timezone`.

User model:

- `backend/app/modules/users/models.py`
- table: `users`
- fields to preserve: `id`, `email`, `name`, `hashed_password`, `birth_date`, `is_active`, `is_verified`, `is_superuser`.

V2 integration rule:

- v2 may be triggered after registration/profile completion has enough birth input;
- auth/profile code should remain platform-owned;
- any socionics/chart side effect currently inside auth registration must be removed or bypassed for v2, but auth itself must not be replaced.

---

## Actual chart calculation entrypoints

Existing chart engine:

- `backend/app/chart_engine/chart.py` exposes `build_chart`;
- `backend/app/chart_engine/features.py` exposes `extract_features`;
- `backend/app/chart_engine/types.py` defines chart data types;
- `backend/app/chart_engine/socionics.py` is legacy v1/socionics and must not be imported by v2.

Existing chart service/router:

- `backend/app/modules/charts/service.py`
- `backend/app/modules/charts/router.py`
- router prefix: `/profiles/{profile_id}/chart`
- model: `backend/app/modules/charts/models.py`, table `chart_snapshots`.

Current risk:

- `ChartService` imports `evaluate_socionics` and writes `socionics` / `function_strengths`.
- `ChartSnapshot` schema/model contains `socionics` and `function_strengths`.
- Existing chart endpoints expose `socionics` and `function_strengths`.

V2 rule:

- reuse only pure natal chart calculation primitives (`build_chart`, chart types, safe deterministic calculations);
- do not import `app.chart_engine.socionics` from `astrotype_v2`;
- do not use `ChartSnapshot` as v2 source of truth;
- write normalized v2 natal tables instead.

---

## Actual legacy product/runtime artifacts

Current source scan on 2026-08-05 still shows legacy runtime/UI in the active codebase. This is expected during P0/V2-E2, but those paths must not be imported or rendered by v2:

- backend `socionics`: 85 matches in 13 Python files;
- backend `function_strength`: 27 matches in 7 Python files;
- backend `report_narratives`: 47 matches in 24 Python files;
- frontend `socionics`: 63 matches in 6 TypeScript/TSX files;
- frontend `function_strength`: 16 matches in 3 TypeScript/TSX files;
- legacy `TechnicalDetailsAccordion` references: 8 matches in 3 TSX files.

Backend purge / isolation candidates:

- `backend/app/chart_engine/socionics.py`
- `backend/app/modules/reports/`
- `backend/app/modules/report_narratives/`
- legacy chart payload fields: `socionics`, `function_strengths`
- legacy DB tables: `reports`, `report_versions`, `report_narratives`, `chart_snapshots` socionics/function fields
- legacy prompts under `backend/app/modules/report_narratives/prompts/`

Important: purge candidates are product artifacts, not platform identity/profile data.

Do not delete platform modules:

- `auth`
- `users`
- `profiles`
- `billing` / `subscriptions` / `payments` / `entitlements` where applicable
- `authorization`

Frontend purge / isolation candidates:

- `frontend/src/components/chart/socionics-result.tsx`
- `frontend/src/components/report/socionics-profile-simple.tsx`
- report view-model fields for `socionics` / `function_strengths`
- legacy report page `frontend/src/app/(dashboard)/report/[profileId]/page.tsx`
- product self page if it routes to legacy report behavior
- report components that render v1 archetype/socionics/career CTA behavior

V2 frontend rule:

- build a new progressive v2 reader path;
- use `docs/design/astrotype-v2-infographic-db-report-sample.html` as the visual source of truth;
- use `docs/design/astrotype-v2-canonical-report-ui-contract.md` as implementation contract for component/page structure;
- do not keep visible socionics/model-a blocks in v2 report UI;
- deterministic calculation layer is a report foundation, not a “factual basis dashboard”;
- do not adapt the current `/report/[profileId]` dashboard/report layout as the v2 visual design.

---

## Migration tooling and current revision chain

Migration tooling:

- Alembic config: `backend/alembic.ini`
- Alembic env: `backend/alembic/env.py`
- versions directory: `backend/alembic/versions/`
- SQLAlchemy metadata: `app.infrastructure.database.Base.metadata`

Known migration chain from files:

```text
b0f2a3b7fae2 initial_schema
→ 4b32a2d6a931 add_users_table
→ 563eb156e1f1 add_email_verification
→ 738693432883 add_password_resets_table
→ 9ad2219a9521 add_identity_links_table
→ a1b2c3d4e5f6 add_person_profiles_table
→ b2c3d4e5f6a7 add_chart_snapshots_table
→ c3d4e5f6a7b8 add_birth_date_to_users
→ d4e5f6a7b8c9 add_fields_to_chart_snapshots
→ e5f6a7b8c9d0 add_reports_tables
→ f6a7b8c9d0e1 add_name_to_users
→ a7b8c9d0e1f2 add_payments_tables
→ b8c9d0e1f2a3 add_report_narratives_table
→ c9d0e1f2a3b4 add_entitlements_table
→ d0e1f2a3b4c5 add_astrotype_v2_foundation
```

V2-E2 first migration now branches from the previous head and creates only new v2/reference tables. It must continue to avoid platform-table mutations in later revisions.

---

## Local environment/database preflight

### Local environment/database preflight on 2026-08-05

Observed without exposing secrets:

- config module: `backend/app/config.py`;
- backend `.env` exists with 47 keys, including `DATABASE_URL`, auth/OAuth, billing, S3, SMTP and frontend URL keys;
- repo-level `.env` exists with LLM keys only;
- effective backend settings through `uv run python`:
  - `APP_ENV=development`;
  - `DATABASE_URL=postgresql://[REDACTED]@localhost:5432/astrotype`;
  - `LLM_ENABLED=False`;
  - `LLM_PROVIDER=mock`;
- PostgreSQL port is reachable: `pg_isready -h localhost -p 5432` reports accepting connections.

Initial blocker:

- `uv run alembic current` was blocked by `asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "astrotype"`.

Resolution:

- PostgreSQL role/database access was repaired from `backend/.env` without exposing the password;
- direct psql through `DATABASE_URL` now returns `astrotype|astrotype`;
- pre-migration local snapshot created: `backend/../backups/astrotype_p0_pre_migration_20260805_222722.sql`;
- snapshot size: 911 bytes;
- initial local DB had no public tables and no `alembic_version`, so local dev data-loss risk was zero before migration;
- `uv run alembic upgrade head` completed successfully through `d0e1f2a3b4c5 add astrotype v2 foundation`;
- `uv run alembic current` now returns `d0e1f2a3b4c5 (head)`.

Post-migration local row-count preflight:

```text
identity: astrotype|astrotype
alembic_version: d0e1f2a3b4c5
table_count: 22
v2_table_count: 8
users: 0
person_profiles: 0
identity_links: 0
email_verifications: 0
password_resets: 0
payments: 0
payment_webhooks: 0
subscriptions: MISSING
entitlements: 0
reports: 0
report_versions: 0
report_narratives: 0
chart_snapshots: 0
astrotype_v2_aspect_definitions: 0
astrotype_v2_aspect_pair_interpretations: 0
astrotype_v2_natal_charts: 0
astrotype_v2_natal_planet_positions: 0
astrotype_v2_natal_houses: 0
astrotype_v2_natal_aspects: 0
astrotype_v2_natal_chart_balances: 0
astrotype_v2_natal_chart_patterns: 0
```

Note: `subscriptions` is listed as a preserve category, but no `subscriptions` table exists in the current local migration chain. Billing persistence currently observed in local schema is `payments`, `payment_webhooks` and `entitlements`.

---

## Data classification for implementation

### Preserve / reuse

- `users`
- auth/password/email verification/identity-link tables
- profile ownership and `person_profiles` birth input
- billing/payment/subscription/entitlement tables
- authorization tables

### Purge candidates after explicit inventory/runbook

- `reports`
- `report_versions`
- `report_narratives`
- old report PDFs/object-storage keys if any
- socionics/function-strength content in `chart_snapshots`
- frontend pages/components that expose socionics or legacy report UX

### New v2 source of truth

Create in V2-E2/V2-E3 and later slices:

- `aspect_definitions`
- `aspect_pair_interpretations`
- `natal_charts`
- `natal_planet_positions`
- `natal_houses`
- `natal_aspects`
- `natal_chart_balances`
- `natal_chart_patterns`
- `natal_facts`
- `natal_syntheses`
- `report_outlines`
- `report_segment_generations`
- `natal_reports`
- calculation-layer typed JSON/view-model storage

---

## First implementation slice status

The recommended tests-first V2-E2 S01/S02 tracer bullet has started and its first backend/model-storage step is implemented locally:

1. Added tests importing the new v2 models and asserting table names/columns/foreign-key isolation.
2. Observed RED failure while `app.modules.astrotype_v2` did not exist.
3. Added `backend/app/modules/astrotype_v2/` with model definitions only.
4. Registered v2 models in the Alembic metadata import path.
5. Added the first Alembic migration creating only reference + core natal chart tables.
6. Added migration-contract tests that reject destructive operations against platform/legacy tables.

Still not part of this slice:

- LLM;
- report assembly;
- frontend;
- API endpoints;
- old v1 purge scripts.

---

## P0 exit status

Completed:

- repo layout found;
- auth/profile entrypoints found;
- chart calculation entrypoints found;
- registered router aggregation found;
- migration tooling and current revision chain found;
- legacy v1 product/runtime candidates identified;
- platform data vs purge-candidate product data separated;
- canonical v2 report UI sample and implementation contract captured;
- first v2 backend package/migration status recorded after initial V2-E2 slice.

Remaining before production migration/purge:

- local dev DB preflight is complete and currently has zero user/platform/legacy rows;
- for any non-local target environment, run row-count/checksum preflight against that target before migration;
- confirm backup/snapshot mechanics for the target environment;
- run migrations/purge on staging/restored copy before production.
