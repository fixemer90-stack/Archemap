# Переход YooKassa с тестового на боевой магазин

Статус: операторский runbook подготовлен; переключение и live-платёж не выполнялись.

Дата аудита репозитория: 2026-09-12.

Область: текущие разовые платежи Astrotype через YooKassa. Будущая ежемесячная подписка Plus из `docs/architecture/monthly-plus-subscription-contract.md` ещё не реализована и этим переключением не включается.

## 1. Что именно меняется

Astrotype уже обращается к единому API `https://api.yookassa.ru/v3`. Отдельного production URL в коде нет: тестовый или боевой магазин определяется парой `shopId` + `secret key`.

При переходе меняются:

- `YOOKASSA_SHOP_ID` — идентификатор боевого магазина;
- `YOOKASSA_SECRET_KEY` — секретный ключ боевого магазина;
- настройки уведомлений в личном кабинете боевого магазина;
- фискальный сценарий и разрешённые способы оплаты;
- операторский мониторинг и процедура возврата денег.

Не меняются:

- API URL YooKassa;
- публичный webhook Astrotype: `https://astrotype.ru/api/v1/payments/webhooks/yookassa`;
- return URL: `https://astrotype.ru/billing?checkout=return`;
- правило подтверждения: только server-to-server сверка YooKassa и локальная запись, а не возврат браузера.

## 2. Текущий контракт Astrotype

| Область                       | Реализовано сейчас                                                                     |
| ----------------------------- | -------------------------------------------------------------------------------------- |
| Создание checkout             | `POST /api/v1/payments`, продукт и цена берутся из backend catalog                     |
| Боевой товар, используемый UI | `self_full`, 999 RUB                                                                   |
| YooKassa confirmation         | redirect с возвратом на `/billing?checkout=return`                                     |
| Capture                       | автоматический (`capture=true`)                                                        |
| Webhook                       | `POST /api/v1/payments/webhooks/yookassa`                                              |
| Подтверждение                 | backend получает canonical payment через YooKassa API                                  |
| Успех                         | `status=succeeded` и `paid=true`                                                       |
| Доступ                        | `payments.paid_at`, entitlement и `users.account_tier=plus`                            |
| Защита от повтора create      | `Idempotence-Key` равен локальному `payments.id`                                       |
| Пропущенный webhook           | bounded reconciliation последнего pending/processing payment при чтении billing/access |

Исходники: `backend/app/modules/payments/`, `backend/app/modules/catalog/service.py`, `frontend/src/components/billing/billing-checkout-button.tsx`.

## 3. Стоп-факторы до переключения

Переключение в боевой режим запрещено, пока каждый пункт не имеет владельца и подтверждения.

### 3.1 Фискализация и чеки — обязательное решение

Текущий `POST /v3/payments` не передаёт объект `receipt`, данные покупателя, позиции чека, НДС или систему налогообложения.

До go-live ответственный за бухгалтерию/54-ФЗ должен подтвердить один из вариантов:

1. чеки полностью формируются настроенной внешней онлайн-кассой/решением YooKassa без `receipt` в запросе Astrotype; или
2. Astrotype должен передавать `receipt` — тогда сначала требуется отдельная code/story реализация и тестирование.

Без зафиксированного варианта нельзя считать платёжный контур production-ready.

### 3.2 Нет программного kill switch

В приложении нет env-флага, который отключает только создание новых checkout. До появления такого флага аварийная остановка выполняется ingress-правилом из раздела 10.

### 3.3 Возвраты не автоматизированы

Модель содержит статус `refunded`, но текущий webhook parser и service не обрабатывают объект `refund`. На первом запуске:

- не подписывать текущий endpoint на `refund.succeeded`;
- выполнять возвраты по согласованной ручной процедуре в YooKassa;
- отдельно сверять и документировать локальный доступ после возврата;
- автоматизацию возвратов реализовать отдельной Story до массового использования refund flow.

