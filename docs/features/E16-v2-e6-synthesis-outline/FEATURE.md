# V2-E6: Synthesis & outline

## Status

✅ Завершено

## Goal

Turn facts into higher-level themes and assign each theme to report sections through deterministic ownership before LLM generation.

## Dependencies

V2-E5 persisted facts.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`

## Scope

This feature covers the `V2-E6` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [x] Every theme has exactly one owning section.
- [x] Reference and forbidden sections are explicit.
- [x] No LLM receives the full unrestricted fact set.
- [x] Outline can be persisted and regenerated deterministically.

## Stories

| ID  | Story                                                                   | Status       |
| --- | ----------------------------------------------------------------------- | ------------ |
| S01 | [Build synthesis model](./S01-build-synthesis-model.md)                 | ✅ Завершено |
| S02 | [Score and cluster themes](./S02-theme-scoring-clustering.md)           | ✅ Завершено |
| S03 | [Build ReportOutlineV2](./S03-build-report-outline.md)                  | ✅ Завершено |
| S04 | [Add debug deterministic outline view](./S04-debug-outline-renderer.md) | ✅ Завершено |

## Implementation order

```text
S01 → S02 → S03 → S04
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e6-synthesis-outline
```

For implementation stories, add targeted tests to the active story before marking it complete.

Implementation verification evidence:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_synthesis.py tests/unit/test_astrotype_v2/test_outline.py -v --tb=short
cd backend && uv run pytest tests/unit/test_astrotype_v2 -v --tb=short
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run ruff format --check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2
git diff --check -- backend/app/modules/astrotype_v2 backend/tests/unit/test_astrotype_v2 docs/features/E16-v2-e6-synthesis-outline
```
