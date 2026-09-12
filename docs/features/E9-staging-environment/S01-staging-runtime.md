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
- [ ] Runtime развернут и проверен снаружи.
- [ ] Production regression health прошёл после deploy.

## Verification evidence

Локально 2026-09-12:

- `docker:29-cli compose ... config --quiet` — staging contract valid;
- `caddy:2-alpine caddy validate` — production и staging Caddyfiles valid;
- YAML parse — production/staging services, volumes и edge network разделены.

## Rollback

Остановить только staging project, удалить staging host из production Caddy и не выполнять `down -v`, пока сохранение staging данных не решено явно.
