# S02 — Aspect Ranking and Pattern Clustering

> Статус: ✅ Готово
> Коммит: `193b605`

## Контекст

Сейчас аспекты попадают в `key_aspects`, но часто остаются плоским списком. Для глубокого отчёта аспекты должны объяснять динамику карты: связь психических функций, внутреннее напряжение, ресурс, компенсацию и зрелую интеграцию.

## Что сделано

1. Добавлена нормализация и deterministic scoring аспектов.
2. Введены веса для orb exactness, planet importance, aspect type, personal relevance и section relevance.
3. Добавлен deterministic aspect pattern clustering.
4. Patterns классифицируются как `support`, `tension`, `mixed`, `integration`.
5. Добавлены tests на ranking/cluster behavior для tight personal aspects vs wide/outer patterns.

## Затрагиваемые файлы

| Файл                                                                 | Действие                        |
| -------------------------------------------------------------------- | ------------------------------- |
| `backend/app/modules/report_narratives/aspect_synthesis.py`          | Ranker / clusterer             |
| `backend/app/modules/report_narratives/schemas.py`                   | `RankedAspect`, `AspectPattern` |
| `backend/tests/unit/test_report_narratives/test_aspect_synthesis.py` | Ranking/cluster tests           |
| `backend/app/modules/report_narratives/deep_synthesis.py`            | Подключение ranked/pattern synthesis |

## Acceptance criteria

- [x] Top aspects are deterministic and explainable.
- [x] Wide minor aspects cannot dominate tight personal aspects.
- [x] Outer-outer aspects are downweighted unless connected to personal planets/angles.
- [x] Every `AspectPattern` includes mechanism, manifestation, risk, mature expression and evidence ids.
- [x] Section targets are assigned for each pattern.

## Verification

- `pytest tests/unit/test_report_narratives/test_aspect_synthesis.py -q`
- `pytest tests/unit/test_report_narratives -q`
- `ruff check app/modules/report_narratives/aspect_synthesis.py app/modules/report_narratives/schemas.py tests/unit/test_report_narratives/test_aspect_synthesis.py`
- `mypy app/modules/report_narratives/aspect_synthesis.py tests/unit/test_report_narratives/test_aspect_synthesis.py`
