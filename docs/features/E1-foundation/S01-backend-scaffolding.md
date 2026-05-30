# Story E1.S01: Backend scaffolding: FastAPI, структура проекта, pyproject.toml

**Feature:** [Foundation](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Создание backend-скелета: FastAPI приложение, структура модулей, pyproject.toml с зависимостями.

## Что сделать

1. FastAPI app с lifespan, CORS, exception handlers
2. Структура: app/modules/, app/core/, app/infrastructure/, app/api/
3. pyproject.toml с hatchling, dependencies
4. config.py через pydantic-settings
5. Base SQLAlchemy model с UUID + timestamps

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/main.py` | Создан — FastAPI entrypoint |
| `app/config.py` | Создан — Settings |
| `app/core/models.py` | Создан — BaseModel |
| `app/core/exceptions.py` | Создан — domain exceptions |
| `app/infrastructure/database.py` | Создан — async engine |
| `pyproject.toml` | Создан |

## Критерии приёмки

- [x] FastAPI app запускается
- [x] Структура модульная
- [x] pydantic-settings конфиг
- [x] SQLAlchemy async engine
- [x] BaseModel с UUID + timestamps

## Примечания

Часть начального scaffolding.
