# Story E12.S05: Local runbook — start, logs, smoke flow

**Feature:** [LLM Report Runtime Readiness](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

После S01-S04 уже понятно, какие runtime-компоненты обязательны, как устроен worker, какие есть LLM режимы и почему PDF зависит от bucket bootstrap. Но новому участнику команды всё ещё нужен один последовательный операторский runbook: что именно подготовить, как поднять стек, где смотреть логи и как пройти mock / real / fallback smoke path без reverse engineering по исходникам.

## Что было проверено

Проверены и сведены в один operational flow следующие источники истины:

- `docs/features/E12-llm-report-runtime-readiness/S01-runtime-inventory-gap-analysis.md`
- `docs/features/E12-llm-report-runtime-readiness/S02-dev-orchestration-worker-runtime.md`
- `docs/features/E12-llm-report-runtime-readiness/S03-llm-environment-contract.md`
- `docs/features/E12-llm-report-runtime-readiness/S04-object-storage-pdf-bootstrap.md`
- `docker-compose.yml`
- `.env.example`
- `backend/app/main.py`
- `backend/app/api/v1/health.py`
- `backend/app/modules/auth/router.py`
- `backend/app/modules/auth/service.py`
- `backend/app/modules/profiles/router.py`
- `backend/app/modules/profiles/schemas.py`
- `backend/app/modules/reports/router.py`
- `backend/app/modules/reports/schemas.py`
- `backend/app/modules/reports/tasks.py`
- `backend/app/modules/report_narratives/service.py`
- `backend/app/modules/reports/storage.py`

## Для кого этот runbook

Этот runbook рассчитан на локальный/dev запуск E11/E12 через Docker Compose.

Цель runbook:

1. поднять narrative-ready stack;
2. проверить health и логи;
3. подготовить verified user + profile;
4. пройти generate -> polling -> ready/fallback;
5. проверить regenerate;
6. проверить PDF artifact path.

## Важные ограничения runbook

1. В текущем коде reports API требует авторизованного и **verified** пользователя.
2. `POST /api/v1/auth/register` не даёт готовый access token для smoke; после него нужно подтвердить email и только потом логиниться.
3. В текущем коде real provider path поддержан только через `openrouter`.
4. Bucket для PDF **не создаётся автоматически**. Его нужно bootstrap'ить отдельно до PDF smoke.
5. Команды ниже не только выведены из кода, но и дополнительно сверены живым compose smoke в этой WSL-сессии для controlled fallback path.

## 1. Минимальный narrative-ready stack

Должны быть доступны:

- `postgres`
- `redis`
- `minio`
- `backend`
- `frontend`
- `worker`

Worker обязателен, потому что именно он исполняет:

- `reports.generate_report_narrative`
- `reports.generate_pdf`

## 2. Подготовка env

### 2.1 Базовый `.env`

Для compose-based runbook нужен repo-root `.env` рядом с `docker-compose.yml`.

Если файла нет:

```bash
cp .env.example .env
```

Базовые storage/database defaults уже есть в `.env.example`.

### 2.2 Добавить LLM variables

В `.env.example` сейчас нет narrative LLM блока, поэтому для E12 smoke его нужно дописать в `.env` явно.

### Mock smoke path

```env
LLM_ENABLED=true
LLM_PROVIDER=mock
LLM_MODEL=mock-self-v1
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

### Real provider path

```env
LLM_ENABLED=true
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4.1-mini
LLM_API_KEY=or-v1-...
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

### Controlled fallback path

```env
LLM_ENABLED=false
LLM_PROVIDER=mock
LLM_MODEL=mock-self-v1
LLM_API_KEY=
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=2
```

Принцип:
- `LLM_ENABLED=false` -> deterministic fallback path;
- `LLM_ENABLED=true + LLM_PROVIDER=mock` -> pipeline smoke без network calls;
- `LLM_ENABLED=true + LLM_PROVIDER=openrouter` -> реальный внешний LLM path.

## 3. Поднять стек

Основная команда:

```bash
docker compose up -d postgres redis minio backend frontend worker
```

Legacy-вариант, если окружение использует старую обёртку:

```bash
docker-compose up -d postgres redis minio backend frontend worker
```

## 4. Проверка health после старта

### 4.1 Backend health

```bash
curl -s http://localhost:8000/api/v1/health
```

Ожидаемый минимум:

```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok"
}
```

`status=degraded` означает, что backend поднялся, но DB/Redis недоступны корректно.

### 4.2 Secrets/config sanity check

Для dev/staging можно проверить:

```bash
curl -s http://localhost:8000/api/v1/health/secrets
```

Этот endpoint полезен, чтобы быстро увидеть missing secrets/config blocks в development.

### 4.3 Worker/log readiness

Главные команды наблюдения:

```bash
docker compose logs -f backend worker
```

При проблемах storage/broker дополнительно:

```bash
docker compose logs -f minio redis
```

Практические признаки readiness:

- backend отвечает на `/api/v1/health`;
- worker не завершается сразу после старта;
- backend и worker используют согласованные env для Redis/S3/LLM.

## 5. Bucket bootstrap до первого PDF smoke

### 5.1 Почему этот шаг обязателен

В текущем runtime path `S3Storage.ensure_bucket()` существует, но не вызывается автоматически ни backend startup'ом, ни worker startup'ом, ни `generate_pdf_task()`.

Значит, bucket нужно гарантировать отдельно до первого PDF upload.

### 5.2 Bucket name в текущем dev stack

По текущему compose/env contract bucket должен быть:

```text
astrotype
```

### 5.3 Рекомендуемый bootstrap через backend container

После старта compose можно выполнить:

```bash
docker compose exec backend python - <<'PY'
from app.modules.reports.storage import S3Storage
S3Storage().ensure_bucket()
print('bucket ensured')
PY
```

Что это делает:
- использует тот же runtime config, что и сам backend/worker;
- не требует внешнего `aws`/`mc` CLI;
- создаёт bucket, если его ещё нет.

### 5.4 Что считать успехом

Успех bucket bootstrap = команда завершается без исключения, после чего PDF task может писать в `S3_BUCKET_NAME`.

## 6. Auth и profile prerequisites

Для reports API нужен verified user.

### 6.1 Самый быстрый путь для smoke

Использовать уже существующего verified пользователя и его profile.

### 6.2 Если verified user уже есть — логин

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "user@example.com",
    "password": "your-password"
  }'
