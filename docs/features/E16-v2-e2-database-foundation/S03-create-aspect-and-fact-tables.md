# V2-E2 S03: Create aspect and fact tables

## Status

✅ Реализовано

## Context

This story belongs to `V2-E2 — Database foundation`.

Add `natal_aspects` and `natal_facts` with evidence source links.

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
- [x] `astrotype_v2_natal_facts` stores deterministic report-building facts as rows tied to v2 natal charts.
- [x] `astrotype_v2_natal_fact_evidence` links facts to deterministic source entities without FK to legacy reports/chart snapshots.
- [x] Migration is additive and creates only new `astrotype_v2_*` fact tables.
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-05:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_fact_models.py tests/unit/test_astrotype_v2/test_fact_migration_contract.py -q
cd backend && uv run alembic upgrade head
cd backend && uv run alembic current
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py tests/unit/test_profile_service.py tests/unit/test_auth_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2 alembic/versions/e1f2a3b4c5d6_add_astrotype_v2_fact_storage.py alembic/versions/d0e1f2a3b4c5_add_astrotype_v2_foundation.py app/infrastructure/model_registry.py alembic/env.py
cd backend && uv run mypy app/modules/astrotype_v2
```

Local DB migration evidence:

```text
BACKUP_CREATED=../backups/astrotype_e2_s03_pre_migration_20260805_225235.sql
39786 ../backups/astrotype_e2_s03_pre_migration_20260805_225235.sql
Running upgrade d0e1f2a3b4c5 -> e1f2a3b4c5d6, add astrotype v2 fact storage
e1f2a3b4c5d6 (head)
table_count: 24
v2_table_count: 10
users: 0
person_profiles: 0
reports: 0
report_versions: 0
report_narratives: 0
chart_snapshots: 0
astrotype_v2_natal_facts: 0
astrotype_v2_natal_fact_evidence: 0
```
