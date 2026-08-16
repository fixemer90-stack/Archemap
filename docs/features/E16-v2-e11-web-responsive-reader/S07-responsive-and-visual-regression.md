# S07: Responsive and visual regression gates

## Status

⬜ Не начато

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

- [ ] DOM check verifies hero, section order and calculation layer.
- [ ] DOM check verifies forbidden markers are absent.
- [ ] Responsive/mobile conditions are documented or automated.

## Verification

```bash
cd frontend && node scripts/check-v2-report-reader-dom.mjs && npx eslint scripts/check-v2-report-reader-dom.mjs && npx prettier --check scripts/check-v2-report-reader-dom.mjs
```
