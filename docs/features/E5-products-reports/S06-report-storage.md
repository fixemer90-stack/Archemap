w# Story E5.S06: Хранилище артефактов (PDF + S3)

**Feature:** [Products & Reports](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

PDF-генерация, загрузка в S3/MinIO, signed links для скачивания.

## Что сделать

- PDF-генерация через WeasyPrint или Playwright
- HTML-шаблон для PDF (Design Code: Deep Space, glassmorphism)
- Загрузка PDF в S3/MinIO
- Signed links с TTL (24h для paid, 1h для free)
- GET /reports/{id}/pdf endpoint
- Celery async task для PDF-генерации
- Cleanup старых артефактов

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/reports/pdf.py` | PDF-генерация (WeasyPrint/Playwright) |
| `backend/app/modules/reports/storage.py` | S3/MinIO client |
| `backend/app/modules/reports/tasks.py` | Celery tasks |
| `backend/app/modules/reports/router.py` | GET /reports/{id}/pdf |
| `backend/app/modules/reports/templates/` | HTML-шаблоны для PDF |

## Pipeline

```
POST /reports/generate
  → генерация report_data
  → Celery task: generate_pdf(report_id)
    → рендер HTML из шаблона
    → WeasyPrint: HTML → PDF
    → загрузка в S3: reports/{user_id}/{report_id}/v{version}.pdf
    → signed link с TTL
    → обновление report: pdf_url, pdf_generated=true
```

## Критерии приёмки

- [ ] PDF-генерация из HTML-шаблона
- [ ] HTML-шаблон соответствует Design Code
- [ ] Загрузка PDF в S3/MinIO
- [ ] Signed links с TTL (24h paid / 1h free)
- [ ] GET /reports/{id}/pdf возвращает redirect на signed URL
- [ ] Celery async task
- [ ] Retry при ошибке (max 3)
- [ ] Cleanup старых артефактов
- [ ] Тесты

## Примечания

- Зависит от S3/MinIO (docker-compose: minio service)
- WeasyPrint требует системных зависимостей (libpango, libcairo)
- Альтернатива: Playwright (headless Chrome) — тяжелее, но лучше CSS support
- Поля pdf_url и pdf_generated уже есть в Report модели
