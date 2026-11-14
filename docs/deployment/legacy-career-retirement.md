# E20: неразрушающий retirement Career v1 и последующая проверка

## Текущая граница

Production/staging rollout **не выполняется**: владелец сообщил об утрате сервера после кибератаки. Этот runbook не является разрешением обращаться к старому серверу, доверять восстановленному snapshot, включать платежи/LLM или удалять данные. Кодовые и synthetic проверки не закрывают live gates E20.

Источники: [Feature](../features/E20-legacy-career-retirement/FEATURE.md), [source inventory](../features/E20-legacy-career-retirement/INVENTORY.md), [SRS](../SRS/SRS-E20-legacy-career-retirement.md).

Default data strategy: **retain**. Сохраняются generic Career rows, version snapshots, saved narratives и direct Career entitlements. Retirement не выполняет migration/backfill/conversion, удаление, отзыв grants или удаление ruleset. Утверждение окончательной retention/removal strategy остаётся отдельным owner decision.

## Локальная проверка без старой инфраструктуры

1. Использовать только собственные disposable PostgreSQL fixtures и явно заданный `TEST_DATABASE_URL`; существующие backend fixtures могут выполнять schema teardown. Не использовать application `.env` как тестовую базу.
2. `LLM_ENABLED=false`, `LLM_PROVIDER=mock`, `LLM_MODEL=mock-self-v1`, пустой provider API key; никаких настоящих payment/provider calls.
3. Проверить generic Career generation/interpretation/regenerate и worker обходы: стабильный 410 или контролируемый retirement outcome без report/status/version/narrative/chart mutation.
4. Проверить owned historical JSON/versions/GET-HEAD-POST PDF на свежей DB session; сравнить status/version/payload и связанные rows до/после. Foreign/nonexistent IDs не раскрывают содержимое.
5. Проверить target Career с Plus/direct Career grant и без legacy row, отказ expired/revoked/future grants, duplicate grants и отрицательный legacy-ID target lookup.
6. Проверить Self generation/narrative/reader/PDF как отдельный non-regression flow.
7. Проверить native desktop/mobile reader через synthetic API fixtures: existing archive, missing row, denied access, download PDF, отсутствие chart POST/generation/regeneration/polling для архива.
8. Провести независимые spec, затем code/security reviews. Runbook/production критерии не отмечать PASS на основании authored tests или коллекции тестов.

## Подготовка восстановленной среды

До любых будущих действий отдельно согласовать target, release SHA, trusted data source и scope. Не использовать адрес/credential из исторического `.env` как доказательство актуального сервера.

- Зафиксировать identity восстановленной среды, безопасные DB credentials и независимость staging/production.
- Подтвердить происхождение и целостность восстановленных данных; отсутствие источника — unknown, не ноль rows.
- Восстановить environment/configuration и проверить readiness каждого consumer, брокера и scheduler.
- Сделать независимую backup/restore rehearsal с aggregate/hash equality до будущего destructive proposal. E20 retirement сам по себе не требует destructive proposal.
- Проверить разрешённые native auth/access/owner fixtures; не выдавать grants реальным клиентам ради теста.
- Публикация кода не означает rollout: deploy jobs должны оставаться manual-only; manual dispatch сейчас не выполняется.

## Read-only aggregate census

У инструмента нет application DB default. Operator настраивает `E20_CENSUS_DATABASE_URL` через защищённый локальный способ; значение не публикуется в чате, docs, shell trace или CI logs. Роль для реальной проверки должна иметь только необходимые SELECT privileges на `reports`/`entitlements` и разрешение read-only connection. Ниже приведена команда чтения, не provisioning credentials и не команда запуска на утраченной инфраструктуре.

```bash
cd backend
./.venv/bin/python scripts/legacy_career_census.py --confirm-read-only
```

Другую явно подготовленную переменную можно выбрать через `--database-url-env`. Application `DATABASE_URL`/dotenv не используются как fallback. При отсутствующем URL/таблицах/доступе инструмент завершается nonzero с безопасной общей ошибкой; отсутствие доступа не превращается в пустой census.

Сохранять только aggregate output и приватный execution record с target identity/release/time; сам публичный JSON не доказывает, что соединение было production. Tool устанавливает/проверяет `REPEATABLE READ, READ ONLY`, ограничивает statement timeout и не принимает caller transaction. Counts legacy rows и grandfathered grants раздельны; прямой grant не является ссылкой на report row. Malformed/unknown statuses объединяются в `other`, payloads/identifiers не выбираются.

