# S02: Build section fact usage assignment

## Status

⬜ Не начато

## Context

The extractor currently labels facts by source type (`placements`, `aspects`, `balances`, `patterns`). Synthesis then maps those broad hints mostly to `core_pattern`. This loses semantic section coverage.

This Story adds an explicit assignment layer that maps each technical fact to one or more report-section usages.

## What to do

1. Introduce a deterministic section usage contract, for example `SectionFactUsageV2`.
2. Assign placement facts using planet/body, sign, house and angularity signals.
3. Assign aspect facts using both participants and aspect type.
4. Assign balance/pattern facts using element/modality/house/pattern dimensions.
5. Allow one technical fact to support multiple sections when justified.
6. Preserve stable source evidence ids; do not invent uncited evidence.
7. Add coverage diagnostics per section: owned usage count, evidence count, top reasons.

## Minimum assignment rules

Use the canonical rules in `docs/architecture/astrotype-v2-section-evidence-grounding.md`.

Examples:

- Mercury / Gemini / Virgo / 3rd house / Mercury aspects -> `perception_and_mind`.
- Moon / Cancer / water / 4th or 8th house / Moon aspects -> `emotional_regulation`.
- Mars / Sun / Aries / fire / 1st or 5th house -> `agency_and_desire`.
- Venus / Libra / Taurus / 7th or 8th house / Venus aspects -> `relationships_and_intimacy`.
- Saturn / Jupiter / MC / 9th, 10th or 12th house / strong patterns -> `growth_vector`.

## Files affected

| File | Action |
|---|---|
| `backend/app/modules/astrotype_v2/synthesis.py` | Add section usage assignment or delegate to a new module |
| `backend/app/modules/astrotype_v2/section_usage.py` | Preferred new module for assignment rules |
| `backend/tests/unit/test_astrotype_v2/test_fact_section_assignment.py` | Cover assignment rules and multi-section usage |

## Acceptance criteria

- [ ] Existing fact extraction remains deterministic and natal-only.
- [ ] Each generated `SynthesisThemeV2` has section-specific evidence usage.
- [ ] A realistic chart fixture gives non-zero coverage for all core MVP sections or marks explicit gaps.
- [ ] Multi-section usage is tested for cross-domain aspects such as Moon-Mercury and Venus-Mars.
- [ ] No socionics/typology/legacy report fields enter v2.

## Verification

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_fact_section_assignment.py -v --tb=short
uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2/test_fact_section_assignment.py
uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2/test_fact_section_assignment.py
```
