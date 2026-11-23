# E23.S06: Защищённый business dashboard

**Цель (SMART):** закрыть перечисленные критерии S06 воспроизводимыми tests/review/evidence до смены статуса на complete.

Status: 🟡 Frontend verified locally; review and S04 RBAC evidence pending

[Feature](./FEATURE.md) · [Contract](../../architecture/business-monitoring-contract.md) · [Registry](../../architecture/analytics-event-registry.md)

## Scope

Implementation task T06. Do not infer live readiness from code/tests. External operations and authorizations are separate gates.

`/admin/business` is a standalone, noindex admin page. It reads `GET /api/v1/admin/business/overview` using the existing cookie session. The API owns authorization; the page does not grant access using local roles or display metrics on an error response. It does not add navigation links or third-party analytics to customer surfaces.

## Acceptance

- [ ] Server-backed admin overview distinguishes unavailable/stale/estimated/unknown values.
- [x] Mobile/desktop/dark/light/keyboard verified with no fabricated financial totals.
- [ ] Ordinary users cannot obtain dashboard data by direct API request.

## Evidence

- Implementation: `frontend/src/app/admin/business/page.tsx`, `frontend/src/components/admin/business-overview.{tsx,module.css}`, and `frontend/src/lib/api/admin-business.ts`. Browser coverage: `frontend/tests/e2e/admin-business.spec.ts` and `frontend/tests/e2e/support/admin-business-fixtures.ts`.
- RED: `playwright test tests/e2e/admin-business.spec.ts --project=chromium-desktop -g 'overview denial'` against the pre-implementation checkout returned the Next.js 404 instead of the expected denial view.
- GREEN: `playwright test tests/e2e/admin-business.spec.ts` passed against both the default Next.js dev server and `next build --webpack` production output in a Linux scratch copy (14 passed, 2 duplicate viewport cases skipped in each run). No requests reached a backend. Separate fixtures exercised observed, stale, unavailable, loading, malformed DTO, 503 with retry, 401 sign-in and 403 denial. The browser matrix checked 320/820/1440 px in both themes for overflow and axe violations; keyboard checks exercised visible focus, retry and return navigation. Six full-page captures were inspected.
- `npm test`, ESLint on the changed TypeScript files, Prettier on the changed paths, and the build's TypeScript check passed. Scope fingerprint: `fc4458c543701ed888161a403bcb57a4536964bacfbc610971b33b21efa7094d` (`sha256sum` of the six repo-relative paths above, in listed order with `.tsx` before `.module.css`, piped through `sha256sum`).
- The page preserves cash amounts as exact decimal strings, lists currencies separately, and distinguishes missing data, observed zero, and unknown payment mode. S04 has no estimate field or proven refund ledger and does not certify MRR. No estimated financial amount, refund total, or MRR amount is substituted. Server-backed acceptance and direct API RBAC are verified separately in [S04](./S04-business-overview-api.md); fixture 403 does not prove API authorization. Independent reviews and live rollout have not been performed for this slice.
