# S14: Публикация Career на stage и сбор live evidence

## Статус

✅ Завершено — stage publication, browser/entitlement matrix, mock flow, dashboards, observability и rollback подтверждены

## Контекст

Локальная реализация Career, API, reader/PDF и mocked Playwright browser suite подготовлены, но этого недостаточно для закрытия E19. Текущий stage не доказывает целевой пользовательский поток с реальным backend, entitlement policy, worker, mock LLM runtime и наблюдаемостью.

Runtime-аудит 25 сентября 2026 года показал:

- `CAREER_REPORT_ENABLED=True`, но target Career routes в запущенном backend не обнаружены;
- `LLM_PROVIDER=mock` и `LLM_ENABLED=False`;
- OTLP metrics endpoint не настроен;
- в `career_generations` нет live generation;
- текущие Playwright Career tests используют mocked API и ещё не закреплены точным зелёным CI SHA.

Поэтому для завершения S10/S12 и Feature требуется отдельная публикация на stage, а не только локальный прогон тестов.

## Цель

Опубликовать точный зелёный Career revision на изолированный stage, выполнить полный live flow и сохранить проверяемое evidence для entitlement, mock-provider narrative, reader/PDF, observability и rollback. По решению владельца продукта от 27 сентября 2026 года real provider для stage не требуется. Production Career rollout в эту Story не входит, но production health после изменения общего ingress обязан остаться зелёным.

## Что сделать

### 1. Закрепить публикуемый revision

1. Добавить в Git текущие Playwright tests, visual baselines, Playwright config, CI browser-smoke job, env/Compose contract и связанные UI/docs изменения.
2. Запустить repo-wide backend/frontend/docs проверки после последнего edit.
3. Commit и push выполнить одним идентифицируемым набором или последовательностью логических commits.
4. Дождаться завершения CI для точного финального SHA; проверить conclusions всех jobs, включая Career browser smoke.
5. Записать SHA и CI run URL в эту Story до deploy.

### 2. Подготовить безопасную публикацию на stage

1. Зафиксировать текущий stage deploy marker, Compose services и health.
2. Создать restorable dump stage PostgreSQL и проверить ненулевой размер/checksum.
3. Снять pre-migration row counts/checksums для `person_profiles`, legacy `reports`, `payments` и `entitlements`.
4. Убедиться, что `.env.staging` использует только stage/test credentials и отдельные PostgreSQL/Redis volumes.
5. Проверить staging и production Compose/Caddy contracts до изменения runtime.

### 3. Опубликовать Career runtime на stage

1. Развернуть на `/opt/astrotype` точный чистый Git SHA без копирования локального dirty worktree.
2. Пересобрать и перезапустить stage `backend`, `worker` и `frontend`; gateway менять только при необходимости.
3. Дождаться PostgreSQL/Redis/backend/worker/frontend readiness.
4. Проверить migration head и повторить legacy row counts/checksums; значения должны совпасть с preflight.
5. Записать staging-specific deploy marker только после успешного Compose update.
6. Проверить, что target `/api/v1/career/*` routes присутствуют в реально запущенном backend.
7. Включить на stage:
   - `CAREER_REPORT_ENABLED=true`;
   - `LLM_PROVIDER=mock` и включённый mock LLM runtime;
   - mock-safe cost settings; реальные provider rates не считаются stage evidence;
   - OTLP metrics endpoint и stage service name.
8. Не переносить эти настройки и credentials в production автоматически.

### 4. Выполнить live entitlement matrix

Проверить через реальный backend и браузер:

- active Plus: questionnaire и target generation доступны;
- grandfathered legacy Career: target flow доступен, старый legacy reader/PDF продолжает открываться;
- locked/expired: create/status/read/sections/regenerate/PDF не возвращают protected payload;
- feature flag off: новые target writes блокируются, существующие target и legacy artifacts сохраняются;
- повторный completion/retry не создаёт дубликат generation.

### 5. Выполнить полный stage flow

1. Открыть `/products/career` под active Plus account.
2. Пройти questionnaire, включая autosave/resume и consent.
3. Записать questionnaire response/version и idempotency evidence без персонального payload.
4. Создать generation и записать `generation_id`.
5. Доказать переходы `queued/calculating → deterministic_ready → generating_sections → ready`.
6. Открыть progressive reader на `deterministic_ready` до готовности всех narrative sections.
7. Дождаться mock-provider narrative и записать `report_id`.
8. Скачать backend PDF, проверить HTTP 200, `%PDF`, ненулевой размер и одинаковый порядок секций с web reader.
9. Выполнить isolated retry одной failed section либо управляемый provider-failure smoke и доказать сохранность deterministic content.

### 6. Провести human quality review

Сравнить live report с design-документом и canonical sample:

- структура и claims привязаны к evidence contract;
- contradictions сохранены;
- low-confidence выводы сформулированы условно;
- нет диагноза, гарантированных исходов и назначения профессии;
- профессии показаны только как примеры классов ролей;
- секции не дублируют друг друга;
- web и PDF читаемы на desktop/mobile/print.

Результат review записать в Story с redacted report ID и перечнем найденных/исправленных замечаний.

