# V2-E11 S01: Build mobile report layout

## Status

⬜ Не начато

## Context

This story belongs to `V2-E11 — Web responsive reader`.

Create responsive reading layout for long detailed sections. The canonical visual reference is `docs/design/astrotype-v2-infographic-db-report-sample.html`, not the existing product report/dashboard UI.

Related architecture:

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`


## What to do

1. Read the related architecture and roadmap documents.
2. Inspect existing code/docs relevant to this boundary before implementation.
3. Implement only the scope of this story.
4. Add or update tests/documentation for the changed contract.
5. Verify with targeted commands and record the evidence in this story when work starts.

## Files likely affected

| Path | Action |
|---|---|
| `backend/app/modules/astrotype_v2/` | Add/update v2 backend module code when implementation starts. |
| `docs/features/E16-v2-e11-web-responsive-reader/` | Keep feature/story docs synchronized. |
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md` | Update if functional/API/data contract changes. |

## Acceptance criteria

- [ ] Scope is implemented without crossing into unrelated v2 epics.
- [ ] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [ ] Layout visually matches `docs/design/astrotype-v2-infographic-db-report-sample.html`.
- [ ] The first screen is a full-width dark report cover, not the current dashboard/report shell.
- [ ] Narrative sections render as large prose cards with right-side asides on desktop and stacked asides on mobile.
- [ ] Report order is hero → six narrative sections → lower deterministic calculation layer.
- [ ] Behavior is backed by tests or documented verification evidence.
- [ ] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Fill this when implementation starts:

```bash
# targeted tests/verification for this story
```
