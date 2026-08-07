# Story E12.S04: Object storage and PDF bootstrap

**Feature:** [LLM Report Runtime Readiness](Archemap/docs/features/v1/E12-llm-report-runtime-readiness/FEATURE.md)
**Статус:** ✅ Готово

## Текущий контракт после refactor: S3 больше не нужен

Этот документ исторически описывал S3/MinIO bootstrap path. Контракт переигран: готовые PDF больше не хранятся как object-storage artifacts.

Актуальный runtime contract:

- `reports.report_data` хранит deterministic report JSON в PostgreSQL;
- `report_narratives.content` хранит narrative JSON в PostgreSQL;
- `POST /api/v1/reports/generate` больше не enqueue'ит PDF artifact task;
- `GET /api/v1/reports/{id}/pdf` рендерит PDF на лету из сохранённых JSON и возвращает `200 application/pdf`;
- `pdf_url` / `pdf_generated` остаются legacy-полями до отдельной миграции удаления;
- MinIO/S3 env vars, bucket bootstrap и signed URL больше не являются обязательными для локального/dev report flow.

Ниже оставлен исторический анализ прежнего S3-контракта как контекст решения.

## Контекст

E11 narrative flow считается реально готовым только если после deterministic/narrative generation система может отдать финальный PDF deliverable. В текущем коде PDF generation идёт отдельной Celery task и публикует артефакт в S3-compatible storage. Значит, narrative-ready runtime без storage bootstrap остаётся частично рабочим: report может стать `ready`, но PDF download path останется сломанным.

## Что было проверено

Проверены фактические источники истины:

- `backend/app/config.py`
- `backend/app/modules/reports/storage.py`
- `backend/app/modules/reports/tasks.py`
- `backend/app/modules/reports/router.py`
- `backend/app/modules/reports/models.py`
- `docker-compose.yml`
- `.env.example`
- `scripts/setup.sh`

## Фактический storage runtime contract

### Базовые env-переменные

Из `backend/app/config.py` и `.env.example` следует текущий storage contract:

- `S3_ENDPOINT_URL`
- `S3_ACCESS_KEY_ID`
- `S3_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME`
- `S3_REGION`

Текущие default/example значения:

```env
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=astrotype
S3_REGION=us-east-1
```

В `docker-compose.yml` backend/worker сейчас получают:

```yaml
S3_ENDPOINT_URL: http://minio:9000
S3_ACCESS_KEY_ID: minioadmin
S3_SECRET_ACCESS_KEY: minioadmin
S3_BUCKET_NAME: astrotype
```

То есть локальный compose path ориентирован на встроенный MinIO service, а не на внешний AWS S3 endpoint.

## Что реально делает storage layer

### `S3Storage`

`backend/app/modules/reports/storage.py` реализует runtime client на `boto3`:

- `upload(...)` -> `put_object(...)`
- `get_signed_url(...)` -> `generate_presigned_url("get_object", ...)`
- `delete(...)` -> `delete_object(...)`
- `ensure_bucket()` -> `head_bucket(...)`, при отсутствии пытается `create_bucket(...)`

### Ключевой факт по bootstrap

Метод `ensure_bucket()` в коде есть, но в текущем runtime path он нигде не вызывается автоматически.

Проверенный вывод:
- backend startup не делает bucket bootstrap;
- worker startup не делает bucket bootstrap;
- `generate_pdf_task(...)` не вызывает `ensure_bucket()` перед upload;
- `scripts/setup.sh` поднимает compose и миграции, но не создаёт bucket.

Итог: существование bucket сейчас является обязательным внешним предусловием для первого успешного PDF upload.

## Кто отвечает за bucket existence

Для текущего состояния проекта правильный documented contract такой:

- bucket existence НЕ гарантируется startup hook'ом;
- bucket existence НЕ гарантируется PDF task'ом;
- bucket existence должно быть обеспечено отдельным bootstrap step до smoke/generate flow.

То есть это manual bootstrap contract, пока не появится отдельный admin script или startup automation.

## Фактический PDF runtime flow

### Generate path

Из `backend/app/modules/reports/router.py`:

1. `POST /api/v1/reports/generate` создаёт report.
2. Backend пытается enqueue'ить `generate_pdf.delay(...)`.
3. Если enqueue сломался, backend только логирует `pdf_task_enqueue_failed` и не валит сам report request.

### Worker path

Из `backend/app/modules/reports/tasks.py`:

1. Worker загружает report из БД.
2. Берёт latest saved narrative, если он есть.
3. Генерирует PDF через `generate_report_pdf(...)`.
4. Строит S3 key:

```text
reports/{user_id}/{report_id}/v{version}.pdf
```

5. Загружает PDF через `await storage.upload(...)`.
6. Генерирует signed URL через `storage.get_signed_url(...)`.
7. Только после этого выставляет:
   - `report.pdf_url`
   - `report.pdf_generated = True`

### Download path

Из `GET /api/v1/reports/{report_id}/pdf`:

- если `pdf_generated=false` или `pdf_url` отсутствует -> API возвращает `404 PDF not generated yet`
- если PDF есть, backend пересобирает fresh signed URL и отдаёт `307 redirect`

## Signed URL contract

`get_signed_ttl(mode)` задаёт TTL по режиму отчёта:

- `full` -> `86400` секунд (24 часа)
- всё остальное -> `3600` секунд (1 час)

Важно:
- persisted `pdf_url` не считается вечным URL;
- download endpoint каждый раз генерирует fresh signed URL;
- истечение старого signed URL само по себе не означает потерю PDF-артефакта, если bucket/object всё ещё существуют.

