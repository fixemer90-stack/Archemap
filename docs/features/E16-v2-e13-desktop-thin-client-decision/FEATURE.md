# V2-E13: Desktop thin client decision

## Status

⬜ Не начато

## Goal

Decide whether to build a Windows `.exe` and, if yes, keep it as a thin client over the same backend API rather than a local source-of-truth product.

## Dependencies

V2-E10 stable API; V2-E11 reusable frontend.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## Scope

This feature covers the `V2-E13` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [ ] `.exe` is not required for v2 core launch.
- [ ] If built, `.exe` uses same backend/API/report ids.
- [ ] No local DB is source of truth.
- [ ] Desktop decision does not block Android roadmap.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Make desktop product decision](./S01-desktop-product-decision.md) | ⬜ Не начато |
| S02 | [Spike Tauri vs Electron shell](./S02-tauri-electron-spike.md) | ⬜ Не начато |
| S03 | [Define desktop cache contract](./S03-desktop-cache-contract.md) | ⬜ Не начато |
| S04 | [Write packaging plan](./S04-desktop-packaging-plan.md) | ⬜ Не начато |

## Implementation order

```text
S01 → S02 → S03 → S04
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e13-desktop-thin-client-decision
```

For implementation stories, add targeted tests to the active story before marking it complete.
