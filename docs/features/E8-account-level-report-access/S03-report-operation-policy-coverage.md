# Story E8.S03: Report operation policy coverage

Status: ✅ Готово
Feature: [E8 Account-level report access](./FEATURE.md)
Architecture: [Account levels and report access policy](../../architecture/account-levels-report-access-policy.md)

## Context

Protecting only the main report endpoint leaves bypasses through generation, segment, calculation, regeneration, PDF or artifact routes.

## What to do

1. Apply the report policy to create/generate routes.
2. Apply it to report, status, segment and calculation-layer reads.
3. Apply it to regeneration and PDF/export/share/download routes.
4. Check access before loading or serializing protected payloads.
5. Remove the current paid-entitlement requirement from the canonical basic-report flow only.

## Acceptance criteria

- [x] Free can create, generate, read, regenerate and export the basic report.
- [x] Direct API calls cannot expose Plus-only report content to Free accounts.
- [x] Artifact URLs cannot bypass policy checks.
- [x] Every supported client sees the same access outcome.
- [x] Existing ownership checks remain in force; free basic access never grants access to another user's report.

## Implementation evidence

- Every Astrotype v2 report route declares an explicit operation contract covering create, generation status, read, progress, facts, infographic, segments, regeneration and PDF export.
- The mounted legacy `/reports` API now has its own executable inventory covering create, list, read, narrative regeneration, GET/POST/HEAD PDF and version routes; it no longer bypasses E8 for `career`, `love` or `child` payloads.
- Basic-report routes use `ReportAccessPolicy` and never consult or reconcile a paid entitlement.
- Owned report identifiers are resolved with metadata-only queries before report JSON/payload columns are loaded.
- Legacy report listing filters at SQL level to identifiers the account may access, so locked payload rows are not deserialized and then discarded.
- Career report reads, sections, versions, regeneration and PDF resolve ownership, then active Plus or grandfathered Career access, then load protected payloads.
- Career questionnaire/create operations preserve ownership-first 404 behavior before the Plus gate.
- Subscription-backed entitlements require `active`/`cancel_scheduled` inside the paid period. `past_due` grace does not become product grandfathering; only a current direct historical product grant can use that exception.
- A current direct grandfathered grant is evaluated against the report catalog's own entitlement product, so scoped Career, Love or Child access unlocks only that report and never account-wide Plus.
- Verification: the full backend unit suite passes with the executable Astrotype v2, Career and legacy-report inventories; PostgreSQL-backed Career and legacy-report matrices run against disposable PostgreSQL 16.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_astrotype_v2/test_api_runtime.py tests/integration -q
./.venv/bin/python -m ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```