```

Ожидаемый результат:
- `access_token`
- `refresh_token`
- `token_type=bearer`

Сохранить access token в переменную:

```bash
export ACCESS_TOKEN='<paste-access-token>'
```

Проверка токена:

```bash
curl -s http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 6.3 Если verified user ещё нет

1. Зарегистрировать пользователя:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "user@example.com",
    "password": "strongpassword",
    "name": "Smoke User",
    "birth_date": "1990-08-24",
    "birth_time": "11:00:00",
    "birth_time_accuracy": "exact",
    "birth_place": "Moscow",
    "latitude": 55.7558,
    "longitude": 37.6173,
    "timezone": "Europe/Moscow"
  }'
```

2. Подтвердить email через token из письма:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/verify \
  -H 'Content-Type: application/json' \
  -d '{"token": "<token-from-email>"}'
```

3. После этого выполнить `/auth/login` и получить `ACCESS_TOKEN`.

Примечание:
- registration path сам создаёт profile и chart snapshot;
- если этот путь использован успешно, `profile_id` уже вернётся в register response.

### 6.4 Получить profile_id

Если profile уже есть:

```bash
curl -s http://localhost:8000/api/v1/profiles \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Если профиля ещё нет, создать его:

```bash
curl -s -X POST http://localhost:8000/api/v1/profiles \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "name": "Smoke Profile",
    "birth_date": "1990-08-24",
    "birth_time": "11:00:00",
    "birth_time_accuracy": "exact",
    "birth_place": "Moscow",
    "latitude": 55.7558,
    "longitude": 37.6173,
    "timezone": "Europe/Moscow"
  }'
