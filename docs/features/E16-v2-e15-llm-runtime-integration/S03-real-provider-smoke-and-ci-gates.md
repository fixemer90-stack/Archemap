# S03: Add real-provider smoke and CI-safe mock gates

## Status

✅ Готово

## Context

The existing full-flow smoke proves that V2 flow works end-to-end, but it currently validates canonical payload/readiness rather than proving real LLM provider usage. After S01/S02, smoke must distinguish three modes:

1. CI/mock mode: no real credentials required; deterministic/mock provider is allowed and expected.
2. Local real-provider mode: root `.env` provides DeepSeek credentials; V2 narrative segments must show provider/model from real config.
3. Failure mode: bad/missing credentials, quota or network failures are reported honestly and do not masquerade as complete LLM-backed reports.

## What to do

1. Extend `scripts/smoke/astrotype-v2-full-flow.py` with optional provider/model assertions:
   - `--expect-provider deepseek`
   - `--expect-model deepseek-v4-flash`
2. Add redacted env/config summary to smoke output:
   - provider/model visible;
   - API key presence only as `[REDACTED]` / boolean.
3. Verify frontend route remains HTTP 200 for the real-provider generated report.
4. Keep CI path green without real credentials by using explicit mock/deterministic mode.
5. Document exact operator runbook for real LLM local smoke.

## Files likely affected

| File                                                                                       | Action                                                      |
| ------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| `scripts/smoke/astrotype-v2-full-flow.py`                                                  | Add provider/model assertions and redacted config evidence. |
| `docs/features/E16-v2-e15-llm-runtime-integration/S03-real-provider-smoke-and-ci-gates.md` | Mark complete only after real smoke.                        |
| `docs/features/E16-v2-e15-llm-runtime-integration/FEATURE.md`                              | Update status/verification evidence after implementation.   |
| CI workflow or docs                                                                        | Only if current CI needs an explicit mock-mode env.         |

## Acceptance criteria

- [x] Real-provider smoke creates a report with segment/provider evidence matching `deepseek/deepseek-v4-flash`.
- [x] Smoke prints no secrets.
- [x] Smoke confirms `report_status=ready/complete`, `ready_segments=6`, `total_segments=6`.
- [x] Smoke confirms frontend `/report/v2/{profile_id}` returns HTTP 200.
- [x] CI remains green without real LLM credentials.
- [x] A bad-provider/bad-key case fails loudly with a precise blocker.

## Verification

Real-provider smoke (local backend, worker and frontend running; email forced to console for local smoke):

```bash
cd backend && EMAIL_PROVIDER=console uv run python ../scripts/smoke/astrotype-v2-full-flow.py \
  --base-url http://127.0.0.1:3000 \
  --backend-url http://127.0.0.1:8000 \
  --timeout 600 \
  --expect-provider deepseek \
  --expect-model deepseek-v4-flash
```

Observed smoke evidence:

```json
{
  "status": "ok",
  "report_status": "ready",
  "ready_segments": 6,
  "total_segments": 6,
  "llm_config": {
    "llm_enabled": true,
    "llm_provider": "deepseek",
    "llm_model": "deepseek-v4-flash",
    "llm_api_key_present": true,
    "llm_api_key": "[REDACTED]"
  },
  "segment_providers": "6 sections all provider=deepseek model=deepseek-v4-flash",
  "frontend_route_http": 200
}
```

CI-safe gates:

```bash
cd backend && uv run pytest tests/unit/test_smoke_astrotype_v2_full_flow.py -q --tb=short
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_segment_inputs.py tests/unit/test_astrotype_v2/test_segment_validation.py tests/unit/test_astrotype_v2/test_llm_segments.py -q --tb=short
cd backend && uv run ruff check app/modules/astrotype_v2 app/modules/llm/providers/deepseek.py workers/tasks/astrotype_v2.py ../scripts/smoke/astrotype-v2-full-flow.py tests/unit/test_smoke_astrotype_v2_full_flow.py tests/unit/test_astrotype_v2
cd backend && uv run mypy app/modules/astrotype_v2 app/modules/llm/providers/deepseek.py workers/tasks/astrotype_v2.py ../scripts/smoke/astrotype-v2-full-flow.py tests/unit/test_smoke_astrotype_v2_full_flow.py tests/unit/test_astrotype_v2
```
