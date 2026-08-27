# Astrotype v2 deterministic-first delivery

## Purpose

This document defines the required Astrotype v2 runtime boundary: deterministic natal report data must become visible before any LLM narrative section is generated.

The product promise is not "wait until the whole large narrative report is ready". The product promise is:

1. calculate deterministic natal foundation quickly;
2. persist it durably;
3. return a usable report shell immediately;
4. generate LLM narrative sections progressively;
5. keep deterministic data available even if LLM generation fails.

This document complements:

- `docs/architecture/astrotype-v2-section-evidence-grounding.md`;
- `docs/features/E16-v2-e17-section-evidence-grounding/FEATURE.md`;
- `docs/features/E16-v2-e17-section-evidence-grounding/WORKFLOW.md`.

## Production problem

A production report generation failed because an LLM segment had no valid evidence ids. That exposed a second architectural issue: the user had to wait for the whole report because the current worker creates the `NatalReport` row only after all LLM segments complete.

Current worker shape:

```python
chart = ...
facts = ...
synthesis = ...
outline = ...
infographic = ...
segments = await _ensure_ready_segments(...)
report = build_natal_report_row(...)
await repository.add(report)
await db.commit()
```

On any exception, the worker rolls back:

```python
except Exception:
    await db.rollback()
    raise
```

Therefore, if LLM generation fails:

- deterministic chart/facts/synthesis/outline/infographic work is not visible as a report;
- no `report_id` is returned to the client;
- the user sees waiting/failure instead of deterministic-ready content;
- operators cannot diagnose progress from a persisted report row.

## Required invariant

The required invariant is:

```text
No LLM provider call may happen before deterministic report commit.
```

More explicitly:

```text
chart + facts + synthesis + outline + infographic + report(status=deterministic_ready)
MUST be persisted and committed before the first LLM segment request.
```

This is a hard runtime boundary, not an optimization.

## Target lifecycle

```text
queued
  -> deterministic_running
  -> deterministic_ready
  -> narrative_generating
  -> partial
  -> complete
```

Failure variants:

```text
queued -> deterministic_running -> deterministic_failed
queued -> deterministic_running -> deterministic_ready -> narrative_generating -> partial
queued -> deterministic_running -> deterministic_ready -> narrative_generating -> narrative_failed
```

Meaning:

| Status | Meaning | User-visible behavior |
|---|---|---|
| `queued` | request accepted; no work started yet | waiting state |
| `deterministic_running` | chart/facts/synthesis/outline are being built | short waiting state |
| `deterministic_ready` | report row exists with deterministic payload | show report shell, chart, facts, infographic/calculation layer |
| `narrative_generating` | LLM sections are running | show deterministic report plus generation progress |
| `partial` | at least one narrative section is ready, at least one is not | show ready sections and diagnostics for missing sections |
| `complete` | all required narrative sections are ready | show full report |
| `deterministic_failed` | deterministic foundation could not be built | show actionable failure; no report shell unless safe fallback exists |
| `narrative_failed` | deterministic report exists, but no narrative section could be completed | show deterministic report plus narrative failure diagnostics |

## Required worker flow

The worker must split deterministic and narrative transactions.

### Phase 1: deterministic transaction

```python
async with async_session_factory() as db:
    generation = await mark_generation_running(...)
    profile = await load_profile(...)
    chart = await get_or_create_chart(...)
    facts = await get_or_create_facts(...)
    synthesis = await get_or_create_synthesis(...)
    outline = await get_or_create_outline(...)
    infographic = await get_or_create_infographic(...)
    report = await get_or_create_report(
        status="deterministic_ready",
        deterministic_payload=build_deterministic_payload(...),
        narrative_payload={},
        assembled_payload={},
    )
    generation.report_id = report.id
    generation.status = "deterministic_ready"
    await db.commit()
```

After this commit, the client must be able to fetch `GET /api/v1/astrotype-v2/reports/{report_id}` and render deterministic content.

### Phase 2: narrative transactions

Each section runs after deterministic commit:

```python
for section in grounded_sections:
    await mark_segment_running(report_id, section_id)
    try:
        segment = await generate_one_segment(...)
        await persist_ready_segment(segment)
    except ValidationError as exc:
        await persist_failed_segment(section_id, "failed_validation", exc)
    except ProviderError as exc:
        await persist_failed_segment(section_id, "failed_provider", exc)
    await update_report_partial_or_complete(report_id)
    await db.commit()
```

A section failure must not delete or hide deterministic output.

## Required API behavior

### POST generation response

The POST endpoint may return `202 queued` immediately, but status polling must expose the deterministic report id as soon as Phase 1 commits.

Preferred response once deterministic phase finishes quickly:

```json
{
  "contract_version": "astrotype_v2_generation_job_v1",
  "generation_id": "...",
  "status": "deterministic_ready",
  "profile_id": "...",
  "report_id": "...",
  "links": {
    "report": "/api/v1/astrotype-v2/reports/...",
    "progress": "/api/v1/astrotype-v2/reports/generations/..."
  }
}
```

If the initial POST returns before deterministic work finishes, the generation status endpoint must later return the `report_id`:

