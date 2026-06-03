# Индекс проекта Astrotype

Быстрая карта репозитория `D:\Python\Balthier\Archemap` для навигации по коду, документации, API и проверкам.

## 1. Что это за проект

Astrotype — full-stack SaaS для астрологических self-reports, соционики и продуктовых вертикалей. Архитектура: модульный монолит с FastAPI backend, Next.js frontend, PostgreSQL, Redis, Celery и MinIO/S3 для PDF-артефактов.

Основной pipeline:

```text
birth data
  -> chart snapshot
  -> normalized features
  -> rules engine
  -> claims + evidence
  -> narrative report
  -> UI / PDF
```

## 2. Быстрые ссылки

| Область | Куда идти |
| --- | --- |
| Общее описание и запуск | `README.md` |
| Дорожная карта | `docs/ROADMAP.md` |
| Полная продуктовая спецификация | `docs/SPEC.md` |
| API auth | `docs/API-AUTH.md` |
| OpenAPI contract | `contracts/openapi.yaml` |
| AsyncAPI/event contract | `contracts/asyncapi.yaml` |
| Дизайн-код | `docs/astrotype_design_code.md` |
| UX отчётов | `docs/design/report-ux-redesign.md` |
| Self storytelling | `docs/design/self-report-storytelling.md` |
| LLM narrative architecture | `docs/design/llm-report-narrative-architecture.md` |
| Feature/story docs | `docs/features/` |
| SRS docs | `docs/SRS/` |
| Kubernetes manifests | `infra/k8s/` |
| Local orchestration | `docker-compose.yml` |

## 3. Технологический стек

### Backend

- Python 3.12
- FastAPI + Pydantic v2
- SQLAlchemy 2 async + Alembic
- PostgreSQL 16
- Redis 7
- Celery
- Swiss Ephemeris / Flatlib
- WeasyPrint + Jinja2
- MinIO / S3
- Ruff, mypy, pytest

### Frontend

- Next.js 15
- React 19
- Tailwind CSS 4
- TanStack Query
- Zustand
- React Hook Form + Zod
- ESLint, Prettier, TypeScript

### Infra / integrations

- Docker Compose для локального окружения
- GitHub Actions CI/CD
- Yandex OAuth
- YooKassa / Yandex Pay architecture
- Kubernetes manifests под staging/production

## 4. Структура репозитория

```text
.
├── backend/                  # FastAPI backend, domain modules, rules, tests, Celery workers
│   ├── app/
│   │   ├── api/              # Versioned API, middleware, health routes
│   │   ├── chart_engine/     # Natal chart, ephemeris, socionics engine
│   │   ├── core/             # Shared kernel: settings, base models, secrets/security
│   │   ├── infrastructure/   # DB, Redis, email, geocoding, storage integrations
│   │   └── modules/          # Domain modules
│   ├── alembic/              # DB migrations
│   ├── rules/                # YAML rulesets by product vertical
│   ├── tests/                # Unit, integration, contract, chart tests
│   └── workers/              # Celery app and tasks
├── contracts/                # OpenAPI / AsyncAPI contracts
├── docs/                     # Product, SRS, design, feature/story documentation
├── frontend/                 # Next.js frontend
│   ├── scripts/              # Frontend regression scripts
│   └── src/
│       ├── app/              # Next.js App Router pages
│       ├── components/       # UI, chart, report, glossary, layout components
│       ├── hooks/            # React hooks
│       ├── lib/              # API clients, labels, report view models, utilities
│       ├── providers/        # React providers
│       ├── stores/           # Zustand stores
│       └── types/            # Shared TS types
├── infra/                    # Kubernetes manifests and overlays
├── scripts/                  # Utility scripts
├── docker-compose.yml        # Local services
└── README.md                 # Main project README
```

Текущий репозиторий содержит примерно 403 tracked files без dependency/build/generated директорий.

## 5. Backend domain index

