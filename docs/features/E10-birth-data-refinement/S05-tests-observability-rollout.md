# S05: Тесты, наблюдаемость и rollout

## Статус

🟡 Controlled staging workflow, метрики, alerts, payment/entitlement и deployed rollback подтверждены; открыты буквальная 24-часовая граница и production canary

## Контекст

Функция меняет персональные исходные данные, запускает фоновый pipeline и ограничивает пользователя по времени. Локальные тесты необходимы, но не заменяют наблюдение за реальным staging, проверку 24-часового окна и сравнение payment/entitlement до и после операции.

## Реализованный локальный контракт

### Rollback feature flags

- Backend: `BIRTH_DATA_REFINEMENT_ENABLED`, безопасный default `false` в `Settings`.
- Frontend: `NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED`, безопасный default `false` в example/local окружении.
- В `docker-compose.staging.yml` и `docker-compose.prod.yml` backend/worker/refinement-monitor/scheduler используют `${BIRTH_DATA_REFINEMENT_ENABLED:-false}`, а frontend build/runtime — `${NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED:-false}`. Отсутствующее operator-owned значение поэтому fail-closed; `true` разрешено задавать явно только для контролируемого staging gate или одобренного production canary.
- Изменение backend flag применяется после recreate `backend`, `worker`, `refinement-monitor` и `scheduler`. Для `NEXT_PUBLIC_*` runtime-only изменение недостаточно: значение встраивается в Next.js bundle, поэтому для скрытия уже собранного UI обязателен rebuild frontend image с `false` и recreate frontend service.
- При выключенном backend flag POST возвращает bounded `503 / birth_data_refinement_disabled` до DB mutation и dispatch.
- Status/read endpoints и завершение уже запущенных worker-задач flag не блокирует.
- Rollback не удаляет ревизии, карты, отчёты или active-report pointer.

### Метрики без персональных данных

OTel-native instrument names в приложении:

- `birth_data_refinement_requests{outcome}`;
- `birth_data_refinement_cooldown_rejections`;
- `birth_data_refinement_generation_duration` с unit `s`;
- `birth_data_refinement_generation_failures{code}`;
- `birth_data_refinement_stuck_generations`;
- `birth_data_refinement_recent_failures`.

Ожидаемые Prometheus series после collector translation: counters получают `_total`, а duration histogram — unit suffix `_seconds`, то есть Story-facing имена остаются `birth_data_refinement_requests_total`, `birth_data_refinement_cooldown_rejections_total`, `birth_data_refinement_generation_duration_seconds` и `birth_data_refinement_generation_failures_total`. Локальные тесты различают OTel source names и Prometheus-facing names; локальный Docker smoke с pinned collector `0.103.0` подтвердил перевод всех четырёх series и обеих gauges. Это не является staging scrape/readback evidence.

`outcome` и `code` принимаются только из фиксированных allowlist. UUID, birth values, координаты, snapshots и тексты исключений не являются metric attributes.

### Monitor и alert rules

Celery beat запускает `profiles.monitor_birth_data_refinements` с configurable interval и route в отдельную очередь `birth-data-monitor`. В каждом local/staging/production Compose ровно один сервис `refinement-monitor` с `--concurrency=1 --pool=solo` потребляет только эту очередь без prefork parent/child duplication. Только этот сервис получает внутренний `BIRTH_DATA_REFINEMENT_MONITOR_EXPORTER=true` и регистрирует observable gauges; API, основной worker и scheduler их не регистрируют, поэтому нулевые/stale process-local series из других процессов не экспортируются. Основной worker явно потребляет только default queue `celery`, не запускает beat и не может забрать monitor task; singleton scheduler остаётся единственным beat process. Monitor worker использует отдельный OTLP service identity suffix `refinement-monitor-worker`. Monitor считает:

- `queued|processing` revisions старше `BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES`;
- revisions с bounded `error_code` `narrative_generation_failed|report_generation_failed` за `BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES`, независимо от status. Это включает narrative failure, который намеренно сохраняет пригодный deterministic result со status `deterministic_ready`, и исключает обычный `deterministic_ready` без failure code.

Monitor обновляет gauges `birth_data_refinement_stuck_generations` и `birth_data_refinement_recent_failures`, затем пишет bounded event `birth_data_refinement_alert` только с агрегатами и порогами. Staging Prometheus загружает `deploy/prometheus-birth-data-refinement.rules.yaml`; failed alert использует authoritative recent-failure gauge `> 0`, а failure counter сохраняется для rate/history анализа без риска потерять первый ненулевой sample.

