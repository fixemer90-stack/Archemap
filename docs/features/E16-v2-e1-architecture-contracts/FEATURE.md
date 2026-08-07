# V2-E1: Architecture & contracts

## Status

🟡 Contract documentation aligned; implementation not started

## Goal

Freeze the Astrotype v2 product and engineering boundaries before implementation: natal-only cloud-core, PostgreSQL source of truth, deterministic chart/fact/derived-calculation layers available immediately after registration/profile completion when enough birth data is present, builder-created JSON inputs for bounded async LLM personality-section generation, progressive narrative completion, and a canonical report layout where deterministic natal facts/calculations are not blocked by LLM output.

## Current canonical report sample

The current sample is the visual/product contract for the report shape:

- `docs/design/astrotype-v2-infographic-db-report-sample.html`
- `docs/design/astrotype-v2-infographic-db-report-data.json`

Report information architecture:

```text
First useful screen / deterministic foundation
  - chart/key indicators: ASC, MC, chart ruler
  - planet positions table
  - element and modality balances
  - house emphasis
  - aspect network
  - key aspects table
  - bottom 2x2 derived accents:
      house mode balance
      hemisphere/orientation balance
      quadrant balance
      compact aspect profile

Progressive upper narrative report
  - hero / main portrait
  - core_pattern
  - perception_and_mind
  - emotional_regulation
  - agency_and_desire
  - relationships_and_intimacy
  - growth_vector
```

## Dependencies

Existing architecture discussion docs; current FastAPI/Next.js/PostgreSQL stack.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/architecture/astrotype-v2-derived-calculations/README.md`
- `docs/architecture/astrotype-v2-balance-calculation.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`

## Scope

This feature covers the `V2-E1` slice from `docs/ROADMAP-v2.md`: architecture and contract documentation only.

In scope:

- canonical v2 boundaries and terminology;
- domain contract names from chart to report;
- section taxonomy and ownership semantics;
- LLM builder boundary and JSON input contract;
- deterministic foundation / calculation layer contract;
- progressive delivery states (`deterministic_ready`, narrative partial/complete);
- v1 quarantine boundary and no-old-REST-methods rule;
- multi-client API direction at contract level;
- explicit deferred/non-MVP blocks.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Backend/frontend implementation work.
- Marking implementation epics complete from documentation alone.

## Acceptance criteria

- [x] Architecture docs agree on cloud-core, Android-first-client direction and thin desktop client strategy.
- [x] Contracts name every core artifact from `NatalChartV2` through `NatalReportV2` / calculation-layer output.
- [x] LLM boundary is described as builder-created JSON inputs for bounded personality-section prose generation only after persisted facts, synthesis and outline.
- [x] The deterministic foundation/calculation layer is described as LLM-free and renderable before narrative completion.
- [x] Progressive delivery states separate deterministic readiness from LLM narrative completion.
- [x] V1 artifacts are quarantined as archive/reference-only and old REST/report/socionics methods are forbidden from the active v2 surface.
- [x] The current visual sample is linked as the canonical report-shape reference.
- [x] Deferred weak blocks are explicitly excluded from current MVP UI: `Most aspected planets`, `Thematic indicator bundles`, separate “factual basis” cards and calculation-to-section links.
- [x] Feature stories define concrete documentation deliverables and verification evidence.
- [ ] Implementation epics consume these contracts with code/tests. This belongs to later E16 stories, not to E1 itself.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Align v2 architecture documents](./S01-align-v2-architecture-docs.md) | ✅ Contract docs aligned |
| S02 | [Define v2 domain contracts](./S02-define-domain-contracts.md) | ✅ Contract docs aligned |
| S03 | [Define section taxonomy and ownership rules](./S03-define-section-taxonomy.md) | ✅ Contract docs aligned |
| S04 | [Define multi-client API surface](./S04-define-api-surface.md) | ✅ Contract docs aligned |

## Implementation order

```text
S01 → S02 → S03 → S04
```

## Verification

Docs-only verification for this feature:

```bash
git diff --check -- \
  docs/features/E16-v2-e1-architecture-contracts \
  docs/SRS/SRS-E16-astrotype-v2-cloud-core.md \
  docs/architecture/astrotype-v2-natal-report-architecture.md \
  docs/architecture/astrotype-v2-database-design.md \
  docs/architecture/astrotype-v2-c4-architecture.md \
  docs/architecture/astrotype-v2-derived-calculations/README.md
```

Contract sanity checks:

```text
canonical sample links are present in architecture/SRS/task docs;
builder + JSON + one LLM request per personality section are documented;
lower deterministic calculation layer is documented;
old “factual basis” / weak MVP blocks are not described as active UI scope.
```
