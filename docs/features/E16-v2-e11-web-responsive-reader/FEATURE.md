# V2-E11: Web responsive reader

## Status

⬜ Не начато

## Goal

Build a mobile-friendly web reading experience that follows the canonical sample exactly: `docs/design/astrotype-v2-infographic-db-report-sample.html`. Existing product report/dashboard design is legacy reference only and must not define v2 UI.

## Dependencies

V2-E10 APIs.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## Scope

This feature covers the `V2-E11` slice from `docs/ROADMAP-v2.md`.

Canonical visual target:

- `docs/design/astrotype-v2-infographic-db-report-sample.html`
- `docs/design/astrotype-v2-canonical-report-ui-contract.md`

The sample is the source of truth for:

- dark full-width reader surface;
- hero cover with three compact action pills;
- long-form Russian narrative sections first;
- right-side section asides inside narrative cards;
- lower deterministic calculation layer after prose;
- compact tables/bars/aspect network/cards;
- no dashboard header/sidebar/metric-summary layout in the report itself.

Existing product UI under `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` and old report components are legacy implementation references only. They must not be copied as the v2 visual design.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [ ] v2 report reader visually matches `docs/design/astrotype-v2-infographic-db-report-sample.html` rather than the current legacy product report page.
- [ ] Report is readable on mobile screen sizes while preserving the sample's order: hero → narrative sections → calculation layer.
- [ ] Long sections use the sample's prose-card + right-aside structure, not dashboard metric blocks.
- [ ] Evidence/provenance is folded into the lower deterministic calculation layer and progressive disclosure; no separate “factual basis dashboard” is introduced.
- [ ] Infographics are responsive and reusable for Android wrapper.
- [ ] Socionics/Model A/function-strength UI from the existing product report is absent from v2.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Build mobile report layout](./S01-mobile-report-layout.md) | ⬜ Не начато |
| S02 | [Build generation status UI](./S02-generation-status-ui.md) | ⬜ Не начато |
| S03 | [Build evidence disclosure UI](./S03-evidence-disclosure-ui.md) | ⬜ Не начато |
| S04 | [Build responsive infographic UI](./S04-responsive-infographics-ui.md) | ⬜ Не начато |
| S05 | [Build PDF/share/export UI](./S05-pdf-share-export-ui.md) | ⬜ Не начато |

## Implementation order

```text
S01 → S02 → S03 → S04 → S05
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e11-web-responsive-reader
```

For implementation stories, add targeted tests to the active story before marking it complete.
