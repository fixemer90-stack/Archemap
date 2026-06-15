# Story E5.S06: PDF rendering from stored report JSON

**Feature:** [Products & Reports](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Первоначальный план хранил готовые PDF как S3/MinIO artifacts и отдавал signed URL. Это решение заменено: готовый PDF больше не является persisted artifact. Источник истины — JSON в PostgreSQL:

- `reports.report_data` — deterministic report JSON;
- `report_narratives.content` — narrative JSON, если он уже сгенерирован.

`GET /reports/{id}/pdf` рендерит PDF на лету через WeasyPrint из этих JSON-данных.

## Что сделать

- PDF-генерация через WeasyPrint из сохранённого JSON
- HTML-шаблон для PDF (Design Code: Deep Space, glassmorphism)
- GET `/reports/{id}/pdf` endpoint, который возвращает `200 application/pdf`
- Не требовать S3/MinIO, bucket bootstrap, persisted signed URL или заранее созданный PDF
- Сохранить старые `pdf_url` / `pdf_generated` как legacy-поля до отдельной миграции удаления

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/reports/pdf.py` | PDF-генерация (WeasyPrint + Jinja2) |
| `backend/app/modules/reports/router.py` | GET `/{id}/pdf` renders PDF on demand |
| `backend/app/modules/reports/tasks.py` | Legacy PDF task no longer uploads/stores artifacts |
| `backend/app/modules/reports/storage.py` | Legacy stub; S3 runtime removed |
| `backend/app/modules/reports/templates/report.html` | HTML-шаблон для PDF |
| `docker-compose.yml` | MinIO service removed from local runtime |

## Pipeline

```text
POST /reports/generate
  → generation of report_data JSON
  → optional narrative task stores narrative JSON
  → no PDF task enqueue, no artifact upload

GET /reports/{id}/pdf
  → load report by id/user
  → load latest saved narrative JSON if present
  → render HTML from report_data + narrative JSON
  → WeasyPrint: HTML → PDF bytes
  → return 200 application/pdf
```

## Критерии приёмки

- [x] PDF-генерация из HTML-шаблона (WeasyPrint)
- [x] HTML-шаблон соответствует Design Code (Deep Space, glassmorphism)
- [x] GET `/reports/{id}/pdf` возвращает PDF bytes (`200 application/pdf`)
- [x] Endpoint работает без `pdf_generated=true` и без `pdf_url`
- [x] S3/MinIO не участвует в runtime PDF path
- [x] Local compose не требует MinIO service для report/PDF flow
- [x] ruff/mypy/unit tests проходят

## Примечания

- WeasyPrint требует системных зависимостей (libpango, libcairo) — они остаются в Docker образе.
- PDF формируется синхронно при скачивании. Для текущего MVP это проще и дешевле, чем object storage.
- Если позже потребуется кэшировать тяжёлые PDF, это нужно делать отдельной историей с явной политикой invalidation/cache, а не возвращать скрытую S3-зависимость.