| Модуль | Путь | Назначение |
| --- | --- | --- |
| API shell | `backend/app/api/` | Versioned router assembly, middleware, health endpoints |
| Auth | `backend/app/modules/auth/` | Registration, email verification, login/logout, refresh, password reset, Yandex OAuth, account linking |
| Users | `backend/app/modules/users/` | Current user profile, name update |
| Profiles | `backend/app/modules/profiles/` | Birth profiles CRUD, geocoding |
| Charts | `backend/app/modules/charts/` | Chart snapshots and chart retrieval by profile |
| Chart engine | `backend/app/chart_engine/` | Ephemeris, astrological objects, aspects, houses, socionics calculation |
| Rules | `backend/app/modules/rules/` | Rule engine API, ruleset loading, resolver, interpretation result |
| Reports | `backend/app/modules/reports/` | Report generation, versioning, PDF rendering/storage, report API |
| Payments | `backend/app/modules/payments/` | Payment models, YooKassa provider, payment webhook |
| Billing/subscriptions/catalog | `backend/app/modules/billing/`, `subscriptions/`, `catalog/` | Commercial domain boundaries / future product modules |
| Notifications/admin/webhooks | `backend/app/modules/notifications/`, `admin/`, `webhooks/` | Operational and integration boundaries |
| Core | `backend/app/core/` | Base model, production secret validation, shared security/config primitives |
| Infrastructure | `backend/app/infrastructure/` | DB/session, Redis, geocoding, email templates, external services |
| Workers | `backend/workers/` | Celery app and async report tasks |

## 6. Backend API index

Все product API подключаются под `/api/v1`.

### Health

- `GET /api/v1/health`
- `GET /api/v1/health/secrets`

### Auth: `/api/v1/auth`

- `POST /register`
- `POST /complete-profile`
- `POST /verify`
- `POST /resend-verification`
- `POST /refresh`
- `POST /logout`
- `POST /password-reset/request`
- `POST /password-reset/confirm`
- `POST /change-password`
- `GET /oauth/yandex/start`
- `GET /oauth/yandex/callback`
- `GET /linked-providers`
- `DELETE /unlink/{provider}`

### Users: `/api/v1/users`

- `GET /me`
- `PATCH /me`

### Profiles: `/api/v1/profiles`

- `GET /geocode`
- `POST /`
- `GET /`
- `GET /{profile_id}`
- `PATCH /{profile_id}`
- `DELETE /{profile_id}`

### Charts: `/api/v1/profiles/{profile_id}/chart`

- `POST /`
- `GET /`
- `GET /{snapshot_id}`

### Rules: `/api/v1/rules`

- `POST /interpret`
- `GET /rulesets`

### Reports: `/api/v1/reports`

- `POST /generate`
- `GET /`
- `GET /{report_id}`
- `GET /{report_id}/pdf`
- `GET /{report_id}/versions`
- `GET /{report_id}/versions/{version}`

### Payments: `/api/v1/payments`

- `POST /`
- `GET /`
- `GET /{payment_id}`
- `POST /webhooks/yookassa`

### Other mounted module prefixes

- `/api/v1/admin`
- `/api/v1/authorization`
- `/api/v1/billing`
- `/api/v1/catalog`
- `/api/v1/notifications`
- `/api/v1/reconciliation`
- `/api/v1/subscriptions`
- `/api/v1/webhooks`

## 7. Frontend route index

| Route | Source | Назначение |
| --- | --- | --- |
| `/` | `frontend/src/app/page.tsx` | Landing page |
| `/register` | `frontend/src/app/(auth)/register/page.tsx` | Registration / OAuth complete-profile flow |
| `/login` | `frontend/src/app/(auth)/login/page.tsx` | Login |
| `/verify` | `frontend/src/app/(auth)/verify/page.tsx` | Email verification / resend |
| `/forgot-password` | `frontend/src/app/(auth)/forgot-password/page.tsx` | Password reset request |
| `/reset-password` | `frontend/src/app/(auth)/reset-password/page.tsx` | Password reset confirm |
| `/auth/callback` | `frontend/src/app/(auth)/auth/callback/page.tsx` | OAuth callback UI |
| `/dashboard` | `frontend/src/app/(dashboard)/dashboard/page.tsx` | User dashboard and product cards |
| `/products/self` | `frontend/src/app/(dashboard)/products/self/page.tsx` | Self product flow |
| `/products/career` | `frontend/src/app/(dashboard)/products/career/page.tsx` | Career product flow |
| `/products/love` | `frontend/src/app/(dashboard)/products/love/page.tsx` | Love product page |
| `/products/child` | `frontend/src/app/(dashboard)/products/child/page.tsx` | Child product page |
| `/report/[profileId]` | `frontend/src/app/(dashboard)/report/[profileId]/page.tsx` | Report view |
| `/settings` | `frontend/src/app/(dashboard)/settings/page.tsx` | Profile settings and password change |
| `/billing` | `frontend/src/app/(dashboard)/billing/page.tsx` | Billing UI |
| `/subscriptions` | `frontend/src/app/(dashboard)/subscriptions/page.tsx` | Subscription UI |

