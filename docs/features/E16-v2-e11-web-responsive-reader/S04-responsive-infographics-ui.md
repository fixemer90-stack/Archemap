# V2-E11 S04: Build responsive infographic UI

## Status

⬜ Не начато

## Context

This story belongs to `V2-E11 — Web responsive reader`.

Render the lower deterministic calculation layer from the canonical sample on mobile and desktop web: key indicators, planet table, balance bars, house accents, aspect network/table and compact calculation matrix.

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
- [ ] Infographic layout follows `docs/design/astrotype-v2-infographic-db-report-sample.html`.
- [ ] Lower layer includes key indicators, planet positions, element/modality balances, house emphasis, aspect network, key aspect table and calculation matrix.
- [ ] Deferred blocks are not rendered: archetypes, theme maps, standalone factual-basis cards, most-aspected rankings.
- [ ] Behavior is backed by tests or documented verification evidence.
- [ ] Relevant parent `FEATURE.md` row is updated when the story status changes.

## Verification commands

Fill this when implementation starts:

```bash
# targeted tests/verification for this story
```
