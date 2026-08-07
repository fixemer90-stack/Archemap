# Story E1.S06: Quality gates: ruff, mypy, eslint, prettier, pre-commit

**Feature:** [Foundation](Archemap/docs/features/v1/E1-foundation/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Настройка инструментов качества кода.

## Что сделать

1. ruff: lint + format
2. mypy: static typing
3. eslint + prettier: frontend
4. pre-commit hooks

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `pyproject.toml` | Изменён — ruff, mypy config |
| `frontend/.eslintrc.*` | Создан |
| `.pre-commit-config.yaml` | Создан |

## Критерии приёмки

- [x] ruff check/format
- [x] mypy strict
- [x] eslint + prettier
- [x] pre-commit hooks

## Примечания

Часть начального scaffolding.