Monitor query paths поддержаны двумя additive partial PostgreSQL indexes, одинаково определёнными в ORM и migration `e0f1a2b3c4d5`: `(status, updated_at) WHERE status IN ('queued','processing')` и `(error_code, updated_at) WHERE error_code IN ('narrative_generation_failed','report_generation_failed')`. Локальная disposable PostgreSQL 16 проверка подтвердила `alembic upgrade head`, наличие обоих indexes, downgrade до `d9e0f1a2b3c4` с удалением только этих indexes, повторный upgrade до head и `EXPLAIN` выбор каждого index при отключённом sequential scan. Migration не изменяет и не удаляет существующие rows. Это локальное migration/planner evidence, не live staging evidence.

Правила Prometheus реализованы, но доставка уведомления через Alertmanager не настроена и не заявляется как выполненная.

### Безопасные логи

Для refinement execution start/success/narrative-failure/fatal-failure logs содержат только разрешённые correlation IDs (`revision_id`, `generation_id`) и, где применимо, bounded `status`/`error_code`. `user_id`, `profile_id`, `report_id`, birth time/place/coordinates, snapshots и exception strings не логируются. Более богатый non-refinement logging сохранён отдельно, чтобы не ухудшить существующую диагностику общего v2 pipeline.

## Alert operator checks

1. Открыть staging Prometheus и проверить, что обе rules загружены без evaluation errors.
2. Проверить текущие значения stuck/recent-failure gauges и failure counter.
3. Сопоставить агрегат с revision status в БД без вывода snapshots/birth fields в тикет или лог.
4. При stuck проверить worker/broker health и возраст revision; не удалять committed rows.
5. При rollback установить оба flag в `false`, recreate backend/worker/refinement-monitor/scheduler, затем rebuild и recreate frontend; runtime-only frontend env change не скрывает UI из уже собранного bundle. Новые POST должны прекратиться, а read/status endpoints и worker completion остаться доступными.

## Выполненное live staging evidence

На staging 7 октября 2026 года развёрнут exact green SHA `4e4c60048f63e089306e913974ccc5c25843ab7c`.

- GitHub Actions run `37671694295` завершён успешно: Security Audit, backend/frontend lint, contracts, backend/frontend tests/build и Docker image build зелёные.
- Перед mutation создан dump `/opt/astrotype/backups/staging/predeploy-4e4c60048f63e089306e913974ccc5c25843ab7c-20261007T192550Z.dump`; restore в отдельную disposable database подтвердил одинаковые protected counts `6|6|2|2|12` до и после восстановления.
- Staging deploy marker прочитан как `4e4c60048f63e089306e913974ccc5c25843ab7c`, migration head — `e0f1a2b3c4d5`; protected counts после additive migration остались `6|6|2|2|12`.
- Deployment выполнен fail-closed: backend, основной worker, monitor и frontend используют `false`; только dedicated `refinement-monitor` имеет exporter flag `true`.
- Dedicated monitor запущен в единственном экземпляре с queue `birth-data-monitor`, `--concurrency=1 --pool=solo`. Реальное periodic execution завершилось с `stuck=0`, `recent_failed=0`, `alerted=false`, без `KeyError`/traceback.
- Staging Prometheus прочитал реальные series `birth_data_refinement_stuck_generations` и `birth_data_refinement_recent_failures`. Обе rules загружены и находятся в ожидаемом состоянии `inactive`; управляемое срабатывание alert ещё не выполнялось.
- Staging backend health вернул `status=ok`, `database=ok`, `redis=ok`; unauthenticated public staging boundary вернул `401` и сохранил `noindex` boundary.
- Production во время staging rollout не обновлялся: marker остался `d87dfc8d1d2d14e04d171262f2b00a9d0f9b591a`, migration head — `d9e0f1a2b3c4`, public health — `200`.
- Для frontend build временно включался swap из-за VPS с `3.8 GiB` RAM; после завершения build swap отключён и файл удалён.

Это подтверждает безопасный fail-closed deployment, миграцию, singleton monitor topology, scheduler execution и частичный Prometheus readback. Оно не подтверждает пользовательский refinement flow, counter/histogram series, alert firing, rollback при in-flight задаче или 24-часовую границу.

## Controlled staging evidence 8 октября 2026 года

На staging с marker `4e4c60048f63e089306e913974ccc5c25843ab7c` выполнен полный controlled workflow до 24-часовой границы и production canary.

