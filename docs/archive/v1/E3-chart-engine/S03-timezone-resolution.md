# Story E3.S03: Определение часового пояса: IANA TZ по координатам, timezonefinder, Redis-кэш

**Feature:** [Profile & Chart Engine](Archemap/docs/features/v1/E3-chart-engine/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Для расчёта натальной карты нужен корректный часовой пояс места рождения. Часовой пояс определяется по координатам (lat/lon) с помощью offline-библиотеки `timezonefinder`, которая использует IANA tz database. Результат кэшируется в Redis на 30 дней.

## Что сделать

1. `TimezoneResolver` в `app/infrastructure/timezone.py`: offline-резолв через `timezonefinder`, Redis-кэш 30 дней
2. Добавить `timezonefinder>=6.5,<7` в зависимости pyproject.toml
3. Unit-тесты: Москва, Лондон, Нью-Йорк, Токио, океан (None), cache hit/miss/fallback

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/infrastructure/timezone.py` | Создан — TimezoneResolver |
| `pyproject.toml` | Изменён — добавлен timezonefinder |
| `tests/unit/test_timezone.py` | Создан — 10 unit-тестов |

## Критерии приёмки

- [x] Координаты → IANA timezone (e.g. `Europe/Moscow`)
- [x] Offline-резолв (без внешнего API)
- [x] Redis-кэш: 30 дней TTL
- [x] Океан/неизвестные координаты → None (не crash)
- [x] Redis errors → fallback на вычисление
- [x] Тесты написаны и проходят (10/10)
- [x] ruff, mypy — 0 ошибок

## Примечания

- `timezonefinder` использует `h3` (Uber's hexagonal grid) для быстрого поиска — ~1ms на запрос
- Кэш-ключ: `tz:{lat:.4f},{lon:.4f}` — 4 знака после запятой (~11м точность, достаточно для TZ)
- Исторические изменения TZ: `timezonefinder` использует IANA tz database, которая учитывает исторические переходы. Для точного времени в конкретной дате нужно дополнительно учитывать DST, что делает `pytz`/`zoneinfo` при расчёте карты (E3.S04)
