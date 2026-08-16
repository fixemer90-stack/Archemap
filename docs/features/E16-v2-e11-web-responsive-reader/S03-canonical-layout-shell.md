# S03: Canonical layout shell

## Status

⬜ Не начато

## Context

The current V2 page is a minimal card reader. It needs dedicated report components that follow the sample order and visual hierarchy.

## What to do

1. Create `V2ReportReader`, `V2ReportHero`, `V2NarrativeSectionCard`, and `V2ReportActions`.
2. Replace ready-state raw card list in `/report/v2/[profileId]` with `V2ReportReader`.
3. Keep loading/error states outside the ready-state report layout.
4. Keep calculation layer as a placeholder until S05.

## Files affected

| Action | Path                                                                     |
| ------ | ------------------------------------------------------------------------ |
| Modify | `frontend/src/app/(dashboard)/report/v2/[profileId]/page.tsx`            |
| Create | `frontend/src/components/astrotype-v2/report/V2ReportReader.tsx`         |
| Create | `frontend/src/components/astrotype-v2/report/V2ReportHero.tsx`           |
| Create | `frontend/src/components/astrotype-v2/report/V2NarrativeSectionCard.tsx` |
| Create | `frontend/src/components/astrotype-v2/report/V2ReportActions.tsx`        |

## Acceptance criteria

- [ ] Ready state begins with a hero cover.
- [ ] Narrative area follows the hero.
- [ ] Calculation layer placeholder follows narrative.
- [ ] No legacy report components are imported.

## Verification

```bash
cd frontend && npx eslint src/app/\(dashboard\)/report/v2/\[profileId\]/page.tsx src/components/astrotype-v2/report && npx prettier --check src/app/\(dashboard\)/report/v2/\[profileId\]/page.tsx src/components/astrotype-v2/report && npx tsc --noEmit
```
