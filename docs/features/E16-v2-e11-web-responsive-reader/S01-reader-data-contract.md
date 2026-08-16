# S01: Reader data contract

## Status

⬜ Не начато

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

- [ ] API payload includes hero data.
- [ ] API payload includes ordered narrative section data.
- [ ] API payload includes deterministic calculation-layer data.
- [ ] Tests fail if required reader data disappears.
- [ ] No frontend-only astrology calculations are required.

## Verification

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py tests/unit/test_astrotype_v2/test_qa_smoke_rollout.py -q
```
