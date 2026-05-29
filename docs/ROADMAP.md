# Archemap — Roadmap

## Стратегия

Модульный монолит. Сначала домен, потом платежи. Каждый Epic завершается рабочим инкрементом.

```
Epic 1 → Epic 2 → Epic 3 → Epic 4 → Epic 5 → Epic 6 → Epic 7
Foundation   Identity   Catalog   Payments   Billing   Security   Scale
  (4 нед)    (4 нед)    (3 нед)   (5 нед)    (4 нед)   (3 нед)   (4 нед)
                                                        ─────────────
                                                         ~27 недель
```

---

## Epic 1: Foundation

**Goal:** Рабочий backend + frontend + infra, готовый к разработке фич.

| # | Feature | Описание | Файлы | Acceptance Criteria |
|---|---------|----------|-------|---------------------|
| 1.1 | Health & Config | Health endpoint, pydantic-settings, .env | config.py, health.py | `GET /api/v1/health` → `{"status":"ok","database":"ok","redis":"ok"}` |
| 1.2 | Database Setup | PostgreSQL connection, async engine, Base model, Alembic migrations | database.py, alembic/ | `alembic upgrade head` создаёт таблицы |
| 1.3 | Redis Setup | Async Redis client, connection pooling | redis.py | Redis ping из health endpoint |
| 1.4 | CI Pipeline | GitHub Actions: lint, typecheck, test, build, security audit | ci.yml | Все gates зелёные на push |
| 1.5 | OpenAPI Contract | API spec для всех endpoints v1 | openapi.yaml | `redocly lint` проходит |
| 1.6 | AsyncAPI Contract | Webhook event schemas | asyncapi.yaml | `asyncapi validate` проходит |
| 1.7 | Frontend Scaffold | Next.js 15, Tailwind, shadcn, Zustand, TanStack Query | frontend/ | `npm run build` без ошибок |
| 1.8 | Dev Environment | docker-compose, Makefile, setup script | docker-compose.yml, Makefile | `make infra-up && make backend-dev` работает |

**Status:** ✅ Done

---

## Epic 2: Identity & Auth

**Goal:** Пользователь может войти через VK ID и получить JWT.

| # | Feature | Описание | Файлы | Acceptance Criteria |
|---|---------|----------|-------|---------------------|
| 2.1 | User Model | SQLAlchemy модель User, миграция, CRUD repository | modules/users/ | Таблица `users` в БД, базовые CRUD операции |
| 2.2 | Auth Module | Auth service, JWT issuance, password hashing | modules/auth/ | `POST /api/v1/auth/register` создаёт пользователя |
| 2.3 | VK ID OAuth Flow | Authorization Code + PKCE, redirect handling | modules/auth/ | Редирект на VK → callback → JWT |
| 2.4 | Token Management | Access + refresh tokens, rotation, expiration | core/security.py | Access 30min, refresh 30d, rotation работает |
| 2.5 | Session & Middleware | Bearer auth middleware, get_current_user dependency | dependencies.py, middleware.py | Защищённые эндпоинты требуют JWT |
| 2.6 | Account Linking | Привязка нескольких IdP к одному пользователю | modules/auth/ | Один user может иметь VK + будущие IdP |
| 2.7 | Login Page (FE) | Форма входа, OAuth редирект, обработка callback | app/(auth)/ | Клик "Войти через VK" → редирект → dashboard |
| 2.8 | Auth Store (FE) | Zustand store для user/token, cookie persistence | stores/auth-store.ts | Токен сохраняется, user данные доступны |

**Dependencies:** Epic 1

---

## Epic 3: Catalog & Subscriptions

**Goal:** Пользователь видит тарифы и может оформить подписку.

