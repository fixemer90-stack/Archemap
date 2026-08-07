# Story E1.S05: Database migrations: Alembic setup, базовые миграции

**Feature:** [Foundation](Archemap/docs/features/v1/E1-foundation/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Настройка Alembic для миграций базы данных.

## Что сделать

1. Alembic setup с async engine
2. Базовые миграции: users, email_verification, identity_links
3. Downgrade support

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `alembic.ini` | Создан |
| `alembic/env.py` | Создан — async env |
| `alembic/versions/*.py` | Созданы — миграции |

## Критерии приёмки

- [x] alembic upgrade head работает
- [x] Downgrade работает
- [x] Async engine support

## Примечания

Часть начального scaffolding.
