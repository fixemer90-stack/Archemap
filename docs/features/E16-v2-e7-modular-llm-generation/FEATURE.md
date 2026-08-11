# V2-E7: Modular LLM generation

## Status

✅ Завершено

## Goal

Generate genuinely large, deep and expanded personality-section prose from builder-created `SectionRenderInputV2` JSON. The report must not be artificially shortened by product-level character caps, paragraph caps or “summary-style” prompt limits; section length is driven by owned evidence, section purpose and quality requirements.

## Core length/depth contract

Astrotype v2 reports are intended to be large and detailed.

Rules:

- Do not impose arbitrary `max_chars`, `max_paragraphs`, “short answer”, “brief summary” or hard section-size caps as product rules.
- Do not truncate valid prose just because it is long.
- Provider context/output limits are infrastructure constraints, not product requirements.
- If a provider cannot complete a section in one response, use continuation/chunking at the segment level and assemble the parts after validation.
- Completeness is judged by coverage of owned themes/evidence, specificity, coherence and non-duplication, not by being short.
- Validators may enforce minimum depth/coverage and maximum safety/runtime limits, but not a low content cap that makes the report shallow.

## Dependencies

V2-E6 outline; LLM provider infrastructure.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`

## Scope

This feature covers the `V2-E7` slice from `docs/ROADMAP-v2.md`.

In scope:

- `SectionRenderInputV2` JSON builder contract;
- prompt contracts for each upper personality section;
- segment runner lifecycle and persistence;
- continuation/chunking strategy for long sections;
- parsing/validation of LLM responses;
- retry of failed segments without rerunning the whole report.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Lower deterministic calculation-layer rendering. LLM does not write that layer.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [x] Each segment request is persisted.
- [x] Each segment output links to evidence ids.
- [x] Failed segments can be retried individually.
- [x] The report is not artificially length-capped; section completeness follows owned evidence.
- [x] Prompt contracts explicitly ask for deep, expanded, non-summary prose.
- [x] Segment runner supports continuation/chunking when provider output is cut by token limits.
- [x] Validators reject shallow/generic/underdeveloped sections, but do not reject a valid section merely because it is long.
- [x] Final assembly preserves long validated section text.

## Stories

| ID  | Story                                                               | Status       |
| --- | ------------------------------------------------------------------- | ------------ |
| S01 | [Build SectionRenderInputV2](./S01-section-render-inputs.md)        | ✅ Завершено |
| S02 | [Write segment prompt contracts](./S02-segment-prompt-contracts.md) | ✅ Завершено |
| S03 | [Implement segment runner](./S03-llm-segment-runner.md)             | ✅ Завершено |
| S04 | [Validate segment outputs](./S04-segment-validation.md)             | ✅ Завершено |

## Implementation order

```text
S01 → S02 → S03 → S04
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e7-modular-llm-generation docs/SRS/SRS-E16-astrotype-v2-cloud-core.md docs/architecture/astrotype-v2-natal-report-architecture.md docs/architecture/astrotype-v2-c4-architecture.md
```

For implementation stories, add targeted tests to the active story before marking it complete.

Implementation verification evidence:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_segment_inputs.py tests/unit/test_astrotype_v2/test_llm_segments.py -v --tb=short
cd backend && uv run pytest tests/unit/test_astrotype_v2 -v --tb=short
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run ruff format --check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2
git diff --check -- backend/app/modules/astrotype_v2 backend/tests/unit/test_astrotype_v2 docs/features/E16-v2-e7-modular-llm-generation
```
