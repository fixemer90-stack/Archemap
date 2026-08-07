# V2-E2 S05: Add v2 repository layer

## Status

✅ Реализовано

## Context

This story belongs to `V2-E2 — Database foundation`.

Create async SQLAlchemy repositories that isolate persistence from domain builders.

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
- [x] Async SQLAlchemy repository accepts an injected `AsyncSession` and does not own transaction boundaries.
- [x] Repository query helpers target only `astrotype_v2_*` models/tables.
- [x] Repository save helpers add v2 model instances without legacy report/report_narrative/chart_snapshot fallback.
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-05:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_repository.py -q
cd backend && python3 -m py_compile app/modules/astrotype_v2/__init__.py app/modules/astrotype_v2/models.py app/modules/astrotype_v2/repository.py tests/unit/test_astrotype_v2/test_repository.py
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py tests/unit/test_profile_service.py tests/unit/test_auth_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2 alembic/versions/f2a3b4c5d6e7_add_astrotype_v2_report_artifacts.py alembic/versions/e1f2a3b4c5d6_add_astrotype_v2_fact_storage.py alembic/versions/d0e1f2a3b4c5_add_astrotype_v2_foundation.py app/infrastructure/model_registry.py alembic/env.py
cd backend && uv run mypy app/modules/astrotype_v2
cd backend && uv run alembic current
```
