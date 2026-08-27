# S05: Persist generation status and diagnostics

## Status

⬜ Не начато

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

- [ ] `generation_id` from POST response can be looked up later.
- [ ] Status endpoint returns 404 for unknown ids, not fake queued state.
- [ ] Status endpoint is owner-scoped.
- [ ] Worker logs include `generation_id` for every task start/success/failure.
- [ ] Section-level failures expose actionable diagnostics without leaking secrets.

## Verification

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py tests/unit/test_astrotype_v2/test_router.py -v --tb=short
uv run alembic upgrade head
uv run ruff check app/modules/astrotype_v2 app/api/v1 workers/tasks tests/unit/test_astrotype_v2
uv run mypy app/modules/astrotype_v2 app/api/v1 workers/tasks tests/unit/test_astrotype_v2
```
