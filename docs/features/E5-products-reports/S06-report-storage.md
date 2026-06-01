# Story E5.S06: Хранилище артефактов (PDF + S3)

**Feature:** [Products & Reports](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

PDF-генерация, загрузка в S3/MinIO, signed links для скачивания.

## Что сделать

- PDF-генерация через WeasyPrint
- HTML-шаблон для PDF (Design Code: Deep Space, glassmorphism)
- Загрузка PDF в S3/MinIO
- Signed links с TTL (24h для paid, 1h для free)
- GET /reports/{id}/pdf endpoint
- Celery async task для PDF-генерации

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/reports/pdf.py` | PDF-генерация (WeasyPrint + Jinja2) |
| `backend/app/modules/reports/storage.py` | S3/MinIO client (boto3) |
| `backend/app/modules/reports/tasks.py` | Async PDF generation logic |
| `backend/workers/tasks/reports.py` | Celery task с retry |
| `backend/app/modules/reports/router.py` | POST /generate (trigger), GET /{id}/pdf |
| `backend/app/modules/reports/templates/report.html` | HTML-шаблон для PDF |
| `docker-compose.yml` | MinIO service |

## Pipeline

```
POST /reports/generate
  → генерация report_data
  → Celery task: generate_pdf(report_id, user_id)
    → рендер HTML из Jinja2 шаблона
    → WeasyPrint: HTML → PDF
    → загрузка в S3: reports/{user_id}/{report_id}/v{version}.pdf
    → signed link с TTL (24h full / 1h preview)
    → обновление report: pdf_url, pdf_generated=true

GET /reports/{id}/pdf
  → проверка pdf_generated
  → генерация свежего signed URL
  → 307 redirect на S3
```

## Критерии приёмки

- [x] PDF-генерация из HTML-шаблона (WeasyPrint)
- [x] HTML-шаблон соответствует Design Code (Deep Space, glassmorphism)
- [x] Загрузка PDF в S3/MinIO (boto3)
- [x] Signed links с TTL (24h paid / 1h free)
- [x] GET /reports/{id}/pdf возвращает 307 redirect
- [x] Celery task с retry (max 3)
- [x] MinIO service в docker-compose
- [x] ruff check: 0 ошибок

## Примечания

- WeasyPrint требует системных зависимостей (libpango, libcairo) — есть в Docker образе
- PDF-генерация асинхронная (Celery) — не блокирует POST /generate
- Signed URL генерируется заново при каждом GET /pdf (TTL может истечь)
- Поля pdf_url и pdf_generated уже были в Report модели (из S01)
