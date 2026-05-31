# Spec: Archemap

## Objective

**Archemap** — платформа астрологического анализа личности. Четыре продуктовых вертикали на едином вычислительном ядре:

| Вертикаль | Что получает пользователь |
|---|---|
| **Archemap Self** | Натальная карта, архетипический портрет, персональный отчёт |
| **Archemap Love** | Совместимость, паттерны отношений, триггеры конфликтов |
| **Archemap Child** | Профиль ребёнка, рекомендации по воспитанию, семейная интерпретация |
| **Archemap Career** | Сильные стороны, подходящие роли, сценарии профессионального развития |

**Целевая аудитория:** русскоязычные пользователи 20–45 лет, интересующиеся самопознанием через астрологию. Международный рынок — вторая волна.

**Принцип:** вся интерпретация — rule-based на движке правил + шаблоны контента. AI используется только как вспомогательный инструмент для редактуры текстов, но не для генерации отчётов в рантайме.

**Success looks like:**
- Пользователь регистрируется через Yandex ID / email+password
- Вводит данные рождения → получает натальную карту + соционический тип за < 2 сек
- Видит score, confidence, evidence для каждого вывода
- Покупает отчёт через YooKassa / Stripe (planned)
- Получает детальный PDF-отчёт с интерпретацией (planned)
- Совместимость двух людей рассчитывается по двум картам (planned)
- Родитель добавляет профиль ребёнка и получает рекомендации (planned)
- Все 4 вертикали используют единый chart-engine + socionics engine

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python / FastAPI | 3.12+ / 0.136+ |
| ORM | SQLAlchemy + Alembic | 2.0+ / 1.18+ |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Queue | Celery + Redis broker | 5.6+ |
| Chart Engine | Swiss Ephemeris (swisseph) + Flatlib | latest |
| Socionics | Custom Model A engine (8 functions, 16 types) | v8 |
| Template Engine | Jinja2 | 3.1+ |
| Frontend | Next.js / React | 15 / 19 |
| UI | shadcn/ui + Tailwind CSS 4 + Cormorant Garamond / Inter | — |
| State | Zustand + TanStack Query | latest |
| Payments (RU) | YooKassa | — |
| Payments (Intl) | Stripe | — |
| Auth (OAuth) | Yandex ID | OAuth 2.1 + PKCE |
| PDF Generation | WeasyPrint / Playwright | — (planned) |
| CI | GitHub Actions | — |
| Containers | Docker + Docker Compose | — |

## Commands

```bash
# Infrastructure (Docker)
docker compose up -d              # Start all services (PG, Redis, backend, frontend)
docker compose down               # Stop all
docker compose up -d --build      # Rebuild after changes
docker compose logs -f backend    # Tail backend logs

# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload    # Dev server on :8000
alembic upgrade head              # Apply migrations
alembic revision --autogenerate -m "description"  # New migration
pytest tests/unit -v              # Unit tests
pytest tests/integration -v       # Integration tests
ruff check .                      # Lint
ruff format .                     # Format
mypy .                            # Type check

# Frontend
cd frontend
npm run dev                       # Dev server on :3000
npm run build                     # Production build
npx eslint .                      # Lint
npx prettier --check .            # Format check
npx tsc --noEmit                  # Type check
```

## Project Structure

