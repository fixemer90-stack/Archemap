# E6 API: Free vs Plus access contract

Этот документ описывает API-сценарий E6 с практической точки зрения:

- каким endpoint'ом запускается upgrade;
- как клиент узнаёт access state;
- чем отличается `preview` от `full`;
- какие состояния должен понимать frontend;
- как не допустить утечку платного контента через API.

Документ служит контрактом под реализацию. Он фиксирует целевое поведение даже там, где код ещё не доведён до него.

## 1. Основная идея API

У E6 не должно быть «магического frontend paywall», который скрывает уже полученный полный контент.

API-контракт должен быть таким:

1. frontend запрашивает текущий access state;
2. backend возвращает разрешённый режим (`free`/`plus_active` и `preview`/`full`);
3. report/product endpoints отдают только тот объём данных, который разрешён этим state;
4. после оплаты frontend перечитывает access state, а не включает Plus локально сам.

## 2. Ключевые сущности

### 2.1 AccessState

Минимальный целевой объект для billing/account UI:

```json
{
  "plan_code": "free",
  "access_status": "free",
  "has_plus": false,
  "grants": {
    "self": "preview",
    "career": "locked"
  },
  "active_payment": null,
  "upgrade_cta": {
    "plan_code": "plus_monthly",
    "label": "Открыть Plus"
  }
}
```

### 2.2 ReportAccess

Каждый report/detail endpoint должен уметь возвращать не только контент, но и режим доступа:

```json
{
  "report_id": "...",
  "product": "self",
  "access_mode": "preview",
  "upgrade_required": true,
  "locked_sections": ["relationships", "sexuality", "career_path"],
  "billing_cta": {
    "href": "/billing",
    "label": "Открыть полный отчёт"
  }
}
```

`access_mode`:

- `preview` — free-friendly контент
- `full` — полный платный контент
- `locked` — продукт не доступен без оплаты вообще

## 3. Состояния, которые клиент обязан понимать

Frontend не должен ориентироваться только на boolean-флаг `has_plus`.

Нужны как минимум такие состояния:

- `free`
- `checkout_pending`
- `plus_active`
- `payment_failed`
- `plus_inactive`

### `free`

Значение:

- пользователь не имеет активного платного доступа;
- разрешён только Free scope.

Ожидаемое поведение клиента:

- показать preview/locked blocks;
- показать billing CTA.

### `checkout_pending`

Значение:

- payment создан или пользователь вернулся с PSP;
- entitlement ещё не подтверждён backend'ом.

Ожидаемое поведение клиента:

- не открывать full content заранее;
- показать статус ожидания и кнопку обновления.

### `plus_active`

Значение:

- backend подтвердил активный доступ.

Ожидаемое поведение клиента:

- загрузить полный контент;
- убрать paywall-CTA из оплаченных вертикалей.

### `payment_failed`

Значение:

- последняя попытка оплаты завершилась неуспешно.

Ожидаемое поведение клиента:

- оставить пользователя во Free;
- показать retry checkout.

### `plus_inactive`

Значение:

- у пользователя нет текущего активного Plus, даже если в истории были платежи.

Ожидаемое поведение клиента:

- вести себя как Free, но можно показать billing history/status.

## 4. Каталог и checkout

## 4.1 Плановый endpoint каталога

Целевой контракт:

```http
GET /api/v1/catalog/plans
```

Пример ответа:

```json
{
  "items": [
    {
      "plan_code": "plus_monthly",
      "title": "Astrotype Plus",
      "price": 999,
      "currency": "RUB",
      "interval": "month",
      "grants": {
        "self": "full",
        "career": "full"
      }
    }
  ]
}
```

Клиент читает этот контракт для отображения billing page, но не может подменять цену.

## 4.2 Создание оплаты

Текущий и желаемый принцип одинаковый: frontend отправляет только server-owned identifier.

```http
POST /api/v1/payments
Content-Type: application/json
```

Body:

