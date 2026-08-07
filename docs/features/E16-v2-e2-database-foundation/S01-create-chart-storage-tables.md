# V2-E2 S01: Create chart storage tables

## Status

✅ Реализовано

## Context

This story belongs to `V2-E2 — Database foundation`.

Add migrations/models for `natal_charts`, `natal_planet_positions`, `natal_houses`, balances and patterns.

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
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

Implemented in:

- `backend/app/modules/astrotype_v2/models.py`
- `backend/alembic/versions/d0e1f2a3b4c5_add_astrotype_v2_foundation.py`
- `backend/tests/unit/test_astrotype_v2/test_models.py`
- `backend/tests/unit/test_astrotype_v2/test_migration_contract.py`

## Verification commands

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_models.py tests/unit/test_astrotype_v2/test_migration_contract.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2 alembic/versions/d0e1f2a3b4c5_add_astrotype_v2_foundation.py app/infrastructure/model_registry.py alembic/env.py
cd backend && uv run mypy app/modules/astrotype_v2
```
