# Story E8.S04: Frontend account-level report UX

Status: ✅ Готово
Feature: [E8 Account-level report access](./FEATURE.md)
Architecture: [Account levels and report access policy](../../architecture/account-levels-report-access-policy.md)

## Context

The UI currently describes the personal report as closed when Plus is inactive. Under the target policy, the basic report remains available and only other reports should carry a Plus lock.

## What to do

1. Show the basic report as available for Free and Plus accounts.
2. Label every non-basic report card as Plus-only when access is inactive.
3. Render backend-owned locked state and billing CTA without hiding protected payload client-side.
4. Update dashboard/billing copy so it does not say the basic/full personal report is closed for Free.
5. Show that basic access remains after Plus expiry.

## Acceptance criteria

- [x] Basic report CTA works for Free and Plus.
- [x] Non-basic report cards clearly say `Доступно с Plus` when locked.
- [x] Billing copy says `Базовый отчёт доступен на любом уровне аккаунта`.
- [x] Expired Plus UX keeps the basic report available.
- [x] Browser return/query params do not activate Plus.
- [x] Mobile and desktop layouts expose the same matrix.

## Implementation evidence

- Dashboard product metadata explicitly classifies the Self report as `basic` and Career, Love and Child as `plus_only`; only Plus-only cards are locked when backend billing access is inactive.
- Dashboard and billing copy state that the basic report is available at every account level and remains available after Plus expires.
- The basic Astrotype v2 client no longer models or renders a paid locked response; specialized Career access keeps the backend-owned `402` lock and renders a Plus CTA without exposing the structured error payload.
- Checkout return triggers a fresh `/billing/access` read. Query parameters do not activate Plus locally.
- The same product matrix renders across responsive breakpoints. Intentional dashboard/billing visual changes were captured for desktop, tablet and mobile in both light and dark themes.

## Verification evidence

```text
npm test
  -> all 15 frontend contract scripts passed
npx eslint <changed frontend files>
  -> passed
npx tsc --noEmit --pretty false
  -> passed
npx playwright test tests/e2e/theme-visual.spec.ts
  -> 6 passed (desktop/tablet/mobile, light/dark)
npm run build
  -> Next.js production build completed successfully; 17/17 static pages generated
```

## Verification target

```bash
cd frontend
npm test
npx eslint src/app src/components src/hooks src/lib
npx tsc --noEmit --pretty false
npm run build
```
