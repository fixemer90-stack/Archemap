# Story E8.S01: Rate Limiting API

**Feature:** [Production & Scale](Archemap/docs/features/v1/E8-production-scale/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Глобальный rate limiting для всех API endpoints. Защита от DDoS, brute-force, scraping.

## Что сделать

### Уже реализовано

- `backend/app/core/rate_limit.py` — Redis-backed token bucket
- Login: 5 req/15min per email
- Geocode: 30 req/min per IP

### Реализовано

- Глобальный rate limit middleware (все endpoints)
- Per-user limits: 100 req/min для authenticated, 20 req/min для anonymous
- Per-endpoint overrides: auth endpoints строже
- Rate limit headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
- 429 ответ с Retry-After header
- Конфигурация через settings

## Затрагиваемые файлы

| Путь | Описание |
|---|---|
| `backend/app/core/rate_limit.py` | RateLimiter (✅ есть) |
| `backend/app/api/middleware.py` | RateLimitMiddleware + RequestLoggingMiddleware |
| `backend/app/config.py` | Rate limit settings |
| `backend/app/main.py` | Middleware registration |
| `backend/tests/unit/test_rate_limit.py` | 7 unit-тестов |

## Конфигурация

```python
# config.py
RATE_LIMIT_GLOBAL_PER_MINUTE: int = 100
RATE_LIMIT_ANONYMOUS_PER_MINUTE: int = 20
RATE_LIMIT_LOGIN_MAX_ATTEMPTS: int = 5
RATE_LIMIT_LOGIN_WINDOW_SECONDS: int = 900
RATE_LIMIT_GEOCODE_PER_MINUTE: int = 30
```

## Критерии приёмки

- [x] RateLimiter class (Redis INCR + EXPIRE)
- [x] Login rate limiting (5 req/15min)
- [x] Geocode rate limiting (30 req/min per IP)
- [x] Global middleware для всех endpoints
- [x] Per-user vs per-anonymous limits
- [x] Rate limit headers в response
- [x] 429 + Retry-After
- [x] Конфигурация через settings
- [x] 7 unit-тестов pass

## Примечания

- Redis обязателен — без него rate limiting не работает (graceful degradation)
- IP определяется через X-Forwarded-For (за proxy) или request.client.host
- Для production: Cloudflare Rate Limiting или nginx limit_req как дополнительный слой
