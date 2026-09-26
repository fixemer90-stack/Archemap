# E9: Изолированная staging-среда

## Статус

🟡 Runtime healthy; isolation, deploy identity and automatic webhook gaps remain open.

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

## Аудит

Консолидированные расхождения и текущий live readback: `./AUDIT-discrepancies.md`.

## Не входит

- копирование production базы или пользовательских данных;
- использование production YooKassa secret key;
- автоматическое продвижение staging базы в production;
- включение ещё не реализованной monthly Plus subscription.

## Acceptance criteria

- [x] Staging topology и isolation contract документированы.
- [x] Отдельные Compose/env/Caddy contracts добавлены.
- [x] `staging.astrotype.ru` указывает на production VPS.
- [x] Staging containers запущены под отдельным Compose project.
- [x] Публичный HTTPS требует Basic Auth и отдаёт `X-Robots-Tag`.
- [x] Внутренний staging health возвращает HTTP 200 после Basic Auth.
- [x] Production health остаётся HTTP 200 после подключения edge network.
- [ ] Только staging gateway подключён к общей `astrotype_edge`; backend/frontend остаются в private staging network.
- [ ] YooKassa test-shop credentials отличаются от credentials production runtime.
- [ ] Live staging соответствует одному точному green commit и staging deploy marker.
- [ ] Текущая Compose topology, включая scheduler, развёрнута полностью.
- [ ] Staging auth cookies используют `Secure` на публичном HTTPS host.
- [ ] YooKassa test-shop automatic webhook/readback smoke пройден.

## Stories

| ID  | Story                                                            | Статус               |
| --- | ---------------------------------------------------------------- | -------------------- |
| S01 | [Staging runtime, isolation and smoke](./S01-staging-runtime.md) | 🟡 Audit gaps remain |

## Runbook

`docs/deployment/staging-vps.md`
