# S01: Staging runtime, isolation and smoke

## Статус

🟡 Runtime healthy; isolation and webhook gaps remain

## Что сделать

- создать staging Compose с отдельными stateful volumes;
- подключить staging gateway и production Caddy через `astrotype_edge`;
- закрыть staging Basic Auth;
- добавить staging env contract;
- описать DNS, deploy, smoke, YooKassa test-shop и rollback;
- развернуть на VPS и зафиксировать live evidence.

## Файлы

- `docker-compose.staging.yml`
- `.env.staging.example`
- `deploy/Caddyfile.staging`
- `docker-compose.prod.yml`
- `deploy/Caddyfile`
- `docs/deployment/staging-vps.md`

## Acceptance criteria

- [x] Staging не использует production PostgreSQL/Redis volumes.
- [x] Test-shop credentials хранятся только в `.env.staging`.
- [x] Staging gateway требует Basic Auth и добавляет noindex header.
- [x] Runbook содержит bootstrap, health, logs, payment smoke и teardown.
- [x] Compose contracts проверены Compose CLI v5.5.1.
- [x] Caddy contracts проверены `caddy validate` на `caddy:2-alpine`.
- [x] Runtime развёрнут на VPS и проверен через внутренний staging gateway.
- [x] Production regression health прошёл после deploy.
- [x] Публичный HTTPS smoke пройден после настройки DNS.
- [ ] Только gateway подключён к `astrotype_edge`; backend/frontend недоступны в общей edge network.
- [ ] Staging использует отдельную YooKassa test-shop credential pair, не совпадающую с production runtime.
- [x] Staging deploy marker и runtime files соответствуют одному точному green commit.
- [x] Все сервисы текущего Compose contract, включая scheduler, запущены на VPS.
- [ ] Auth cookies на staging HTTPS имеют атрибут `Secure`.
- [ ] Fresh test-shop payment создаёт обработанный automatic webhook row и полный access readback.

## Verification evidence

Локально 2026-09-12:

- `docker:29-cli compose ... config --quiet` — staging contract valid;
- `caddy:2-alpine caddy validate` — production и staging Caddyfiles valid;
- YAML parse — production/staging services, volumes и edge network разделены.

VPS 2026-09-12:

- Compose CLI `2.40.3`, отдельный project `astrotype-staging`;
- backend, frontend, gateway, worker, PostgreSQL и Redis запущены;
- staging backend health: HTTP 200, database/Redis `ok`;
- gateway без Basic Auth: HTTP 401; с Basic Auth: HTTP 200;
- staging frontend через gateway: HTTP 200;
- `X-Robots-Tag: noindex, nofollow, noarchive` присутствует;
- credentials YooKassa приняты API, существующие payment objects имеют `test=true`;
- production health и frontend после подключения `astrotype_edge`: HTTP 200;
- DNS `staging.astrotype.ru` указывает на `46.173.16.113`;
- публичный TLS валиден: без Basic Auth HTTP 401, с Basic Auth health HTTP 200;
- публичный payment route за Basic Auth доступен и без app session корректно возвращает HTTP 401 `Not authenticated`.

## Re-audit evidence — 2026-09-26

- staging backend, frontend, gateway, worker, PostgreSQL и Redis запущены; scheduler отсутствует;
- staging Alembic current/head: `a6b7c8d9e0f1`;
- public staging без Basic Auth: HTTP 401, HSTS и `X-Robots-Tag` присутствуют;
- production public health: HTTP 200;
- production stateful services не подключены к staging network; production Caddy подключён к `astrotype_edge`;
- staging backend и frontend также подключены к `astrotype_edge`, поэтому target gateway-only boundary не соблюдён;
- staging PostgreSQL/Redis используют отдельные project volumes;
- `.env.staging` и Basic Auth include имеют mode `600`;
- staging PostgreSQL password и `SECRET_KEY` отличаются от production;
- staging и production используют одинаковую YooKassa credential pair; provider API подтверждает, что текущий shop test-only;
- staging DB: 6 users, 1 succeeded/paid test payment, active `self` entitlement, `account_tier=plus`, 0 webhook rows;
- `.deploy-sha` остаётся `0a498a0` и не идентифицирует фактическую E9 source revision;
- live Compose/runbook/env files происходят из разных repository revisions.

## E6 rollout evidence — 2026-10-09

- staging развёрнут из exact green SHA `a38101bfcf223a1b73d6daaeb92f67f9c4b06e92`;
- `.deploy-sha.staging` прочитан обратно с тем же SHA, scope — `release:main-full`;
- перед миграцией создан dump `backups/staging/pre-e6-20261009T221419Z.dump`, SHA-256 `188b40e9758f88b9ca2ad81dd2b2529ab9a1c46381e426b005b4fceb7d6539ad`; restore в disposable database сохранил counts `users=7`, `payments=4`, `entitlements=4`;
- Alembic staging обновлён с `e0f1a2b3c4d5` до `f1a2b3c4d5e6`; после миграции protected counts не изменились;
- backend, frontend, worker, refinement-monitor, scheduler, PostgreSQL, Redis, OTEL collector, Prometheus и gateway запущены; backend/Prometheus healthy, worker сообщает `ready`, scheduler отправляет periodic tasks;
- OpenAPI содержит monthly subscription checkout, cancel/resume, billing access и admin support/reconciliation routes;
- Prometheus загрузил правила `SubscriptionRenewalFailures`, `SubscriptionWebhookReconciliationFailures`, `UnexpectedSubscriptionExpiryTransitions` со здоровьем `ok`;
- public staging: без Basic Auth `401`, с Basic Auth health `200`, `/billing` `200`, app-session boundary `401`; `X-Robots-Tag: noindex, nofollow, noarchive` присутствует;
- production health после rollout остаётся `200`; production deploy marker не изменялся;
- provider probe подтверждает test-shop object: `status=succeeded`, `paid=true`, `test=true`, `999.00 RUB`;
- gateway-only edge isolation всё ещё не соблюдена: `astrotype_edge` содержит staging backend/frontend вместе с gateway;
- staging и production по-прежнему используют одинаковую YooKassa credential pair;
- fresh automatic webhook/payment smoke не выполнялся, поэтому webhook criterion остаётся открытым.

Точный анализ и closure proof: `./AUDIT-discrepancies.md`.

## Rollback

Остановить только staging project, удалить staging host из production Caddy и не выполнять `down -v`, пока сохранение staging данных не решено явно.
