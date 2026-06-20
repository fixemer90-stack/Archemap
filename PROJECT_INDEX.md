# PROJECT_INDEX

## Что это

Astrotype — full-stack narrative-first платформа для астрологических отчётов, соционики и продуктовых вертикалей. Детерминированный backend считает карту, признаки, архетипы и evidence trail; UI и PDF показывают human-readable narrative поверх этих данных.

## Быстрые ссылки

- README: `README.md`
- Product spec: `docs/SPEC.md`
- Roadmap: `docs/ROADMAP.md`
- OpenAPI: `contracts/openapi.yaml`
- AsyncAPI: `contracts/asyncapi.yaml`
- LLM design: `docs/design/llm-report-narrative-architecture.md`
- E11 feature pack: `docs/features/E11-llm-report-narrative/FEATURE.md`
- E13 report depth improvements: `docs/features/E13-report-depth-improvements/FEATURE.md`
- E2 identity auth cleanup: `docs/features/E2-identity/S10-cookie-first-session-auth.md`
- E2 auth workflow/API: `docs/features/E2-identity/WORKFLOW.md`, `docs/features/E2-identity/API.md`
- SRS E11: `docs/SRS/SRS-E11-llm-report-narrative.md`
- SRS E13: `docs/SRS/SRS-E13-report-depth-improvements.md`

## Tech stack

- Backend: FastAPI, SQLAlchemy 2 async, PostgreSQL, Redis
- Frontend: Next.js 15, React 19, Tailwind 4, Zustand, TanStack Query
- Workers: Celery-style async task bridge
- PDF: WeasyPrint + Jinja2
- Storage: MinIO / S3
- CI: GitHub Actions (`.github/workflows/ci.yml`)

## Repository map

```text
backend/
  app/
    api/                 Versioned API routers and middleware
    chart_engine/        Natal chart + socionics computation
    core/                Settings, base models, exceptions, secrets
    infrastructure/      DB, Redis, email, storage, geocoding
    modules/             Product/domain modules
  alembic/               Migrations
  rules/                 Deterministic interpretation rules
  tests/                 Unit + integration tests
  workers/               Worker entrypoints
frontend/
  src/app/               App Router pages
  src/components/        UI/report/chart/layout components
  src/lib/               API client, adapters, labels, utils
  scripts/               Structural regression checks
contracts/               OpenAPI + AsyncAPI
.docs/ not used
.github/workflows/       CI/CD workflows
docs/                    Design, SRS, feature stories, reviews
```

## Backend module index

- `app/modules/auth/` — login, register, OAuth, password reset, account linking; target browser auth is cookie-first via HttpOnly `access_token`/`refresh_token`, with Bearer only as API-client fallback
- `app/modules/users/` — `/users/me`, profile name update
- `app/modules/profiles/` — person profiles, geocoding inputs
- `app/modules/charts/` — chart snapshots and socionics computation
- `app/modules/rules/` — deterministic rules/resolver/interpretation
- `app/modules/reports/` — report persistence, API, PDF, storage, tasks
- `app/modules/report_narratives/` — LLM narrative layer over deterministic reports
- `app/modules/payments/` — YooKassa payment flow
- `app/modules/llm/` — provider abstraction, mock/openrouter providers

## LLM narrative implementation paths

Core backend:
- `backend/app/modules/report_narratives/schemas.py` — `NarrativeInput`, `SelfNarrative`
- `backend/app/modules/report_narratives/input_builder.py` — deterministic DTO builder
- `backend/app/modules/report_narratives/hash.py` — stable narrative input hash
- `backend/app/modules/report_narratives/prompts.py` + `prompts/` — prompt loading/versioning
- `backend/app/modules/report_narratives/validators.py` — contract validation + recovery policy
- `backend/app/modules/report_narratives/fallback.py` — deterministic fallback narrative
- `backend/app/modules/report_narratives/service.py` — cache, generation, validation, structured logs
- `backend/app/modules/report_narratives/tasks.py` — async task orchestration helpers
- `backend/app/modules/report_narratives/models.py` — `ReportNarrative` storage model

LLM provider layer:
- `backend/app/modules/llm/provider.py` — factory
- `backend/app/modules/llm/providers/mock.py` — offline-safe test provider
- `backend/app/modules/llm/providers/openrouter.py` — real network provider

