# S03: Implement dashboard redesign

## Status

✅ Реализовано

## Context

The dashboard should feel like a personal report workspace, not a generic product grid. It must preserve current auth/session/profile behavior while improving the visual hierarchy.

Design direction:

- `docs/design/astrotype-v2-dashboard-sample.html`
- `docs/design/astrotype-v2-infographic-db-report-sample.html`

## What to do

1. Update `frontend/src/app/(dashboard)/dashboard/page.tsx`.
2. Preserve existing data behavior:
   - `bootstrapSession()` fallback;
   - `/api/v1/profiles` fetch;
   - links to `/report/v2/{profile.id}`;
   - product links.
3. Replace the current simple heading with a large personal workspace hero:
   - greeting by user name;
   - last/primary report path when profiles exist;
   - “build first chart” action when profiles are empty.
4. Redesign “Мои отчёты”:
   - report-style cards;
   - profile name/date/place;
   - clear primary action;
   - avoid tiny generic glass tiles.
5. Redesign product entry cards:
   - Self and Career visible as available;
   - Love/Child subdued as future directions;
   - copy should describe scenarios, not modules.
6. Add a calm account status/billing surface if account tier is available later; for now it can be static/placeholder-free or omitted.
7. Improve empty state:
   - one clear start action;
   - no confusing list of unavailable products first.

## Files likely affected

| Path                                                  | Action                                                           |
| ----------------------------------------------------- | ---------------------------------------------------------------- |
| `frontend/src/app/(dashboard)/dashboard/page.tsx`     | Main implementation                                              |
| `frontend/src/components/product-surface/`            | Use shared primitives if S01 creates them                        |
| `frontend/src/stores/auth-store.ts`                   | Read only unless account-tier API work is separately implemented |
| `frontend/scripts/check-product-surface-redesign.mjs` | Add dashboard checks in S05                                      |

## Acceptance criteria

- [x] Existing dashboard data loading still works.
- [x] If profiles exist, user sees a prominent path to the latest/first report.
- [x] Profile cards link to `/report/v2/{profile.id}`.
- [x] If profiles are empty, dashboard shows one clear “build first chart” path.
- [x] Product cards remain available/coming soon according to current product behavior.
- [x] Dashboard does not introduce account-tier gating.
- [x] User-facing copy avoids forbidden legacy/technical terms.
- [x] Mobile layout is readable without horizontal overflow.

## Verification

```bash
cd frontend
npx eslint .
npx prettier --check 'src/app/(dashboard)/dashboard/page.tsx'
npx tsc --noEmit
```

Runtime smoke when available:

```text
/dashboard with at least one profile
/dashboard with no profiles
```

## Implementation evidence

Implemented and verified with:

```bash
cd frontend
npm test
npx eslint .
npx prettier --check .
npx tsc --noEmit --pretty false
npm run build
```

Result: all commands passed; Next production build completed successfully.
