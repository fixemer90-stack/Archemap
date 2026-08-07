# V2-E5 S02: Extract aspect facts

## Status

✅ Реализовано

## Context

Create deterministic facts from v2 natal aspects and reference lookup.

## What to do

1. Add aspect fact extraction to the side-effect-free v2 fact extractor.
2. Resolve active versioned reference interpretation through V2-E4 lookup service.
3. Build deterministic fallback fact when reference data is missing, without legacy fallback.
4. Link evidence only to `astrotype_v2_natal_aspects`.

## Acceptance criteria

- [x] Scope is implemented without crossing into unrelated v2 epics.
- [x] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [x] Aspect facts canonicalize reversed body pairs before lookup.
- [x] Reference-backed facts include reference summary/keywords/source version in payload.
- [x] Missing reference rows still produce deterministic aspect facts with lower confidence.
- [x] Each aspect fact has evidence pointing to `astrotype_v2_natal_aspects`.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-06:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_aspect_fact_extractor.py tests/unit/test_astrotype_v2/test_placement_fact_extractor.py -q
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2
```

Observed focused result:

```text
6 passed in 0.82s
```
