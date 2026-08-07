# V2-E10: API & async runtime

## Status

⬜ Не начато

## Goal

Expose v2 generation, progress, report retrieval, facts and infographics through stable multi-client APIs with async generation support.

## Dependencies

V2-E2 through V2-E9 core pipeline.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## Scope

This feature covers the `V2-E10` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [ ] Web and Android can use the same endpoints.
- [ ] Generation can continue while client is closed.
- [ ] Progress exposes segment-level state.
- [ ] Auth/entitlement checks are server-side.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Add report generation endpoint](./S01-report-generation-endpoint.md) | ⬜ Не начато |
| S02 | [Add status/progress API](./S02-status-progress-api.md) | ⬜ Не начато |
| S03 | [Add read APIs](./S03-report-read-apis.md) | ⬜ Не начато |
| S04 | [Wire async runtime](./S04-async-worker-orchestration.md) | ⬜ Не начато |
| S05 | [Add regeneration API](./S05-regeneration-api.md) | ⬜ Не начато |

## Implementation order

```text
S01 → S02 → S03 → S04 → S05
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e10-api-async-runtime
```

For implementation stories, add targeted tests to the active story before marking it complete.
