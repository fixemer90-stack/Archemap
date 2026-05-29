# Archemap

Платформа астрологического анализа личности. Четыре продуктовых вертикали на едином вычислительном ядре.

| Вертикаль | Что получает пользователь |
|---|---|
| **Archemap Self** | Натальная карта, архетипический портрет, персональный отчёт |
| **Archemap Love** | Совместимость, паттерны отношений, триггеры конфликтов |
| **Archemap Child** | Профиль ребёнка, рекомендации по воспитанию, семейная интерпретация |
| **Archemap Career** | Сильные стороны, подходящие роли, сценарии профессионального развития |

**Принцип:** вся интерпретация — rule-based на движке правил + шаблоны контента. Детерминированный расчёт и explainable scoring — первичны, narrative layer — вторичен. AI не используется для генерации отчётов в рантайме.

**Документация:** [SPEC.md](docs/SPEC.md) · [ROADMAP.md](docs/ROADMAP.md) · [Design Code](docs/archemap_design_code.md) · [C4 Architecture](docs/C4%20архитектура%20SaaS-платформы%20Archemap.md) · [Business Logic Spec](docs/Спецификация%20бизнес-логики%20и%20доменных%20правил%20Archemap.md)

---

## Архитектура

Модульный монолит с чёткими доменными границами. Contract-first подход через OpenAPI/AsyncAPI.

Вычислительный конвейер:

```
input envelope → chart snapshot → normalized features → axes → archetypes/claims → confidence → report assembly → entitlement-aware rendering
```

Домены разделены на bounded contexts: Auth, Profiles, Chart Engine, Content/Rules, Reports, Billing, Payments, Notifications, Admin.

---

## Стек технологий

### Backend

| Компонент | Технология | Обоснование |
|---|---|---|
| **Фреймворк** | FastAPI (Python 3.12+) | Async-native, автоматическая OpenAPI-генерация, Pydantic-валидация |
| **ORM** | SQLAlchemy 2.0 + Alembic | Зрелый async ORM, миграции схемы, repository pattern |
| **База данных** | PostgreSQL 16 | ACID для ledger/подписок, JSONB, расширения (pgcrypto, uuid-ossp) |
| **Кэш / Rate Limiting** | Redis 7 | Сессии, rate limiting, short-lived cache, pub/sub |
| **Очередь задач** | Celery + Redis (broker) | Фоновые задачи: генерация отчётов, reconciliation, email |
| **HTTP-клиент** | httpx | Async HTTP для интеграций с PSP/OAuth-провайдерами |
| **Валидация** | Pydantic v2 | Строгая типизация, автоматическая JSON Schema |
| **Движок карт** | Swiss Ephemeris (swisseph) + Flatlib | Высокоточные эфемериды, построение астрологических объектов |
| **Шаблоны** | Jinja2 | Рендеринг отчётов из шаблонов |
| **Email** | SMTP/SMTPS (smtplib) | Transactional email: верификация, уведомления |

### Frontend

| Компонент | Технология | Обоснование |
|---|---|---|
| **Фреймворк** | Next.js 15 (React 19) | SSR/SSG, App Router, Server Components, middleware для auth |
| **UI-библиотека** | shadcn/ui + Tailwind CSS 4 | Кастомизируемые компоненты, дизайн-система, tree-shaking |
| **State management** | Zustand + TanStack Query | Лёгкий, типизированный, без boilerplate |
| **Формы** | React Hook Form + Zod | Валидация на клиенте, типобезопасность |

### Инфраструктура

| Компонент | Технология | Обоснование |
|---|---|---|
| **Контейнеризация** | Docker + Docker Compose | Локальная разработка, воспроизводимые окружения |
| **CI/CD** | GitHub Actions | Lint, тесты, contract validation, build, deploy |
| **Миграции БД** | Alembic | Версионированная миграция схемы, downgrade support |
| **Reverse Proxy** | Caddy (dev), Nginx/Gateway API (prod) | TLS, routing, rate limiting |

### Качество кода

| Инструмент | Назначение |
|---|---|
| **ruff** | Линтинг и форматирование Python |
| **mypy** | Статическая типизация Python |
| **ESLint + Prettier** | Линтинг и форматирование TypeScript |
| **pre-commit** | Автоматические проверки перед коммитом |

### Observability

| Компонент | Технология | Обоснование |
|---|---|---|
| **Трейсинг** | OpenTelemetry | Vendor-neutral, совместимость с Jaeger/Tempo |
| **Метрики** | Prometheus + Grafana | Стандарт де-факто для метрик |
| **Логи** | structlog | Структурированные JSON-логи с correlation ID |

---

## Структура проекта