## Минимальный bucket bootstrap contract

Для локального/dev narrative-ready стека до первого generate flow должен существовать bucket с именем из `S3_BUCKET_NAME`.

В текущем compose/dev contract это означает bucket:

```text
astrotype
```

на endpoint:

```text
http://localhost:9000   # с хоста
http://minio:9000       # из compose network
```

Минимальный операторский bootstrap шаг можно формулировать так:

1. Поднять `minio`.
2. Проверить доступность storage credentials.
3. Создать bucket `astrotype`, если он ещё не существует.
4. Только после этого проверять PDF upload path.

Story S04 фиксирует именно этот контракт; конкретная runbook-команда будет собрана в S05.

## Smoke path для PDF

Проверяемый smoke flow для PDF сейчас такой:

1. Bucket уже существует.
2. Поднят worker.
3. Вызван `POST /api/v1/reports/generate`.
4. Worker исполнил `reports.generate_pdf` без ошибок upload/signing.
5. В записи report появились:
   - `pdf_generated = true`
   - непустой `pdf_url`
6. `GET /api/v1/reports/{report_id}/pdf` возвращает `307` redirect на fresh signed URL.

Это отдельная проверка от narrative success:
- narrative может стать `ready`, даже если PDF path сломан;
- PDF deliverable считается готовым только после успешного upload + signed URL path.

## Типичные failure cases

### 1. Bucket missing

Что происходит:
- `put_object(...)` в `upload()` падает с `ClientError`
- worker логирует `s3_upload_failed` / `pdf_task_failed`
- `report.pdf_generated` не становится `true`
- download endpoint продолжает возвращать 404

Вывод:
- narrative workflow может быть завершён,
- но финальная PDF deliverable-цепочка сломана.

### 2. Bad credentials / wrong endpoint

Что происходит:
- boto3 client не может аутентифицироваться или достучаться до storage
- upload/signing path падает с `ClientError`
- PDF не публикуется

Вывод:
- проблема не в LLM narrative,
- а в object storage runtime contract.

### 3. Upload failed after successful report generation

Что происходит:
- deterministic report и narrative могут уже существовать
- PDF task падает отдельно
- `POST /reports/generate` сам по себе не откатывается

Вывод:
- это не полный report-generation failure,
- это artifact publication failure.

### 4. Signed URL missing or expired

Что происходит:
- если PDF вообще не был опубликован, `GET /pdf` даст 404
- если старый signed URL истёк, endpoint генерирует новый URL при запросе

Вывод:
- expired stored URL не является критическим состоянием сам по себе;
- критично отсутствие bucket/object или невозможность сгенерировать новый presigned URL.

## Что ломает narrative workflow, а что ломает только финальный deliverable

### Не обязательно ломает narrative workflow

Следующие проблемы могут не мешать report стать `ready`, но ломают финальный PDF deliverable:

- bucket missing
- bad storage credentials
- upload failure
- signed URL generation failure
- PDF task enqueue failure

### Ломает финальную доставку PDF

Следствие во всех этих случаях одно:

- `pdf_generated=false`
- `pdf_url` отсутствует или unusable
- `GET /api/v1/reports/{id}/pdf` не выдаёт рабочий download path

Именно поэтому S04 обязателен: без storage bootstrap narrative report остаётся не полностью ship-ready.

## Что меняется в понимании runtime после S04

После этой story явно зафиксировано:

1. MinIO/S3 не является факультативной частью E11 launch path, если нужен финальный PDF.
2. Bucket existence сейчас не автоматизирован и должен быть обеспечен заранее.
3. `ensure_bucket()` в кодовой базе существует, но не участвует в фактическом runtime path.
4. PDF failure и narrative failure — это разные operational классы проблем.
5. `GET /reports/{id}/pdf` зависит не только от report row, но и от живого object storage contract.

## Ограничения этой story

S04 фиксирует storage/bootstrap contract, но не закрывает:

- пошаговый runbook с точными операторскими командами — это S05
- triage/checklist по stuck/failure cases — это S06

## Затронутые файлы

| Файл | Действие |
|---|---|
| `backend/app/modules/reports/storage.py` | Сверен runtime storage client и bucket bootstrap behavior |
| `backend/app/modules/reports/tasks.py` | Сверены PDF upload assumptions |
| `backend/app/modules/reports/router.py` | Сверен download/signed URL path |
| `.env.example` | Подтверждён storage env contract |
| `scripts/setup.sh` | Подтверждено отсутствие bucket bootstrap шага |
| `docs/features/E12-llm-report-runtime-readiness/S04-object-storage-pdf-bootstrap.md` | Описан storage contract и bootstrap path |

## Проверка

В этой story фактически проверено:

- storage env contract существует в `Settings` и `.env.example`
- compose использует MinIO-compatible значения для backend/worker
- PDF upload path идёт через `S3Storage.upload(...)`
- signed download path идёт через `S3Storage.get_signed_url(...)`
- `ensure_bucket()` существует, но не вызывается автоматически в runtime path
- `GET /reports/{id}/pdf` требует `pdf_generated=true` и рабочий signing path

Ограничение текущей среды:

- live upload в MinIO не прогонялся, потому что в текущей WSL-сессии недоступен рабочий Docker Compose runtime
- поэтому S04 закрывает contract/bootstrap documentation, а не фактический end-to-end storage smoke run

## Критерии приёмки

- [x] Документировано, как гарантируется существование bucket до первого PDF upload.
- [x] Есть проверяемый smoke path для PDF.
- [x] Понятно, какие ошибки narrative workflow не ломают, а какие ломают финальную PDF deliverable-цепочку.
