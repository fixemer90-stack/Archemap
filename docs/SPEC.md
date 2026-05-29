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
- Пользователь регистрируется через VK ID / Yandex ID / email+password
- Вводит данные рождения → получает натальную карту за < 2 сек
- Покупает отчёт через YooKassa / CloudPayments / Stripe
- Получает детальный PDF-отчёт с интерпретацией
- Совместимость двух людей рассчитывается по двум картам
- Родитель добавляет профиль ребёнка и получает рекомендации
- Все 4 вертикали используют единый chart-engine

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Backend | Python / FastAPI | 3.12+ / 0.115+ |
| ORM | SQLAlchemy + Alembic | 2.0+ / 1.14+ |
| Database | PostgreSQL | 16 |
| Cache | Redis | 7 |
| Queue | Celery + Redis broker | 5.4+ |
| Chart Engine | Swiss Ephemeris (swisseph) + Flatlib | latest |
| Template Engine | Jinja2 | 3.1+ |
| Frontend | Next.js / React | 15 / 19 |
| UI | shadcn/ui + Tailwind CSS | 4 |
| State | Zustand + TanStack Query | latest |
| Payments (RU) | YooKassa + CloudPayments | — |
| Payments (Intl) | Stripe | — |
| Auth (OAuth) | VK ID + Yandex ID | OAuth 2.1 + PKCE |
| PDF Generation | WeasyPrint / Playwright | — |
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
pytest tests/golden -v           # Golden tests for chart interpretation
pytest tests/chart -v            # Chart engine tests (ephemeris + flatlib)
ruff check .                     # Lint
ruff format .                    # Format
mypy .                           # Type check

# Chart Engine
python -m app.chart_engine.compute --date 1990-05-15 --time 14:30 --lat 55.75 --lon 37.62  # CLI test

# Content
python -m app.content.build_templates  # Compile templates from source

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
│   │   ├── main.py                 # FastAPI entrypoint
│   │   ├── config.py               # pydantic-settings
│   │   ├── dependencies.py         # DI (db, auth, redis)
│   │   ├── core/                   # Shared kernel
│   │   │   ├── models.py           # Base SQLAlchemy models, mixins
│   │   │   ├── security.py         # JWT, password hashing, token blacklist
│   │   │   ├── exceptions.py       # Domain exceptions
│   │   │   └── events.py           # Event bus primitives
│   │   ├── infrastructure/         # database, redis, queue, email, storage
│   │   │   ├── database.py         # Async engine, session factory
│   │   │   ├── redis.py            # Redis client
│   │   │   ├── email.py            # SMTP sender
│   │   │   └── storage.py          # S3-compatible file storage
│   │   ├── chart_engine/           # Астрологическое вычислительное ядро
│   │   │   ├── __init__.py
│   │   │   ├── ephemeris.py        # Swiss Ephemeris wrapper (planets, points)
│   │   │   ├── houses.py           # House system calculations (Placidus default)
│   │   │   ├── aspects.py          # Aspect detection (orbs, applying/separating)
│   │   │   ├── chart.py            # ChartSnapshot builder
│   │   │   ├── compatibility.py    # Synastry + composite chart logic
│   │   │   ├── compute.py          # CLI entrypoint for testing
│   │   │   └── types.py            # Dataclasses: Planet, House, Aspect, ChartData
│   │   ├── content/                # Интерпретация и шаблоны контента
│   │   │   ├── __init__.py
│   │   │   ├── rules/              # YAML/JSON rulesets per vertical
│   │   │   │   ├── self.yaml       # Self: archetype rules
│   │   │   │   ├── love.yaml       # Love: compatibility rules
│   │   │   │   ├── child.yaml      # Child: parenting rules
│   │   │   │   └── career.yaml     # Career: strengths & roles rules
│   │   │   ├── templates/          # Jinja2 report templates
│   │   │   │   ├── self/
│   │   │   │   ├── love/
│   │   │   │   ├── child/
│   │   │   │   └── career/
│   │   │   ├── interpreter.py      # Rule engine: ChartData → InterpretationResult
│   │   │   └── renderer.py         # Jinja2 renderer: InterpretationResult → text/HTML
│   │   ├── domains/                # Domain modules (Bounded Contexts)
│   │   │   ├── auth/               # Authentication & OAuth
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   ├── models.py       # IdentityLink, Consent
│   │   │   │   └── providers/      # vk_id.py, yandex_id.py
│   │   │   ├── users/              # User management
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── models.py       # User
│   │   │   ├── profiles/           # Birth data & person profiles
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── models.py       # PersonProfile, ChartSnapshot
│   │   │   ├── reports/            # Report generation & delivery
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   ├── models.py       # Report, RuleSetVersion, TemplateVersion
│   │   │   │   └── pdf.py          # PDF rendering
│   │   │   ├── billing/            # Plans, subscriptions, entitlements
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   ├── models.py       # Plan, Subscription, Entitlement
│   │   │   │   └── lifecycle.py    # Subscription state machine
│   │   │   ├── payments/           # PSP integration
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   ├── models.py       # PaymentAttempt, WebhookEvent
│   │   │   │   └── adapters/       # yookassa.py, cloudpayments.py, stripe.py
│   │   │   ├── notifications/      # Email, push, in-app notifications
│   │   │   │   ├── router.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── service.py
│   │   │   │   └── models.py       # Notification
│   │   │   └── admin/              # Admin dashboard API
│   │   │       ├── router.py
│   │   │       └── schemas.py
│   │   └── api/v1/                 # Versioned router aggregation
│   │       └── __init__.py
│   ├── workers/                    # Celery tasks
│   │   ├── report_tasks.py         # Async report generation
│   │   ├── billing_tasks.py        # Subscription renewal, reconciliation
│   │   └── notification_tasks.py   # Email/push delivery
│   ├── tests/
│   │   ├── unit/                   # Fast, isolated tests
│   │   ├── integration/            # DB/Redis dependent
│   │   ├── contract/               # API contract tests
│   │   ├── golden/                 # Golden tests: chart → expected interpretation
│   │   │   ├── fixtures/           # Reference charts with known data
│   │   │   ├── test_self_golden.py
│   │   │   ├── test_love_golden.py
│   │   │   ├── test_child_golden.py
│   │   │   └── test_career_golden.py
│   │   └── chart/                  # Chart engine unit tests
│   │       ├── test_ephemeris.py
│   │       ├── test_houses.py
│   │       ├── test_aspects.py
│   │       └── test_compatibility.py
│   └── alembic/
├── frontend/
│   ├── src/
│   │   ├── app/                    # Next.js App Router
│   │   │   ├── (marketing)/        # Landing pages per vertical
│   │   │   ├── (auth)/             # Login, register, verify
│   │   │   ├── (dashboard)/        # User dashboard
│   │   │   │   ├── self/           # Archemap Self flow
│   │   │   │   ├── love/           # Archemap Love flow
│   │   │   │   ├── child/          # Archemap Child flow
│   │   │   │   └── career/         # Archemap Career flow
│   │   │   └── admin/              # Admin panel
│   │   ├── components/
│   │   │   ├── ui/                 # shadcn-style components
│   │   │   ├── layout/             # Header, sidebar, footer
│   │   │   ├── chart/              # Natal chart visualization (SVG)
│   │   │   └── reports/            # Report preview components
│   │   ├── stores/                 # Zustand stores
│   │   ├── hooks/                  # Custom hooks
│   │   └── lib/                    # Utilities, API client
│   └── public/
├── contracts/
│   ├── openapi.yaml                # HTTP API spec
│   └── asyncapi.yaml               # Webhook/event spec
├── docs/
│   ├── SPEC.md                     # This file
│   ├── adr/                        # Architecture decisions
│   └── deep-research-report.md     # Architecture research
└── docker-compose.yml
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
User                — учётная запись (email, name, status)
IdentityLink        — OAuth-связка (user_id, provider, provider_user_id)
Consent             — согласия пользователя (terms, privacy, marketing)
PersonProfile       — данные рождения (date, time, lat, lon, timezone, name)
ChartSnapshot       — вычисленная карта (profile_id, chart_data: JSON, computed_at)
RuleSetVersion      — версия правил интерпретации (vertical, version, rules: JSON)
TemplateVersion     — версия шаблона отчёта (vertical, version, template: text)
Report              — готовый отчёт (user_id, vertical, chart_snapshot_id, content, pdf_url)
Plan                — тарифный план (vertical, price, interval, features)
Subscription        — подписка (user_id, plan_id, status, current_period_end)
PaymentAttempt      — попытка платежа (subscription_id, provider, amount, status)
WebhookEvent        — входящий вебхук от PSP (provider, payload, processed_at)
Entitlement         — право доступа (user_id, vertical, valid_until)
Notification        — уведомление (user_id, channel, template, sent_at)
AuditEvent          — аудит-лог (actor_id, action, target, metadata)
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

