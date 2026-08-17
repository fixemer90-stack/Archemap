# V2-E15 API: LLM narrative runtime contract

## Цель документа

Этот документ фиксирует API/state contract для перехода Astrotype v2 на real LLM narrative sections.

Документ дополняет:

- `FEATURE.md`
- `WORKFLOW.md`
- `../../SRS/SRS-E16-astrotype-v2-cloud-core.md`
- `../E16-v2-e10-api-async-runtime/FEATURE.md`
- `../E16-v2-e11-web-responsive-reader/FEATURE.md`

## Report generation entrypoint

Existing preferred entrypoint:

```http
POST /api/v1/astrotype-v2/reports
```

Request shape:

```json
{
  "profile_id": "uuid",
  "force": false
}
```

Expected behavior:

- If deterministic foundation exists and generation is already running, return current report/progress identity.
- If deterministic foundation is missing, enqueue/build deterministic foundation first.
- If deterministic foundation is ready but narrative is missing/failed, enqueue narrative segment generation.
- Do not create duplicate chart/report rows for concurrent `force=false` requests.

## Report read endpoint

```http
GET /api/v1/astrotype-v2/reports/{report_id}
```

Response must distinguish deterministic and narrative readiness.

Required high-level fields:

```json
{
  "contract_version": "astrotype_v2_report_api_v1",
  "report": {
    "id": "uuid",
    "status": "deterministic_ready|narrative_generating|narrative_partial|narrative_ready|narrative_failed",
    "deterministic_payload": {},
    "narrative_payload": null,
    "assembled_payload": null
  },
  "progress": {},
  "infographic": {},
  "segments": []
}
```

Rules:

- `deterministic_payload` must remain present after LLM failures.
- `infographic.calculation_layer` must remain LLM-free.
- `narrative_payload` may be null while segments are generating.
- Partial ready segments may be returned in `segments` even before `narrative_payload` is complete.

## Progress endpoint

Preferred existing endpoint:

```http
GET /api/v1/astrotype-v2/reports/{report_id}/progress
```

Required fields:

```json
{
  "contract_version": "astrotype_v2_report_progress_v1",
  "report_id": "uuid",
  "chart_id": "uuid",
  "status": "deterministic_ready|narrative_generating|narrative_partial|narrative_ready|narrative_failed",
  "total_segments": 6,
  "ready_segments": 1,
  "failed_segments": 0,
  "running_segments": 1,
  "segments": [
    {
      "section_key": "core-pattern",
      "status": "ready",
      "provider": "deepseek",
      "model": "deepseek-v4-flash",
      "prompt_version": "astrotype_v2_section_core_pattern_v1",
      "error": null
    }
  ]
}
```

Frontend rendering rules:

| Progress state         | Frontend behavior                                            |
| ---------------------- | ------------------------------------------------------------ |
| `deterministic_ready`  | Show deterministic report foundation and narrative skeleton. |
| `narrative_generating` | Continue polling; show per-section progress.                 |
| `narrative_partial`    | Render ready sections; show pending/failed placeholders.     |
| `narrative_ready`      | Render complete narrative + calculation layer.               |
| `narrative_failed`     | Preserve deterministic report; show retry/error state.       |

## Segment contract

Each persisted segment generation row should expose/debug at least:

```json
{
  "section_key": "core-pattern",
  "status": "ready|pending|running|failed",
  "provider": "deepseek",
  "model": "deepseek-v4-flash",
  "prompt_version": "astrotype_v2_section_core_pattern_v1",
  "input_hash": "sha256:...",
  "attempt_count": 1,
  "payload": {
    "section_id": "core-pattern",
    "title": "Ядро личности",
    "body": "...",
    "evidence_ids": ["fact:..."],
    "covered_theme_ids": ["theme:..."]
  },
  "error": null
}
```

Backend may keep full raw provider response in internal/debug fields, but user-facing API must not leak secrets or provider credentials.

## Regenerate / retry semantics

Preferred endpoint:

```http
POST /api/v1/astrotype-v2/reports/{report_id}/regenerate
```

Request shape:

```json
{
  "mode": "failed_segments|all_narrative|full_if_input_changed",
  "section_keys": ["core-pattern"]
}
```

MVP acceptable simplification:

- `force=false`: return existing ready/running report identity;
- `force=true`: clear/retry narrative segments but preserve deterministic foundation when input hash is unchanged.

Rules:

- Retrying failed narrative must not recalculate chart/facts by default.
- If birth/profile source input changed, deterministic input hash changes and full deterministic regeneration is allowed.
- A retry should keep old successful segment payloads unless mode explicitly asks for all narrative.

## Error contract

Provider/runtime errors must be precise.

Examples:

```json
{
  "status": "narrative_failed",
  "error": {
    "code": "provider_timeout",
    "message": "LLM provider timed out after 180 seconds",
    "retryable": true,
    "section_key": "core-pattern"
  }
}
```

Allowed error codes:

- `provider_timeout`
- `provider_error`
- `invalid_json`
- `schema_error`
- `business_validation_error`
- `persistence_error`
- `configuration_error`

Forbidden behavior:

- Do not return HTTP 200 with `provider=deterministic` while claiming real LLM success.
- Do not erase deterministic payload on narrative failure.
- Do not return generic `Internal Server Error` to frontend when a typed narrative error exists.

## Smoke contract

Real-provider local smoke should prove:

```text
backend health OK
frontend route OK
LLM env visible to worker with key redacted
provider tiny request OK
report generation started
progress reached narrative_ready or documented narrative_partial/failure
segments have provider=deepseek and model=deepseek-v4-flash
/report/v2/{profile_id} returns HTTP 200
```

CI/mock smoke should prove:

```text
LLM_ENABLED=false or LLM_PROVIDER=mock
no real credentials required
pipeline contracts and validators remain green
frontend build remains green
```

## Security notes

- LLM API key is backend/worker-only.
- Frontend receives only status/provider/model names, never credentials.
- Logs may state API key presence as boolean or `[REDACTED]` only.
- Provider raw response must not include prompt secrets in user-facing payloads.
