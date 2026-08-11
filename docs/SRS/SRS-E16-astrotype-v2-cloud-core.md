# SRS-E16: Astrotype v2 Cloud-Core Multi-Client Natal Report Platform

## 1. Introduction

### Purpose

This SRS defines Astrotype v2 as a natal-only, cloud-core, multi-client report platform.

v2 calculates and stores a natal chart without LLM, generates evidence-backed facts, builds deterministic synthesis, outline and calculation-layer data, returns this deterministic foundation to the client as soon as it is ready, creates builder-owned JSON inputs for bounded asynchronous LLM requests per personality segment, and progressively completes the large detailed upper narrative report.

### Scope

In scope:

- backend-owned v2 report pipeline;
- normalized PostgreSQL source-of-truth storage;
- immediate deterministic foundation delivery after registration/profile completion when birth data is sufficient;
- bounded async LLM segment generation from persisted facts;
- deterministic calculation-layer data;
- web/mobile/desktop client API compatibility;
- Android MVP path via responsive web/PWA/Capacitor.

Out of scope for foundation:

- socionics and Model A;
- v1 REST/report compatibility endpoints or aliases;
- reuse of legacy report DTOs, `NarrativeInput`, `function_strengths` or socionics fields;
- desktop-local-first product architecture;
- local LLM generation;
- native React Native rewrite unless later justified;
- Love/Child/Career v2 expansion.

### References

- `docs/ROADMAP-v2.md`
- `docs/architecture/astrotype-v2-natal-report-architecture.md`
- `docs/architecture/astrotype-v2-database-design.md`
- `docs/architecture/astrotype-v2-c4-architecture.md`
- `docs/architecture/astrotype-v2-cloud-core-mobile-desktop-strategy.md`
- `docs/architecture/astrotype-v2-derived-calculations/README.md`
- `docs/design/astrotype-v2-infographic-db-report-sample.html`
- `docs/design/astrotype-v2-infographic-db-report-data.json`

Feature contracts:

- `V2-E1` — `Architecture & contracts`: `docs/features/E16-v2-e1-architecture-contracts/FEATURE.md`
- `V2-E2` — `Database foundation`: `docs/features/E16-v2-e2-database-foundation/FEATURE.md`
- `V2-E3` — `Natal chart adapter`: `docs/features/E16-v2-e3-natal-chart-adapter/FEATURE.md`
- `V2-E4` — `Reference data`: `docs/features/E16-v2-e4-reference-data/FEATURE.md`
- `V2-E5` — `Fact extraction`: `docs/features/E16-v2-e5-fact-extraction/FEATURE.md`
- `V2-E6` — `Synthesis & outline`: `docs/features/E16-v2-e6-synthesis-outline/FEATURE.md`
- `V2-E7` — `Modular LLM generation`: `docs/features/E16-v2-e7-modular-llm-generation/FEATURE.md`
- `V2-E8` — `Final report assembly`: `docs/features/E16-v2-e8-final-report-assembly/FEATURE.md`
- `V2-E9` — `Infographics & calculation layer`: `docs/features/E16-v2-e9-infographics-factual-basis/FEATURE.md`
- `V2-E10` — `API & async runtime`: `docs/features/E16-v2-e10-api-async-runtime/FEATURE.md`
- `V2-E11` — `Web responsive reader`: `docs/features/E16-v2-e11-web-responsive-reader/FEATURE.md`
- `V2-E12` — `Android MVP path`: `docs/features/E16-v2-e12-android-mvp-path/FEATURE.md`
- `V2-E13` — `Desktop thin client decision`: `docs/features/E16-v2-e13-desktop-thin-client-decision/FEATURE.md`; decision artifact: `docs/architecture/astrotype-v2-desktop-thin-client-decision.md`.
- `V2-E14` — `QA, smoke, rollout`: `docs/features/E16-v2-e14-qa-smoke-rollout/FEATURE.md`

---

## 2. Overall description

### Product perspective

Astrotype v2 is a new bounded context, not a refactor of legacy Self report. It shares platform concerns such as auth/profile/API infrastructure, but owns a clean natal-only domain model and storage model. Legacy v1 documentation is retained only under `docs/archive/v1/` as historical reference and is not an active implementation contract.

### System functions

