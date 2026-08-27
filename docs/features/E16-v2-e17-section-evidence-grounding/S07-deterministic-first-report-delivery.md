# S07: Deterministic-first report delivery

## Status

⬜ Не начато

## Context

The v2 data model already has a `deterministic_ready` report status, but the current worker creates the `NatalReport` row only after all LLM segments complete. If one LLM section fails validation/provider handling, the worker rolls back and the user sees no deterministic report.

This Story makes deterministic delivery a hard runtime boundary:

```text
No LLM provider call before deterministic report commit.
```

Architecture contract: `docs/architecture/astrotype-v2-deterministic-first-delivery.md`.

## What to do

1. Split worker execution into deterministic and narrative phases.
2. In the deterministic phase, build and commit:
   - chart;
   - facts;
   - synthesis;
   - outline;
   - infographic/calculation layer;
   - `NatalReport(status="deterministic_ready")`.
3. Return or persist `report_id` as soon as deterministic phase commits.
4. Start LLM segment generation only after the deterministic report is fetchable.
5. Update report status progressively:
   - `deterministic_ready`;
   - `narrative_generating`;
   - `partial`;
   - `complete`;
   - `narrative_failed`.
6. Ensure LLM failures do not roll back deterministic artifacts.
7. Update frontend polling so it can render deterministic content before narrative completion.

## Files affected

| File | Action |
|---|---|
| `backend/workers/tasks/astrotype_v2.py` | Split deterministic and narrative transactions |
| `backend/app/modules/astrotype_v2/report_assembler.py` | Support deterministic-only and partial report assembly |
| `backend/app/modules/astrotype_v2/api_runtime.py` | Return deterministic-ready report/progress payloads |
| `backend/app/modules/astrotype_v2/router.py` | Expose report once deterministic phase commits |
| `frontend/src/lib/astrotype-v2/use-v2-report-generation.ts` | Poll by generation id until report id exists; render deterministic report before complete |
| `frontend/src/lib/api/astrotype-v2.ts` | Add real generation status type/client if needed |
| `frontend/src/app/(dashboard)/report/v2/[profileId]/page.tsx` | Render deterministic-ready/partial states |
| `backend/tests/unit/test_astrotype_v2/test_worker_runtime.py` | Prove deterministic commit before LLM and no rollback on LLM failure |

## Acceptance criteria

- [ ] Worker commits `NatalReport(status="deterministic_ready")` before any LLM provider call.
- [ ] `GET /api/v1/astrotype-v2/reports/{report_id}` returns deterministic payload, facts, outline and infographic before narrative completion.
- [ ] If all LLM sections fail, the deterministic report remains available.
- [ ] If one section fails, the report becomes `partial` or remains deterministic-ready with diagnostics, not missing.
- [ ] Frontend displays deterministic content as soon as it exists.
- [ ] Generation status endpoint exposes `report_id` immediately after deterministic commit.
- [ ] Tests verify transaction boundaries and frontend state behavior.

## Verification

Backend:

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_worker_runtime.py -v --tb=short
uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py -v --tb=short
uv run ruff check app/modules/astrotype_v2 workers/tasks tests/unit/test_astrotype_v2
uv run mypy app/modules/astrotype_v2 workers/tasks tests/unit/test_astrotype_v2
```

Frontend:

```bash
cd frontend
npm run lint
npm run typecheck
```

Production-like smoke:

```text
POST generation -> poll generation_id -> receive report_id at deterministic_ready -> fetch report -> see deterministic payload while narrative is still running/failing.
```
