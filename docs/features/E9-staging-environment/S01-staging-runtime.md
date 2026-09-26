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
- [ ] Staging deploy marker и runtime files соответствуют одному точному green commit.
- [ ] Все сервисы текущего Compose contract, включая scheduler, запущены на VPS.
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

Точный анализ и closure proof: `./AUDIT-discrepancies.md`.

## Rollback

Остановить только staging project, удалить staging host из production Caddy и не выполнять `down -v`, пока сохранение staging данных не решено явно.
