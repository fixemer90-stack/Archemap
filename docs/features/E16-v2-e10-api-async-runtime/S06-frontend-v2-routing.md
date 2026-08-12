# Story S06: Frontend report links use Astrotype V2 runtime

**Feature:** E16 V2-E10 API Async Runtime

**Status:** In progress

## Goal

Switch active frontend Self-report navigation away from legacy `/report/[profileId]` and `/api/v1/reports` to Astrotype V2 natal-only report routes and `/api/v1/astrotype-v2/reports`.

## Context

The legacy Self report page still renders socionics-derived payloads from v1 report APIs. Astrotype V2 is natal-only and must not expose socionics, Model A, function strengths, archetype labels, or legacy report DTOs in active Self-report links.

## Scope

- Registration completion links for OAuth/full profile users.
- Dashboard “My reports” links.
- Self product “My reports Self” links.
- New frontend V2 report route under `/report/v2/[profileId]`.
- Static frontend guard that fails if default Self links point to legacy `/report/[profileId]`.

## Out of scope

- Career legacy report product migration.
- Deleting v1 report routes or data.
- Final production-grade V2 worker orchestration beyond existing API contract.

## Acceptance criteria

- Active Self-report frontend links use `/report/v2/${profileId}`.
- V2 page calls `POST /api/v1/astrotype-v2/reports` and reads existing reports via `GET /api/v1/astrotype-v2/reports/{reportId}` when available.
- V2 page does not import legacy report view-model, socionics components, or `/api/v1/reports` helpers.
- Static check prevents reintroducing legacy `/report/${profileId}` links in registration/dashboard/self product flows.
- TypeScript, lint, and targeted static guard pass.

## Verification commands

```bash
cd frontend
node scripts/check-v2-report-routing.mjs
npx eslint src/app/\(auth\)/register/page.tsx src/app/\(dashboard\)/dashboard/page.tsx src/app/\(dashboard\)/products/self/page.tsx src/app/\(dashboard\)/report/v2/\[profileId\]/page.tsx src/lib/api/astrotype-v2.ts scripts/check-v2-report-routing.mjs
npx tsc --noEmit
```
