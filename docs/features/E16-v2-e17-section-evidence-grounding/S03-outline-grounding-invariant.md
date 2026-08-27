# S03: Enforce outline grounding invariant

## Status

⬜ Не начато

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

- [ ] `SectionRenderInputV2` for generated sections always has non-empty evidence ids.
- [ ] Ungrounded sections are explicitly `skipped` or `blocked`, not silently sent to LLM.
- [ ] Debug outline shows why each section is ready/bridged/skipped/blocked.
- [ ] Existing anti-duplication fields (`owned_theme_ids`, `reference_theme_ids`, `forbidden_theme_ids`) remain intact.

## Verification

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_outline.py tests/unit/test_astrotype_v2/test_segment_inputs.py -v --tb=short
uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```
