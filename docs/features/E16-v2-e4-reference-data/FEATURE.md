# V2-E4: Reference data

## Status

✅ Реализовано

## Goal

Create reusable versioned interpretation data for aspects and later planet/sign/house meanings so report meaning is not hardcoded in scattered Python dictionaries.

## Dependencies

V2-E2 reference tables.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## Scope

This feature covers the `V2-E4` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [x] Aspect type definitions are stored once.
- [x] Aspect pair meanings are versioned and can be enabled/disabled.
- [x] `Mercury sextile Saturn` and `Mars opposition Uranus` resolve from reference data.
- [x] No duplicate reversed planet-pair interpretations are required.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Seed aspect definitions](./S01-seed-aspect-definitions.md) | ✅ Реализовано |
| S02 | [Seed aspect pair examples](./S02-seed-aspect-pair-examples.md) | ✅ Реализовано |
| S03 | [Implement canonical planet order](./S03-canonical-planet-order.md) | ✅ Реализовано |
| S04 | [Build reference lookup service](./S04-reference-lookup-service.md) | ✅ Реализовано |

## Implementation order

```text
S01 → S02 → S03 → S04
```

## Verification

Executed on 2026-08-06 after S04:

```bash
cd backend && python3 -m py_compile app/modules/astrotype_v2/__init__.py app/modules/astrotype_v2/models.py app/modules/astrotype_v2/repository.py app/modules/astrotype_v2/reference_data.py app/modules/astrotype_v2/reference_lookup.py tests/unit/test_astrotype_v2/test_reference_lookup.py
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2 alembic/versions/a3b4c5d6e7f8_add_astrotype_v2_aspect_pair_enabled.py alembic/versions/f2a3b4c5d6e7_add_astrotype_v2_report_artifacts.py alembic/versions/e1f2a3b4c5d6_add_astrotype_v2_fact_storage.py alembic/versions/d0e1f2a3b4c5_add_astrotype_v2_foundation.py app/infrastructure/model_registry.py alembic/env.py
cd backend && uv run mypy app/modules/astrotype_v2
cd backend && uv run alembic current
git diff --check -- backend/app/modules/astrotype_v2 backend/tests/unit/test_astrotype_v2 docs/features/E16-v2-e4-reference-data
```

Observed results:

```text
55 passed in 1.43s
6 passed, 2 warnings in 0.34s
All checks passed!
Success: no issues found in 8 source files
a3b4c5d6e7f8 (head)
```
