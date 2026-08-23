# V2-E16 S01: Depth prompt contracts

## Status

⬜ Не начато

## Context

Current `build_segment_prompt()` requires “deep, expanded, specific prose”, but the concrete minimum is only 3 paragraphs / 80 words. That lets a segment pass while still feeling poor.

This story upgrades the prompt contract from a weak generic instruction to section-specific depth requirements.

## What to do

1. Read `docs/architecture/astrotype-v2-narrative-depth-contract.md`.
2. Update `backend/app/modules/astrotype_v2/llm_segments.py` or split prompt templates under `backend/app/modules/astrotype_v2/prompts/`.
3. Replace the product-depth minimum with section-specific requirements:
   - `core_pattern`: 700–1200 words, 6–9 paragraphs;
   - other upper sections: 450–900 words, 4–7 paragraphs.
4. Keep a separate technical emptiness floor only for malformed/empty response detection.
5. Add section-specific instructions for:
   - central formula;
   - mechanism;
   - lived manifestation;
   - inner tension;
   - protection/shadow;
   - mature expression;
   - self-check/integration cue where appropriate.
6. Ensure retry prompt text does not collapse the quality bar back to “at least 80 words”.
7. Keep forbidden constraints: no socionics, no Model A, no typology labels, no deterministic calculation layer, no invented facts.

## Files likely affected

| Path                                                         | Action                                                            |
| ------------------------------------------------------------ | ----------------------------------------------------------------- |
| `backend/app/modules/astrotype_v2/llm_segments.py`           | Update prompt construction and retry prompt.                      |
| `backend/app/modules/astrotype_v2/prompts/`                  | Add templates if prompts are split out.                           |
| `backend/tests/unit/test_astrotype_v2/test_llm_segments.py`  | Add prompt contract tests.                                        |
| `docs/architecture/astrotype-v2-narrative-depth-contract.md` | Keep product contract synchronized if prompt requirements change. |

## Acceptance criteria

- [ ] Prompt says this is not a broad overview.
- [ ] Prompt says to write a deep psychological reading of one section.
- [ ] `core_pattern` has 700–1200 word / 6–9 paragraph target.
- [ ] Other upper sections have 450–900 word / 4–7 paragraph target.
- [ ] Prompt requires mechanism, lived manifestation, tension, protection/shadow and mature expression.
- [ ] Prompt forbids placement/aspect summaries as the section structure.
- [ ] Retry prompt preserves the same depth contract.
- [ ] Unit tests assert these prompt markers.

## Verification commands

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_llm_segments.py -v --tb=short
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```
