# V2-E14: QA, smoke, rollout

## Status

✅ Завершено

## Goal

Verify quality, evidence consistency, runtime reliability and multi-client readiness before shipping v2.

## Dependencies

V2-E1 through V2-E12 minimum.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`

## Scope

This feature covers the `V2-E14` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [x] A smoke profile generates complete v2 report.
- [x] Facts shown to user match report evidence ids.
- [x] Infographics render from deterministic data.
- [x] No socionics appears in v2 payloads/prompts/UI.
- [x] Runtime proof includes actual report readiness, not infra health only.

## Stories

| ID  | Story                                                                     | Status       |
| --- | ------------------------------------------------------------------------- | ------------ |
| S01 | [Add backend contract tests](./S01-backend-contract-tests.md)             | ✅ Завершено |
| S02 | [Add quality regression suite](./S02-quality-regression-suite.md)         | ✅ Завершено |
| S03 | [Run live runtime smoke](./S03-runtime-smoke.md)                          | ✅ Завершено |
| S04 | [Run multi-client smoke](./S04-multi-client-smoke.md)                     | ✅ Завершено |
| S05 | [Add observability and rollout checklist](./S05-observability-rollout.md) | ✅ Завершено |

## Implementation order

```text
S01 → S02 → S03 → S04 → S05
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e14-qa-smoke-rollout
```

For implementation stories, add targeted tests to the active story before marking it complete.
