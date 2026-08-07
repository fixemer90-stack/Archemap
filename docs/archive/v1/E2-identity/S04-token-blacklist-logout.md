# Story E2.04: Token blacklist (logout)

**Feature:** [Authentication & Identity](Archemap/docs/features/v1/E2-identity/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Blacklist токенов для logout через Redis.

## Что сделать

1. Redis-based token blacklist
2. POST /auth/logout endpoint
3. Проверка blacklist при валидации токена

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/core/token_blacklist.py` | Создан — Redis blacklist |
| `app/modules/auth/router.py` | Изменён — logout endpoint |

## Критерии приёмки

- [x] Logout blacklists access token
- [x] Blacklisted token → 401
- [x] Optional refresh token blacklist

## Примечания

Часть Epic 2: Identity.