```

Сохранить `profile_id` для generate steps.

## 7. Mock happy path smoke

Это основной smoke path для локальной проверки orchestration.

### 7.1 Preconditions

- в `.env`: `LLM_ENABLED=true`, `LLM_PROVIDER=mock`
- stack поднят
- bucket создан
- есть `ACCESS_TOKEN`
- есть `PROFILE_ID`

### 7.2 Generate report

```bash
curl -s -X POST http://localhost:8000/api/v1/reports/generate \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "profile_id": "<PROFILE_ID>",
    "product": "self",
    "mode": "full"
  }'
```

Ожидаемый первый ответ:
- чаще всего `status=generating_narrative`
- fallback-friendly вариант: `status=deterministic_ready`, если enqueue narrative не удался

Из ответа сохранить `report_id`.

### 7.3 Polling detail endpoint

```bash
curl -s http://localhost:8000/api/v1/reports/<REPORT_ID> \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Повторять каждые ~5 секунд.

Практически важные статусы:
- `generating_narrative`
- `ready`
- `narrative_failed`
- `deterministic_ready`

### 7.4 Что считать успешным mock smoke

Успешный mock path =

1. generate response не падает;
2. worker получает narrative task;
3. report переходит в `ready`;
4. `narrative` в detail response больше не `null`;
5. `narrative.model_provider=mock`;
6. PDF path позже доходит до `pdf_generated=true`.

### 7.5 Где это должно быть видно в логах

Искать в `backend`/`worker` логах события вида:
- enqueue generate_report_narrative / generate_pdf;
- narrative generation started;
- narrative generation succeeded;
- pdf task success.

## 8. Real provider happy path smoke

Этот сценарий нужен не для pipeline smoke, а для продуктовой проверки real narrative generation.

### 8.1 Preconditions

- в `.env`:
  - `LLM_ENABLED=true`
  - `LLM_PROVIDER=openrouter`
  - `LLM_MODEL=<real model id>`
  - `LLM_API_KEY=<valid key>`
- stack перезапущен после изменения env
- bucket создан
- есть `ACCESS_TOKEN`
- есть `PROFILE_ID`

После смены env безопаснее перезапустить runtime:

```bash
docker compose up -d --force-recreate backend worker
```

### 8.2 Generate и polling

Использовать те же команды, что в mock smoke path:

```bash
curl -s -X POST http://localhost:8000/api/v1/reports/generate \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "profile_id": "<PROFILE_ID>",
    "product": "self",
    "mode": "full"
  }'
```

и затем polling:

