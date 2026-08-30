# V2-E17: Section evidence grounding remediation

## Status

🟡 Частично закрыто в документации (S02-S07 closed; S01 needs follow-up evidence)

## Goal

Fix the v2 report-generation failure class where the worker attempts to generate upper narrative sections that do not have enough section-specific evidence. The pipeline must distribute deterministic chart facts into semantic report-section usages, enforce a pre-LLM grounding invariant, and preserve/diagnose partial progress instead of rolling back the whole report.

## Production incident trigger

On 2026-08-27 production worker logs showed repeated `astrotype_v2.generate_natal_report` failures:

```text
SegmentValidationError("missing evidence ids")
```

The immediate validator failure was correct: a generated segment had no `evidence_ids`. The root cause was earlier: the current synthesis maps nearly all extracted technical facts into `core_pattern`, while the outline always requests six sections. Several sections therefore receive zero owned evidence.

Root-cause architecture docs:

- `docs/architecture/astrotype-v2-section-evidence-grounding.md`;
- `docs/architecture/astrotype-v2-deterministic-first-delivery.md`.

## Scope

In scope:

- section-specific fact usage assignment from existing v2 chart/fact rows;
- coverage diagnostics for all six upper narrative sections;
- outline grounding statuses and pre-LLM invariant checks;
- segment orchestration that can mark one section failed/skipped without losing deterministic artifacts;
- persisted generation/status traceability by `generation_id`;
- API/debug surfaces that show why a section is ready, bridged, skipped, blocked, or failed.

## Out of scope

- Socionics, Model A, typology, archetype labels, or legacy v1 report fields.
- A broad rewrite of the chart engine.
- Making DeepSeek invent facts not present in deterministic inputs.
- Hiding validation errors by accepting ungrounded prose as a complete section.
- Frontend redesign beyond rendering the new statuses/errors if needed.

## Acceptance criteria

- [x] Every generated section has at least the configured minimum owned/reference evidence before LLM call.
- [x] Empty-evidence section prompts are impossible in the normal runtime path.
- [x] Technical facts can support multiple semantic section usages when astrologically justified.
- [x] `perception_and_mind`, `emotional_regulation`, `agency_and_desire`, and `relationships_and_intimacy` receive facts from relevant planets/houses/aspects/balances instead of defaulting to zero.
- [x] `ReportOutlineV2` exposes section grounding diagnostics.
- [x] Worker persists deterministic artifacts before LLM generation and does not roll them back because one segment fails.
- [x] `NatalReport(status="deterministic_ready")` is committed before the first LLM provider call, so users can see deterministic content immediately.
- [x] Generation status can be traced by `generation_id` from API response to worker/result/status rows.
- [x] Production smoke with real provider proves generated sections contain non-empty `evidence_ids`.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Reproduce current evidence starvation](./S01-reproduce-evidence-starvation.md) | ⬜ Не закрыто: original RED evidence not preserved in current tests |
| S02 | [Build section fact usage assignment](./S02-section-fact-usage-assignment.md) | ✅ Реализовано |
| S03 | [Enforce outline grounding invariant](./S03-outline-grounding-invariant.md) | ✅ Реализовано |
| S04 | [Harden segment runtime and partial persistence](./S04-segment-runtime-partial-persistence.md) | ✅ Реализовано |
| S05 | [Persist generation status and diagnostics](./S05-generation-status-diagnostics.md) | ✅ Реализовано |
| S06 | [Production smoke and backfill/retry runbook](./S06-production-smoke-retry-runbook.md) | ✅ Реализовано |
| S07 | [Deterministic-first report delivery](./S07-deterministic-first-report-delivery.md) | ✅ Реализовано |

## Implementation order

```text
S01 -> S02 -> S03 -> S07 -> S04 -> S05 -> S06
```

S01 must fail before implementation. S02/S03 fix the actual lack of section-specific facts. S07 creates the deterministic-visible report before any LLM call. S04/S05 make narrative failures observable and non-destructive. S06 proves the fix against production-like behavior.

## Verification

Docs-only verification:

```bash
git diff --check -- docs/architecture/astrotype-v2-section-evidence-grounding.md docs/features/E16-v2-e17-section-evidence-grounding docs/features/README.md docs/SRS/SRS-E16-astrotype-v2-cloud-core.md
```

Implementation verification will be added to each Story. Minimum expected backend gates:

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_fact_section_assignment.py -v --tb=short
uv run pytest tests/unit/test_astrotype_v2/test_outline.py tests/unit/test_astrotype_v2/test_segment_inputs.py -v --tb=short
uv run pytest tests/unit/test_astrotype_v2/test_api_runtime.py -v --tb=short
uv run ruff check app/modules/astrotype_v2 tests/unit/test_astrotype_v2
uv run mypy app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```

## Documentation audit — 2026-08-30

Fresh audit command:

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_fact_section_assignment.py tests/unit/test_astrotype_v2/test_outline.py tests/unit/test_astrotype_v2/test_segment_inputs.py tests/unit/test_astrotype_v2/test_report_assembler.py::test_build_deterministic_natal_report_row_exposes_calculation_layer_before_segments tests/unit/test_astrotype_v2/test_worker_runtime.py tests/unit/test_astrotype_v2/test_api_runtime.py -q
```

Result: `25 passed`.

Closed in this audit:

- S02 section fact usage assignment;
- S03 outline grounding invariant.

Not closed:

- S01: the current test suite verifies the fixed behavior, but does not preserve the original standalone RED evidence-starvation reproduction required by that Story.

Closed after this audit:

- S07: frontend generation-status polling and deterministic-first render are implemented; the old `deterministic_failed` wording was corrected to the implemented `failed` deterministic-phase status.
