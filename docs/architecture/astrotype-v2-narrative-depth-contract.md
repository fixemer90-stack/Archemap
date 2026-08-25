# Astrotype v2 Narrative Depth Contract

## Purpose

Astrotype v2 Self report is not a short astrological overview. Its upper narrative layer must deeply analyze the person from the natal chart: how chart factors combine into psychological mechanisms, lived scenarios, tensions, protections and mature forms.

This document hardens the generation contract after local testing showed that technically valid sections can still feel poor: too short, too generic, too close to a placement summary, or not recognizably about a person.

## Product principle

A good section is not “more words”. A good section contains more layers of meaning.

Every upper narrative section must transform source evidence through this chain:

```text
chart evidence
→ psychological mechanism
→ lived manifestation
→ inner tension or polarity
→ protective/shadow strategy
→ mature/integrated expression
→ soft self-check question or integration cue
```

The LLM may mention chart factors when useful, but it must not render a list of placements, aspects, houses or balances. Technical evidence belongs to the lower deterministic calculation layer and factual basis, not to the human narrative as raw material.

## Non-goals

The depth contract must not turn the report into:

- a broad shallow overview of every life domain;
- a generic horoscope;
- a table explanation in prose;
- a psychometric diagnosis;
- socionics, Model A, MBTI or any other typology layer;
- a career/love/child report hidden inside the natal Self report.

Depth means staying inside the current section and explaining it thoroughly, not expanding into unrelated product scopes.

## Section length and paragraph rhythm

The current active code-level minimum of 3 paragraphs / 80 words is only a technical emptiness guard. It is not a product-quality requirement.

Target depth requirements:

| Section                        | Target length | Paragraph rhythm         |
| ------------------------------ | ------------: | ------------------------ |
| `core_pattern` / Ядро личности | 450–700 words | 4–6 developed paragraphs |
| `perception_and_mind`          | 300–500 words | 3–5 developed paragraphs |
| `emotional_regulation`         | 300–500 words | 3–5 developed paragraphs |
| `agency_and_desire`            | 300–500 words | 3–5 developed paragraphs |
| `relationships_and_intimacy`   | 300–500 words | 3–5 developed paragraphs |
| `growth_vector`                | 300–500 words | 3–5 developed paragraphs |

Provider output limits are infrastructure constraints. If a section is cut by the provider, the segment runner must request continuation for the same section rather than compress the report into a short summary.

## Mandatory depth moves per section

Each generated section must contain these moves, explicitly or naturally in prose:

1. central formula — what pattern this section is really about;
2. mechanism — how the pattern operates internally;
3. lived manifestation — how it is visible in ordinary decisions, relationships, work, stress or self-regulation;
4. tension — what internal contradiction, polarity or pressure appears;
5. protection/shadow — what the person tends to do when unsafe, pressured, unseen or overwhelmed;
6. mature form — how the same material becomes strength when integrated;
7. grounding — coverage of owned themes and evidence ids without raw fact dumping.

A section is underdeveloped if it names traits but does not explain how they work in life.

## Section-specific contracts

### `core_pattern` / Ядро личности

Purpose: assemble the central personality formula, not a chart summary.

Required content:

- what organizes identity, attention and decision-making;
- what the person is trying to protect or stabilize inside;
- the main inner contradiction or polarity;
- how the pattern appears in everyday life without becoming a broad life-domain overview;
- what happens under pressure or insecurity;
- mature integration: how the same pattern becomes strength;
- one gentle self-check or integration question.

Forbidden:

- listing Sun/Moon/Ascendant/house placements as the structure of the text;
- repeating every owned evidence item mechanically;
- replacing the central formula with a generic “you are complex and balanced” summary.

### `perception_and_mind`

Purpose: explain how perception, thinking, interpretation and decision-making work.

Required content:

- attention style: what the person notices first;
- how they verify truth or reject weak claims;
- how stress changes thinking;
- where analysis becomes avoidance, rigidity or overload;
- mature use of mind: when clarity becomes service to action rather than control.

### `emotional_regulation`

Purpose: explain emotional rhythm, safety, recovery and defensive regulation.

Required content:

- what kinds of atmosphere calm or destabilize the person;
- how feelings move through the body/mind before expression;
- what the person does when emotions feel unsafe;
- how relational context affects regulation;
- mature form: naming, boundaries, repair, restoration.

### `agency_and_desire`

Purpose: explain will, initiative, desire, anger, inertia and action.

Required content:

- what turns action on;
- what blocks or delays action;
- how pressure changes desire or resistance;
- immature expression: stubbornness, passivity, overcontrol, impulsive compensation, etc. when supported by evidence;
- mature expression: chosen movement, clean boundaries, sustainable effort.

### `relationships_and_intimacy`

Purpose: explain closeness, attachment, trust, relational testing and intimacy dynamics.

Required content:

- how the person approaches closeness;
- what they need to trust another person;
- what they test or watch for in contact;
- protective strategy when the relationship field feels unsafe;
- mature intimacy: clarity, vulnerability, boundaries, repair.

### `growth_vector`

Purpose: define a development vector, not generic advice.

Required content:

- what must be integrated, not erased;
- what old protection becomes too costly;
- what practice or orientation helps the person mature;
- how growth would look behaviorally;
- one practical self-check question or integration cue.

## Prompt requirements

The segment prompt must explicitly say:

```text
This is not a broad overview. Write a deep psychological reading of this one section.
Do not summarize placements. Convert evidence into lived psychological mechanisms.
A paragraph is invalid if it only names a trait without explaining how it operates in real life.
For core_pattern write 450–700 words in 4–6 paragraphs.
For other upper sections write 300–500 words in 3–5 paragraphs.
Each section must include: mechanism, lived manifestation, tension, protection/shadow and mature expression.
If the answer would be cut by provider limits, set continuation_complete=false; do not compress.
```

Retry prompts must preserve the same depth requirement. They must not say “expand to at least 80 words” as the final bar; that is a technical floor only.

## Validation requirements

Validators should reject a section when:

- word count is below the section target floor;
- paragraph count is below the section target floor;
- required depth moves are missing;
- the body contains raw technical dumps such as `is in`, `with orb`, `house 10`, or English placement/aspect lists;
- the prose is generic enough to fit almost anyone;
- owned evidence ids are not covered;
- forbidden theme ids are expanded;
- the section compresses instead of requesting continuation.

Validators should not reject a grounded valid section merely because it is long.

## Deterministic synthesis requirements

The LLM cannot reliably produce depth from only raw placements. The deterministic synthesis layer provides richer fields for each theme:

- `psychological_mechanism`;
- `lived_manifestation`;
- `inner_tension`;
- `protective_strategy`;
- `immature_expression`;
- `mature_expression`;
- `integration_question`;
- `evidence_strength`;
- `contradictions` / `compensations` where present.

Prompts still require the LLM to transform these fields into prose rather than copy raw facts, and quality gates flag thin output.

## Smoke examples

A local smoke report is acceptable only when checks show:

- `core_pattern` is not a raw fact dump;
- every upper section has the target paragraph count and word floor;
- at least one paragraph in each section contains a concrete lived scenario;
- at least one paragraph names a risk/protection/shadow pattern;
- at least one paragraph names a mature/integrated expression;
- the lower calculation layer remains deterministic and separate.

## Implementation feature

Implementation is tracked by:

- `docs/features/E16-v2-e16-narrative-depth-quality/FEATURE.md`