```bash
curl -s http://localhost:8000/api/v1/reports/<REPORT_ID> \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 8.3 Что считать успехом real-provider path

Успех =

1. report доходит до `ready`;
2. `narrative.model_provider=openrouter`;
3. `narrative.model_name` равен реальной configured модели;
4. narrative не является mock payload и не является disabled fallback path;
5. PDF path тоже закрыт (`pdf_generated=true` или рабочий `/pdf` redirect).

## 9. Controlled fallback smoke

Это отдельный сценарий, который проверяет degraded path, а не provider success.

### 9.1 Preconditions

- `LLM_ENABLED=false`
- стек перезапущен для backend/worker

```bash
docker compose up -d --force-recreate backend worker
```

### 9.2 Generate и polling

Использовать тот же `POST /api/v1/reports/generate` и `GET /api/v1/reports/{id}`.

### 9.3 Что считать успехом fallback path

Успех =

1. report не застревает бесконечно;
2. report приходит в `ready` или fallback-friendly состояние, пригодное для чтения;
3. narrative payload построен через deterministic fallback, а не через real provider;
4. deliverable не теряется, хотя внешний LLM path выключен.

Смысл сценария:
- доказать, что LLM layer вторичен;
- базовый результат не уничтожается при intentional disable.

## 10. Broken provider / failure path smoke

Этот сценарий нужен, чтобы проверить diagnosable failure, а не success.

### 10.1 Пример misconfigured real provider

```env
LLM_ENABLED=true
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4.1-mini
LLM_API_KEY=
```

или

```env
LLM_ENABLED=true
LLM_PROVIDER=unsupported-provider
```

Перезапуск runtime:

```bash
docker compose up -d --force-recreate backend worker
```

### 10.2 Ожидаемый результат

- worker пытается выполнить task;
- после retry path report приходит в `narrative_failed`;
- `error_message` объясняет проблему конфигурации provider;
- deterministic report при этом не исчезает.

Этот сценарий полезен для проверки, что команда видит разницу между:
- provider disabled/fallback;
- pipeline smoke success;
- real provider misconfiguration.

## 11. Проверка regenerate path

### 11.1 Когда использовать

Regenerate нужен, когда narrative завис, упал или нужно повторить только narrative layer без пересчёта deterministic report.

### 11.2 Команда

```bash
curl -s -X POST http://localhost:8000/api/v1/reports/<REPORT_ID>/narrative/regenerate \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{}'
```

### 11.3 Что считать успехом

- верхнеуровневый `report.status` снова становится `generating_narrative`;
- после этого detail endpoint можно снова polling'ить;
- deterministic report не пересчитывается заново как отдельный продуктовый flow.

## 12. Проверка PDF path

### 12.1 Что проверять

PDF path считается успешным только если:

1. bucket существует;
2. worker исполнил `reports.generate_pdf`;
3. `report.pdf_generated=true`;
4. `report.pdf_url` заполнен;
5. download endpoint отдаёт redirect на fresh signed URL.

### 12.2 Detail check

```bash
curl -s http://localhost:8000/api/v1/reports/<REPORT_ID> \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ожидание:
- `pdf_generated: true`
- `pdf_url` непустой

### 12.3 Download endpoint check

