# V2-E4 S02: Seed aspect pair examples

## Status

✅ Реализовано

## Context

This story belongs to `V2-E4 — Reference data`.

Add canonical reference rows for examples like Mercury sextile Saturn and Mars opposition Uranus.

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
| `docs/features/E16-v2-e4-reference-data/` | Keep feature/story docs synchronized. |
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md` | Update if functional/API/data contract changes. |

## Acceptance criteria

- [x] Scope is implemented without crossing into unrelated v2 epics.
- [x] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [x] Canonical reference rows exist for Mercury sextile Saturn and Mars opposition Uranus.
- [x] Pair interpretations are versioned by `source_version` and can be enabled/disabled via `enabled`.
- [x] Additive migration updates only `astrotype_v2_aspect_pair_interpretations`.
- [x] Repository resolves only enabled pair interpretations from the v2 table.
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-06:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_reference_pair_data.py -q
cd backend && uv run alembic current
cd backend && pg_dump "$PG_DUMP_URL" > ../backups/astrotype_e4_s02_pre_migration_20260806_211816.sql
cd backend && uv run alembic upgrade head
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2 alembic/versions/a3b4c5d6e7f8_add_astrotype_v2_aspect_pair_enabled.py
cd backend && uv run mypy app/modules/astrotype_v2
```

Observed focused/local DB result:

```text
6 passed in 0.59s
backup ../backups/astrotype_e4_s02_pre_migration_20260806_211816.sql 61876 bytes
a3b4c5d6e7f8 (head)
astrotype_v2_aspect_pair_interpretations: 0
astrotype_v2_aspect_definitions: 0
users: 0
person_profiles: 0
reports: 0
report_versions: 0
report_narratives: 0
chart_snapshots: 0
enabled_column_exists: 1
```
