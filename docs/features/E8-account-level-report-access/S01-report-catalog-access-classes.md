# Story E8.S01: Report catalog and access classes

Status: ✅ Готово
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

- [x] Exactly one report type is `basic`.
- [x] Career, Love, Child and every other enabled non-basic report are `plus_only`.
- [x] Unknown report types are rejected or treated as Plus-only, never free.
- [x] Payment product identifiers and report type identifiers have one documented mapping.
- [x] Existing report/profile/artifact identifiers remain retrievable after migration.

## Implementation evidence

- `CatalogService` owns canonical `ReportDefinition` records for `basic_natal`, `career`, `love` and `child`.
- Legacy `self`, `self_full` and `career_full` identifiers resolve through lookup aliases only; persisted rows and UUIDs are not rewritten.
- Career constants derive their report type, access class, entitlement product and retired SKU from the canonical catalog.
- Verification: `tests/unit/test_report_catalog.py` and `tests/unit/test_career/test_product_access_contract.py`.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_report_catalog*.py -q
./.venv/bin/python -m ruff check app/modules/catalog app/modules/astrotype_v2 tests/unit/test_report_catalog*.py
```
