# V2-E9 S04: Render infographics and facts

## Status

⬜ Не начато

## Context

This story belongs to `V2-E9 — Infographics & calculation layer`.

Add responsive UI components for the lower deterministic calculation layer from `docs/design/astrotype-v2-infographic-db-report-sample.html`; do not build a separate factual-basis dashboard.

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
| `docs/features/E16-v2-e9-infographics-factual-basis/` | Keep feature/story docs synchronized. |
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md` | Update if functional/API/data contract changes. |

## Acceptance criteria

- [ ] Scope is implemented without crossing into unrelated v2 epics.
- [ ] v2 remains natal-only and does not depend on socionics/Model A/function strengths.
- [ ] UI components match the canonical sample's lower calculation layer.
- [ ] Visible blocks are limited to key indicators, planet positions, balances, house emphasis, aspect network/table and calculation matrix.
- [ ] No separate factual-basis/evidence dashboard, archetype/theme map or most-aspected ranking is rendered.
- [ ] Behavior is backed by tests or documented verification evidence.
- [ ] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Fill this when implementation starts:

```bash
# targeted tests/verification for this story
```
