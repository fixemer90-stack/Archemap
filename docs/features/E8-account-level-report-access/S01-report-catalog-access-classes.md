# Story E8.S01: Report catalog and access classes

Status: ⬜ Не начато
Feature: [E8 Account-level report access](./FEATURE.md)
Architecture: [Account levels and report access policy](../../architecture/account-levels-report-access-policy.md)

## Context

The current catalog uses payment/product identifiers such as `self_full`, while the new policy needs one stable report classification that is independent of frontend labels.

## What to do

1. Add a backend-owned report catalog with `report_type`, display name and `access_class`.
2. Define exactly one `basic` report type (`basic_natal` target name).
3. Classify every other report type as `plus_only`.
4. Make unknown/new report types fail closed instead of inheriting free access.
5. Define a migration/alias strategy for existing `self` / `self_full` identifiers without rewriting or deleting historical report rows.

## Acceptance criteria

- [ ] Exactly one report type is `basic`.
- [ ] Career, Love, Child and every other enabled non-basic report are `plus_only`.
- [ ] Unknown report types are rejected or treated as Plus-only, never free.
- [ ] Payment product identifiers and report type identifiers have one documented mapping.
- [ ] Existing report/profile/artifact identifiers remain retrievable after migration.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_report_catalog*.py -q
./.venv/bin/python -m ruff check app/modules/catalog app/modules/astrotype_v2 tests/unit/test_report_catalog*.py
```
