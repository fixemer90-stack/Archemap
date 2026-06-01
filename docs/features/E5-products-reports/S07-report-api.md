# Story E5.S07: REST API отчётов

**Feature:** [Products & Reports](FEATURE.md)
**Статус:** ✅ Готово (частично из S01)

## Контекст

REST API для генерации, получения и управления отчётами. Обеспечивает CRUD-операции, pagination, ownership check.

## Что сделать

- POST /api/v1/reports/generate — генерация отчёта
- GET /api/v1/reports — список отчётов с pagination
- GET /api/v1/reports/{id} — детали отчёта
- GET /api/v1/reports/{id}/versions — история версий
- GET /api/v1/reports/{id}/versions/{version} — конкретная версия
- Ownership check: пользователь видит только свои отчёты
- Pagination: limit/offset параметры

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/reports/router.py` | API endpoints |
| `backend/app/modules/reports/schemas.py` | Pydantic schemas |
| `backend/app/modules/reports/service.py` | Business logic |
| `backend/app/modules/reports/models.py` | Report, ReportVersion |
| `backend/app/api/v1/__init__.py` | Router registration |

## API Endpoints

### POST /api/v1/reports/generate

Request:
```json
{
  "profile_id": "uuid",
  "product": "self",
  "mode": "full"
}
```

Response (200):
```json
{
  "id": "uuid",
  "profile_id": "uuid",
  "product": "self",
  "version": 1,
  "status": "ready",
  "mode": "full",
  "archetype": "Стратег",
  "score": 0.78,
  "confidence": 0.72,
  "pdf_url": null,
  "pdf_generated": false,
  "report_data": { ... },
  "created_at": "2026-05-31T12:00:00Z",
  "updated_at": "2026-05-31T12:00:00Z"
}
```

### GET /api/v1/reports?product=self&limit=10&offset=0

Response (200):
```json
{
  "items": [ ... ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### GET /api/v1/reports/{id}

Response (200): ReportResponse

### GET /api/v1/reports/{id}/versions

Response (200):
```json
{
  "items": [
    {
      "id": "uuid",
      "report_id": "uuid",
      "version": 1,
      "report_data": { ... },
      "pdf_url": null,
      "diff_summary": null,
      "created_at": "2026-05-31T12:00:00Z"
    }
  ]
}
```

### GET /api/v1/reports/{id}/versions/{version}

Response (200): ReportVersionResponse

## Критерии приёмки

- [x] POST /generate создаёт отчёт через rule engine
- [x] GET /reports возвращает пагинированный список
- [x] GET /reports/{id} возвращает детали отчёта
- [x] GET /reports/{id}/versions возвращает историю версий
- [x] GET /reports/{id}/versions/{version} возвращает конкретную версию
- [x] Ownership check: user_id фильтр на все endpoints
- [x] Pagination: limit (1-100), offset (≥0)
- [x] Auth: все endpoints требуют JWT (Bearer или HttpOnly cookie)
- [x] 13 unit-тестов pass
- [x] ruff + mypy: 0 ошибок

## Примечания

- Реализовано в S01 вместе с report service
- PDF endpoint (GET /reports/{id}/pdf) — backlog (S06)
- DELETE endpoint — не предусмотрен (1 пользователь = 1 отчёт на вертикаль)
- PATCH endpoint — не предусмотрен (при изменении профиля создаётся новая версия)
