# V2-E7 S04: Validate segment outputs

## Status

⬜ Не начато

## Context

This story belongs to `V2-E7 — Modular LLM generation`.

Validate schema, evidence ids, forbidden themes, invented facts and shallow/generic prose. Validation must enforce quality and grounding without imposing an artificial maximum length on valid sections.

## Validation pipeline

```text
raw LLM response
→ parse as typed JSON
→ validate section_id
→ validate evidence ids
→ validate no forbidden theme expansion
→ validate no invented chart facts
→ validate depth/specificity/style
→ normalize
→ persist ready segment
```

## Depth validation

Validators should reject:

- empty output;
- generic horoscope prose;
- too few developed paragraphs for the section purpose;
- missing owned theme coverage;
- repeated filler;
- invented facts;
- forbidden themes;
- socionics/archetype/typology leakage.

Validators should not reject:

- long valid prose;
- many paragraphs when they are coherent and grounded;
- expanded explanations that stay within owned evidence.

Allowed length-related checks:

- minimum coverage/depth checks;
- provider/runtime safety checks;
- continuation completeness checks.

Disallowed as product validators:

- low `max_chars` section cap;
- low paragraph cap;
- truncation to fit UI card height;
- “summarize because section is too long”.

## Files likely affected

| Path | Action |
|---|---|
| `backend/app/modules/astrotype_v2/segment_validation.py` | Segment validation logic. |
| `backend/app/modules/astrotype_v2/schemas.py` | `ReportSegmentOutputV2` schema. |
| `backend/tests/unit/test_astrotype_v2/` | Validation tests when implementation starts. |

## Acceptance criteria

- [ ] Invalid JSON fails validation.
- [ ] Unknown evidence ids fail validation.
- [ ] Forbidden theme expansion fails validation.
- [ ] Invented chart facts fail validation.
- [ ] Shallow/generic sections fail validation.
- [ ] Long grounded sections pass validation.
- [ ] No artificial max-length validator is introduced.

## Verification commands

Fill with targeted validation tests when implementation starts.
