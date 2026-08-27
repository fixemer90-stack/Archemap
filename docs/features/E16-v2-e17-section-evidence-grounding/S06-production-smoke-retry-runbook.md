# S06: Production smoke and backfill/retry runbook

## Status

⬜ Не начато

## Context

After the grounding/runtime fixes, production needs a safe operator path to verify new reports and retry reports that previously failed because of missing evidence ids.

## What to do

1. Write a production smoke command sequence for one real-provider generation.
2. Verify status by `generation_id`, not only by final report id.
3. Verify every generated section has non-empty `evidence_ids`.
4. Verify ungrounded/skipped sections, if any, are represented intentionally.
5. Add a safe retry/regenerate runbook for failed profiles/reports.
6. Document how to inspect worker logs, generation rows, segment rows and report rows.
7. Do not delete generated data or truncate production tables.

## Runbook requirements

The runbook must include:

- health checks for backend, Redis, Postgres and worker;
- how to start a generation from API/frontend/admin context;
- how to query generation status by id;
- SQL snippets for report/segment/section diagnostics;
- log grep snippets by `generation_id` and Celery task id;
- retry/regenerate command or API request;
- rollback/disable switch if real-provider failures spike.

## Files affected

| File | Action |
|---|---|
| `docs/deployment/production-vps.md` | Add troubleshooting section or link new runbook |
| `docs/features/E16-v2-e17-section-evidence-grounding/RUNBOOK.md` | Create operator runbook |
| `backend/tests/unit/test_astrotype_v2/*` | Add smoke helper tests if needed |

## Acceptance criteria

- [ ] A new production-like report reaches `complete` or intentional `partial`.
- [ ] `GET /reports/generations/{generation_id}` shows real state.
- [ ] All generated ready sections have non-empty evidence ids.
- [ ] Worker logs can be correlated by generation id.
- [ ] Failed old generations can be retried without manual DB surgery.
- [ ] Runbook explicitly forbids destructive cleanup of generated production data.

## Verification

Production-like smoke should record exact command outputs in this Story before marking it complete.

```bash
curl -fsS https://astrotype.ru/api/v1/health
# authenticated generation request here
# authenticated generation status lookup here
# DB/worker diagnostics here
```
