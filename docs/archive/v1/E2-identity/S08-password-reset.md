# Story E2.08: Сброс пароля

**Feature:** [Authentication & Identity](Archemap/docs/features/v1/E2-identity/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Сброс пароля по email с токеном.

## Что сделать

1. PasswordResetService: request, confirm
2. Token TTL 24h
3. Anti-enumeration
4. POST /auth/password-reset/request + confirm

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/modules/auth/password_reset.py` | Создан — PasswordResetService |
| `app/modules/auth/models.py` | Создан — PasswordReset model |

## Критерии приёмки

- [x] Запрос сброса по email
- [x] Токен истекает через 24ч
- [x] Новый пароль устанавливается
- [x] Anti-enumeration

## Примечания

Часть Epic 2: Identity.
