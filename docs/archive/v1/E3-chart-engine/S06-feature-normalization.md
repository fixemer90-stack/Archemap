# Story E3.S06: Нормализация признаков: извлечение feature vector из карты, значения 0.0-1.0, quality flags

**Feature:** [Profile & Chart Engine](Archemap/docs/features/v1/E3-chart-engine/FEATURE.md)
**Статус:** ✅ Готово

## Контекст

Feature normalization — мост между сырыми данными карты (E3.S04) и rule engine (E4). Извлекает нормализованные признаки из ChartData в FeatureVector со значениями 0.0-1.0 для использования в правилах интерпретации.

## Что сделать

1. `FeatureVector` dataclass: element distribution (fire/earth/air/water), modality (cardinal/fixed/mutable), house emphasis, aspect counts, quality flags
2. `extract_features(chart: ChartData) -> FeatureVector`: нормализация через взвешивание планет
3. Маппинг знаков → стихии/модальности
4. Веса планет для emphasis calculation
5. Quality flags: has_birth_time, birth_time_quality
6. `to_dict()` для сериализации
7. 8 unit-тестов

## Затрагиваемые файлы

| Файл | Действие |
|---|---|
| `app/chart_engine/features.py` | Создан — FeatureVector + extract_features |
| `tests/chart/test_features.py` | Создан — 8 unit-тестов |

## Критерии приёмки

- [x] Element distribution: fire + earth + air + water = 1.0
- [x] Modality distribution: cardinal + fixed + mutable = 1.0
- [x] House emphasis: нормализованные веса по домам
- [x] Aspect counts: нормализованы от max possible
- [x] Quality flags: has_birth_time, birth_time_quality
- [x] Все значения в [0.0, 1.0]
- [x] Детерминированность: одинаковый вход → одинаковый выход
- [x] Тесты: 8/8
- [x] ruff, mypy — 0 ошибок

## Примечания

- Веса планет: Sun 1.0, Moon 0.9, Mercury/Venus 0.6, Mars/Jupiter/Saturn 0.7, Uranus/Neptune/Pluto 0.5, Node/Chiron 0.3
- Sun/Moon balance пока упрощён (longitude fraction) — можно расширить через элементные силы
- Quality flags пока hardcoded (has_birth_time=True, quality=1.0) — будет заполняться из PersonProfile.birth_time_accuracy в E4
