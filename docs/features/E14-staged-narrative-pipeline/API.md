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
  "pending" | "running" | "ready" | "repairing" | "failed" | "skipped";
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

MVP keeps existing body optional:

```http
POST /api/v1/reports/{report_id}/narrative/regenerate
```

Future debug/admin extension:

```json
{
  "scope": "full" | "failed_stages" | "stage",
  "stage_id": "relationship_section",
  "force": true
}
```

## API acceptance criteria

- Top-level report status remains backward compatible.
- Stage metadata never exposes prompt bodies, API keys or raw provider payloads.
- Stage errors are human-safe and operator-debuggable.
- `GET /reports/{id}` can render progress without leaking internal implementation details.
- Ready response includes only validated final narrative, not partial raw sections.
- PDF endpoint uses the same assembled narrative content as web.
