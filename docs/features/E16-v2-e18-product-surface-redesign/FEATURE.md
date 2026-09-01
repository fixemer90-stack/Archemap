# V2-E18: Product surface redesign — homepage, dashboard, billing

## Status

⬜ Не начато

## Goal

Implement a refreshed Astrotype product surface so the public homepage, user dashboard and billing page visually belong to the same product as the canonical v2 report reader.

## Design direction sources

These files are concept/direction samples, not pixel-perfect implementation contracts:

- `docs/design/astrotype-v2-homepage-sample.html`
- `docs/design/astrotype-v2-dashboard-sample.html`
- `docs/design/astrotype-v2-billing-sample.html`
- `docs/design/astrotype-v2-infographic-db-report-sample.html`
- `docs/design/astrotype-v2-canonical-report-ui-contract.md`

The implementation should preserve the direction: wide dark report-style pages, large cover sections, gold accents, calm premium feel, narrative-first hierarchy and compact calculation/proof language. Exact copy, exact spacing and exact block order may change during implementation.

## Dependencies

- V2-E11 report reader visual language: `docs/features/E16-v2-e11-web-responsive-reader/FEATURE.md`
- Current frontend auth/session patterns in `frontend/src/app/(auth)` and `frontend/src/lib/auth-session.ts`
- Current dashboard route: `frontend/src/app/(dashboard)/dashboard/page.tsx`
- Current billing route: `frontend/src/app/(dashboard)/billing/page.tsx`
- Current homepage route: `frontend/src/app/page.tsx`
- Account tier foundation doc: `docs/architecture/account-tier-role-foundation.md`
- Payment confirmation doc: `docs/architecture/current-payment-confirmation-flow.md`

## Scope

- Shared visual surface primitives or local composition utilities for marketing/dashboard/billing pages.
- Public homepage redesign.
- Dashboard redesign.
- Billing page redesign.
- Copy cleanup to remove obsolete archetype/legacy language from these pages.
- Status-only Free/Plus presentation where useful; no account-tier feature gating in this feature.
- Frontend regression checks that protect the new visual/content direction.

## Out of scope

- Broad redesign of the canonical v2 report reader itself, beyond the small report-to-dashboard return action in S06.
- Implementing account-tier database fields or payment-to-plus role upgrade.
- Enforcing Free/Plus access restrictions.
- New billing/access API endpoints.
- Reworking auth/register/login pages.
- Implementing Love/Child/Career product functionality.
- Pixel-perfect copy of the static HTML samples.
- Introducing socionics, Model A, MBTI, function-strength radar/profile, or legacy archetype positioning.

## Product principles

1. The homepage is the cover of the product, not a generic SaaS landing page.
2. Dashboard is a personal report workspace, not a grid of unrelated modules.
3. Billing is a trust page: it explains what Plus means and how payment confirmation works.
4. Free/Plus can be displayed as account status, but must not restrict functionality until a later gating feature.
5. Technical terms such as v2/json/LLM/evidence ids should not leak into user-facing copy.
6. The report remains the visual source of truth: large dark cards, gold accents, narrative sections, compact calculation/proof blocks.

## Acceptance criteria

- [ ] Homepage `/` uses the new report-style direction and no longer looks like the old compass/card landing page.
- [ ] Homepage hero clearly communicates: birth data → calculated foundation → personal report.
- [ ] Homepage includes a report-preview/proof block that resembles the report reader language without pretending to be a real generated result.
- [ ] Dashboard `/dashboard` presents the user's workspace with a large personal hero and latest-report path before product cards.
- [ ] Dashboard keeps existing profile fetching and report links working.
- [ ] Dashboard empty state provides one clear start action for creating/opening Self.
- [ ] Billing `/billing` explains Free/Plus, YooKassa checkout and server-side payment confirmation in the new visual language.
- [ ] Billing does not imply that return from YooKassa equals successful payment.
- [ ] Billing can display account-tier/status copy, but does not gate features by account tier.
- [ ] Public/user-facing copy on these pages does not contain `v2/json`, `LLM`, `Model A`, `MBTI`, `function_strengths`, `socionics`, or raw `evidence ids` wording.
- [ ] Responsive behavior works at mobile, tablet and desktop widths.
- [ ] Frontend lint, format and TypeScript checks pass.
- [ ] A targeted visual/content regression script covers homepage, dashboard and billing markers.
- [ ] Report pages have a visible return action to `/dashboard` without losing standalone report focus.
- [ ] GitHub CI for pushed HEAD is green or any unrelated failure is documented precisely.

## Stories

| ID  | Story                                                                                   | Status       |
| --- | --------------------------------------------------------------------------------------- | ------------ |
| S01 | [Define shared product surface language](./S01-shared-product-surface-language.md)      | ⬜ Не начато |
| S02 | [Implement homepage redesign](./S02-homepage-redesign.md)                               | ⬜ Не начато |
| S03 | [Implement dashboard redesign](./S03-dashboard-redesign.md)                             | ⬜ Не начато |
| S04 | [Implement billing redesign](./S04-billing-redesign.md)                                 | ⬜ Не начато |
| S05 | [Add responsive/content regression gates](./S05-responsive-content-regression-gates.md) | ⬜ Не начато |
| S06 | [Add report-to-dashboard return action](./S06-report-dashboard-return-action.md)        | ⬜ Не начато |

## Implementation order

```mermaid
flowchart LR
  S01[S01 shared surface language] --> S02[S02 homepage]
  S01 --> S03[S03 dashboard]
  S01 --> S04[S04 billing]
  S02 --> S05[S05 regression gates]
  S03 --> S05
  S04 --> S05
  S05 --> S06[S06 report return action]
```

## Verification commands

```bash
cd frontend
npx eslint .
npx prettier --check .
npx tsc --noEmit
npm test
```

```bash
cd frontend
node scripts/check-product-surface-redesign.mjs
```

Optional browser smoke when local runtime is available:

```bash
cd frontend
npm run build
npm run start
# inspect /, /dashboard and /billing at mobile/tablet/desktop widths
```
