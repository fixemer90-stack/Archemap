# S03 — Chart Dynamics: Contradictions, Compensations, Maturity

> Статус: ⬜ Не начато

## Контекст

Пользовательский фидбек: отчёт всё ещё звучит как поверхностный гороскоп. Причина — недостаточно объясняется взаимодействие факторов: где карта тянет в разные стороны, как человек компенсирует напряжение и что является зрелой формой паттерна.

## Что сделать

1. Построить `ChartDynamic` items from:
   - dominant elements/modalities;
   - house axis patterns;
   - aspect patterns;
   - archetype claims;
   - socionics summary when relevant.
2. Вывести 3–5 central contradictions.
3. Для каждого contradiction указать:
   - source evidence;
   - psychological mechanism;
   - visible life manifestation;
   - failure mode;
   - mature expression;
   - calibration question.
4. Добавить maturity levels: low / medium / high expression.
5. Добавить tests against generic outputs: no item can be only “вы практичны/эмоциональны/структурны”.

## Затрагиваемые файлы

| Файл                                                               | Действие                                                   |
| ------------------------------------------------------------------ | ---------------------------------------------------------- |
| `backend/app/modules/report_narratives/deep_synthesis.py`          | Dynamics builder                                           |
| `backend/app/modules/report_narratives/schemas.py`                 | `ChartDynamic`, `ContradictionInsight`, `MaturityLevelSet` |
| `backend/tests/unit/test_report_narratives/test_chart_dynamics.py` | Dynamics tests                                             |

## Acceptance criteria

- [ ] At least 3 central contradictions are produced when chart evidence supports them.
- [ ] Contradictions reference aspect/house/planet evidence, not just archetype labels.
- [ ] Failure modes are concrete but non-diagnostic.
- [ ] Mature expressions are actionable and bounded.
- [ ] Calibration questions are specific enough to validate the hypothesis.
