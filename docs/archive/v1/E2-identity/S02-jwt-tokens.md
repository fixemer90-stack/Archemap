# Story E2.02: JWT access/refresh токены

**Feature:** [Authentication & Identity](Archemap/docs/features/v1/E2-identity/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Создание и валидация JWT access/refresh токенов.

## Что сделать

1. create_access_token / create_refresh_token
2. decode_access_token / decode_refresh_token
3. Refresh flow: POST /auth/refresh

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/core/security.py` | Создан — JWT functions |
| `app/modules/auth/router.py` | Изменён — login + refresh endpoints |

## Критерии приёмки

- [x] Access token 30 мин
- [x] Refresh token 30 дней
- [x] HS256 algorithm
- [x] Refresh flow работает

## Примечания

Часть Epic 2: Identity.
