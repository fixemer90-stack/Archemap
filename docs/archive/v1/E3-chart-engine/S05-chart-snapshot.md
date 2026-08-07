# Story E3.S05: ChartSnapshot: вычисление, сохранение в БД, кэширование

**Feature:** [Profile & Chart Engine](Archemap/docs/features/v1/E3-chart-engine/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

ChartSnapshot — персистентное хранение вычисленной натальной карты. При повторном запросе возвращается кэш (если engine version не изменилась). Это экономит время вычисления и обеспечивает воспроизводимость.

## Что сделать

1. `ChartSnapshot` SQLAlchemy-модель: profile_id, user_id, engine_version, chart_data (JSON)
2. `ChartService`: get_or_compute (кэш или вычисление), get_by_id, list_by_profile
3. Сериализация ChartData → JSON dict
4. Alembic-миграция для chart_snapshots
5. Router: POST /profiles/{id}/chart, GET list, GET by id
6. Pydantic-схемы: ChartSnapshotResponse, ChartSnapshotListResponse
7. Unit-тесты

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/modules/charts/__init__.py` | Создан |
| `app/modules/charts/models.py` | Создан — ChartSnapshot модель |
| `app/modules/charts/schemas.py` | Создан — Pydantic schemas |
| `app/modules/charts/service.py` | Создан — ChartService + serialization |
| `app/modules/charts/router.py` | Создан — FastAPI endpoints |
| `app/api/v1/__init__.py` | Изменён — charts_router |
| `alembic/versions/b2c3d4e5f6a7_*.py` | Создан — миграция |
| `tests/unit/test_chart_service.py` | Создан — 5 тестов |

## Критерии приёмки

- [x] ChartSnapshot хранит вычисленную карту как JSON
- [x] engine_version для воспроизводимости
- [x] get_or_compute: возвращает кэш или вычисляет новый
- [x] force_recompute=True для принудительного пересчёта
- [x] Ownership check: только свои снимки
- [x] POST /profiles/{id}/chart — вычислить/получить
- [x] GET list + GET by id
- [x] Alembic-миграция с downgrade
- [x] Тесты: 5/5
- [x] ruff, mypy — 0 ошибок

## Примечания

- Кэш-ключ: (profile_id, user_id, engine_version). При обновлении engine_version старые снимки не удаляются, но не отдаются как кэш
- chart_data хранится как JSONB в PostgreSQL — можно查询ить отдельные поля
- birth_time nullable: если unknown, используется 00:00 с предупреждением о точности
