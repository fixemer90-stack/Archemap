# E14 API and Status Contract

## Public API compatibility

E14 should not require a new user-facing endpoint for MVP. Existing endpoints remain:

```text
POST /api/v1/reports/generate
GET /api/v1/reports/{report_id}
GET /api/v1/reports
POST /api/v1/reports/{report_id}/narrative/regenerate
GET /api/v1/reports/{report_id}/pdf
```

The response contract expands narrative metadata and internal status details.

## Report status state machine

```text
deterministic_ready
  -> generating_narrative
  -> ready
  -> narrative_failed
```

E14 adds stage progress while keeping top-level statuses compatible.

## Narrative stage statuses

Suggested enum:

```ts
type NarrativeStageStatus =
  | "pending"
  | "running"
  | "ready"
  | "repairing"
  | "failed"
  | "skipped";
```

Suggested stage ids:

```ts
type NarrativeStageId =
  | "deep_natal_synthesis"
  | "narrative_plan"
  | "identity_section"
  | "emotional_section"
  | "relationship_section"
  | "development_section"
  | "house_scenarios_section"
  | "assembly"
  | "final_validation";
```

## Response shape extension

```json
{
  "id": "report-id",
  "status": "generating_narrative",
  "narrative": null,
  "narrative_progress": {
    "current_stage": "relationship_section",
    "completed_stages": 3,
    "total_stages": 9,
    "label": "Собираем сценарии близости и отношений",
    "stages": [
      {
        "stage_id": "deep_natal_synthesis",
        "status": "ready",
        "duration_ms": 120,
        "error_message": null
      }
    ]
  }
}
```

## Ready response

```json
{
  "id": "report-id",
  "status": "ready",
  "narrative": {
    "status": "ready",
    "prompt_version": "self_staged_v1",
    "content": {
      "title": "Self-отчёт: ...",
      "hero": {},
      "dominants": [],
      "aspect_patterns": [],
      "inner_mechanism": {},
      "house_scenarios": [],
      "sections": [],
      "final_summary": "..."
    }
  }
}
```

## Regenerate request

The request body is optional. Omitting it keeps the default selective resume behavior:

```http
POST /api/v1/reports/{report_id}/narrative/regenerate
```

Optional body:

```json
{
  "scope": "failed_stages" | "stage" | "full",
  "stage_id": "relationships"
}
```

Scope semantics:

- omitted / `failed_stages`: preserve valid `stage_artifacts`, rerun failed/missing/stale stages plus downstream `assembly`;
- `stage`: invalidate the requested stage and downstream `assembly`, while reusing valid upstream and sibling stages;
- `full`: clear prior narrative content/stage artifacts and start staged generation from `plan` intentionally.

Current server-side behavior for staged Self narratives:

```text
force=true
  -> matching ReportNarrative row is reused
  -> status becomes pending
  -> existing stage_artifacts are preserved
  -> error_message is cleared
  -> generation timestamps are cleared
  -> worker recomputes expected stage hashes
  -> valid ready stage artifacts are reused
  -> failed/missing/stale stages and downstream assembly are regenerated
```

Important current contract:

- regenerate is selective resume for staged Self narratives when reusable `stage_artifacts` exist;
- deterministic report data is not recomputed by narrative regenerate;
- explicit `scope: "full"` clears previous narrative content and stage artifacts intentionally;
- persisted `narrative_progress`, `stage_resume` and `stage_artifacts` must not expose prompts or provider payloads.

Implemented S08 behavior:

- default staged regenerate performs selective resume when valid stage artifacts exist;
- `scope: "failed_stages"` reruns failed/missing/stale stages plus downstream `assembly`;
- `scope: "stage"` reruns the requested stage plus downstream `assembly` while reusing valid upstream and sibling stages;
- `scope: "full"` starts from scratch intentionally;
- API response exposes safe `narrative.stage_resume` metadata with `resume_mode`, `reused_stages`, `regenerated_stages`, `stale_stages` and `reason`.

Example selective progress payload:

```json
{
  "narrative_progress": {
    "current_stage": "assembly",
    "resume_mode": "resume",
    "reused_stages": [
      "narrative_plan",
      "identity_section",
      "emotional_section",
      "development_section",
      "house_scenarios_section"
    ],
    "regenerated_stages": [
      "relationship_section",
      "assembly",
      "final_validation"
    ],
    "label": "Переиспользуем готовые блоки и пересобираем проблемный шаг"
  }
}
```

## API acceptance criteria

- Top-level report status remains backward compatible.
- Stage metadata never exposes prompt bodies, API keys or raw provider payloads.
- Stage errors are human-safe and operator-debuggable.
- `GET /reports/{id}` can render progress without leaking internal implementation details.
- Ready response includes only validated final narrative, not partial raw sections.
- PDF endpoint uses the same assembled narrative content as web.
