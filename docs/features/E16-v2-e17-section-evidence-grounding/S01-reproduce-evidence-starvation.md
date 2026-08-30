# S01: Reproduce current evidence starvation

## Status

⬜ Не закрыто

## Context

Production showed `SegmentValidationError("missing evidence ids")` in `astrotype_v2.generate_natal_report`. This Story creates a deterministic failing test that proves the root cause: the current pipeline can produce many technical facts overall while leaving several report sections with zero section-owned evidence.

## What to do

1. Add a unit test fixture that builds a realistic v2 fact set with placements, balances, aspects and optional patterns.
2. Run the current synthesis and outline builders.
3. Assert the current bad distribution:
   - most or all placement/balance/aspect facts map to `core_pattern`;
   - `growth_vector` may get only pattern facts;
   - at least one of `perception_and_mind`, `emotional_regulation`, `agency_and_desire`, `relationships_and_intimacy` has zero `evidence_ids`.
4. Add a runtime regression test that proves an empty-evidence `SectionRenderInputV2` would fail validation with `missing evidence ids`.
5. Keep this Story RED until S02/S03 introduce the semantic assignment and invariant checks.

## Files affected

| File | Action |
|---|---|
| `backend/tests/unit/test_astrotype_v2/test_fact_section_assignment.py` | Create failing coverage/assignment tests |
| `backend/tests/unit/test_astrotype_v2/test_segment_inputs.py` | Add empty-evidence guard regression if no dedicated test exists |
| `backend/app/modules/astrotype_v2/synthesis.py` | Read-only during S01 |
| `backend/app/modules/astrotype_v2/outline.py` | Read-only during S01 |

## Acceptance criteria

- [ ] Test demonstrates that total fact count can be high while section coverage is low.
- [ ] Test names the exact empty sections.
- [ ] Test proves empty evidence reaches the LLM/validator boundary in current code.
- [ ] No production fix is attempted in this Story.

## Verification

Expected before fix: targeted test fails with current evidence-starvation behavior documented.

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_fact_section_assignment.py -v --tb=short
```

## Audit note

Not closed in the 2026-08-30 documentation audit. The current code is already remediated, and `test_fact_section_assignment.py` now verifies the fixed distribution and skipped-section guard. This Story's original RED-only criteria required preserving a failing pre-fix reproduction of the old starvation behavior:

- high total fact count with low section coverage;
- exact empty sections from the old implementation;
- proof that empty evidence reached the LLM/validator boundary in the old implementation;
- no production fix in the same Story.

Those exact historical RED criteria are no longer present as a standalone failing test, so the Story should not be marked `✅` without either recovering the original RED evidence from history or rewriting this Story into a retrospective incident-reproduction contract.
