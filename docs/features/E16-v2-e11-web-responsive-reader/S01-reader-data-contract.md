# S01: Reader data contract

## Status

✅ Готово

## Context

The canonical reader must not guess or calculate astrology in React. It needs a stable V2 API payload with hero, narrative, and deterministic calculation-layer data.

## What to do

1. Dump a live V2 report payload and compare it with `docs/design/astrotype-v2-infographic-db-report-data.json`.
2. Add or update backend contract tests for required reader fields.
3. If data is missing, add deterministic backend builder fields before frontend rendering.
4. Document the final API-to-reader field mapping.

## Files affected

| Action | Path                                                            |
| ------ | --------------------------------------------------------------- |
| Modify | `backend/app/modules/astrotype_v2/api_runtime.py`               |
| Modify | `backend/app/modules/astrotype_v2/infographic_data.py`          |
| Modify | `backend/app/modules/astrotype_v2/report_assembler.py`          |
| Test   | `backend/tests/unit/test_astrotype_v2/test_api_runtime.py`      |
| Test   | `backend/tests/unit/test_astrotype_v2/test_qa_smoke_rollout.py` |

## Acceptance criteria

- [x] API payload includes hero data.
- [x] API payload includes ordered narrative section data.
- [x] API payload includes deterministic calculation-layer data.
- [x] Tests fail if required reader data disappears.
- [x] No frontend-only astrology calculations are required.

## Verification

```bash
cd backend && python3 -m py_compile app/modules/astrotype_v2/report_assembler.py app/modules/astrotype_v2/infographic_data.py tests/unit/test_astrotype_v2/test_api_runtime.py tests/unit/test_astrotype_v2/test_infographic_data.py
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py::test_v2_report_payload_exposes_canonical_reader_hero_and_narrative_contract tests/unit/test_astrotype_v2/test_api_runtime.py::test_v2_infographic_payload_exposes_canonical_calculation_layer_contract tests/unit/test_astrotype_v2/test_infographic_data.py::test_build_natal_infographic_data_v2_matches_canonical_lower_layer_blocks -q
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py tests/unit/test_astrotype_v2/test_infographic_data.py tests/unit/test_astrotype_v2/test_report_assembler.py tests/unit/test_astrotype_v2/test_qa_smoke_rollout.py -q
cd backend && uv run ruff check app/modules/astrotype_v2/report_assembler.py app/modules/astrotype_v2/infographic_data.py tests/unit/test_astrotype_v2/test_api_runtime.py tests/unit/test_astrotype_v2/test_infographic_data.py
cd backend && uv run mypy app/modules/astrotype_v2/report_assembler.py app/modules/astrotype_v2/infographic_data.py
```
