# V2-E3 S04: Reload chart contract from storage

## Status

✅ Реализовано

## Context

This story belongs to `V2-E3 — Natal chart adapter`.

Round-trip stored rows back into `NatalChartV2` for API/debug use.

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
| `docs/features/E16-v2-e3-natal-chart-adapter/` | Keep feature/story docs synchronized. |
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md` | Update if functional/API/data contract changes. |

## Acceptance criteria

- [x] Scope is implemented without crossing into unrelated v2 epics.
- [x] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [x] Repository can reload normalized v2 planet, house, aspect, balance and pattern rows by chart id.
- [x] `chart_contract.py` assembles a stable serializable contract from v2 rows for API/debug use.
- [x] Missing chart returns `None` instead of falling back to legacy storage.
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-05:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_chart_contract.py -q
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2
```

Observed focused result:

```text
4 passed in 0.52s
```