| # | Feature | Описание | Файлы | Acceptance Criteria |
|---|---------|----------|-------|---------------------|
| 3.1 | Product Model | Product, Plan, Price — SQLAlchemy модели | modules/catalog/ | Таблицы `products`, `plans`, `prices` |
| 3.2 | Plan CRUD | API для управления тарифными планами | modules/catalog/ | `GET /api/v1/plans` возвращает список планов |
| 3.3 | Subscription Model | Подписка со статусами: active, paused, cancelled, expired | modules/subscriptions/ | State machine с валидными переходами |
| 3.4 | Subscription Lifecycle | Create, pause, cancel, renew, grace period | modules/subscriptions/ | `POST /api/v1/subscriptions` создаёт подписку |
| 3.5 | Trial & Grace | Пробный период, grace period при ошибке оплаты | modules/subscriptions/ | trial_days из плана, grace = 7 дней |
| 3.6 | Entitlement Engine | Проверка доступа к premium-функциям по подписке | modules/authorization/ | `has_access(user_id, feature)` → bool |
| 3.7 | Plans Page (FE) | Карточки тарифов, выбор плана | app/(dashboard)/plans | Отображение планов с ценами |
| 3.8 | Subscriptions Page (FE) | Список подписок, статусы, действия | app/(dashboard)/subscriptions | Активные/архивные подписки |

**Dependencies:** Epic 2

---

## Epic 4: Payments

**Goal:** Пользователь оплачивает подписку через PSP, webhook обрабатывается.

| # | Feature | Описание | Файлы | Acceptance Criteria |
|---|---------|----------|-------|---------------------|
| 4.1 | Payment Provider Interface | Абстрактный `PaymentProvider` протокол | modules/payments/ | Интерфейс: create_checkout, charge, refund, verify_webhook |
| 4.2 | Stripe Adapter | Реализация PaymentProvider для Stripe | modules/payments/adapters/ | Checkout session создаётся, webhook верифицируется |
| 4.3 | Checkout Flow | Создание checkout session, редирект на PSP | modules/payments/ | `POST /api/v1/payments/checkout` → URL для оплаты |
| 4.4 | Webhook Ingress | Верификация подписей, dedup, fast ACK, queue | modules/webhooks/ | Webhook сохраняется, ACK < 500ms, дубликат игнорируется |
| 4.5 | Idempotency | Idempotency-Key для всех mutating запросов | core/ | Повторный запрос с тем же ключом → тот же ответ |
| 4.6 | Payment State Machine | Статусы платежа: pending, succeeded, failed, refunded | modules/payments/ | Переходы валидируются, audit trail |
| 4.7 | Checkout Page (FE) | Страница оплаты, редирект, success/cancel | app/(dashboard)/checkout | Пользователь попадает на Stripe → возвращается |
| 4.8 | Payment Methods (FE) | Сохранённые способы оплаты | app/(dashboard)/billing | Список карт, привязка новой |

**Dependencies:** Epic 3

---

## Epic 5: Billing & Reconciliation

**Goal:** Полный цикл биллинга: инвойсы, автосписание, сверка с PSP.

| # | Feature | Описание | Файлы | Acceptance Criteria |
|---|---------|----------|-------|---------------------|
| 5.1 | Invoice Model | Инвойс со статусами, line items, суммы | modules/billing/ | Таблица `invoices`, связь с подпиской |
| 5.2 | Auto-Renewal | Celery task: проверка expiring подписок, списание | workers/tasks/renewals.py | Подписка продлевается за 3 дня до expiry |
| 5.3 | Dunning | Retry policy при неудачном списании | modules/billing/ | 3 попытки: сразу, +3 дня, +7 дней |
| 5.4 | Refund Flow | Возврат средств через PSP adapter | modules/payments/ | `POST /api/v1/payments/refund` → refund в PSP |
| 5.5 | Ledger | Двойная запись: credit/debit для всех операций | modules/billing/ | Баланс всегда = сумме credit - debit |
| 5.6 | Reconciliation | Сверка internal ledger vs PSP state | workers/tasks/reconciliation.py | Мismatch → alert, case management |
| 5.7 | Finance Export | Экспорт инвойсов в CSV/JSON для бухгалтерии | modules/billing/ | `GET /api/v1/billing/export?format=csv` |
| 5.8 | Billing Page (FE) | История платежей, инвойсы, скачивание | app/(dashboard)/billing | Список транзакций, ссылки на инвойсы |

**Dependencies:** Epic 4

---

## Epic 6: Notifications & Admin

**Goal:** Пользователи получают уведомления, админы управляют системой.

