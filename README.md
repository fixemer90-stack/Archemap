# Astrotype

Платформа астрологического анализа личности. Четыре продуктовых вертикали на едином вычислительном ядре.

| Вертикаль | Что получает пользователь | Статус |
|---|---|---|
| **Astrotype Self** | Натальная карта, архетипический портрет, персональный отчёт | ✅ |
| **Astrotype Love** | Совместимость, паттерны отношений, триггеры конфликтов | ⬜ |
| **Astrotype Child** | Профиль ребёнка, рекомендации по воспитанию, семейная интерпретация | ⬜ |
| **Astrotype Career** | Сильные стороны, подходящие роли, сценарии профессионального развития | ✅ |

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
| **Очередь задач** | Celery + Redis (broker) | Фоновые задачи: генерация PDF, reconciliation, email |
| **HTTP-клиент** | httpx | Async HTTP для интеграций с PSP/OAuth-провайдерами |
| **Валидация** | Pydantic v2 | Строгая типизация, автоматическая JSON Schema |
| **Движок карт** | Swiss Ephemeris (swisseph) + Flatlib | Высокоточные эфемериды, построение астрологических объектов |
| **Шаблоны** | Jinja2 | Рендеринг PDF-отчётов из шаблонов |
| **PDF** | WeasyPrint | HTML → PDF конвертация |
| **S3/MinIO** | boto3 | Хранилище PDF-артефактов, signed links |
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
| **Object Storage** | MinIO (локально), S3 (prod) | Хранилище PDF-артефактов |

### Качество кода

| Инструмент | Назначение |
|---|---|
| **ruff** | Линтинг и форматирование Python |
| **mypy** | Статическая типизация Python |
| **ESLint + Prettier** | Линтинг и форматирование TypeScript |
| **pre-commit** | Автоматические проверки перед коммитом |

---

## Структура проекта

```
Astrotype/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint
│   │   ├── config.py                  # Settings + production guards
│   │   ├── dependencies.py            # Auth (JWT + HttpOnly cookie)
│   │   ├── core/                      # Shared kernel
│   │   ├── infrastructure/            # Database, Redis, email
│   │   ├── modules/
│   │   │   ├── auth/                  # Auth, OAuth, password reset, account linking
│   │   │   ├── profiles/              # Birth profiles & geocoding
│   │   │   ├── charts/                # Chart snapshots & socionics
│   │   │   ├── rules/                 # Rule engine, loader, resolver
│   │   │   ├── reports/               # Report generation, PDF, S3 storage
│   │   │   └── users/                 # User management
│   │   └── chart_engine/              # Swiss Ephemeris, features, socionics
│   ├── rules/
│   │   ├── self/                      # Self vertical rules (8 archetypes)
│   │   └── career/                    # Career vertical rules (8 archetypes)
│   ├── workers/                       # Celery tasks
│   ├── alembic/                       # DB migrations
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/                # Login, register, forgot-password, reset-password
│   │   │   ├── (dashboard)/           # Dashboard, report, products
│   │   │   └── page.tsx               # Landing page
│   │   ├── components/
│   │   ├── stores/                    # Zustand (auth, UI)
│   │   └── lib/                       # API client, cookies, utilities
│   └── public/
├── docs/
│   ├── SPEC.md
│   ├── ROADMAP.md
│   ├── astrotype_design_code.md
│   ├── SRS/                           # Software Requirements Specs
│   ├── features/                      # Feature stories (E1-E10)
│   └── reviews/                       # Code reviews
├── contracts/                         # OpenAPI, AsyncAPI specs
├── docker-compose.yml                 # Postgres, Redis, MinIO, Backend, Frontend
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
git clone git@github.com:fixemer90-stack/Archemap.git
cd Archemap

# 2. Скопировать переменные окружения
cp .env.example .env

# 3. Запустить всё
docker compose up -d
# → frontend:  http://localhost:3000
# → backend:   http://localhost:8000
# → postgres:  localhost:5432
# → redis:     localhost:6379
# → minio:     http://localhost:9000 (console: :9001)
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

## API

### Auth

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Регистрация (name, email, password + birth data) |
| `POST` | `/api/v1/auth/login` | Вход (email + password) |
| `POST` | `/api/v1/auth/refresh` | Обновление токенов |
| `POST` | `/api/v1/auth/logout` | Выход (token blacklist) |
| `POST` | `/api/v1/auth/verify` | Подтверждение email |
| `POST` | `/api/v1/auth/password-reset/request` | Запрос сброса пароля |
| `POST` | `/api/v1/auth/password-reset/confirm` | Сброс пароля по токену |
| `GET` | `/api/v1/auth/linked-providers` | Список привязанных OAuth |
| `DELETE` | `/api/v1/auth/unlink/{provider}` | Отвязка OAuth-провайдера |
| `GET` | `/api/v1/auth/oauth/yandex/start` | OAuth Yandex |
| `GET` | `/api/v1/auth/oauth/yandex/callback` | OAuth callback |

### Profiles & Charts

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/profiles` | Создать профиль |
| `GET` | `/api/v1/profiles` | Список профилей |
| `GET` | `/api/v1/profiles/geocode?q=` | Геокодинг (public, rate-limited) |
| `POST` | `/api/v1/profiles/{id}/chart` | Вычислить/получить карту |

### Rules & Reports

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/rules/interpret` | Интерпретация карты |
| `GET` | `/api/v1/rules/rulesets` | Список правил |
| `POST` | `/api/v1/reports/generate` | Генерация отчёта (self/career) |
| `GET` | `/api/v1/reports` | Список отчётов (pagination) |
| `GET` | `/api/v1/reports/{id}` | Детали отчёта |
| `GET` | `/api/v1/reports/{id}/pdf` | Скачать PDF (signed link) |
| `GET` | `/api/v1/reports/{id}/versions` | История версий |

---

## Статус

| Epic | Название | Статус |
|---|---|---|
| E1 | Foundation | ✅ Готово |
| E2 | Identity (Auth, OAuth, Account Linking) | ✅ Готово |
| E3 | Chart Engine (Swiss Ephemeris, Socionics) | ✅ Готово |
| E4 | Rules & Content (Rule Engine, Evidence) | ✅ Готово |
| E5 | Products & Reports (Self, Career, PDF, S3) | ✅ Готово (S02 Love, S03 Child — backlog) |
| E6 | Billing & Subscriptions | ⬜ Не начато |
| E7 | Notifications & Admin | ⬜ Не начато |
| E8 | Production & Scale | ⬜ Не начато |

Дорожная карта: [docs/ROADMAP.md](docs/ROADMAP.md)

---

## Безопасность

- JWT в HttpOnly Secure cookies (не URL, не localStorage)
- OAuth callback выставляет cookies, не передаёт токены в URL
- Refresh token blacklist перед обновлением
- Production guard: `SECRET_KEY` не может быть `change-me`
- Rate limiting на login и geocode endpoints
- OAuth access_token не хранится в БД
- Account linking: нельзя отвязать единственный способ входа

---

## Лицензия

Proprietary — все права защищены.
