# E20 Legacy Career Retirement Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Retire every generic Career v1 writer while preserving historical read/PDF, scoped grandfathered access to target E19, and generic Self behavior.

**Architecture:** Keep legacy generic reports and target Career separate. Add early router/service/queued-consumer retirement guards and a no-refresh historical read branch; do not remove rules or rows. Preserve existing ownership/access checks without widening grants. Instrument only bounded operation/outcome attributes. Production census/rollout cannot execute because the owner reports the server was lost; record those gates open, not as zero counts or successful deployment.

**Tech Stack:** FastAPI, SQLAlchemy/PostgreSQL, OpenTelemetry, Next.js/React, pytest, Playwright.

Baseline: `c7eb2c2`, clean canonical checkout `/mnt/d/Python/Balthier/Archemap`. Seven Stories / 46 unchecked criteria inventoried in the scratch acceptance matrix. No deployment, paid LLM/payment calls, customer writes, destructive SQL, rules deletion or other worktree modifications are authorized.

## S01 — Source/runtime inventory and safe census preparation

Files: create `docs/features/E20-legacy-career-retirement/INVENTORY.md`; create `backend/scripts/legacy_career_census.py` with tests in `backend/tests/unit/test_reports/test_legacy_career_census.py`; update S01/FEATURE/WORKFLOW after verification.

1. Enumerate mounted `/v1/reports` endpoints from the executable access inventory and actual FastAPI app. Trace service/PDF/narrative/worker/rules paths and frontend consumers, including POST PDF alias and versions reads.
2. Separate target `/career` routes, grandfathered entitlement literal and legacy report storage. Identify shared Self code that must remain.
3. TDD a read-only aggregate census: return counts/status/version distributions and separate active direct Career grants, overlap/row-only/grant-only owner counts; no identifiers, payloads or PII. Missing data/telemetry are unknown, never fabricated zeros. Execute only against disposable synthetic PostgreSQL.
4. Preserve production census/external-client/usage-window criteria as blocked pending restored infrastructure and telemetry.

## S02 + S04 — Backend retirement and immutable archive

Files: `backend/app/modules/reports/router.py`, `service.py`, `schemas.py`, `pdf.py` only as required; new bounded retirement/telemetry module under `reports`; `backend/app/modules/report_narratives/service.py`/`tasks.py`, `backend/workers/tasks/reports.py` only for real hidden writers; `backend/tests/unit/test_reports/test_legacy_career_retirement.py`; `backend/tests/integration/test_legacy_career_retirement.py`.

RED → GREEN tracer bullets:

1. Owned authenticated generic Career generation returns 410 before report lookup/mutation/chart/rules/dispatch. Stable detail: `{code: legacy_career_generation_retired, message: Career reports are created through the Career product flow., target_path: /products/career}`. Authentication/ownership and access precedence must remain privacy-safe.
2. Direct `ReportService.generate_report(product="career")` cannot bypass retirement, even if caller catches the error and commits.
3. Report-ID narrative regenerate, worker execution and failure-finalization must not mutate Career legacy rows. Direct service/queued-consumer entrypoints need explicit coverage; guard before provider/cache/status mutation.
4. Legacy get/list/versions/GET-HEAD-POST PDF render saved artifacts without `_report_requires_refresh`, chart calculation, version increments or narrative generation. Preserve row status/version/payload and historical hashes, including non-ready statuses; missing payload is an honest unavailable response, not regeneration.
5. Preserve shared Self behavior, historical fixture variants, and target E19 404 for seeded legacy IDs. Test owned/foreign/missing, same-owner other product and direct grants without broadening authorization.
6. Inspect actual runtime OpenAPI and document 410 in tracked `contracts/openapi.yaml` without removing `career` from request parsing (it must reach 410 rather than 422).

Run focused units then reports/narrative regressions. Run real PostgreSQL on an owned disposable database for before/after fresh-session snapshots; never use application `.env` database. Do not commit in a shared worker lane; parent reviews and commits explicit paths.

## S03 — Grandfathered target access

Files: preserve `career/access.py`, `career/contracts.py`, `authorization` policy; add focused unit/integration coverage, modifying runtime only for demonstrated gaps.