### 3.4 `YOOKASSA_WEBHOOK_SECRET` не является защитой текущего webhook

Настройка существует в `Settings`, но код её не использует. Текущий handler не проверяет HMAC: он получает payment id из уведомления, затем запрашивает canonical payment у YooKassa и сверяет id, сумму, валюту и metadata.

Не считать заполнение `YOOKASSA_WEBHOOK_SECRET` мерой готовности. Секрет не нужен текущему runtime и не должен подменять server-to-server reconciliation.

### 3.5 Production guard не проверяет YooKassa credentials

`backend/app/core/secrets.py` пока не включает `YOOKASSA_SHOP_ID` и `YOOKASSA_SECRET_KEY` в обязательные production secrets. Поэтому успешный старт backend не доказывает готовность платежей. Использовать отдельную credential-проверку из раздела 7.

## 4. Предварительные решения в личном кабинете YooKassa

До работ на VPS подтвердить:

- боевой магазин активирован и договор/анкета завершены;
- получены именно боевые `shopId` и secret key;
- разрешены нужные способы оплаты;
- выбран и проверен сценарий чеков/54-ФЗ;
- определены email/телефон покупателя, если они требуются выбранному сценарию чеков;
- согласованы назначение платежа, оферта, политика возвратов и контакт поддержки;
- назначены владелец переключения и оператор, который видит YooKassa, VPS, логи и PostgreSQL;
- выбран временной слот, в который можно выполнить реальный платёж на 999 RUB и при необходимости возврат.

Тестовые карты предназначены для тестового магазина. Финальный smoke с боевыми credentials — реальная финансовая операция.

## 5. Уведомления боевого магазина

Для текущей реализации зарегистрировать:

```text
https://astrotype.ru/api/v1/payments/webhooks/yookassa
```

События первого запуска:

- `payment.succeeded`;
- `payment.canceled`.

Не включать на этот endpoint события с другим object shape, в частности `refund.succeeded`, пока backend явно их не поддерживает.

Webhook должен быть доступен по публичному HTTPS без пользовательской авторизации. Caddy уже проксирует `/api/*` в backend.

Успешная доставка webhook сама по себе не доказывает оплату: Astrotype повторно получает payment через API YooKassa. Для валидной обработки endpoint возвращает HTTP 200.

## 6. Подготовка VPS

Рабочий каталог:

```bash
cd /opt/astrotype
```

### 6.1 Снимок и backup

Перед изменением credentials сделать snapshot VPS у провайдера и dump базы:

```bash
cd /opt/astrotype
mkdir -p backups
stamp=$(date -u +%Y%m%dT%H%M%SZ)
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T postgres \
  sh -lc 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' \
  > "backups/postgres-$stamp.sql"
test -s "backups/postgres-$stamp.sql"
```

Сохранить защищённую копию текущего env:

```bash
cp -p .env.production ".env.production.before-yookassa-$stamp"
chmod 600 ".env.production.before-yookassa-$stamp"
```

Не печатать secret key в терминальный лог, CI, issue или документацию.

### 6.2 Заполнить env

В `/opt/astrotype/.env.production`:

```dotenv
YOOKASSA_SHOP_ID=<production-shop-id>
YOOKASSA_SECRET_KEY=<production-secret-key>
```

`FRONTEND_URL` должен оставаться:

```dotenv
FRONTEND_URL=https://astrotype.ru
```

Проверить только наличие, не значения:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production config >/dev/null
set -a
. ./.env.production
set +a
test -n "$YOOKASSA_SHOP_ID"
test -n "$YOOKASSA_SECRET_KEY"
```

После проверки очистить переменные текущей shell-сессии:

```bash
unset YOOKASSA_SHOP_ID YOOKASSA_SECRET_KEY
```

## 7. Deploy и credential probe

Пересобрать и перезапустить backend; worker получает тот же env, поэтому его также пересоздать:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build backend worker frontend caddy

docker compose -f docker-compose.prod.yml --env-file .env.production ps
curl -fsS https://astrotype.ru/api/v1/health
```

