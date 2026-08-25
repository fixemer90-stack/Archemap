# V2-E15: LLM runtime integration for real V2 reports

## Status

✅ Готово

## Goal

Make the production/local V2 report generation worker use the configured real LLM provider from the project root `.env` for narrative segment generation, while keeping deterministic chart/facts/synthesis/outline/calculation-layer data backend-owned and non-LLM.

This feature closes the gap discovered after V2-E11: the web/API/generation flow is green and frontend-ready, but the current V2 worker persists narrative sections through a local deterministic runtime (`provider=deterministic`, `model=v2-local-runtime`) rather than using the configured `deepseek` provider from `D:\Python\Balthier\Archemap\.env`.

## Current verified state

As of the discovery pass:

- root `.env` exists and contains real LLM configuration:
  - `LLM_ENABLED=true`
  - `LLM_PROVIDER=deepseek`
  - `LLM_MODEL=deepseek-v4-flash`
  - `LLM_API_KEY` present and must never be committed or printed
  - `LLM_TIMEOUT_SECONDS=180`
  - `LLM_MAX_RETRIES=2`
- `backend/app/config.py` uses `SettingsConfigDict(env_file=".env")`.
- When backend/worker are started from `backend/`, settings read `backend/.env`, not the root `.env`.
- `backend/.env` exists but does not contain the LLM variables.
- Current V2 worker code in `backend/workers/tasks/astrotype_v2.py` hardcodes:
  - `_PROMPT_VERSION = "astrotype_v2_deterministic_local_v1"`
  - `_PROVIDER = "deterministic"`
  - `_MODEL = "v2-local-runtime"`
- Current V2 worker does not call `get_llm_provider`, `generate_structured`, `DeepSeekProvider`, or `OpenRouterProvider`.
- Current frontend V2 flow is ready for UX/API/runtime work, but not yet a real LLM-backed V2 narrative flow.

## Companion docs

- Workflow / product-runtime scenario: [`WORKFLOW.md`](./WORKFLOW.md)
- API/state contract: [`API.md`](./API.md)

## Dependencies

- V2-E7 Modular LLM generation: `../E16-v2-e7-modular-llm-generation/FEATURE.md`
- V2-E10 API & async runtime: `../E16-v2-e10-api-async-runtime/FEATURE.md`
- V2-E11 Web responsive reader: `../E16-v2-e11-web-responsive-reader/FEATURE.md`
- V2-E14 QA, smoke, rollout: `../E16-v2-e14-qa-smoke-rollout/FEATURE.md`
- Umbrella SRS: `../../SRS/SRS-E16-astrotype-v2-cloud-core.md`

## In scope

- Make backend/worker load the intended LLM environment consistently from the project root or an explicit documented env path.
- Wire the V2 worker narrative segment stage to the real LLM provider factory.
- Reuse existing V2 LLM segment contracts, prompts, validators, retries and persistence where possible.
- Keep deterministic foundation generation deterministic:
  - chart calculation;
  - facts/evidence;
  - synthesis/outline;
  - infographic/calculation layer.
- Persist provider/model/prompt metadata from the real LLM run.
- Add smoke/verification that proves generated V2 report segments use `deepseek/deepseek-v4-flash` when configured.
- Keep a mock/deterministic mode for CI/local offline tests, but make it explicit and not silently used when real LLM env is configured.

## Out of scope

- Rewriting the canonical V2 reader UI; V2-E11 already owns that.
- Adding socionics, Model A, MBTI, `function_strengths` or any typology leakage to V2.
- Moving secrets into git.
- Replacing DeepSeek provider infrastructure with a new provider system unless the existing factory is insufficient.
- Calling the LLM for deterministic lower calculation layer/table/infographic data.

## Acceptance criteria

- [x] Backend and worker can be started from `backend/` and still resolve the intended root `.env` LLM variables, or a documented explicit env-loading command is used.
- [x] There is no secret leakage in docs, tests, logs, commits, or smoke output.
- [x] V2 worker uses the existing LLM provider factory for narrative sections when `LLM_ENABLED=true` and `LLM_PROVIDER=deepseek`.
- [x] V2 worker no longer persists real user-facing narrative segments as `provider=deterministic` when real LLM config is present.
- [x] Deterministic chart/fact/synthesis/outline/calculation-layer stages remain LLM-free.
- [x] Segment rows persist real provider/model/prompt metadata.
- [x] Provider timeout/retry behavior respects `LLM_TIMEOUT_SECONDS` and `LLM_MAX_RETRIES`.
- [x] Failure path keeps deterministic foundation readable and marks narrative/report status honestly.
- [x] Full-flow smoke proves registration → verify → login → V2 generation → LLM-backed report ready → `/report/v2/{profile_id}` HTTP 200.
- [x] Smoke output redacts secrets and includes provider/model/status evidence.
- [x] CI remains green using mock/deterministic mode without real API credentials.

## Stories

| ID  | Story                                                                                       | Status    |
| --- | ------------------------------------------------------------------------------------------- | --------- |
| S01 | [Fix backend/worker LLM environment loading](./S01-env-loading-contract.md)                 | ✅ Готово |
| S02 | [Wire V2 worker narrative segments to LLM provider](./S02-worker-llm-segment-runtime.md)    | ✅ Готово |
| S03 | [Add real-provider smoke and CI-safe mock gates](./S03-real-provider-smoke-and-ci-gates.md) | ✅ Готово |

## Implementation order

```text
S01 → S02 → S03
```

Recommended first vertical slice before scaling to all sections:

```text
core-pattern only
→ build curated input
→ call configured provider
→ validate structured payload
→ persist one segment
→ expose progress/API state
→ render one real LLM section in `/report/v2/{profile_id}`
```

## Verification plan

Docs-only verification:

```bash
cd frontend && npx prettier --check ../docs/features/E16-v2-e15-llm-runtime-integration/*.md ../docs/features/README.md ../docs/SRS/SRS-E16-astrotype-v2-cloud-core.md
cd .. && git diff --check -- docs/features/E16-v2-e15-llm-runtime-integration docs/features/README.md docs/SRS/SRS-E16-astrotype-v2-cloud-core.md
```

Implementation verification must add fresh commands to each story before marking it complete. Minimum expected final gates:

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy .
cd backend && uv run pytest tests/unit -q
cd frontend && npx eslint . && npx prettier --check . && rm -rf .next && npx tsc --noEmit --pretty false && npm test && npm run build
cd backend && uv run python ../scripts/smoke/astrotype-v2-full-flow.py --base-url http://127.0.0.1:3000 --backend-url http://127.0.0.1:8000 --timeout 600 --expect-provider deepseek --expect-model deepseek-v4-flash
```

## Non-negotiable secret handling

- Never commit `.env`, API keys, tokens or connection strings.
- Logs and smoke output may state that `LLM_API_KEY` is present, but must print `[REDACTED]` instead of the value.
- If a provider call fails due auth/quota/network, report that precise blocker; do not silently fall back to deterministic output and call it LLM-backed.