## 8. Product verticals and rules

| Vertical | Rules path | Frontend path | Status |
| --- | --- | --- | --- |
| Self | `backend/rules/self/` | `frontend/src/app/(dashboard)/products/self/page.tsx` | Implemented |
| Career | `backend/rules/career/` | `frontend/src/app/(dashboard)/products/career/page.tsx` | Implemented |
| Love | planned | `frontend/src/app/(dashboard)/products/love/page.tsx` | Planned / product shell |
| Child | planned | `frontend/src/app/(dashboard)/products/child/page.tsx` | Planned / product shell |

Rule vertical structure:

```text
backend/rules/{vertical}/
├── archetypes_v1.yaml
└── evidence_templates_v1.yaml
```

## 9. Important implementation paths

### Auth and user identity

- `backend/app/modules/auth/router.py`
- `backend/app/modules/auth/service.py`
- `backend/app/modules/auth/schemas.py`
- `backend/app/modules/auth/verification.py`
- `backend/app/modules/auth/oauth/`
- `backend/app/modules/users/router.py`
- `backend/app/modules/users/models.py`
- `frontend/src/stores/auth-store.ts`
- `frontend/src/app/(auth)/register/page.tsx`
- `frontend/src/app/(auth)/login/page.tsx`
- `frontend/src/app/(auth)/verify/page.tsx`
- `frontend/src/app/(dashboard)/settings/page.tsx`

### Chart and socionics

- `backend/app/chart_engine/ephemeris.py`
- `backend/app/chart_engine/socionics.py`
- `backend/app/modules/charts/service.py`
- `backend/app/modules/charts/router.py`
- `backend/app/modules/charts/schemas.py`
- `backend/tests/chart/test_socionics.py`
- `frontend/src/components/chart/natal-chart.tsx`
- `frontend/src/lib/astrology/labels.ts`

### Reports

- `backend/app/modules/reports/service.py`
- `backend/app/modules/reports/router.py`
- `backend/app/modules/reports/models.py`
- `backend/app/modules/reports/schemas.py`
- `backend/app/modules/reports/pdf.py`
- `backend/app/modules/reports/storage.py`
- `backend/app/modules/reports/templates/report.html`
- `backend/workers/tasks/reports.py`
- `frontend/src/app/(dashboard)/report/[profileId]/page.tsx`
- `frontend/src/lib/report/view-model.ts`
- `frontend/src/lib/api/report.ts`
- `frontend/src/components/report/`

### Report UX / glossary / localization

- `frontend/src/components/report/report-header.tsx`
- `frontend/src/components/report/report-executive-summary.tsx`
- `frontend/src/components/report/astrology-overview.tsx`
- `frontend/src/components/report/archetype-profile-summary.tsx`
- `frontend/src/components/report/socionics-profile-simple.tsx`
- `frontend/src/components/report/technical-details-accordion.tsx`
- `frontend/src/components/glossary/term-help.tsx`
- `frontend/src/lib/glossary/report-glossary.ts`
- `frontend/scripts/check-report-ux.mjs`

### Payments

- `backend/app/modules/payments/models.py`
- `backend/app/modules/payments/router.py`
- `backend/app/modules/payments/schemas.py`
- `backend/app/modules/payments/service.py`
- `backend/app/modules/payments/providers/yookassa.py`
- `backend/alembic/versions/a7b8c9d0e1f2_add_payments_tables.py`