Проверить, что credentials принимаются API YooKassa, не выводя их:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec -T backend \
  python - <<'PY'
import os
import httpx

response = httpx.get(
    "https://api.yookassa.ru/v3/payments",
    params={"limit": 1},
    auth=(os.environ["YOOKASSA_SHOP_ID"], os.environ["YOOKASSA_SECRET_KEY"]),
    timeout=30,
)
print(f"YooKassa credential probe: HTTP {response.status_code}")
response.raise_for_status()
PY
```

Ожидается HTTP 200. HTTP 401 означает неверную пару магазина/ключа; не продолжать.

Проверить маршрут webhook извне безопасным невалидным JSON:

```bash
curl -i -X POST \
  -H 'Content-Type: application/json' \
  --data 'not-json' \
  https://astrotype.ru/api/v1/payments/webhooks/yookassa
```

Ожидается HTTP 400 `Invalid JSON`, а не 404/502/HTML frontend. Это доказывает маршрутизацию, но не доставку от YooKassa.

## 8. Последовательность cutover

1. Завершить checklist разделов 3–5.
2. Сделать snapshot, DB dump и защищённую копию env.
3. Установить боевые credentials и выполнить deploy.
4. Получить HTTP 200 от credential probe.
5. Зарегистрировать URL и два payment events в боевом кабинете YooKassa.
6. Выполнить внешний route probe и проверить backend/Caddy logs.
7. Войти отдельным production-smoke пользователем.
8. Открыть `https://astrotype.ru/billing` и создать checkout обычной кнопкой.
9. Проверить в YooKassa до оплаты: магазин боевой, сумма 999.00 RUB, описание ожидаемое.
10. Выполнить реальную оплату.
11. Провести readback из раздела 9.
12. Зафиксировать payment id, время, результат, ответственного и решение о возврате тестовой суммы. Не фиксировать PAN/CVC или secret key.

Не менять цену на лету ради smoke: production UI использует backend-owned catalog.

## 9. Обязательный readback после live-платежа

### 9.1 Логи

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production logs --since=15m backend \
  | grep -E 'payment_created|payment_status_updated|webhook_provider_reconciliation_failed|webhook_payment_mismatch|webhook_succeeded_without_paid_true'
```

Не публиковать raw webhook payload или платёжные реквизиты.

### 9.2 PostgreSQL

Открыть psql:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec postgres \
  sh -lc 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

Проверить пользователя, локальный payment и provider id:

```sql
select id, user_id, provider, provider_payment_id, amount, currency,
       status, paid_at, failed_at, cancelled_at, created_at
from payments
where user_id = '<production-smoke-user-id>'
order by created_at desc
limit 5;
```

Проверить реальную доставку webhook:

```sql
select id, provider, event_type, payment_id, processed,
       processed_at, error_message, created_at
from payment_webhooks
where payment_id = '<provider-payment-id>'
order by created_at desc;
```

Проверить доступ:

```sql
select id, user_id, product, status, source_payment_id,
       starts_at, expires_at, created_at
from entitlements
where user_id = '<production-smoke-user-id>'
order by created_at desc;

select id, account_tier
from users
where id = '<production-smoke-user-id>';
```

Критерий успешного cutover:

- YooKassa показывает payment `succeeded`, `paid=true`, 999.00 RUB;
- локальный payment имеет `status='succeeded'` и `paid_at is not null`;
- есть обработанный `payment.succeeded` webhook без ошибки;
- entitlement имеет `product='self'`, `status='active'` и ссылается на локальный payment;
- `users.account_tier='plus'`;
- `GET /api/v1/billing/access` аутентифицированного smoke-пользователя возвращает `plus_active`;
- платный ресурс открывается тому же user id;
- backend не содержит reconciliation/mismatch ошибок для этого payment.

Если доступ активировался fallback-reconciliation, но строки `payment_webhooks` нет, платёж подтверждён, однако webhook cutover не принят: исправить доставку и повторить smoke отдельным платежом.

## 10. Аварийная остановка и rollback

### 10.1 Сначала остановить новые checkout

Пока нет application kill switch, временно добавить в site block `deploy/Caddyfile` перед `@api`:

```caddyfile
@disablePaymentCheckout {
  method POST
  path /api/v1/payments
}
respond @disablePaymentCheckout 503
```

Затем применить:

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec caddy \
  caddy reload --config /etc/caddy/Caddyfile
```

