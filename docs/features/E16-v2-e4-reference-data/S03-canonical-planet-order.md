# V2-E4 S03: Implement canonical planet order

## Status

✅ Реализовано

## Context

This story belongs to `V2-E4 — Reference data`.

Normalize symmetric aspect pairs so each interpretation is stored once.

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
- [x] Shared `CANONICAL_BODY_ORDER` defines stable planet/body ordering for v2 references.
- [x] `canonicalize_body_pair()` normalizes symmetric aspect pairs and preserves deterministic unknown-body tie-breaks.
- [x] Chart adapter and repository use the same canonicalizer, so reversed pair lookups do not require duplicate rows.
- [x] Behavior is backed by tests or documented verification evidence.
- [x] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Executed on 2026-08-06:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_reference_planet_order.py tests/unit/test_astrotype_v2/test_chart_adapter.py tests/unit/test_astrotype_v2/test_reference_pair_data.py -q
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run pytest tests/unit/test_chart_service.py -q
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2
```

Observed focused result:

```text
16 passed in 0.95s
```
