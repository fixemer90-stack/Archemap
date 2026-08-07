# V2-E5 S03: Extract balance and pattern facts

## Status

✅ Реализовано

## Context

Create deterministic facts from v2 balance and pattern rows.

## What to do

1. Convert `NatalChartBalance` rows into `balance` facts.
2. Convert `NatalChartPattern` rows into `pattern` facts.
3. Link evidence only to v2 balance/pattern source tables.
4. Preserve side-effect-free extraction: no persistence in extractor.

## Acceptance criteria

- [x] Scope is implemented without crossing into unrelated v2 epics.
- [x] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [x] Balance facts have stable `balance:{category}:{key}` keys and v2 balance evidence.
- [x] Pattern facts have stable `pattern:{pattern_code}` keys and v2 pattern evidence.
- [x] Missing rank/weight values remain deterministic.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-06:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_balance_pattern_fact_extractor.py tests/unit/test_astrotype_v2/test_aspect_fact_extractor.py tests/unit/test_astrotype_v2/test_placement_fact_extractor.py -q
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2
```

Observed focused result:

```text
8 passed in 0.90s
```
