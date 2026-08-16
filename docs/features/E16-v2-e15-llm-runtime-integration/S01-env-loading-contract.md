# S01: Fix backend/worker LLM environment loading

## Status

⬜ Не начато

## Context

The user configured real LLM settings in the project root `.env`:

- `D:\Python\Balthier\Archemap\.env`
- WSL equivalent: `/home/balthier/archemap/.env`

However backend and worker are normally launched from `/home/balthier/archemap/backend`, and `backend/app/config.py` currently declares `env_file=".env"`. That means the process reads `/home/balthier/archemap/backend/.env`, not the root `.env`.

Current observed settings from backend cwd:

```text
LLM_ENABLED=False
LLM_PROVIDER=mock
LLM_MODEL=mock-self-v1
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

Current observed settings from root cwd:

```text
LLM_ENABLED=True
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=[REDACTED]
LLM_TIMEOUT_SECONDS=180
LLM_MAX_RETRIES=2
```

## What to do

1. Decide and implement one canonical env-loading contract:
   - preferred: backend settings load root `.env` explicitly relative to repository root; or
   - alternative: document and enforce a single startup command that loads root `.env` before `uvicorn`/Celery.
2. Keep `backend/.env` behavior understandable; do not let it silently override root LLM config unless intentionally documented.
3. Add a settings/unit test or script-level assertion proving backend cwd resolves the intended LLM settings.
4. Update local startup/runbook docs with exact backend and worker commands for real LLM mode and mock CI mode.
5. Do not print or commit `LLM_API_KEY`.

## Files likely affected

| File                                                                           | Action                                                |
| ------------------------------------------------------------------------------ | ----------------------------------------------------- |
| `backend/app/config.py`                                                        | Update env-file resolution or settings docs/comments. |
| `backend/tests/...`                                                            | Add settings/env contract regression.                 |
| `docs/features/E16-v2-e15-llm-runtime-integration/S01-env-loading-contract.md` | Mark complete only after verification.                |
| `scripts/smoke/astrotype-v2-full-flow.py`                                      | Optionally add redacted env summary.                  |

## Acceptance criteria

- [ ] Running settings import from `backend/` sees the intended configured LLM provider/model.
- [ ] Running settings import from repo root sees the same provider/model.
- [ ] Secret values are redacted in all verification output.
- [ ] Mock/offline mode remains available for CI without requiring real API credentials.
- [ ] Backend and Celery startup commands for real LLM mode are documented.

## Verification

To be filled during implementation. Expected shape:

```bash
cd backend && uv run python - <<'PY'
from app.config import settings
assert settings.LLM_ENABLED is True
assert settings.LLM_PROVIDER == 'deepseek'
assert settings.LLM_MODEL == 'deepseek-v4-flash'
assert bool(settings.LLM_API_KEY)
print('LLM env resolved with API key [REDACTED]')
PY
cd backend && uv run pytest <settings-env-contract-test> -q
cd backend && uv run ruff check app/config.py <test-file>
cd backend && uv run mypy app/config.py <test-file>
```
