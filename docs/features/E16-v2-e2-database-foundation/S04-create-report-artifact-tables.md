# V2-E2 S04: Create synthesis/outline/report artifact tables

## Status

✅ Реализовано

## Context

This story belongs to `V2-E2 — Database foundation`.

Add `natal_syntheses`, `report_outlines`, `report_segment_generations`, `natal_infographic_data`, `natal_reports`.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## What to do

1. Read the related architecture and roadmap documents.
2. Inspect existing code/docs relevant to this boundary before implementation.
3. Implement only the scope of this story.
4. Add or update tests/documentation for the changed contract.
5. Verify with targeted commands and record the evidence in this story when work starts.

## Files likely affected

| Path | Action |
|---|---|
| `backend/app/modules/astrotype_v2/` | Add/update v2 backend module code when implementation starts. |
| `docs/features/E16-v2-e2-database-foundation/` | Keep feature/story docs synchronized. |
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md` | Update if functional/API/data contract changes. |

## Acceptance criteria

- [x] Scope is implemented without crossing into unrelated v2 epics.
- [x] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [x] `astrotype_v2_natal_syntheses` stores deterministic synthesis rows tied to v2 natal charts.
- [x] `astrotype_v2_report_outlines` stores deterministic report outline/section plans.
- [x] `astrotype_v2_report_segment_generations` stores async LLM section-generation artifacts separately from deterministic rows.
- [x] `astrotype_v2_natal_infographic_data` stores canonical sample calculation-layer payloads.
- [x] `astrotype_v2_natal_reports` stores versioned final/progressive report artifacts with deterministic and narrative payloads separated.
- [x] Migration is additive and creates only new `astrotype_v2_*` artifact tables.
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-05:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_report_artifact_models.py tests/unit/test_astrotype_v2/test_report_artifact_migration_contract.py -q
cd backend && uv run alembic upgrade head
cd backend && uv run alembic current
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py tests/unit/test_profile_service.py tests/unit/test_auth_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2 alembic/versions/f2a3b4c5d6e7_add_astrotype_v2_report_artifacts.py alembic/versions/e1f2a3b4c5d6_add_astrotype_v2_fact_storage.py alembic/versions/d0e1f2a3b4c5_add_astrotype_v2_foundation.py app/infrastructure/model_registry.py alembic/env.py
cd backend && uv run mypy app/modules/astrotype_v2
```

Local DB migration evidence:

```text
BACKUP_CREATED=../backups/astrotype_e2_s04_pre_migration_20260805_231420.sql
45071 ../backups/astrotype_e2_s04_pre_migration_20260805_231420.sql
Running upgrade e1f2a3b4c5d6 -> f2a3b4c5d6e7, add astrotype v2 report artifacts
f2a3b4c5d6e7 (head)
table_count: 29
v2_table_count: 15
users: 0
person_profiles: 0
reports: 0
report_versions: 0
report_narratives: 0
chart_snapshots: 0
astrotype_v2_natal_syntheses: 0
astrotype_v2_report_outlines: 0
astrotype_v2_report_segment_generations: 0
astrotype_v2_natal_infographic_data: 0
astrotype_v2_natal_reports: 0
```
