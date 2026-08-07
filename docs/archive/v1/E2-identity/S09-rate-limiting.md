# Story E2.09: Rate limiting входа

**Feature:** [Authentication & Identity](Archemap/docs/features/v1/E2-identity/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Защита от брутфорса: 5 попыток / 15 мин.

## Что сделать

1. RateLimiter: Redis INCR + EXPIRE
2. 5 попыток / 15 мин на login
3. HTTP 429 при превышении
4. Сброс после успешного входа

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/core/rate_limit.py` | Создан — RateLimiter |

## Критерии приёмки

- [x] 5 попыток / 15 мин
- [x] HTTP 429 с retry_after
- [x] Сброс после успешного login

## Примечания

Часть Epic 2: Identity.
