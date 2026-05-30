# Story E1.S03: Infrastructure: Docker Compose, PostgreSQL 16, Redis 7

**Feature:** [Foundation](FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Настройка локальной инфраструктуры: Docker Compose с PostgreSQL и Redis.

## Что сделать

1. docker-compose.yml с PostgreSQL 16 + Redis 7
2. .env.example с переменными
3. Health check endpoint

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `docker-compose.yml` | Создан — PostgreSQL + Redis |
| `.env.example` | Создан — template переменных |
| `app/api/v1/health.py` | Создан — health endpoint |

## Критерии приёмки

- [x] PostgreSQL 16 через Docker
- [x] Redis 7 через Docker
- [x] .env.example
- [x] Health endpoint с DB + Redis checks

## Примечания

Часть начального scaffolding.
