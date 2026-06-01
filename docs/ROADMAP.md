# Astrotype — Дорожная карта

> **Продукт:** Платформа астрологических личностных профилей (4 вертикали: Self, Love, Child, Career)
> **Обновлено:** 2026-05-29

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
| E5 | Products & Reports | ⬜ Не начато |
| E6 | Billing & Subscriptions | ⬜ Не начато |
| E7 | Notifications & Admin | ⬜ Не начато |
| E8 | Production & Scale | ⬜ Не начато |

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

## Epic 5: Products & Reports

**Статус:** ⬜ Не начато
**Оценка:** 4–5 недель
**Зависимости:** E3, E4

| # | Фича | Описание | Файлы/модули | Критерии приёмки |
|---|------|----------|---------------|------------------|
| 5.1 | Self-отчёт | Генерация персонального отчёта по натальной карте | `reports/self/`, `reports/generator.py` | Отчёт содержит: солнце, луна, асцендент, доминанты, архетип; PDF/API |
| 5.2 | Love: совместимость | Анализ пары: синастрия, паттерны, триггеры | `reports/love/`, `reports/synastry.py` | Два профиля → отчёт; оценка совместимости 0–100; топ-3 триггера |
| 5.3 | Child: профиль | Профиль ребёнка + рекомендации родителю | `reports/child/`, `reports/child_profile.py` | По дате/времени/месту → темперамент, сильные стороны, советы по воспитанию |
| 5.4 | Career: сильные стороны | Карьерные рекомендации по карте | `reports/career/`, `reports/career_profile.py` | Топ-5 профессий, сильные/слабые стороны, рекомендации по развитию |
| 5.5 | Версионирование отчётов | Хранение версий сгенерированных отчётов | `reports/models.py` | При изменении профиля — новый отчёт (старый сохраняется); история доступна |
| 5.6 | Хранилище отчётов | Хранение PDF и структурированных данных | `reports/storage.py`, S3/MinIO | PDF генерируется асинхронно; доступен по ссылке; TTL 30 дней для free |
| 5.7 | API отчётов | REST-эндпоинты для генерации и получения отчётов | `reports/views.py`, `reports/serializers.py` | POST generate, GET list/detail; pagination; permissions |

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

## Epic 8: Production & Scale

**Статус:** ⬜ Не начато
**Оценка:** 3–4 недели
**Зависимости:** E6, E7

| # | Фича | Описание | Файлы/модули | Критерии приёмки |
|---|------|----------|---------------|------------------|
| 8.1 | Rate limiting | Ограничение запросов по API | `middleware/rate_limit.py`, Redis | 100 req/min/user для API; 10 req/min для auth; 429 при превышении |
| 8.2 | WAF | Web Application Firewall (ModSecurity / Cloudflare) | infra/, nginx config | Блокировка SQLi, XSS, path traversal; логирование |
| 8.3 | Secrets manager | Хранение секретов (Yandex Lockbox / Vault) | `config/secrets.py`, deploy scripts | Ни одного секрета в коде/env-файлах; ротация через CI |
| 8.4 | Observability | Трассировка, метрики, логи | `observability/`, OTEL config, Prometheus, Loki | Traces в Jaeger; метрики в Grafana; логи в Loki; alerting |
| 8.5 | Load testing | Нагрузочное тестирование | `tests/load/`, k6/locust scripts | 500 concurrent users; p95 < 500ms для report generation |
| 8.6 | Yandex Managed K8s | Деплой на Yandex Managed Kubernetes | `deploy/k8s/`, Helm charts | Pod autoscaling; health checks; rolling updates; zero-downtime deploy |
| 8.7 | GitOps (Argo CD) | Автоматический деплой из Git | `deploy/argocd/`, `deploy/apps/` | Push в main → Argo CD sync → deploy; rollback через revert commit |

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
                          └─► E7 (Notifications & Admin)
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
| E8 | Rate limiting, базовая observability | WAF, load testing, GitOps |

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
