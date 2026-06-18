# Astrotype — Дорожная карта

> **Продукт:** Платформа астрологических личностных профилей (4 вертикали: Self, Love, Child, Career)
> **Обновлено:** 2026-06-15

---

## Обзор вертикалей

| Вертикаль | Описание | Ключевые сущности |
|-----------|----------|-------------------|
| **Self** | Натальная карта, портрет архетипа, персональный отчёт | PersonProfile, ChartSnapshot, SelfReport |
| **Love** | Совместимость, паттерны отношений, триггеры конфликтов | PairProfile, CompatibilityReport |
| **Child** | Профиль ребёнка, рекомендации по воспитанию | ChildProfile, ParentingReport |
| **Career** | Сильные стороны, роли, профессиональное развитие | CareerProfile, CareerReport |

**Общая основа:** Chart & Archetype Engine (Swiss Ephemeris + Flatlib), движок правил, шаблонный контент.

---

## Статус эпиков

| Эпик | Название | Статус |
|------|----------|--------|
| E1 | Foundation | ✅ Готово |
| E2 | Identity | 🟡 В процессе |
| E3 | Profile & Chart Engine | ✅ Готово |
| E4 | Rules & Content | ✅ Готово (S06 CMS — backlog) |
| E5 | Products & Reports | 🟡 В процессе |
| E6 | Billing & Subscriptions | ⬜ Не начато |
| E7 | Notifications & Admin | ⬜ Не начато |
| E8 | Production & Scale | 🟡 В процессе |
| E9 | Frontend Self Report | ✅ Готово |
| E10 | Report UX Redesign | ✅ Готово |
| E11 | LLM Report Narrative | ✅ Готово |
| E12 | LLM Report Runtime Readiness | ✅ Готово (PDF delivery без обязательного object storage) |
| E13 | Report Depth Improvements | ⬜ Не начато |

---

## Epic 1: Foundation ✅

**Статус:** Готово

- Скелет проекта, CI/CD, инфраструктура, Docker.

---

## Epic 2: Identity 🟡

**Статус:** В процессе
**Оценка:** 1.5–2 недели (на завершение оставшегося)
**Зависимости:** E1 ✅

| # | Фича | Описание | Файлы/модули | Критерии приёмки |
|---|------|----------|---------------|------------------|
| 2.1 | Email + пароль | Регистрация, вход, верификация email, logout | `auth/`, `accounts/models.py`, `accounts/views.py` | ✅ Готово |
| 2.2 | VK ID OAuth | Авторизация через VK ID (OpenID Connect) | `auth/oauth/vk.py`, `auth/pipeline.py`, settings | Пользователь может войти через VK; email привязывается при наличии |
| 2.3 | Yandex ID OAuth | Авторизация через Yandex ID | `auth/oauth/yandex.py`, `auth/pipeline.py`, settings | Пользователь может войти через Yandex; аккаунт линкуется по email |
| 2.4 | Привязка аккаунтов | Linking OAuth-провайдеров к существующему аккаунту | `auth/linking.py`, `accounts/models.py` | Пользователь может привязать VK/Yandex к email-аккаунту из настроек |
| 2.5 | Сброс пароля | Запрос сброса по email, токен, новый пароль | `auth/password_reset.py`, `accounts/views.py` | Письмо отправляется; токен истекает через 24ч; пароль меняется |
| 2.6 | Rate-limiting входа | Защита от брутфорса (5 попыток / 15 мин) | `auth/throttling.py`, middleware | При превышении — HTTP 429; счётчик сбрасывается через 15 мин |

---

## Epic 3: Profile & Chart Engine ✅

**Статус:** Готово
**Зависимости:** E2

| # | Фича | Описание | Статус |
|---|------|----------|--------|
| 3.1 | PersonProfile | Модель профиля: дата, время, место рождения | ✅ |
| 3.2 | Геокодинг (Open-Meteo) | Получение координат по названию места | ✅ |
| 3.3 | Определение часового пояса | Разрешение IANA TZ по координатам | ✅ |
| 3.4 | Swiss Ephemeris + Flatlib | Вычисление позиций планет, домов, аспектов | ✅ |
| 3.5 | ChartSnapshot | Сохранённый снимок натальной карты (JSON) | ✅ |
| 3.6 | Нормализация признаков | Извлечение FeatureVector из карты | ✅ |
| 3.7 | Socionics Model A | Вычисление соционического типа (16 типов, 8 функций) | ✅ |