`compatibility_usage.available=false` означает, что historical usage этим SQL не измерено. Для удаления нужны реальные telemetry/external-client evidence; копирование текущих aggregate counts не заменяет наблюдение.

## Телеметрия retirement

Source contract инструментации: `backend/app/modules/reports/retirement.py`. Native OTel counter должен называться `legacy_career_operations` без Prometheus `_total`; ожидаемое имя после стандартного Prometheus exporter — `legacy_career_operations_total`. Реальное exporter mapping и scrape visibility проверяются после восстановления, не выводятся из source unit tests.

Единственный прикладной label — `operation`, из фиксированного списка:

- `blocked_generation` — generic Report/rules Career generation отклонена;
- `blocked_regenerate` — narrative regeneration отклонена;
- `blocked_worker` — queued/direct narrative writer/finalizer отклонён;
- `archive_read` — разрешённый user-facing historical JSON read;
- `archive_versions` — historical versions read;
- `archive_pdf` — разрешённый PDF/export, не каждый внутренний `get_report`;
- `archive_missing` — авторизованный profile-scoped archive lookup без legacy row;
- `target_grandfathered_access` — target Career operation допущена direct Career grant.

No report/profile/user IDs, payloads, birth fields, names, email, URL parameters или free-form exception messages в новых event/metric attributes. Unknown operation не записывается. Внутренний PDF lookup не должен увеличивать user-facing archive JSON reads; отказ не должен считаться успешным чтением.

Базовый readback после exporter проверки:

```promql
sum by (operation) (legacy_career_operations_total)
```

Grafana template для **отдельно согласованного** observation range:

```promql
sum by (operation) (increase(legacy_career_operations_total[$__range]))
```

Это dashboard template с Grafana substitution, не готовая команда с утверждённой длительностью. Для eligibility отдельно проверить resets, scrape gaps и все consumer instances. Отсутствующая series, stale collector или неполное окно — unknown, не ноль использования. Counter increases за частичное окно и source-level name tests не считаются live dashboard evidence.

## Stage matrix после восстановления

- Active Plus и active direct Career grant: target questionnaire → generation/status → report/versions/PDF, без generic payload fallback.
- Expired/revoked/future grant: honest locked response; чужие/nonexistent artifacts не раскрываются.
- Owned existing legacy row: read-only archive + generic PDF + CTA в target.
- Owned missing legacy row: target CTA с корректным profile context; нет автоматического create.
- Career v1 generic generation/interpretation/narrative retry: retirement response; before/after fresh-session DB equality.
- Queued pre-retirement narrative messages/finalization: нет изменения исторического артефакта.
- Shared Self: прежняя generation/narrative/PDF цепочка.
- Проверить новый profile list filter до pagination: более 100 reports других профилей не скрывают нужный архив.

## Observation/removal decision — пока не разрешён

Перед будущим предложением физического удаления потребуются:

1. Проверенный production/restored census и отдельные counts rows/owners/grants, с execution record и trusted source.
2. Inventory внешних API clients, bookmarks, admin/support consumers и всех реально выполняемых rules/report workers.
3. Заранее утверждённые длительность, UTC start/due/end, нагрузка, учёт reset/gaps и zero/acceptable-use threshold. Численные значения сейчас **не утверждены**, не выбираются агентом ради PASS.
4. Реальный full-window read/PDF/blocked-write/grandfathered-access readback. Ни один unknown consumer или telemetry gap не трактуется как отсутствие использования.
5. Отдельное customer-support/retention решение: retain/export/explicit migration/later deletion и судьба grants, не смешанная с судьбой report rows.
6. Независимая backup/restore rehearsal и проверенный rollback.
7. Явное owner approval на конкретные endpoints/rules/rows и scope. Одного флага `approved=true` без identity/evidence недостаточно.

Пока хотя бы один пункт отсутствует: **не удалять compatibility endpoints, rules, report/version/narrative rows или grandfathered entitlements**. Удаление данных не является частью текущего implementation scope.

## Rollback

На восстановленной среде отдельно подготовить и согласовать previous code/images/config identity, baseline row hashes и smoke matrix. Code rollback может вернуть старые writers, поэтому это осознанное изменение поведения, не безопасная автоматическая реакция на ошибку чтения. Routing/client rollback не должен конвертировать новые target artifacts в legacy или менять grants. Наличие плана не считается выполненным rollback drill; stage/production rehearsal и observation в S07 остаются открытыми.
