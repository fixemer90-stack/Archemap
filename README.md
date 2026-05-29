# Archemap

Платформа подписок и аккаунтов с модульной архитектурой, multi-provider авторизацией и платёжным оркестратором.

## Архитектура

Модульный монолит с чёткими доменными границами. C4-модель как код. Contract-first подход через OpenAPI/AsyncAPI.

Документация архитектуры: [docs/deep-research-report.md](deep-research-reportv1.md)

## Стек технологий

### Backend

| Компонент | Технология | Обоснование |
|---|---|---|
| **Фреймворк** | FastAPI (Python 3.12+) | Async-native, автоматическая OpenAPI-генерация, Pydantic-валидация, высокая производительность |
| **ORM** | SQLAlchemy 2.0 + Alembic | Зрелый async ORM, миграции схемы, поддержка repository pattern |
| **База данных** | PostgreSQL 16 | ACID для ledger/подписок, JSONB для гибких атрибутов, расширения (pgcrypto, uuid-ossp) |
| **Кэш / Rate Limiting** | Redis 7 | Сессии, rate limiting, short-lived cache, pub/sub для инвалидации |
| **Очередь задач** | Celery + Redis (broker) | Фоновые задачи: renewal, reconciliation, email, retries |
| **HTTP-клиент** | httpx | Async HTTP для интеграций с PSP/IdP |
| **Валидация** | Pydantic v2 | Строгая типизация запросов/ответов, автоматическая JSON Schema |

### Frontend

| Компонент | Технология | Обоснование |
|---|---|---|
| **Фреймворк** | Next.js 15 (React 19) | SSR/SSG, App Router, Server Components, middleware для auth |
| **UI-библиотека** | shadcn/ui + Tailwind CSS 4 | Кастомизируемые компоненты, дизайн-система, tree-shaking |
| **State management** | Zustand | Лёгкий, типизированный, без boilerplate |
| **API-клиент** | OpenAPI Generator (TypeScript) | Автогенерация типов и клиентов из openapi.yaml |
| **Формы** | React Hook Form + Zod | Валидация на клиенте, типобезопасность |

### Инфраструктура

| Компонент | Технология | Обоснование |
|---|---|---|
| **Контейнеризация** | Docker + Docker Compose | Локальная разработка, воспроизводимые окружения |
| **CI/CD** | GitHub Actions | Lint, тесты, contract validation, build, deploy |
| **Миграции БД** | Alembic | Версионированная миграция схемы, downgrade support |
| **Секреты** | .env (dev), Vault/K8s Secrets (prod) | Разделение окружений |
| **Reverse Proxy** | Caddy (dev), Nginx/Gateway API (prod) | TLS, routing, rate limiting |

### Тестирование

| Компонент | Технология | Обоснование |
|---|---|---|
| **Unit-тесты** | pytest + pytest-asyncio | Async-native тестирование FastAPI |
| **Интеграционные** | Testcontainers (PostgreSQL, Redis) | Тесты с реальными зависимостями |
| **Contract-тесты** | Pact | Consumer-driven контракты для PSP/IdP интеграций |
| **E2E** | Playwright | Браузерные тесты фронтенда |
| **Мокирование** | respx (HTTP), pytest fixtures | Изоляция от внешних сервисов |

### Качество кода

| Инструмент | Назначение |
|---|---|
| **ruff** | Линтинг и форматирование Python |
| **mypy** | Статическая типизация Python |
| **ESLint + Prettier** | Линтинг и форматирование TypeScript |
| **pre-commit** | Автоматические проверки перед коммитом |
| **OpenAPI Validator** | Валидация контрактов API |

### Observability

| Компонент | Технология | Обоснование |
|---|---|---|
| **Трейсинг** | OpenTelemetry | Vendor-neutral, совместимость с Jaeger/Tempo |
| **Метрики** | Prometheus + Grafana | Стандарт де-факто для метрик |
| **Логи** | structlog | Структурированные JSON-логи с correlation ID |
| **Алерты** | Alertmanager | Дедупликация и роутинг алертов |

## Структура проекта