---

## Epic 4: Rules & Content 🟡

**Статус:** В процессе
**Зависимости:** E3 ✅

| # | Фича | Описание | Статус |
|---|------|----------|--------|
| 4.1 | RuleSetVersion | YAML-правила для Self вертикали (8 архетипов) | ✅ |
| 4.2 | TemplateVersion | Evidence templates для рендеринга текста | ✅ |
| 4.3 | Движок правил | Оценка условий → score → claim с confidence | ✅ |
| 4.4 | Content Resolver | Claim'ы → текст отчёта с evidence trail | ✅ |
| 4.5 | API endpoint | POST /api/v1/rules/interpret | ✅ |
| 4.6 | Unit tests | 20 тестов rule engine + loader | ✅ |
| 4.7 | Локализация RU/EN | Поддержка EN для правил и шаблонов | ⬜ |
| 4.8 | CMS для редакторов | UI для редактирования правил | ⬜ |

---

## Epic 5: Products & Reports 🟡

**Статус:** 🟡 В процессе
**Оценка:** 4–5 недель
**Зависимости:** E3, E4

Текущее состояние PDF path:

- отчёт доступен для скачивания сразу из сохранённых данных профиля и narrative-слоя;
- отдельное файловое хранилище для PDF больше не является обязательной частью runtime;
- старые поля `pdf_url` / `pdf_generated` пока сохраняются для совместимости и будут убраны отдельной миграцией.

| # | Фича | Описание | Файлы/модули | Критерии приёмки |
|---|------|----------|---------------|------------------|
| 5.1 | Self-отчёт | Генерация персонального отчёта по натальной карте | `reports/self/`, `reports/generator.py` | ✅ Готово |
| 5.2 | Love: совместимость | Анализ пары: синастрия, паттерны, триггеры | `reports/love/`, `reports/synastry.py` | Два профиля → отчёт; оценка совместимости 0–100; топ-3 триггера |
| 5.3 | Child: профиль | Профиль ребёнка + рекомендации родителю | `reports/child/`, `reports/child_profile.py` | По дате/времени/месту → темперамент, сильные стороны, советы по воспитанию |
| 5.4 | Career: сильные стороны | Карьерные рекомендации по карте | `reports/career/`, `reports/career_profile.py` | ✅ Готово |
| 5.5 | Версионирование отчётов | Хранение версий сгенерированных отчётов | `reports/models.py` | ✅ Готово |
| 5.6 | Хранилище отчётов | Отчёт собирается из сохранённых данных приложения; отдельное object storage для PDF не требуется | `reports/storage.py`, `reports/pdf.py`, `reports/router.py` | ✅ Готово |
| 5.7 | API отчётов | REST-эндпоинты для генерации и получения отчётов | `reports/views.py`, `reports/serializers.py` | ✅ Готово |

---

## Epic 6: Billing & Subscriptions

**Статус:** ⬜ Не начато
**Оценка:** 4–5 недель
**Зависимости:** E5

| # | Фича | Описание | Файлы/модули | Критерии приёмки |
|---|------|----------|---------------|------------------|
| 6.1 | Каталог планов | Планы подписок (по вертикалям: Self, Love, Child, Career, Bundle) | `billing/models.py`, `billing/catalog.py` | CRUD планов; цена, интервал, trial; привязка к вертикалям |
| 6.2 | Жизненный цикл подписки | Создание, активация, продление, отмена, grace period | `billing/subscription.py`, `billing/lifecycle.py` | Статусы: trial→active→past_due→cancelled→expired; webhook-driven |
| 6.3 | YooKassa | Провайдер оплаты: создание платежа, подтверждение | `billing/adapters/yookassa.py` | Платёж создаётся → редирект → callback → подписка активна |
| 6.4 | CloudPayments | Провайдер оплаты: виджет, рекуррентные платежи | `billing/adapters/cloudpayments.py` | Первый платёж + рекуррент; обработка отказа; retry |
| 6.5 | Stripe | Международный провайдер: Checkout, Billing Portal | `billing/adapters/stripe.py` | Checkout session → success → webhook → subscription active |
| 6.6 | Webhook handling | Обработка входящих webhook'ов от платёжных систем | `billing/webhooks.py` | Идемпотентность; верификация подписи; логирование; retry |
| 6.7 | Entitlement engine | Проверка доступа к вертикалям по подписке | `billing/entitlements.py`, middleware | `has_access(user, "love")` → bool; free-план = только Self preview |
| 6.8 | In-app billing (мобильные) | Мост для Google Play Billing и App Store | `billing/adapters/mobile.py`, API | Мобильный клиент отправляет receipt → сервер верифицирует → entitlement |

