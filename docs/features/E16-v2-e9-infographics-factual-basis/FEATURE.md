# V2-E9: Infographics & calculation layer

## Status

⬜ Не начато

## Goal

Provide deterministic natal-chart visual datasets for the lower calculation layer exactly as represented in `docs/design/astrotype-v2-infographic-db-report-sample.html` and specified in `docs/design/astrotype-v2-canonical-report-ui-contract.md`. This is not a separate factual-basis dashboard.

## Dependencies

V2-E5 facts; V2-E8 final report.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/architecture/astrotype-v2-balance-calculation.md`
- `docs/architecture/astrotype-v2-derived-calculations/README.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## Scope

This feature covers the `V2-E9` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [ ] Infographics are generated from stored chart/fact rows only.
- [ ] User-visible calculation layer matches the canonical sample: key indicators, planet table, balance bars, house accents, aspect network/table and calculation matrix.
- [ ] Evidence/provenance is available through compact/progressive disclosure, not as a separate dashboard block.
- [ ] Data is reusable by web and Android clients.
- [ ] No LLM prose is used as source for chart visuals.
- [ ] Deferred blocks are absent from MVP UI: archetypes, theme maps, standalone factual-basis cards, most-aspected rankings.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Build infographic data builder](./S01-infographic-data-builder.md) | ⬜ Не начато |
| S02 | [Build evidence card model](./S02-evidence-card-model.md) | ⬜ Не начато |
| S03 | [Expose infographic API contract](./S03-infographic-api-contract.md) | ⬜ Не начато |
| S04 | [Render infographics and facts](./S04-frontend-infographic-rendering.md) | ⬜ Не начато |

## Implementation order

```text
S01 → S02 → S03 → S04
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e9-infographics-factual-basis
```

For implementation stories, add targeted tests to the active story before marking it complete.