### Rate limiting and production safety

- `backend/app/api/middleware.py`
- `backend/app/api/v1/health.py`
- `backend/app/config.py`
- `backend/app/core/secrets.py`
- `backend/tests/unit/test_rate_limit.py`

## 10. Local runbook

### Docker start

```bash
cd /mnt/d/Python/Balthier/Archemap
docker compose up -d --build
```

Local URLs:

| Service | URL |
| --- | --- |
| Frontend | `http://localhost:3000` |
| Backend API | `http://localhost:8000` |
| Health | `http://localhost:8000/api/v1/health` |
| OpenAPI UI | `http://localhost:8000/docs` |
| MinIO Console | `http://localhost:9001` |
| PostgreSQL | `localhost:5432` |
| Redis | `localhost:6379` |

### Useful Docker commands

```bash
docker compose ps
docker compose logs -f backend
docker compose logs -f frontend
docker compose up -d --build
docker compose down
```

If local PostgreSQL auth/volume state is broken:

```bash
docker compose down -v
docker compose up -d --build
```

## 11. Quality gates

### Backend

```bash
cd backend
python3 -m ruff check .
python3 -m ruff format --check .
python3 -m mypy .
python3 -m pytest tests/unit -q
```

If host Python is missing project dependencies, run parity checks inside Docker backend:

```bash
docker compose exec -T backend sh -lc 'cd /app && python -m ruff check . && python -m ruff format --check . && python -m mypy . && python -m pytest tests/unit -q'
```

### Frontend

```bash
cd frontend
npm test
npx tsc --noEmit --pretty false
npx prettier --check .
npx eslint .
```

## 12. Documentation index

### Core docs

- `README.md` — overview, launch, structure, docs table, CI/CD.
- `docs/SPEC.md` — full product specification.
- `docs/ROADMAP.md` — epic roadmap and statuses.
- `docs/API-AUTH.md` — auth API behavior.
- `docs/MVP-STATUS.md` — MVP state.
- `docs/canonical-data-rules-socionics.md` — canonical domain/rules/socionics notes.
- `docs/Socionics/README.md` — socionics-specific documentation entry.

### Design docs

- `docs/astrotype_design_code.md` — visual identity and design tokens.
- `docs/design/report-ux-redesign.md` — report UX redesign.
- `docs/design/self-report-storytelling.md` — narrative-first Self report direction.
- `docs/design/llm-report-narrative-architecture.md` — controlled LLM narrative layer.

### Feature docs

Feature directories live under `docs/features/`:

- `E1-foundation`
- `E2-identity`
- `E3-chart-engine`
- `E4-rules-content`
- `E5-products-reports`
- `E6-billing-subscriptions`
- `E7-notifications-admin`
- `E8-production-scale`
- `E9-frontend-self-report`
- `E10-report-ux-redesign`

Each feature directory uses `FEATURE.md` plus story docs `Sxx-*.md`.

## 13. Common gotchas

- Canonical path for this request is `/mnt/d/Python/Balthier/Archemap`, which maps to `D:\Python\Balthier\Archemap`.
- In this environment `/home/balthier/archemap` currently resolves to the same physical path as `/mnt/d/Python/Balthier/Archemap`.
- Do not assume Docker is serving the same source tree unless mounts are checked with `docker inspect`.
- Backend health endpoint is `/api/v1/health`, not `/health`.
- Frontend protected fetches must support HttpOnly cookie auth; do not require JS token to exist before calling protected API.
- After socionics scoring changes, bump `ENGINE_VERSION` so cached chart snapshots recompute.
- Next dev cache can serve stale chunks; if source is fixed but UI is old, inspect served chunk and clear `/app/.next` inside frontend container.
- Keep Self report narrative-first. Raw scores, confidence and evidence belong in progressive disclosure.
- Self may mention career only briefly; deep career analysis belongs to Career product.

## 14. Maintenance rules for this index

Update this file when:

- a new backend module or router prefix is added;
- a new frontend route appears;
- a product vertical changes status;
- core docs are moved/renamed;
- local run or quality-gate commands change;
- Docker/Kubernetes service topology changes.