```
Archemap/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint
│   │   ├── config.py               # pydantic-settings
│   │   ├── dependencies.py         # DI (db, auth, redis)
│   │   ├── core/                   # Shared kernel
│   │   │   ├── models.py           # Base SQLAlchemy models, mixins
│   │   │   ├── security.py         # JWT, password hashing, token blacklist
│   │   │   ├── exceptions.py       # Domain exceptions
│   │   │   └── rate_limit.py       # Redis-backed rate limiter
│   │   ├── infrastructure/         # database, redis, email, geocoding
│   │   │   ├── database.py         # Async engine, session factory
│   │   │   ├── redis.py            # Redis client
│   │   │   ├── email.py            # SMTP sender
│   │   │   ├── email_templates.py  # Email HTML/text templates
│   │   │   ├── geocoding.py        # Open-Meteo geocoding
│   │   │   └── storage.py          # S3-compatible file storage (placeholder)
│   │   ├── modules/                # Domain modules (Bounded Contexts)
│   │   │   ├── auth/               # Authentication & OAuth
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   ├── models.py       # User, EmailVerification, IdentityLink
│   │   │   │   ├── verification.py # Email verification
│   │   │   │   ├── password_reset.py
│   │   │   │   └── oauth/          # Yandex OAuth
│   │   │   │       ├── yandex.py
│   │   │   │       └── service.py
│   │   │   ├── profiles/           # Birth data & person profiles
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   └── models.py       # PersonProfile, ChartSnapshot
│   │   │   ├── chart_engine/       # Natal chart computation
│   │   │   │   ├── ephemeris.py    # Swiss Ephemeris wrapper
│   │   │   │   ├── houses.py       # House system (Placidus)
│   │   │   │   ├── aspects.py      # Aspect detection
│   │   │   │   └── socionics.py    # Socionics Model A engine
│   │   │   └── users/              # User management
│   │   │       ├── router.py
│   │   │       └── models.py
│   │   └── api/v1/                 # Versioned router aggregation
│   ├── alembic/                    # DB migrations
│   ├── tests/
│   │   ├── unit/                   # Fast, isolated tests
│   │   └── integration/            # DB/Redis dependent
│   ├── pyproject.toml
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router
│   │   │   ├── layout.tsx          # Root layout (Inter + Cormorant Garamond)
│   │   │   ├── globals.css         # Archemap design tokens + utilities
│   │   │   ├── (auth)/             # Login, register, verify, OAuth callback
│   │   │   └── (dashboard)/        # User dashboard
│   │   │       ├── report/         # Report page (natal chart + socionics)
│   │   │       ├── settings/
│   │   │       ├── billing/
│   │   │       └── subscriptions/
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn-style (glass cards, gradient buttons)
│   │   │   ├── layout/             # Header, sidebar, footer
│   │   │   └── chart/              # NatalChart, SocionicsResult (SVG radar)
│   │   ├── stores/                 # Zustand stores
│   │   ├── lib/                    # Utilities, API client
│   │   └── providers/              # Theme, Query providers
│   ├── Dockerfile
│   └── package.json
├── contracts/
│   ├── openapi.yaml                # HTTP API spec
│   └── asyncapi.yaml               # Webhook/event spec
├── docs/
│   ├── SPEC.md                     # This file
│   ├── ROADMAP.md                  # Roadmap
│   ├── archemap_design_code.md     # Design system & brand
│   ├── SRS/
│   │   ├── SRS-FRONTEND.md         # Frontend SRS (design system, components)
│   │   ├── SRS-E3-chart-engine.md  # Chart engine SRS
│   │   └── SRS-E4-rules-content.md # Rules & content SRS
│   └── features/                   # Feature specifications
├── .github/workflows/
│   ├── ci.yml                      # Lint, test, validate, build
│   └── deploy.yml                  # Deploy (placeholder)
├── docker-compose.yml              # Full-stack local dev
└── README.md
```

## Code Style

### Backend (Python)

```python
"""Domain: report generation service."""

from __future__ import annotations

from uuid import UUID

from app.chart_engine.chart import ChartSnapshot
from app.content.interpreter import InterpretationResult, interpret_chart
from app.content.renderer import render_report
from app.domains.reports.models import Report


class ReportService:
    """Генерация отчётов по натальной карте."""

    async def generate_self_report(
        self,
        user_id: UUID,
        chart: ChartSnapshot,
        rule_version: str,
    ) -> Report:
        """Создать персональный отчёт Self на основе натальной карты."""
        interpretation = interpret_chart(
            chart=chart,
            vertical="self",
            rule_version=rule_version,
        )
        html = render_report(
            template="self/full_report",
            context=interpretation.to_dict(),
        )
        # persist Report, return
```

