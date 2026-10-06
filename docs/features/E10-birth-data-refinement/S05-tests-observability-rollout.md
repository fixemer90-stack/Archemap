# S05: Тесты, наблюдаемость и rollout

## Статус

🟡 Локальные observability/rollback-контракты реализованы; live staging/production evidence открыты

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

Celery beat запускает `profiles.monitor_birth_data_refinements` с configurable interval и route в отдельную очередь `birth-data-monitor`. В каждом local/staging/production Compose ровно один сервис `refinement-monitor` с `--concurrency=1` потребляет только эту очередь и экспортирует gauges из одного process-local instrument state. Основной worker явно потребляет только default queue `celery`, не запускает beat и не может забрать monitor task; singleton scheduler остаётся единственным beat process. Monitor worker использует отдельный OTLP service identity suffix `refinement-monitor-worker`. Monitor считает:

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

## Staging smoke — ещё не выполнен

```text
1. GET refinement-status -> can_refine=true.
2. POST с новым временем/местом -> 202, revision_id + generation_id.
3. GET status -> queued/processing -> deterministic_ready/ready.
4. Старый отчёт читается во время пересчёта.
5. Новый отчёт использует новую карту/input snapshot.
6. Повторный POST -> 429 + Retry-After + next_available_at.
7. Через полные 24 часа серверное окно снова открывается.
8. В базе одна committed revision, старые chart/report rows сохранены.
9. YooKassa/payment records не созданы и entitlement не изменён.
10. Оба flag выключаются; POST блокируется без write/dispatch, reads и in-flight completion работают.
```

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
