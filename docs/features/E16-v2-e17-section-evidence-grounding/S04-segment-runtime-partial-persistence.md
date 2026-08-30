# S04: Harden segment runtime and partial persistence

## Status

✅ Реализовано

## Context

The current worker builds deterministic artifacts and LLM segments inside one task transaction. If one segment raises `SegmentValidationError`, the exception propagates through `asyncio.gather(...)`, the worker rolls back, and no user-visible report row is created.

This Story makes segment generation resilient at the section boundary.

## What to do

1. Persist chart, facts, synthesis, outline and infographic before LLM segment calls.
2. Generate each section independently and record per-section result.
3. Replace all-or-nothing `asyncio.gather(...)` behavior with section-level error handling.
4. Persist failed segment rows with error class/message and grounding context.
5. Assemble a `partial` report when deterministic foundation and at least one narrative segment are usable.
6. Keep strict validation for complete sections; do not accept ungrounded prose as ready.

## Segment statuses

Required statuses:

| Status | Meaning |
|---|---|
| `ready` | validated segment can be assembled |
| `running` | section is in progress |
| `failed_validation` | provider response parsed but violated segment contract |
| `failed_provider` | provider timeout, HTTP error, non-JSON, schema failure |
| `skipped_ungrounded` | section had no valid grounding and was not sent to LLM |

## Files affected

| File | Action |
|---|---|
| `backend/workers/tasks/astrotype_v2.py` | Persist deterministic stages before LLM; handle per-section exceptions |
| `backend/app/modules/astrotype_v2/models.py` | Add/confirm status/error fields if needed |
| `backend/app/modules/astrotype_v2/report_assembler.py` | Assemble partial reports safely |
| `backend/tests/unit/test_astrotype_v2/test_worker_runtime.py` | Add regression tests for one failed section not rolling back all artifacts |

## Acceptance criteria

- [x] One failed section no longer deletes chart/facts/synthesis/outline/infographic work.
- [x] Failed sections are visible in stored segment rows.
- [x] A partial report can be served when at least one segment is ready.
- [x] Complete reports still require all required sections to be ready.
- [x] Provider non-JSON and validation errors are classified separately.

## Verification

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_worker_runtime.py -v --tb=short
uv run pytest tests/unit/test_astrotype_v2/test_report_assembler.py -v --tb=short
uv run ruff check workers/tasks/astrotype_v2.py app/modules/astrotype_v2 tests/unit/test_astrotype_v2
uv run mypy workers/tasks/astrotype_v2.py app/modules/astrotype_v2 tests/unit/test_astrotype_v2
```

## Implementation notes

- `workers/tasks/astrotype_v2.py` now writes `running` segment rows before provider calls and commits that state separately from the final report assembly.
- LLM segment generation is isolated per section: `SegmentValidationError` becomes `failed_validation`; other provider/schema/runtime exceptions become `failed_provider`.
- `report_assembler.build_partial_natal_report_row(...)` assembles ready sections plus `segment_diagnostics` when at least one narrative segment is usable.
- Complete report assembly still requires every required section to be `ready`; failed sections are not accepted as complete prose.

Fresh verification on 2026-08-30:

```bash
cd backend
uv run pytest tests/unit/test_astrotype_v2/test_worker_runtime.py tests/unit/test_astrotype_v2/test_report_assembler.py tests/unit/test_astrotype_v2/test_api_runtime.py -q
# 20 passed

uv run ruff check workers/tasks/astrotype_v2.py app/modules/astrotype_v2/report_assembler.py tests/unit/test_astrotype_v2/test_worker_runtime.py tests/unit/test_astrotype_v2/test_report_assembler.py
# All checks passed!

uv run ruff format --check workers/tasks/astrotype_v2.py app/modules/astrotype_v2/report_assembler.py tests/unit/test_astrotype_v2/test_worker_runtime.py tests/unit/test_astrotype_v2/test_report_assembler.py
# 4 files already formatted

uv run mypy workers/tasks/astrotype_v2.py app/modules/astrotype_v2 tests/unit/test_astrotype_v2/test_worker_runtime.py tests/unit/test_astrotype_v2/test_report_assembler.py
# Success: no issues found in 25 source files
```
