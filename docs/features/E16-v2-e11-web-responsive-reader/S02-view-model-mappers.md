# S02: Frontend view-model mappers

## Status

✅ Готово

## Context

UI components should consume a typed view-model, not raw nested API JSON. This keeps the reader maintainable and testable.

## What to do

1. Create `buildV2ReportReaderViewModel(apiPayload)`.
2. Map hero, six narrative sections, and calculation layer into typed props.
3. Add tests using sample-shaped and live-shaped payload fixtures.
4. Assert forbidden legacy markers are absent from mapped output.

## Files affected

| Action | Path                                                      |
| ------ | --------------------------------------------------------- |
| Create | `frontend/src/lib/astrotype-v2/report-view-model.ts`      |
| Create | `frontend/src/lib/astrotype-v2/report-view-model.test.ts` |
| Modify | `frontend/src/lib/api/astrotype-v2.ts`                    |

## Acceptance criteria

- [x] Mapper returns hero, narrative, calculation layer groups.
- [x] Canonical section order is stable.
- [x] Missing required deterministic data is visible to tests.
- [x] Forbidden typology markers are rejected.

## Verification

```bash
cd frontend && node scripts/check-v2-report-view-model.mjs
cd frontend && npx eslint src/lib/astrotype-v2/report-view-model.ts scripts/check-v2-report-view-model.mjs
cd frontend && rm -rf .next && npx tsc --noEmit --pretty false
cd frontend && npx prettier --check src/lib/astrotype-v2/report-view-model.ts scripts/check-v2-report-view-model.mjs package.json
cd frontend && npm test
```