Webhook `/api/v1/payments/webhooks/yookassa` должен оставаться доступным, чтобы завершить уже начатые платежи.

### 10.2 Сверить незавершённые операции

До отзыва ключа найти `pending`/`processing` платежи и сверить каждый с YooKassa. Не удалять `payments`, `payment_webhooks` или `entitlements` и не выдавать доступ по скриншоту/return URL.

### 10.3 Отозвать доступ

После reconciliation:

1. удалить/отключить webhook в кабинете, если его доставка вызывает инцидент;
2. отозвать скомпрометированный secret key и выпустить новый;
3. восстановить предыдущий env только если он заведомо безопасен и соответствует нужному магазину;
4. пересоздать backend и worker;
5. повторить health, credential и DB readback.

Нельзя переключать production UI обратно на тестовый магазин как пользовательский rollback: это создаст ложные checkout. Сначала checkout должен быть закрыт ingress/application kill switch.

## 11. Go/no-go checklist

### До deploy

- [ ] Боевой магазин активен.
- [ ] Боевые `shopId` и secret key получены и сохранены вне Git.
- [ ] Сценарий чеков/54-ФЗ письменно подтверждён.
- [ ] В кабинете разрешены нужные способы оплаты.
- [ ] Оферта, возвраты и поддержка готовы.
- [ ] Snapshot, DB dump и env backup созданы.
- [ ] Назначены владелец cutover и оператор наблюдения.

### После deploy, до реального платежа

- [ ] Backend/worker/frontend/Caddy healthy.
- [ ] YooKassa credential probe вернул HTTP 200.
- [ ] Webhook route probe вернул ожидаемый HTTP 400.
- [ ] В боевом кабинете зарегистрированы только `payment.succeeded` и `payment.canceled`.
- [ ] Согласованы smoke-user, платёж 999 RUB и последующий возврат/учёт.

### После реального платежа

- [ ] Provider payment: `succeeded`, `paid=true`, сумма и валюта совпадают.
- [ ] Local payment: `succeeded`, `paid_at` заполнен.
- [ ] Webhook сохранён и обработан.
- [ ] Entitlement и account tier принадлежат тому же user id.
- [ ] Billing access и платный ресурс проверены через UI/API.
- [ ] Ошибок reconciliation/mismatch нет.
- [ ] Результат, payment id и решение по возврату записаны в журнал запуска.

## 12. Официальные справочные материалы YooKassa

Перед фактическим cutover перепроверить пункты в актуальной документации и личном кабинете:

- переход в боевой режим: https://yookassa.ru/developers/payment-acceptance/testing-and-going-live/going-live
- быстрый старт и создание платежа: https://yookassa.ru/developers/payment-acceptance/getting-started/quick-start
- авторизация API: https://yookassa.ru/developers/using-api/authorization/basics
- входящие уведомления: https://yookassa.ru/developers/using-api/webhooks
- статусы платежа: https://yookassa.ru/developers/payment-acceptance/after-the-payment/payment-statuses
- способы оплаты: https://yookassa.ru/developers/payment-acceptance/payment-methods
- чеки по 54-ФЗ: https://yookassa.ru/developers/payment-acceptance/receipts/54fz/basics

Внешняя документация может меняться; личный кабинет боевого магазина остаётся источником фактически подключённых методов, ключей и уведомлений.
