# E9: Изолированная staging-среда

## Статус

🟡 Runtime развёрнут на VPS; публичный HTTPS зависит от DNS.

## Цель

Поднять `staging.astrotype.ru` на текущем VPS как изолированный runtime для проверки релизов и YooKassa test-shop до production cutover, не используя production PostgreSQL, Redis, credentials или volumes.

## Контракт

- отдельный Compose project `astrotype-staging`;
- отдельные PostgreSQL и Redis volumes;
- отдельный `.env.staging`, не попадающий в Git;
- `APP_ENV=staging`, LLM по умолчанию выключен/mock;
- только тестовые credentials YooKassa;
- Basic Auth перед всем staging surface;
- `X-Robots-Tag: noindex, nofollow, noarchive`;
- TLS завершается существующим production Caddy;
- связь Caddy со staging gateway идёт через внешнюю сеть `astrotype_edge`;
- production backend/frontend/database не подключаются к staging Compose network.

## Не входит

- копирование production базы или пользовательских данных;
- использование production YooKassa secret key;
- автоматическое продвижение staging базы в production;
- включение ещё не реализованной monthly Plus subscription.

## Acceptance criteria

- [x] Staging topology и isolation contract документированы.
- [x] Отдельные Compose/env/Caddy contracts добавлены.
- [ ] `staging.astrotype.ru` указывает на production VPS.
- [x] Staging containers запущены под отдельным Compose project.
- [ ] Публичный HTTPS требует Basic Auth и отдаёт `X-Robots-Tag`.
- [x] Внутренний staging health возвращает HTTP 200 после Basic Auth.
- [x] Production health остаётся HTTP 200 после подключения edge network.
- [ ] YooKassa test-shop checkout/webhook/readback smoke пройден.

## Stories

| ID  | Story                                                            | Статус        |
| --- | ---------------------------------------------------------------- | ------------- |
| S01 | [Staging runtime, isolation and smoke](./S01-staging-runtime.md) | 🟡 В процессе |

## Runbook

`docs/deployment/staging-vps.md`
