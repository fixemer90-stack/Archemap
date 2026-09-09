# Story E8.S03: Report operation policy coverage

Status: ⬜ Не начато
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

- [ ] Free can create, generate, read, regenerate and export the basic report.
- [ ] Direct API calls cannot expose Plus-only report content to Free accounts.
- [ ] Artifact URLs cannot bypass policy checks.
- [ ] Every supported client sees the same access outcome.
- [ ] Existing ownership checks remain in force; free basic access never grants access to another user's report.

## Verification target

```bash
cd backend
./.venv/bin/python -m pytest tests/unit/test_astrotype_v2/test_api_runtime.py tests/integration -q
./.venv/bin/python -m ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```