```json
{
  "generation_id": "...",
  "status": "deterministic_ready",
  "report_id": "...",
  "deterministic": {
    "chart_ready": true,
    "facts_count": 54,
    "synthesis_ready": true,
    "outline_ready": true,
    "infographic_ready": true
  },
  "narrative": {
    "status": "narrative_generating",
    "ready_segments": 0,
    "total_segments": 6
  }
}
```

### Report read response

`GET /api/v1/astrotype-v2/reports/{report_id}` must support deterministic-ready reports:

```json
{
  "contract_version": "astrotype_v2_report_api_v1",
  "report": {
    "id": "...",
    "status": "deterministic_ready",
    "deterministic_payload": {...},
    "narrative_payload": {},
    "assembled_payload": {}
  },
  "outline": {...},
  "infographic": {...},
  "facts": [...],
  "segments": [],
  "progress": {
    "status": "narrative_generating",
    "ready_segments": 0,
    "running_segments": 6,
    "failed_segments": 0
  }
}
```

The endpoint must not require complete narrative sections before returning deterministic content.

## Required frontend behavior

The frontend must not wait for `complete` before rendering.

Required states:

| API state | Frontend behavior |
|---|---|
| `queued` | small loading state |
| `deterministic_running` | small loading state |
| `deterministic_ready` | render deterministic report shell immediately; show narrative progress |
| `narrative_generating` | render deterministic shell plus ready narrative sections as they arrive |
| `partial` | render deterministic shell plus ready sections; show failed/skipped section diagnostics softly |
| `complete` | render full report |
| `deterministic_failed` | show hard error with retry/support diagnostics |
| `narrative_failed` | render deterministic report plus narrative failure message and retry action |

Frontend polling must use `generation_id` until `report_id` exists, then it may switch to report/progress endpoints.

## How the client knows the rest is ready

The client learns that the remaining narrative report is ready through the persisted generation/progress state, not through a long blocking registration request.

Required client sequence after registration/profile completion:

1. The registration/profile completion flow receives or follows a v2 generation handle:
   - `generation_id` immediately;
   - `report_id` once deterministic phase commits.
2. While only `generation_id` is known, the client polls:

   ```text
   GET /api/v1/astrotype-v2/reports/generations/{generation_id}
   ```

3. As soon as that response contains `report_id` and `status=deterministic_ready|narrative_generating|partial|complete`, the client fetches the report:

   ```text
   GET /api/v1/astrotype-v2/reports/{report_id}
   ```

4. While the report is not terminal, the client polls either the generation status endpoint or report progress endpoint:

   ```text
   GET /api/v1/astrotype-v2/reports/generations/{generation_id}
   GET /api/v1/astrotype-v2/reports/{report_id}/progress
   ```

5. The client stops polling when status is terminal:
   - `complete`;
   - `narrative_failed`;
   - `deterministic_failed`.

6. For `partial`, the client keeps deterministic content visible, inserts ready sections, and may continue polling until `complete` or `narrative_failed` depending on retry policy.

Minimum polling payload:

```json
{
  "generation_id": "...",
  "report_id": "...",
  "status": "narrative_generating",
  "narrative": {
    "ready_segments": 2,
    "running_segments": 3,
    "failed_segments": 1,
    "total_segments": 6
  },
  "links": {
    "report": "/api/v1/astrotype-v2/reports/...",
    "progress": "/api/v1/astrotype-v2/reports/.../progress"
  }
}
```

MVP transport is polling. SSE/WebSocket/push may be added later, but they are not required for the deterministic-first contract. If added, they must publish the same persisted statuses and must not become the source of truth.

## Data model requirements

The implementation may use existing tables plus a new generation-status table, but the data model must support:

- generation id -> user id/profile id/report id;
- deterministic phase status and timestamps;
- narrative phase status and timestamps;
- per-section status and diagnostics;
- retry/regeneration lineage;
- owner-scoped API access.

`NatalReport.status` must be allowed to represent at least:

- `deterministic_ready`;
- `narrative_generating`;
- `partial`;
- `complete`;
- `narrative_failed`.

## Acceptance criteria

- A report row is created and committed before first LLM provider call.
- `GET /reports/{report_id}` returns useful deterministic content for `status=deterministic_ready`.
- If every LLM segment fails, deterministic report remains fetchable.
- If one LLM segment fails, other segments and deterministic content remain fetchable.
- Frontend renders deterministic chart/facts/infographic/calculation layer before full narrative completion.
- Generation status endpoint returns real `report_id` once deterministic phase commits.
- Tests prove transaction boundaries: deterministic commit happens before LLM; LLM failure does not roll back deterministic report.

## Verification plan

Unit tests:

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_worker_runtime.py -v --tb=short
uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py -v --tb=short
```

Frontend tests:

```bash
cd frontend
npm run lint
npm run typecheck
```

Production smoke:

1. Start generation for a completed profile.
2. Poll by `generation_id` until `report_id` appears.
3. Fetch `GET /reports/{report_id}` while narrative is still running.
4. Confirm deterministic payload, facts, outline and infographic are present.
5. Simulate or observe LLM section failure.
6. Confirm deterministic report remains available and status is `partial` or `narrative_failed`, not missing/queued forever.
