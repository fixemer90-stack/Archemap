# S05: Тесты, наблюдаемость и rollout

## Статус

🟡 Локальные observability/rollback-контракты реализованы; live staging/production evidence открыты

## Контекст

Функция меняет персональные исходные данные, запускает фоновый pipeline и ограничивает пользователя по времени. Локальные тесты необходимы, но не заменяют наблюдение за реальным staging, проверку 24-часового окна и сравнение payment/entitlement до и после операции.

## Реализованный локальный контракт

### Rollback feature flags

- Backend: `BIRTH_DATA_REFINEMENT_ENABLED`, безопасный default `false` в `Settings`.
- Frontend: `NEXT_PUBLIC_BIRTH_DATA_REFINEMENT_ENABLED`, безопасный default `false` в example/local окружении.
- В `docker-compose.staging.yml`, `docker-compose.prod.yml`, `.env.staging.example` и `.env.production.example` значение задано явно как `true`: это фиксирует намерение уже включённых окружений, а не полагается на default.
- При выключенном backend flag POST возвращает bounded `503 / birth_data_refinement_disabled` до DB mutation и dispatch.
- Status/read endpoints и завершение уже запущенных worker-задач flag не блокирует.
- Rollback не удаляет ревизии, карты, отчёты или active-report pointer.

### Метрики без персональных данных

- `birth_data_refinement_requests_total{outcome}`;
- `birth_data_refinement_cooldown_rejections_total`;
- `birth_data_refinement_generation_duration_seconds`;
- `birth_data_refinement_generation_failures_total{code}`;
- `birth_data_refinement_stuck_generations`.

`outcome` и `code` принимаются только из фиксированных allowlist. UUID, birth values, координаты, snapshots и тексты исключений не являются metric attributes.

### Monitor и alert rules

Celery beat запускает `profiles.monitor_birth_data_refinements` с configurable interval. Monitor считает:

- `queued|processing` revisions старше `BIRTH_DATA_REFINEMENT_STUCK_AFTER_MINUTES`;
- `failed` revisions за `BIRTH_DATA_REFINEMENT_MONITOR_WINDOW_MINUTES`.

При ненулевом результате он обновляет stuck gauge и пишет bounded event `birth_data_refinement_alert` только с агрегатами и порогами. Staging Prometheus загружает `deploy/prometheus-birth-data-refinement.rules.yaml` с правилами на stuck gauge и увеличение failure counter.

Правила Prometheus реализованы, но доставка уведомления через Alertmanager не настроена и не заявляется как выполненная.

### Безопасные логи

Refinement failure logs содержат только разрешённые correlation IDs (`revision_id`, `generation_id`) и bounded `error_code`. Birth time/place/coordinates/snapshots и `str(exc)` не логируются. Non-refinement exception logging сохранено отдельно, чтобы не ухудшить существующую диагностику общего v2 pipeline.

## Alert operator checks

1. Открыть staging Prometheus и проверить, что обе rules загружены без evaluation errors.
2. Проверить текущие значения stuck gauge и failure counter.
3. Сопоставить агрегат с revision status в БД без вывода snapshots/birth fields в тикет или лог.
4. При stuck проверить worker/broker health и возраст revision; не удалять committed rows.
5. При rollback выключить оба flag, прекратить новые POST, оставить read/status endpoints и worker completion доступными.

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

- [x] Backend telemetry allowlists/redaction, monitor output, scheduler и Prometheus rules покрыты локальными тестами.
- [x] Выключенный backend flag не создаёт revision и не вызывает dispatch; read/status остаётся доступен.
- [x] Frontend скрывает E10 UI при выключенном public flag; staging/prod включение задано явно.
- [x] Browser source/E2E покрывает profile switch, manual-place rejection, POST 429 sync, keyboard activation и overflow на `320px`/`768px`; запуск подтверждается только фактическим Playwright result.
- [ ] Метрики прочитаны на реальном staging из OTLP/Prometheus.
- [ ] Prometheus alert rules сработали на управляемом stuck/failed staging scenario.
- [ ] Реальный 24-часовой staging smoke завершён.
- [ ] Сравнение payment rows и entitlement до/после staging refinement выполнено.
- [ ] Rollback обоих flag проверен на deployed staging с in-flight worker completion.
- [ ] Production canary выполнен после перечисленного staging evidence.

Статические тесты, compose validation и наличие rule-файла не закрывают runtime-критерии выше.
