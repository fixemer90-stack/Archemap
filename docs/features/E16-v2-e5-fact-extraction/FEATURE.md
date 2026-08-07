# V2-E5: Fact extraction

## Status

✅ Реализовано

## Goal

Extract deterministic natal facts from v2 normalized chart rows for downstream synthesis/report generation.

## Scope

- Build `astrotype_v2_natal_facts` rows from v2 chart entities.
- Build `astrotype_v2_natal_fact_evidence` rows pointing only to v2 source entities.
- Keep extraction natal-only and deterministic-first.
- Do not depend on socionics, Model A, legacy report narratives, or chart snapshot fallback.

## Out of scope

- LLM narrative generation.
- v1 report/archetype compatibility.
- Socionics or typology facts.

## Acceptance criteria

- [x] Placement facts are extracted from planet positions.
- [x] Aspect facts are extracted from natal aspects and reference lookup.
- [x] Balance/pattern facts are extracted from deterministic rows.
- [x] Fact evidence points only to v2 chart source tables.

## Stories

| Story | Title | Status |
|---|---|---|
| S01 | [Extract placement facts](./S01-extract-placement-facts.md) | ✅ Реализовано |
| S02 | [Extract aspect facts](./S02-extract-aspect-facts.md) | ✅ Реализовано |
| S03 | [Extract balance and pattern facts](./S03-extract-balance-pattern-facts.md) | ✅ Реализовано |
| S04 | [Build fact evidence API shape](./S04-fact-evidence-api-shape.md) | ✅ Реализовано |

## Verification

Executed on 2026-08-06 after S04:

```bash
cd backend && python3 -m py_compile app/modules/astrotype_v2/__init__.py app/modules/astrotype_v2/models.py app/modules/astrotype_v2/fact_extractor.py app/modules/astrotype_v2/fact_view.py tests/unit/test_astrotype_v2/test_fact_evidence_view.py
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2
cd backend && uv run alembic current
git diff --check -- backend/app/modules/astrotype_v2 backend/tests/unit/test_astrotype_v2 docs/features/E16-v2-e5-fact-extraction
```

Observed results:

```text
66 passed in 1.65s
6 passed, 2 warnings in 0.36s
All checks passed!
Success: no issues found in 10 source files
a3b4c5d6e7f8 (head)
```
