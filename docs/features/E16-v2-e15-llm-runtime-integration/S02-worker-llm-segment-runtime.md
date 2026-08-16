# S02: Wire V2 worker narrative segments to LLM provider

## Status

⬜ Не начато

## Context

V2-E7 already documents and tests modular LLM contracts, but the currently active V2 worker does not use that runtime. `backend/workers/tasks/astrotype_v2.py` currently persists narrative segments with:

```python
_PROMPT_VERSION = "astrotype_v2_deterministic_local_v1"
_PROVIDER = "deterministic"
_MODEL = "v2-local-runtime"
```

The task currently builds a complete report flow, but the narrative prose is generated locally/deterministically. This is acceptable for CI/offline smoke, but not for real V2 user-facing reports when `LLM_ENABLED=true` and `LLM_PROVIDER=deepseek` are configured.

## What to do

1. Trace existing V2 LLM modules:
   - `backend/app/modules/astrotype_v2/llm_segments.py`
   - segment input builders and validators from V2-E7
   - `backend/app/modules/llm/provider.py`
2. Replace deterministic narrative section generation in the worker with provider-backed segment generation when real LLM is enabled.
3. Keep deterministic foundation stages unchanged:
   - chart;
   - facts/evidence;
   - synthesis;
   - outline;
   - infographic/calculation layer.
4. Persist per-section segment status, provider, model, prompt_version, payload, errors and retry metadata.
5. Preserve idempotency/race fix: concurrent `force=false` generation must return `already_exists`, not duplicate chart/report rows.
6. Make fallback behavior explicit:
   - CI/mock mode may use mock/deterministic provider;
   - real-provider failure must not be mislabeled as a successful LLM-backed report.

## Files likely affected

| File                                               | Action                                                                             |
| -------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `backend/workers/tasks/astrotype_v2.py`            | Replace deterministic segment generation with LLM provider-backed segment runtime. |
| `backend/app/modules/astrotype_v2/llm_segments.py` | Reuse or extend prompt/input contracts.                                            |
| `backend/app/modules/llm/provider.py`              | Reuse existing provider factory; avoid new parallel provider system.               |
| `backend/tests/unit/test_astrotype_v2/...`         | Add worker/provider contract tests.                                                |
| `scripts/smoke/astrotype-v2-full-flow.py`          | Add provider/model assertions.                                                     |

## Acceptance criteria

- [ ] Worker calls the existing LLM provider factory when `LLM_ENABLED=true`.
- [ ] Worker persists real provider/model metadata in segment rows.
- [ ] Worker does not call LLM for deterministic lower calculation layer.
- [ ] Worker does not silently downgrade real-provider failures to deterministic prose.
- [ ] Existing idempotency/race behavior remains green.
- [ ] V2 remains natal-only; no socionics/Model A/MBTI leakage.

## Verification

To be filled during implementation. Expected shape:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_llm_segments.py tests/unit/test_astrotype_v2/test_api_runtime.py -q
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
cd backend && uv run ruff check workers/tasks/astrotype_v2.py app/modules/astrotype_v2 app/modules/llm tests/unit/test_astrotype_v2
cd backend && uv run mypy workers/tasks/astrotype_v2.py app/modules/astrotype_v2 app/modules/llm
```