**Conventions:**
- Python 3.12+ syntax, `from __future__ import annotations`
- Type hints everywhere, `dict[str, Any]` not bare `dict`
- Async/await for all I/O
- Modules: `snake_case`, Classes: `PascalCase`, Functions: `snake_case`
- API paths: `kebab-case`, Pydantic schemas: `PascalCase`
- Line length: 120, ruff for linting + formatting
- Domain logic в service layer, не в router
- Chart engine чистый — нет I/O, нет зависимостей от FastAPI

### Frontend (TypeScript)

```tsx
// Server Component by default
import { NatalChart } from "@/components/chart/natal-chart";
import { Button } from "@/components/ui/button";

interface SelfPageProps {
  params: Promise<{ profileId: string }>;
}

export default async function SelfPage({ params }: SelfPageProps) {
  const { profileId } = await params;
  const chart = await getChart(profileId);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Ваш архетипический портрет</h1>
      <NatalChart data={chart} />
      <Button variant="default">Скачать PDF-отчёт</Button>
    </div>
  );
}
```

**Conventions:**
- Server Components by default, `'use client'` only when needed
- Semantic color tokens: `text-primary`, `bg-card`, `text-muted-foreground`
- Mobile-first responsive: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
- Props interfaces: `ComponentProps` pattern
- Chart visualization — SVG-based, без тяжёлых библиотек

## Testing Strategy

| Level | Framework | Location | Coverage |
|---|---|---|---|
| Unit | pytest | tests/unit/ | Business logic, services, utils |
| Integration | pytest + Testcontainers | tests/integration/ | DB queries, Redis, API endpoints |
| Contract | Pact | tests/contract/ | PSP/IdP integration contracts |
| Golden | pytest + fixtures | tests/golden/ | Chart interpretation correctness |
| Chart Engine | pytest | tests/chart/ | Ephemeris, houses, aspects, synastry |
| E2E | Playwright | e2e/ | Critical user flows |
| Frontend | Vitest | src/**/*.test.tsx | Components, hooks |

**Golden tests — ключевой механизм уверенности в интерпретациях:**

```python
# tests/golden/test_self_golden.py
def test_sun_in_aries_interpretation():
    """Sun in Aries → archetype: Warrior, fire emphasis."""
    chart = load_fixture("sun_aries_12h")
    result = interpret_chart(chart, vertical="self", rule_version="v1")

    assert result.archetype.primary == "Warrior"
    assert result.element_distribution.fire > 0.4
    assert "leadership" in result.keywords
    assert_snapshot(result.to_dict(), "golden/self/sun_aries_v1.json")
```

**Rules:**
- Unit tests run without DB/Redis
- Integration tests use real PostgreSQL + Redis (via Docker)
- Golden tests: фиксированные chart fixtures → ожидаемые JSON snapshots
- При изменении правил интерпретации golden tests требуют явного обновления snapshot
- Every endpoint has at least one integration test
- Coverage target: 80%+ for business logic, 95%+ for chart engine

## Domain Entities

```
User                — учётная запись (email, hashed_password, birth_date, is_active, is_verified)
IdentityLink        — OAuth-связка (user_id, provider, provider_user_id)
EmailVerification   — токен верификации email (user_id, token, expires_at)
PersonProfile       — данные рождения (user_id, name, birth_date, birth_time, birth_place, lat, lon, timezone)
ChartSnapshot       — вычисленная карта (profile_id, planets:JSON, houses:JSON, aspects:JSON, socionics:JSON)
```

## Boundaries

### Always do
- Run `ruff check` + `mypy` before committing
- Write tests for new endpoints/services
- Golden tests при любом изменении правил интерпретации
- Use `from __future__ import annotations` in Python
- Use semantic color tokens in frontend (not raw hex)
- Follow conventional commits (feat:, fix:, refactor:)
- Chart engine — чистые функции, детерминированный вывод

