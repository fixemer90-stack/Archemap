# V2-E10: API & async runtime

## Status

✅ Завершено

## Goal

Expose v2 generation, progress, report retrieval, facts and infographics through stable multi-client APIs with async generation support.

## Dependencies

V2-E2 through V2-E9 core pipeline.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`

## Scope

This feature covers the `V2-E10` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [x] Web and Android can use the same endpoints.
- [x] Generation can continue while client is closed.
- [x] Progress exposes segment-level state.
- [x] Auth/entitlement checks are server-side.

## Stories

| ID  | Story                                                                 | Status       |
| --- | --------------------------------------------------------------------- | ------------ |
| S01 | [Add report generation endpoint](./S01-report-generation-endpoint.md) | ✅ Завершено |
| S02 | [Add status/progress API](./S02-status-progress-api.md)               | ✅ Завершено |
| S03 | [Add read APIs](./S03-report-read-apis.md)                            | ✅ Завершено |
| S04 | [Wire async runtime](./S04-async-worker-orchestration.md)             | ✅ Завершено |
| S05 | [Add regeneration API](./S05-regeneration-api.md)                     | ✅ Завершено |

## Implementation order

```text
S01 → S02 → S03 → S04 → S05
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e10-api-async-runtime
```

For implementation stories, add targeted tests to the active story before marking it complete.

Implementation verification evidence:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py -v --tb=short
cd backend && uv run pytest tests/unit/test_astrotype_v2 -v --tb=short
cd backend && uv run ruff check app/modules/astrotype_v2 app/api/v1 workers/tasks tests/unit/test_astrotype_v2
cd backend && uv run ruff format --check app/modules/astrotype_v2 app/api/v1 workers/tasks tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2 app/api/v1 workers/tasks tests/unit/test_astrotype_v2
cd backend && uv run python - <<'PY'
import asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app

async def main():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/v1/astrotype-v2/reports/generations/00000000-0000-0000-0000-000000000000')
    assert response.status_code == 401
    print('astrotype-v2 API auth route smoke ok')

asyncio.run(main())
PY
git diff --check -- backend/app/modules/astrotype_v2 backend/app/api/v1 backend/workers/tasks backend/tests/unit/test_astrotype_v2 docs/features/E16-v2-e10-api-async-runtime
```
