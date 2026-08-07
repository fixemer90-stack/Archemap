# V2-E5 S01: Extract placement facts

## Status

✅ Реализовано

## Context

Create deterministic facts from v2 natal planet positions.

## What to do

1. Add a side-effect-free extractor for placement facts.
2. Convert each `NatalPlanetPosition` into one `NatalFact` and one `NatalFactEvidence` row.
3. Keep fact/evidence source links inside v2 tables only.
4. Verify with RED→GREEN tests and focused/broad gates.

## Acceptance criteria

- [x] Scope is implemented without crossing into unrelated v2 epics.
- [x] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [x] Each planet position creates a `placement` fact with stable key, title, payload, weight and section hint.
- [x] Each placement fact has evidence pointing to `astrotype_v2_natal_planet_positions`.
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-06:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_placement_fact_extractor.py -q
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2
```

Observed focused result:

```text
3 passed in 0.54s
```