### Ask first
- Database schema changes (new tables, columns, indexes)
- Adding new Python/Node dependencies
- Changing CI pipeline configuration
- Modifying authentication/authorization flow
- Changing payment provider integration
- Changing rule engine DSL or template syntax
- Adding new astrological points/aspects to the engine

### Never do
- Commit secrets (.env, API keys, tokens)
- Skip type annotations in new Python code
- Use `# type: ignore` without explaining why
- Mix formatting changes with behavior changes
- Push directly to main without CI passing
- Use AI/LLM for runtime report generation (rule-based only)
- Hardcode interpretation text in Python code (must be in templates/rules)
- Call chart engine from inside FastAPI request handlers synchronously (use Celery for heavy computation)

## Success Criteria

### Phase 1: Foundation ✅
- [x] Project scaffolding (backend, frontend, infra)
- [x] CI pipeline with all quality gates (ruff, mypy, eslint, prettier, tsc)
- [x] Health endpoint with DB + Redis checks
- [x] Alembic migrations (auto-apply on container start)
- [x] User model + registration endpoint (email+password + birth data)
- [x] JWT access/refresh tokens (httpOnly cookies)
- [x] Email verification
- [x] Token blacklist (logout)
- [x] Yandex ID OAuth integration (scope: login:birthday, login:email)
- [ ] VK ID OAuth integration

### Phase 2: Chart Engine ✅
- [x] Swiss Ephemeris integration (12 planets + Lilith)
- [x] House system calculation (Placidus)
- [x] Aspect detection with orbs (applying/separating)
- [x] ChartSnapshot model + computation pipeline
- [x] PersonProfile CRUD (birth data input + geocoding)
- [x] Socionics Model A engine (8 functions, 16 types, top3, confidence)
- [ ] Chart engine golden tests

### Phase 3: Content & Reports (Archemap Self)
- [ ] Rule engine: YAML rulesets → InterpretationResult
- [ ] Jinja2 template system for reports
- [ ] Self vertical: archetype portrait rules + templates
- [ ] PDF generation (WeasyPrint)
- [ ] Report generation as Celery task
- [ ] Golden tests for Self vertical

### Phase 4: Payments & Billing
- [ ] Plan model + admin CRUD
- [ ] YooKassa adapter (cards, SBP)
- [ ] Stripe adapter (international)
- [ ] Webhook intake + idempotent processing
- [ ] Subscription lifecycle (create, renew, cancel)
- [ ] Entitlement engine (vertical access gating)

### Phase 5: Remaining Verticals
- [ ] Archemap Love: compatibility rules, synastry templates
- [ ] Archemap Child: child profile, parenting rules
- [ ] Archemap Career: strengths & roles rules
- [ ] Golden tests for all verticals

### Phase 6: Production Readiness
- [x] Rate limiting (Redis-backed token bucket)
- [ ] WAF configuration
- [ ] Secrets management
- [ ] Observability (traces, metrics, alerts)
- [ ] Load testing
- [ ] Admin dashboard

## Open Questions

1. ~~Какую систему домов использовать по умолчанию — Placidus или Equal?~~ → **Placidus** (реализовано)
2. ~~Нужна ли поддержка астероидов (Chiron, Lilith) в первой версии?~~ → **Lilith да, Chiron нет** (нет файлов эфемерид)
3. Как хранить версии правил — Git + deploy или runtime из БД с hot-reload?
4. PDF-отчёты: WeasyPrint (CSS→PDF) или Playwright (HTML→PDF через Chromium)?
5. Совместимость: только синастрия или ещё composite chart?
6. ~~Точность времени рождения — как обрабатывать неизвестное время?~~ → **12:00 по умолчанию + birth_time_accuracy поле** (реализовано)
7. ~~Нужна ли интерактивная карта на фронте или только статичный SVG?~~ → **SVG колесо + табличный вид** (реализовано)
8. Какой лимит бесплатного контента — полная карта без интерпретации или краткий отчёт?
9. Мультиязычность: только RU на старте или сразу RU+EN?
10. Нужен ли admin UI в первой версии или только API?
