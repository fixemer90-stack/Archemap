# V2-E16 S05: Reader/PDF long-section preservation

## Status

⬜ Не начато

## Context

Even if the backend generates a deep section, the product can still feel shallow if the frontend or PDF layer truncates, collapses badly, creates unreadable walls of text, or silently drops paragraphs.

This story verifies that long validated sections remain readable and complete in web/PDF outputs.

## What to do

1. Inspect v2 reader rendering for narrative section paragraph handling.
2. Ensure paragraph splitting preserves blank-line-separated sections.
3. Ensure glossary wrapping does not corrupt text or match terms inside words.
4. Ensure long sections do not overflow cards or disappear on mobile widths.
5. If PDF export exists for v2, verify it preserves all paragraphs and does not cut after the first page/section.
6. Add sample long-section fixture aligned with `core_pattern` target length.
7. Add smoke checks that compare backend paragraph count to rendered paragraph count where practical.

## Files likely affected

| Path                                              | Action                                          |
| ------------------------------------------------- | ----------------------------------------------- |
| `frontend/src/components/astrotype-v2/report/`    | Preserve and render long section paragraphs.    |
| `frontend/src/lib/astrotype-v2/`                  | Ensure view-model mapping does not truncate.    |
| `frontend/scripts/check-v2-report-reader-dom.mjs` | Add reader markers/sanity checks.               |
| `frontend/tests/` or existing script tests        | Add long-section regression tests if available. |
| v2 PDF/export code if present                     | Preserve long sections in exported output.      |

## Acceptance criteria

- [ ] Web reader renders every paragraph from a long `core_pattern` section.
- [ ] View-model mapping does not truncate narrative body text.
- [ ] Glossary wrapping still respects word boundaries inside long prose.
- [ ] Mobile layout remains readable for long sections.
- [ ] PDF/export, if present, preserves full section text.
- [ ] Frontend checks include at least one long-section regression.

## Verification commands

```bash
cd frontend && npx prettier --check src/components/astrotype-v2/report src/lib/astrotype-v2 scripts/check-v2-report-reader-dom.mjs
cd frontend && npx eslint src/components/astrotype-v2/report
cd frontend && npx tsc --noEmit --pretty false
cd frontend && npm test
```
