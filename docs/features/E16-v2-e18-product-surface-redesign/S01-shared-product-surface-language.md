# S01: Define shared product surface language

## Status

✅ Реализовано

## Context

Homepage, dashboard and billing currently share some colors with Astrotype, but they do not consistently feel like the canonical v2 report reader. Before changing individual routes, define a small shared visual/content language so the three pages do not drift into separate designs.

The static samples are direction references, not pixel-perfect contracts.

## What to do

1. Audit reusable frontend styling patterns:
   - `frontend/src/app/page.tsx`
   - `frontend/src/app/(dashboard)/dashboard/page.tsx`
   - `frontend/src/app/(dashboard)/billing/page.tsx`
   - shared UI components under `frontend/src/components/ui/`
   - global styles under `frontend/src/app/globals.css` if present.
2. Decide whether to extract shared components or keep route-local composition.
3. If extracting, create lightweight primitives only:
   - `ProductSurfaceShell`
   - `ProductSurfaceHero`
   - `ProductSurfaceCard`
   - `SurfaceEyebrow`
   - `SurfaceActionRow`
4. Keep existing app/session behavior unchanged.
5. Document the final implementation choice in this Story before marking it done.

## Files likely affected

| Path                                              | Action                                                       |
| ------------------------------------------------- | ------------------------------------------------------------ |
| `frontend/src/components/product-surface/`        | Create if shared primitives are useful                       |
| `frontend/src/app/page.tsx`                       | Later consumer                                               |
| `frontend/src/app/(dashboard)/dashboard/page.tsx` | Later consumer                                               |
| `frontend/src/app/(dashboard)/billing/page.tsx`   | Later consumer                                               |
| `frontend/src/app/globals.css`                    | Modify only if existing global utilities are the right place |

## Design requirements

- Use the report reader visual direction: wide dark surfaces, large cover blocks, gold accent, subtle blue/violet depth.
- Prefer long-form hierarchy over equal small cards.
- Avoid debug language in user-facing copy.
- Keep the product softer and narrative-first, not corporate SaaS.
- Do not use literal “премиальный” as a value claim.

## Acceptance criteria

- [x] Shared approach is chosen and implemented without over-abstracting.
- [x] The chosen primitives or route-local patterns can support homepage, dashboard and billing.
- [x] No route behavior changes are introduced by this story alone.
- [x] No user-facing copy contains forbidden technical/legacy terms.
- [x] Frontend lint/format/typecheck pass after this story.

## Verification

```bash
cd frontend
npx eslint .
npx prettier --check .
npx tsc --noEmit
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
