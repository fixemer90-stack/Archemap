# Story E2.S07: Привязка OAuth-провайдеров

**Feature:** [Authentication & Identity](FEATURE.md)
**Статус:** 🟡 В процессе (модель и OAuth flow есть, API для link/unlink нет)

## Контекст

Пользователь может войти через Yandex OAuth. При первом входе создаётся IdentityLink. Но нет API для:
- Просмотра привязанных провайдеров
- Привязки нового провайдера к существующему аккаунту
- Отвязки провайдера

## Что сделать

### Уже реализовано

- IdentityLink модель (provider, provider_user_id, provider_email, provider_name)
- OAuth flow: Yandex → create IdentityLink при первом входе
- Привязка по email: если email совпадает — линк к существующему пользователю
- access_token не хранится (WARN-03 fix)

### Нужно реализовать

- GET /auth/linked-providers — список привязанных провайдеров
- POST /auth/link/{provider} — инициация привязки (redirect на OAuth)
- DELETE /auth/unlink/{provider} — отвязка провайдера
- Валидация: нельзя отвязать единственный способ входа (если нет пароля)

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/modules/auth/models.py` | IdentityLink модель (✅ есть) |
| `backend/app/modules/auth/oauth/service.py` | OAuth flow, _find_or_create_user (✅ есть) |
| `backend/app/modules/auth/oauth/yandex.py` | Yandex OAuth provider (✅ есть) |
| `backend/app/modules/auth/router.py` | OAuth endpoints (✅ есть) |
| `backend/app/modules/auth/router.py` | link/unlink endpoints (⬜ нужно) |
| `backend/app/modules/auth/schemas.py` | LinkedProviderResponse (⬜ нужно) |

## API

### GET /auth/linked-providers

Response:
```json
{
  "providers": [
    {
      "provider": "yandex",
      "provider_email": "user@yandex.ru",
      "linked_at": "2026-05-31T12:00:00Z"
    }
  ]
}
```

### POST /auth/link/{provider}

Инициирует OAuth flow для привязки провайдера к текущему пользователю.
- Redirect на OAuth authorize URL
- Callback создаёт IdentityLink для текущего пользователя (не создаёт нового)

### DELETE /auth/unlink/{provider}

Удаляет IdentityLink.
- Валидация: если у пользователя нет пароля и это единственный провайдер → 400
- Удаляет связь из identity_links

## Критерии приёмки

- [x] IdentityLink модель с provider, provider_user_id, provider_email
- [x] OAuth flow создаёт IdentityLink при первом входе
- [x] Привязка по email (существующий пользователь + новый OAuth)
- [x] access_token не хранится (WARN-03)
- [ ] GET /auth/linked-providers
- [ ] POST /auth/link/{provider}
- [ ] DELETE /auth/unlink/{provider}
- [ ] Валидация: нельзя отвязать единственный способ входа
- [ ] Тесты для link/unlink
- [ ] ruff, mypy — 0 ошибок

## Примечания

- IdentityLink уже используется в OAuth flow (oauth/service.py)
- Для link/{provider} нужен отдельный OAuth state с user_id (чтобы callback знал, что это привязка, а не вход)
- Для unlink нужна проверка: есть ли пароль или другие провайдеры
- Провайдеры: пока только Yandex, в будущем VK, Google
