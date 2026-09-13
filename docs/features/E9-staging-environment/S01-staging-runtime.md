# S01: Staging runtime, isolation and smoke

## Статус

🟡 В процессе

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

## Rollback

Остановить только staging project, удалить staging host из production Caddy и не выполнять `down -v`, пока сохранение staging данных не решено явно.
