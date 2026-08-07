# V2-E5 S04: Build fact evidence API shape

## Status

✅ Реализовано

## Context

Expose/shape deterministic fact evidence for report assembly and UI traceability.

## What to do

1. Build a serializable fact payload shape with grouped evidence rows.
2. Convert UUIDs to strings for API/report assembly consumers.
3. Reject non-v2 evidence source tables instead of silently leaking legacy references.
4. Keep view builder side-effect-free.

## Acceptance criteria

- [x] Scope is implemented without crossing into unrelated v2 epics.
- [x] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [x] Facts serialize with grouped evidence rows.
- [x] Evidence payload includes source table/id/key/payload.
- [x] Non-v2 evidence source tables are rejected.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-06:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_fact_evidence_view.py -q
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2
```

Observed focused result:

```text
3 passed in 0.59s
```