```
Archemap/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint
│   │   ├── config.py                  # Settings via pydantic-settings
│   │   ├── dependencies.py            # FastAPI dependencies
│   │   ├── core/                      # Shared kernel
│   │   │   ├── models.py              # Base SQLAlchemy models
│   │   │   ├── security.py            # JWT, hashing, crypto
│   │   │   ├── exceptions.py          # Domain exceptions
│   │   │   ├── rate_limit.py          # Redis-backed rate limiter
│   │   │   └── token_blacklist.py     # JWT blacklist (logout)
│   │   ├── infrastructure/            # External integrations
│   │   │   ├── database.py            # Async engine, session factory
│   │   │   ├── redis.py               # Redis client
│   │   │   ├── email.py               # SMTP/SMTPS sender
│   │   │   └── email_templates.py     # Email HTML/text templates
│   │   ├── modules/                   # Доменные модули
│   │   │   ├── auth/                  # Authentication & OAuth
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   ├── schemas.py
│   │   │   │   ├── models.py          # User, EmailVerification, IdentityLink
│   │   │   │   ├── verification.py    # Email verification service
│   │   │   │   ├── password_reset.py  # Password reset flow
│   │   │   │   └── oauth/             # OAuth providers
│   │   │   │       ├── yandex.py      # Yandex ID provider
│   │   │   │       └── service.py     # OAuth service (state, linking)
│   │   │   └── users/                 # User management
│   │   │       ├── router.py
│   │   │       └── models.py
│   │   └── api/v1/                    # Versioned router aggregation
│   ├── alembic/                       # DB migrations
│   ├── tests/
│   │   ├── unit/                      # Fast, isolated tests
│   │   ├── integration/               # DB/Redis dependent
│   │   ├── golden/                    # Golden tests for chart interpretation
│   │   └── chart/                     # Chart engine tests
│   ├── pyproject.toml
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── app/                       # Next.js App Router
│   │   │   ├── (marketing)/           # Landing pages per vertical
│   │   │   ├── (auth)/                # Login, register, verify
│   │   │   ├── (dashboard)/           # User dashboard
│   │   │   │   ├── self/              # Archemap Self flow
│   │   │   │   ├── love/              # Archemap Love flow
│   │   │   │   ├── child/             # Archemap Child flow
│   │   │   │   └── career/            # Archemap Career flow
│   │   │   └── admin/                 # Admin panel
│   │   ├── components/
│   │   │   ├── ui/                    # shadcn-style components
│   │   │   ├── chart/                 # Natal chart visualization (SVG)
│   │   │   └── reports/               # Report preview components
│   │   ├── stores/                    # Zustand stores
│   │   ├── hooks/                     # Custom hooks
│   │   └── lib/                       # Utilities, API client
│   └── public/
├── docs/                              # Проектная документация
│   ├── SPEC.md                        # Полная спецификация продукта
│   ├── ROADMAP.md                     # Дорожная карта эпиков
│   ├── archemap_design_code.md        # Дизайн-система и бренд
│   ├── C4 архитектура ...md           # C4-архитектура платформы
│   └── Спецификация бизнес-логики ...md # Доменные правила и скоринг
├── .github/workflows/
│   └── ci.yml                         # Lint, test, validate, build
├── Makefile                           # Команды разработки
└── README.md
```

---

## Запуск локально

### Предварительные требования

- Python 3.12+
- Node.js 20+
- Docker + Docker Compose

### Быстрый старт

```bash
# 1. Клонировать
git clone git@github.com:fixemer90-stack/Archemap.git
cd Archemap

# 2. Скопировать переменные окружения
cp .env.example .env

# 3. Запустить инфраструктуру (PostgreSQL, Redis)
make infra-up

# 4. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload   # → :8000

# 5. Frontend (в отдельном терминале)
cd frontend
npm install && npm run dev      # → :3000
```

### Основные команды

```bash
make infra-up          # Запустить Docker-сервисы (PostgreSQL, Redis)
make infra-down        # Остановить Docker-сервисы

# Backend
cd backend && source .venv/bin/activate
ruff check .           # Линтинг
ruff format .          # Форматирование
mypy .                 # Статическая типизация
pytest tests/unit -v   # Unit-тесты
pytest tests/golden -v # Golden tests для интерпретаций

# Frontend
cd frontend
npm run dev            # Dev server
npm run build          # Production build
npx eslint .           # Линтинг
npx tsc --noEmit       # Type check
```

---

## Дизайн-система

Archemap — не «астро-гадалка», а **премиальная навигационная система для самопознания**.

| Роль | Название | HEX |
|---|---|---:|
| Основной фон | Deep Space | `#17142A` |
| Главный акцент | Royal Violet | `#5B3FD6` |
| Премиальный акцент | Soft Gold | `#D8B45A` |
| Вторичный текст | Moon Silver | `#D8DCE8` |
| Интерактивный | Mist Blue | `#8DA8FF` |
| Основной текст | Warm Ivory | `#F6F1E8` |

Акценты по вертикалям: Self (фиолетовый + золото), Love (розово-бордовый `#B84A6B`), Child (мягкий голубой `#6BAFBD`), Career (янтарный `#C28A2E`).

Полный дизайн-код: [docs/archemap_design_code.md](docs/archemap_design_code.md)

---

## Статус

🟡 Epic 2 (Identity) — в процессе. Дорожная карта: [docs/ROADMAP.md](docs/ROADMAP.md)

## Лицензия

Proprietary — все права защищены.
