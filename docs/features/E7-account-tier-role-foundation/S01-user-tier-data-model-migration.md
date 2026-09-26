# S01: User tier data model and migration

## Status

🟡 Deployed; allowed-value enforcement missing

## Context

Astrotype needs a durable account-level Free/Plus status separate from payment attempts and product entitlements.

## Source architecture

- `../../architecture/account-tier-role-foundation.md`
- Parent feature: `./FEATURE.md`

## Files affected

- `backend/app/modules/users/models.py`
- `backend/alembic/versions/d3e4f5a6b7c8_add_account_tier_to_users.py`
- user/current-user schemas
- migration verification docs

## What to do

For implemented code, keep this document as the acceptance contract and regression checklist. Production migration is tracked separately in S05.

## Acceptance criteria

- [x] `users.account_tier` exists in code.
- [x] Default value is `free` for new users.
- [x] Migration preserves users, auth data, profiles, payments, webhooks, entitlements and v2 artifacts.
- [ ] Database/application boundaries reject values outside `free` and `plus`.
- [x] The column is not modeled as admin/RBAC permission.
- [x] Production database has the column after deploy/migration.

## Audit note — 2026-09-26

Production contains only `free` and `plus`, but the invariant is not enforced: the ORM and migration use a plain `varchar(20)`, production has no `account_tier` check constraint, and the API schema uses a plain string. See `./AUDIT-discrepancies.md`.

## Verification

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_payments.py tests/unit/test_auth_service.py tests/unit/test_dependencies.py -q
./.venv/bin/ruff check app/modules/users backend/alembic/versions/d3e4f5a6b7c8_add_account_tier_to_users.py
./.venv/bin/python -m mypy .
```
