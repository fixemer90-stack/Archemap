# Story E3.S04: Swiss Ephemeris + Flatlib: позиции планет, дома (Placidus), аспекты, CLI

**Feature:** [Profile & Chart Engine](Archemap/docs/features/v1/E3-chart-engine/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Ядро астрологического движка. По UTC-дате рождения и координатам вычисляются позиции планет, дома и аспекты. Результат — `ChartData` dataclass, детерминированный и воспроизводимый.

## Что сделать

1. `app/chart_engine/types.py` — dataclasses: PlanetPosition, HousePosition, Aspect, ChartData
2. `app/chart_engine/ephemeris.py` — Swiss Ephemeris wrapper с fallback-стабом (если pyswisseph не доступен)
3. `app/chart_engine/aspects.py` — детекция аспектов с orb checking и applying/separating
4. `app/chart_engine/chart.py` — сборка ChartData: планеты → дома → аспекты
5. `app/chart_engine/compute.py` — CLI для тестирования
6. Зависимости: pyswisseph, flatlib в pyproject.toml
7. 16 unit-тестов

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/chart_engine/__init__.py` | Создан |
| `app/chart_engine/types.py` | Создан — dataclasses |
| `app/chart_engine/ephemeris.py` | Создан — ephemeris wrapper + stub |
| `app/chart_engine/aspects.py` | Создан — aspect detection |
| `app/chart_engine/chart.py` | Создан — chart builder |
| `app/chart_engine/compute.py` | Создан — CLI entrypoint |
| `pyproject.toml` | Изменён — pyswisseph, flatlib |
| `tests/chart/test_chart_engine.py` | Создан — 16 тестов |

## Критерии приёмки

- [x] 12 планет/точек: Sun-Pluto + North Node + Chiron
- [x] Дома: Placidus (P) по умолчанию, поддержка Equal (E)
- [x] Аспекты: conjunction, sextile, square, trine, quincunx, opposition
- [x] Orb checking с дефолтными и кастомными значениями
- [x] Applying/separating определение
- [x] House assignment для каждой планеты
- [x] CLI: `python -m app.chart_engine.compute --date ... --time ... --lat ... --lon ...`
- [x] Fallback-stab: работает без pyswisseph (для CI и тестов)
- [x] Детерминированность: одинаковый вход → одинаковый выход
- [x] Тесты: 16/16
- [x] ruff, mypy — 0 ошибок

## Примечания

- pyswisseph 2.8.0 не компилируется на Python 3.12 (PyUnicode_AS_DATA удалён). Используется fallback-stab, пока pyswisseph 2.10+ не стабилизируется
- Stub вычисляет приблизительные позиции (±5°) — достаточно для тестов структуры, не для продакшена
- Для продакшена нужен pyswisseph с бинарным wheel для Python 3.12
- flatlib добавлен в зависимости, но не используется напрямую — будет нужен в S05/S06 для feature extraction
