# Story E8.S04: Frontend account-level report UX

Status: ⬜ Не начато
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

- [ ] Basic report CTA works for Free and Plus.
- [ ] Non-basic report cards clearly say `Доступно с Plus` when locked.
- [ ] Billing copy says `Базовый отчёт доступен на любом уровне аккаунта`.
- [ ] Expired Plus UX keeps the basic report available.
- [ ] Browser return/query params do not activate Plus.
- [ ] Mobile and desktop layouts expose the same matrix.

## Verification target

```bash
cd frontend
npm test
npx eslint src/app src/components src/hooks src/lib
npx tsc --noEmit --pretty false
npm run build
```
