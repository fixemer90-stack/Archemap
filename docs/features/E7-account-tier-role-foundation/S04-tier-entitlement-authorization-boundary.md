# S04: Tier vs entitlement authorization boundary

## Status

✅ Реализовано

## Context

`account_tier` is a commercial/account status. Product authorization must remain entitlement-based so a stale or manually changed tier cannot leak paid report payloads.

## Source architecture

- `../../architecture/account-tier-role-foundation.md`
- Parent feature: `./FEATURE.md`
- Related story: `../E6-billing-subscriptions/S07-report-product-entitlement-gates.md`

## Files affected

- `backend/app/modules/authorization/service.py`
- `backend/app/modules/astrotype_v2/router.py`
- `backend/tests/unit/test_payments.py`
- `frontend/src/lib/api/astrotype-v2.ts`
- `frontend/src/lib/astrotype-v2/use-v2-report-generation.ts`
- `frontend/src/app/(dashboard)/report/v2/[profileId]/page.tsx`

## Implemented behavior

- `EntitlementsService.has_active_product_access(user_id, product)` checks active, unexpired, matching-product entitlements.
- Locked response metadata is safe and contains no full paid report payload.
- Astrotype v2 self-report endpoints require active `self` entitlement for full report payload/artifacts.
- Frontend recognises locked report responses and renders a billing CTA.

## Acceptance criteria

- [x] Code distinguishes status tier from product entitlement.
- [x] Paid product/report gates do not trust `account_tier` alone.
- [x] Missing entitlement locks paid payload.
- [x] Inactive/expired/mismatched entitlement locks paid payload.
- [x] Locked response includes safe upgrade metadata.
- [x] Direct API calls cannot bypass frontend gating.

## Verification

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_payments.py -q
./.venv/bin/ruff check app/modules/authorization app/modules/astrotype_v2 tests/unit/test_payments.py
./.venv/bin/python -m mypy .
```
