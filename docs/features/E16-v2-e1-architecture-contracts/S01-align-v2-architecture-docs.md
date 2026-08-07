# V2-E1 S01: Align v2 architecture documents

## Status

✅ Contract docs aligned

## Context

This story belongs to `V2-E1 — Architecture & contracts`.

The architecture, DB, C4, SRS and derived-calculation documents must describe the same v2 product boundary and the same canonical report shape.

Current decision:

```text
Upper report = narrative personality sections generated from builder-created JSON inputs.
Lower report = deterministic calculation layer, calculated without LLM.
```

Canonical sample:

- `docs/design/astrotype-v2-infographic-db-report-sample.html`
- `docs/design/astrotype-v2-infographic-db-report-data.json`

## Related architecture

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/architecture/astrotype-v2-derived-calculations/README.md`
- `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md`

## What this story requires

1. Align all primary v2 docs on these boundaries:
   - v2 is natal-only;
   - PostgreSQL is source of truth;
   - Redis is runtime/cache/queue only;
   - natal calculation and derived calculations are deterministic;
   - LLM receives bounded JSON inputs for one personality section at a time;
   - final report is assembled from validated LLM sections plus deterministic lower calculation layer.
2. Link the canonical sample from architecture/SRS/task docs.
3. Remove or downgrade stale “infographics and factual basis” wording when it implies a separate evidence/dashboard block.
4. Explicitly exclude weak/deferred UI blocks from current MVP:
   - `Most aspected planets`;
   - `Thematic indicator bundles`;
   - “Связь расчёта с разделами отчёта”;
   - separate “factual basis” cards;
   - archetypes / typology / dominant-planet rankings.

## Files affected

| Path | Action |
|---|---|
| `docs/architecture/astrotype-v2-natal-report-architecture.md` | Defines upper LLM narrative and lower deterministic report layer. |
| `docs/architecture/astrotype-v2-c4-architecture.md` | C4 flow names builder-created JSON inputs and deterministic calculation appendix. |
| `docs/architecture/astrotype-v2-database-design.md` | Storage layers describe LLM segment artifacts separately from deterministic calculation layer. |
| `docs/architecture/astrotype-v2-derived-calculations/README.md` | Current visible derived calculations and deferred items are aligned with sample. |
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md` | SRS terminology follows the same report boundary. |
| `docs/features/E16-v2-e1-architecture-contracts/` | Feature/story docs reflect the contract. |

## Acceptance criteria

- [x] Architecture docs describe the same report shape as the canonical sample.
- [x] Upper report is documented as bounded LLM section prose from builder-created JSON inputs.
- [x] Lower report is documented as fully deterministic and LLM-free.
- [x] Deferred weak blocks are not presented as current MVP UI.
- [x] SRS uses the same terminology as architecture docs.
- [x] Verification evidence is recorded below.

## Verification evidence

```bash
git diff --check -- \
  docs/features/E16-v2-e1-architecture-contracts \
  docs/SRS/SRS-E16-astrotype-v2-cloud-core.md \
  docs/architecture/astrotype-v2-natal-report-architecture.md \
  docs/architecture/astrotype-v2-database-design.md \
  docs/architecture/astrotype-v2-c4-architecture.md \
  docs/architecture/astrotype-v2-derived-calculations/README.md
```

Expected/current result: no whitespace/table errors.
