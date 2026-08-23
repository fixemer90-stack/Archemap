# V2-E16 S03: Deep synthesis inputs

## Status

⬜ Не начато

## Context

The LLM cannot consistently produce deep psychological prose from raw placements alone. If the deterministic layer only provides facts like “planet in sign/house” and “aspect with orb”, the model is forced to invent the missing interpretive bridge.

This story enriches deterministic synthesis so the prompt receives already-structured depth material.

## What to do

1. Inspect current fact extraction and synthesis payloads.
2. Extend synthesis theme contracts with depth fields where supported by evidence:
   - `psychological_mechanism`;
   - `lived_manifestation`;
   - `inner_tension`;
   - `protective_strategy`;
   - `immature_expression`;
   - `mature_expression`;
   - `integration_question`;
   - `evidence_strength`;
   - `contradictions` / `compensations`.
3. Add deterministic builders for at least the strongest themes first: core identity, mind, emotional regulation, agency, relationships and growth.
4. Keep every synthesized field grounded in evidence ids; do not invent evidence.
5. Update `SectionRenderInputV2` so the LLM sees the enriched theme payload.
6. Update debug outline renderer so engineers can inspect depth inputs before LLM calls.

## Files likely affected

| Path                                                          | Action                                          |
| ------------------------------------------------------------- | ----------------------------------------------- |
| `backend/app/modules/astrotype_v2/synthesis.py`               | Add richer theme construction.                  |
| `backend/app/modules/astrotype_v2/schemas.py`                 | Extend payload contracts if needed.             |
| `backend/app/modules/astrotype_v2/segment_inputs.py`          | Include depth fields in `SectionRenderInputV2`. |
| `backend/app/modules/astrotype_v2/outline.py`                 | Preserve/debug enriched theme payloads.         |
| `backend/tests/unit/test_astrotype_v2/test_synthesis.py`      | Add synthesis-depth tests.                      |
| `backend/tests/unit/test_astrotype_v2/test_segment_inputs.py` | Assert LLM inputs include depth fields.         |

## Acceptance criteria

- [ ] Each major section can receive at least one enriched theme when evidence supports it.
- [ ] Enriched fields retain evidence ids.
- [ ] `SectionRenderInputV2` exposes enriched theme fields to the LLM.
- [ ] Debug output lets engineers inspect mechanism/tension/protection/mature-expression data before provider calls.
- [ ] Tests prove enriched fields are deterministic and evidence-backed.

## Verification commands

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_synthesis.py tests/unit/test_astrotype_v2/test_segment_inputs.py -v --tb=short
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q --tb=short
cd backend && uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```
