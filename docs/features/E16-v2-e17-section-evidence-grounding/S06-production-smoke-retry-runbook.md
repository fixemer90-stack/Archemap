# S06: Production smoke and backfill/retry runbook

## Status

✅ Реализовано

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

- [x] A new production-like report reaches `complete` or intentional `partial`.
- [x] `GET /reports/generations/{generation_id}` shows real state.
- [x] All generated ready sections have non-empty evidence ids.
- [x] Worker logs can be correlated by generation id.
- [x] Failed old generations can be retried without manual DB surgery.
- [x] Runbook explicitly forbids destructive cleanup of generated production data.

## Verification

Production smoke recorded on 2026-08-30 after deploying commit `0dd47f7` to backend/worker.

```text
Profile id: 548049cd-99d3-4186-ae5b-fc53a64b05e7
Generation id: 4034efcf-b27c-4867-a30f-5cf00de22b65
Celery task id: 34d24fb1-1b68-45aa-9db8-3453e1ef7155
Report id: e21c7daf-4257-408c-9d66-5106e3fd26b6
Final status: complete
Health: {"status":"ok","database":"ok","redis":"ok"}
Worker log correlation: generation_id=true, celery_task_id=true
```

Status endpoint proof:

```text
POLL 1 queued None
POLL 2 complete e21c7daf-4257-408c-9d66-5106e3fd26b6
GENERATION_ROW 4034efcf-b27c-4867-a30f-5cf00de22b65|34d24fb1-1b68-45aa-9db8-3453e1ef7155|e21c7daf-4257-408c-9d66-5106e3fd26b6|complete
```

Ready section evidence counts:

```text
agency_and_desire:ready:8
core_pattern:ready:9
emotional_regulation:ready:3
growth_vector:ready:18
perception_and_mind:ready:12
relationships_and_intimacy:ready:4
```

All ready sections have non-empty `evidence_ids`.
