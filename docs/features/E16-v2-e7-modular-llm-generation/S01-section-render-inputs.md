# V2-E7 S01: Build SectionRenderInputV2

## Status

⬜ Не начато

## Context

This story belongs to `V2-E7 — Modular LLM generation`.

Generate builder-created JSON inputs per upper personality section with owned facts/themes and allowed references only. The input must support long, deep prose generation by giving enough structured evidence and section intent, without sending the full unrestricted chart.

## What to do

1. Define `SectionRenderInputV2` schema.
2. Build one JSON input per upper personality section from `ReportOutlineV2`.
3. Include enough owned evidence for a genuinely expanded answer.
4. Include a depth contract that asks for full section coverage, not summary output.
5. Include continuation metadata so the runner can ask for the next part if provider output is cut.

## Required input fields

```text
section_id
section_title
section_purpose
owned_themes
reference_themes
forbidden_theme_ids
facts/evidence ids
already_explained summary
style_contract
depth_contract
continuation_policy
```

## Length/depth rules

- The builder must not add low `max_chars` / `max_paragraphs` product caps.
- The builder should describe desired depth as coverage requirements, not short limits.
- The builder may include provider/runtime hints such as continuation markers, but those are not content limits.

## Files likely affected

| Path | Action |
|---|---|
| `backend/app/modules/astrotype_v2/segment_inputs.py` | Build section JSON inputs. |
| `backend/app/modules/astrotype_v2/schemas.py` | Define `SectionRenderInputV2`. |
| `backend/tests/unit/test_astrotype_v2/` | Contract tests when implementation starts. |
| `docs/features/E16-v2-e7-modular-llm-generation/` | Keep feature/story docs synchronized. |

## Acceptance criteria

- [ ] One input JSON is produced per upper report section.
- [ ] Input contains owned/reference/forbidden theme boundaries.
- [ ] Input includes enough evidence for long section prose.
- [ ] Input contains a depth contract and continuation policy.
- [ ] No artificial low section-size cap is encoded in the input contract.
- [ ] v2 remains natal-only and does not depend on socionics/Model A/function strengths.

## Verification commands

Fill with targeted tests when implementation starts.
