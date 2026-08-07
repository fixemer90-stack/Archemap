# V2-E1 S04: Define multi-client API surface

## Status

✅ Contract docs aligned

## Context

This story belongs to `V2-E1 — Architecture & contracts`.

The API contract must support the same generated report across web, Android/PWA and future thin desktop clients. Backend builders create JSON inputs for LLM sections; clients only receive/render resulting report data. Clients render the report; they do not calculate charts, call LLM providers or hold provider keys.

## Canonical visual sample

- `docs/design/astrotype-v2-infographic-db-report-sample.html`
- `docs/design/astrotype-v2-infographic-db-report-data.json`

## Current API direction

Initial API surface:

```text
POST /api/v1/astrotype-v2/reports
GET  /api/v1/astrotype-v2/reports/{report_id}
GET  /api/v1/astrotype-v2/reports/{report_id}/status
GET  /api/v1/astrotype-v2/reports/{report_id}/calculation-layer
GET  /api/v1/astrotype-v2/reports/{report_id}/segments
POST /api/v1/astrotype-v2/reports/{report_id}/regenerate
GET  /api/v1/astrotype-v2/reports/{report_id}/pdf
```

Notes:

- `GET /reports/{report_id}` may return the full assembled report including `calculation_layer`.
- `GET /calculation-layer` is the optional focused endpoint for deterministic lower-layer data if clients need separate lazy loading.
- Old separate `/facts` and `/infographics` endpoints are not the current naming preference for MVP; if added later, they must map to internal/debug/provenance use, not a visible “factual basis” dashboard.

## Response shape direction

```json
{
  "report_id": "...",
  "status": "ready",
  "upper_report": {
    "hero": {},
    "sections": []
  },
  "calculation_layer": {
    "key_indicators": {},
    "planet_positions": [],
    "balances": {},
    "house_emphasis": {},
    "aspect_network": {},
    "key_aspects": [],
    "derived_accents_2x2": {}
  },
  "metadata": {
    "contract_version": "natal_report_v2",
    "source_profile_id": "...",
    "generated_at": "..."
  }
}
```

## Client responsibilities

Clients may:

- request report generation/status/read endpoints;
- render upper narrative first;
- render the deterministic calculation layer at the bottom;
- lazy-load heavy calculation-layer data if needed;
- request PDF/export when available.

Clients must not:

- calculate natal chart facts;
- call LLM provider directly;
- store LLM provider keys;
- invent/rearrange derived calculation blocks;
- render deferred blocks as active UI.

## Files affected

| Path | Action |
|---|---|
| `docs/SRS/SRS-E16-astrotype-v2-cloud-core.md` | API and functional requirement naming. |
| `docs/architecture/astrotype-v2-c4-architecture.md` | Multi-client boundary and report artifact shape. |
| `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md` | Client strategy, if endpoint naming changes later. |

## Acceptance criteria

- [x] API surface has a clear report/status/read/regenerate/PDF direction.
- [x] Deterministic lower calculation data is named `calculation_layer`, not a user-facing factual-basis dashboard.
- [x] Clients are thin and do not own calculation or LLM generation.
- [x] Endpoint naming is compatible with web/Android/future desktop clients.
- [x] Deferred active-UI blocks are excluded from the MVP API contract, including `Most aspected planets` and `Thematic indicator bundles`.

## Verification evidence

Same docs-only verification as `FEATURE.md`; API wording in SRS and feature docs now matches the canonical report shape.
