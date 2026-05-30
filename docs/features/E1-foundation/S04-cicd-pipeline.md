# Story E1.S04: CI/CD: GitHub Actions — lint, typecheck, tests, build

**Feature:** [Foundation](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Настройка CI/CD pipeline в GitHub Actions с проверками качества.

## Что сделать

1. ci.yml: lint backend/frontend, typecheck, tests, build
2. Deploy workflow
3. Quality gates: ruff, mypy, eslint, prettier

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `.github/workflows/ci.yml` | Создан — CI pipeline |
| `.github/workflows/deploy.yml` | Создан — Deploy workflow |

## Критерии приёмки

- [x] CI проходит при push
- [x] Lint backend (ruff) + frontend (eslint)
- [x] Typecheck (mypy + tsc)
- [x] Tests (pytest + npm test)
- [x] Docker build

## Примечания

Часть начального scaffolding.