---

## Epic 7: Notifications & Admin

**Статус:** ⬜ Не начато
**Оценка:** 3–4 недели
**Зависимости:** E5, E6

| # | Фича | Описание | Файлы/модули | Критерии приёмки |
|---|------|----------|---------------|------------------|
| 7.1 | Email-уведомления | Отправка email (transactional): отчёт готов, подписка | `notifications/email.py`, templates | Email отправляется через SMTP/SendPulse; шаблоны на RU/EN |
| 7.2 | SMS-уведомления | Отправка SMS (подтверждение, важные события) | `notifications/sms.py`, provider adapter | SMS через SMS.ru / Infobip; rate-limit 3/день/user |
| 7.3 | Push-уведомления | Web и мобильные push (FCM/APNs) | `notifications/push.py`, `notifications/fcm.py` | Push при готовности отчёта, напоминание о продлении |
| 7.4 | Напоминания о продлении | Автоматические напоминания за 7/3/1 день | `notifications/reminders.py`, cron | Письмо+push за 7, 3, 1 день до окончания подписки |
| 7.5 | Admin Dashboard | Админ-панель: пользователи, подписки, отчёты | `admin/dashboard.py`, frontend | Поиск пользователя; просмотр подписок; ручная активация/отмена |
| 7.6 | Content Editor | Редактор правил и шаблонов через UI | `admin/content_editor.py`, frontend | WYSIWYG для шаблонов; JSON editor для правил; preview |
| 7.7 | Analytics (PostHog) | Трекинг событий: регистрация, оплата, отчёт | `analytics/posthog.py`, middleware | События: signup, login, report_generated, payment_success; dashboard |
| 7.8 | Audit trail | Лог действий: кто, что, когда | `audit/models.py`, `audit/middleware.py` | Каждое изменение подписки/профиля логируется; доступно в admin |

---

## Epic 8: Production & Scale 🟡

**Статус:** 🟡 В процессе
**Оценка:** 3–4 недели
**Зависимости:** E6, E7

| # | Фича | Описание | Файлы/модули | Критерии приёмки |
|---|------|----------|---------------|------------------|
| 8.1 | Rate limiting | Ограничение запросов по API | `middleware/rate_limit.py`, Redis | 🟡 Частично: login/geocode limits готовы; глобальный лимит ещё нет |
| 8.2 | WAF | Web Application Firewall (ModSecurity / Cloudflare) | infra/, nginx config | Блокировка SQLi, XSS, path traversal; логирование |
| 8.3 | Secrets manager | Хранение секретов (Yandex Lockbox / Vault) | `config/secrets.py`, deploy scripts | ✅ Базовые production guards и validation готовы; полноценный secrets manager ещё нет |
| 8.4 | Observability | Трассировка, метрики, логи | `observability/`, OTEL config, Prometheus, Loki | 🟡 Частично: OTEL + structlog есть; полный metrics/logs stack ещё нет |
| 8.5 | Load testing | Нагрузочное тестирование | `tests/load/`, k6/locust scripts | 500 concurrent users; p95 < 500ms для report generation |
| 8.6 | Yandex Managed K8s | Деплой на Yandex Managed Kubernetes | `deploy/k8s/`, Helm charts | Pod autoscaling; health checks; rolling updates; zero-downtime deploy |
| 8.7 | GitOps (Argo CD) | Автоматический деплой из Git | `deploy/argocd/`, `deploy/apps/` | Push в main → Argo CD sync → deploy; rollback через revert commit |
| 8.8 | Render deploy MVP | Blueprint для frontend/backend/worker + managed Postgres + managed Redis/Valkey | `render.yaml`, deploy docs | ⬜ Не начато: deploy contract и storage-decision docs синхронизированы; реальный render blueprint/runtime rollout ещё не доведён |
| 8.9 | PDF storage strategy | Решение по PDF delivery для managed deploy | `reports/storage.py`, `reports/pdf.py`, deploy docs | ✅ Готово: отдельное object storage не является обязательным для MVP; env/infra contract очищен от обязательных `S3_*` |

