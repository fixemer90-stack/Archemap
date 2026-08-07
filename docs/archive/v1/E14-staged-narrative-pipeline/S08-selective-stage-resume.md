# S08 — Selective Stage Resume for Staged Narrative Generation

> Статус: 🟡 Частично готово
> Тип: reliability / cost-control / operator UX
> Feature: E14 — Staged Narrative Pipeline
> Реализовано: default staged regenerate reuses valid persisted artifacts; `failed_stages`, `stage`, and `full` API scopes are supported; safe `stage_resume` metadata is exposed in the narrative API response.
> Осталось: stage history table, lease-timeout recovery job.

## Context

Current shipped E14 behavior persists `stage_progress` and `stage_artifacts`, but uses them only for polling and debugging. If generation fails late — for example at `assembly` or final validation — the next regenerate starts from `plan` again and repeats every LLM stage.

That is wasteful and makes failures harder to recover from:

- a single invalid section can force a full narrative rerun;
- a late quality-gate failure can discard ready section outputs;
- a worker interruption can leave useful completed stages unused;
- repeated LLM calls increase cost and time even when upstream inputs did not change.

S08 defines the target behavior: staged narrative generation should resume from valid persisted stage artifacts and regenerate only the failed or invalidated stage plus its downstream dependents.

## Goal

When a staged narrative run fails or is interrupted, the next retry/regenerate must not automatically start from scratch. The system should reuse ready stage artifacts whose inputs are still valid and rebuild only the minimal affected subgraph.

## Non-goals

- Do not expose partial report prose as a user-visible final report.
- Do not let users manually edit stage JSON.
- Do not reuse artifacts if deterministic report data, prompt version, model contract, schema version, or relevant input hash changed.
- Do not hide final validation failures by publishing a partial/fallback narrative.
- Do not make LLM output authoritative over deterministic evidence refs.

## Stage dependency graph

```text
deep_natal_synthesis
  -> narrative_plan
      -> identity_section
      -> emotional_section
      -> relationship_section
      -> development_section
      -> house_scenarios_section
          -> assembly
              -> final_validation
                  -> ready narrative
```

Dependency rules:

| Stage                  | Can reuse when                                                                    | Must invalidate when                                                                                     |
| ---------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `deep_natal_synthesis` | deterministic report input hash is unchanged                                      | `Report.report_data`, builder version, synthesis schema, or calculation quality changes                  |
| `narrative_plan`       | synthesis hash + prompt/model/schema versions unchanged                           | synthesis changes or plan prompt/schema changes                                                          |
| section stages         | plan hash + section input slice hash + prompt/model/schema unchanged              | plan changes, section-specific synthesis slice changes, prompt/schema changes, or explicit section retry |
| `assembly`             | all required section artifact hashes unchanged + assembly prompt/schema unchanged | any section changes, assembly validation fails, or final validation requires rewrite                     |
| `final_validation`     | assembled narrative hash unchanged + validator version unchanged                  | assembly changes or validator rules change                                                               |

## Artifact contract

Each persisted stage artifact must be recoverable as an execution checkpoint, not only as progress metadata.

Minimum fields:

```ts
type NarrativeStageArtifact = {
  stage_id: NarrativeStageId;
  status:
    | "pending"
    | "running"
    | "ready"
    | "repairing"
    | "failed"
    | "stale"
    | "skipped";
  prompt_version: string;
  model_provider: string;
  model_name: string;
  schema_version: string;
  validator_version: string;
  input_hash: string;
  output_hash: string | null;
  dependency_hashes: Record<NarrativeStageId, string>;
  attempt_count: number;
  error_message: string | null;
  failure_kind: string | null;
  artifact: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
};
```

Rules:

- `ready` artifacts with matching input/dependency/version hashes may be reused.
- `failed` artifacts are never reused as outputs, but their error metadata is kept for diagnostics.
- `running` artifacts older than the worker lease timeout are treated as interrupted and become retryable.
- `stale` means the artifact was once ready but no longer matches current inputs or versions.
- `artifact` must contain only validated structured output, never raw provider payloads or prompt bodies.

## Resume planner

Before each narrative generation attempt, build a resume plan from the current report input and persisted artifacts.

Pseudo-flow:

```text
1. Load latest ReportNarrative for report_id.
2. Load persisted stage_artifacts.
3. Recompute expected input hashes for every stage.
4. Mark each artifact:
   - reusable: status=ready and all hashes/versions match;
   - retryable: status=failed/running/repairing or missing artifact;
   - stale: hashes/versions do not match.
5. Walk the dependency graph topologically.
6. Reuse reusable upstream artifacts.
7. Regenerate the first non-reusable stage and every downstream dependent stage.
8. Persist progress after each stage.
9. Publish final narrative only after assembly + final_validation pass.
```

Example resume plan after `relationship_section` fails:

```json
{
  "mode": "resume",
  "reuse": [
    "deep_natal_synthesis",
    "narrative_plan",
    "identity_section",
    "emotional_section",
    "development_section",
    "house_scenarios_section"
  ],
  "regenerate": ["relationship_section", "assembly", "final_validation"],
  "reason": "relationship_section failed validation"
}
```

Example resume plan after late `assembly` validation fails:

```json
{
  "mode": "resume",
  "reuse": [
    "deep_natal_synthesis",
    "narrative_plan",
    "identity_section",
    "emotional_section",
    "relationship_section",
    "development_section",
    "house_scenarios_section"
  ],
  "regenerate": ["assembly", "final_validation"],
  "reason": "assembly failed final quality gate"
}
```

## Retry / regenerate semantics

### Default regenerate

`POST /api/v1/reports/{report_id}/narrative/regenerate` should default to selective resume when reusable artifacts exist.

