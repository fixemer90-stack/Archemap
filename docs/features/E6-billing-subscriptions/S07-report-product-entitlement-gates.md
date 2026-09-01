# S07: Report and product entitlement gates

## Status

⬜ Не начато

## Context

Entitlement creation only matters if paid reports/products consistently read it. Gating should be a separate explicit slice so it does not accidentally ship with the status-only Free/Plus role.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- report/product backend endpoints
- `backend/app/modules/authorization/service.py`
- product catalog/access matrix
- report response serializers
- frontend upgrade metadata consumers

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [ ] Define which report/product routes require entitlement.
- [ ] Add backend policy helper for `user + product + access_mode`.
- [ ] Apply policy checks to paid endpoints.
- [ ] Free response does not include full paid payload when gated.
- [ ] Locked responses include safe upgrade metadata.
- [ ] Direct API calls cannot bypass frontend gating.
- [ ] Tests cover active, missing, expired/inactive and mismatched entitlement cases.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py -q
```

Add narrower or broader checks in the implementation PR when this story touches additional modules.