| Function                          | Description                                                                                                                            |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| Natal calculation                 | Calculate chart placements, houses, aspects and balances without LLM after registration/profile completion provides enough birth data. |
| Persistence                       | Save chart entities/facts/reports in PostgreSQL.                                                                                       |
| Fact extraction                   | Convert chart rows into evidence-backed facts.                                                                                         |
| Synthesis                         | Build themes, tensions, resources and growth vectors from facts.                                                                       |
| Outline                           | Assign themes to sections with owned/reference/forbidden semantics.                                                                    |
| Deterministic foundation delivery | Return chart/facts/synthesis/outline/calculation-layer data as `deterministic_ready` before LLM completion.                            |
| LLM generation                    | Generate detailed section prose asynchronously from builder-created JSON input for one personality segment.                            |
| Assembly                          | Progressively assemble upper narrative sections over the deterministic foundation.                                                     |
| Calculation layer                 | Generate report calculation data without LLM.                                                                                          |
| Multi-client API                  | Serve same report to web, Android and desktop clients.                                                                                 |
| Desktop thin-client decision      | Windows `.exe` is optional for v2 core launch; if pursued, it uses the same backend API/report ids and cache-only local storage.       |

---

## 3. Functional requirements

### FR-1: Natal-only bounded context

- FR-1.1: v2 shall live under `backend/app/modules/astrotype_v2/`.
- FR-1.2: v2 shall not import socionics, Model A, `function_strengths` or legacy `NarrativeInput` as domain inputs.
- FR-1.3: v2 shall keep legacy v1 artifacts quarantined under `docs/archive/v1/` or unregistered legacy code paths until explicit migration/removal.
- FR-1.4: v2 shall not expose old v1 REST report methods, compatibility aliases, old report DTOs or legacy frontend report/socionics routes as active v2 behavior.

### FR-2: Deterministic chart and fact storage

- FR-2.1: v2 shall calculate or adapt natal chart data without LLM.
- FR-2.2: v2 shall persist placements, houses and aspects as normalized rows.
- FR-2.3: v2 shall persist `NatalFactV2` before synthesis or LLM generation.
- FR-2.4: every fact shall link to a source row and technical value.

### FR-3: Reference data

- FR-3.1: v2 shall store aspect type definitions separately from user aspects.
- FR-3.2: v2 shall store aspect pair interpretations separately from user aspects.
- FR-3.3: symmetric aspect pairs shall use canonical planet order.

### FR-4: Synthesis and outline

- FR-4.1: v2 shall build `NatalSynthesisV2` from persisted facts.
- FR-4.2: v2 shall build `ReportOutlineV2` before LLM generation.
- FR-4.3: every theme shall have one owning section.
- FR-4.4: references and forbidden expansions shall be explicit.

### FR-5: Modular LLM generation

- FR-5.1: v2 shall generate one builder-created JSON input per personality segment.
- FR-5.2: segment inputs shall contain only owned facts/themes, allowed references, forbidden theme ids, evidence ids, already-explained summary and style contract.
- FR-5.3: segment requests/responses shall be persisted.
- FR-5.4: segment failures shall be retryable without rerunning the entire pipeline.
- FR-5.5: final report depth shall not be limited by arbitrary hard section caps, low character caps, summary-style prompt limits or any other artificial content cap.
- FR-5.6: provider output limits shall be handled with continuation/chunking at segment level rather than by shortening the product report.
- FR-5.7: validators shall reject shallow/generic output, but shall not reject a grounded valid section merely because it is long.

### FR-6: Progressive report delivery

- FR-6.1: v2 shall return deterministic chart/fact/synthesis/outline/calculation-layer data as `deterministic_ready` before LLM completion.
- FR-6.2: v2 shall expose narrative generation states separately from deterministic readiness: `narrative_generating`, `partial`, `complete` and `failed`.
- FR-6.3: LLM failures or retries shall not hide or invalidate already persisted deterministic output.
- FR-6.4: registration/profile completion may trigger deterministic calculation when enough birth data is present.

### FR-7: Final report

- FR-7.1: v2 shall assemble `NatalReportV2` from deterministic foundation plus validated segment outputs.
- FR-7.2: v2 shall keep deterministic calculation-layer details available in the final report.
- FR-7.3: regeneration shall preserve version/lineage rather than silently overwriting previous reports.

### FR-8: Deterministic calculation layer

- FR-8.1: v2 shall generate calculation-layer datasets without LLM.
- FR-8.2: the calculation layer shall include chart/key indicators, planet positions, balances, house emphasis, aspect network, key aspects and bottom 2x2 derived accents.
- FR-8.3: the calculation layer shall not include deferred current-MVP blocks: most-aspected planets, thematic indicator bundles, calculation-to-section links, archetypes or typology labels.
- FR-8.4: web and Android clients shall consume the same `calculation_layer` contract.

