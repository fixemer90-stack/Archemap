# V2-E7 S02: Write segment prompt contracts

## Status

✅ Завершено

## Context

This story belongs to `V2-E7 — Modular LLM generation`.

Create prompt contracts for the upper narrative sections: core, mind, emotions, agency, relationships and growth. The prompts must produce large, specific, human, non-summary report prose.

## Prompt contract

Each prompt must tell the LLM:

- write only the requested personality section;
- use only the provided JSON facts/themes/evidence;
- cover every owned theme deeply enough;
- follow `docs/architecture/astrotype-v2-narrative-depth-contract.md`;
- transform evidence into psychological mechanism, lived manifestation, tension, protection/shadow and mature expression;
- avoid generic horoscope filler;
- avoid socionics, archetypes and typology labels;
- do not write the deterministic lower calculation layer;
- return typed JSON matching `ReportSegmentOutputV2`.

## No artificial length cap rule

Prompt text must not say:

```text
be brief
short summary
max 3 paragraphs
keep under N characters
concise overview only
```

Unless a provider-specific emergency continuation prompt is being used, the default instruction should be:

```text
write a detailed, expanded section; continue until the section purpose and owned evidence are fully covered.
```

If output is cut by provider token limits, the runner should request continuation for the same segment, not accept a shallow section as complete.

The historical 3-paragraph / 80-word check is only a technical emptiness guard. It is not sufficient for product depth; V2-E16 defines the stricter implementation work.

## Files likely affected

| Path                                               | Action                                            |
| -------------------------------------------------- | ------------------------------------------------- |
| `backend/app/modules/astrotype_v2/llm_segments.py` | Prompt construction / provider call.              |
| `backend/app/modules/astrotype_v2/prompts/`        | Prompt templates if split into files.             |
| `backend/tests/unit/test_astrotype_v2/`            | Prompt contract tests when implementation starts. |

## Acceptance criteria

- [x] Prompt contracts exist for every upper narrative section.
- [x] Prompts require expanded, specific, non-summary prose.
- [x] Prompts do not include artificial low length caps.
- [x] Prompts require typed JSON output.
- [x] Prompts forbid invented chart facts and forbidden themes.
- [x] Prompts exclude lower deterministic calculation-layer rendering.

## Verification commands

Fill with targeted prompt/contract tests when implementation starts.