| # | Feature | Описание | Файлы | Acceptance Criteria |
|---|---------|----------|-------|---------------------|
| 6.1 | Email Provider | Интеграция с SMTP/SendGrid | modules/notifications/ | Email отправляется, delivery status tracking |
| 6.2 | Notification Templates | Шаблоны: renewal_reminder, payment_failed, welcome | modules/notifications/ | Jinja2/микро-шаблоны с переменными |
| 6.3 | Notification Preferences | Пользователь настраивает каналы и частоту | modules/notifications/ | `PATCH /api/v1/notifications/preferences` |
| 6.4 | Renewal Reminders | Уведомление за 7 дней и за 1 день до списания | workers/tasks/notifications.py | Email отправляется по расписанию |
| 6.5 | Admin Dashboard | Управление пользователями, подписками, планами | modules/admin/ | CRUD для admin role |
| 6.6 | Admin Analytics | MRR, churn, active subscriptions, revenue | modules/admin/ | `GET /api/v1/admin/analytics` → метрики |
| 6.7 | Audit Trail | Логирование всех admin/payment действий | core/audit.py | Таблица `audit_log`, immutable append-only |
| 6.8 | Settings Page (FE) | Профиль, уведомления, привязанные аккаунты | app/(dashboard)/settings | Редактирование профиля |

**Dependencies:** Epic 5

---

## Epic 7: Security & Scale

**Goal:** Production-ready: безопасность, observability, масштабирование.

| # | Feature | Описание | Файлы | Acceptance Criteria |
|---|---------|----------|-------|---------------------|
| 7.1 | Rate Limiting | Лимиты на gateway и app level | middleware.py, redis.py | 429 при превышении лимита |
| 7.2 | WAF Rules | OWASP CRS rule set перед edge | infrastructure/ | Блокировка SQL injection, XSS |
| 7.3 | Secrets Manager | Внешний Vault вместо .env в prod | infrastructure/ | Ротация ключей без downtime |
| 7.4 | Structured Logging | JSON-логи с correlation ID | core/audit.py, middleware.py | Каждый запрос имеет trace_id |
| 7.5 | Metrics & Traces | OpenTelemetry traces, Prometheus metrics | infrastructure/ | Jaeger/Tempo dashboard |
| 7.6 | Alerting | Alertmanager rules для error rate, latency | infrastructure/ | Alert при p99 > 1s или error rate > 1% |
| 7.7 | Load Testing | k6/locust сценарии для critical paths | tests/load/ | 1000 RPS на health, 100 RPS на subscriptions |
| 7.8 | Incident Playbook | Runbook для типовых инцидентов | docs/runbook.md | Payment failure, DB down, Redis down |

**Dependencies:** Epic 5

---

## Epic 8: Regional Expansion (future)

**Goal:** Multi-provider, multi-region, mobile-ready.

| # | Feature | Описание | Acceptance Criteria |
|---|---------|----------|---------------------|
| 8.1 | Second PSP | PayPal или ЮKassa adapter | Checkout через нового провайдера работает |
| 8.2 | Second IdP | Google OIDC / Apple Sign In | Вход через Google → тот же аккаунт |
| 8.3 | Mobile BFF | API adjustments для mobile clients | Mobile app может использовать все API |
| 8.4 | Multi-Currency | Валюты, локализация цен | Планы отображаются в валюте пользователя |
| 8.5 | Feature Flags | OpenFeature + flag provider | Поэтапный rollout новых функций |

**Dependencies:** Epic 7

---

## Приоритеты

```
MVP (Epic 1-3):   ~11 недель  — пользователь может зарегистрироваться,
                                 выбрать план и оформить подписку

Revenue (Epic 4-5): ~9 недель  — платёжный цикл работает end-to-end

Production (Epic 6-7): ~7 недель — система готова к продакшену

Growth (Epic 8):   ~4 недели  — масштабирование на новые рынки
```

## Текущий статус

```
Epic 1: Foundation      ✅ Done
Epic 2: Identity        ⬜ Not started
Epic 3: Catalog         ⬜ Not started
Epic 4: Payments        ⬜ Not started
Epic 5: Billing         ⬜ Not started
Epic 6: Notifications   ⬜ Not started
Epic 7: Security        ⬜ Not started
Epic 8: Expansion       ⬜ Future
```
