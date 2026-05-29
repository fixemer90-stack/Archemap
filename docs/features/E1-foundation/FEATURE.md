# Feature E1: Foundation

## Цель

Инфраструктурная основа проекта: скелет backend/frontend, CI/CD, Docker, миграции, quality gates. Без этого фичи не могут разрабатываться и деплоиться.

## Зависимости

Нет

## Критерии приёмки

- [ ] Backend запускается локально через uvicorn
- [ ] Frontend запускается через npm run dev
- [ ] PostgreSQL + Redis поднимаются через Docker Compose
- [ ] Alembic миграции применяются без ошибок
- [ ] CI pipeline проходит: lint, typecheck, tests
- [ ] pre-commit hooks настроены

## Stories

| ID | Описание | Статус |
|---|---|---|
| S01 | [Backend scaffolding: FastAPI, структура проекта, pyproject.toml, зависимости](S01-backend-scaffolding.md) | ✅ Готово |
| S02 | [Frontend scaffolding: Next.js 15, shadcn/ui, Tailwind 4, структура App Router](S02-frontend-scaffolding.md) | ✅ Готово |
| S03 | [Infrastructure: Docker Compose (PostgreSQL 16, Redis 7), .env.example](S03-infrastructure.md) | ✅ Готово |
| S04 | [CI/CD: GitHub Actions — lint, typecheck, tests, build](S04-cicd-pipeline.md) | ✅ Готово |
| S05 | [Database migrations: Alembic setup, базовые миграции, downgrade support](S05-database-migrations.md) | ✅ Готово |
| S06 | [Quality gates: ruff, mypy, eslint, prettier, pre-commit hooks](S06-quality-gates.md) | ✅ Готово |
