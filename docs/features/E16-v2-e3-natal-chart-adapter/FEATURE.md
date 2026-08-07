# V2-E3: Natal chart adapter

## Status

✅ Реализовано

## Goal

Convert existing chart-engine output into clean v2 normalized contracts and rows without socionics or function-strength concepts.

## Dependencies

V2-E2 tables/repositories; existing chart engine.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## Scope

This feature covers the `V2-E3` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [x] A known profile produces complete v2 chart rows.
- [x] No v2 adapter imports socionics/function strengths.
- [x] Mars/Taurus/10/retrograde style data is stored as structured rows.
- [x] Chart rows can be reloaded into a stable v2 contract.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Inspect current chart output](./S01-inspect-chart-engine-output.md) | ✅ Реализовано |
| S02 | [Build chart adapter](./S02-build-chart-adapter.md) | ✅ Реализовано |
| S03 | [Persist normalized chart rows](./S03-persist-normalized-chart.md) | ✅ Реализовано |
| S04 | [Reload chart contract from storage](./S04-reload-chart-contract.md) | ✅ Реализовано |

## Implementation order

```text
S01 → S02 → S03 → S04
```

## Verification

Executed on 2026-08-05 after S04:

```bash
cd backend && python3 -m py_compile app/modules/astrotype_v2/__init__.py app/modules/astrotype_v2/models.py app/modules/astrotype_v2/repository.py app/modules/astrotype_v2/chart_adapter.py app/modules/astrotype_v2/chart_persistence.py app/modules/astrotype_v2/chart_contract.py tests/unit/test_astrotype_v2/test_chart_contract.py
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2 alembic/versions/f2a3b4c5d6e7_add_astrotype_v2_report_artifacts.py alembic/versions/e1f2a3b4c5d6_add_astrotype_v2_fact_storage.py alembic/versions/d0e1f2a3b4c5_add_astrotype_v2_foundation.py app/infrastructure/model_registry.py alembic/env.py
cd backend && uv run mypy app/modules/astrotype_v2
cd backend && uv run alembic current
git diff --check -- backend/app/modules/astrotype_v2 backend/tests/unit/test_astrotype_v2 docs/features/E16-v2-e3-natal-chart-adapter
```

Observed results:

```text
37 passed in 0.91s
6 passed, 2 warnings in 0.35s
All checks passed!
Success: no issues found in 6 source files
f2a3b4c5d6e7 (head)
```
