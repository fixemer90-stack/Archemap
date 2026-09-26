# S14: Публикация Career на stage и сбор live evidence

## Статус

🟡 В работе — exact green revision закреплён; stage publication и live evidence не выполнены

## Контекст

Локальная реализация Career, API, reader/PDF и mocked Playwright browser suite подготовлены, но этого недостаточно для закрытия E19. Текущий stage не доказывает целевой пользовательский поток с реальным backend, entitlement policy, worker, LLM provider и наблюдаемостью.

Runtime-аудит 25 сентября 2026 года показал:

- `CAREER_REPORT_ENABLED=True`, но target Career routes в запущенном backend не обнаружены;
- `LLM_PROVIDER=mock` и `LLM_ENABLED=False`;
- OTLP metrics endpoint не настроен;
- в `career_generations` нет live generation;
- текущие Playwright Career tests используют mocked API и ещё не закреплены точным зелёным CI SHA.

Поэтому для завершения S10/S12 и Feature требуется отдельная публикация на stage, а не только локальный прогон тестов.

## Цель

Опубликовать точный зелёный Career revision на изолированный stage, выполнить полный live flow и сохранить проверяемое evidence для entitlement, real-provider narrative, reader/PDF, observability и rollback. Production Career rollout в эту Story не входит, но production health после изменения общего ingress обязан остаться зелёным.

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
   - real LLM provider и stage API key;
   - актуальные provider cost rates;
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
7. Дождаться real-provider narrative и записать `report_id`.
8. Скачать backend PDF, проверить HTTP 200, `%PDF`, ненулевой размер и одинаковый порядок секций с web reader.
9. Выполнить isolated retry одной failed section либо управляемый provider-failure smoke и доказать сохранность deterministic content.

### 6. Провести human quality review

Сравнить live report с design-документом и canonical sample:

- выводы специфичны и привязаны к evidence;
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
- [ ] На stage опубликован именно этот SHA; marker прочитан обратно из runtime.
- [ ] Stage backup/checksum и pre/post legacy row evidence сохранены.
- [ ] Backend, worker и frontend stage запущены с target Career revision; health/readiness зелёные.
- [ ] Target Career routes и актуальный migration head подтверждены в running containers.
- [ ] Real provider и OTLP включены только на stage; production configuration не изменена.
- [ ] Active Plus, grandfathered legacy и locked/expired matrix пройдена через live backend.
- [ ] Полный questionnaire → deterministic → narrative → reader/PDF flow пройден; generation/report/PDF IDs записаны с редактированием персональных данных.
- [ ] Human quality review пройден относительно design и canonical sample.
- [ ] Latency/token/cost dashboards и zero-stuck observation window записаны.
- [ ] Rollback flag rehearsal подтверждает отсутствие новых writes и сохранность target/legacy artifacts.
- [ ] Staging без Basic Auth возвращает 401, с Basic Auth health возвращает 200 и `X-Robots-Tag: noindex, nofollow, noarchive`.
- [ ] Production health/frontend после stage publication остаются HTTP 200.
- [ ] S10/S12/S13 и `FEATURE.md` синхронизированы с фактическим evidence.

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

## Evidence 2026-09-26

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

## Вне области Story

- включение Career для production пользователей;
- production Career report/PDF smoke;
- отключение legacy Career generation в production;
- расширение Career beyond MVP dimensions/questions.
