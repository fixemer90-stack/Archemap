# V2-E16: Narrative depth quality

## Status

⬜ Не начато

## Goal

Harden Astrotype v2 narrative generation so the upper report is a deep psychological reading of the person, not a short overview, generic horoscope, or prose version of technical chart tables.

The feature turns the product requirement “глубоко разобрать человека” into implementable contracts: section-specific prompt requirements, richer synthesis inputs, validation quality gates, and local/real-provider smoke tests.

## Problem

Current local testing exposed a quality gap:

- the prompt says “deep, expanded, specific prose”, but the enforced minimum is only 3 paragraphs / 80 words;
- deterministic fallback can avoid raw fact dumps but still remains a fallback, not a deep reading;
- LLM segments can pass schema validation while still being too short, abstract or generic;
- source facts are often technical placements/aspects, so the LLM may summarize rather than synthesize lived mechanisms;
- simulated LLM output is useful for layout smoke, but it must not become the quality bar.

## Product contract

Canonical depth contract:

- `docs/architecture/astrotype-v2-narrative-depth-contract.md`

The report must transform evidence through this chain:

```text
chart evidence
→ psychological mechanism
→ lived manifestation
→ inner tension or polarity
→ protective/shadow strategy
→ mature/integrated expression
→ soft self-check question or integration cue
```

This is not a broad life-domain overview. Each section stays inside its purpose and goes deeper into the mechanism.

## Dependencies

- V2-E5 Fact extraction
- V2-E6 Synthesis & outline
- V2-E7 Modular LLM generation
- V2-E8 Final report assembly
- V2-E14 QA, smoke, rollout
- V2-E15 LLM runtime integration

Related docs:

- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-narrative-depth-contract.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`

## Scope

In scope:

- replace low prompt depth floors with section-specific length and paragraph requirements;
- define section-specific narrative moves for all upper report sections;
- add validators for shallow/generic/underdeveloped output;
- enrich deterministic synthesis inputs with mechanism/tension/protection/maturity fields;
- add simulated and real-provider smoke fixtures for narrative depth;
- keep calculation layer deterministic and separate from LLM prose.

Out of scope:

- adding socionics, Model A, MBTI or typology labels;
- expanding Self report into Career/Love/Child reports;
- changing billing/access model;
- requiring real LLM calls in ordinary unit tests;
- marking implementation complete from docs-only work.

## Acceptance criteria

- [ ] Prompt contract distinguishes technical emptiness floor from product depth target.
- [ ] `core_pattern` requires 700–1200 words and 6–9 developed paragraphs unless continuation is needed.
- [ ] Other upper sections require 450–900 words and 4–7 developed paragraphs unless continuation is needed.
- [ ] Every upper section requires mechanism, lived manifestation, tension, protection/shadow and mature expression.
- [ ] Retry prompts preserve depth requirements instead of shrinking to “at least 80 words”.
- [ ] Validators reject raw fact dumps, shallow/generic sections and missing depth moves.
- [ ] Validators allow long grounded sections and use continuation/chunking for provider output limits.
- [ ] Deterministic synthesis exposes or plans richer fields needed for depth: mechanism, manifestation, tension, protection, immature/mature expression and integration cue.
- [ ] Local simulated LLM smoke and real-provider smoke check the same quality gates.
- [ ] Final report assembly and frontend rendering preserve long validated sections.

## Stories

| ID  | Story                                                                                 | Status       |
| --- | ------------------------------------------------------------------------------------- | ------------ |
| S01 | [Depth prompt contracts](./S01-depth-prompt-contracts.md)                             | ⬜ Не начато |
| S02 | [Depth validation gates](./S02-depth-validation-gates.md)                             | ⬜ Не начато |
| S03 | [Deep synthesis inputs](./S03-deep-synthesis-inputs.md)                               | ⬜ Не начато |
| S04 | [Narrative depth smoke fixtures](./S04-narrative-depth-smoke-fixtures.md)             | ⬜ Не начато |
| S05 | [Reader/PDF long-section preservation](./S05-reader-pdf-long-section-preservation.md) | ⬜ Не начато |

## Implementation order

```text
S01 → S02 → S03 → S04 → S05
```

S01 and S02 may be implemented before S03, but S03 is required for consistently deep real output. Without richer synthesis, the prompt will keep asking the LLM to infer too much from raw chart facts.

## Verification

Docs-only verification:

```bash
git diff --check -- docs/architecture/astrotype-v2-narrative-depth-contract.md docs/features/E16-v2-e16-narrative-depth-quality docs/features/README.md docs/ROADMAP-v2.md docs/SRS/SRS-E16-astrotype-v2-cloud-core.md
```

Implementation verification must add targeted backend tests for prompt construction, segment validation and report assembly before any story is marked complete.
