# Astrotype v2 QA smoke rollout

## Status

✅ Verified

## Goal

Provide one reproducible QA smoke gate for Astrotype v2 that proves:

- actual report readiness, not infra health only
- same report id across web, Android/PWA and optional desktop
- facts shown to user match report evidence ids
- infographics render from deterministic data
- no excluded typology appears in v2 payloads/prompts/UI
- segment-level retry recovery
- LLM cost, latency and failures by segment

## Verification source

Primary automated gate:

```bash
uv run pytest tests/unit/test_astrotype_v2/test_qa_smoke_rollout.py -q
```

Supporting regression slice:

```bash
uv run pytest tests/unit/test_astrotype_v2/test_report_assembler.py tests/unit/test_astrotype_v2/test_infographic_data.py tests/unit/test_astrotype_v2/test_api_runtime.py -q
```

## What the smoke bundle proves

1. A deterministic lower layer can be built from v2-only rows.
2. Synthesis, outline, segments and final report assembly produce a ready report.
3. Runtime readiness is based on completed report assembly and ready segments, not a generic process health signal.
4. Facts exposed to the user stay anchored to evidence ids used by narrative sections.
5. Web, Android/PWA and optional desktop resolve the same report id.
6. Retry scope is section-only when one segment fails.

## Rollout checklist

Required observability keys:

- `llm_cost_by_segment`
- `llm_latency_by_segment`
- `llm_failures_by_segment`
- `generation_recovery_rate`
- `report_ready_latency`
- `rollback_to_previous_main_sha`

## Notes

This is a contract-level smoke harness, not a live environment probe. It intentionally verifies the v2 assembly/runtime contract offline and guards against typology leakage inside the assembled payload path.
