# S05: Тесты, наблюдаемость и rollout

## Статус

🟡 Реализация и fail-closed staging deployment завершены; controlled workflow/alert/24h/rollback evidence и production canary открыты

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

## Остаток rollout-задачи

1. Явно включить на staging `BIRTH_DATA_REFINEMENT_ENABLED=true`; recreate `backend`, `worker`, `refinement-monitor` и `scheduler`.
2. Явно включить `NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED=true`; rebuild frontend image и recreate frontend. Runtime-only изменение env не считается включением UI.
3. Выполнить authenticated workflow на выделенном staging profile:
   - `GET refinement-status` возвращает `can_refine=true`;
   - первый `POST` возвращает `202` с `revision_id` и `generation_id`;
   - status проходит `queued/processing -> deterministic_ready/ready`;
   - старый отчёт остаётся читаемым во время пересчёта;
   - новый отчёт использует новую карту/input snapshot;
   - повторный `POST` возвращает `429`, `Retry-After` и `next_available_at`;
   - committed revision ровно одна, старые chart/report rows сохранены.
4. После реального workflow прочитать из Prometheus request/cooldown/duration/failure series, а не только monitor gauges, и зафиксировать bounded labels без персональных данных.
5. Создать управляемые staging stuck и failed scenarios, дождаться фактического перехода обеих Prometheus rules в firing, затем подтвердить возврат в inactive. Alertmanager delivery остаётся отдельным незакрытым контрактом.
6. Сравнить payment rows и entitlement до/после refinement; подтвердить отсутствие новых YooKassa/payment rows и отсутствие изменения entitlement.
7. Во время реально выполняющейся worker-задачи выключить оба flag: новые POST должны блокироваться без DB write/dispatch, status/read должны работать, уже запущенная задача должна завершиться. Для frontend rollback обязателен rebuild с `false`.
8. Выдержать буквальные полные 24 часа от committed revision и подтвердить повторное открытие серверного окна, не подменяя этот gate изменением времени или данных.
9. Только после пунктов 1–8 выполнить ограниченный production canary с отдельным backup/restore proof, readback exact deploy SHA и проверкой production rollback.

## Историческое нарушение production gate

Commit `d87dfc8` уже находился в production lineage при открытых критериях S05. Следовательно, ранее документированное правило «production только после зелёного CI и staging evidence» было нарушено. Текущая реализация добавляет технический rollback flag и локальные проверки, но не превращает отсутствующее историческое staging/production evidence в выполненное.

## Критерии приёмки

- [x] Backend telemetry allowlists/redaction, dedicated monitor-worker topology, bounded settings, indexed monitor queries, scheduler и Prometheus rules покрыты локальными тестами.
- [x] Выключенный backend flag не создаёт revision и не вызывает dispatch; read/status остаётся доступен.
- [x] Frontend скрывает E10 UI при выключенном public flag; staging/prod defaults fail-closed, а явный `true` зарезервирован для controlled stage/canary.
- [x] Browser source/E2E покрывает profile switch, manual-place rejection, POST 429 sync, keyboard activation и overflow на `320px`/`768px`; запуск подтверждается только фактическим Playwright result.
- [ ] Метрики прочитаны на реальном staging из OTLP/Prometheus.
- [ ] Prometheus alert rules сработали на управляемом stuck/failed staging scenario.
- [ ] Реальный 24-часовой staging smoke завершён.
- [ ] Сравнение payment rows и entitlement до/после staging refinement выполнено.
- [ ] Rollback обоих flag проверен на deployed staging с in-flight worker completion.
- [ ] Production canary выполнен после перечисленного staging evidence.

Статические тесты, compose validation и наличие rule-файла не закрывают runtime-критерии выше.