### 7. Собрать observability evidence

1. Записать dashboard links для latency, failures/retries, stuck generations, validator failures, token estimate и estimated cost.
2. Сравнить значения с бюджетами из S13.
3. Выдержать полный observation window без stuck generation и access leak.
4. Проверить alert path управляемым безопасным событием либо зафиксированным test signal.
5. Не сохранять ответы, UUID, prompt или report payload в metric labels/log evidence.

### 8. Выполнить rollback rehearsal

1. Установить `CAREER_REPORT_ENABLED=false` на stage и перезапустить API/worker.
2. Доказать, что новые generation не создаются.
3. Доказать, что созданные target rows и legacy reports/PDF не удалены и не изменены.
4. Вернуть feature flag в согласованное stage-состояние.
5. Записать команды, timestamps, deploy marker и результаты readback.

### 9. Закрыть документацию

После получения evidence:

- закрыть live-backend criterion в S10;
- записать stage report/PDF IDs, human review, metrics и observation window в S12;
- отметить выполненные шаги runbook S13;
- обновить статус S14;
- оставить production report/PDF criterion S12 открытым до отдельной production публикации;
- синхронизировать статус и Story table в `FEATURE.md`.

## Критерии приёмки

- [x] Текущий Career browser-smoke набор закоммичен и имеет точный зелёный CI SHA.
- [x] На stage опубликован именно этот SHA; marker прочитан обратно из runtime.
- [x] Stage backup/checksum и pre/post legacy row evidence сохранены.
- [x] Backend, worker и frontend stage запущены с target Career revision; health/readiness зелёные.
- [x] Target Career routes и актуальный migration head подтверждены в running containers.
- [x] Mock LLM runtime и OTLP включены на stage; production configuration не изменена.
- [x] Active Plus, grandfathered legacy и locked/expired matrix пройдена через live backend.
- [x] Полный questionnaire → deterministic → narrative → reader/PDF flow пройден; generation/report/PDF IDs записаны с редактированием персональных данных.
- [x] Human quality review пройден относительно design и canonical sample.
- [x] Latency/token/cost dashboards и zero-stuck observation window записаны.
- [x] Rollback flag rehearsal подтверждает отсутствие новых writes и сохранность target/legacy artifacts.
- [x] Staging без Basic Auth возвращает 401, с Basic Auth health возвращает 200 и `X-Robots-Tag: noindex, nofollow, noarchive`.
- [x] Production health/frontend после stage publication остаются HTTP 200.
- [x] S10/S12/S13 и `FEATURE.md` синхронизированы с фактическим evidence.

## Evidence template

```text
Git SHA:
CI run URL / job conclusions:
Stage deploy marker:
Backup path / SHA-256:
Pre/post legacy counts and checksums:
Migration head:
Stage services/readiness:
Career route proof:
Entitlement matrix:
Generation ID:
Report ID:
PDF proof:
Human review result:
Dashboard links:
Observation window:
Rollback rehearsal:
Production regression health:
```

## Historical snapshot 2026-09-26

- Git SHA: `a821404d0b010fc9f1f1cd04d01170a825dc29b8`.
- CI: `https://github.com/fixemer90-stack/Archemap/actions/runs/36210137484`; семь jobs завершены `success`, включая `Test & Build Frontend` с Career Playwright smoke.
- Текущий stage marker: `3462865ed1a7158023c99bc491044dcea048ad23` — не совпадает с target SHA.
- Stage containers запущены, backend healthy, migration current/head `a6b7c8d9e0f1`, но `/api/v1/career/*` routes в running backend отсутствуют.
- Stage safe settings: `CAREER_REPORT_ENABLED=true`, `LLM_ENABLED=false`, `LLM_PROVIDER=mock`, OTLP endpoint пуст.
- Stage DB readback: `career_generations=2`, `career_reports=0`, `career_questionnaire_sessions=1`; сохранённого полного report/PDF evidence нет.
- Career preflight dump в `/opt/astrotype` не найден; pre/post checksums и restore evidence отсутствуют.
- Без Basic Auth stage health возвращает `401` и `X-Robots-Tag: noindex, nofollow, noarchive`; authenticated `200` в этом аудите не подтверждён.
- Production `/api/v1/health` после read-only stage audit возвращает `200`; это не заменяет regression smoke после будущей target stage publication.
- Deploy topology пока не запускает Celery Beat, поэтому zero-stuck/alert-path evidence заблокировано implementation/config gap.

## Решение по provider gate 2026-09-27

Владелец продукта подтвердил, что для stage достаточно mock LLM. Исторические требования real-provider stage report/API key сняты. Real-provider prose quality, authoritative latency/token/cost и provider billing evidence переносятся в canary/pre-production gate S12. Scheduler implementation gap закрыт после исторического snapshot; S14 должен доказать уже запущенный stage Beat service и alert path.

Exact green Career revision для публикации: `3fbd11948a9676d440915cd5abcd50dbbf7aa3c5`; GitHub Actions CI run `36285160532`, все семь jobs `success`, включая Career Chromium browser smoke.

## Stage publication evidence 2026-09-27

