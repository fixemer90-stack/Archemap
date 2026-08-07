# Story E2.05: Yandex ID OAuth

**Feature:** [Authentication & Identity](Archemap/docs/features/v1/E2-identity/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

OAuth 2.0 flow через Yandex ID с account linking.

## Что сделать

1. YandexOAuthProvider: authorize URL, code exchange, user info
2. OAuthService: state management, callback handling
3. Account linking по email
4. GET /auth/oauth/yandex/start + callback

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/modules/auth/oauth/yandex.py` | Создан — YandexOAuthProvider |
| `app/modules/auth/oauth/service.py` | Создан — OAuthService |
| `app/modules/auth/models.py` | Создан — IdentityLink model |

## Критерии приёмки

- [x] Authorization Code flow
- [x] State validation
- [x] Account linking по email
- [x] Новый user создаётся при отсутствии

## Примечания

Часть Epic 2: Identity.