```
Archemap/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI application entrypoint
│   │   ├── config.py                  # Settings via pydantic-settings
│   │   ├── dependencies.py            # FastAPI dependencies
│   │   ├── modules/                   # Доменные модули
│   │   │   ├── auth/                  # Auth Broker (VK ID, OIDC adapters)
│   │   │   ├── users/                 # User model, profiles
│   │   │   ├── authorization/         # RBAC/ABAC, entitlements
│   │   │   ├── catalog/               # Products, plans, pricing
│   │   │   ├── subscriptions/         # Subscription lifecycle
│   │   │   ├── billing/               # Invoices, ledger, dunning
│   │   │   ├── payments/              # Payment orchestrator, adapters
│   │   │   ├── webhooks/              # Webhook intake, verification
│   │   │   ├── reconciliation/        # Finance reconciliation
│   │   │   ├── notifications/         # Email, SMS, push
│   │   │   └── admin/                 # Admin operations
│   │   ├── core/                      # Shared kernel
│   │   │   ├── models.py              # Base SQLAlchemy models
│   │   │   ├── security.py            # JWT, hashing, crypto
│   │   │   ├── exceptions.py          # Domain exceptions
│   │   │   ├── events.py              # Outbox/event publisher
│   │   │   └── audit.py               # Audit trail
│   │   ├── infrastructure/            # External integrations
│   │   │   ├── database.py            # Async engine, session factory
│   │   │   ├── redis.py               # Redis client
│   │   │   ├── queue.py               # Celery app
│   │   │   └── storage.py             # Object storage client
│   │   └── api/                       # API layer
│   │       ├── v1/                    # Versioned endpoints
│   │       ├── schemas/               # Pydantic request/response schemas
│   │       └── middleware.py          # CORS, rate limit, logging
│   ├── workers/                       # Celery workers
│   ├── alembic/                       # DB migrations
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── contract/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── app/                       # Next.js App Router
│   │   ├── components/                # UI components
│   │   ├── lib/                       # Utilities, API client
│   │   ├── hooks/                     # Custom React hooks
│   │   ├── stores/                    # Zustand stores
│   │   └── types/                     # Generated TypeScript types
│   ├── public/
│   ├── package.json
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── Dockerfile
├── contracts/                         # API contracts (source of truth)
│   ├── openapi.yaml                   # HTTP API specification
│   ├── asyncapi.yaml                  # Webhook/event specification
│   └── schemas/                       # Shared JSON schemas
├── infrastructure/
│   ├── docker-compose.yml             # Local dev environment
│   ├── docker-compose.prod.yml        # Production-like compose
│   ├── terraform/                     # IaC (when needed)
│   └── helm/                          # K8s manifests (when needed)
├── docs/
│   ├── deep-research-report.md        # Архитектурное исследование
│   ├── adr/                           # Architecture Decision Records
│   └── diagrams/                      # C4 diagrams (Structurizr/Mermaid)
├── scripts/
│   ├── setup.sh                       # Локальная настройка
│   ├── seed.sh                        # Начальные данные
│   └── generate-client.sh             # Генерация API-клиента
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Lint, test, validate contracts
│       └── deploy.yml                 # Build, sign, deploy
├── .env.example                       # Шаблон переменных окружения
├── .pre-commit-config.yaml
├── Makefile                           # Команды разработки
└── README.md
```

## Модули (доменные границы)

Каждый модуль в `backend/app/modules/` содержит:

```
module_name/
├── __init__.py
├── router.py          # FastAPI endpoints
├── schemas.py         # Pydantic models (request/response)
├── service.py         # Business logic (use cases)
├── repository.py      # Data access (SQLAlchemy queries)
├── models.py          # SQLAlchemy ORM models
├── exceptions.py      # Module-specific exceptions
├── dependencies.py    # FastAPI dependencies for this module
└── events.py          # Domain events (outbox pattern)
```

| Модуль | Ответственность |
|---|---|
| `auth` | VK ID OAuth 2.1 + PKCE, account linking, session/token issuance, будущие OIDC-провайдеры |
| `users` | User profiles, preferences, identity links |
| `authorization` | RBAC/ABAC, entitlement checks, BOLA protection |
| `catalog` | Products, plans, pricing, trials, coupons |
| `subscriptions` | Lifecycle: create, pause, cancel, renew, grace, proration |
| `billing` | Invoices, credit notes, payment attempts, dunning, ledger |
| `payments` | Orchestrator + provider adapters (Stripe/PayPal/ЮKassa), idempotency |
| `webhooks` | Verification, deduplication, persistence, fast ACK |
| `reconciliation` | Ledger vs PSP state comparison, mismatch cases |
| `notifications` | Email, SMS, push через провайдеров |
| `admin` | Internal operations, support, finance tools |

## Запуск локально

### Предварительные требования

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose
- Make

### Быстрый старт

```bash
# 1. Клонировать и перейти в директорию
cd D:\Python\Balthier\Archemap

# 2. Скопировать переменные окружения
cp .env.example .env

# 3. Запустить инфраструктуру (PostgreSQL, Redis)
make infra-up

# 4. Установить зависимости backend
cd backend && pip install -e ".[dev]" && cd ..

# 5. Применить миграции
make db-migrate

# 6. Запустить backend
make backend-dev

# 7. Установить зависимости frontend (в отдельном терминале)
cd frontend && npm install && npm run dev
```

### Основные команды

```bash
make infra-up          # Запустить Docker-сервисы (PostgreSQL, Redis)
make infra-down        # Остановить Docker-сервисы
make backend-dev       # Запустить backend в dev-режиме
make frontend-dev      # Запустить frontend в dev-режиме
make db-migrate        # Применить миграции Alembic
make db-revision       # Создать новую миграцию
make test              # Запустить все тесты
make test-unit         # Только unit-тесты
make test-integration  # Только интеграционные тесты
make lint              # Линтинг (ruff + eslint)
make format            # Форматирование (ruff + prettier)
make typecheck         # Статическая типизация (mypy)
make contracts-validate # Валидация OpenAPI/AsyncAPI
make generate-client   # Сгенерировать TypeScript API-клиент
```

## Конвенции

### Именование

- Модули: `snake_case` (подписки → `subscriptions`)
- Endpoint paths: `kebab-case` (`/v1/subscriptions/create`)
- Pydantic schemas: `PascalCase` (`CreateSubscriptionRequest`)
- DB tables: `snake_case`, plural (`subscriptions`, `ledger_entries`)

### API Versioning

- Все публичные эндпоинты под `/v1/`
- Breaking changes — новая версия (`/v2/`)
- Deprecation через `Sunset` header и OpenAPI `deprecated` field

### Безопасность

- PKCE обязателен для всех OAuth flows
- Idempotency-Key для всех mutating запросов
- Structured logging с correlation ID
- Secrets только через env/secrets manager, никогда в коде

### Git

- `main` — стабильная ветка, deploy в production
- `develop` — интеграционная ветка
- `feature/*` — функциональные ветки
- `fix/*` — исправления
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`

## Статус

🚧 Начальная стадия разработки

## Лицензия

Proprietary — все права защищены.
