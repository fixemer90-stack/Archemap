# S07: Report and product entitlement gates

## Status

✅ Реализовано

## Context

Entitlement creation only matters if paid reports/products consistently read it. This story wires the first explicit backend gate for paid self-report payloads.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `backend/app/modules/authorization/service.py`
- `backend/app/modules/astrotype_v2/router.py`
- `backend/tests/unit/test_payments.py`
- `frontend/src/lib/api/astrotype-v2.ts`
- `frontend/src/lib/astrotype-v2/use-v2-report-generation.ts`
- `frontend/src/app/(dashboard)/report/v2/[profileId]/page.tsx`
- `frontend/src/lib/astrotype-v2/report-view-model.ts`

## Implemented behavior

- `EntitlementsService.has_active_product_access(user_id, product)` checks active, unexpired, matching-product entitlements.
- `build_locked_product_response(product, reason)` returns safe upgrade metadata without full paid payload fields.
- Astrotype v2 report read returns locked metadata instead of full report payload when the user lacks `self` entitlement.
- Paid report artifact endpoints (`pdf`, `progress`, `facts`, `infographic`, `segments`, `regenerate`) require active `self` entitlement and return HTTP 402 with safe upgrade metadata when locked.
- Frontend v2 report generation flow recognises locked report responses and renders a billing CTA instead of assuming a full report shape.

## Acceptance criteria

- [x] Define which report/product routes require entitlement.
- [x] Add backend policy helper for `user + product + access_mode`.
- [x] Apply policy checks to paid endpoints.
- [x] Free response does not include full paid payload when gated.
- [x] Locked responses include safe upgrade metadata.
- [x] Direct API calls cannot bypass frontend gating.
- [x] Tests cover active, missing, expired/inactive and mismatched entitlement cases.

## Verification

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_payments.py -q
./.venv/bin/ruff check app/modules/authorization app/modules/astrotype_v2 tests/unit/test_payments.py
./.venv/bin/python -m mypy .

cd ../frontend
npx eslint src/lib/api/astrotype-v2.ts src/lib/astrotype-v2/use-v2-report-generation.ts src/app/\(dashboard\)/report/v2/\[profileId\]/page.tsx src/lib/astrotype-v2/report-view-model.ts
npx tsc --noEmit --pretty false
```

Latest local result:

```text
backend/tests/unit/test_payments.py: 22 passed
ruff: All checks passed!
mypy: Success: no issues found in 291 source files
frontend eslint: passed
frontend TypeScript: passed
```