1. RED/GREEN matrix for active Plus, active direct Career grant, expired/revoked/future-start/subscription-linked/duplicate grants.
2. A grant without legacy row allows target admission; a legacy row alone never grants target access.
3. Exercise actual target questionnaire/generation/read/versions/PDF routes and ownership-safe denial. Legacy IDs remain rejected by target routes.
4. Retain metadata-only ownership before protected payload loading; do not copy the ambiguous older Story wording into a payload-leaking implementation. Clarify Story wording to match the existing safe API order.

## S05 — Frontend archive and target routing

Files: `frontend/src/app/(dashboard)/report/[profileId]/page.tsx`, `frontend/src/lib/api/report.ts`, report view-model only if needed, active Career navigation clients only if an actual legacy consumer is found; new `frontend/tests/e2e/e20-legacy-career.spec.ts` and scoped harness if required.

1. Browser RED: old Career link must never POST chart recomputation, generic generation, narrative regeneration or target create automatically. Existing client currently POSTs `/profiles/{id}/chart` during every generic read; remove this for archive reads, deriving calculation display from saved data rather than the current chart.
2. Existing row shows explicit read-only archive, exact saved text, a working generic PDF download and CTA `/products/career` with safely encoded valid profile context.
3. Missing row shows target CTA without creating anything. Distinguish 401/402/404 and cross-navigation races; do not leak foreign data or use the wrong profile/product report.
4. Career historical nonterminal status does not start generation/poll/retry. Generic Self auto-generation remains unchanged.
5. Verify desktop/mobile/keyboard/overflow and no unexpected mutations. Audit sidebar/dashboard/billing/CTAs and target flow for residual legacy create links.

Run focused Playwright first, then repo ESLint/Prettier/TypeScript, UX contracts and build. Capture representative desktop/mobile screenshots, do not reset unrelated runtimes.

## S06 — Telemetry and retained-data removal gate

Files: bounded `reports` telemetry module and its tests; target `career/access.py` instrumentation; create `docs/deployment/legacy-career-retirement.md`; update S06 and workflow.

1. Count blocked generation/regenerate/worker attempts, successful legacy reads/versions/PDF, authenticated missing-archive reads and target access via grandfathered grant separately. Avoid double-counting PDF internal loads as user reads. No user/profile/report IDs, payload, birth data, emails or exception prose in event attributes.
2. Test operation/outcome allowlists and actual endpoint/service call sites; unknown/malformed values fail closed.
3. Provide Prometheus queries consistent with real instrument/exporter naming, staged observation protocol and approval template. Historical usage without telemetry remains unknown.
4. Current data strategy is conservative retention, no migration/deletion. Do not invent owner-approved numeric observation windows/thresholds: destructive removal requires a separately approved window/limits, restored-data census, backup/restore, support/retention decision and explicit approval. Provide a fail-closed eligibility contract if implemented.
5. Dashboard/live scrape/observation and backup rehearsal remain unexecuted external gates.

## S07 — Integrated verification, reviews, publication

1. Use disposable synthetic PostgreSQL to prove saved artifacts and entitlements remain unchanged across denied writes and archive reads/PDF.
2. Run full backend CI-equivalent Ruff/format/mypy and unit/integration regression coverage; local tool versions must match CI where drift matters. Run repo frontend gates/build and focused browser matrix.
3. Spec reviewer builds acceptance coverage across FEATURE/SRS/WORKFLOW/S01-S07; explicitly distinguishes verified local implementation from blocked production census/rollout/removal gates.
4. After spec PASS, independent code/security review challenges hidden worker writers, ownership/access ordering, race/stale identity, archive mutation and privacy/cardinality.
5. Fix all blockers, re-run affected/broader suites, sync each Story criterion and parent status. Commit coherent verified slices separately.
6. Publish and verify exact-SHA CI; deploy jobs must remain manual-only. No automatic closure of E20 while production criteria remain unavailable. Stage/production evidence remains blocked, not silently waived by the prior agreement that applied only to issue #51.

## Completion artifacts

Update every touched Story and FEATURE with verified criteria, commands/results, commit identity and explicit remaining blockers. Save review/evidence under `docs/reviews/` and link it from E20. Record production census as unavailable, physical data deletion as not performed, paid calls as not executed, and final removal as not authorized.
