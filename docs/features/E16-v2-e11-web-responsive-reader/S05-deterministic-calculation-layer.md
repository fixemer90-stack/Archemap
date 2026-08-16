# S05: Deterministic calculation layer

## Status

✅ Готово

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

- [x] All seven deterministic blocks render.
- [x] Calculation layer appears after narrative.
- [x] Missing required data fails tests or DOM checks.
- [x] ASC and MC from house calculation are preserved as chart points for key indicators.
- [x] No standalone factual-basis dashboard is introduced.

## Regression notes

- 2026-08-16: fixed ASC/MC loss at source. `compute_houses()` returned ASC/MC, but `build_chart()` discarded them before v2 persistence, so `key_indicators.ascendant` could be `null` even though house 1 was available. Engine version was bumped to `0.1.5`; regenerated reports create a fresh v2 chart with `Ascendant` and `MC` in `astrotype_v2_natal_planet_positions`.

## Verification

```bash
cd frontend && node scripts/check-v2-report-reader-dom.mjs
cd frontend && npx prettier --check src/components/astrotype-v2/report/*.tsx src/components/astrotype-v2/report/format.ts scripts/check-v2-report-reader-dom.mjs package.json
cd frontend && npx eslint src/components/astrotype-v2/report/*.tsx src/components/astrotype-v2/report/format.ts scripts/check-v2-report-reader-dom.mjs
cd frontend && rm -rf .next && npx tsc --noEmit --pretty false
cd frontend && npm test
```