---

## Epic 11: LLM Report Narrative

**Статус:** ✅ Готово
**Оценка:** 2–3 недели
**Зависимости:** E3, E4, E5, E10

| # | Фича | Описание | Документы | Критерии приёмки |
|---|------|----------|-----------|------------------|
| 11.1 | Narrative contracts | `NarrativeInput` и `SelfNarrative` schemas | `docs/features/E11-llm-report-narrative/S01-narrative-contracts.md` | JSON schema валидируется, Markdown output запрещён |
| 11.2 | Storage/versioning | `report_narratives` отдельно от deterministic report | `docs/features/E11-llm-report-narrative/S02-report-narratives-storage.md` | Хранятся prompt_version, model, input_hash, status |
| 11.3 | LLM infrastructure | Provider abstraction, mock provider, settings | `docs/features/E11-llm-report-narrative/S03-llm-provider-abstraction.md` | Tests не ходят в сеть, mock работает без API key |
| 11.4 | Prompt + validation | `self_story_v1`, evidence discipline, validators | `docs/features/E11-llm-report-narrative/S04-prompt-contract-self-story-v1.md` | Нет hallucinated facts, career deep dive и unsafe language |
| 11.5 | Async/API/UI/PDF | Celery task, statuses, regenerate, frontend fallback, PDF from JSON | `docs/features/E11-llm-report-narrative/FEATURE.md` | Нет endless spinner, deterministic fallback доступен |

Полный контракт: `docs/SRS/SRS-E11-llm-report-narrative.md`.

---

## Epic 12: LLM Report Runtime Readiness ✅

**Статус:** ✅ Готово
**Оценка:** 1–2 недели
**Зависимости:** E11 ✅, E5 🟡, E1 ✅

| # | Фича | Описание | Документы | Критерии приёмки |
|---|------|----------|-----------|------------------|
| 12.1 | Runtime inventory | Что реально нужно для запуска E11, а не только для code-complete состояния | `docs/features/E12-llm-report-runtime-readiness/S01-runtime-inventory-gap-analysis.md` | ✅ Готово |
| 12.2 | Worker/dev orchestration | Отдельный Celery worker и narrative-ready local stack | `docs/features/E12-llm-report-runtime-readiness/S02-dev-orchestration-worker-runtime.md` | ✅ Готово |
| 12.3 | LLM env contract | Disabled/mock/real provider modes и required env | `docs/features/E12-llm-report-runtime-readiness/S03-llm-environment-contract.md` | ✅ Готово |
| 12.4 | PDF delivery/runtime path | Полный deliverable path: сохранённый отчёт -> PDF без скрытых ручных шагов и без обязательного object storage | `docs/features/E12-llm-report-runtime-readiness/S04-object-storage-pdf-bootstrap.md` | ✅ Готово |
| 12.5 | Runbook + smoke | Пошаговый запуск, логи, generate/polling/regenerate/PDF checks | `docs/features/E12-llm-report-runtime-readiness/S05-local-runbook-start-logs-smoke.md` | ✅ Готово |
| 12.6 | Triage + launch checklist | Симптомы, причины, readiness checklist | `docs/features/E12-llm-report-runtime-readiness/S06-failure-triage-launch-checklist.md` | ✅ Готово |

Полный контракт: `docs/SRS/SRS-E12-llm-report-runtime-readiness.md`.

---

## Epic 13: Report Depth Improvements

