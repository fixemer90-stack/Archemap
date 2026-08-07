# Story E2.01: User model + регистрация по email/password

**Feature:** [Authentication & Identity](Archemap/docs/features/v1/E2-identity/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Создание модели User и endpoint'а регистрации с хешированием паролей.

## Что сделать

1. User SQLAlchemy model: email, hashed_password, is_active, is_verified
2. Registration service с hash_password
3. POST /auth/register endpoint
4. Pydantic schemas

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/modules/users/models.py` | Создан — User model |
| `app/modules/auth/service.py` | Создан — AuthService.register |
| `app/modules/auth/router.py` | Создан — POST /auth/register |
| `app/modules/auth/schemas.py` | Создан — RegisterRequest |

## Критерии приёмки

- [x] User model с UUID PK
- [x] Пароль хешируется (bcrypt)
- [x] Регистрация через POST /auth/register
- [x] Duplicate email → 409 Conflict

## Примечания

Часть Epic 2: Identity.
