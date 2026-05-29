# Spec: Archemap

## Objective


**Success looks like:**
- Пользователь может войти через VK ID
- Пользователь может просмотреть тарифные планы и оформить подписку
- Платёж обрабатывается через PSP-адаптер
- Подписка автоматически продлевается по расписанию
- Пользователь получает уведомления о предстоящих списаниях
- Администратор видит биллинговую аналитику

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python / FastAPI | 3.12+ / 0.115+ |
| ORM | SQLAlchemy + Alembic | 2.0+ / 1.14+ |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Queue | Celery + Redis broker | 5.4+ |
| Frontend | Next.js / React | 15 / 19 |
| UI | shadcn/ui + Tailwind CSS | 4 |
| State | Zustand + TanStack Query | latest |
| CI | GitHub Actions | — |
| Containers | Docker + Docker Compose | — |

## Commands

```bash
# Infrastructure
make infra-up                    # Start PostgreSQL + Redis
make infra-down                  # Stop services

# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload   # Dev server on :8000
alembic upgrade head             # Apply migrations
alembic revision --autogenerate -m "description"  # New migration
pytest tests/unit -v             # Unit tests
pytest tests/integration -v      # Integration tests
ruff check .                     # Lint
ruff format .                    # Format
mypy .                           # Type check

# Frontend
cd frontend
npm run dev                      # Dev server on :3000
npm run build                    # Production build
npm test                         # Tests
npx eslint .                     # Lint
npx tsc --noEmit                 # Type check

# All
make lint                        # Lint everything
make test                        # Test everything
make format                      # Format everything
```

## Project Structure

```
Archemap/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint
│   │   ├── config.py            # pydantic-settings
│   │   ├── dependencies.py      # DI (db, auth, redis)
│   │   ├── core/                # Shared kernel (models, security, exceptions)
│   │   ├── infrastructure/      # database, redis, queue, storage
│   │   ├── api/v1/              # Versioned endpoints
│   │   └── modules/             # Domain modules (11 modules)
│   │       ├── {module}/
│   │       │   ├── router.py    # Endpoints
│   │       │   ├── schemas.py   # Pydantic models
│   │       │   ├── service.py   # Business logic
│   │       │   ├── repository.py # Data access
│   │       │   └── models.py    # SQLAlchemy models
│   ├── workers/                 # Celery tasks
│   ├── tests/
│   │   ├── unit/                # Fast, isolated tests
│   │   ├── integration/         # DB/Redis dependent
│   │   └── contract/            # API contract tests
│   └── alembic/                 # DB migrations
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router
│   │   ├── components/ui/       # shadcn-style components
│   │   ├── components/layout/   # Header, sidebar, footer
│   │   ├── stores/              # Zustand stores
│   │   ├── hooks/               # Custom hooks
│   │   └── lib/                 # Utilities, API client
│   └── public/
├── contracts/
│   ├── openapi.yaml             # HTTP API spec
│   └── asyncapi.yaml            # Webhook/event spec
├── docs/
│   ├── adr/                     # Architecture decisions
│   └── deep-research-report.md  # Architecture research
└── docker-compose.yml           # Local infrastructure
```

## Code Style

### Backend (Python)

```python
"""Module docstring describing purpose."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/")
async def list_subscriptions(
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List user's subscriptions with pagination."""
    # implementation
```

**Conventions:**
- Python 3.12+ syntax, `from __future__ import annotations`
- Type hints everywhere, `dict[str, Any]` not bare `dict`
- Async/await for all I/O
- Modules: `snake_case`, Classes: `PascalCase`, Functions: `snake_case`
- API paths: `kebab-case`, Pydantic schemas: `PascalCase`
- Line length: 120, ruff for linting + formatting

### Frontend (TypeScript)

```tsx
// Server Component by default
import { Button } from "@/components/ui/button";

export default function Page() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Title</h1>
      <Button variant="default">Action</Button>
    </div>
  );
}
```

**Conventions:**
- Server Components by default, `'use client'` only when needed
- Semantic color tokens: `text-primary`, `bg-card`, `text-muted-foreground`
- Mobile-first responsive: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
- Use `<Button>` component, not inline `<a>` styled as button
- Props interfaces: `ComponentProps` pattern

## Testing Strategy

| Level | Framework | Location | Coverage |
|---|---|---|---|
| Unit | pytest | tests/unit/ | Business logic, services, utils |
| Integration | pytest + Testcontainers | tests/integration/ | DB queries, Redis, API endpoints |
| Contract | Pact | tests/contract/ | PSP/IdP integration contracts |
| E2E | Playwright | e2e/ | Critical user flows |
| Frontend | Vitest | src/**/*.test.tsx | Components, hooks |

**Rules:**
- Unit tests run without DB/Redis
- Integration tests use real PostgreSQL + Redis (via Docker)
- Every endpoint has at least one integration test
- Every service method has unit tests for edge cases
- Coverage target: 80%+ for business logic

## Boundaries

### Always do
- Run `ruff check` + `mypy` before committing
- Write tests for new endpoints/services
- Use `from __future__ import annotations` in Python
- Use semantic color tokens in frontend (not raw hex)
- Follow conventional commits (feat:, fix:, refactor:)

### Ask first
- Database schema changes (new tables, columns, indexes)
- Adding new Python/Node dependencies
- Changing CI pipeline configuration
- Modifying authentication/authorization flow
- Changing payment provider integration

### Never do
- Commit secrets (.env, API keys, tokens)
- Skip type annotations in new Python code
- Use `# type: ignore` without explaining why
- Mix formatting changes with behavior changes
- Push directly to main without CI passing

## Success Criteria

### Phase 1: Foundation (current)
- [x] Project scaffolding (backend, frontend, infra)
- [x] CI pipeline with all quality gates
- [x] Health endpoint with DB + Redis checks
- [x] Alembic migrations working
- [ ] User model + registration endpoint
- [ ] VK ID OAuth integration

### Phase 2: Auth & Users
- [ ] VK ID OAuth 2.1 + PKCE login flow
- [ ] JWT access/refresh token issuance
- [ ] Account linking (multiple IdPs)
- [ ] User profile CRUD
- [ ] Admin MFA

### Phase 3: Subscriptions & Billing
- [ ] Product catalog + pricing plans
- [ ] Subscription lifecycle (create, pause, cancel, renew)
- [ ] Invoice generation
- [ ] Entitlement engine

### Phase 4: Payments
- [ ] Payment orchestrator interface
- [ ] First PSP adapter (Stripe)
- [ ] Webhook intake + verification
- [ ] Idempotent payment processing
- [ ] Reconciliation service

### Phase 5: Production Readiness
- [ ] Rate limiting
- [ ] WAF configuration
- [ ] Secrets management
- [ ] Observability (traces, metrics, alerts)
- [ ] Load testing

## Open Questions

1. Первый PSP — Stripe или ЮKassa? (зависит от целевого рынка)
2. Нужен ли hosted checkout или своя платёжная форма?
3. Тарифные планы — фиксированные или usage-based?
4. Какие уведомления приоритетнее — email, push, in-app?
5. Нужен ли admin UI в первой версии или только API?
