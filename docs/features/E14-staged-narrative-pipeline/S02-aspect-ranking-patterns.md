# S02 — Aspect Ranking and Pattern Clustering

> Статус: ⬜ Не начато

## Контекст

Сейчас аспекты попадают в `key_aspects`, но часто остаются плоским списком. Для глубокого отчёта аспекты должны объяснять динамику карты: связь психических функций, внутреннее напряжение, ресурс, компенсацию и зрелую интеграцию.

## Что сделать

1. Нормализовать aspect facts: planet labels, aspect type, orb, applying/separating if available.
2. Ввести deterministic aspect score:
   - orb exactness;
   - planet importance;
   - aspect type weight;
   - personal relevance;
   - section relevance;
   - repeated theme bonus.
3. Ввести aspect pattern clustering:
   - personal planet clusters;
   - Moon/Mercury emotional-cognitive patterns;
   - Venus/Mars relationship/sexuality patterns;
   - Saturn boundary/maturity patterns;
   - Pluto/Uranus/Neptune deep/transpersonal patterns only when tied to personal planets or angles.
4. Классифицировать patterns as `support`, `tension`, `mixed`, `integration`.
5. Добавить tests на конкретные карты: tight aspects должны подниматься выше широких; personal aspects выше isolated outer-outer aspects.

## Затрагиваемые файлы

| Файл                                                                 | Действие                        |
| -------------------------------------------------------------------- | ------------------------------- |
| `backend/app/modules/report_narratives/aspect_synthesis.py`          | Новый ranker/clusterer          |
| `backend/app/modules/report_narratives/schemas.py`                   | `RankedAspect`, `AspectPattern` |
| `backend/tests/unit/test_report_narratives/test_aspect_synthesis.py` | Ranking/cluster tests           |

## Acceptance criteria

- [ ] Top aspects are deterministic and explainable.
- [ ] Wide minor aspects cannot dominate tight personal aspects.
- [ ] Outer-outer aspects are downweighted unless connected to personal planets/angles.
- [ ] Every `AspectPattern` includes mechanism, manifestation, risk, mature expression and evidence ids.
- [ ] Section targets are assigned for each pattern.
