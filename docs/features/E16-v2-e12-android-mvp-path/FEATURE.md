# V2-E12: Android MVP path

## Status

⬜ Не начато

## Goal

Prepare Android MVP as a client to the same backend API, preferably via PWA/Capacitor before considering a native rewrite.

## Dependencies

V2-E11 responsive web; backend API stable.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## Scope

This feature covers the `V2-E12` slice from `docs/ROADMAP-v2.md`.

## Out of scope

- Legacy v1 report rewrites unless explicitly required for compatibility.
- Socionics, Model A, function strengths or typology fields in v2.
- Broad unrelated roadmap work outside this epic.
- Marking implementation complete from documentation alone.

## Acceptance criteria

- [ ] Android app contains no LLM provider key.
- [ ] Android uses backend report APIs.
- [ ] Same report id renders consistently on web and Android.
- [ ] Local storage is cache/draft only.

## Stories

| ID | Story | Status |
|---|---|---|
| S01 | [Prepare PWA readiness](./S01-pwa-readiness.md) | ⬜ Не начато |
| S02 | [Create Capacitor Android shell](./S02-capacitor-shell.md) | ⬜ Не начато |
| S03 | [Handle mobile auth/session](./S03-mobile-auth-session.md) | ⬜ Не начато |
| S04 | [Verify Android report flow](./S04-android-report-flow.md) | ⬜ Не начато |
| S05 | [Prepare push and billing foundation](./S05-mobile-push-billing-foundation.md) | ⬜ Не начато |

## Implementation order

```text
S01 → S02 → S03 → S04 → S05
```

## Verification

For docs-only changes:

```bash
git diff --check -- docs/features/E16-v2-e12-android-mvp-path
```

For implementation stories, add targeted tests to the active story before marking it complete.
