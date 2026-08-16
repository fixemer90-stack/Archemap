# S08: Full-flow smoke and runbook

## Status

✅ Готово

## Context

The complete product flow needs a repeatable smoke command, not manual curl snippets scattered through chat history.

## What to do

1. Add a smoke script for registration → local verification gate → login → V2 generation → ready report read.
2. Verify backend health, frontend route, worker result, report status, sections and deterministic data.
3. Redact tokens/cookies in artifacts.
4. Document local startup commands and expected outputs.

## Files affected

| Action | Path                                                                                |
| ------ | ----------------------------------------------------------------------------------- |
| Create | `scripts/smoke/astrotype-v2-full-flow.py`                                           |
| Modify | `docs/features/E16-v2-e11-web-responsive-reader/S08-full-flow-smoke-and-runbook.md` |

## Acceptance criteria

- [x] One command proves the full local V2 flow.
- [x] Smoke output includes report status, progress, sections, calculation layer and forbidden marker check.
- [x] Runbook names backend, frontend, Postgres, Redis and Celery prerequisites.

## Local runbook

Prerequisites:

- backend API on `http://127.0.0.1:8000`;
- frontend dev server on `http://127.0.0.1:3000`;
- PostgreSQL reachable through backend settings;
- Redis reachable for rate limits and Celery broker;
- Celery worker running `astrotype_v2.generate_natal_report`;
- backend dependencies active via `uv run`.

Fresh verified startup commands:

```bash
cd backend && EMAIL_PROVIDER=console uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
cd backend && EMAIL_PROVIDER=console LLM_ENABLED=true LLM_PROVIDER=mock uv run celery -A workers.celery_app.app worker --loglevel=INFO
cd frontend && npm run dev -- --hostname 127.0.0.1 --port 3000
```

The smoke registers a disposable local user, reads the verification token from the local DB, verifies the account, logs in, generates a V2 report, waits until the report is ready, checks canonical reader payload markers, checks forbidden typology leakage, and checks the frontend route returns HTTP 200.

## Verification

```bash
cd backend && uv run python ../scripts/smoke/astrotype-v2-full-flow.py --base-url http://127.0.0.1:3000 --backend-url http://127.0.0.1:8000 --timeout 120
```

Latest local result:

```json
{
  "status": "ok",
  "report_status": "ready",
  "ready_segments": 6,
  "total_segments": 6,
  "reader_blocks": [
    "key_indicators",
    "planet_positions",
    "balance_bars",
    "house_emphasis",
    "aspect_network",
    "key_aspects",
    "calculation_matrix"
  ],
  "frontend_route_http": 200
}
```
