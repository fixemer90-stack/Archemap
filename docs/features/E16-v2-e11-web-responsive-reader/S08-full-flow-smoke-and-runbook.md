# S08: Full-flow smoke and runbook

## Status

⬜ Не начато

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

- [ ] One command proves the full local V2 flow.
- [ ] Smoke output includes report status, progress, sections, calculation layer and forbidden marker check.
- [ ] Runbook names backend, frontend, Postgres, Redis and Celery prerequisites.

## Verification

```bash
python3 scripts/smoke/astrotype-v2-full-flow.py --base-url http://127.0.0.1:3000 --backend-url http://127.0.0.1:8000
```