```bash
curl -I http://localhost:8000/api/v1/reports/<REPORT_ID>/pdf \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Ожидаемый результат:
- `307 Temporary Redirect`

Если вместо этого `404`, значит PDF ещё не готов или storage path сломан.

## 13. Минимальный checklist успеха по шагам

### Stack startup

- [ ] `docker compose up -d postgres redis minio backend frontend worker`
- [ ] `/api/v1/health` возвращает `status=ok`
- [ ] backend/worker logs не показывают немедленный crash

### Storage bootstrap

- [ ] bucket `astrotype` создан
- [ ] bootstrap command отработала без ошибки

### Auth/profile

- [ ] есть verified user
- [ ] есть working `ACCESS_TOKEN`
- [ ] есть `PROFILE_ID`

### Mock smoke

- [ ] generate response получен
- [ ] report не застрял навсегда в `generating_narrative`
- [ ] detail endpoint вернул `ready`
- [ ] `narrative.model_provider=mock`

### Real smoke

- [ ] `LLM_PROVIDER=openrouter`
- [ ] `LLM_API_KEY` валиден
- [ ] detail endpoint вернул `ready`
- [ ] `narrative.model_provider=openrouter`

### Fallback / failure path

- [ ] controlled fallback при `LLM_ENABLED=false` не теряет deliverable
- [ ] broken provider path доходит до diagnosable `narrative_failed`
- [ ] regenerate endpoint возвращает flow в `generating_narrative`

### PDF

- [ ] `pdf_generated=true`
- [ ] `/api/v1/reports/{id}/pdf` возвращает `307`

## 14. Что новый участник команды должен понимать после этого runbook

1. Запуск E11 начинается не с LLM endpoint, а с `POST /api/v1/reports/generate` для `product=self`.
2. Worker обязателен; без него narrative и PDF задачи не исполняются.
3. Mock smoke и real-provider smoke — это разные классы проверки.
4. Bucket bootstrap обязателен до PDF path.
5. `ready` narrative, `narrative_failed`, `deterministic_ready` и controlled fallback нужно различать операционно.
6. Regenerate повторяет только narrative layer, а не весь отчёт.

## 15. Live-verified smoke snapshot

На 2026-06-07 этот runbook был подтверждён живым локальным прогоном в compose-окружении.

Что реально прошло:

- `docker compose ps` показал поднятые `postgres`, `redis`, `minio`, `backend`, `frontend`, `worker`.
- bucket bootstrap отработал через:

```bash
docker compose exec -T backend sh -lc 'cd /app && python - <<"PY"
from app.modules.reports.storage import S3Storage
S3Storage().ensure_bucket()
print("bucket_ready")
PY'
```

- auth prerequisite path был выполнен живыми HTTP-запросами:
  - `POST /api/v1/auth/register` -> `201`
  - `POST /api/v1/auth/verify` -> `200`
  - `POST /api/v1/auth/login` -> `200`
- report flow был выполнен живыми HTTP-запросами:
  - `POST /api/v1/reports/generate` -> `200`, стартовый `status=generating_narrative`
  - polling `GET /api/v1/reports/{id}` -> финальный `status=ready`
  - `narrative.status=ready`
  - `pdf_generated=true`
  - `pdf_url` заполнен
- worker logs подтвердили:
  - `report_narrative_generation_degraded` с причиной `LLM narrative generation is disabled`
  - затем `report_narrative_generation_succeeded ... used_fallback=True`
  - затем `pdf_task_success`
- `GET /api/v1/reports/{id}/pdf` вернул `307 Temporary Redirect` на fresh signed URL.

Что именно этим доказано:

1. Worker runtime действительно обязателен и реально исполняет обе задачи: narrative + PDF.
2. Controlled fallback path не застревает и после фикса `fallback.py` доходит до `ready`.
3. Bucket bootstrap через backend runtime достаточно для успешного PDF upload path.
4. Runbook больше не является только «документом по исходникам» — его базовый local/dev smoke подтверждён живым запуском.

## Ограничения этой story

S05 даёт пошаговый runbook и smoke flows, но не заменяет symptom-driven triage matrix. Финальная таблица вида symptom -> cause -> next check и launch-readiness summary остаются на S06.

## Затронутые файлы

| Файл | Действие |
|---|---|
| `docs/features/E12-llm-report-runtime-readiness/S05-local-runbook-start-logs-smoke.md` | Собран единый локальный runbook |
| `docs/features/E12-llm-report-runtime-readiness/FEATURE.md` | Синхронизирован статус и acceptance по runbook/smoke |
| `docs/SRS/SRS-E12-llm-report-runtime-readiness.md` | Синхронизированы ссылки/verification around runbook |

## Проверка

В этой story фактически подтверждено по текущему коду и документам:

- compose stack требует `postgres redis minio backend frontend worker`
- health endpoint = `/api/v1/health`
- auth для reports требует verified user
- registration не заменяет verification/login
- profile endpoints дают path для получения `profile_id`
- generate/detail/regenerate/pdf endpoints и их семантика подтверждены кодом
- bucket bootstrap обязателен и не автоматизирован
- mock / real / fallback сценарии различаются по фактическому runtime contract

Ограничение текущей среды:

- live-подтверждение выше относится к controlled fallback/mock-runtime readiness, а не к real-provider quality smoke с внешним OpenRouter API ключом

## Критерии приёмки

- [x] Есть пошаговый runbook для нового участника команды.
- [x] В runbook различаются mock и real-provider smoke сценарии.
- [x] В runbook есть команды логов и проверок статусов API.
- [x] Happy path и fallback path проверяются без чтения исходного кода.
