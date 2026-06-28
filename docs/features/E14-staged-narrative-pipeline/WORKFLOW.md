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

If one stage fails validation:

1. Retry only that stage once with a repair prompt.
2. If still invalid, mark that stage `failed` with error metadata.
3. Do not overwrite previously ready stages.
4. Mark the whole report `narrative_failed` or keep it in `generating_narrative` according to retry policy.
5. UI shows retry/unavailable state, not a fake fallback report.

## Regenerate path

`POST /api/v1/reports/{id}/narrative/regenerate` should support:

- full regenerate;
- stage-specific regenerate in future admin/debug tools;
- preserving deterministic report if `DeepNatalSynthesis.input_hash` is unchanged;
- invalidating dependent downstream stages when upstream plan changes.

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
