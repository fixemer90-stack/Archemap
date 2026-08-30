# ADR-009: Temporary hard-fail segment depth validation must be replaced

## Status

Accepted as temporary mitigation.

## Date

2026-08-30

## Context

Astrotype v2 generates the upper narrative report as section-level LLM segments. The product contract requires every section to be a deep psychological reading, not a shallow horoscope, raw astrological fact dump, or generic overview.

The current implementation enforces part of that contract in `backend/app/modules/astrotype_v2/segment_validation.py`. It validates schema, section identity, evidence coverage, forbidden theme expansion, typology leakage, raw fact dumps, generic filler, word/paragraph floors and required depth moves.

The production incident for profile `548049cd-99d3-4186-ae5b-fc53a64b05e7` showed the architectural weakness:

- a generated segment could be semantically acceptable but fail because the validator looked for narrow lexical markers such as `проявляется`, `в жизни`, `повседнев`;
- the validator treated that semantic-style check as a hard exception in the critical generation path;
- the worker then hit a secondary failure while marking the report as failed, leaving the report stuck in `narrative_generating`;
- the user-facing result was “report did not assemble” instead of a deterministic report with a degraded or repairable narrative layer.

A narrow production fix expanded the Russian marker list and fixed worker error handling. That fix is not the final architecture. It only reduces one false-negative class.

## Decision

The current string-marker depth validator is accepted only as a temporary production guard.

Astrotype v2 must replace hard-fail lexical depth validation with a layered validation and recovery policy:

1. Keep hard validation for objective contract violations:
   - JSON/schema validity;
   - `section_id` mismatch;
   - missing/unknown `evidence_ids`;
   - missing owned theme coverage;
   - forbidden theme expansion;
   - typology/socionics leakage;
   - raw chart fact dumps;
   - technically empty or clearly underdeveloped output.

2. Move semantic depth checks out of the all-or-nothing critical path:
   - mechanism / lived manifestation / tension / protection / mature expression checks should not depend on a tiny list of exact words;
   - absence of one detected move should trigger repair, warning, `degraded` status, or reviewer-visible diagnostics rather than making the whole report fail by default;
   - lexical markers may be used as heuristics, not as the only source of truth.

3. Persist usable deterministic and partial narrative state before and after LLM failures:
   - deterministic chart/facts/synthesis/outline/report payloads must remain readable;
   - segment failures must be persisted at segment level with error context;
   - the report must not remain indefinitely in `narrative_generating`;
   - frontend/API should be able to render deterministic fallback or partial narrative when narrative generation is imperfect.

4. Introduce a replacement design before tightening prose-quality gates further.

## Replacement direction

The target validator should separate four concerns:

| Layer | Behavior | Failure mode |
| --- | --- | --- |
| Contract validator | Checks schema, ids, ownership, forbidden themes, typology leakage, raw fact dumps. | Hard fail; segment is invalid. |
| Technical completeness validator | Checks empty output, minimum words/paragraphs, continuation flags. | Hard fail or continuation request. |
| Quality rubric evaluator | Scores or classifies mechanism, manifestation, tension, protection, mature expression, specificity and human readability. | Warning, repair retry, or degraded narrative; not automatic report failure. |
| Runtime recovery policy | Decides whether to retry same section, persist partial report, show deterministic fallback, or expose regeneration. | Explicit status transition; never silent hanging. |

The quality rubric may be implemented with a structured self-critique prompt, a small deterministic rubric over explicit JSON fields, an LLM judge constrained to section input, or a hybrid. The exact replacement requires a separate implementation story.

## Consequences

Positive:

- fewer false production failures from valid Russian prose that uses different wording;
- clearer separation between objective data-contract failures and subjective quality concerns;
- better user experience: deterministic reports and partial narrative can still render;
- easier debugging because segment-level errors are explicit and persisted.

Negative / trade-offs:

- weak narrative may occasionally pass as `degraded` rather than being blocked;
- frontend/API must represent more states than `generating` / `complete` / `failed`;
- a rubric/recovery design is more work than a regex-like validator;
- tests must cover state transitions, not only pure validation functions.

## Follow-up work

Create a feature/story set to replace temporary depth hard-fails with layered validation and recovery:

- define `degraded` / `repair_pending` / `partial` statuses for segment/report progress if they are product-approved;
- persist failed or degraded segment rows without losing deterministic report state;
- update report progress API and frontend reader states;
- add tests for false-positive/false-negative prose cases;
- add a production smoke that proves a single weak segment does not leave the report stuck in `narrative_generating`;
- retire `_validate_required_depth_moves` as a hard exception or limit it to a non-blocking diagnostic.

## Related documents

- `docs/architecture/astrotype-v2-narrative-depth-contract.md`
- `docs/architecture/astrotype-v2-deterministic-first-delivery.md`
- `docs/features/E16-v2-e16-narrative-depth-quality/FEATURE.md`
- `docs/features/E16-v2-e17-section-evidence-grounding/FEATURE.md`
- `backend/app/modules/astrotype_v2/segment_validation.py`
- `backend/workers/tasks/astrotype_v2.py`
