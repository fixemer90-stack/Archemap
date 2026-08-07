# Astrotype v2 V2-E2/S01 first implementation slice

Date: 2026-08-04

Scope: first code slice for `V2-E2: Database foundation`, story S01/S02 tracer bullet.

This slice must prove the v2 bounded context can add normalized source-of-truth tables without touching platform identity/profile/billing data or relying on legacy v1 report/socionics artifacts.

---

## Slice boundary

Implement only:

- new backend package `backend/app/modules/astrotype_v2/`;
- SQLAlchemy models for the initial v2 reference/chart-storage tables;
- Alembic model registration/import path;
- one Alembic migration creating the initial v2 tables;
- tests that fail before the package/models/migration exist and pass after implementation.

Do not implement yet:

- API router;
- frontend;
- LLM jobs;
- report assembly;
- fact extraction;
- synthesis;
- old v1 purge scripts.

---

## Proposed first table set

Start with stable foundations needed by later slices:

Reference tables:

- `astrotype_v2_aspect_definitions`
- `astrotype_v2_aspect_pair_interpretations`

Core chart tables:

- `astrotype_v2_natal_charts`
- `astrotype_v2_natal_planet_positions`
- `astrotype_v2_natal_houses`
- `astrotype_v2_natal_aspects`
- `astrotype_v2_natal_chart_balances`
- `astrotype_v2_natal_chart_patterns`

Prefixing with `astrotype_v2_` avoids collision with legacy generic names and makes leak/audit checks simple.

---

## Required table relationship policy

Foreign keys allowed:

- v2 chart rows may reference `users.id` and `person_profiles.id`;
- v2 child rows may cascade from their parent v2 natal chart row.

Foreign keys not allowed in this slice:

- no FK to `reports`;
- no FK to `report_versions`;
- no FK to `report_narratives`;
- no FK to `chart_snapshots`.

Data fields not allowed in v2 models:

- `socionics`;
- `function_strengths`;
- `model_a`;
- `NarrativeInput`;
- `archetype` as legacy product identity.

---

## TDD sequence

### RED 1 — package/model absence

Create a focused test file:

`backend/tests/unit/test_astrotype_v2/test_models.py`

Assertions:

- importing `app.modules.astrotype_v2.models` succeeds;
- required model classes exist;
- table names use `astrotype_v2_` prefix;
- model table columns do not contain forbidden v1/socionics names.

Run expected failing command before implementation:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_models.py -q
```

Expected initial failure: module/package missing.

### GREEN 1 — minimal models

Add:

- `backend/app/modules/astrotype_v2/__init__.py`
- `backend/app/modules/astrotype_v2/models.py`

Implement only SQLAlchemy model definitions and constants/enums needed by tests.

### RED 2 — Alembic registration/migration absence

Add focused tests for migration/model registration:

`backend/tests/unit/test_astrotype_v2/test_migration_contract.py`

Assertions:

- Alembic/model registry imports `app.modules.astrotype_v2.models`;
- newest v2 migration file exists;
- migration upgrade creates only `astrotype_v2_*` tables/indexes;
- migration script text does not include destructive operations against `users`, `person_profiles`, auth, billing, reports, report_versions, report_narratives or chart_snapshots.

Run expected failing command:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_migration_contract.py -q
```

Expected initial failure: no migration/registration.

### GREEN 2 — migration + registration

Add model import in Alembic path:

- `backend/alembic/env.py`, or preferably existing model registry if used consistently.

Add migration under:

- `backend/alembic/versions/<revision>_add_astrotype_v2_foundation.py`

Migration must contain only create/drop for new v2 tables. Downgrade may drop new v2 tables only.

---

## Verification commands for this slice

Focused:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_models.py -q
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_migration_contract.py -q
```

Nearby/broader backend checks:

```bash
cd backend && uv run pytest tests/unit/test_chart_service.py tests/unit/test_profile_service.py tests/unit/test_auth_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2 alembic/versions
cd backend && uv run mypy app/modules/astrotype_v2
```

Docs verification after status updates:

```bash
git diff --check -- docs/implementation/astrotype-v2-p0-inventory.md docs/implementation/astrotype-v2-e2-s01-first-slice.md docs/features/E16-v2-e2-database-foundation/FEATURE.md docs/ROADMAP-v2.md
```

---

## Slice exit criteria

- RED failures were observed before implementation.
- New v2 models exist under `app.modules.astrotype_v2`.
- First v2 migration exists and touches only new `astrotype_v2_*` tables.
- Existing auth/profile/billing/platform tables are not modified by the migration.
- Existing v1 product tables are not modified by the foundation migration.
- No v2 model/schema contains socionics/function-strength/model-a fields.
- Focused tests pass.
- Nearby auth/profile/chart regression tests pass or any pre-existing blocker is reported precisely.
