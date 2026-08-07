# V2-E2: Database foundation

## Status

✅ Реализовано

## Goal

Create normalized PostgreSQL source-of-truth storage for v2 chart entities, references, facts, synthesis, outlines, LLM segment artifacts, infographics and final reports.

## Dependencies

V2-E1 contracts approved; Alembic/SQLAlchemy conventions understood.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## Scope

This feature covers the `V2-E2` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [x] Migrations are reversible.
- [x] Canonical chart/fact entities are queryable as rows, not only JSONB.
- [x] Redis is not used as durable report/fact storage.
- [x] Platform identity/profile/billing tables remain compatible and untouched by foundation migrations.
- [x] Legacy v1 product tables are not accidentally touched by foundation migrations; any purge is handled by a separate explicit cleanup runbook.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Create chart storage tables](./S01-create-chart-storage-tables.md) | ✅ Реализовано |
| S02 | [Create aspect reference tables](./S02-create-aspect-reference-tables.md) | ✅ Реализовано |
| S03 | [Create aspect and fact tables](./S03-create-aspect-and-fact-tables.md) | ✅ Реализовано |
| S04 | [Create synthesis/outline/report artifact tables](./S04-create-report-artifact-tables.md) | ✅ Реализовано |
| S05 | [Add v2 repository layer](./S05-add-repository-layer.md) | ✅ Реализовано |

## Implementation order

```text
S01 → S02 → S03 → S04 → S05
```

## Verification

Executed on 2026-08-05 after S05:

```bash
cd backend && python3 -m py_compile app/modules/astrotype_v2/__init__.py app/modules/astrotype_v2/models.py app/modules/astrotype_v2/repository.py tests/unit/test_astrotype_v2/test_repository.py
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py tests/unit/test_profile_service.py tests/unit/test_auth_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2 alembic/versions/f2a3b4c5d6e7_add_astrotype_v2_report_artifacts.py alembic/versions/e1f2a3b4c5d6_add_astrotype_v2_fact_storage.py alembic/versions/d0e1f2a3b4c5_add_astrotype_v2_foundation.py app/infrastructure/model_registry.py alembic/env.py
cd backend && uv run mypy app/modules/astrotype_v2
cd backend && uv run alembic current
git diff --check -- backend/app/modules/astrotype_v2 backend/tests/unit/test_astrotype_v2 docs/features/E16-v2-e2-database-foundation
```

Observed results:

```text
26 passed in 0.86s
31 passed, 7 warnings in 0.73s
All checks passed!
Success: no issues found in 3 source files
f2a3b4c5d6e7 (head)
```
