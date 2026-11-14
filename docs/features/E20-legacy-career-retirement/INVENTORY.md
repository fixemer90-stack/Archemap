# E20: source inventory и границы census

## Статус и доказательства

Source inventory выполнен на canonical checkout после baseline `45c2521`. Mounted generic reports inventory находится в `backend/app/modules/reports/access.py`; реализация router/service и прямые consumers проверены отдельно, а не только по decorator metadata. Это source inventory, не инвентаризация уничтоженного сервера и не измерение внешних клиентов.

Production census: **недоступен** — владелец сообщил об утрате сервера после кибератаки. Число потерянных/сохранившихся rows, owners, grants, старых ссылок и usage неизвестно. Ноль вместо отсутствующих результатов не подставляется. Ни один старый VPS/production DB не опрашивался.

## Три разных значения Career

| Контур                    | Хранилище и API                                                                | Политика E20                                                          |
| ------------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------- |
| Target E19                | `career_*`, `/api/v1/career/*`, `/products/career`                             | Единственный поддерживаемый новый Career report lifecycle             |
| Grandfathered entitlement | `entitlements.product="career"`, canonical `LEGACY_CAREER_ENTITLEMENT_PRODUCT` | Сохранить scoped доступ к target независимо от legacy row             |
| Legacy Career artifact    | `reports.product="career"`, связанные `report_versions`/сохранённые narratives | Не создавать/обновлять; оставить защищённые historical JSON/PDF reads |

## Generic reports: исчерпывающий mounted inventory

Путь `/api` добавляется внешним routing layer; executable app contract использует `/v1/reports`.

| Method/path                                  | Класс                              | Call graph / опасность до retirement                                                                                                                                    | Требуемая граница                                                                   |
| -------------------------------------------- | ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| POST `/v1/reports/generate`                  | Writer                             | Router → profile ownership/access → `ReportService.generate_report` → existing lookup/archive/version/status → chart → rules → persisted JSON → Self narrative dispatch | Career: стабильный 410 до report lookup/mutation/engine/dispatch; Self сохраняется  |
| GET `/v1/reports`                            | Reader                             | Router → SQL access-product filter → `list_reports` → saved narrative serializer                                                                                        | Career: owned permitted historical rows, без generation                             |
| GET `/v1/reports/{id}`                       | Reader с прежним скрытым writer    | Metadata ownership/access → `get_report` → `_report_requires_refresh` → `generate_report`; затем Self narrative ensure                                                  | Career: запрет refresh до проверки engine/source, сохранение status/version/payload |
| POST `/v1/reports/{id}/narrative/regenerate` | Writer                             | Metadata ownership/access → `get_report` (прежде мог refresh) → async enqueue/status                                                                                    | Career: 410 до payload refresh/dispatch/status changes                              |
| HEAD `/v1/reports/{id}/pdf`                  | Reader с прежним скрытым writer    | Access → `_get_report_pdf_headers` → `get_report`                                                                                                                       | Career: headers/availability из saved row, без refresh/PDF body                     |
| GET `/v1/reports/{id}/pdf`                   | Reader с прежним скрытым writer    | Headers → `get_report` → saved narrative → on-demand renderer                                                                                                           | Career: immutable JSON-to-PDF, no storage/upload/recompute                          |
| POST `/v1/reports/{id}/pdf`                  | Export alias, не generation writer | `_render_report_pdf`, как GET                                                                                                                                           | Сохранить только read-only export semantics                                         |
| GET `/v1/reports/{id}/versions`              | Reader с прежним скрытым writer    | `get_versions` → `get_report` → versions query                                                                                                                          | Career: history read без refresh/archive/version increment                          |
| GET `/v1/reports/{id}/versions/{version}`    | Reader с прежним скрытым writer    | `get_version` → `get_report` → exact version                                                                                                                            | Career: ownership-protected saved snapshot                                          |

Read-only не означает обход entitlement policy. Сохраняются существующие authentication, minimal ownership metadata и access gates до protected payload; E20 не расширяет доступ expired/revoked пользователям и не даёт entitlement по наличию row.

## Другие backend consumers

| Consumer                                                                      | Класс                                                             | Решение                                                                                                                     |
| ----------------------------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| `ReportService.generate_report`                                               | Прямой writer, callable без router                                | Defense-in-depth retirement guard до `_find_existing`, flush или engine                                                     |
| `ReportService._archive_version`                                              | Внутренний version writer                                         | Не должен выполняться для Career даже через прямой вызов/случайный refresh                                                  |
| `ReportService._report_requires_refresh`                                      | Источник скрытого regenerate на чтении                            | Career исключается из refresh; Self сохраняет cache/source logic                                                            |
| `ReportNarrativeService.generate_for_report`                                  | Прямой/queued writer, provider/cache/status mutation              | Career retired до mutation/provider work                                                                                    |
| `workers.tasks.reports.generate_report_narrative` → `report_narratives.tasks` | Отложенные сообщения и retries                                    | Отказ без повторного provider dispatch или mutation исторической row                                                        |
| `finalize_narrative_task_failure` / async finalizer                           | Скрытый terminal status writer после exception                    | Retirement error не разрешает overwrite Career report/narrative status                                                      |
| `reports.generate_pdf` → `reports.tasks._generate_pdf_async`                  | Compatibility export из saved row                                 | Оставить immutable render, не создавать narrative/artifact storage                                                          |
| POST `/v1/rules/interpret` → `RulesService.interpret_chart`                   | Публичное создание нового Career v1 claims payload без Report row | Обнаруженный дополнительный generation bypass: Career-only retirement guard; прочие products/чистые engine helpers остаются |
| GET `/v1/rules/rulesets`, `load_ruleset`, golden/unit engine fixtures         | Rules catalog / чистое вычислительное API в коде                  | Не удалять Career ruleset глобально; прекращение report generation не доказывает отсутствие всех consumers                  |
| Target Career `generation/status/sections/versions/PDF`                       | E19 lifecycle                                                     | Не читать generic payload/ID как fallback; grants проверять независимо                                                      |
| Auth/profile/account deletion lifecycle                                       | Shared platform                                                   | Не изменяется E20; никакой новой deletion/migration Career data                                                             |

