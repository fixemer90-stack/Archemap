# S04: Narrative section rendering

## Status

⬜ Не начато

## Context

Narrative sections must match the canonical information architecture instead of generic cards.

## What to do

1. Render numeric eyebrow, title, subtitle/tag, prose paragraphs, and aside bullets.
2. Enforce canonical six-section order.
3. Add stable DOM markers for regression checks.
4. Handle partial generation without changing ready-state structure.

## Files affected

| Action        | Path                                                                     |
| ------------- | ------------------------------------------------------------------------ |
| Modify        | `frontend/src/components/astrotype-v2/report/V2NarrativeSectionCard.tsx` |
| Modify        | `frontend/src/lib/astrotype-v2/report-view-model.ts`                     |
| Create/Modify | `frontend/scripts/check-v2-report-reader-dom.mjs`                        |

## Acceptance criteria

- [ ] `01 · ядро личности` through `06 · вектор роста` render in order.
- [ ] Each section has prose and optional aside bullets.
- [ ] DOM regression fails on missing/reordered sections.

## Verification

```bash
cd frontend && node scripts/check-v2-report-reader-dom.mjs && npx eslint src/components/astrotype-v2/report src/lib/astrotype-v2 scripts/check-v2-report-reader-dom.mjs && npx prettier --check src/components/astrotype-v2/report src/lib/astrotype-v2 scripts/check-v2-report-reader-dom.mjs && npx tsc --noEmit
```