**Статус:** ⬜ Не начато
**Оценка:** 2–3 недели
**Зависимости:** E3 ✅, E4 ✅, E10 ✅, E11 ✅, E12 ✅

Цель E13 — поднять Self report с уровня “технически корректный расширенный гороскоп” до продукта Astrotype: добавить слой между фактами карты и narrative-выводами.

Ключевая формула:

```text
астрологический факт → психологический механизм → жизненный сценарий → риск → зрелая форма → проверочный вопрос
```

| # | Фича | Описание | Документы | Статус |
|---|------|----------|-----------|--------|
| 13.1 | Dominants + mechanism | Ключевые доминанты карты и внутренний механизм личности | `docs/features/E13-report-depth-improvements/S01-dominants-inner-mechanism.md` | ⬜ |
| 13.2 | House scenarios | Дома как жизненные сценарии, а не короткие ярлыки | `docs/features/E13-report-depth-improvements/S02-house-scenarios.md` | ⬜ |
| 13.3 | Evidence tracing | Связка вывода с основаниями в web/PDF | `docs/features/E13-report-depth-improvements/S03-evidence-tracing.md` | ⬜ |
| 13.4 | Contradictions/failures/maturity | Центральные противоречия, сбои системы, уровни зрелости | `docs/features/E13-report-depth-improvements/S04-contradictions-failures-maturity.md` | ⬜ |
| 13.5 | Calibration questions | Проверочные вопросы для подтверждения/будущей коррекции модели | `docs/features/E13-report-depth-improvements/S05-calibration-questions.md` | ⬜ |
| 13.6 | Career teaser | Содержательный Self→Career teaser без замены Career report | `docs/features/E13-report-depth-improvements/S06-career-teaser.md` | ⬜ |
| 13.7 | Rendering + quality gates | `self_story_v2`, UI/PDF rendering, validators, regression checks | `docs/features/E13-report-depth-improvements/S07-rendering-prompt-quality-gates.md` | ⬜ |

Полный контракт: `docs/SRS/SRS-E13-report-depth-improvements.md`.

---

## Зависимости между эпиками

```
E1 (Foundation) ✅
  └─► E2 (Identity) 🟡
        └─► E3 (Profile & Chart Engine)
              └─► E4 (Rules & Content)
                    └─► E5 (Products & Reports)
                          ├─► E6 (Billing & Subscriptions)
                          │     └─► E7 (Notifications & Admin) ──► E8 (Production & Scale)
                          ├─► E7 (Notifications & Admin)
                          └─► E10 (Report UX Redesign) ✅ ──► E11 (LLM Report Narrative) ✅ ──► E12 (LLM Report Runtime Readiness) ✅ ──► E13 (Report Depth Improvements)
```

**Критический путь:** E2 → E3 → E4 → E5 → E6 → E7 → E8

---

## MVP: Что нужно для первого запуска

**MVP = вертикаль "Self" с бесплатным превью + платная подписка**

| Эпик | Что входит в MVP | Что исключено |
|------|-------------------|---------------|
| E2 | Email + VK OAuth | Yandex OAuth, account linking |
| E3 | PersonProfile, геокодинг, эфемериды, ChartSnapshot | — |
| E4 | RuleSetVersion, TemplateVersion, движок правил, resolver | CMS для редакторов |
| E5 | Только Self-отчёт (free preview + полная версия по подписке) | Love, Child, Career |
| E6 | 1 план подписки (Self), 1 платёжный провайдер (YooKassa) | CloudPayments, Stripe, mobile billing |
| E7 | Email-уведомления, базовый admin | SMS, push, analytics |
| E8 | Rate limiting, базовая observability, runtime/deploy docs, PDF delivery без S3 и без обязательного object storage | WAF, load testing, GitOps, полный managed deploy |

**Оценка MVP:** 12–16 недель от текущего состояния.

---

## Таймлайн

```
Неделя:  1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20
E2       ████
E3           ████████████
E4                       ████████████
E5                                   ████████████████
E6                                                   ████████████████
E7                                                                   ████████████
E8                                                                               ████████████
MVP ──────────────────────────────────────────────────┤
```

---

*Документ живой — обновляется по мере продвижения.*
