# Story E8.S09: Report PDF storage strategy — DB JSON source of truth

**Feature:** [Production & Scale](Archemap/docs/features/v1/E8-production-scale/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Первоначальный Render/K8s план предполагал S3-compatible хранилище для готовых PDF artifacts: worker генерирует PDF, загружает его в S3/MinIO, API отдаёт signed URL.

Для текущего MVP это избыточно. Принято новое решение:

- готовые PDF не хранятся как persisted artifacts;
- источник истины хранится в PostgreSQL как JSON:
  - `reports.report_data` — deterministic report JSON;
  - `report_narratives.content` — narrative JSON, если он уже сгенерирован;
- `GET /reports/{id}/pdf` рендерит PDF на лету из этих JSON-данных и возвращает `200 application/pdf`;
- S3/MinIO, bucket bootstrap, signed URLs и object-storage credentials не входят в обязательный runtime contract.

## Решение

### Runtime contract

```text
POST /reports/generate
  -> writes reports.report_data JSON
  -> for self reports enqueues narrative generation
  -> narrative worker writes report_narratives.content JSON
  -> no PDF artifact upload

GET /reports/{id}/pdf
  -> loads report by id/user
  -> loads latest narrative JSON if available
  -> renders HTML from stored JSON
  -> WeasyPrint produces PDF bytes
  -> API returns 200 application/pdf
```

### Почему не S3 сейчас

S3-compatible storage полезен, когда PDF нужно кэшировать/шарить как долгоживущий artifact. Сейчас это даёт лишние операционные зависимости:

- отдельный provider или MinIO;
- секреты `S3_*`;
- bucket bootstrap;
- signed URL topology между backend/worker/browser;
- дополнительный failure mode, не связанный с ценностью MVP.

При хранении JSON в Postgres PDF остаётся воспроизводимым: мы можем в любой момент собрать его заново из persisted report/narrative data.

### Legacy поля

`reports.pdf_url`, `reports.pdf_generated`, `report_versions.pdf_url` пока остаются в БД/API как legacy-поля для совместимости схемы и контрактов.

Правила:

- новый runtime path не должен зависеть от `pdf_generated=true`;
- `/reports/{id}/pdf` не должен требовать `pdf_url`;
- новые PDF artifacts не должны сохраняться в S3/MinIO;
- удаление legacy-полей — отдельная миграция после стабилизации frontend/API-контракта.

## Затрагиваемые файлы

| Путь | Роль |
|---|---|
| `backend/app/modules/reports/router.py` | `/reports/{id}/pdf` рендерит PDF on demand |
| `backend/app/modules/reports/pdf.py` | HTML + WeasyPrint PDF rendering |
| `backend/app/modules/reports/tasks.py` | Legacy task returns PDF size only, без storage upload |
| `backend/app/modules/reports/storage.py` | Legacy stub, S3 runtime удалён |
| `docker-compose.yml` | Local runtime без MinIO |
| `.env.example`, `backend/.env.example.*` | S3 env удалён из обязательных примеров |
| `infra/k8s/base/secrets.yaml` | S3 secrets удалены из base secret contract |

## Acceptance Criteria

- [x] Документация фиксирует отказ от S3-compatible storage для MVP PDF path.
- [x] Runtime source of truth — JSON в Postgres (`reports.report_data`, `report_narratives.content`).
- [x] `/reports/{id}/pdf` возвращает PDF bytes напрямую (`200 application/pdf`).
- [x] PDF endpoint работает без `pdf_generated=true` и без `pdf_url`.
- [x] Local compose не требует MinIO.
- [x] Env examples не требуют `S3_*`.
- [x] K8s base secrets не требуют `S3_*`.
- [x] Legacy `pdf_url` / `pdf_generated` явно помечены как совместимость до отдельной миграции.

## Будущая оптимизация

Если PDF generation станет дорогим, можно добавить отдельный cache layer. Это должна быть новая история с явными правилами:

- cache key / invalidation;
- TTL;
- где хранить cache artifact;
- как не ломать source-of-truth модель Postgres JSON.

Это не должно незаметно возвращать S3 как обязательную dependency для MVP.
