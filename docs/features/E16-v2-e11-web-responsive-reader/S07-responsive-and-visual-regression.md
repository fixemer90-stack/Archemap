# S07: Responsive and visual regression gates

## Status

✅ Готово

## Context

Canonical structure must be automatically checked so the reader does not regress into generic cards again.

## What to do

1. Add DOM/static regression script for canonical markers.
2. If browser tooling is available, add screenshot/DOM smoke for desktop and mobile widths.
3. Wire a package script if useful.
4. Keep checks independent of private user data.

## Files affected

| Action        | Path                                              |
| ------------- | ------------------------------------------------- |
| Create/Modify | `frontend/scripts/check-v2-report-reader-dom.mjs` |
| Modify        | `frontend/package.json`                           |

## Acceptance criteria

- [x] DOM check verifies hero, section order and calculation layer.
- [x] DOM check verifies forbidden markers are absent.
- [x] Responsive/mobile conditions are documented or automated.

## Verification

```bash
cd frontend && node scripts/check-v2-report-reader-dom.mjs
cd frontend && npx eslint src/components/astrotype-v2/report/*.tsx src/components/astrotype-v2/report/format.ts scripts/check-v2-report-reader-dom.mjs
cd frontend && npx prettier --check src/components/astrotype-v2/report/*.tsx src/components/astrotype-v2/report/format.ts scripts/check-v2-report-reader-dom.mjs package.json
cd frontend && npm test
```
