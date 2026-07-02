# E15 Workflow — Humanized Self Report Storytelling

## User-facing scenario

A user opens a ready Self report. The deterministic calculation may be correct, but the report feels too formal: it explains placements and mechanisms without enough human recognition.

E15 changes the narrative generation and rendering path so the user first receives a readable portrait, while evidence and calculation remain available below or collapsed.

## Flow

```text
Profile + chart snapshot
  -> deterministic report + DeepNatalSynthesis
  -> shared staged plan
  -> humanized section prompts v2
  -> deterministic assembler with paragraph rhythm
  -> tone/evidence validators
  -> stored SelfNarrative JSON
  -> web/PDF rendering
```

## What the LLM receives

The LLM receives curated structured data only:

- evidence map;
- planet roles;
- house axis patterns;
- aspect patterns;
- chart dynamics;
- contradictions;
- maturity levels;
- calibration hypotheses;
- previous stage outputs when assembling.

It must not receive permission to invent chart facts, diagnoses, or a Career/Love report.

## What changes for the reader

### First screen

Before: starts with placements and abstract mechanisms.

After: starts with recognition-first prose: how the pattern is likely experienced in life. Technical facts can appear later in a support/evidence layer.

### Section body

Before: one compact paragraph that summarizes a mechanism.

After: 2–3 readable paragraphs when justified:

1. human meaning;
2. lived manifestation;
3. tension/risk and mature form.

### Evidence

Evidence does not disappear. It moves to secondary disclosure so trust is available without making the first read feel like a debug view.

## Failure behavior

If humanized tone validation fails:

1. try one repair/regeneration path if provider/policy supports it;
2. if still invalid, do not publish fake “ready” prose;
3. keep existing report status policy: deterministic report remains intact, narrative reports failure/unavailable according to current E11/E14 rules.

## Rollout

- New staged prompt versions create new generation/cache keys.
- Existing reports are not destructively deleted.
- Users can receive the new prose through regenerate/refresh path.
- The reference report should be used as a local smoke case before broad rollout.
