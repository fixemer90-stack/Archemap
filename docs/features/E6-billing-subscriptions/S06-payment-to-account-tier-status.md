# S06: Payment-to-account-tier status update

## Status

✅ Реализовано

## Context

The account must have a visible Free/Plus status, but in the first implementation that status must not restrict functionality.

## Source architecture

- `../../architecture/current-payment-confirmation-flow.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `docs/architecture/account-tier-role-foundation.md`
- `backend/app/modules/users/models.py`
- user schemas / `/users/me` response
- payment success orchestration
- database migration
- backend tests

## What to do

For implemented stories, keep this document as the acceptance contract and regression checklist. For pending stories, implement only this slice and update the status after code/tests pass.

## Acceptance criteria

- [x] User model stores account tier/status `free` or `plus`.
- [x] Existing users default to `free`.
- [x] Confirmed payment updates account tier to `plus`.
- [x] Tier update is idempotent for repeated webhooks.
- [x] `/users/me` or billing access state exposes the tier.
- [x] No endpoint starts blocking Free users because of this story.
- [x] Tests prove tier is status-only.

## Verification

```bash
./backend/.venv/bin/python -m pytest backend/tests/unit/test_payments.py backend/tests/unit/test_auth_service.py backend/tests/unit/test_dependencies.py -q
./backend/.venv/bin/ruff check backend/app/modules/users backend/app/modules/auth backend/app/modules/authorization backend/app/modules/payments backend/app/modules/billing backend/alembic/versions/d3e4f5a6b7c8_add_account_tier_to_users.py backend/tests/unit/test_payments.py
./backend/.venv/bin/python -m mypy backend/app/modules/users backend/app/modules/auth backend/app/modules/authorization backend/app/modules/payments backend/app/modules/billing --ignore-missing-imports
```

Latest verification for this story:

```text
backend/tests/unit/test_payments.py + auth/dependencies slice: 31 passed, 4 pre-existing AsyncMock warnings
ruff: All checks passed!
mypy: Success: no issues found in 36 source files
```

Implemented files:

- `backend/app/modules/users/models.py`
- `backend/app/modules/auth/schemas.py`
- `backend/app/modules/users/router.py`
- `backend/app/modules/authorization/service.py`
- `backend/app/modules/payments/service.py`
- `backend/alembic/versions/d3e4f5a6b7c8_add_account_tier_to_users.py`
- `backend/tests/unit/test_payments.py`