- Git SHA: `20dcfbfce5ed1e2cb540261e4a1223683b89d7a7`.
- CI: run `36308536986`, семь jobs `success`.
- Stage deploy marker совпадает с Git SHA; migration current/head `b7c8d9e0f1a2`.
- Runtime: `CAREER_REPORT_ENABLED=true`, `LLM_ENABLED=true`, `LLM_PROVIDER=mock`; backend, worker, singleton scheduler, frontend и OTEL collector запущены.
- Live OpenAPI содержит все 10 Career routes.
- Backup: `/opt/astrotype/backups/career-preflight-20260927T022749Z.dump`, `291542` bytes, SHA-256 `1c3ef7d540927a313475d55e708722f1ac77c4428477381b1ac38ca4fd710e49`; restore в отдельную временную БД успешен.
- Pre/post protected-table counts/checksums совпали: profiles `6`, legacy reports `0`, payments `1`, entitlements `1`.
- Active Plus flow завершён; grandfathered Career questionnaire разрешён; duplicate create с одинаковым idempotency key вернул тот же generation.
- Locked create/generation/read/sections/regenerate/PDF вернули `402` без protected payload.
- Expired probe не засчитан: он менял `plus/career`, а канонический Plus product — `self`; smoke-entitlements восстановлены.
- Generation `d98e0b57-b67c-4b1b-8f8b-54c87b4eef4e`, report `c84bfae8-6ed3-4a92-b841-733cbf0c59fb`, version `6`, `10/10` sections ready.
- PDF: `32760` bytes, SHA-256 `1e48f17ba7e7475a3e4e261fecbe7d24aaa3760ec6de3fd05f18fc1d6b8e4c0d`.
- Human structural review: canonical section order, claims/citations and assembled payload присутствуют; exact duplicates, diagnosis, guaranteed outcomes и prescribed profession отсутствуют.
- Generation duration `1.892 s`; estimated mock usage `23066` input / `9063` output tokens; configured cost `$0`.
- OTLP endpoint `http://otel-collector:4318/v1/metrics`; collector принял 16 Career metric batches.
- Observation window: четыре запуска monitor, stuck deterministic `0`, stuck narrative `0`, validator failures `0`, alerts `[]`.
- Historical stage publication не включала dashboard; gap закрыт отдельной публикацией 29 сентября 2026 года.
- Rollback rehearsal: feature off блокирует новый create с `404`, существующий report остаётся `200`, counts generations/reports/segments/legacy `7/4/40/0` не изменились; flag возвращён в `true`.
- Stage health: unauthenticated `401`, authenticated `200`, noindex header присутствует.
- Production non-regression после stage publication: API health `200`, frontend `200`.
- Combined live browser smoke с deployed backend не записан; backend flow и mocked Chromium CI являются отдельными evidence.

## Additional live evidence 2026-09-28

- Correct expired matrix временно истекла все три активных target grants `self`, `plus`, `career`: create/generation/read/sections/regenerate/PDF вернули `402`, protected payload отсутствовал. Все три entitlement восстановлены в `active` с исходным бессрочным сроком.
- Active `self` Chromium flow: page `200`, create `202`, generation `58673ea9-08ee-40e5-93d9-3d887d194e11`, reader report `241306e3-d334-4fdb-87a4-ce816d88f71f` HTTP `200`, PDF `200` / `32760` bytes / `%PDF`.
- Grandfathered `career` Chromium flow: page `200`, create `202`, generation `08d6b11c-2fc7-44bf-b1c0-928ca21c3674`, reader report `b3de9e3e-6831-4964-b1f8-42c9b04af3c0` HTTP `200`, PDF `200` / `32617` bytes / `%PDF`.
- Оба browser flows завершились без failed Career/API responses и page errors.
- После этого browser/entitlement gates закрыты; оставшийся dashboard gap закрыт evidence ниже.

## Metrics dashboard evidence 2026-09-29

- Dashboard revision: `4c1423ccd10a9b4d1cf9a95fac5885dbde75e73a`; stage marker прочитан обратно и совпал.
- Exact-SHA CI run `36510730869`: семь jobs завершены `success`; Build & Push Images run `36510730883` также `success`.
- Basic Auth boundary: `/career-metrics` без credentials → `401`, с credentials → `308` на `/career-metrics/`; `/career-metrics/` без credentials → `401`; `/career-metrics/targets` с credentials → `200`.
- Dashboard links: `https://staging.astrotype.ru/career-metrics/graph` и `https://staging.astrotype.ru/career-metrics/targets`.
- Prometheus target `http://otel-collector:9464/metrics` имеет health `up`, `lastError` пуст.
- Live series: `career_operations_total` — 14; `career_operation_duration_seconds_count` — 2; `career_provider_tokens_token_total` — 2 (`144297`, `52443`); `career_provider_cost_usd_USD_count` — 1 (`60`). Prometheus exporter добавляет unit к исходным token/cost instrument names.
- После публикации production API health и frontend повторно вернули HTTP `200`.

## Вне области Story

- включение Career для production пользователей;
- production Career report/PDF smoke;
- отключение legacy Career generation в production;
- расширение Career beyond MVP dimensions/questions.