### FR-9: Multi-client API

- FR-9.1: v2 shall expose report generation/status/read APIs for web and Android.
- FR-9.2: long generation shall run asynchronously.
- FR-9.3: auth and entitlement checks shall be server-side and reuse the existing auth/profile infrastructure rather than creating a separate v2 auth stack.
- FR-9.4: LLM provider keys shall never be embedded in clients.
- FR-9.5: v2 shall not re-register old v1 REST report/socionics endpoints as compatibility methods.

---

## 4. Non-functional requirements

| Category        | Requirement                                                                                                                                                                                                                                       |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Reliability     | Report jobs are resumable/retryable at segment boundary.                                                                                                                                                                                          |
| Data safety     | v2 foundation migrations preserve platform identity/access and current profile input data. Legacy v1 product artifacts may be purged from active storage only through an explicit inventory + backup/snapshot + staging-verified cleanup runbook. |
| Traceability    | Every generated claim must map to evidence ids or be rejected by validation.                                                                                                                                                                      |
| Security        | LLM keys and billing entitlements are backend-owned.                                                                                                                                                                                              |
| Portability     | Web, Android and desktop clients share the same API/report ids.                                                                                                                                                                                   |
| Performance     | Status/progress APIs should be cheap to poll from mobile.                                                                                                                                                                                         |
| Maintainability | Reference data is versioned and not hardcoded across pipeline code.                                                                                                                                                                               |
| Testability     | Each stage can be tested from stored upstream artifacts.                                                                                                                                                                                          |

---

## 5. Data model

Canonical tables are specified in `docs/architecture/astrotype-v2-database-design.md`.

Core groups:

- chart rows: `natal_charts`, `natal_planet_positions`, `natal_houses`, `natal_aspects`;
- reference rows: `aspect_definitions`, `aspect_pair_interpretations`;
- fact/synthesis rows: `natal_facts`, `natal_syntheses`, `report_outlines`;
- LLM artifact rows: `report_segment_generations`;
- user-facing output rows: `natal_reports`, `natal_calculation_layer_data` or equivalent typed JSONB view-model rows.

---

## 6. API specification

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

Registration/profile completion can trigger the deterministic calculation path when enough birth data is present; it should return or enqueue the v2 deterministic foundation without creating a separate v2 auth flow.

Status APIs must distinguish `deterministic_ready` from LLM narrative `partial` / `complete` states.

API details are refined in `V2-E10: API & async runtime`.

Endpoint note: old separate `/facts` and `/infographics` endpoint names are not the current MVP naming preference for the user-facing report. If debug/provenance endpoints are introduced later, they must remain internal/progressive disclosure and must not recreate a visible “factual basis” dashboard.

Legacy API note: old v1 report/socionics REST methods must not appear as v2 compatibility endpoints. If any old endpoint remains temporarily reachable during migration, it must be outside the v2 namespace, unlinked from v2 clients and covered by a separate deprecation/removal story.

---

## 7. Verification criteria

Minimum v2 MVP verification:

- pre-migration backup/export procedure is documented and tested for any environment containing real users;
- v2 schema migrations preserve users/auth/profile/billing data and current birth/profile input needed for v2 calculation;
- optional v1 product-data purge has an explicit inventory/runbook and deletes only legacy report/socionics artifacts after staging verification;
- one smoke profile generates complete v2 chart rows;
- registration/profile completion can reach or enqueue `deterministic_ready` without replacing existing auth/profile infrastructure;
- facts are persisted before LLM;
- report outline exists before LLM segment generation;
- status/read APIs distinguish deterministic readiness from narrative completion;
- each generated section has evidence ids;
- final report is detailed and complete for all required segments;
- calculation layer renders from deterministic data and matches `docs/design/astrotype-v2-infographic-db-report-sample.html`, not the existing legacy product report/dashboard design;
- no socionics appears in v2 payloads/prompts/UI;
- no old v1 report/socionics REST methods or compatibility aliases appear in the v2 API surface;
- web and Android/PWA path read the same report id;
- runtime smoke verifies actual report readiness.

---

## 8. Dependencies

Internal:

- FastAPI backend;
- existing auth/profile infrastructure;
- existing chart calculation engine as low-level natal calculator;
- SQLAlchemy/Alembic;
- Next.js frontend.

External:

- PostgreSQL;
- Redis/Celery for async runtime;
- LLM provider called server-side;
- Android Capacitor tooling later.
