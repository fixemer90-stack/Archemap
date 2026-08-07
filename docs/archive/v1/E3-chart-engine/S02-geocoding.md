# Story E3.S02: Геокодинг (Nominatim): строка места → lat/lon/city/country, кэш 24ч в Redis

**Feature:** [Profile & Chart Engine](Archemap/docs/features/v1/E3-chart-engine/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Для построения натальной карты нужны координаты места рождения. Пользователь вводит строку (например "Москва"), сервис возвращает lat/lon/city/country. Результаты кэшируются в Redis на 24 часа, чтобы не нагружать внешний API.

## Что сделать

1. `NominatimGeocoder` в `app/infrastructure/geocoding.py`: async HTTP-запрос к Nominatim (OpenStreetMap), парсинг address details, Redis-кэш 24ч
2. `GeocodeResult` dataclass: display_name, latitude, longitude, city, country
3. Pydantic-схемы: `GeocodeResultItem`, `GeocodeSearchResponse`
4. Endpoint: `GET /profiles/geocode?q=...` (authenticated, rate-limited)
5. Unit-тесты: cache hit/miss, Nominatim parsing, HTTP error handling, serialization roundtrip

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/infrastructure/geocoding.py` | Создан — NominatimGeocoder + GeocodeResult |
| `app/modules/profiles/schemas.py` | Изменён — добавлены GeocodeResultItem, GeocodeSearchResponse |
| `app/modules/profiles/router.py` | Изменён — добавлен GET /profiles/geocode |
| `tests/unit/test_geocoding.py` | Создан — 8 unit-тестов |

## Критерии приёмки

- [x] Строка места → список результатов с lat/lon/city/country
- [x] Nominatim (OpenStreetMap) как провайдер — бесплатно, без API ключей
- [x] Redis-кэш: 24ч TTL, cache key = нормализованная строка
- [x] Address fallback: city → town → village → municipality
- [x] HTTP errors → пустой список (не crash)
- [x] Пустой результат не кэшируется
- [x] Endpoint аутентифицирован (get_current_user)
- [x] Тесты написаны и проходят (8/8)
- [x] ruff, mypy — 0 ошибок

## Примечания

- Nominatim policy: не более 1 запроса в секунд. Для продакшена нужен свой сервер или переход на GeoNames/Google Geocoding API
- User-Agent: `Astrotype/0.1 (astro-platform)` — обязателен по Nominatim policy
- `accept-language: ru,en` — приоритет русских названий
- Кэш-ключ — lowercase + strip для единообразия
- GeoNames как альтернативный провайдер — будущее улучшение (S02 расширение или отдельная Story)
