# V2-E8: Final report assembly

## Status

⬜ Не начато

## Goal

Assemble validated LLM segments into one large detailed `NatalReportV2` with stable sections, evidence index, technical basis and versioned persistence.

## Dependencies

V2-E7 segment outputs.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## Scope

This feature covers the `V2-E8` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [ ] Final report includes all required personality segments.
- [ ] Evidence index is included.
- [ ] Technical details are present but not mixed into narrative-first sections.
- [ ] Regeneration does not silently overwrite prior artifacts.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Build report assembler](./S01-report-assembler.md) | ⬜ Не начато |
| S02 | [Add duplication/evidence quality gates](./S02-duplication-quality-gates.md) | ⬜ Не начато |
| S03 | [Persist report versions](./S03-report-versioning.md) | ⬜ Не начато |
| S04 | [Assemble technical basis](./S04-technical-basis-section.md) | ⬜ Не начато |

## Implementation order

```text
S01 → S02 → S03 → S04
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e8-final-report-assembly
```

For implementation stories, add targeted tests to the active story before marking it complete.
