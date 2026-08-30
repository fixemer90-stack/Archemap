# S05: Persist generation status and diagnostics

## Status

✅ Реализовано

## Context

The current generation status endpoint returns a synthetic `queued_or_running` response for any authenticated UUID. It does not read real worker state, DB rows, section status or Celery result metadata. Production incidents therefore cannot be diagnosed from the `generation_id` given to the client.

This Story makes generation ids traceable.

## What to do

1. Add a persisted generation/job status record or equivalent durable status model.
2. Store `generation_id`, Celery task id when available, user id, profile id, report id when created, status and timestamps.
3. Store section-level diagnostics: grounding counts/status, segment status, provider/model, error class/message.
4. Update enqueue logic to create the status record before task dispatch.
5. Update worker task to transition status through queued/running/partial/complete/failed.
6. Update `GET /api/v1/astrotype-v2/reports/generations/{generation_id}` to read real status and enforce owner access.
7. Add log fields so `generation_id` can be searched in worker logs.

## API contract

The status endpoint must return real state:

```json
{
  "generation_id": "...",
  "status": "queued|running|partial|complete|failed",
  "profile_id": "...",
  "report_id": "...",
  "sections": [
    {
      "section_id": "core_pattern",
      "grounding_status": "ready",
      "owned_evidence_count": 8,
      "reference_evidence_count": 0,
      "segment_status": "ready",
      "error": null
    }
  ]
}
```

## Files affected

| File | Action |
|---|---|
| `backend/app/modules/astrotype_v2/models.py` | Add generation/job status model if needed |
| `backend/alembic/versions/*` | Add migration for generation status persistence |
| `backend/app/modules/astrotype_v2/api_runtime.py` | Build real generation status payload |
| `backend/app/modules/astrotype_v2/router.py` | Read owner-scoped generation status |
| `backend/workers/tasks/astrotype_v2.py` | Update status transitions and log context |
| `backend/tests/unit/test_astrotype_v2/test_api_runtime.py` | Cover real status payloads |

## Acceptance criteria

- [x] `generation_id` from POST response can be looked up later.
- [x] Status endpoint returns 404 for unknown ids, not fake queued state.
- [x] Status endpoint is owner-scoped.
- [x] Worker logs include `generation_id` for every task start/success/failure.
- [x] Section-level failures expose actionable diagnostics without leaking secrets.

## Verification

```bash
cd backend
uv run python -m py_compile app/modules/astrotype_v2/router.py app/modules/astrotype_v2/api_runtime.py app/modules/astrotype_v2/models.py app/modules/astrotype_v2/repository.py workers/tasks/astrotype_v2.py
uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py tests/unit/test_astrotype_v2/test_worker_runtime.py -q
uv run pytest tests/unit/test_astrotype_v2 -q
uv run alembic upgrade head
uv run ruff check .
uv run ruff format --check .
uv run mypy app tests
```

Fresh verification on 2026-08-30:

- focused API/runtime tests: `14 passed`;
- full v2 unit suite: `140 passed`;
- local Alembic upgrade applied `c2d3e4f5a6b7`;
- ruff: `All checks passed!`, `291 files already formatted`;
- mypy: `Success: no issues found in 260 source files`.
