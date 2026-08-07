# Story E8.S03: Secrets Manager

**Feature:** [Production & Scale](Archemap/docs/features/v1/E8-production-scale/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Централизованное управление секретами: валидация, проверка дефолтов, environment-specific конфигурация.

## Что сделать

- Модуль валидации секретов
- Проверка insecure defaults в production
- Проверка обязательных секретов
- Environment-specific .env.example файлы
- Health endpoint для проверки статуса секретов

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/core/secrets.py` | Валидация секретов |
| `backend/app/config.py` | Production/staging guards |
| `backend/app/api/v1/health.py` | /health/secrets endpoint |
| `backend/.env.example.development` | Dev environment |
| `backend/.env.example.staging` | Staging environment |
| `backend/.env.example.production` | Production environment |

## Секреты для управления

| Секрет | Где используется | Ротация |
|---|---|---|
| `SECRET_KEY` | JWT signing | Каждые 90 дней |
| `DATABASE_URL` | PostgreSQL connection | При смене пароля БД |
| `REDIS_URL` | Redis connection | При смене пароля Redis |
| `YANDEX_CLIENT_SECRET` | OAuth | При ротации в Yandex Console |
| `SMTP_PASSWORD` | Email sending | При смене пароля SMTP |
| `S3_SECRET_ACCESS_KEY` | MinIO/S3 | При ротации ключей |

## Критерии приёмки

- [x] Secrets validation module
- [x] Production guard: insecure defaults → RuntimeError
- [x] Staging guard: warnings для insecure defaults
- [x] Environment-specific .env.example файлы
- [x] /health/secrets endpoint (dev/staging only)
- [x] get_secret_status() для проверки конфигурации

## Примечания

- Текущий подход: .env файлы (подходит для dev/staging)
- Для production: Yandex Lockbox или HashiCorp Vault
- /health/secrets не работает в production (безопасность)
