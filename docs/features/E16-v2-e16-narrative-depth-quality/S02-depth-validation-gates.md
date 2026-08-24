# V2-E16 S02: Depth validation gates

## Status

✅ Готово

## Context

Prompt instructions alone are not enough. A model can return valid JSON with shallow prose. The segment validator must reject underdeveloped, generic or raw technical output.

This story adds quality gates to `segment_validation` and report assembly tests.

## What to do

1. Inspect `backend/app/modules/astrotype_v2/segment_validation.py` and report assembler quality gates.
2. Add per-section word-count and paragraph-count floors aligned with the depth contract.
3. Add required-depth-move checks where possible:
   - mechanism language;
   - lived manifestation;
   - tension/conflict/polarity;
   - protection/shadow/risk under pressure;
   - mature/integrated expression.
4. Add raw fact dump detection:
   - English placement/aspect dumps (`is in`, `with orb`, `house 10` style);
   - table-like sequences of placements/aspects;
   - repeated technical labels without interpretation.
5. Add generic-filler rejection patterns for phrases that claim depth but explain nothing.
6. Ensure validators do not reject a grounded valid section merely because it is long.
7. Ensure continuation-required segments are not treated as complete shallow sections.

## Files likely affected

| Path                                                              | Action                                                |
| ----------------------------------------------------------------- | ----------------------------------------------------- |
| `backend/app/modules/astrotype_v2/segment_validation.py`          | Add depth quality gates.                              |
| `backend/app/modules/astrotype_v2/report_assembler.py`            | Preserve or assert assembly-level quality guarantees. |
| `backend/tests/unit/test_astrotype_v2/test_segment_validation.py` | Add targeted validator tests.                         |
| `backend/tests/unit/test_astrotype_v2/test_report_assembler.py`   | Add report-level regression tests.                    |

## Acceptance criteria

- [x] Shallow 80-word sections fail validation.
- [x] Raw English fact dumps fail validation.
- [x] Generic horoscope filler fails validation.
- [x] Sections missing lived manifestation fail validation.
- [x] Sections missing protection/shadow or mature expression fail validation.
- [x] Long grounded sections pass validation.
- [x] `continuation_complete=false` is accepted only as an incomplete segment state, not as a complete report section.

## Verification commands

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_segment_validation.py tests/unit/test_astrotype_v2/test_report_assembler.py -v --tb=short
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q --tb=short
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```