Поиск runtime callers в `backend/app` и `backend/workers` не выявил отдельного generic Career scheduler/monitor generation path. Это не доказательство отсутствия старых broker messages, незарегистрированных внешних integrations или ad-hoc operator scripts.

## Frontend consumers

| Consumer                                               | Текущее/целевое поведение                                                                                                                           |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| `components/layout/sidebar.tsx`, dashboard Career card | Уже ведут в `/products/career`; сохранить target-only navigation                                                                                    |
| `components/report/career-cta.tsx`                     | Target Career с encoded `profileId`, не generic report generation                                                                                   |
| `products/career/page.tsx` и target report route       | E19 client/DTO/API, не смешивать с архивом                                                                                                          |
| `/report/{profileId}?product=career`                   | Исторический reader; archive notice + target CTA + generic PDF; no-row не создаёт отчёт                                                             |
| `lib/api/report.ts::fetchReportApiData`                | До E20 любой product вызывал POST `/profiles/{id}/chart`; для Career archive этот side effect убирается, расчётный display берётся из saved payload |
| `generateReportForProfile`                             | Self consumer остаётся; Career convenience call не должен создавать legacy result                                                                   |
| Generic reader polling/retry                           | Self lifecycle сохраняется; historical Career nonterminal status не является разрешением generation/retry                                           |
| Legacy bookmarks/API clients/admin tools               | Полный runtime список неизвестен; закрывается telemetry/наблюдением после восстановления, не grep                                                   |

## Census tool и проверка безопасности

`backend/scripts/legacy_career_census.py` принимает только явно выбранную переменную `E20_CENSUS_DATABASE_URL` с `postgresql+asyncpg` URL. Application `.env`/`app.config` не импортируются. Перед единственным aggregate SELECT устанавливаются и проверяются `REPEATABLE READ` и `READ ONLY`, ограничен statement timeout; активная caller transaction не принимается.

Output содержит только aggregate report rows/owners/status/version distributions, отдельные counts Career entitlements/current direct grants и owner overlap. `report_data`, email, имена, birth data и идентификаторы не выбираются. Нестандартные status значения сводятся в `other`, а usage честно `available=false / requires_observation_telemetry`. Это snapshot выбранного соединения, не автоматическое доказательство environment identity или достаточности removal gate.

Проверки родительского агента:

- RED: **8 failed**, census module отсутствовал.
- Первоначальный GREEN: **8 unit tests** и **2 PostgreSQL integration tests** — **10 passed**. PostgreSQL действительно отклонил намеренно подменённый mutating query с SQLSTATE `25006`, а row count остался неизменным.
- Независимый spec reviewer обнаружил расхождение census с canonical access для пустого массива metadata. Добавлена real-PostgreSQL matrix для всех falsy JSON roots (`[]`, `false`, `0`, пустая строка, `{}`, `null`) с сопоставлением реального `EntitlementsService`: RED **4 failed / 2 passed**, после изменения SQL — весь census suite **16 passed** (8 unit + 8 integration). Existing nonempty-array exclusion и все исходные before/after/read-only проверки сохранены.
- Второй spec finding (raw JSON numeric underflow) воспроизведён в PostgreSQL для root и `subscription_id`: **12 failed / 6 passed**. SQL теперь учитывает binary64 rounding-to-zero по точной `numeric` границе; новые fixtures читают actual database-decoded metadata, а не повторно сериализованный float. Полный census suite: **34 passed** (8 unit + 26 integration); independent SPEC re-review `deleg_fe8fe02d` — source PASS, без independent PostgreSQL execution. Code/security `deleg_4751131c` — scoped PASS; это не approval backend runtime или removal. Unsupported conversion приводит к безопасной ошибке, не к частичным/нулевым counts.
- Отдельный CLI запуск на явно synthetic fixture в owned disposable PostgreSQL завершился `exit 0`; counts проверены без переноса synthetic чисел в production evidence.
- Ruff/format и scoped mypy для трёх файлов — PASS. Scoped mypy сообщает только unused-config-section note.
- Disposable `archemap-e20-census-test` удалён; отсутствие проверено через `docker ps -a --filter name=archemap-e20-census-test`.

## Неизмеренные production/retention gates

- Существующий production/restored-data census и целостность восстановленных источников — не подтверждены.
- Фактические legacy read/PDF/write events до установки telemetry — неизвестны.
- Внешние clients/bookmarks/support/admin operations — требуют отдельного inventory и observation.
- Default strategy E20: **retain**, без переноса payload, удаления row, удаления endpoint/rules или отзыва grant.
- Window, допустимый usage threshold и destructive removal approval владельцем не определены; их нельзя придумать ради закрытия Story.
- До будущего удаления нужны независимо проверенные census, retention/support decision, backup/restore rehearsal и явное отдельное разрешение.

Родительская E20 и production-зависимые критерии S01/S06/S07 остаются открытыми. Предыдущее разрешение закрыть #51 без rollout не переносится автоматически на Feature E20.