### Phase 1: Foundation (current)
- [x] Project scaffolding (backend, frontend, infra)
- [x] CI pipeline with all quality gates
- [x] Health endpoint with DB + Redis checks
- [x] Alembic migrations working
- [x] User model + registration endpoint (email+password)
- [x] JWT access/refresh tokens
- [x] Email verification
- [x] Token blacklist (logout)
- [ ] VK ID OAuth integration
- [ ] Yandex ID OAuth integration

### Phase 2: Chart Engine
- [ ] Swiss Ephemeris integration (planets, asteroids, points)
- [ ] House system calculation (Placidus)
- [ ] Aspect detection with orbs
- [ ] ChartSnapshot model + computation pipeline
- [ ] PersonProfile CRUD (birth data input)
- [ ] Chart engine golden tests (10+ reference charts)

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
- [ ] CloudPayments adapter
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
- [ ] Rate limiting
- [ ] WAF configuration
- [ ] Secrets management
- [ ] Observability (traces, metrics, alerts)
- [ ] Load testing
- [ ] Apple/Google in-app billing (mobile)
- [ ] Admin dashboard

## Open Questions

1. Какую систему домов использовать по умолчанию — Placidus или Equal? (рекомендация: Placidus)
2. Нужна ли поддержка астероидов (Chiron, Lilith) в первой версии или только классические планеты?
3. Как хранить версии правил — Git + deploy или runtime из БД с hot-reload?
4. PDF-отчёты: WeasyPrint (CSS→PDF) или Playwright (HTML→PDF через Chromium)?
5. Совместимость: только синастрия или ещё composite chart?
6. Точность времени рождения — как обрабатывать неизвестное время (полудуга, solar chart)?
7. Нужна ли интерактивная карта на фронте или только статичный SVG?
8. Какой лимит бесплатного контента — полная карта без интерпретации или краткий отчёт?
9. Мультиязычность: только RU на старте или сразу RU+EN?
10. Нужен ли admin UI в первой версии или только API?
