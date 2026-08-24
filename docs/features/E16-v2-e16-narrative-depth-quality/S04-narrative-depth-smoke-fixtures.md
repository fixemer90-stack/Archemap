# V2-E16 S04: Narrative depth smoke fixtures

## Status

✅ Готово

## Context

Local simulation is useful when the real provider is unavailable, but it must not become a fake proof of LLM quality. Smoke fixtures must distinguish:

- deterministic fallback;
- simulated LLM-style output;
- real-provider output;
- provider failure/degraded states.

This story adds repeatable smoke checks for depth without requiring real LLM calls in ordinary unit tests.

## What to do

1. Add fixture data for a known local profile/report path.
2. Add simulated LLM segment payloads that satisfy the depth contract.
3. Add negative fixtures:
   - raw fact dump;
   - 80-word shallow answer;
   - generic horoscope filler;
   - section missing mature expression;
   - section missing lived scenario.
4. Add a smoke script that loads the latest report and checks narrative quality markers.
5. Add an optional real-provider smoke path that runs only when credentials/quota are available.
6. Ensure smoke output states clearly whether it used simulated or real provider data.

## Files likely affected

| Path                                    | Action                                                                |
| --------------------------------------- | --------------------------------------------------------------------- |
| `backend/tests/fixtures/astrotype_v2/`  | Add positive/negative narrative fixtures.                             |
| `backend/tests/unit/test_astrotype_v2/` | Add fixture validation tests.                                         |
| `backend/scripts/` or `scripts/`        | Add local narrative-depth smoke command if project convention allows. |
| `docs/implementation/`                  | Add runbook if a manual smoke command is introduced.                  |

## Acceptance criteria

- [x] Positive simulated fixtures pass the depth validator.
- [x] Negative fixtures fail for the expected reason.
- [x] Smoke output names the generation mode: deterministic, simulated LLM or real provider.
- [x] Real-provider smoke is optional and skipped honestly when provider quota/auth is unavailable.
- [x] Smoke does not claim real LLM quality from simulated text.

## Verification commands

```bash
cd backend && uv run pytest tests/unit/test_astrotype_v2 -q --tb=short
# Optional when real provider is configured and funded:
# cd backend && LLM_ENABLED=true LLM_PROVIDER=deepseek uv run python <smoke-script>
```
