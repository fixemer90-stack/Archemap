# S02: Frontend view-model mappers

## Status

⬜ Не начато

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

- [ ] Mapper returns hero, narrative, calculation layer groups.
- [ ] Canonical section order is stable.
- [ ] Missing required deterministic data is visible to tests.
- [ ] Forbidden typology markers are rejected.

## Verification

```bash
cd frontend && npx eslint src/lib/astrotype-v2 && npx prettier --check src/lib/astrotype-v2 && npx tsc --noEmit && npm test -- report-view-model
```
