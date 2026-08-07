# S03 — Chart Dynamics: Contradictions, Compensations, Maturity

> Статус: ✅ Готово
> Коммит: `91b34fa`

## Контекст

Пользовательский фидбек: отчёт всё ещё звучит как поверхностный гороскоп. Причина — недостаточно объясняется взаимодействие факторов: где карта тянет в разные стороны, как человек компенсирует напряжение и что является зрелой формой паттерна.

## Что сделано

1. Добавлены `ChartDynamic` items поверх аспектных паттернов, house-axis patterns и role synthesis.
2. Добавлены deterministic contradictions.
3. Добавлены bounded maturity levels: low / medium / high.
4. Добавлены calibration hypotheses поверх dynamics/contradictions.
5. Добавлены tests против generic/пустых dynamics outputs.

## Затрагиваемые файлы

| Файл                                                               | Действие                                                   |
| ------------------------------------------------------------------ | ---------------------------------------------------------- |
| `backend/app/modules/report_narratives/deep_synthesis.py`          | Dynamics builder                                           |
| `backend/app/modules/report_narratives/schemas.py`                 | `ChartDynamic`, `ContradictionInsight`, `MaturityLevelSet` |
| `backend/tests/unit/test_report_narratives/test_chart_dynamics.py` | Dynamics tests                                             |
| `backend/tests/unit/test_report_narratives/test_deep_synthesis.py` | Deep synthesis regression                                  |

## Acceptance criteria

- [x] At least 3 central contradictions are produced when chart evidence supports them.
- [x] Contradictions reference aspect/house/planet evidence, not just archetype labels.
- [x] Failure modes are concrete but non-diagnostic.
- [x] Mature expressions are actionable and bounded.
- [x] Calibration questions are specific enough to validate the hypothesis.

## Verification

- `pytest tests/unit/test_report_narratives/test_chart_dynamics.py tests/unit/test_report_narratives/test_deep_synthesis.py -q`
- `pytest tests/unit/test_report_narratives -q`
- `ruff check app/modules/report_narratives/deep_synthesis.py tests/unit/test_report_narratives/test_chart_dynamics.py`
- `mypy app/modules/report_narratives/deep_synthesis.py tests/unit/test_report_narratives/test_chart_dynamics.py`
