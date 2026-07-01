# E14 Workflow — Staged Self Narrative Generation

## User entry point

User opens or generates a Self report exactly as today:

```text
/report/{profile_id}
POST /api/v1/reports/generate { profile_id, product: "self", mode: "full" }
```

The user should not see internal LLM stages as separate content. They may see progress copy such as “анализируем аспекты”, “собираем внутренний механизм”, “проверяем связность”, but the final Self report appears only when all required stages are valid.

## Why staged pipeline exists

The current single-shot narrative generation asks one LLM response to do too many things:

- read all natal facts;
- decide what is central;
- interpret aspects;
- write all sections;
- keep Self/Career boundary;
- produce exact JSON;
- avoid hallucinations and unsafe language.

E14 splits this into deterministic synthesis + smaller LLM tasks.

## Happy path

```text
1. Deterministic report exists or is generated.
2. DeepNatalSynthesisBuilder creates a grounded synthesis from report_data.
3. Stage 1 LLM creates NarrativePlan from DeepNatalSynthesis.
4. Stage 2 LLM section tasks run in parallel using the same NarrativePlan.
5. Deterministic validators check each stage:
   - schema
   - evidence refs
   - section boundaries
   - unsupported claims
   - safety language
6. Assembler merges stage outputs into SelfNarrativeVNext.
7. Final consistency check removes duplicates and contradiction drift.
8. ReportNarrative is saved as ready.
9. Web/PDF render the assembled narrative.
```

## Stage map

| Stage                           | Source                                 | Output                 | LLM?     | Parallel? |
| ------------------------------- | -------------------------------------- | ---------------------- | -------- | --------- |
| Deterministic synthesis         | `Report.report_data`                   | `DeepNatalSynthesis`   | No       | No        |
| Narrative plan                  | `DeepNatalSynthesis`                   | `NarrativePlan`        | Yes      | No        |
| Identity/perception section     | Plan + relevant synthesis slice        | `IdentitySection`      | Yes      | Yes       |
| Emotional/communication section | Plan + Moon/Mercury/aspect slice       | `EmotionalSection`     | Yes      | Yes       |
| Relationships/sexuality section | Plan + Venus/Mars/7th/8th/aspect slice | `RelationshipSection`  | Yes      | Yes       |
| Development/maturity section    | Plan + tensions/failures/calibration   | `DevelopmentSection`   | Yes      | Yes       |
| House scenarios section         | Plan + house axis patterns             | `HouseScenarioSection` | Yes      | Yes       |
| Assembly                        | all sections                           | `SelfNarrativeVNext`   | Optional | No        |

## What is sent to LLM

LLM receives only curated structures:

- `NarrativePlanInput`;
- `DeepNatalSynthesis` slices;
- section-specific evidence map;
- product boundaries;
- required JSON schema.

LLM must not receive:

- raw DB rows;
- auth/user secrets;
- payment info;
- unrestricted `report_data` dump;
- unsupported chart objects not converted into evidence.

## Aspect interpretation workflow

Aspects are handled before prose:

```text
raw chart.aspects
  → normalize aspect ids and labels
  → score by orb + planet importance + aspect type + section relevance
  → group into patterns
  → classify support/tension/mixed/integration
  → map to mechanism/risk/mature expression
  → expose top aspect patterns to LLM
```

The LLM should not decide which of 20+ aspects are important from a flat list. It receives ranked and clustered aspect patterns.

## Failure path

Current shipped behavior is fail-fast at the narrative level, with selective resume on the next staged attempt.

If one stage fails validation or late assembly fails:

1. Retry only the failing stage for invalid structured output inside the same running task.
2. If that stage still fails, mark that stage `failed` with error metadata.
3. Persist `stage_progress` and `stage_artifacts` snapshots into `ReportNarrative.content` for polling/debugging and recovery.
4. Mark the whole narrative/report `narrative_failed`.
5. UI shows retry/unavailable state, not a fake fallback report.

Current selective resume behavior:

- previously ready stage outputs are preserved as resumable artifacts when their `input_hash`, `prompt_version` and `model_name` still match;
- a later retry/regenerate reuses valid ready artifacts;
- only missing/failed/stale stages plus downstream `assembly` are regenerated.

This means a late `assembly` or validation error no longer has to rerun every section stage when ready section artifacts are still valid.

## Selective resume behavior

`S08-selective-stage-resume.md` defines the recovery model. On the next retry after a failed/interrupted staged run, the service should:

1. Recompute expected input hashes for all stages.
2. Reuse every persisted `ready` stage artifact whose input/dependency/version hashes still match.
3. Regenerate only the failed, missing or stale stage.
4. Regenerate downstream dependents of that stage, such as `assembly` and `final_validation`.
5. Keep unrelated ready sibling sections instead of calling the LLM for them again.

Example: if `relationship_section` fails, retry should reuse `narrative_plan`, `identity_section`, `emotional_section`, `development_section` and `house_scenarios_section`, then regenerate only `relationship_section`, `assembly` and `final_validation`.

Example: if final `assembly` validation fails, retry should reuse all ready section artifacts and regenerate only `assembly` plus `final_validation`.

This target behavior must still publish the final Self report only after every required stage is valid. Partial artifacts are checkpoints, not partial user-visible report content.

## Regenerate path

Current shipped regenerate behavior:

```text
POST /api/v1/reports/{id}/narrative/regenerate
  -> enqueue generate_report_narrative(force=true)
  -> reuse the matching ReportNarrative row
  -> keep persisted stage_artifacts for staged selective resume
  -> clear error/timestamps and mark the row pending
  -> recompute stage hashes
  -> reuse valid ready stage artifacts
  -> regenerate failed/missing/stale stages and downstream assembly
```

Current regenerate does support:

- retrying narrative generation without recomputing deterministic report data when the deterministic report itself is still current;
- preserving the deterministic report layer outside narrative generation;
- preserving staged artifacts during forced staged regenerate so retry can resume from ready blocks;
- rerunning only the failed section or failed `assembly` plus required downstream assembly/final validation work.

Current regenerate does not support yet:

- public request-body scopes for `stage`, `failed_stages` or explicit `full`;
- separate `report_narrative_stages` history table;
- lease-timeout recovery job for permanently stuck `running` stages.

## User-visible progress copy

Allowed progress labels:

- “Собираем карту в смысловые доминанты”;
- “Анализируем аспекты и внутренние напряжения”;
- “Собираем жизненные сценарии домов”;
- “Пишем связный Self-отчёт”;
- “Проверяем, что выводы опираются на карту”.

Forbidden progress labels:

- “LLM думает”;
- “генерируем гороскоп”;
- raw stage ids like `self_section_relationships_v1`;
- any promise of psychological diagnosis.
