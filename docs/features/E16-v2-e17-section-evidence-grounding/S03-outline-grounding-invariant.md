# S03: Enforce outline grounding invariant

## Status

✅ Реализовано

## Context

`ReportOutlineV2` currently creates all six sections even when some sections have no owned facts or evidence. The LLM runtime must never receive a section input with `evidence_ids=[]` unless the section is explicitly skipped and not generated.

This Story adds section-level grounding statuses and invariant checks before segment generation.

## What to do

1. Extend `SectionPlanV2` or a companion diagnostic payload with grounding metadata.
2. Compute per-section:
   - owned theme count;
   - owned evidence count;
   - reference evidence count;
   - bridge evidence count;
   - grounding status;
   - grounding reason.
3. Define behavior for each status:
   - `ready`: generate normally;
   - `bridged`: generate with allowed bridge/reference evidence;
   - `skipped`: do not call LLM;
   - `blocked`: fail before LLM with actionable diagnostic.
4. Update `build_section_render_inputs_v2` so it cannot emit impossible generation inputs silently.
5. Add tests for ready, bridged, skipped and blocked sections.

## Files affected

| File | Action |
|---|---|
| `backend/app/modules/astrotype_v2/outline.py` | Add grounding metadata/statuses |
| `backend/app/modules/astrotype_v2/segment_inputs.py` | Enforce no impossible LLM inputs |
| `backend/app/modules/astrotype_v2/schemas.py` | Add public/debug contract fields if needed |
| `backend/tests/unit/test_astrotype_v2/test_outline.py` | Coverage for grounding statuses |
| `backend/tests/unit/test_astrotype_v2/test_segment_inputs.py` | Coverage for blocked/skipped section inputs |

## Acceptance criteria

- [x] `SectionRenderInputV2` for generated sections always has non-empty evidence ids.
- [x] Ungrounded sections are explicitly `skipped` or `blocked`, not silently sent to LLM.
- [x] Debug outline shows why each section is ready/bridged/skipped/blocked.
- [x] Existing anti-duplication fields (`owned_theme_ids`, `reference_theme_ids`, `forbidden_theme_ids`) remain intact.

## Verification

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_outline.py tests/unit/test_astrotype_v2/test_segment_inputs.py -v --tb=short
uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```

Fresh audit verification on 2026-08-30:

```bash
uv run pytest tests/unit/test_astrotype_v2/test_fact_section_assignment.py tests/unit/test_astrotype_v2/test_outline.py tests/unit/test_astrotype_v2/test_segment_inputs.py tests/unit/test_astrotype_v2/test_report_assembler.py::test_build_deterministic_natal_report_row_exposes_calculation_layer_before_segments tests/unit/test_astrotype_v2/test_worker_runtime.py tests/unit/test_astrotype_v2/test_api_runtime.py -q
```

Result: `25 passed`. `outline.py` emits `grounding_status`, owned/reference evidence counts, and `owned_theme_ids` / `reference_theme_ids` / `forbidden_theme_ids`; `segment_inputs.py` excludes skipped sections and only emits generated inputs with evidence ids.
