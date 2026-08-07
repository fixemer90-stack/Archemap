# Story E2.S07: Привязка OAuth-провайдеров

**Feature:** [Authentication & Identity](Archemap/docs/features/v1/E2-identity/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Пользователь может просмотреть привязанные OAuth-провайдеры и отвязать их из настроек.

## Что сделать

- IdentityLink модель (✅ есть)
- OAuth flow создаёт IdentityLink при первом входе (✅ есть)
- GET /auth/linked-providers — список привязок
- DELETE /auth/unlink/{provider} — отвязка с валидацией

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/auth/models.py` | IdentityLink модель |
| `backend/app/modules/auth/service.py` | get_linked_providers(), unlink_provider() |
| `backend/app/modules/auth/router.py` | GET /linked-providers, DELETE /unlink/{provider} |
| `backend/app/modules/auth/schemas.py` | LinkedProviderResponse, LinkedProvidersListResponse |

## API

### GET /auth/linked-providers

Response:
```json
{
  "providers": [
    {
      "provider": "yandex",
      "provider_email": "user@yandex.ru",
      "provider_name": "Иван",
      "linked_at": "2026-05-31T12:00:00Z"
    }
  ],
  "has_password": true
}
```

### DELETE /auth/unlink/{provider}

Response (200):
```json
{
  "message": "Successfully unlinked yandex."
}
```

Response (400 — если единственный способ входа):
```json
{
  "detail": "Cannot unlink the only login method. Set a password first or link another provider."
}
```

## Критерии приёмки

- [x] IdentityLink модель с provider, provider_user_id, provider_email
- [x] OAuth flow создаёт IdentityLink при первом входе
- [x] GET /auth/linked-providers возвращает список привязок
- [x] DELETE /auth/unlink/{provider} удаляет привязку
- [x] Валидация: нельзя отвязать единственный способ входа
- [x] has_password флаг в ответе
- [x] ruff check: 0 ошибок

## Примечания

- Провайдеры: пока только Yandex, в будущем VK, Google
- POST /auth/link/{provider} — отдельная задача (нужен OAuth state с user_id)
- access_token не хранится (WARN-03 fix)
