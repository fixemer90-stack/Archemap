# S02: Implement homepage redesign

## Status

✅ Реализовано

## Context

The public homepage at `/` is visually outdated compared with the report reader. It should become the public cover of the product: calm, dark, report-like and clear about what Astrotype does.

Design direction:

- `docs/design/astrotype-v2-homepage-sample.html`
- `docs/design/astrotype-v2-infographic-db-report-sample.html`

## What to do

1. Replace the old compass/card landing structure in `frontend/src/app/page.tsx`.
2. Build a report-style hero:
   - eyebrow: Astrotype / natal report positioning;
   - main promise: not horoscope, personal portrait from the user's chart;
   - lead: birth data → calculated foundation → personal report;
   - primary CTA to registration;
   - secondary CTA to login or report-structure section.
3. Add a report-preview/proof block:
   - must visually resemble the report reader;
   - must be clearly illustrative, not a fake generated report for the current user.
4. Add a concise “what you get” section:
   - calculated chart basis;
   - synthesis;
   - personal report text.
5. Add a “how it works” section:
   - enter birth data;
   - backend/system calculates chart foundation;
   - report sections are produced from calculated facts.
6. Add a compact Free/Plus or final CTA section only if it supports the homepage flow.
7. Remove obsolete copy:
   - old archetype-first positioning;
   - socionics/Model A/MBTI mentions;
   - raw technical terms like v2/json/LLM/evidence ids.

## Files likely affected

| Path                                                  | Action                                    |
| ----------------------------------------------------- | ----------------------------------------- |
| `frontend/src/app/page.tsx`                           | Main implementation                       |
| `frontend/src/components/product-surface/`            | Use shared primitives if S01 creates them |
| `frontend/src/app/globals.css`                        | Only if shared global styles are needed   |
| `frontend/scripts/check-product-surface-redesign.mjs` | Add homepage checks in S05                |

## Acceptance criteria

- [x] `/` has a new report-style hero and no longer uses the old visual structure as the main design.
- [x] Primary CTA goes to `/register`.
- [x] Existing login path remains available.
- [x] Page explains the chain: birth data → calculated foundation → report.
- [x] Report-preview/proof section is illustrative and does not claim a real user report.
- [x] Page does not mention forbidden legacy/technical terms in user-facing copy.
- [x] Mobile layout stacks cleanly and keeps CTA visible.
- [x] Desktop layout uses the available width similarly to report samples.

## Verification

```bash
cd frontend
npx eslint .
npx prettier --check src/app/page.tsx
npx tsc --noEmit
```

When browser/runtime is available, inspect:

```text
/
```

At widths:

- 390px
- 768px
- 1440px
- 1920px

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
