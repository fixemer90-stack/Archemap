# S02: Wire V2 worker narrative segments to LLM provider

## Status

✅ Готово

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

- [x] Worker calls the existing LLM provider factory when `LLM_ENABLED=true`.
- [x] Worker persists real provider/model metadata in segment rows.
- [x] Worker does not call LLM for deterministic lower calculation layer.
- [x] Worker does not silently downgrade real-provider failures to deterministic prose.
- [x] Existing idempotency/race behavior remains green in the Astrotype v2 regression suite.
- [x] V2 remains natal-only; no socionics/Model A/MBTI leakage in the segment prompt/validation contract.

## Verification

Fresh verification after implementation:

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2/test_llm_segments.py -q
# 6 passed in 1.46s

cd backend && uv run pytest tests/unit/test_astrotype_v2 -q
# 114 passed in 5.52s

cd backend && uv run ruff check app/modules/astrotype_v2/llm_segments.py workers/tasks/astrotype_v2.py tests/unit/test_astrotype_v2/test_llm_segments.py
# All checks passed!

cd backend && uv run mypy app/modules/astrotype_v2/llm_segments.py workers/tasks/astrotype_v2.py tests/unit/test_astrotype_v2/test_llm_segments.py
# Success: no issues found in 3 source files

cd backend && uv run python - <<'PY'
from pathlib import Path
src = Path('workers/tasks/astrotype_v2.py').read_text()
checks = {
    'imports_get_llm_provider': 'get_llm_provider' in src,
    'uses_llm_enabled': 'settings.LLM_ENABLED' in src,
    'uses_segment_adapter': 'StructuredSegmentProviderAdapter' in src,
    'uses_segment_runner': 'run_segment_generation_v2' in src,
    'keeps_deterministic_fallback': '_ensure_deterministic_segments' in src,
}
for key, value in checks.items():
    print(key, value)
assert all(checks.values())
PY
# imports_get_llm_provider True
# uses_llm_enabled True
# uses_segment_adapter True
# uses_segment_runner True
# keeps_deterministic_fallback True
```

Real-provider end-to-end smoke remains owned by S03 so the code path can be verified without printing secrets or making CI depend on external credentials.