Report integration:
- `backend/app/modules/reports/router.py` — report endpoints
- `backend/app/modules/reports/schemas.py` — response contracts with narrative status/payload
- `backend/app/modules/reports/tasks.py` — PDF task wiring reads saved narrative JSON
- `backend/app/modules/reports/pdf.py` — PDF rendering from deterministic data + saved narrative
- `backend/app/modules/reports/templates/report.html` — narrative-first PDF template
- `backend/workers/tasks/reports.py` — worker entrypoints

## Frontend route/component index

Routes:
- `frontend/src/app/(dashboard)/dashboard/page.tsx` — dashboard
- `frontend/src/app/(dashboard)/products/self/page.tsx` — Self product
- `frontend/src/app/(dashboard)/products/career/page.tsx` — Career product
- `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` — report page with polling/fallback
- `frontend/src/app/(auth)/register/page.tsx` — registration + OAuth complete-profile

Narrative UI:
- `frontend/src/components/report/report-generation-progress.tsx` — generating state
- `frontend/src/components/report/deterministic-report-fallback.tsx` — fallback after timeout/failure
- `frontend/src/components/report/report-narrative-page.tsx` — ready narrative rendering root
- `frontend/src/components/report/narrative-section.tsx` — narrative section renderer
- `frontend/src/components/report/career-cta.tsx` — Self→Career upsell block
- `frontend/src/components/report/evidence-notes.tsx` — collapsed evidence disclosure
- `frontend/src/lib/report/view-model.ts` — narrative + deterministic adapter
- `frontend/src/lib/api/report.ts` — report API contract and regenerate endpoint

## API/route index

Main REST prefix: `/api/v1`

Important auth routes:
- `POST /api/v1/auth/login` — email/password login; target browser flow sets HttpOnly cookies
- `POST /api/v1/auth/refresh` — cookie-native refresh with legacy body fallback during migration
- `POST /api/v1/auth/logout` — revoke tokens and clear auth cookies
- `GET /api/v1/users/me` — session bootstrap from cookie-backed auth

Important report routes:
- `POST /api/v1/reports/generate`
- `GET /api/v1/reports/{report_id}`
- `GET /api/v1/reports`
- `GET /api/v1/reports/{report_id}/versions`
- `POST /api/v1/reports/{report_id}/narrative/regenerate`
- `POST /api/v1/reports/{report_id}/pdf`

Health:
- `GET /api/v1/health`

## Rules/product verticals

- `backend/rules/self/` — Self archetypes and evidence templates
- `backend/rules/career/` — Career archetypes and evidence templates
- Future verticals follow the same pattern under `backend/rules/{vertical}/`

## Quality gates

Backend:
```bash
cd backend
ruff check .
ruff format --check .
mypy .
pytest tests/unit -q
pytest tests/integration -q
```

Frontend:
```bash
cd frontend
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
npm run build
```

Report narrative regression focus:
- `backend/tests/unit/test_report_narratives/`
- `backend/tests/unit/test_reports/test_pdf.py`
- `frontend/scripts/check-report-ux.mjs`

CI guardrails:
- `.github/workflows/ci.yml` explicitly pins test env to `LLM_PROVIDER=mock` and `LLM_ENABLED=false`
- Automated tests must not hit real LLM network providers

## Local runbook

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/api/v1/health
```

Useful logs:
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

If Postgres auth/volumes are broken:
```bash
docker compose down -v
docker compose up -d --build
```

## Documentation index

- `docs/design/report-ux-redesign.md`
- `docs/design/self-report-storytelling.md`
- `docs/design/llm-report-narrative-architecture.md`
- `docs/features/E11-llm-report-narrative/FEATURE.md`
- `docs/features/E13-report-depth-improvements/FEATURE.md`
- `docs/features/E2-identity/FEATURE.md`
- `docs/features/E2-identity/S10-cookie-first-session-auth.md`
- `docs/SRS/SRS-E2-identity-auth.md`
- `docs/SRS/SRS-E11-llm-report-narrative.md`
- `docs/SRS/SRS-E13-report-depth-improvements.md`

## Current known gotchas

- `/home/balthier/archemap` and `/mnt/d/Python/Balthier/Archemap` may drift; verify before editing docs/config.
- Report docs must stay honest: story is not done until code/tests/runtime checks actually pass.
- PDF runtime in the current backend container still needs WeasyPrint system libs for real end-to-end smoke.
- Frontend report regression is structural: `npm test` runs `scripts/check-report-ux.mjs`, not a browser unit test runner.
- OAuth cookie-auth flows must work even when JS token state is empty.
