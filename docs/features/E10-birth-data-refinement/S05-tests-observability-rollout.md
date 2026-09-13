# S05: Тесты, наблюдаемость и rollout

## Статус

⬜ Не начато

## Контекст

Функция одновременно меняет персональные исходные данные, запускает дорогой pipeline и ограничивает пользователя по времени. Ошибки гонок или регенерации могут привести к несогласованному отчёту. Нужны автоматические проверки и staged rollout.

## Что сделать

### Backend tests

- Validation matrix для time/accuracy/place/coordinates/timezone.
- Ownership и запрет изменения birth date.
- Cooldown: первый успех, запрос до границы, запрос ровно на границе, после границы.
- Per-account ограничение при разных profile ID.
- Два конкурентных POST дают одну ревизию и один generation.
- Idempotency replay/conflict.
- No-op/422/503 не создают ложную committed-ревизию.
- Retry worker-задачи не создаёт дубликаты.
- Старый отчёт доступен до готовности нового.
- Failed regeneration не удаляет текущие артефакты.

### Frontend tests

- View/edit/cooldown/rebuilding/ready/failed states.
- Геокодер и запрет manual-only place.
- 429 синхронизирует `next_available_at`.
- Профильный selector при нескольких профилях.
- Имя/пароль не блокируются cooldown.
- Accessibility и responsive layout.

### Наблюдаемость

Метрики без персональных данных:

- `birth_data_refinement_requests_total{outcome}`;
- `birth_data_refinement_cooldown_rejections_total`;
- `birth_data_refinement_generation_duration_seconds`;
- `birth_data_refinement_generation_failures_total{code}`;
- количество stuck `queued|processing` старше порога.

Структурные логи содержат revision/profile/user UUID только в соответствии с политикой логирования; birth_time, place, coordinates и snapshots в логи не выводятся.

### Rollout

1. Additive migration + backend за feature flag.
2. Unit/integration/concurrency tests.
3. Staging: реальный профиль, изменение времени, проверка нового chart/report lineage.
4. Staging: 429 на второй запрос и проверка `Retry-After`.
5. Проверка сохранности старого отчёта/PDF и отсутствия платежа.
6. Включение UI на staging.
7. Production canary, мониторинг ошибок/stuck jobs.
8. Полное включение без destructive cleanup исторических данных.

## Staging smoke

```text
1. GET refinement-status -> can_refine=true.
2. POST с новым временем/местом -> 202, revision_id + generation_id.
3. GET status -> queued/processing -> deterministic_ready/ready.
4. Старый отчёт читается во время пересчёта.
5. Новый отчёт использует новую карту/input snapshot.
6. Повторный POST -> 429 + Retry-After + next_available_at.
7. В базе одна committed revision, старые chart/report rows сохранены.
8. YooKassa/payment records не созданы и entitlement не изменён.
```

## Rollback

- Выключить feature flag и скрыть UI.
- Не откатывать/не удалять committed-ревизии, карты и отчёты.
- Остановить новые enqueue, дать текущим задачам завершиться или безопасно retry.
- Вернуть чтение на последнюю готовую активную версию.
- Destructive downgrade таблиц запрещён без отдельного архивирования и проверки отсутствия данных.

## Критерии приёмки

- [ ] Все backend test classes зелёные, включая реальную PostgreSQL concurrency-проверку.
- [ ] Frontend state и accessibility tests зелёные.
- [ ] Метрики и безопасные логи доступны на staging.
- [ ] Alert покрывает stuck и failed generation.
- [ ] Staging smoke доказывает 24-часовой cooldown и сохранность старого отчёта.
- [ ] Staging smoke доказывает отсутствие новой оплаты/изменения entitlement.
- [ ] Rollback feature flag проверен без удаления данных.
- [ ] Production включается только после зелёного CI и staging evidence.