- Перед включением создан backup `backups/staging/pre-e10-controlled-4e4c60048f63e089306e913974ccc5c25843ab7c-20261008T182213Z.dump`, размер `526315` bytes, SHA-256 `6ef31dbd9e9d123c1caa9b4059285e6736910911d337dc8e44af3a5b0dc370f7`.
- Оба flag были явно включены; backend/worker/refinement-monitor/scheduler пересозданы, frontend собран с public flag `true`. После smoke выполнен deployed rollback, и текущее live-состояние снова fail-closed: оба flag `false` во всех соответствующих сервисах, frontend пересобран с `false`.
- Authenticated staging profile `00f67608-a0a9-41f0-88c9-e1513c7e11f9`: status до операции вернул `can_refine=true`; POST вернул `202`, revision `59482b6f-96db-4afb-bc32-df4d9d4b2bd6`, generation `2857f967-5498-48d8-ab14-0172165af4b5`; второй POST вернул `429`, `Retry-After: 86400`, `next_available_at=2026-10-09T18:27:25.228612Z`.
- Старый отчёт оставался читаемым до, во время и после пересчёта; новый отчёт читается. Сохранены старые chart/report rows; создана ровно одна revision, новая карта имеет новый input hash и birth datetime и совпадает с revision snapshot по coordinates/timezone.
- Narrative mock завершился bounded `narrative_generation_failed`, при этом revision сохранила пригодный статус `deterministic_ready`; это ожидаемый failure-path contract, а не потеря deterministic result.
- Для владельца workflow payment rows остались `3 -> 3`, entitlements `3 -> 3`; стабильные hashes до/после совпали: payments `af2cd1c34c4db0d4420b4eba0bcf00e685cbdcabcf2b0b5b1871fd3d429c0fee`, entitlements `9b8aad40847a093ac4d596f55cbb58b2d1d0187cd8fca1508ec4c0921e83e89f`.
- Prometheus прочитал `requests_total{outcome="accepted"}=1`, `requests_total{outcome="cooldown"}=1`, `cooldown_rejections_total=1`, duration histogram count `1` / sum `0.40338439401239157`, `generation_failures_total{code="narrative_generation_failed"}=1`, а также singleton-monitor gauges.
- `BirthDataRefinementGenerationFailures` реально перешёл `pending -> firing -> inactive`; `BirthDataRefinementStuckGenerations` на управляемом временном `processing`/old-`updated_at` scenario перешёл `pending -> firing -> inactive`. После восстановления revision оба gauges прочитаны как `0`.
- Deployed rollback подтверждён отдельной delayed in-flight revision `aeb08592-26b2-4c5c-9735-7dafb9604da1`: backend/frontend rollback containers созданы в `19:10:11Z`/`19:10:44Z`, revision завершилась в `19:13:03Z` после `180.915688s`, а clean worker с flag `false` пересоздан в `19:13:05Z`. После rollback новый POST возвращает bounded `503 birth_data_refinement_disabled`, status/revision и старый/новый отчёты возвращают `200`, revision count остаётся `1`; временная worker-инструментация и swap отсутствуют.
- После перезапуска VPS 9 октября live readback подтвердил healthy staging services, flags `false`, отсутствие временной worker-инструментации и неизменные deploy markers; production public health остаётся `200`, production marker — `d87dfc8d1d2d14e04d171262f2b00a9d0f9b591a`.

## Остаток rollout-задачи

1. После `2026-10-09T18:27:25.228612Z` подтвердить на первой controlled revision буквальное повторное открытие серверного окна без изменения времени или данных. На момент live readback `2026-10-09T16:11:30Z` полные 24 часа ещё не истекли.
2. Только после закрытия 24-часового gate выполнить ограниченный production canary с отдельным backup/restore proof, readback exact deploy SHA и проверкой production rollback.

## Историческое нарушение production gate

Commit `d87dfc8` уже находился в production lineage при открытых критериях S05. Следовательно, ранее документированное правило «production только после зелёного CI и staging evidence» было нарушено. Текущая реализация добавляет технический rollback flag и локальные проверки, но не превращает отсутствующее историческое staging/production evidence в выполненное.

## Критерии приёмки

- [x] Backend telemetry allowlists/redaction, dedicated monitor-worker topology, bounded settings, indexed monitor queries, scheduler и Prometheus rules покрыты локальными тестами.
- [x] Выключенный backend flag не создаёт revision и не вызывает dispatch; read/status остаётся доступен.
- [x] Frontend скрывает E10 UI при выключенном public flag; staging/prod defaults fail-closed, а явный `true` зарезервирован для controlled stage/canary.
- [x] Browser source/E2E покрывает profile switch, manual-place rejection, POST 429 sync, keyboard activation и overflow на `320px`/`768px`; запуск подтверждается только фактическим Playwright result.
- [x] Метрики прочитаны на реальном staging из OTLP/Prometheus.
- [x] Prometheus alert rules сработали на управляемом stuck/failed staging scenario.
- [ ] Реальный 24-часовой staging smoke завершён.
- [x] Сравнение payment rows и entitlement до/после staging refinement выполнено.
- [x] Rollback обоих flag проверен на deployed staging с in-flight worker completion.
- [ ] Production canary выполнен после перечисленного staging evidence.

Статические тесты, compose validation и наличие rule-файла не закрывают runtime-критерии выше.