```text
regenerate default
  -> compute resume plan
  -> reuse valid ready artifacts
  -> rerun failed/stale/missing stages and downstream dependents
```

### Force full regenerate

A full rerun remains available for operator/debug cases:

```json
{
  "scope": "full",
  "force": true
}
```

Full regenerate must:

- mark existing artifacts stale or superseded;
- recompute from `deep_natal_synthesis` / `narrative_plan` onward;
- preserve old artifacts only for audit/debug if storage supports history.

### Stage-specific regenerate

For targeted repair:

```json
{
  "scope": "stage",
  "stage_id": "relationship_section"
}
```

Behavior:

- reuse all valid upstream dependencies;
- regenerate the requested stage;
- invalidate and regenerate downstream dependents;
- do not regenerate unrelated sibling sections unless their dependency hashes changed.

### Failed-stages-only regenerate

For operator-friendly retry:

```json
{
  "scope": "failed_stages"
}
```

Behavior:

- regenerate only failed/missing/stale stages plus downstream dependents;
- reuse all valid ready stages;
- if no reusable artifacts exist, fall back to full staged generation.

## Worker interruption handling

If the worker dies mid-run:

1. The latest persisted artifact snapshot remains the source of truth.
2. Any `running` stage whose `updated_at` is older than the lease timeout is considered interrupted.
3. On next retry, completed `ready` stages are reused.
4. Interrupted stages and downstream dependents are regenerated.
5. The report must not remain permanently stuck in `generating_narrative`; a recovery job or next API-triggered retry must move it to a retryable state.

Suggested timeout:

```text
stage_running_lease_timeout = max(10 minutes, 2x configured provider timeout)
```

## API response additions

During generation, expose a human-safe resume summary:

```json
{
  "narrative_progress": {
    "current_stage": "assembly",
    "completed_stages": 7,
    "total_stages": 9,
    "resume_mode": "resume",
    "reused_stages": [
      "narrative_plan",
      "identity_section",
      "emotional_section"
    ],
    "regenerated_stages": ["assembly", "final_validation"],
    "label": "Переиспользуем готовые блоки и пересобираем финальную связку"
  }
}
```

Do not expose:

- prompt bodies;
- provider raw responses;
- internal stack traces;
- raw DB rows;
- secrets/API keys.

## Logging / observability

Each generation attempt should log:

- `resume_mode`: `full` | `resume` | `stage` | `failed_stages`;
- `reused_stages`;
- `regenerated_stages`;
- `stale_stages`;
- `resume_reason`;
- per-stage `input_hash`, `output_hash`, `failure_kind`, `recovery_action`.

Example:

```text
report_narrative_resume_plan_created
  report_id=...
  narrative_id=...
  resume_mode=resume
  reused_stages=identity_section,emotional_section,development_section
  regenerated_stages=relationship_section,assembly,final_validation
  resume_reason=failed_stage:relationship_section
```

## Acceptance criteria

- [x] A failed section retry reuses valid `deep_natal_synthesis`, `narrative_plan`, and unrelated ready sibling sections at planner level.
- [x] A failed `assembly` retry reuses all ready section artifacts and reruns only `assembly` in the current implementation model.
- [x] If `Report.report_data` changes, the narrative input hash changes and old matching narrative rows are not reused.
- [x] If a stage prompt version changes, the affected artifact is not reused because `prompt_version` must match.
- [ ] Interrupted `running` stages become retryable after lease timeout instead of leaving report permanently stuck.
- [x] API progress can show which stages were reused vs regenerated without exposing raw prompts/provider payloads.
- [x] Public request-body scopes for explicit `stage`, `failed_stages`, and full-force regenerate are implemented.
- [x] Tests cover resume planning for failed section and service-level failed assembly selective resume.

## Fresh verification evidence

- `pytest /app/tests/unit/test_report_narratives -q` → `107 passed`
- `pytest /app/tests/unit/test_reports -q` → `36 passed`
- `ruff check` for changed backend files/tests → `All checks passed!`
- `ruff format --check` for changed backend files/tests → `8 files already formatted`
- `mypy` for changed backend files/tests → `Success: no issues found in 8 source files`
- `prettier --check` for E14 docs → `All matched files use Prettier code style!`

## Verification plan

Backend unit tests:

```bash
cd backend
python -m pytest tests/unit/test_report_narratives/test_resume_planner.py -q
python -m pytest tests/unit/test_report_narratives/test_service.py -q
python -m pytest tests/unit/test_report_narratives/test_tasks.py -q
```

Backend quality:

```bash
cd backend
python -m ruff check app/modules/report_narratives tests/unit/test_report_narratives
python -m mypy app/modules/report_narratives tests/unit/test_report_narratives
```

Runtime smoke:

```text
1. Generate Self report until section artifacts are ready.
2. Inject or reproduce a section validation failure.
3. Retry narrative generation.
4. Verify logs show reused upstream/sibling stages.
5. Verify only failed/downstream stages receive new attempt timestamps/output hashes.
6. Verify final report reaches ready.
```

## Implementation notes

Recommended implementation order:

1. Introduce a pure `ResumePlanner` with deterministic inputs and unit tests.
2. Make persisted `stage_artifacts` round-trip into typed stage outputs.
3. Teach `ReportNarrativeService` to accept a resume plan.
4. Change default regenerate from full rerun to selective resume.
5. Add explicit force-full behavior for admin/debug use.
6. Add stale/running lease recovery.
7. Extend API progress metadata and frontend copy.
8. Add runtime smoke coverage.

Keep the planner pure and separately testable: it should not call the LLM, database, or provider. It should only decide `reuse`, `regenerate`, and `stale` from current expected hashes plus persisted artifact metadata.
