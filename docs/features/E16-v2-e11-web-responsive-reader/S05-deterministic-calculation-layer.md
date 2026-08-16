# S05: Deterministic calculation layer

## Status

⬜ Не начато

## Context

The sample’s lower layer is required product UI, not a debug accordion. It must render from deterministic API data after the narrative.

## What to do

1. Implement key indicators, planet table, balance bars, house emphasis, aspect network, key aspects, and calculation matrix components.
2. Connect all components to view-model props.
3. Keep the layer compact and below narrative prose.
4. Do not compute chart facts in React.

## Files affected

| Action | Path                                                                     |
| ------ | ------------------------------------------------------------------------ |
| Create | `frontend/src/components/astrotype-v2/report/V2CalculationLayer.tsx`     |
| Create | `frontend/src/components/astrotype-v2/report/V2KeyIndicators.tsx`        |
| Create | `frontend/src/components/astrotype-v2/report/V2PlanetPositionsTable.tsx` |
| Create | `frontend/src/components/astrotype-v2/report/V2BalanceBars.tsx`          |
| Create | `frontend/src/components/astrotype-v2/report/V2HouseEmphasis.tsx`        |
| Create | `frontend/src/components/astrotype-v2/report/V2AspectNetwork.tsx`        |
| Create | `frontend/src/components/astrotype-v2/report/V2KeyAspectsTable.tsx`      |
| Create | `frontend/src/components/astrotype-v2/report/V2CalculationMatrix.tsx`    |

## Acceptance criteria

- [ ] All seven deterministic blocks render.
- [ ] Calculation layer appears after narrative.
- [ ] Missing required data fails tests or DOM checks.
- [ ] No standalone factual-basis dashboard is introduced.

## Verification

```bash
cd frontend && node scripts/check-v2-report-reader-dom.mjs && npx eslint src/components/astrotype-v2/report src/lib/astrotype-v2 && npx prettier --check src/components/astrotype-v2/report src/lib/astrotype-v2 && npx tsc --noEmit
```
