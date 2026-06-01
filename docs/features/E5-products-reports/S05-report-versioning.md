# Story E5.S05: Версионирование отчётов

**Feature:** [Products & Reports](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

При изменении профиля или повторной генерации — старая версия отчёта сохраняется, создаётся новая.

## Что сделать

- ReportVersion модель (SQLAlchemy)
- _archive_version() — архивация текущей версии перед регенерацией
- version auto-increment при повторной генерации
- API: GET /reports/{id}/versions, GET /reports/{id}/versions/{v}

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/reports/models.py` | ReportVersion модель |
| `backend/app/modules/reports/service.py` | _archive_version(), get_versions(), get_version() |
| `backend/app/modules/reports/router.py` | GET /versions endpoints |
| `backend/app/modules/reports/schemas.py` | ReportVersionResponse |
| `backend/alembic/versions/e5f6a7b8c9d0_add_reports_tables.py` | Миграция |

## Pipeline

```
generate_report() вызван повторно
  → _archive_version(existing)  # сохраняет report_data в report_versions
  → version++                   # инкремент номера
  → генерация нового отчёта
  → старая версия доступна через GET /reports/{id}/versions
```

## Критерии приёмки

- [x] ReportVersion модель: report_id, version, report_data, pdf_url, diff_summary
- [x] _archive_version() вызывается перед регенерацией
- [x] version auto-increment
- [x] GET /reports/{id}/versions возвращает историю
- [x] GET /reports/{id}/versions/{v} возвращает конкретную версию
- [x] Ownership check на всех endpoints
- [x] 13 unit-тестов pass

## Примечания

- Immutable: старые версии не редактируются и не удаляются
- diff_summary — зарезервировано для будущего (сравнение версий)
- Повторная генерация = новая версия, не замена