```json
{
  "product_id": "plus_monthly",
  "return_url": "https://app.example.com/billing?from=payment"
}
```

Важно:

- `amount`, `currency`, `description`, `metadata` не приходят с клиента;
- backend маппит identifier на server-owned catalog entry;
- response возвращает redirect/confirmation URL.

## 4.3 Ответ create payment

```json
{
  "id": "payment_uuid",
  "provider": "yookassa",
  "provider_payment_id": "2f2f...",
  "amount": 999.0,
  "currency": "RUB",
  "status": "pending",
  "description": "Astrotype Plus — monthly access",
  "confirmation_url": "https://yookassa.ru/...",
  "payment_method_type": null,
  "paid_at": null,
  "created_at": "2026-06-07T12:00:00Z"
}
```

## 5. Billing/account state endpoint

Для frontend нужен отдельный удобный endpoint, а не сборка картины из пяти разных ресурсов.

Целевой контракт:

```http
GET /api/v1/billing/access
```

Пример ответа:

```json
{
  "plan_code": "plus_monthly",
  "access_status": "plus_active",
  "has_plus": true,
  "grants": {
    "self": "full",
    "career": "full"
  },
  "active_payment": {
    "status": "succeeded",
    "paid_at": "2026-06-07T12:03:00Z"
  }
}
```

Этот endpoint нужен для:

- `/billing`;
- post-payment refresh;
- product pages;
- account summary widgets.

## 6. Webhook semantics

```http
POST /api/v1/payments/webhooks/yookassa
```

Backend должен:

1. сохранить raw webhook;
2. найти локальный payment;
3. запросить canonical object у YooKassa;
4. сверить id/amount/currency/metadata;
5. только после этого обновить payment и активировать entitlement.

Если webhook не подтверждён, UI не должен автоматически переходить в `plus_active`.

## 7. Report API contract

## 7.1 Принцип

Report endpoint не должен возвращать полный платный payload бесплатному пользователю с расчётом, что frontend его спрячет.

Целевое поведение:

- backend знает access state пользователя;
- backend знает продукт (`self`, `career`);
- backend возвращает только разрешённый слой данных.

## 7.2 Self preview example

```json
{
  "id": "report_uuid",
  "product": "self",
  "access_mode": "preview",
  "upgrade_required": true,
  "narrative": {
    "hero": { "summary": "..." },
    "sections": [
      { "id": "strengths_preview", "title": "Ваш базовый паттерн", "locked": false },
      { "id": "relationships", "locked": true },
      { "id": "sexuality", "locked": true }
    ]
  },
  "locked_sections": ["relationships", "sexuality", "development"],
  "billing_cta": {
    "href": "/billing",
    "label": "Открыть полный отчёт"
  }
}
```

## 7.3 Career without Plus example

```json
{
  "product": "career",
  "access_mode": "locked",
  "upgrade_required": true,
  "locked_reason": "plus_required",
  "billing_cta": {
    "href": "/billing",
    "label": "Открыть Career в Plus"
  }
}
```

## 8. Post-payment refresh flow

После возврата с PSP frontend делает не optimistic unlock, а такой порядок:

1. читает `GET /api/v1/billing/access`;
2. если ещё `checkout_pending`, показывает ожидание и refresh;
3. если `plus_active`, перечитывает report/product data;
4. если `payment_failed`, остаётся во Free и предлагает retry.

## 9. Что должен проверить backend до выдачи full access

Перед возвратом `full` backend должен уметь ответить «да» на все вопросы:

- entitlement активен;
- entitlement относится к нужному продукту/плану;
- payment действительно подтверждён провайдером;
- срок доступа не истёк;
- current user совпадает с владельцем entitlement/report.

## 10. Антипаттерны

Нельзя делать так:

- full report в ответе + `is_blurred: true` на фронте;
- локальный флаг `subscribed=true` без backend refresh;
- price/amount из frontend body;
- paid access через отдельный route без backend policy;
- разблокировка Career только потому, что user уже успел открыть страницу.
