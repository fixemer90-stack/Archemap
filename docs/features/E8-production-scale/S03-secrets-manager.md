# Story E8.S03: Secrets Manager

**Feature:** [Production & Scale](FEATURE.md)
**Статус:** ⬜ Не начато

## Контекст

Централизованное управление секретами: API keys, database credentials, JWT secrets.

## Что сделать

- Выбрать secrets manager (HashiCorp Vault, AWS SSM, Yandex Lockbox)
- Интеграция с backend (чтение секретов при старте)
- Ротация секретов через CI/CD
- Аудит доступа к секретам

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/config.py` | Settings из secrets manager |
| `infra/vault/` | Vault configuration (если выбран) |
| `.github/workflows/deploy.yml` | Secrets injection при деплое |

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

- [ ] Secrets manager выбран и настроен
- [ ] Backend читает секреты из manager (не из .env)
- [ ] CI/CD инжектит секреты при деплое
- [ ] Ротация через CI pipeline
- [ ] Аудит доступа

## Примечания

- Для старта: .env файлы (текущий подход)
- Потом: Yandex LockBox (если деплой на Yandex Cloud)
- Альтернатива: HashiCorp Vault (self-hosted)
