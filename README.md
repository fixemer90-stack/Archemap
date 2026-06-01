# Astrotype

Платформа астрологического анализа личности. Четыре продуктовых вертикали на едином вычислительном ядре.

| Вертикаль | Что получает пользователь |
|---|---|
| **Astrotype Self** | Натальная карта, архетипический портрет, персональный отчёт |
| **Astrotype Love** | Совместимость, паттерны отношений, триггеры конфликтов |
| **Astrotype Child** | Профиль ребёнка, рекомендации по воспитанию, семейная интерпретация |
| **Astrotype Career** | Сильные стороны, подходящие роли, сценарии профессионального развития |

**Принцип:** вся интерпретация — rule-based на движке правил + шаблоны контента. Детерминированный расчёт и explainable scoring — первичны, narrative layer — вторичен. AI не используется для генерации отчётов в рантайме.

**Документация:** [SPEC.md](docs/SPEC.md) · [ROADMAP.md](docs/ROADMAP.md) · [Design Code](docs/astrotype_design_code.md) · [C4 Architecture](docs/C4%20архитектура%20SaaS-платформы%20Astrotype.md) · [Business Logic Spec](docs/Спецификация%20бизнес-логики%20и%20доменных%20правил%20Astrotype.md)

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
Astrotype/
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
│   │   │   ├── profiles/              # Birth profiles & geocoding
│   │   │   │   ├── router.py
│   │   │   │   ├── service.py
│   │   │   │   └── models.py
│   │   │   ├── chart_engine/          # Natal chart computation
│   │   │   │   ├── ephemeris.py       # Swiss Ephemeris wrapper
│   │   │   │   ├── houses.py          # House system calculation
│   │   │   │   ├── aspects.py         # Aspect computation
│   │   │   │   └── socionics.py       # Socionics type calculation
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
│   │   │   │   ├── self/              # Astrotype Self flow
│   │   │   │   ├── love/              # Astrotype Love flow
│   │   │   │   ├── child/             # Astrotype Child flow
│   │   │   │   └── career/            # Astrotype Career flow
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
│   ├── astrotype_design_code.md        # Дизайн-система и бренд
│   ├── C4 архитектура ...md           # C4-архитектура платформы
│   ├── Спецификация бизнес-логики ...md # Доменные правила и скоринг
│   ├── SRS/
│   │   ├── SRS-FRONTEND.md            # SRS frontend (дизайн-система, компоненты)
│   │   ├── SRS-E3-chart-engine.md     # SRS движок карт
│   │   └── SRS-E4-rules-content.md    # SRS правила и контент
│   └── features/                      # Спецификации фич
├── .github/workflows/
│   └── ci.yml                         # Lint, test, validate, build
├── Makefile                           # Команды разработки
└── README.md
```

---

## Запуск локально

### Предварительные требования

- Docker + Docker Compose (WSL или Linux)
- Python 3.12+ (для разработки backend без контейнера)
- Node.js 20+ (для разработки frontend без контейнера)

### Быстрый старт (Docker)

```bash
# 1. Клонировать
git clone git@github.com:fixemer90-stack/Astrotype.git
cd Astrotype

# 2. Скопировать переменные окружения
cp .env.example .env

# 3. Запустить всё
docker compose up -d
# → frontend:  http://localhost:3000
# → backend:   http://localhost:8000
# → postgres:  localhost:5432
# → redis:     localhost:6379
```

### Без Docker (разработка)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload   # → :8000

# Frontend (в отдельном терминале)
cd frontend
npm install && npm run dev      # → :3000
```

### Основные команды

```bash
# Docker
docker compose up -d            # Запустить все сервисы
docker compose down             # Остановить
docker compose up -d --build    # Пересобрать после изменений
docker compose logs -f backend  # Логи backend

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
npx prettier --check . # Форматирование
npx tsc --noEmit       # Type check
```

---

## Дизайн-система

Astrotype — не «астро-гадалка», а **премиальная навигационная система для самопознания**.

| Роль | Название | HEX |
|---|---|---:|
| Основной фон | Deep Space | `#17142A` |
| Главный акцент | Royal Violet | `#5B3FD6` |
| Премиальный акцент | Soft Gold | `#D8B45A` |
| Вторичный текст | Moon Silver | `#D8DCE8` |
| Интерактивный | Mist Blue | `#8DA8FF` |
| Основной текст | Warm Ivory | `#F6F1E8` |

Акценты по вертикалям: Self (фиолетовый + золото), Love (розово-бордовый `#B84A6B`), Child (мягкий голубой `#6BAFBD`), Career (янтарный `#C28A2E`).

**Реализация:** дизайн-код внедрён во все UI-компоненты. Cormorant Garamond для заголовков, Inter для интерфейса. Glass-карточки (`backdrop-blur`, `rgba(255,255,255,0.06)`). Primary button — pill shape с violet→gold градиентом. Radial gradient фон. Evidence blocks для explainability.

Полный дизайн-код: [docs/astrotype_design_code.md](docs/astrotype_design_code.md)
Документация реализации: [docs/SRS/SRS-FRONTEND.md](docs/SRS/SRS-FRONTEND.md) (секция 8)

---

## Статус

🟢 Epic 1 (Foundation) — done. Epic 2 (Identity) — done.
🟡 Epic 3 (Chart Engine) — в процессе. Дорожная карта: [docs/ROADMAP.md](docs/ROADMAP.md)

## Лицензия

Proprietary — все права защищены.
